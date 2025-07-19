# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Concurrent processing system for handling multiple video generation requests.

This module provides asynchronous processing capabilities, request queuing,
and resource management for the multi-agent video system.
"""

import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union
from queue import Queue, PriorityQueue
import psutil
import os

from .models import VideoGenerationRequest, VideoStatus
from .session_manager import get_session_manager, SessionStage
from .error_handling import VideoSystemError, ProcessingError
from .logging_config import get_logger

logger = get_logger(__name__)


class RequestPriority(Enum):
    """Priority levels for video generation requests."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class ProcessorStatus(Enum):
    """Status of the concurrent processor."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class QueuedRequest:
    """Represents a queued video generation request."""
    request_id: str
    session_id: str
    request: VideoGenerationRequest
    priority: RequestPriority
    submitted_at: datetime
    user_id: Optional[str] = None
    estimated_duration: Optional[int] = None
    
    def __lt__(self, other):
        """Compare requests for priority queue ordering."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.submitted_at < other.submitted_at


@dataclass
class ProcessingTask:
    """Represents an active processing task."""
    task_id: str
    session_id: str
    request: VideoGenerationRequest
    future: Future
    started_at: datetime
    worker_id: str
    estimated_completion: Optional[datetime] = None


@dataclass
class ResourceLimits:
    """Resource limits for the processing system."""
    max_concurrent_requests: int = 5
    max_queue_size: int = 100
    max_memory_usage_percent: float = 80.0
    max_cpu_usage_percent: float = 85.0
    max_disk_usage_percent: float = 90.0
    worker_timeout_seconds: int = 3600  # 1 hour


@dataclass
class ProcessorMetrics:
    """Metrics for the concurrent processor."""
    total_requests_processed: int = 0
    total_requests_failed: int = 0
    total_requests_queued: int = 0
    current_active_tasks: int = 0
    current_queue_size: int = 0
    average_processing_time: float = 0.0
    peak_concurrent_requests: int = 0
    uptime_seconds: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class ConcurrentProcessor:
    """Manages concurrent processing of video generation requests."""
    
    def __init__(self, 
                 resource_limits: Optional[ResourceLimits] = None,
                 check_interval: float = 5.0):
        """Initialize the concurrent processor.
        
        Args:
            resource_limits: Resource limits configuration
            check_interval: Interval for resource monitoring in seconds
        """
        self.resource_limits = resource_limits or ResourceLimits()
        self.check_interval = check_interval
        
        # Processing state
        self.status = ProcessorStatus.STOPPED
        self.start_time: Optional[datetime] = None
        
        # Request queue and active tasks
        self.request_queue: PriorityQueue[QueuedRequest] = PriorityQueue()
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.completed_tasks: Dict[str, ProcessingTask] = {}
        
        # Thread pool for workers
        self.executor: Optional[ThreadPoolExecutor] = None
        
        # Monitoring and metrics
        self.metrics = ProcessorMetrics()
        self.resource_monitor_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        
        # Synchronization
        self.lock = threading.RLock()
        self.shutdown_event = threading.Event()
        
        # Session manager
        self.session_manager = get_session_manager()
        
        logger.info("ConcurrentProcessor initialized")
    
    def start(self) -> bool:
        """Start the concurrent processor.
        
        Returns:
            True if started successfully, False otherwise
        """
        with self.lock:
            if self.status != ProcessorStatus.STOPPED:
                logger.warning("Processor is already running or starting")
                return False
            
            self.status = ProcessorStatus.STARTING
            self.start_time = datetime.utcnow()
            self.shutdown_event.clear()
            
            try:
                # Initialize thread pool
                self.executor = ThreadPoolExecutor(
                    max_workers=self.resource_limits.max_concurrent_requests,
                    thread_name_prefix="VideoProcessor"
                )
                
                # Start monitoring thread
                self.resource_monitor_thread = threading.Thread(
                    target=self._resource_monitor_loop,
                    daemon=True,
                    name="ResourceMonitor"
                )
                self.resource_monitor_thread.start()
                
                # Start processor thread
                self.processor_thread = threading.Thread(
                    target=self._processor_loop,
                    daemon=True,
                    name="ProcessorLoop"
                )
                self.processor_thread.start()
                
                self.status = ProcessorStatus.RUNNING
                logger.info("ConcurrentProcessor started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start ConcurrentProcessor: {e}")
                self.status = ProcessorStatus.STOPPED
                return False
    
    def stop(self, timeout: float = 30.0) -> bool:
        """Stop the concurrent processor.
        
        Args:
            timeout: Maximum time to wait for shutdown
            
        Returns:
            True if stopped successfully, False otherwise
        """
        with self.lock:
            if self.status == ProcessorStatus.STOPPED:
                return True
            
            logger.info("Stopping ConcurrentProcessor...")
            self.status = ProcessorStatus.STOPPING
            
            # Signal shutdown
            self.shutdown_event.set()
            
            # Cancel active tasks
            for task in self.active_tasks.values():
                if not task.future.done():
                    task.future.cancel()
            
            # Shutdown executor
            if self.executor:
                self.executor.shutdown(wait=True, timeout=timeout)
            
            # Wait for threads to finish
            if self.resource_monitor_thread and self.resource_monitor_thread.is_alive():
                self.resource_monitor_thread.join(timeout=5.0)
            
            if self.processor_thread and self.processor_thread.is_alive():
                self.processor_thread.join(timeout=5.0)
            
            self.status = ProcessorStatus.STOPPED
            logger.info("ConcurrentProcessor stopped")
            return True
    
    def submit_request(self, 
                      request: VideoGenerationRequest,
                      user_id: Optional[str] = None,
                      priority: RequestPriority = RequestPriority.NORMAL) -> str:
        """Submit a video generation request for processing.
        
        Args:
            request: Video generation request
            user_id: Optional user identifier
            priority: Request priority
            
        Returns:
            Request ID for tracking
            
        Raises:
            ProcessingError: If the request cannot be queued
        """
        if self.status != ProcessorStatus.RUNNING:
            raise ProcessingError("Processor is not running")
        
        # Check queue capacity
        if self.request_queue.qsize() >= self.resource_limits.max_queue_size:
            raise ProcessingError("Request queue is full")
        
        # Create session
        session_id = self.session_manager.create_session(request, user_id)
        
        # Create queued request
        request_id = str(uuid.uuid4())
        queued_request = QueuedRequest(
            request_id=request_id,
            session_id=session_id,
            request=request,
            priority=priority,
            submitted_at=datetime.utcnow(),
            user_id=user_id,
            estimated_duration=self._estimate_processing_time(request)
        )
        
        # Add to queue
        self.request_queue.put(queued_request)
        
        # Update metrics
        with self.lock:
            self.metrics.total_requests_queued += 1
            self.metrics.current_queue_size = self.request_queue.qsize()
        
        # Update session status
        self.session_manager.update_session_status(
            session_id,
            VideoStatus.QUEUED,
            SessionStage.INITIALIZING,
            0.0
        )
        
        logger.info(f"Queued request {request_id} for session {session_id}")
        return request_id
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a submitted request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Request status information or None if not found
        """
        # Check active tasks
        with self.lock:
            for task in self.active_tasks.values():
                if task.task_id == request_id:
                    session_status = self.session_manager.get_session_status(task.session_id)
                    return {
                        "request_id": request_id,
                        "status": "processing",
                        "session_id": task.session_id,
                        "started_at": task.started_at.isoformat(),
                        "estimated_completion": task.estimated_completion.isoformat() if task.estimated_completion else None,
                        "session_status": session_status.model_dump() if session_status else None
                    }
            
            # Check completed tasks
            if request_id in self.completed_tasks:
                task = self.completed_tasks[request_id]
                session_status = self.session_manager.get_session_status(task.session_id)
                return {
                    "request_id": request_id,
                    "status": "completed",
                    "session_id": task.session_id,
                    "started_at": task.started_at.isoformat(),
                    "session_status": session_status.model_dump() if session_status else None
                }
        
        # Check queue
        queue_items = []
        temp_queue = PriorityQueue()
        
        try:
            while not self.request_queue.empty():
                item = self.request_queue.get_nowait()
                queue_items.append(item)
                temp_queue.put(item)
            
            # Restore queue
            while not temp_queue.empty():
                self.request_queue.put(temp_queue.get_nowait())
            
            # Find request in queue
            for item in queue_items:
                if item.request_id == request_id:
                    return {
                        "request_id": request_id,
                        "status": "queued",
                        "session_id": item.session_id,
                        "submitted_at": item.submitted_at.isoformat(),
                        "priority": item.priority.name,
                        "estimated_duration": item.estimated_duration
                    }
        
        except Exception as e:
            logger.error(f"Error checking queue for request {request_id}: {e}")
        
        return None
    
    def get_metrics(self) -> ProcessorMetrics:
        """Get current processor metrics.
        
        Returns:
            Current metrics
        """
        with self.lock:
            # Update dynamic metrics
            self.metrics.current_active_tasks = len(self.active_tasks)
            self.metrics.current_queue_size = self.request_queue.qsize()
            
            if self.start_time:
                self.metrics.uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            self.metrics.last_updated = datetime.utcnow()
            
            return self.metrics
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage.
        
        Returns:
            Resource usage information
        """
        try:
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process-specific usage
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3)
                },
                "process": {
                    "cpu_percent": process_cpu,
                    "memory_mb": process_memory.rss / (1024**2),
                    "memory_percent": (process_memory.rss / memory.total) * 100
                },
                "limits": {
                    "max_memory_percent": self.resource_limits.max_memory_usage_percent,
                    "max_cpu_percent": self.resource_limits.max_cpu_usage_percent,
                    "max_disk_percent": self.resource_limits.max_disk_usage_percent,
                    "max_concurrent_requests": self.resource_limits.max_concurrent_requests
                },
                "status": self.status.value
            }
        
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {"error": str(e)}
    
    def pause(self) -> bool:
        """Pause processing new requests.
        
        Returns:
            True if paused successfully
        """
        with self.lock:
            if self.status == ProcessorStatus.RUNNING:
                self.status = ProcessorStatus.PAUSED
                logger.info("ConcurrentProcessor paused")
                return True
            return False
    
    def resume(self) -> bool:
        """Resume processing requests.
        
        Returns:
            True if resumed successfully
        """
        with self.lock:
            if self.status == ProcessorStatus.PAUSED:
                self.status = ProcessorStatus.RUNNING
                logger.info("ConcurrentProcessor resumed")
                return True
            return False
    
    def _processor_loop(self):
        """Main processor loop that handles queued requests."""
        logger.info("Processor loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # Check if we can process more requests
                if (self.status != ProcessorStatus.RUNNING or
                    len(self.active_tasks) >= self.resource_limits.max_concurrent_requests):
                    time.sleep(1.0)
                    continue
                
                # Check resource constraints
                if not self._check_resource_availability():
                    time.sleep(5.0)
                    continue
                
                # Get next request from queue
                try:
                    queued_request = self.request_queue.get(timeout=1.0)
                except:
                    continue
                
                # Submit for processing
                self._start_processing_task(queued_request)
                
            except Exception as e:
                logger.error(f"Error in processor loop: {e}")
                time.sleep(1.0)
        
        logger.info("Processor loop stopped")
    
    def _start_processing_task(self, queued_request: QueuedRequest):
        """Start processing a queued request.
        
        Args:
            queued_request: Request to process
        """
        try:
            # Create processing task
            task_id = queued_request.request_id
            worker_id = f"worker-{len(self.active_tasks)}"
            
            # Submit to executor
            future = self.executor.submit(
                self._process_video_request,
                queued_request.session_id,
                queued_request.request
            )
            
            # Create task record
            processing_task = ProcessingTask(
                task_id=task_id,
                session_id=queued_request.session_id,
                request=queued_request.request,
                future=future,
                started_at=datetime.utcnow(),
                worker_id=worker_id,
                estimated_completion=datetime.utcnow() + timedelta(
                    seconds=queued_request.estimated_duration or 1800
                )
            )
            
            # Add to active tasks
            with self.lock:
                self.active_tasks[task_id] = processing_task
                self.metrics.current_active_tasks = len(self.active_tasks)
                self.metrics.peak_concurrent_requests = max(
                    self.metrics.peak_concurrent_requests,
                    len(self.active_tasks)
                )
            
            # Update session status
            self.session_manager.update_session_status(
                queued_request.session_id,
                VideoStatus.PROCESSING,
                SessionStage.RESEARCHING,
                0.1,
                estimated_completion=processing_task.estimated_completion
            )
            
            # Add completion callback
            future.add_done_callback(
                lambda f: self._task_completed(task_id, f)
            )
            
            logger.info(f"Started processing task {task_id} for session {queued_request.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start processing task: {e}")
            # Update session with error
            self.session_manager.update_session_status(
                queued_request.session_id,
                VideoStatus.FAILED,
                error_message=f"Failed to start processing: {str(e)}"
            )
    
    def _task_completed(self, task_id: str, future: Future):
        """Handle task completion.
        
        Args:
            task_id: Task identifier
            future: Completed future
        """
        with self.lock:
            task = self.active_tasks.pop(task_id, None)
            if not task:
                return
            
            # Move to completed tasks
            self.completed_tasks[task_id] = task
            
            # Update metrics
            self.metrics.current_active_tasks = len(self.active_tasks)
            
            processing_time = (datetime.utcnow() - task.started_at).total_seconds()
            
            if future.exception():
                self.metrics.total_requests_failed += 1
                logger.error(f"Task {task_id} failed: {future.exception()}")
                
                # Update session with error
                self.session_manager.update_session_status(
                    task.session_id,
                    VideoStatus.FAILED,
                    error_message=str(future.exception())
                )
            else:
                self.metrics.total_requests_processed += 1
                logger.info(f"Task {task_id} completed successfully in {processing_time:.1f}s")
                
                # Update average processing time
                total_completed = self.metrics.total_requests_processed
                self.metrics.average_processing_time = (
                    (self.metrics.average_processing_time * (total_completed - 1) + processing_time) /
                    total_completed
                )
    
    def _process_video_request(self, session_id: str, request: VideoGenerationRequest) -> Dict[str, Any]:
        """Process a video generation request.
        
        This is a placeholder for the actual video processing workflow.
        In a real implementation, this would coordinate all the sub-agents.
        
        Args:
            session_id: Session identifier
            request: Video generation request
            
        Returns:
            Processing result
        """
        try:
            logger.info(f"Processing video request for session {session_id}")
            
            # Simulate processing stages
            stages = [
                (SessionStage.RESEARCHING, 0.2),
                (SessionStage.SCRIPTING, 0.4),
                (SessionStage.ASSET_SOURCING, 0.6),
                (SessionStage.AUDIO_GENERATION, 0.8),
                (SessionStage.VIDEO_ASSEMBLY, 0.9),
                (SessionStage.FINALIZING, 0.95),
                (SessionStage.COMPLETED, 1.0)
            ]
            
            for stage, progress in stages:
                # Check for cancellation
                if self.shutdown_event.is_set():
                    raise ProcessingError("Processing cancelled due to shutdown")
                
                # Update session status
                self.session_manager.update_session_status(
                    session_id,
                    VideoStatus.PROCESSING,
                    stage,
                    progress
                )
                
                # Simulate processing time
                time.sleep(2.0)
            
            # Mark as completed
            self.session_manager.update_session_status(
                session_id,
                VideoStatus.COMPLETED,
                SessionStage.COMPLETED,
                1.0
            )
            
            return {
                "session_id": session_id,
                "status": "completed",
                "final_video_path": f"/tmp/video_{session_id}.mp4"
            }
            
        except Exception as e:
            logger.error(f"Error processing video request for session {session_id}: {e}")
            self.session_manager.update_session_status(
                session_id,
                VideoStatus.FAILED,
                error_message=str(e)
            )
            raise
    
    def _resource_monitor_loop(self):
        """Monitor system resources and adjust processing accordingly."""
        logger.info("Resource monitor started")
        
        while not self.shutdown_event.is_set():
            try:
                # Check resource usage
                resource_usage = self.get_resource_usage()
                system_usage = resource_usage.get("system", {})
                
                # Check if resources are constrained
                memory_constrained = (
                    system_usage.get("memory_percent", 0) > 
                    self.resource_limits.max_memory_usage_percent
                )
                cpu_constrained = (
                    system_usage.get("cpu_percent", 0) > 
                    self.resource_limits.max_cpu_usage_percent
                )
                disk_constrained = (
                    system_usage.get("disk_percent", 0) > 
                    self.resource_limits.max_disk_usage_percent
                )
                
                # Pause processing if resources are constrained
                if (memory_constrained or cpu_constrained or disk_constrained) and self.status == ProcessorStatus.RUNNING:
                    logger.warning("Resource constraints detected, pausing processor")
                    self.pause()
                elif not (memory_constrained or cpu_constrained or disk_constrained) and self.status == ProcessorStatus.PAUSED:
                    logger.info("Resource constraints cleared, resuming processor")
                    self.resume()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                time.sleep(self.check_interval)
        
        logger.info("Resource monitor stopped")
    
    def _check_resource_availability(self) -> bool:
        """Check if resources are available for processing.
        
        Returns:
            True if resources are available
        """
        try:
            resource_usage = self.get_resource_usage()
            system_usage = resource_usage.get("system", {})
            
            return (
                system_usage.get("memory_percent", 0) < self.resource_limits.max_memory_usage_percent and
                system_usage.get("cpu_percent", 0) < self.resource_limits.max_cpu_usage_percent and
                system_usage.get("disk_percent", 0) < self.resource_limits.max_disk_usage_percent
            )
        except Exception as e:
            logger.error(f"Error checking resource availability: {e}")
            return False
    
    def _estimate_processing_time(self, request: VideoGenerationRequest) -> int:
        """Estimate processing time for a request.
        
        Args:
            request: Video generation request
            
        Returns:
            Estimated processing time in seconds
        """
        # Base time
        base_time = 300  # 5 minutes
        
        # Adjust based on duration
        duration_factor = request.duration_preference / 60.0  # minutes
        duration_time = duration_factor * 120  # 2 minutes per minute of video
        
        # Adjust based on quality
        quality_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
            "ultra": 2.0
        }
        quality_multiplier = quality_multipliers.get(request.quality, 1.0)
        
        # Calculate total estimate
        total_time = int((base_time + duration_time) * quality_multiplier)
        
        return max(300, min(3600, total_time))  # Between 5 minutes and 1 hour


# Global processor instance
_concurrent_processor: Optional[ConcurrentProcessor] = None


def get_concurrent_processor() -> ConcurrentProcessor:
    """Get the global concurrent processor instance."""
    global _concurrent_processor
    if _concurrent_processor is None:
        _concurrent_processor = ConcurrentProcessor()
    return _concurrent_processor


def initialize_concurrent_processor(resource_limits: Optional[ResourceLimits] = None) -> ConcurrentProcessor:
    """Initialize the global concurrent processor."""
    global _concurrent_processor
    _concurrent_processor = ConcurrentProcessor(resource_limits)
    return _concurrent_processor