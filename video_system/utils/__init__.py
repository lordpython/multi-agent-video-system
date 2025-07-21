# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utilities package for the video system.

This package contains shared utilities, configuration management, and models.
"""

# Import error handling utilities
from .error_handling import (
    get_logger,
    log_error,
    handle_api_errors,
    create_error_response,
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
    CircuitBreaker
)

# Import resilience utilities
from .resilience import (
    ServiceHealth,
    HealthCheckResult,
    ResourceMetrics,
    ServiceRegistry,
    ResourceMonitor,
    GracefulDegradation,
    RateLimiter as ResilienceRateLimiter,
    HealthMonitor,
    get_health_monitor,
    get_rate_limiter as get_resilience_rate_limiter,
    with_resource_check,
    with_rate_limit
)

# Import configuration management
from .config_manager import (
    ConfigurationManager,
    get_config_manager,
    get_video_system_config,
    validate_system_configuration,
    get_system_config_summary
)

# Import logging configuration
from .logging_config import (
    get_logger as get_system_logger,
    get_performance_logger,
    get_audit_logger,
    initialize_logging,
    log_system_startup,
    log_system_shutdown,
    LoggedOperation
)

# Import data models
from .models import (
    VideoGenerationRequest,
    VideoScript,
    VideoScene,
    AssetItem,
    AssetCollection,
    VideoGenerationStatus,
    ResearchData,
    AudioAssets,
    FinalVideo,
    VideoStatus,
    VideoQuality,
    VideoStyle,
    AssetType
)

# Import resource management
from .resource_manager import (
    ResourceManager,
    ResourceThresholds,
    ResourceUsage,
    ResourceAlert,
    get_resource_manager,
    initialize_resource_manager
)

# Import rate limiting
from .rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    ServiceLimits,
    get_rate_limiter,
    initialize_rate_limiter
)

# Import concurrent processing
from .concurrent_processor import (
    ConcurrentProcessor,
    RequestPriority,
    get_concurrent_processor
)

# Import load testing
from .load_tester import (
    LoadTester,
    LoadTestConfig,
    LoadTestType,
    get_load_tester
)

__all__ = [
    # Error handling
    "get_logger",
    "log_error",
    "handle_api_errors",
    "create_error_response",
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
    
    # Resilience
    "ServiceHealth",
    "HealthCheckResult",
    "ResourceMetrics",
    "ServiceRegistry",
    "ResourceMonitor",
    "GracefulDegradation",
    "ResilienceRateLimiter",
    "HealthMonitor",
    "get_health_monitor",
    "get_resilience_rate_limiter",
    "with_resource_check",
    "with_rate_limit",
    
    # Configuration management
    "ConfigurationManager",
    "get_config_manager", 
    "get_video_system_config",
    "validate_system_configuration",
    "get_system_config_summary",
    
    # Logging
    "get_system_logger",
    "get_performance_logger",
    "get_audit_logger",
    "initialize_logging",
    "log_system_startup",
    "log_system_shutdown",
    "LoggedOperation",
    
    # Data models
    "VideoGenerationRequest",
    "VideoScript",
    "VideoScene",
    "AssetItem",
    "AssetCollection",
    "VideoGenerationStatus",
    "ResearchData",
    "AudioAssets",
    "FinalVideo",
    "VideoStatus",
    "VideoQuality",
    "VideoStyle",
    "AssetType",
    
    # Resource management
    "ResourceManager",
    "ResourceThresholds",
    "ResourceUsage",
    "ResourceAlert",
    "get_resource_manager",
    "initialize_resource_manager",
    
    # Rate limiting
    "RateLimiter",
    "RateLimitConfig",
    "ServiceLimits",
    "get_rate_limiter",
    "initialize_rate_limiter",
]

# Import concurrent processing
from .concurrent_processor import (
    ConcurrentProcessor,
    get_concurrent_processor,
    initialize_concurrent_processor
)

# Import load testing
from .load_tester import (
    LoadTester,
    LoadTestConfig,
    get_load_tester
)

__all__.extend([
    # Concurrent processing
    "ConcurrentProcessor",
    "get_concurrent_processor", 
    "initialize_concurrent_processor",
    
    # Load testing
    "LoadTester",
    "LoadTestConfig",
    "get_load_tester",
])