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

"""Comprehensive configuration management system for the multi-agent video system."""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml
from pydantic import BaseModel, Field, validator, ValidationError
from dotenv import load_dotenv

from .error_handling import VideoSystemError, ConfigurationError
from .logging_config import get_logger


logger = get_logger("config_manager")


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class VideoQuality(str, Enum):
    """Video quality settings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class AudioFormat(str, Enum):
    """Audio format options."""
    WAV = "wav"
    MP3 = "mp3"
    AAC = "aac"
    FLAC = "flac"


class VideoFormat(str, Enum):
    """Video format options."""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    WEBM = "webm"


@dataclass
class APIKeyConfig:
    """Configuration for API keys and their validation."""
    name: str
    required: bool = True
    description: str = ""
    validation_pattern: Optional[str] = None
    rotation_days: int = 90


class GoogleCloudConfig(BaseModel):
    """Google Cloud configuration."""
    use_vertexai: bool = Field(default=True, description="Use Vertex AI instead of ML Dev")
    project_id: Optional[str] = Field(default=None, description="Google Cloud Project ID")
    location: str = Field(default="us-central1", description="Google Cloud Location")
    api_key: Optional[str] = Field(default=None, description="Google API Key for ML Dev")
    credentials_path: Optional[str] = Field(default=None, description="Path to service account credentials")
    staging_bucket: Optional[str] = Field(default=None, description="Staging bucket for deployment")
    agent_engine_id: Optional[str] = Field(default=None, description="Agent Engine ID")

    @validator('staging_bucket')
    def validate_staging_bucket(cls, v):
        if v and not v.startswith('gs://'):
            raise ValueError('Staging bucket must start with gs://')
        return v


class ExternalAPIConfig(BaseModel):
    """External API configuration."""
    serper_api_key: Optional[str] = Field(default=None, description="Serper API key for web search")
    pexels_api_key: Optional[str] = Field(default=None, description="Pexels API key")
    unsplash_access_key: Optional[str] = Field(default=None, description="Unsplash access key")
    pixabay_api_key: Optional[str] = Field(default=None, description="Pixabay API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    stability_api_key: Optional[str] = Field(default=None, description="Stability AI API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key for TTS")
    elevenlabs_api_key: Optional[str] = Field(default=None, description="ElevenLabs API key")


class DatabaseConfig(BaseModel):
    """Database configuration."""
    mongodb_connection_string: str = Field(
        default="mongodb://localhost:27017/video_system",
        description="MongoDB connection string"
    )
    session_timeout_minutes: int = Field(default=60, description="Session timeout in minutes")
    enable_session_encryption: bool = Field(default=True, description="Enable session encryption")
    session_secret_key: Optional[str] = Field(default=None, description="Secret key for session encryption")


class StorageConfig(BaseModel):
    """Storage configuration."""
    video_output_dir: Path = Field(default=Path("./output"), description="Video output directory")
    temp_dir: Path = Field(default=Path("./temp"), description="Temporary files directory")
    asset_cache_dir: Path = Field(default=Path("./cache/assets"), description="Asset cache directory")
    session_data_dir: Path = Field(default=Path("./data/sessions"), description="Session data directory")
    max_disk_usage_gb: int = Field(default=50, description="Maximum disk usage in GB")

    def create_directories(self):
        """Create all configured directories."""
        for dir_path in [self.video_output_dir, self.temp_dir, self.asset_cache_dir, self.session_data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    log_dir: Path = Field(default=Path("./logs"), description="Log directory")
    enable_structured_logging: bool = Field(default=True, description="Enable structured JSON logging")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    max_log_file_size_mb: int = Field(default=10, description="Maximum log file size in MB")
    max_log_files: int = Field(default=5, description="Maximum number of log files to keep")


class PerformanceConfig(BaseModel):
    """Performance and resource configuration."""
    max_concurrent_requests: int = Field(default=10, description="Maximum concurrent requests")
    request_timeout_seconds: int = Field(default=300, description="Request timeout in seconds")
    max_memory_usage_mb: int = Field(default=4096, description="Maximum memory usage in MB")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    default_requests_per_second: float = Field(default=10.0, description="Default requests per second")
    default_requests_per_minute: float = Field(default=600.0, description="Default requests per minute")
    default_requests_per_hour: float = Field(default=3600.0, description="Default requests per hour")


class VideoProcessingConfig(BaseModel):
    """Video processing configuration."""
    ffmpeg_path: Path = Field(default=Path("/usr/bin/ffmpeg"), description="Path to FFmpeg executable")
    ffmpeg_threads: int = Field(default=4, description="Number of FFmpeg threads")
    video_quality: VideoQuality = Field(default=VideoQuality.HIGH, description="Default video quality")
    default_video_format: VideoFormat = Field(default=VideoFormat.MP4, description="Default video format")
    default_video_resolution: str = Field(default="1920x1080", description="Default video resolution")
    default_video_fps: int = Field(default=30, description="Default video FPS")
    default_audio_format: AudioFormat = Field(default=AudioFormat.WAV, description="Default audio format")
    default_audio_sample_rate: int = Field(default=44100, description="Default audio sample rate")
    default_audio_bitrate: str = Field(default="128k", description="Default audio bitrate")

    @validator('default_video_resolution')
    def validate_resolution(cls, v):
        if 'x' not in v or len(v.split('x')) != 2:
            raise ValueError('Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)')
        try:
            width, height = map(int, v.split('x'))
            if width <= 0 or height <= 0:
                raise ValueError('Resolution dimensions must be positive')
        except ValueError:
            raise ValueError('Resolution dimensions must be valid integers')
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""
    enable_api_key_validation: bool = Field(default=True, description="Enable API key validation")
    enable_request_signing: bool = Field(default=False, description="Enable request signing")
    api_key_rotation_days: int = Field(default=90, description="API key rotation period in days")
    enable_circuit_breaker: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_timeout_seconds: int = Field(default=60, description="Circuit breaker timeout in seconds")


class MonitoringConfig(BaseModel):
    """Monitoring and health check configuration."""
    enable_health_checks: bool = Field(default=True, description="Enable health checks")
    health_check_interval_seconds: int = Field(default=30, description="Health check interval in seconds")
    enable_performance_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    enable_graceful_degradation: bool = Field(default=True, description="Enable graceful degradation")


class RetryConfig(BaseModel):
    """Retry configuration."""
    default_max_retries: int = Field(default=3, description="Default maximum retries")
    default_retry_delay_seconds: float = Field(default=1.0, description="Default retry delay in seconds")
    exponential_backoff_multiplier: float = Field(default=2.0, description="Exponential backoff multiplier")


class DevelopmentConfig(BaseModel):
    """Development and testing configuration."""
    environment: Environment = Field(default=Environment.PRODUCTION, description="Environment type")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    enable_mock_apis: bool = Field(default=False, description="Enable mock APIs for testing")
    test_data_dir: Path = Field(default=Path("./test_data"), description="Test data directory")
    enable_test_logging: bool = Field(default=False, description="Enable test logging")
    test_timeout_seconds: int = Field(default=60, description="Test timeout in seconds")


class VideoSystemConfig(BaseModel):
    """Complete video system configuration."""
    google_cloud: GoogleCloudConfig = Field(default_factory=GoogleCloudConfig)
    external_apis: ExternalAPIConfig = Field(default_factory=ExternalAPIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    video_processing: VideoProcessingConfig = Field(default_factory=VideoProcessingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True


class ConfigurationManager:
    """Centralized configuration management system."""

    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (JSON or YAML)
            env_file: Path to environment file (.env)
        """
        self.config_file = config_file
        self.env_file = env_file or ".env"
        self._config: Optional[VideoSystemConfig] = None
        self._api_key_configs = self._define_api_key_configs()
        
        # Load configuration
        self.load_configuration()
    
    def _define_api_key_configs(self) -> Dict[str, APIKeyConfig]:
        """Define API key configurations."""
        return {
            "SERPER_API_KEY": APIKeyConfig(
                name="SERPER_API_KEY",
                required=True,
                description="Required for web search functionality"
            ),
            "PEXELS_API_KEY": APIKeyConfig(
                name="PEXELS_API_KEY",
                required=False,
                description="Required for Pexels stock media search"
            ),
            "UNSPLASH_ACCESS_KEY": APIKeyConfig(
                name="UNSPLASH_ACCESS_KEY",
                required=False,
                description="Required for Unsplash stock photo search"
            ),
            "PIXABAY_API_KEY": APIKeyConfig(
                name="PIXABAY_API_KEY",
                required=False,
                description="Required for Pixabay media search"
            ),
            "OPENAI_API_KEY": APIKeyConfig(
                name="OPENAI_API_KEY",
                required=False,
                description="Required for DALL-E image generation"
            ),
            "STABILITY_API_KEY": APIKeyConfig(
                name="STABILITY_API_KEY",
                required=False,
                description="Required for Stable Diffusion image generation"
            ),
            "GEMINI_API_KEY": APIKeyConfig(
                name="GEMINI_API_KEY",
                required=True,
                description="Required for Gemini TTS and image generation"
            ),
            "ELEVENLABS_API_KEY": APIKeyConfig(
                name="ELEVENLABS_API_KEY",
                required=False,
                description="Optional for ElevenLabs TTS"
            ),
        }
    
    def load_configuration(self) -> VideoSystemConfig:
        """Load configuration from environment and files."""
        try:
            # Load environment variables
            if Path(self.env_file).exists():
                load_dotenv(self.env_file)
                logger.info(f"Loaded environment variables from {self.env_file}")
            
            # Load from configuration file if provided
            file_config = {}
            if self.config_file and Path(self.config_file).exists():
                file_config = self._load_config_file(self.config_file)
                logger.info(f"Loaded configuration from {self.config_file}")
            
            # Build configuration from environment variables
            env_config = self._build_config_from_env()
            
            # Merge configurations (file config takes precedence)
            merged_config = {**env_config, **file_config}
            
            # Create and validate configuration
            self._config = VideoSystemConfig(**merged_config)
            
            # Create necessary directories
            self._config.storage.create_directories()
            self._config.logging.log_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("Configuration loaded and validated successfully")
            return self._config
            
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def _load_config_file(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON or YAML file."""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to parse configuration file {config_file}: {str(e)}") from e
    
    def _build_config_from_env(self) -> Dict[str, Any]:
        """Build configuration dictionary from environment variables."""
        return {
            "google_cloud": {
                "use_vertexai": self._get_bool_env("GOOGLE_GENAI_USE_VERTEXAI", True),
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                "staging_bucket": os.getenv("STAGING_BUCKET"),
                "agent_engine_id": os.getenv("AGENT_ENGINE_ID"),
            },
            "external_apis": {
                "serper_api_key": os.getenv("SERPER_API_KEY"),
                "pexels_api_key": os.getenv("PEXELS_API_KEY"),
                "unsplash_access_key": os.getenv("UNSPLASH_ACCESS_KEY"),
                "pixabay_api_key": os.getenv("PIXABAY_API_KEY"),
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "stability_api_key": os.getenv("STABILITY_API_KEY"),
                "gemini_api_key": os.getenv("GEMINI_API_KEY"),
                "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            },
            "database": {
                "mongodb_connection_string": os.getenv("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017/video_system"),
                "session_timeout_minutes": self._get_int_env("SESSION_TIMEOUT_MINUTES", 60),
                "enable_session_encryption": self._get_bool_env("ENABLE_SESSION_ENCRYPTION", True),
                "session_secret_key": os.getenv("SESSION_SECRET_KEY"),
            },
            "storage": {
                "video_output_dir": Path(os.getenv("VIDEO_OUTPUT_DIR", "./output")),
                "temp_dir": Path(os.getenv("TEMP_DIR", "./temp")),
                "asset_cache_dir": Path(os.getenv("ASSET_CACHE_DIR", "./cache/assets")),
                "session_data_dir": Path(os.getenv("SESSION_DATA_DIR", "./data/sessions")),
                "max_disk_usage_gb": self._get_int_env("MAX_DISK_USAGE_GB", 50),
            },
            "logging": {
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "log_dir": Path(os.getenv("LOG_DIR", "./logs")),
                "enable_structured_logging": self._get_bool_env("ENABLE_STRUCTURED_LOGGING", True),
                "enable_audit_logging": self._get_bool_env("ENABLE_AUDIT_LOGGING", True),
            },
            "performance": {
                "max_concurrent_requests": self._get_int_env("MAX_CONCURRENT_REQUESTS", 10),
                "request_timeout_seconds": self._get_int_env("REQUEST_TIMEOUT_SECONDS", 300),
                "max_memory_usage_mb": self._get_int_env("MAX_MEMORY_USAGE_MB", 4096),
                "enable_rate_limiting": self._get_bool_env("ENABLE_RATE_LIMITING", True),
                "default_requests_per_second": self._get_float_env("DEFAULT_REQUESTS_PER_SECOND", 10.0),
                "default_requests_per_minute": self._get_float_env("DEFAULT_REQUESTS_PER_MINUTE", 600.0),
                "default_requests_per_hour": self._get_float_env("DEFAULT_REQUESTS_PER_HOUR", 3600.0),
            },
            "video_processing": {
                "ffmpeg_path": Path(os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")),
                "ffmpeg_threads": self._get_int_env("FFMPEG_THREADS", 4),
                "video_quality": os.getenv("VIDEO_QUALITY", "high"),
                "default_video_format": os.getenv("DEFAULT_VIDEO_FORMAT", "mp4"),
                "default_video_resolution": os.getenv("DEFAULT_VIDEO_RESOLUTION", "1920x1080"),
                "default_video_fps": self._get_int_env("DEFAULT_VIDEO_FPS", 30),
                "default_audio_format": os.getenv("DEFAULT_AUDIO_FORMAT", "wav"),
                "default_audio_sample_rate": self._get_int_env("DEFAULT_AUDIO_SAMPLE_RATE", 44100),
                "default_audio_bitrate": os.getenv("DEFAULT_AUDIO_BITRATE", "128k"),
            },
            "security": {
                "enable_api_key_validation": self._get_bool_env("ENABLE_API_KEY_VALIDATION", True),
                "enable_request_signing": self._get_bool_env("ENABLE_REQUEST_SIGNING", False),
                "api_key_rotation_days": self._get_int_env("API_KEY_ROTATION_DAYS", 90),
                "enable_circuit_breaker": self._get_bool_env("ENABLE_CIRCUIT_BREAKER", True),
                "circuit_breaker_failure_threshold": self._get_int_env("CIRCUIT_BREAKER_FAILURE_THRESHOLD", 5),
                "circuit_breaker_timeout_seconds": self._get_int_env("CIRCUIT_BREAKER_TIMEOUT_SECONDS", 60),
            },
            "monitoring": {
                "enable_health_checks": self._get_bool_env("ENABLE_HEALTH_CHECKS", True),
                "health_check_interval_seconds": self._get_int_env("HEALTH_CHECK_INTERVAL_SECONDS", 30),
                "enable_performance_monitoring": self._get_bool_env("ENABLE_PERFORMANCE_MONITORING", True),
                "enable_graceful_degradation": self._get_bool_env("ENABLE_GRACEFUL_DEGRADATION", True),
            },
            "retry": {
                "default_max_retries": self._get_int_env("DEFAULT_MAX_RETRIES", 3),
                "default_retry_delay_seconds": self._get_float_env("DEFAULT_RETRY_DELAY_SECONDS", 1.0),
                "exponential_backoff_multiplier": self._get_float_env("EXPONENTIAL_BACKOFF_MULTIPLIER", 2.0),
            },
            "development": {
                "environment": os.getenv("ENVIRONMENT", "production"),
                "debug_mode": self._get_bool_env("DEBUG_MODE", False),
                "enable_mock_apis": self._get_bool_env("ENABLE_MOCK_APIS", False),
                "test_data_dir": Path(os.getenv("TEST_DATA_DIR", "./test_data")),
                "enable_test_logging": self._get_bool_env("ENABLE_TEST_LOGGING", False),
                "test_timeout_seconds": self._get_int_env("TEST_TIMEOUT_SECONDS", 60),
            },
        }
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_int_env(self, key: str, default: int = 0) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def _get_float_env(self, key: str, default: float = 0.0) -> float:
        """Get float environment variable."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    @property
    def config(self) -> VideoSystemConfig:
        """Get the current configuration."""
        if self._config is None:
            self.load_configuration()
        return self._config
    
    def validate_configuration(self) -> List[str]:
        """Validate the current configuration and return any issues."""
        issues = []
        
        try:
            # Validate API keys
            api_issues = self._validate_api_keys()
            issues.extend(api_issues)
            
            # Validate paths and directories
            path_issues = self._validate_paths()
            issues.extend(path_issues)
            
            # Validate Google Cloud configuration
            gcp_issues = self._validate_google_cloud_config()
            issues.extend(gcp_issues)
            
            # Validate database configuration
            db_issues = self._validate_database_config()
            issues.extend(db_issues)
            
            # Validate video processing configuration
            video_issues = self._validate_video_processing_config()
            issues.extend(video_issues)
            
        except Exception as e:
            issues.append(f"Configuration validation error: {str(e)}")
        
        return issues
    
    def _validate_api_keys(self) -> List[str]:
        """Validate API key configuration."""
        issues = []
        
        for key_name, key_config in self._api_key_configs.items():
            env_value = os.getenv(key_name)
            
            if key_config.required and not env_value:
                issues.append(f"Required API key missing: {key_name} - {key_config.description}")
            elif env_value and key_config.validation_pattern:
                import re
                if not re.match(key_config.validation_pattern, env_value):
                    issues.append(f"Invalid format for API key: {key_name}")
        
        # Check that at least one stock media API is configured
        stock_apis = ["PEXELS_API_KEY", "UNSPLASH_ACCESS_KEY", "PIXABAY_API_KEY"]
        if not any(os.getenv(key) for key in stock_apis):
            issues.append("At least one stock media API key is required (Pexels, Unsplash, or Pixabay)")
        
        return issues
    
    def _validate_paths(self) -> List[str]:
        """Validate path configurations."""
        issues = []
        
        # Check FFmpeg path
        ffmpeg_path = self.config.video_processing.ffmpeg_path
        if not ffmpeg_path.exists():
            issues.append(f"FFmpeg not found at: {ffmpeg_path}")
        
        # Check if directories can be created
        try:
            self.config.storage.create_directories()
        except Exception as e:
            issues.append(f"Cannot create storage directories: {str(e)}")
        
        return issues
    
    def _validate_google_cloud_config(self) -> List[str]:
        """Validate Google Cloud configuration."""
        issues = []
        
        gcp_config = self.config.google_cloud
        
        if gcp_config.use_vertexai:
            if not gcp_config.project_id:
                issues.append("Google Cloud Project ID is required when using Vertex AI")
            
            if gcp_config.staging_bucket and not gcp_config.staging_bucket.startswith('gs://'):
                issues.append("Staging bucket must start with 'gs://'")
        else:
            if not gcp_config.api_key:
                issues.append("Google API Key is required when not using Vertex AI")
        
        return issues
    
    def _validate_database_config(self) -> List[str]:
        """Validate database configuration."""
        issues = []
        
        db_config = self.config.database
        
        # Basic MongoDB connection string validation
        if not db_config.mongodb_connection_string.startswith('mongodb://'):
            issues.append("MongoDB connection string must start with 'mongodb://'")
        
        return issues
    
    def _validate_video_processing_config(self) -> List[str]:
        """Validate video processing configuration."""
        issues = []
        
        video_config = self.config.video_processing
        
        # Validate resolution format
        try:
            width, height = map(int, video_config.default_video_resolution.split('x'))
            if width <= 0 or height <= 0:
                issues.append("Video resolution dimensions must be positive")
        except ValueError:
            issues.append("Invalid video resolution format (should be WIDTHxHEIGHT)")
        
        # Validate FPS
        if video_config.default_video_fps <= 0:
            issues.append("Video FPS must be positive")
        
        # Validate audio sample rate
        if video_config.default_audio_sample_rate <= 0:
            issues.append("Audio sample rate must be positive")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration (without sensitive data)."""
        config = self.config
        
        return {
            "environment": config.development.environment,
            "debug_mode": config.development.debug_mode,
            "google_cloud": {
                "use_vertexai": config.google_cloud.use_vertexai,
                "project_id": config.google_cloud.project_id,
                "location": config.google_cloud.location,
                "has_staging_bucket": bool(config.google_cloud.staging_bucket),
                "has_agent_engine_id": bool(config.google_cloud.agent_engine_id),
            },
            "api_keys_configured": {
                key: bool(getattr(config.external_apis, key.lower()))
                for key in self._api_key_configs.keys()
            },
            "storage": {
                "video_output_dir": str(config.storage.video_output_dir),
                "temp_dir": str(config.storage.temp_dir),
                "max_disk_usage_gb": config.storage.max_disk_usage_gb,
            },
            "performance": {
                "max_concurrent_requests": config.performance.max_concurrent_requests,
                "request_timeout_seconds": config.performance.request_timeout_seconds,
                "rate_limiting_enabled": config.performance.enable_rate_limiting,
            },
            "video_processing": {
                "ffmpeg_path": str(config.video_processing.ffmpeg_path),
                "video_quality": config.video_processing.video_quality,
                "default_resolution": config.video_processing.default_video_resolution,
                "default_fps": config.video_processing.default_video_fps,
            },
            "monitoring": {
                "health_checks_enabled": config.monitoring.enable_health_checks,
                "performance_monitoring_enabled": config.monitoring.enable_performance_monitoring,
                "graceful_degradation_enabled": config.monitoring.enable_graceful_degradation,
            },
        }
    
    def save_config_to_file(self, file_path: str, format: str = "yaml"):
        """Save current configuration to file."""
        config_dict = self.config.dict()
        
        # Remove sensitive information
        sensitive_keys = ["api_key", "secret_key", "connection_string"]
        config_dict = self._remove_sensitive_data(config_dict, sensitive_keys)
        
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'w') as f:
                if format.lower() == "yaml":
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                elif format.lower() == "json":
                    json.dump(config_dict, f, indent=2, default=str)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            error_msg = f"Failed to save configuration to {file_path}: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def _remove_sensitive_data(self, data: Any, sensitive_keys: List[str]) -> Any:
        """Recursively remove sensitive data from configuration."""
        if isinstance(data, dict):
            return {
                key: self._remove_sensitive_data(value, sensitive_keys)
                if not any(sensitive in key.lower() for sensitive in sensitive_keys)
                else "[REDACTED]"
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._remove_sensitive_data(item, sensitive_keys) for item in data]
        else:
            return data


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(config_file: Optional[str] = None, env_file: Optional[str] = None) -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_file, env_file)
    
    return _config_manager


def get_config() -> VideoSystemConfig:
    """Get the current system configuration."""
    return get_config_manager().config


def validate_system_configuration() -> List[str]:
    """Validate the current system configuration."""
    return get_config_manager().validate_configuration()


def initialize_configuration(config_file: Optional[str] = None, env_file: Optional[str] = None) -> VideoSystemConfig:
    """Initialize and validate system configuration."""
    global _config_manager
    
    _config_manager = ConfigurationManager(config_file, env_file)
    
    # Validate configuration
    issues = _config_manager.validate_configuration()
    
    if issues:
        logger.warning("Configuration validation issues found:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    logger.info("System configuration initialized successfully")
    return _config_manager.config