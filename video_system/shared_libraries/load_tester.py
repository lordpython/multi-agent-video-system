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

"""Load testing and performance validation utilities for the multi-agent video system.

This module provides comprehensive load testing capabilities to validate system
performance under various load conditions and identify bottlenecks.
"""

import asyncio
import concurrent.futures
import json
import random
import statistics
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
import uuid

from .models import VideoGenerationRequest
from .concurrent_processor import get_concurrent_processor, RequestPriority
from .resource_manager import get_resource_manager
from .rate_limiter import get_rate_limiter
from .logging_config import get_logger

logger = get_logger(__name__)


class LoadTestType(Enum):
    """Types of load tests."""
    CONSTANT_LOAD = "constant_load"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    STRESS = "stress"
    ENDURANCE = "endurance"
    BURST = "burst"


class TestPhase(Enum):
    """Phases of load testing."""
    PREPARING = "preparing"
    RUNNING = "running"
    RAMPING_DOWN = "ramping_down"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    test_name: str
    test_type: LoadTestType
    duration_seconds: int = 300  # 5 minutes
    max_concurrent_users: int = 10
    ramp_up_seconds: int = 60
    ramp_down_seconds: int = 30
    requests_per_user: int = 1
    think_time_seconds: float = 1.0
    timeout_seconds: float = 300.0
    target_success_rate: float = 0.95
    target_avg_response_time_ms: float = 5000.0
    collect_detailed_metrics: bool = True


@dataclass
class RequestResult:
    """Result of a single request during load testing."""
    request_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    response_time_ms: float = 0.0
    status_code: Optional[int] = None
    rate_limited: bool = False


@dataclass
class UserMetrics:
    """Metrics for a single virtual user."""
    user_id: str
    requests_sent: int = 0
    requests_completed: int = 0
    requests_failed: int = 0
    total_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    rate_limited_count: int = 0


@dataclass
class LoadTestMetrics:
    """Comprehensive metrics for a load test."""
    test_name: str
    test_type: LoadTestType
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    
    # Throughput metrics
    requests_per_second: float = 0.0
    peak_concurrent_users: int = 0
    
    # Success metrics
    success_rate: float = 0.0
    error_rate: float = 0.0
    
    # Resource metrics
    peak_cpu_percent: float = 0.0
    peak_memory_percent: float = 0.0
    peak_disk_percent: float = 0.0
    
    # Detailed results
    request_results: List[RequestResult] = field(default_factory=list)
    user_metrics: Dict[str, UserMetrics] = field(default_factory=dict)
    resource_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    
    # Test status
    phase: TestPhase = TestPhase.PREPARING
    error_messages: List[str] = field(default_factory=list)


class VirtualUser:
    """Represents a virtual user for load testing."""
    
    def __init__(self, 
                 user_id: str, 
                 config: LoadTestConfig,
                 request_generator: Callable[[], VideoGenerationRequest]):
        """Initialize virtual user.
        
        Args:
            user_id: Unique user identifier
            config: Load test configuration
            request_generator: Function to generate test requests
        """
        self.user_id = user_id
        self.config = config
        self.request_generator = request_generator
        self.metrics = UserMetrics(user_id=user_id)
        self.active = False
        self.processor = get_concurrent_processor()
    
    async def run(self, stop_event: asyncio.Event) -> List[RequestResult]:
        """Run the virtual user's load test scenario.
        
        Args:
            stop_event: Event to signal when to stop
            
        Returns:
            List of request results
        """
        results = []
        self.active = True
        
        try:
            for i in range(self.config.requests_per_user):
                if stop_event.is_set():
                    break
                
                # Generate and send request
                result = await self._send_request()
                results.append(result)
                
                # Update metrics
                self._update_metrics(result)
                
                # Think time between requests
                if i < self.config.requests_per_user - 1:
                    await asyncio.sleep(self.config.think_time_seconds)
        
        except Exception as e:
            logger.error(f"Error in virtual user {self.user_id}: {e}")
        
        finally:
            self.active = False
        
        return results
    
    async def _send_request(self) -> RequestResult:
        """Send a single request and measure performance.
        
        Returns:
            Request result
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        result = RequestResult(
            request_id=request_id,
            user_id=self.user_id,
            start_time=start_time
        )
        
        try:
            # Generate request
            video_request = self.request_generator()
            
            # Submit request to processor
            submitted_request_id = self.processor.submit_request(
                video_request,
                user_id=self.user_id,
                priority=RequestPriority.NORMAL
            )
            
            # Wait for completion or timeout
            timeout_time = start_time + timedelta(seconds=self.config.timeout_seconds)
            
            while datetime.utcnow() < timeout_time:
                status = self.processor.get_request_status(submitted_request_id)
                if status:
                    if status["status"] == "completed":
                        result.success = True
                        break
                    elif status["status"] == "failed":
                        result.success = False
                        result.error_message = "Request processing failed"
                        break
                
                await asyncio.sleep(1.0)  # Check every second
            
            if not result.success and not result.error_message:
                result.error_message = "Request timeout"
        
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Request {request_id} failed: {e}")
        
        finally:
            result.end_time = datetime.utcnow()
            result.response_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _update_metrics(self, result: RequestResult):
        """Update user metrics with request result.
        
        Args:
            result: Request result to process
        """
        self.metrics.requests_sent += 1
        
        if result.end_time:
            self.metrics.requests_completed += 1
            self.metrics.total_response_time_ms += result.response_time_ms
            self.metrics.min_response_time_ms = min(self.metrics.min_response_time_ms, result.response_time_ms)
            self.metrics.max_response_time_ms = max(self.metrics.max_response_time_ms, result.response_time_ms)
        
        if not result.success:
            self.metrics.requests_failed += 1
        
        if result.rate_limited:
            self.metrics.rate_limited_count += 1


class LoadTester:
    """Main load testing orchestrator."""
    
    def __init__(self):
        """Initialize the load tester."""
        self.active_tests: Dict[str, LoadTestMetrics] = {}
        self.test_history: List[LoadTestMetrics] = []
        self.resource_manager = get_resource_manager()
        self.rate_limiter = get_rate_limiter()
        self.lock = threading.Lock()
        
        logger.info("LoadTester initialized")
    
    async def run_load_test(self, 
                           config: LoadTestConfig,
                           request_generator: Optional[Callable[[], VideoGenerationRequest]] = None) -> LoadTestMetrics:
        """Run a load test with the specified configuration.
        
        Args:
            config: Load test configuration
            request_generator: Function to generate test requests
            
        Returns:
            Load test metrics
        """
        if request_generator is None:
            request_generator = self._default_request_generator
        
        # Initialize metrics
        metrics = LoadTestMetrics(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.utcnow(),
            phase=TestPhase.PREPARING
        )
        
        with self.lock:
            self.active_tests[config.test_name] = metrics
        
        try:
            logger.info(f"Starting load test: {config.test_name}")
            
            # Start resource monitoring
            resource_monitor_task = asyncio.create_task(
                self._monitor_resources(metrics, config.duration_seconds + config.ramp_up_seconds + config.ramp_down_seconds)
            )
            
            # Run the actual load test
            await self._execute_load_test(config, request_generator, metrics)
            
            # Stop resource monitoring
            resource_monitor_task.cancel()
            
            # Calculate final metrics
            self._calculate_final_metrics(metrics)
            
            metrics.phase = TestPhase.COMPLETED
            metrics.end_time = datetime.utcnow()
            metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            
            logger.info(f"Load test completed: {config.test_name}")
            
        except Exception as e:
            metrics.phase = TestPhase.FAILED
            metrics.error_messages.append(str(e))
            logger.error(f"Load test failed: {config.test_name} - {e}")
        
        finally:
            # Move to history
            with self.lock:
                self.active_tests.pop(config.test_name, None)
                self.test_history.append(metrics)
                
                # Limit history size
                if len(self.test_history) > 100:
                    self.test_history = self.test_history[-50:]
        
        return metrics
    
    async def _execute_load_test(self, 
                                config: LoadTestConfig,
                                request_generator: Callable[[], VideoGenerationRequest],
                                metrics: LoadTestMetrics):
        """Execute the main load test logic.
        
        Args:
            config: Load test configuration
            request_generator: Function to generate test requests
            metrics: Metrics object to update
        """
        metrics.phase = TestPhase.RUNNING
        
        # Create stop event
        stop_event = asyncio.Event()
        
        # Schedule test phases
        if config.test_type == LoadTestType.CONSTANT_LOAD:
            await self._run_constant_load(config, request_generator, metrics, stop_event)
        elif config.test_type == LoadTestType.RAMP_UP:
            await self._run_ramp_up_test(config, request_generator, metrics, stop_event)
        elif config.test_type == LoadTestType.SPIKE:
            await self._run_spike_test(config, request_generator, metrics, stop_event)
        elif config.test_type == LoadTestType.STRESS:
            await self._run_stress_test(config, request_generator, metrics, stop_event)
        elif config.test_type == LoadTestType.ENDURANCE:
            await self._run_endurance_test(config, request_generator, metrics, stop_event)
        elif config.test_type == LoadTestType.BURST:
            await self._run_burst_test(config, request_generator, metrics, stop_event)
        else:
            raise ValueError(f"Unsupported test type: {config.test_type}")
    
    async def _run_constant_load(self, 
                                config: LoadTestConfig,
                                request_generator: Callable[[], VideoGenerationRequest],
                                metrics: LoadTestMetrics,
                                stop_event: asyncio.Event):
        """Run constant load test.
        
        Args:
            config: Test configuration
            request_generator: Request generator function
            metrics: Metrics to update
            stop_event: Stop event
        """
        # Create virtual users
        users = []
        for i in range(config.max_concurrent_users):
            user_id = f"user_{i:04d}"
            user = VirtualUser(user_id, config, request_generator)
            users.append(user)
            metrics.user_metrics[user_id] = user.metrics
        
        # Start all users
        user_tasks = [asyncio.create_task(user.run(stop_event)) for user in users]
        metrics.peak_concurrent_users = len(users)
        
        # Wait for test duration
        await asyncio.sleep(config.duration_seconds)
        
        # Stop all users
        stop_event.set()
        
        # Collect results
        all_results = []
        for task in user_tasks:
            try:
                results = await asyncio.wait_for(task, timeout=30.0)
                all_results.extend(results)
            except asyncio.TimeoutError:
                logger.warning("User task timed out during shutdown")
        
        metrics.request_results = all_results
    
    async def _run_ramp_up_test(self, 
                               config: LoadTestConfig,
                               request_generator: Callable[[], VideoGenerationRequest],
                               metrics: LoadTestMetrics,
                               stop_event: asyncio.Event):
        """Run ramp-up load test.
        
        Args:
            config: Test configuration
            request_generator: Request generator function
            metrics: Metrics to update
            stop_event: Stop event
        """
        users = []
        user_tasks = []
        all_results = []
        
        # Calculate ramp-up schedule
        user_interval = config.ramp_up_seconds / config.max_concurrent_users
        
        # Ramp up users gradually
        for i in range(config.max_concurrent_users):
            user_id = f"user_{i:04d}"
            user = VirtualUser(user_id, config, request_generator)
            users.append(user)
            metrics.user_metrics[user_id] = user.metrics
            
            # Start user
            task = asyncio.create_task(user.run(stop_event))
            user_tasks.append(task)
            
            # Update peak concurrent users
            metrics.peak_concurrent_users = len([u for u in users if u.active])
            
            # Wait before starting next user
            if i < config.max_concurrent_users - 1:
                await asyncio.sleep(user_interval)
        
        # Run at full load
        await asyncio.sleep(config.duration_seconds)
        
        # Ramp down
        metrics.phase = TestPhase.RAMPING_DOWN
        stop_event.set()
        
        # Collect results
        for task in user_tasks:
            try:
                results = await asyncio.wait_for(task, timeout=30.0)
                all_results.extend(results)
            except asyncio.TimeoutError:
                logger.warning("User task timed out during shutdown")
        
        metrics.request_results = all_results
    
    async def _run_spike_test(self, 
                             config: LoadTestConfig,
                             request_generator: Callable[[], VideoGenerationRequest],
                             metrics: LoadTestMetrics,
                             stop_event: asyncio.Event):
        """Run spike load test.
        
        Args:
            config: Test configuration
            request_generator: Request generator function
            metrics: Metrics to update
            stop_event: Stop event
        """
        # Start with baseline load (25% of max)
        baseline_users = max(1, config.max_concurrent_users // 4)
        
        # Phase 1: Baseline load
        users = []
        user_tasks = []
        
        for i in range(baseline_users):
            user_id = f"baseline_user_{i:04d}"
            user = VirtualUser(user_id, config, request_generator)
            users.append(user)
            metrics.user_metrics[user_id] = user.metrics
            
            task = asyncio.create_task(user.run(stop_event))
            user_tasks.append(task)
        
        # Run baseline for 1/3 of duration
        await asyncio.sleep(config.duration_seconds // 3)
        
        # Phase 2: Spike to full load
        spike_users = config.max_concurrent_users - baseline_users
        for i in range(spike_users):
            user_id = f"spike_user_{i:04d}"
            user = VirtualUser(user_id, config, request_generator)
            users.append(user)
            metrics.user_metrics[user_id] = user.metrics
            
            task = asyncio.create_task(user.run(stop_event))
            user_tasks.append(task)
        
        metrics.peak_concurrent_users = len(users)
        
        # Run spike for 1/3 of duration
        await asyncio.sleep(config.duration_seconds // 3)
        
        # Phase 3: Back to baseline
        stop_event.set()
        
        # Wait for remaining duration
        await asyncio.sleep(config.duration_seconds // 3)
        
        # Collect results
        all_results = []
        for task in user_tasks:
            try:
                results = await asyncio.wait_for(task, timeout=30.0)
                all_results.extend(results)
            except asyncio.TimeoutError:
                logger.warning("User task timed out during shutdown")
        
        metrics.request_results = all_results
    
    async def _run_stress_test(self, 
                              config: LoadTestConfig,
                              request_generator: Callable[[], VideoGenerationRequest],
                              metrics: LoadTestMetrics,
                              stop_event: asyncio.Event):
        """Run stress test (gradually increase load beyond normal capacity).
        
        Args:
            config: Test configuration
            request_generator: Request generator function
            metrics: Metrics to update
            stop_event: Stop event
        """
        # Stress test uses 150% of configured max users
        stress_users = int(config.max_concurrent_users * 1.5)
        
        users = []
        user_tasks = []
        all_results = []
        
        # Gradually add users beyond normal capacity
        user_interval = config.duration_seconds / stress_users
        
        for i in range(stress_users):
            user_id = f"stress_user_{i:04d}"
            user = VirtualUser(user_id, config, request_generator)
            users.append(user)
            metrics.user_metrics[user_id] = user.metrics
            
            task = asyncio.create_task(user.run(stop_event))
            user_tasks.append(task)
            
            metrics.peak_concurrent_users = len([u for u in users if u.active])
            
            if i < stress_users - 1:
                await asyncio.sleep(user_interval)
        
        # Let stress test run for remaining time
        remaining_time = config.duration_seconds - (stress_users * user_interval)
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)
        
        stop_event.set()
        
        # Collect results
        for task in user_tasks:
            try:
                results = await asyncio.wait_for(task, timeout=30.0)
                all_results.extend(results)
            except asyncio.TimeoutError:
                logger.warning("User task timed out during shutdown")
        
        metrics.request_results = all_results
    
    async def _run_endurance_test(self, 
                                 config: LoadTestConfig,
                                 request_generator: Callable[[], VideoGenerationRequest],
                                 metrics: LoadTestMetrics,
                                 stop_event: asyncio.Event):
        """Run endurance test (constant load for extended period).
        
        Args:
            config: Test configuration
            request_generator: Request generator function
            metrics: Metrics to update
            stop_event: Stop event
        """
        # Endurance test runs at 75% capacity for extended time
        endurance_users = int(config.max_concurrent_users * 0.75)
        
        # Create users with longer think times to simulate realistic usage
        endurance_config = LoadTestConfig(
            test_name=config.test_name,
            test_type=config.test_type,
            duration_seconds=config.duration_seconds,
            max_concurrent_users=endurance_users,
            requests_per_user=config.requests_per_user * 3,  # More requests over time
            think_time_seconds=config.think_time_seconds * 2,  # Longer think time
            timeout_seconds=config.timeout_seconds
        )
        
        users = []
        user_tasks = []
        
        for i in range(endurance_users):
            user_id = f"endurance_user_{i:04d}"
            user = VirtualUser(user_id, endurance_config, request_generator)
            users.append(user)
            metrics.user_metrics[user_id] = user.metrics
            
            task = asyncio.create_task(user.run(stop_event))
            user_tasks.append(task)
        
        metrics.peak_concurrent_users = len(users)
        
        # Run for full duration
        await asyncio.sleep(config.duration_seconds)
        stop_event.set()
        
        # Collect results
        all_results = []
        for task in user_tasks:
            try:
                results = await asyncio.wait_for(task, timeout=60.0)  # Longer timeout for endurance
                all_results.extend(results)
            except asyncio.TimeoutError:
                logger.warning("User task timed out during shutdown")
        
        metrics.request_results = all_results
    
    async def _run_burst_test(self, 
                             config: LoadTestConfig,
                             request_generator: Callable[[], VideoGenerationRequest],
                             metrics: LoadTestMetrics,
                             stop_event: asyncio.Event):
        """Run burst test (short bursts of high load).
        
        Args:
            config: Test configuration
            request_generator: Request generator function
            metrics: Metrics to update
            stop_event: Stop event
        """
        all_results = []
        burst_duration = 30  # 30 second bursts
        rest_duration = 60   # 60 second rest periods
        
        total_time = 0
        burst_count = 0
        
        while total_time < config.duration_seconds:
            burst_count += 1
            logger.info(f"Starting burst {burst_count}")
            
            # Create burst users
            users = []
            user_tasks = []
            
            for i in range(config.max_concurrent_users):
                user_id = f"burst_{burst_count}_user_{i:04d}"
                
                # Create short burst config
                burst_config = LoadTestConfig(
                    test_name=f"{config.test_name}_burst_{burst_count}",
                    test_type=config.test_type,
                    duration_seconds=burst_duration,
                    max_concurrent_users=config.max_concurrent_users,
                    requests_per_user=1,  # One request per burst
                    think_time_seconds=0.1,  # Very short think time
                    timeout_seconds=config.timeout_seconds
                )
                
                user = VirtualUser(user_id, burst_config, request_generator)
                users.append(user)
                metrics.user_metrics[user_id] = user.metrics
                
                task = asyncio.create_task(user.run(stop_event))
                user_tasks.append(task)
            
            metrics.peak_concurrent_users = max(metrics.peak_concurrent_users, len(users))
            
            # Wait for burst to complete
            await asyncio.sleep(burst_duration)
            
            # Collect burst results
            for task in user_tasks:
                try:
                    results = await asyncio.wait_for(task, timeout=10.0)
                    all_results.extend(results)
                except asyncio.TimeoutError:
                    logger.warning(f"Burst {burst_count} task timed out")
            
            total_time += burst_duration
            
            # Rest period (if not the last burst)
            if total_time + rest_duration < config.duration_seconds:
                logger.info(f"Resting after burst {burst_count}")
                await asyncio.sleep(rest_duration)
                total_time += rest_duration
            else:
                # Final rest period (partial)
                remaining_time = config.duration_seconds - total_time
                if remaining_time > 0:
                    await asyncio.sleep(remaining_time)
                break
        
        metrics.request_results = all_results
    
    async def _monitor_resources(self, metrics: LoadTestMetrics, duration_seconds: int):
        """Monitor system resources during load test.
        
        Args:
            metrics: Metrics object to update
            duration_seconds: How long to monitor
        """
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            try:
                # Get resource usage
                resource_usage = self.resource_manager.get_current_usage()
                
                # Update peak values
                metrics.peak_cpu_percent = max(metrics.peak_cpu_percent, resource_usage.cpu_percent)
                metrics.peak_memory_percent = max(metrics.peak_memory_percent, resource_usage.memory_percent)
                metrics.peak_disk_percent = max(metrics.peak_disk_percent, resource_usage.disk_percent)
                
                # Store snapshot
                if len(metrics.resource_snapshots) < 1000:  # Limit snapshots
                    snapshot = {
                        "timestamp": resource_usage.timestamp.isoformat(),
                        "cpu_percent": resource_usage.cpu_percent,
                        "memory_percent": resource_usage.memory_percent,
                        "disk_percent": resource_usage.disk_percent,
                        "network_sent_mbps": resource_usage.network_sent_mbps,
                        "network_recv_mbps": resource_usage.network_recv_mbps
                    }
                    metrics.resource_snapshots.append(snapshot)
                
                await asyncio.sleep(5.0)  # Sample every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                await asyncio.sleep(5.0)
    
    def _calculate_final_metrics(self, metrics: LoadTestMetrics):
        """Calculate final metrics from collected results.
        
        Args:
            metrics: Metrics object to update
        """
        results = metrics.request_results
        
        if not results:
            return
        
        # Basic counts
        metrics.total_requests = len(results)
        metrics.successful_requests = sum(1 for r in results if r.success)
        metrics.failed_requests = metrics.total_requests - metrics.successful_requests
        metrics.rate_limited_requests = sum(1 for r in results if r.rate_limited)
        
        # Success rates
        metrics.success_rate = metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0.0
        metrics.error_rate = metrics.failed_requests / metrics.total_requests if metrics.total_requests > 0 else 0.0
        
        # Response time metrics
        response_times = [r.response_time_ms for r in results if r.end_time]
        
        if response_times:
            metrics.avg_response_time_ms = statistics.mean(response_times)
            metrics.min_response_time_ms = min(response_times)
            metrics.max_response_time_ms = max(response_times)
            
            # Percentiles
            sorted_times = sorted(response_times)
            metrics.p50_response_time_ms = sorted_times[int(len(sorted_times) * 0.5)]
            metrics.p95_response_time_ms = sorted_times[int(len(sorted_times) * 0.95)]
            metrics.p99_response_time_ms = sorted_times[int(len(sorted_times) * 0.99)]
        
        # Throughput
        if metrics.duration_seconds > 0:
            metrics.requests_per_second = metrics.total_requests / metrics.duration_seconds
    
    def _default_request_generator(self) -> VideoGenerationRequest:
        """Generate a default test request.
        
        Returns:
            Video generation request
        """
        prompts = [
            "Create a video about artificial intelligence and machine learning",
            "Make a video explaining renewable energy sources",
            "Generate a video about space exploration and Mars missions",
            "Create an educational video about climate change",
            "Make a video about the history of the internet",
            "Generate a video about healthy cooking and nutrition",
            "Create a video about wildlife conservation",
            "Make a video explaining quantum computing basics"
        ]
        
        styles = ["professional", "casual", "educational", "entertainment"]
        qualities = ["medium", "high"]
        durations = [30, 60, 90, 120]
        
        return VideoGenerationRequest(
            prompt=random.choice(prompts),
            duration_preference=random.choice(durations),
            style=random.choice(styles),
            quality=random.choice(qualities),
            voice_preference="neutral"
        )
    
    def get_test_status(self, test_name: str) -> Optional[LoadTestMetrics]:
        """Get status of a running or completed test.
        
        Args:
            test_name: Name of the test
            
        Returns:
            Test metrics or None if not found
        """
        with self.lock:
            # Check active tests
            if test_name in self.active_tests:
                return self.active_tests[test_name]
            
            # Check history
            for test in reversed(self.test_history):
                if test.test_name == test_name:
                    return test
        
        return None
    
    def get_all_test_results(self) -> List[LoadTestMetrics]:
        """Get all test results.
        
        Returns:
            List of all test metrics
        """
        with self.lock:
            return list(self.active_tests.values()) + self.test_history.copy()
    
    def export_test_results(self, test_name: str, file_path: str) -> bool:
        """Export test results to JSON file.
        
        Args:
            test_name: Name of the test
            file_path: Path to export file
            
        Returns:
            True if exported successfully
        """
        test_metrics = self.get_test_status(test_name)
        if not test_metrics:
            return False
        
        try:
            # Convert to serializable format
            data = asdict(test_metrics)
            
            # Convert datetime objects to strings
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            serializable_data = convert_datetime(data)
            
            with open(file_path, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            
            logger.info(f"Exported test results to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export test results: {e}")
            return False


# Global load tester instance
_load_tester: Optional[LoadTester] = None


def get_load_tester() -> LoadTester:
    """Get the global load tester instance."""
    global _load_tester
    if _load_tester is None:
        _load_tester = LoadTester()
    return _load_tester