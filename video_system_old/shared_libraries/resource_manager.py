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

"""Resource monitoring and management system for the multi-agent video system.

This module provides comprehensive resource monitoring, allocation tracking,
and automatic resource management to ensure system stability under load.
"""

import threading
import time
import psutil
import gc
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

from video_system.utils.logging_config import get_logger

logger = get_logger(__name__)


class ResourceType(Enum):
    """Types of system resources."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"


class AlertLevel(Enum):
    """Alert levels for resource monitoring."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceThresholds:
    """Resource usage thresholds for monitoring."""

    cpu_warning: float = 70.0
    cpu_critical: float = 85.0
    cpu_emergency: float = 95.0

    memory_warning: float = 70.0
    memory_critical: float = 85.0
    memory_emergency: float = 95.0

    disk_warning: float = 80.0
    disk_critical: float = 90.0
    disk_emergency: float = 95.0

    network_warning_mbps: float = 100.0
    network_critical_mbps: float = 500.0


@dataclass
class ResourceUsage:
    """Current resource usage information."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_percent: float
    disk_free_gb: float
    network_sent_mbps: float = 0.0
    network_recv_mbps: float = 0.0
    gpu_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    process_count: int = 0
    thread_count: int = 0


@dataclass
class ResourceAlert:
    """Resource usage alert."""

    timestamp: datetime
    resource_type: ResourceType
    level: AlertLevel
    message: str
    current_value: float
    threshold_value: float
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class ResourceAllocation:
    """Resource allocation for a specific task or session."""

    allocation_id: str
    session_id: str
    allocated_at: datetime
    cpu_cores: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    gpu_memory_mb: float = 0.0
    priority: int = 1  # 1 = highest, 5 = lowest
    active: bool = True


class ResourceManager:
    """Manages system resources and monitors usage."""

    def __init__(
        self,
        thresholds: Optional[ResourceThresholds] = None,
        monitoring_interval: float = 5.0,
        history_retention_hours: int = 24,
    ):
        """Initialize the resource manager.

        Args:
            thresholds: Resource usage thresholds
            monitoring_interval: Monitoring interval in seconds
            history_retention_hours: How long to keep usage history
        """
        self.thresholds = thresholds or ResourceThresholds()
        self.monitoring_interval = monitoring_interval
        self.history_retention = timedelta(hours=history_retention_hours)

        # Resource tracking
        self.usage_history: List[ResourceUsage] = []
        self.active_alerts: Dict[str, ResourceAlert] = {}
        self.alert_history: List[ResourceAlert] = []
        self.allocations: Dict[str, ResourceAllocation] = {}

        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()

        # Callbacks for resource events
        self.alert_callbacks: List[Callable[[ResourceAlert], None]] = []
        self.usage_callbacks: List[Callable[[ResourceUsage], None]] = []

        # Network monitoring baseline
        self.last_network_stats: Optional[Tuple[float, float]] = None
        self.last_network_time: Optional[datetime] = None

        logger.info("ResourceManager initialized")

    def start_monitoring(self) -> bool:
        """Start resource monitoring.

        Returns:
            True if monitoring started successfully
        """
        with self.lock:
            if self.monitoring_active:
                logger.warning("Resource monitoring is already active")
                return False

            self.monitoring_active = True
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="ResourceMonitor"
            )
            self.monitor_thread.start()

            logger.info("Resource monitoring started")
            return True

    def stop_monitoring(self) -> bool:
        """Stop resource monitoring.

        Returns:
            True if monitoring stopped successfully
        """
        with self.lock:
            if not self.monitoring_active:
                return True

            self.monitoring_active = False

            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10.0)

            logger.info("Resource monitoring stopped")
            return True

    def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage.

        Returns:
            Current resource usage
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)

            # Network usage
            network_sent_mbps, network_recv_mbps = self._get_network_usage()

            # GPU usage (if available)
            gpu_percent, gpu_memory_percent = self._get_gpu_usage()

            # Process information
            process_count = len(psutil.pids())
            current_process = psutil.Process()
            thread_count = current_process.num_threads()

            return ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                network_sent_mbps=network_sent_mbps,
                network_recv_mbps=network_recv_mbps,
                gpu_percent=gpu_percent,
                gpu_memory_percent=gpu_memory_percent,
                process_count=process_count,
                thread_count=thread_count,
            )

        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            # Return minimal usage data
            return ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_gb=0.0,
                disk_percent=0.0,
                disk_free_gb=0.0,
            )

    def allocate_resources(
        self,
        session_id: str,
        cpu_cores: float = 0.0,
        memory_mb: float = 0.0,
        disk_mb: float = 0.0,
        gpu_memory_mb: float = 0.0,
        priority: int = 1,
    ) -> str:
        """Allocate resources for a session.

        Args:
            session_id: Session identifier
            cpu_cores: CPU cores to allocate
            memory_mb: Memory in MB to allocate
            disk_mb: Disk space in MB to allocate
            gpu_memory_mb: GPU memory in MB to allocate
            priority: Priority level (1 = highest, 5 = lowest)

        Returns:
            Allocation ID
        """
        allocation_id = f"alloc_{session_id}_{int(time.time())}"

        allocation = ResourceAllocation(
            allocation_id=allocation_id,
            session_id=session_id,
            allocated_at=datetime.utcnow(),
            cpu_cores=cpu_cores,
            memory_mb=memory_mb,
            disk_mb=disk_mb,
            gpu_memory_mb=gpu_memory_mb,
            priority=priority,
        )

        with self.lock:
            self.allocations[allocation_id] = allocation

        logger.info(f"Allocated resources for session {session_id}: {allocation_id}")
        return allocation_id

    def deallocate_resources(self, allocation_id: str) -> bool:
        """Deallocate resources.

        Args:
            allocation_id: Allocation identifier

        Returns:
            True if deallocated successfully
        """
        with self.lock:
            allocation = self.allocations.pop(allocation_id, None)
            if allocation:
                allocation.active = False
                logger.info(f"Deallocated resources: {allocation_id}")
                return True
            return False

    def get_resource_availability(self) -> Dict[str, Any]:
        """Get current resource availability.

        Returns:
            Resource availability information
        """
        current_usage = self.get_current_usage()

        # Calculate allocated resources
        total_allocated_cpu = 0.0
        total_allocated_memory = 0.0
        total_allocated_disk = 0.0
        total_allocated_gpu_memory = 0.0

        with self.lock:
            for allocation in self.allocations.values():
                if allocation.active:
                    total_allocated_cpu += allocation.cpu_cores
                    total_allocated_memory += allocation.memory_mb
                    total_allocated_disk += allocation.disk_mb
                    total_allocated_gpu_memory += allocation.gpu_memory_mb

        # Get system totals
        cpu_count = psutil.cpu_count()
        memory_total_gb = psutil.virtual_memory().total / (1024**3)
        disk_total_gb = psutil.disk_usage("/").total / (1024**3)

        return {
            "cpu": {
                "total_cores": cpu_count,
                "allocated_cores": total_allocated_cpu,
                "available_cores": max(0, cpu_count - total_allocated_cpu),
                "usage_percent": current_usage.cpu_percent,
            },
            "memory": {
                "total_gb": memory_total_gb,
                "allocated_mb": total_allocated_memory,
                "available_gb": current_usage.memory_available_gb,
                "usage_percent": current_usage.memory_percent,
            },
            "disk": {
                "total_gb": disk_total_gb,
                "allocated_mb": total_allocated_disk,
                "free_gb": current_usage.disk_free_gb,
                "usage_percent": current_usage.disk_percent,
            },
            "gpu": {
                "allocated_memory_mb": total_allocated_gpu_memory,
                "usage_percent": current_usage.gpu_percent,
                "memory_percent": current_usage.gpu_memory_percent,
            },
            "network": {
                "sent_mbps": current_usage.network_sent_mbps,
                "recv_mbps": current_usage.network_recv_mbps,
            },
        }

    def can_allocate_resources(
        self,
        cpu_cores: float = 0.0,
        memory_mb: float = 0.0,
        disk_mb: float = 0.0,
        gpu_memory_mb: float = 0.0,
    ) -> Tuple[bool, str]:
        """Check if resources can be allocated.

        Args:
            cpu_cores: CPU cores needed
            memory_mb: Memory in MB needed
            disk_mb: Disk space in MB needed
            gpu_memory_mb: GPU memory in MB needed

        Returns:
            Tuple of (can_allocate, reason)
        """
        availability = self.get_resource_availability()

        # Check CPU
        if cpu_cores > availability["cpu"]["available_cores"]:
            return (
                False,
                f"Insufficient CPU cores: need {cpu_cores}, available {availability['cpu']['available_cores']}",
            )

        # Check memory
        memory_gb_needed = memory_mb / 1024
        if memory_gb_needed > availability["memory"]["available_gb"]:
            return (
                False,
                f"Insufficient memory: need {memory_gb_needed:.1f}GB, available {availability['memory']['available_gb']:.1f}GB",
            )

        # Check disk
        disk_gb_needed = disk_mb / 1024
        if disk_gb_needed > availability["disk"]["free_gb"]:
            return (
                False,
                f"Insufficient disk space: need {disk_gb_needed:.1f}GB, available {availability['disk']['free_gb']:.1f}GB",
            )

        return True, "Resources available"

    def get_usage_history(self, hours: int = 1) -> List[ResourceUsage]:
        """Get resource usage history.

        Args:
            hours: Number of hours of history to return

        Returns:
            List of resource usage records
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        with self.lock:
            return [
                usage for usage in self.usage_history if usage.timestamp >= cutoff_time
            ]

    def get_active_alerts(self) -> List[ResourceAlert]:
        """Get active resource alerts.

        Returns:
            List of active alerts
        """
        with self.lock:
            return [
                alert for alert in self.active_alerts.values() if not alert.resolved
            ]

    def get_alert_history(self, hours: int = 24) -> List[ResourceAlert]:
        """Get alert history.

        Args:
            hours: Number of hours of history to return

        Returns:
            List of alerts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        with self.lock:
            return [
                alert for alert in self.alert_history if alert.timestamp >= cutoff_time
            ]

    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]):
        """Add callback for resource alerts.

        Args:
            callback: Function to call when alerts are triggered
        """
        self.alert_callbacks.append(callback)

    def add_usage_callback(self, callback: Callable[[ResourceUsage], None]):
        """Add callback for resource usage updates.

        Args:
            callback: Function to call when usage is updated
        """
        self.usage_callbacks.append(callback)

    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return memory statistics.

        Returns:
            Memory statistics before and after GC
        """
        # Get memory before GC
        process = psutil.Process()
        memory_before = process.memory_info().rss / (1024**2)  # MB

        # Force garbage collection
        collected = gc.collect()

        # Get memory after GC
        memory_after = process.memory_info().rss / (1024**2)  # MB
        memory_freed = memory_before - memory_after

        logger.info(
            f"Garbage collection freed {memory_freed:.1f}MB, collected {collected} objects"
        )

        return {
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after,
            "memory_freed_mb": memory_freed,
            "objects_collected": collected,
        }

    def optimize_resources(self) -> Dict[str, Any]:
        """Perform resource optimization.

        Returns:
            Optimization results
        """
        results = {}

        # Force garbage collection
        gc_results = self.force_garbage_collection()
        results["garbage_collection"] = gc_results

        # Clear old usage history
        cutoff_time = datetime.utcnow() - self.history_retention
        with self.lock:
            old_count = len(self.usage_history)
            self.usage_history = [
                usage for usage in self.usage_history if usage.timestamp >= cutoff_time
            ]
            new_count = len(self.usage_history)
            results["history_cleanup"] = {
                "old_count": old_count,
                "new_count": new_count,
                "removed": old_count - new_count,
            }

        # Clear resolved alerts older than 1 hour
        alert_cutoff = datetime.utcnow() - timedelta(hours=1)
        with self.lock:
            old_alert_count = len(self.alert_history)
            self.alert_history = [
                alert
                for alert in self.alert_history
                if not alert.resolved or alert.resolved_at >= alert_cutoff
            ]
            new_alert_count = len(self.alert_history)
            results["alert_cleanup"] = {
                "old_count": old_alert_count,
                "new_count": new_alert_count,
                "removed": old_alert_count - new_alert_count,
            }

        logger.info(f"Resource optimization completed: {results}")
        return results

    def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Resource monitoring loop started")

        while self.monitoring_active:
            try:
                # Get current usage
                usage = self.get_current_usage()

                # Store in history
                with self.lock:
                    self.usage_history.append(usage)

                    # Limit history size
                    cutoff_time = datetime.utcnow() - self.history_retention
                    self.usage_history = [
                        u for u in self.usage_history if u.timestamp >= cutoff_time
                    ]

                # Check for alerts
                self._check_resource_alerts(usage)

                # Call usage callbacks
                for callback in self.usage_callbacks:
                    try:
                        callback(usage)
                    except Exception as e:
                        logger.error(f"Error in usage callback: {e}")

                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

        logger.info("Resource monitoring loop stopped")

    def _check_resource_alerts(self, usage: ResourceUsage):
        """Check for resource alerts based on current usage.

        Args:
            usage: Current resource usage
        """
        alerts_to_check = [
            (
                ResourceType.CPU,
                usage.cpu_percent,
                self.thresholds.cpu_warning,
                self.thresholds.cpu_critical,
                self.thresholds.cpu_emergency,
            ),
            (
                ResourceType.MEMORY,
                usage.memory_percent,
                self.thresholds.memory_warning,
                self.thresholds.memory_critical,
                self.thresholds.memory_emergency,
            ),
            (
                ResourceType.DISK,
                usage.disk_percent,
                self.thresholds.disk_warning,
                self.thresholds.disk_critical,
                self.thresholds.disk_emergency,
            ),
        ]

        for (
            resource_type,
            current_value,
            warning_threshold,
            critical_threshold,
            emergency_threshold,
        ) in alerts_to_check:
            alert_key = f"{resource_type.value}_alert"

            # Determine alert level
            alert_level = None
            threshold_value = 0.0

            if current_value >= emergency_threshold:
                alert_level = AlertLevel.EMERGENCY
                threshold_value = emergency_threshold
            elif current_value >= critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = critical_threshold
            elif current_value >= warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = warning_threshold

            # Handle alert
            if alert_level:
                # Create or update alert
                if (
                    alert_key not in self.active_alerts
                    or self.active_alerts[alert_key].resolved
                ):
                    alert = ResourceAlert(
                        timestamp=datetime.utcnow(),
                        resource_type=resource_type,
                        level=alert_level,
                        message=f"{resource_type.value.upper()} usage is {current_value:.1f}% (threshold: {threshold_value:.1f}%)",
                        current_value=current_value,
                        threshold_value=threshold_value,
                    )

                    with self.lock:
                        self.active_alerts[alert_key] = alert
                        self.alert_history.append(alert)

                    # Call alert callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"Error in alert callback: {e}")

                    logger.warning(f"Resource alert: {alert.message}")
            else:
                # Resolve existing alert if usage is back to normal
                if (
                    alert_key in self.active_alerts
                    and not self.active_alerts[alert_key].resolved
                ):
                    with self.lock:
                        self.active_alerts[alert_key].resolved = True
                        self.active_alerts[alert_key].resolved_at = datetime.utcnow()

                    logger.info(
                        f"Resource alert resolved: {resource_type.value.upper()} usage back to normal"
                    )

    def _get_network_usage(self) -> Tuple[float, float]:
        """Get network usage in Mbps.

        Returns:
            Tuple of (sent_mbps, recv_mbps)
        """
        try:
            current_time = datetime.utcnow()
            net_io = psutil.net_io_counters()
            current_stats = (net_io.bytes_sent, net_io.bytes_recv)

            if self.last_network_stats and self.last_network_time:
                time_delta = (current_time - self.last_network_time).total_seconds()
                if time_delta > 0:
                    sent_delta = current_stats[0] - self.last_network_stats[0]
                    recv_delta = current_stats[1] - self.last_network_stats[1]

                    sent_mbps = (sent_delta * 8) / (
                        time_delta * 1024 * 1024
                    )  # Convert to Mbps
                    recv_mbps = (recv_delta * 8) / (
                        time_delta * 1024 * 1024
                    )  # Convert to Mbps

                    self.last_network_stats = current_stats
                    self.last_network_time = current_time

                    return sent_mbps, recv_mbps

            # First measurement or error
            self.last_network_stats = current_stats
            self.last_network_time = current_time
            return 0.0, 0.0

        except Exception as e:
            logger.error(f"Error getting network usage: {e}")
            return 0.0, 0.0

    def _get_gpu_usage(self) -> Tuple[float, float]:
        """Get GPU usage if available.

        Returns:
            Tuple of (gpu_percent, gpu_memory_percent)
        """
        try:
            # Try to get GPU usage using nvidia-ml-py if available
            import pynvml

            pynvml.nvmlInit()

            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Use first GPU

                # Get utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_percent = util.gpu

                # Get memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_memory_percent = (mem_info.used / mem_info.total) * 100

                return float(gpu_percent), float(gpu_memory_percent)

        except ImportError:
            # pynvml not available
            pass
        except Exception as e:
            logger.debug(f"Error getting GPU usage: {e}")

        return 0.0, 0.0


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def initialize_resource_manager(
    thresholds: Optional[ResourceThresholds] = None,
) -> ResourceManager:
    """Initialize the global resource manager."""
    global _resource_manager
    _resource_manager = ResourceManager(thresholds)
    return _resource_manager
