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

from .session_manager import (
    SessionManager,
    SessionData,
    ProjectState,
    SessionStage,
    get_session_manager,
    initialize_session_manager,
)

from .progress_monitor import (
    ProgressMonitor,
    StageProgress,
    get_progress_monitor,
    initialize_progress_monitor,
    start_monitoring,
    update_progress,
    advance_stage,
    complete_monitoring,
    get_progress,
)

from .maintenance import (
    MaintenanceManager,
    CleanupStats,
    SystemHealth,
    get_maintenance_manager,
    initialize_maintenance_manager,
    run_maintenance,
    get_system_health,
    cleanup_session,
    start_auto_maintenance,
    stop_auto_maintenance,
)

from .concurrent_processor import (
    ConcurrentProcessor,
    RequestPriority,
    ProcessorStatus,
    QueuedRequest,
    ProcessingTask,
    ResourceLimits,
    ProcessorMetrics,
    get_concurrent_processor,
    initialize_concurrent_processor,
)

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
    'VideoGenerationRequest',
    'VideoScene',
    'VideoScript',
    'AssetItem',
    'VideoGenerationStatus',
    'VideoStatus',
    'AssetType',
    'VideoQuality',
    'VideoStyle',
    'ResearchRequest',
    'ResearchData',
    'ScriptRequest',
    'AssetRequest',
    'AssetCollection',
    'AudioRequest',
    'AudioAssets',
    'AssemblyRequest',
    'FinalVideo',
    
    # Error Handling
    'VideoSystemError',
    'APIError',
    'NetworkError',
    'ValidationError',
    'ProcessingError',
    'ResourceError',
    'RateLimitError',
    'TimeoutError',
    'RetryConfig',
    'FallbackConfig',
    'retry_with_exponential_backoff',
    'async_retry_with_exponential_backoff',
    'FallbackManager',
    'CircuitBreaker',
    'handle_api_errors',
    'create_error_response',
    'get_logger',
    'log_error',
    
    # Resilience
    'ServiceHealth',
    'HealthCheckResult',
    'ResourceMetrics',
    'ServiceRegistry',
    'ResourceMonitor',
    'GracefulDegradation',
    'RateLimiter',
    'HealthMonitor',
    'get_health_monitor',
    'get_rate_limiter',
    'with_resource_check',
    'with_rate_limit',
    
    # Logging
    'initialize_logging',
    'get_performance_logger',
    'get_audit_logger',
    'log_system_startup',
    'log_system_shutdown',
    'LoggedOperation',
    
    # Configuration Management
    'ConfigurationManager',
    'VideoSystemConfig',
    'GoogleCloudConfig',
    'ExternalAPIConfig',
    'DatabaseConfig',
    'StorageConfig',
    'LoggingConfig',
    'PerformanceConfig',
    'VideoProcessingConfig',
    'SecurityConfig',
    'MonitoringConfig',
    'RetryConfig',
    'DevelopmentConfig',
    'Environment',
    'LogLevel',
    'VideoQuality',
    'AudioFormat',
    'VideoFormat',
    'get_config_manager',
    'get_config',
    'validate_system_configuration',
    'initialize_configuration',
    
    # Session Management
    'SessionManager',
    'SessionData',
    'ProjectState',
    'SessionStage',
    'get_session_manager',
    'initialize_session_manager',
    
    # Progress Monitoring
    'ProgressMonitor',
    'StageProgress',
    'get_progress_monitor',
    'initialize_progress_monitor',
    'start_monitoring',
    'update_progress',
    'advance_stage',
    'complete_monitoring',
    'get_progress',
    
    # Maintenance
    'MaintenanceManager',
    'CleanupStats',
    'SystemHealth',
    'get_maintenance_manager',
    'initialize_maintenance_manager',
    'run_maintenance',
    'get_system_health',
    'cleanup_session',
    'start_auto_maintenance',
    'stop_auto_maintenance',
    
    # Concurrent Processing
    'ConcurrentProcessor',
    'RequestPriority',
    'ProcessorStatus',
    'QueuedRequest',
    'ProcessingTask',
    'ResourceLimits',
    'ProcessorMetrics',
    'get_concurrent_processor',
    'initialize_concurrent_processor',
    
    # Resource Management
    'ResourceManager',
    'ResourceType',
    'AlertLevel',
    'ResourceThresholds',
    'ResourceUsage',
    'ResourceAlert',
    'ResourceAllocation',
    'get_resource_manager',
    'initialize_resource_manager',
    
    # Rate Limiting
    'RateLimitStrategy',
    'ThrottleAction',
    'RateLimitConfig',
    'ServiceLimits',
    'RequestRecord',
    'RateLimitStatus',
    'get_new_rate_limiter',
    'initialize_rate_limiter',
    
    # Load Testing
    'LoadTester',
    'LoadTestType',
    'TestPhase',
    'LoadTestConfig',
    'RequestResult',
    'UserMetrics',
    'LoadTestMetrics',
    'get_load_tester',
]