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

"""Comprehensive logging configuration following ADK patterns for the multi-agent video system."""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str)


class VideoSystemLogger:
    """Centralized logging configuration for the video system."""

    def __init__(self, log_level: str = "INFO", log_dir: Optional[str] = None):
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Configure root logger
        self._configure_root_logger()

        # Configure component-specific loggers
        self._configure_component_loggers()

    def _configure_root_logger(self):
        """Configure the root logger for the video system."""
        root_logger = logging.getLogger("video_system")
        root_logger.setLevel(self.log_level)

        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler with structured output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = StructuredFormatter()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler for all logs
        all_logs_file = self.log_dir / "video_system.log"
        file_handler = logging.handlers.RotatingFileHandler(
            all_logs_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

        # Error-only file handler
        error_logs_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_logs_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)

    def _configure_component_loggers(self):
        """Configure loggers for specific components."""
        components = [
            "video_system.root_orchestrator",
            "video_system.research_agent",
            "video_system.story_agent",
            "video_system.asset_sourcing_agent",
            "video_system.audio_agent",
            "video_system.video_assembly_agent",
            "video_system.research.web_search",
            "video_system.story.script_generator",
            "video_system.asset_sourcing.pexels",
            "video_system.audio.gemini_tts",
            "video_system.video_assembly.ffmpeg_composition",
            "video_system.health_monitor",
            "video_system.resource_monitor",
            "video_system.error_handling",
            "video_system.resilience",
        ]

        for component in components:
            logger = logging.getLogger(component)
            logger.setLevel(self.log_level)

            # Component-specific file handler
            component_name = component.split(".")[-1]
            component_file = self.log_dir / f"{component_name}.log"

            component_handler = logging.handlers.RotatingFileHandler(
                component_file,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
            )
            component_handler.setLevel(logging.DEBUG)
            component_handler.setFormatter(StructuredFormatter())
            logger.addHandler(component_handler)

            # Prevent propagation to avoid duplicate logs
            logger.propagate = False

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific component."""
        full_name = (
            f"video_system.{name}" if not name.startswith("video_system") else name
        )
        return logging.getLogger(full_name)


class PerformanceLogger:
    """Logger for performance metrics and timing information."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_operation_start(self, operation: str, **kwargs):
        """Log the start of an operation."""
        self.logger.info(
            f"Operation started: {operation}",
            extra={
                "operation": operation,
                "operation_phase": "start",
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

    def log_operation_end(
        self, operation: str, duration: float, success: bool = True, **kwargs
    ):
        """Log the end of an operation with timing information."""
        self.logger.info(
            f"Operation {'completed' if success else 'failed'}: {operation} ({duration:.3f}s)",
            extra={
                "operation": operation,
                "operation_phase": "end",
                "duration_seconds": duration,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

    def log_performance_metric(
        self, metric_name: str, value: float, unit: str = "", **kwargs
    ):
        """Log a performance metric."""
        self.logger.info(
            f"Performance metric: {metric_name} = {value}{unit}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "metric_type": "performance",
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            },
        )


class AuditLogger:
    """Logger for audit trail and security events."""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Configure audit logger
        self.logger = logging.getLogger("video_system.audit")
        self.logger.setLevel(logging.INFO)

        # Audit log file handler
        audit_file = self.log_dir / "audit.log"
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,  # Keep more audit logs
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(audit_handler)
        self.logger.propagate = False

    def log_user_action(self, action: str, user_id: str = "unknown", **kwargs):
        """Log a user action for audit purposes."""
        self.logger.info(
            f"User action: {action}",
            extra={
                "event_type": "user_action",
                "action": action,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

    def log_system_event(self, event: str, severity: str = "info", **kwargs):
        """Log a system event for audit purposes."""
        log_level = getattr(logging, severity.upper(), logging.INFO)
        self.logger.log(
            log_level,
            f"System event: {event}",
            extra={
                "event_type": "system_event",
                "event": event,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            },
        )

    def log_security_event(self, event: str, risk_level: str = "low", **kwargs):
        """Log a security-related event."""
        log_level = (
            logging.WARNING if risk_level in ["medium", "high"] else logging.INFO
        )
        self.logger.log(
            log_level,
            f"Security event: {event}",
            extra={
                "event_type": "security_event",
                "event": event,
                "risk_level": risk_level,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            },
        )


# Global logging configuration
_video_system_logger = None
_performance_logger = None
_audit_logger = None


def initialize_logging(log_level: str = "INFO", log_dir: Optional[str] = None):
    """Initialize the logging system for the video system."""
    global _video_system_logger, _performance_logger, _audit_logger

    # Get log level from environment if not specified
    if not log_level:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # Get log directory from environment if not specified
    if not log_dir:
        log_dir = os.getenv("LOG_DIR", "logs")

    _video_system_logger = VideoSystemLogger(log_level, log_dir)
    _performance_logger = PerformanceLogger(
        _video_system_logger.get_logger("performance")
    )
    _audit_logger = AuditLogger(log_dir)

    # Log initialization
    logger = _video_system_logger.get_logger("logging_config")
    logger.info(
        f"Logging system initialized with level: {log_level}, directory: {log_dir}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component."""
    global _video_system_logger

    if _video_system_logger is None:
        initialize_logging()

    return _video_system_logger.get_logger(name)


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger."""
    global _performance_logger

    if _performance_logger is None:
        initialize_logging()

    return _performance_logger


def get_audit_logger() -> AuditLogger:
    """Get the audit logger."""
    global _audit_logger

    if _audit_logger is None:
        initialize_logging()

    return _audit_logger


def log_system_startup():
    """Log system startup information."""
    logger = get_logger("system")
    audit_logger = get_audit_logger()

    startup_info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "working_directory": os.getcwd(),
        "environment_variables": {
            key: value
            for key, value in os.environ.items()
            if not key.endswith("_KEY")
            and not key.endswith("_SECRET")  # Don't log secrets
        },
    }

    logger.info("Video system starting up", extra=startup_info)
    audit_logger.log_system_event("system_startup", severity="info", **startup_info)


def log_system_shutdown():
    """Log system shutdown information."""
    logger = get_logger("system")
    audit_logger = get_audit_logger()

    logger.info("Video system shutting down")
    audit_logger.log_system_event("system_shutdown", severity="info")


# Context manager for operation timing
class LoggedOperation:
    """Context manager for logging operation timing and success/failure."""

    def __init__(
        self, operation_name: str, logger: Optional[logging.Logger] = None, **kwargs
    ):
        self.operation_name = operation_name
        self.logger = logger or get_logger("operations")
        self.performance_logger = get_performance_logger()
        self.start_time = None
        self.kwargs = kwargs

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.performance_logger.log_operation_start(self.operation_name, **self.kwargs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        success = exc_type is None

        self.performance_logger.log_operation_end(
            self.operation_name, duration, success, **self.kwargs
        )

        if not success:
            self.logger.error(
                f"Operation failed: {self.operation_name}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={"operation": self.operation_name, "duration": duration},
            )
