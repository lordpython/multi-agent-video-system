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

"""Resilience utilities for the video system."""

import time
import threading
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from enum import Enum

from .error_handling import get_logger

# Type variable for function return type
T = TypeVar('T')

# Configure logger
logger = get_logger("resilience")

class ServiceHealth(str, Enum):
    """Enum for service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthCheckResult:
    """Result of a health check."""
    
    def __init__(
        self,
        status: ServiceHealth,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ):
        """
        Initialize health check result.
        
        Args:
            status: Health status
            details: Additional details
            timestamp: Timestamp of the health check
        """
        self.status = status
        self.details = details or {}
        self.timestamp = timestamp or time.time()

class ResourceMetrics:
    """Metrics for resource usage."""
    
    def __init__(
        self,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
        disk_percent: float = 0.0,
        network_usage: float = 0.0
    ):
        """
        Initialize resource metrics.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
            network_usage: Network usage in bytes/second
        """
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.disk_percent = disk_percent
        self.network_usage = network_usage
        self.timestamp = time.time()

class ServiceRegistry:
    """Registry for services and their health check functions."""
    
    def __init__(self):
        """Initialize service registry."""
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_results: Dict[str, HealthCheckResult] = {}
    
    def register_service(
        self,
        service_name: str,
        health_check_func: Callable[[], Dict[str, Any]],
        health_check_interval: int = 60,
        critical: bool = False
    ) -> None:
        """
        Register a service with its health check function.
        
        Args:
            service_name: Name of the service
            health_check_func: Function to check service health
            health_check_interval: Interval in seconds between health checks
            critical: Whether the service is critical
        """
        self.services[service_name] = {
            "health_check_func": health_check_func,
            "health_check_interval": health_check_interval,
            "critical": critical,
            "last_check_time": 0
        }
        
        logger.info(f"Registered service: {service_name}, critical: {critical}")
    
    def check_service_health(self, service_name: str) -> HealthCheckResult:
        """
        Check the health of a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Health check result
        """
        if service_name not in self.services:
            return HealthCheckResult(
                status=ServiceHealth.UNHEALTHY,
                details={"error": f"Service {service_name} not registered"}
            )
        
        try:
            service = self.services[service_name]
            health_check_func = service["health_check_func"]
            
            result = health_check_func()
            status = result.get("status", "unhealthy")
            
            health_result = HealthCheckResult(
                status=ServiceHealth(status),
                details=result.get("details", {})
            )
            
            self.health_results[service_name] = health_result
            service["last_check_time"] = time.time()
            
            return health_result
        except Exception as e:
            logger.error(f"Health check failed for service {service_name}: {str(e)}")
            
            health_result = HealthCheckResult(
                status=ServiceHealth.UNHEALTHY,
                details={"error": str(e)}
            )
            
            self.health_results[service_name] = health_result
            return health_result
    
    def get_service_health(self, service_name: str) -> HealthCheckResult:
        """
        Get the health of a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Health check result
        """
        if service_name not in self.services:
            return HealthCheckResult(
                status=ServiceHealth.UNHEALTHY,
                details={"error": f"Service {service_name} not registered"}
            )
        
        service = self.services[service_name]
        current_time = time.time()
        last_check_time = service["last_check_time"]
        health_check_interval = service["health_check_interval"]
        
        # Check if we need to refresh the health check
        if current_time - last_check_time > health_check_interval:
            return self.check_service_health(service_name)
        
        # Return cached result
        return self.health_results.get(
            service_name,
            HealthCheckResult(
                status=ServiceHealth.UNHEALTHY,
                details={"error": "No health check result available"}
            )
        )
    
    def get_all_service_health(self) -> Dict[str, HealthCheckResult]:
        """
        Get the health of all services.
        
        Returns:
            Dictionary of service names to health check results
        """
        results = {}
        
        for service_name in self.services:
            results[service_name] = self.get_service_health(service_name)
        
        return results
    
    def is_system_healthy(self) -> bool:
        """
        Check if the system is healthy.
        
        Returns:
            True if all critical services are healthy, False otherwise
        """
        for service_name, service in self.services.items():
            if service["critical"]:
                health_result = self.get_service_health(service_name)
                if health_result.status == ServiceHealth.UNHEALTHY:
                    return False
        
        return True

class ResourceMonitor:
    """Monitor for system resources."""
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize resource monitor.
        
        Args:
            check_interval: Interval in seconds between resource checks
        """
        self.check_interval = check_interval
        self.last_metrics: Optional[ResourceMetrics] = None
        self.last_check_time = 0
    
    def check_resources(self) -> ResourceMetrics:
        """
        Check system resources.
        
        Returns:
            Resource metrics
        """
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            # Get network usage
            net_io_counters = psutil.net_io_counters()
            bytes_sent = net_io_counters.bytes_sent
            bytes_recv = net_io_counters.bytes_recv
            
            # Calculate network usage rate if we have previous measurements
            network_usage = 0.0
            if self.last_metrics and self.last_check_time > 0:
                time_diff = time.time() - self.last_check_time
                if time_diff > 0:
                    bytes_sent_diff = bytes_sent - getattr(self.last_metrics, 'bytes_sent', bytes_sent)
                    bytes_recv_diff = bytes_recv - getattr(self.last_metrics, 'bytes_recv', bytes_recv)
                    network_usage = (bytes_sent_diff + bytes_recv_diff) / time_diff
            
            metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_usage=network_usage
            )
            
            # Store additional attributes for next calculation
            setattr(metrics, 'bytes_sent', bytes_sent)
            setattr(metrics, 'bytes_recv', bytes_recv)
            
            self.last_metrics = metrics
            self.last_check_time = time.time()
            
            return metrics
        except ImportError:
            logger.warning("psutil not installed, using dummy resource metrics")
            return ResourceMetrics()
        except Exception as e:
            logger.error(f"Failed to check resources: {str(e)}")
            return ResourceMetrics()
    
    def get_resources(self) -> ResourceMetrics:
        """
        Get system resources.
        
        Returns:
            Resource metrics
        """
        current_time = time.time()
        
        # Check if we need to refresh the metrics
        if self.last_metrics is None or current_time - self.last_check_time > self.check_interval:
            return self.check_resources()
        
        # Return cached metrics
        return self.last_metrics

class GracefulDegradation:
    """Manager for graceful degradation of services."""
    
    def __init__(
        self,
        resource_monitor: Optional[ResourceMonitor] = None,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0
    ):
        """
        Initialize graceful degradation manager.
        
        Args:
            resource_monitor: Resource monitor
            cpu_threshold: CPU usage threshold percentage
            memory_threshold: Memory usage threshold percentage
        """
        self.resource_monitor = resource_monitor or ResourceMonitor()
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
    
    def should_degrade(self) -> bool:
        """
        Check if services should be degraded.
        
        Returns:
            True if services should be degraded, False otherwise
        """
        metrics = self.resource_monitor.get_resources()
        
        return (metrics.cpu_percent > self.cpu_threshold or
                metrics.memory_percent > self.memory_threshold)
    
    def with_degradation(self, func: Callable[..., T], fallback_func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to apply graceful degradation.
        
        Args:
            func: Function to execute
            fallback_func: Fallback function to execute if resources are constrained
            
        Returns:
            Decorated function
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if self.should_degrade():
                logger.warning(f"Resources constrained, degrading {func.__name__}")
                return fallback_func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return cast(Callable[..., T], wrapper)

class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum number of calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0
        self.lock = threading.Lock()
    
    def wait(self) -> None:
        """Wait until the next call is allowed."""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()
    
    def limit_rate(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to limit the rate of function calls.
        
        Args:
            func: Function to rate limit
            
        Returns:
            Rate-limited function
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self.wait()
            return func(*args, **kwargs)
        
        return cast(Callable[..., T], wrapper)

class HealthMonitor:
    """Monitor for service health."""
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(HealthMonitor, cls).__new__(cls)
            cls._instance.service_registry = ServiceRegistry()
            cls._instance.resource_monitor = ResourceMonitor()
            cls._instance.check_thread = None
            cls._instance.stop_event = threading.Event()
        
        return cls._instance
    
    def start_monitoring(self, check_interval: int = 60) -> None:
        """
        Start monitoring services.
        
        Args:
            check_interval: Interval in seconds between health checks
        """
        if self.check_thread is not None and self.check_thread.is_alive():
            logger.warning("Health monitoring already started")
            return
        
        self.stop_event.clear()
        self.check_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.check_thread.start()
        
        logger.info("Health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring services."""
        if self.check_thread is None or not self.check_thread.is_alive():
            logger.warning("Health monitoring not running")
            return
        
        self.stop_event.set()
        self.check_thread.join(timeout=5.0)
        
        logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self, check_interval: int) -> None:
        """
        Monitoring loop.
        
        Args:
            check_interval: Interval in seconds between health checks
        """
        while not self.stop_event.is_set():
            try:
                # Check all services
                all_health = self.service_registry.get_all_service_health()
                
                # Log unhealthy services
                for service_name, health_result in all_health.items():
                    if health_result.status == ServiceHealth.UNHEALTHY:
                        logger.warning(f"Service {service_name} is unhealthy: {health_result.details}")
                    elif health_result.status == ServiceHealth.DEGRADED:
                        logger.info(f"Service {service_name} is degraded: {health_result.details}")
                
                # Check system resources
                metrics = self.resource_monitor.check_resources()
                if metrics.cpu_percent > 80.0:
                    logger.warning(f"High CPU usage: {metrics.cpu_percent}%")
                if metrics.memory_percent > 80.0:
                    logger.warning(f"High memory usage: {metrics.memory_percent}%")
                if metrics.disk_percent > 90.0:
                    logger.warning(f"High disk usage: {metrics.disk_percent}%")
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {str(e)}")
            
            # Wait for next check
            self.stop_event.wait(check_interval)
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get the health of the system.
        
        Returns:
            System health information
        """
        all_health = self.service_registry.get_all_service_health()
        metrics = self.resource_monitor.get_resources()
        
        # Count services by status
        status_counts = {
            ServiceHealth.HEALTHY.value: 0,
            ServiceHealth.DEGRADED.value: 0,
            ServiceHealth.UNHEALTHY.value: 0
        }
        
        for health_result in all_health.values():
            status_counts[health_result.status.value] += 1
        
        # Determine overall status
        overall_status = ServiceHealth.HEALTHY
        if status_counts[ServiceHealth.UNHEALTHY.value] > 0:
            overall_status = ServiceHealth.UNHEALTHY
        elif status_counts[ServiceHealth.DEGRADED.value] > 0:
            overall_status = ServiceHealth.DEGRADED
        
        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "services": {
                "total": len(all_health),
                "healthy": status_counts[ServiceHealth.HEALTHY.value],
                "degraded": status_counts[ServiceHealth.DEGRADED.value],
                "unhealthy": status_counts[ServiceHealth.UNHEALTHY.value]
            },
            "resources": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_percent": metrics.disk_percent,
                "network_usage": metrics.network_usage
            }
        }

def get_health_monitor() -> HealthMonitor:
    """
    Get the health monitor instance.
    
    Returns:
        Health monitor instance
    """
    return HealthMonitor()

def get_rate_limiter(calls_per_second: float = 1.0) -> RateLimiter:
    """
    Get a rate limiter.
    
    Args:
        calls_per_second: Maximum number of calls per second
        
    Returns:
        Rate limiter instance
    """
    return RateLimiter(calls_per_second)

def with_resource_check(
    cpu_threshold: float = 80.0,
    memory_threshold: float = 80.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to check resource usage before executing a function.
    
    Args:
        cpu_threshold: CPU usage threshold percentage
        memory_threshold: Memory usage threshold percentage
        
    Returns:
        Decorator function
    """
    resource_monitor = ResourceMonitor()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            metrics = resource_monitor.get_resources()
            
            if metrics.cpu_percent > cpu_threshold:
                logger.warning(f"High CPU usage ({metrics.cpu_percent}%) before executing {func.__name__}")
            
            if metrics.memory_percent > memory_threshold:
                logger.warning(f"High memory usage ({metrics.memory_percent}%) before executing {func.__name__}")
            
            return func(*args, **kwargs)
        
        return cast(Callable[..., T], wrapper)
    
    return decorator

def with_rate_limit(calls_per_second: float = 1.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to rate limit a function.
    
    Args:
        calls_per_second: Maximum number of calls per second
        
    Returns:
        Decorator function
    """
    rate_limiter = RateLimiter(calls_per_second)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return rate_limiter.limit_rate(func)
    
    return decorator