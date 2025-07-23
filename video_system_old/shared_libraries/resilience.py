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

"""Resilience utilities for the multi-agent video system.

This module provides additional resilience patterns including health checks,
resource monitoring, and service degradation strategies.
"""

import psutil
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import json

from .error_handling import ProcessingError, ResourceError, get_logger


class ServiceHealth(str, Enum):
    """Service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ResourceType(str, Enum):
    """Resource types for monitoring."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"


class HealthCheckResult(BaseModel):
    """Result of a health check."""

    service_name: str
    status: ServiceHealth
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ResourceMetrics(BaseModel):
    """System resource metrics."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    available_memory_gb: float
    timestamp: datetime


class ServiceRegistry:
    """Registry for tracking service health and availability."""

    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger or get_logger("service_registry")
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_checks: Dict[str, HealthCheckResult] = {}
        self._lock = threading.Lock()

    def register_service(
        self,
        service_name: str,
        health_check_func: Optional[Callable] = None,
        health_check_interval: int = 60,
        critical: bool = False,
    ):
        """Register a service for monitoring."""
        with self._lock:
            self.services[service_name] = {
                "health_check_func": health_check_func,
                "health_check_interval": health_check_interval,
                "critical": critical,
                "last_check": None,
                "consecutive_failures": 0,
            }

        self.logger.info(f"Registered service: {service_name}")

    def get_service_health(self, service_name: str) -> Optional[HealthCheckResult]:
        """Get the latest health check result for a service."""
        return self.health_checks.get(service_name)

    def get_all_service_health(self) -> Dict[str, HealthCheckResult]:
        """Get health status for all registered services."""
        return self.health_checks.copy()

    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        health = self.get_service_health(service_name)
        return health is not None and health.status == ServiceHealth.HEALTHY

    def perform_health_check(self, service_name: str) -> HealthCheckResult:
        """Perform health check for a specific service."""
        if service_name not in self.services:
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceHealth.UNKNOWN,
                timestamp=datetime.utcnow(),
                response_time_ms=0,
                error_message="Service not registered",
            )

        service_info = self.services[service_name]
        health_check_func = service_info["health_check_func"]

        if not health_check_func:
            # Default health check - just mark as healthy if registered
            result = HealthCheckResult(
                service_name=service_name,
                status=ServiceHealth.HEALTHY,
                timestamp=datetime.utcnow(),
                response_time_ms=0,
                details={"type": "default_check"},
            )
        else:
            start_time = time.time()
            try:
                check_result = health_check_func()
                response_time = (time.time() - start_time) * 1000

                if isinstance(check_result, bool):
                    status = (
                        ServiceHealth.HEALTHY
                        if check_result
                        else ServiceHealth.UNHEALTHY
                    )
                    details = {}
                elif isinstance(check_result, dict):
                    status = ServiceHealth(
                        check_result.get("status", ServiceHealth.HEALTHY)
                    )
                    details = check_result.get("details", {})
                else:
                    status = ServiceHealth.HEALTHY
                    details = {"result": str(check_result)}

                result = HealthCheckResult(
                    service_name=service_name,
                    status=status,
                    timestamp=datetime.utcnow(),
                    response_time_ms=response_time,
                    details=details,
                )

                # Reset consecutive failures on success
                service_info["consecutive_failures"] = 0

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                service_info["consecutive_failures"] += 1

                result = HealthCheckResult(
                    service_name=service_name,
                    status=ServiceHealth.UNHEALTHY,
                    timestamp=datetime.utcnow(),
                    response_time_ms=response_time,
                    error_message=str(e),
                    details={
                        "consecutive_failures": service_info["consecutive_failures"]
                    },
                )

                self.logger.error(f"Health check failed for {service_name}: {str(e)}")

        # Update the registry
        with self._lock:
            self.health_checks[service_name] = result
            service_info["last_check"] = datetime.utcnow()

        return result


class ResourceMonitor:
    """Monitor system resources and detect resource constraints."""

    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger or get_logger("resource_monitor")
        self.thresholds = {
            "cpu_warning": 80.0,
            "cpu_critical": 95.0,
            "memory_warning": 80.0,
            "memory_critical": 95.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0,
        }

    def get_current_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                available_memory_gb=memory.available / (1024**3),
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            self.logger.error(f"Failed to get resource metrics: {str(e)}")
            raise ResourceError(
                f"Failed to get resource metrics: {str(e)}", original_exception=e
            )

    def check_resource_constraints(self) -> Dict[str, Any]:
        """Check for resource constraints and return warnings/alerts."""
        metrics = self.get_current_metrics()
        alerts = []
        warnings = []

        # Check CPU
        if metrics.cpu_percent >= self.thresholds["cpu_critical"]:
            alerts.append(f"Critical CPU usage: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent >= self.thresholds["cpu_warning"]:
            warnings.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        # Check Memory
        if metrics.memory_percent >= self.thresholds["memory_critical"]:
            alerts.append(f"Critical memory usage: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent >= self.thresholds["memory_warning"]:
            warnings.append(f"High memory usage: {metrics.memory_percent:.1f}%")

        # Check Disk
        if metrics.disk_percent >= self.thresholds["disk_critical"]:
            alerts.append(f"Critical disk usage: {metrics.disk_percent:.1f}%")
        elif metrics.disk_percent >= self.thresholds["disk_warning"]:
            warnings.append(f"High disk usage: {metrics.disk_percent:.1f}%")

        return {
            "metrics": metrics.model_dump(),
            "alerts": alerts,
            "warnings": warnings,
            "healthy": len(alerts) == 0,
        }

    def should_throttle_requests(self) -> bool:
        """Determine if requests should be throttled due to resource constraints."""
        try:
            metrics = self.get_current_metrics()
            return (
                metrics.cpu_percent >= self.thresholds["cpu_warning"]
                or metrics.memory_percent >= self.thresholds["memory_warning"]
            )
        except Exception:
            # If we can't get metrics, err on the side of caution
            return True


class GracefulDegradation:
    """Implement graceful degradation strategies."""

    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger or get_logger("graceful_degradation")
        self.degradation_levels = {
            "normal": 0,
            "reduced_quality": 1,
            "essential_only": 2,
            "emergency": 3,
        }
        self.current_level = 0

    def set_degradation_level(self, level: Union[str, int]):
        """Set the current degradation level."""
        if isinstance(level, str):
            level = self.degradation_levels.get(level, 0)

        self.current_level = level
        self.logger.info(f"Degradation level set to: {level}")

    def should_skip_non_essential(self) -> bool:
        """Check if non-essential operations should be skipped."""
        return self.current_level >= self.degradation_levels["essential_only"]

    def should_reduce_quality(self) -> bool:
        """Check if quality should be reduced."""
        return self.current_level >= self.degradation_levels["reduced_quality"]

    def get_quality_settings(self) -> Dict[str, Any]:
        """Get quality settings based on current degradation level."""
        if self.current_level >= self.degradation_levels["emergency"]:
            return {
                "video_quality": "low",
                "audio_quality": "low",
                "max_duration": 30,
                "skip_effects": True,
                "skip_transitions": True,
            }
        elif self.current_level >= self.degradation_levels["essential_only"]:
            return {
                "video_quality": "medium",
                "audio_quality": "medium",
                "max_duration": 60,
                "skip_effects": True,
                "skip_transitions": False,
            }
        elif self.current_level >= self.degradation_levels["reduced_quality"]:
            return {
                "video_quality": "medium",
                "audio_quality": "high",
                "max_duration": 120,
                "skip_effects": False,
                "skip_transitions": False,
            }
        else:
            return {
                "video_quality": "high",
                "audio_quality": "high",
                "max_duration": 300,
                "skip_effects": False,
                "skip_transitions": False,
            }


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        max_tokens: int = 100,
        refill_rate: float = 10.0,
        logger: Optional[Any] = None,
    ):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
        self.logger = logger or get_logger("rate_limiter")
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket."""
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                self.logger.warning(
                    f"Rate limit exceeded. Requested: {tokens}, Available: {self.tokens}"
                )
                return False

    def _refill(self):
        """Refill the token bucket."""
        now = time.time()
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.refill_rate

        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now


class HealthMonitor:
    """Comprehensive health monitoring system."""

    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger or get_logger("health_monitor")
        self.service_registry = ServiceRegistry(logger)
        self.resource_monitor = ResourceMonitor(logger)
        self.degradation = GracefulDegradation(logger)
        self.monitoring_active = False
        self.monitoring_thread = None

    def start_monitoring(self, check_interval: int = 30):
        """Start the health monitoring background thread."""
        if self.monitoring_active:
            self.logger.warning("Health monitoring is already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(check_interval,), daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Health monitoring stopped")

    def _monitoring_loop(self, check_interval: int):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Check system resources
                resource_status = self.resource_monitor.check_resource_constraints()

                # Adjust degradation level based on resource status
                if resource_status["alerts"]:
                    self.degradation.set_degradation_level("emergency")
                elif resource_status["warnings"]:
                    self.degradation.set_degradation_level("reduced_quality")
                else:
                    self.degradation.set_degradation_level("normal")

                # Check all registered services
                for service_name in self.service_registry.services:
                    self.service_registry.perform_health_check(service_name)

                # Log overall system health
                self._log_system_health(resource_status)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")

            time.sleep(check_interval)

    def _log_system_health(self, resource_status: Dict[str, Any]):
        """Log overall system health status."""
        service_health = self.service_registry.get_all_service_health()
        healthy_services = sum(
            1 for h in service_health.values() if h.status == ServiceHealth.HEALTHY
        )
        total_services = len(service_health)

        health_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "resource_status": resource_status,
            "services": {
                "healthy": healthy_services,
                "total": total_services,
                "health_percentage": (healthy_services / total_services * 100)
                if total_services > 0
                else 100,
            },
            "degradation_level": self.degradation.current_level,
        }

        self.logger.info(
            f"System health summary: {json.dumps(health_summary, indent=2, default=str)}"
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            resource_status = self.resource_monitor.check_resource_constraints()
            service_health = self.service_registry.get_all_service_health()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_healthy": resource_status["healthy"]
                and all(
                    h.status == ServiceHealth.HEALTHY for h in service_health.values()
                ),
                "resource_status": resource_status,
                "service_health": {
                    name: h.model_dump() for name, h in service_health.items()
                },
                "degradation_level": self.degradation.current_level,
                "quality_settings": self.degradation.get_quality_settings(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get system status: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_healthy": False,
                "error": str(e),
            }


# Global instances for easy access
_health_monitor = None
_rate_limiter = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def with_resource_check(func: Callable) -> Callable:
    """Decorator to check resources before executing function."""

    def wrapper(*args, **kwargs):
        monitor = get_health_monitor()
        if monitor.resource_monitor.should_throttle_requests():
            raise ResourceError("System resources are constrained, request throttled")
        return func(*args, **kwargs)

    return wrapper


def with_rate_limit(tokens: int = 1):
    """Decorator to apply rate limiting to function calls."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            if not limiter.acquire(tokens):
                raise ProcessingError("Rate limit exceeded, please try again later")
            return func(*args, **kwargs)

        return wrapper

    return decorator
