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

"""Shared libraries and utilities for the video system."""

from .models import (
    VideoGenerationRequest,
    VideoScene,
    VideoScript,
    AssetItem,
    VideoGenerationStatus,
    VideoStatus,
    AssetType,
    VideoQuality,
    VideoStyle,
    ResearchRequest,
    ResearchData,
    ScriptRequest,
    AssetRequest,
    AssetCollection,
    AudioRequest,
    AudioAssets,
    AssemblyRequest,
    FinalVideo,
)

from .error_handling import (
    VideoSystemError,
    APIError,
    NetworkError,
    ValidationError,
    ProcessingError,
    ResourceError,
    RateLimitError,
    TimeoutError,
    RetryConfig,
    FallbackConfig,
    retry_with_exponential_backoff,
    async_retry_with_exponential_backoff,
    FallbackManager,
    CircuitBreaker,
    handle_api_errors,
    create_error_response,
    get_logger,
    log_error,
)

from .resilience import (
    ServiceHealth,
    HealthCheckResult,
    ResourceMetrics,
    ServiceRegistry,
    ResourceMonitor,
    GracefulDegradation,
    RateLimiter,
    HealthMonitor,
    get_health_monitor,
    get_rate_limiter,
    with_resource_check,
    with_rate_limit,
)

from .logging_config import (
    initialize_logging,
    get_performance_logger,
    get_audit_logger,
    log_system_startup,
    log_system_shutdown,
    LoggedOperation,
)

from .config_manager import (
    ConfigurationManager,
    VideoSystemConfig,
    GoogleCloudConfig,
    ExternalAPIConfig,
    DatabaseConfig,
    StorageConfig,
    LoggingConfig,
    PerformanceConfig,
    VideoProcessingConfig,
    SecurityConfig,
    MonitoringConfig,
    RetryConfig,
    DevelopmentConfig,
    Environment,
    LogLevel,
    VideoQuality,
    AudioFormat,
    VideoFormat,
    get_config_manager,
    get_config,
    validate_system_configuration,
    initialize_configuration,
)

# Removed imports of deleted custom session management modules:
# - adk_session_manager (deleted)
# - adk_session_models (deleted)
# - progress_monitor (deleted)
# - maintenance (deleted)

# Removed concurrent_processor import - incompatible with simplified system
# from .concurrent_processor import ...

from .resource_manager import (
    ResourceManager,
    ResourceType,
    AlertLevel,
    ResourceThresholds,
    ResourceUsage,
    ResourceAlert,
    ResourceAllocation,
    get_resource_manager,
    initialize_resource_manager,
)

from .rate_limiter import (
    RateLimitStrategy,
    ThrottleAction,
    RateLimitConfig,
    ServiceLimits,
    RequestRecord,
    RateLimitStatus,
    get_rate_limiter as get_new_rate_limiter,
    initialize_rate_limiter,
)

from .load_tester import (
    LoadTester,
    LoadTestType,
    TestPhase,
    LoadTestConfig,
    RequestResult,
    UserMetrics,
    LoadTestMetrics,
    get_load_tester,
)

__all__ = [
    # Models
    "VideoGenerationRequest",
    "VideoScene",
    "VideoScript",
    "AssetItem",
    "VideoGenerationStatus",
    "VideoStatus",
    "AssetType",
    "VideoQuality",
    "VideoStyle",
    "ResearchRequest",
    "ResearchData",
    "ScriptRequest",
    "AssetRequest",
    "AssetCollection",
    "AudioRequest",
    "AudioAssets",
    "AssemblyRequest",
    "FinalVideo",
    # Error Handling
    "VideoSystemError",
    "APIError",
    "NetworkError",
    "ValidationError",
    "ProcessingError",
    "ResourceError",
    "RateLimitError",
    "TimeoutError",
    "RetryConfig",
    "FallbackConfig",
    "retry_with_exponential_backoff",
    "async_retry_with_exponential_backoff",
    "FallbackManager",
    "CircuitBreaker",
    "handle_api_errors",
    "create_error_response",
    "get_logger",
    "log_error",
    # Resilience
    "ServiceHealth",
    "HealthCheckResult",
    "ResourceMetrics",
    "ServiceRegistry",
    "ResourceMonitor",
    "GracefulDegradation",
    "RateLimiter",
    "HealthMonitor",
    "get_health_monitor",
    "get_rate_limiter",
    "with_resource_check",
    "with_rate_limit",
    # Logging
    "initialize_logging",
    "get_performance_logger",
    "get_audit_logger",
    "log_system_startup",
    "log_system_shutdown",
    "LoggedOperation",
    # Configuration Management
    "ConfigurationManager",
    "VideoSystemConfig",
    "GoogleCloudConfig",
    "ExternalAPIConfig",
    "DatabaseConfig",
    "StorageConfig",
    "LoggingConfig",
    "PerformanceConfig",
    "VideoProcessingConfig",
    "SecurityConfig",
    "MonitoringConfig",
    "RetryConfig",
    "DevelopmentConfig",
    "Environment",
    "LogLevel",
    "VideoQuality",
    "AudioFormat",
    "VideoFormat",
    "get_config_manager",
    "get_config",
    "validate_system_configuration",
    "initialize_configuration",
    # Removed exports for deleted modules:
    # - Session Management (adk_session_manager deleted)
    # - Progress Monitoring (progress_monitor deleted)
    # - Maintenance (maintenance deleted)
    # Removed concurrent processing exports - incompatible with simplified system
    # Resource Management
    "ResourceManager",
    "ResourceType",
    "AlertLevel",
    "ResourceThresholds",
    "ResourceUsage",
    "ResourceAlert",
    "ResourceAllocation",
    "get_resource_manager",
    "initialize_resource_manager",
    # Rate Limiting
    "RateLimitStrategy",
    "ThrottleAction",
    "RateLimitConfig",
    "ServiceLimits",
    "RequestRecord",
    "RateLimitStatus",
    "get_new_rate_limiter",
    "initialize_rate_limiter",
    # Load Testing
    "LoadTester",
    "LoadTestType",
    "TestPhase",
    "LoadTestConfig",
    "RequestResult",
    "UserMetrics",
    "LoadTestMetrics",
    "get_load_tester",
]
