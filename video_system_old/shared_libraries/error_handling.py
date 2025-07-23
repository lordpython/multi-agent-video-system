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

"""Comprehensive error handling and resilience utilities for the multi-agent video system.

This module provides error handling patterns, retry mechanisms, fallback strategies,
and logging utilities following ADK patterns.
"""

import asyncio
import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field
import random
import json
from datetime import datetime


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    RESOURCE_ERROR = "resource_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class VideoSystemError(Exception):
    """Base exception class for video system errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "original_exception": str(self.original_exception)
            if self.original_exception
            else None,
        }


class APIError(VideoSystemError):
    """Error for API-related failures."""

    def __init__(
        self, message: str, api_name: str, status_code: Optional[int] = None, **kwargs
    ):
        super().__init__(
            message, error_code="API_ERROR", category=ErrorCategory.API_ERROR, **kwargs
        )
        self.details.update({"api_name": api_name, "status_code": status_code})


class NetworkError(VideoSystemError):
    """Error for network-related failures."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK_ERROR,
            **kwargs,
        )


class ValidationError(VideoSystemError):
    """Error for validation failures."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )
        if field:
            self.details["field"] = field


class ProcessingError(VideoSystemError):
    """Error for processing failures."""

    def __init__(self, message: str, stage: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="PROCESSING_ERROR",
            category=ErrorCategory.PROCESSING_ERROR,
            **kwargs,
        )
        if stage:
            self.details["stage"] = stage


class ConfigurationError(VideoSystemError):
    """Error for configuration-related failures."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="CONFIGURATION_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )
        if config_key:
            self.details["config_key"] = config_key


class ResourceError(VideoSystemError):
    """Error for resource-related failures."""

    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="RESOURCE_ERROR",
            category=ErrorCategory.RESOURCE_ERROR,
            **kwargs,
        )
        if resource_type:
            self.details["resource_type"] = resource_type


class RateLimitError(VideoSystemError):
    """Error for rate limiting."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            error_code="RATE_LIMIT_ERROR",
            category=ErrorCategory.RATE_LIMIT_ERROR,
            **kwargs,
        )
        if retry_after:
            self.details["retry_after"] = retry_after


class TimeoutError(VideoSystemError):
    """Error for timeout failures."""

    def __init__(
        self, message: str, timeout_duration: Optional[float] = None, **kwargs
    ):
        super().__init__(
            message,
            error_code="TIMEOUT_ERROR",
            category=ErrorCategory.TIMEOUT_ERROR,
            **kwargs,
        )
        if timeout_duration:
            self.details["timeout_duration"] = timeout_duration


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    max_delay: float = Field(default=60.0, ge=1.0, le=300.0)
    exponential_base: float = Field(default=2.0, ge=1.1, le=10.0)
    jitter: bool = Field(default=True)
    backoff_strategy: str = Field(
        default="exponential"
    )  # "exponential", "linear", "fixed"


class FallbackConfig(BaseModel):
    """Configuration for fallback behavior."""

    enabled: bool = Field(default=True)
    fallback_services: List[str] = Field(default=[])
    fallback_timeout: float = Field(default=30.0, ge=1.0, le=120.0)
    graceful_degradation: bool = Field(default=True)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger following ADK patterns."""
    logger = logging.getLogger(f"video_system.{name}")

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def log_error(
    logger: logging.Logger,
    error: Union[Exception, VideoSystemError],
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an error with structured information."""
    if isinstance(error, VideoSystemError):
        error_info = error.to_dict()
        if context:
            error_info["context"] = context

        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(error.severity, logging.ERROR)

        logger.log(log_level, f"VideoSystemError: {json.dumps(error_info, indent=2)}")
    else:
        logger.error(f"Exception: {str(error)}", exc_info=True)
        if context:
            logger.error(f"Context: {json.dumps(context, indent=2)}")


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt."""
    if config.backoff_strategy == "exponential":
        delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    elif config.backoff_strategy == "linear":
        delay = config.base_delay * attempt
    else:  # fixed
        delay = config.base_delay

    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add jitter to prevent thundering herd
        jitter_amount = delay * 0.1 * random.random()
        delay += jitter_amount

    return delay


def retry_with_exponential_backoff(
    retry_config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None,
):
    """Decorator for retry with exponential backoff."""
    if retry_config is None:
        retry_config = RetryConfig()

    if logger is None:
        logger = get_logger("retry")

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == retry_config.max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {attempt} attempts"
                        )
                        log_error(
                            logger, e, {"function": func.__name__, "attempt": attempt}
                        )
                        raise

                    delay = calculate_delay(attempt, retry_config)
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt}/{retry_config.max_attempts}. "
                        f"Retrying in {delay:.2f} seconds. Error: {str(e)}"
                    )

                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def async_retry_with_exponential_backoff(
    retry_config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None,
):
    """Async decorator for retry with exponential backoff."""
    if retry_config is None:
        retry_config = RetryConfig()

    if logger is None:
        logger = get_logger("async_retry")

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == retry_config.max_attempts:
                        logger.error(
                            f"Async function {func.__name__} failed after {attempt} attempts"
                        )
                        log_error(
                            logger, e, {"function": func.__name__, "attempt": attempt}
                        )
                        raise

                    delay = calculate_delay(attempt, retry_config)
                    logger.warning(
                        f"Async function {func.__name__} failed on attempt {attempt}/{retry_config.max_attempts}. "
                        f"Retrying in {delay:.2f} seconds. Error: {str(e)}"
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class FallbackManager:
    """Manager for handling fallback strategies."""

    def __init__(self, config: FallbackConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or get_logger("fallback")

    def execute_with_fallback(
        self, primary_func: Callable, fallback_funcs: List[Callable], *args, **kwargs
    ) -> Any:
        """Execute function with fallback options."""
        if not self.config.enabled:
            return primary_func(*args, **kwargs)

        # Try primary function first
        try:
            self.logger.info("Attempting primary function")
            return primary_func(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"Primary function failed: {str(e)}")
            log_error(self.logger, e, {"function": "primary"})

        # Try fallback functions
        for i, fallback_func in enumerate(fallback_funcs):
            try:
                self.logger.info(f"Attempting fallback function {i + 1}")
                return fallback_func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"Fallback function {i + 1} failed: {str(e)}")
                log_error(self.logger, e, {"function": f"fallback_{i + 1}"})

        # If all fallbacks fail
        if self.config.graceful_degradation:
            self.logger.error(
                "All functions failed, returning graceful degradation response"
            )
            return self._get_graceful_degradation_response()
        else:
            raise ProcessingError("All primary and fallback functions failed")

    def _get_graceful_degradation_response(self) -> Dict[str, Any]:
        """Get a graceful degradation response."""
        return {
            "success": False,
            "error": "Service temporarily unavailable",
            "fallback_response": True,
            "timestamp": datetime.utcnow().isoformat(),
        }


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        logger: Optional[logging.Logger] = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.logger = logger or get_logger("circuit_breaker")

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    self.logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise ProcessingError(
                        "Circuit breaker is OPEN - service unavailable"
                    )

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful execution."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker reset to CLOSED state")
        self.failure_count = 0

    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


def handle_api_errors(func: Callable) -> Callable:
    """Decorator to handle common API errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"API request timed out: {str(e)}", original_exception=e)
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Network connection failed: {str(e)}", original_exception=e
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            if status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise RateLimitError(
                    f"Rate limit exceeded: {str(e)}",
                    retry_after=int(retry_after) if retry_after else None,
                    original_exception=e,
                )
            elif status_code and 400 <= status_code < 500:
                raise APIError(
                    f"Client error: {str(e)}",
                    api_name="unknown",
                    status_code=status_code,
                    original_exception=e,
                )
            elif status_code and status_code >= 500:
                raise APIError(
                    f"Server error: {str(e)}",
                    api_name="unknown",
                    status_code=status_code,
                    severity=ErrorSeverity.HIGH,
                    original_exception=e,
                )
            else:
                raise APIError(
                    f"HTTP error: {str(e)}", api_name="unknown", original_exception=e
                )
        except Exception as e:
            raise ProcessingError(
                f"Unexpected error in API call: {str(e)}", original_exception=e
            )

    return wrapper


def create_error_response(
    error: Union[Exception, VideoSystemError], context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response."""
    if isinstance(error, VideoSystemError):
        response = {
            "success": False,
            "error": {
                "message": error.message,
                "code": error.error_code,
                "category": error.category.value,
                "severity": error.severity.value,
                "timestamp": error.timestamp.isoformat(),
            },
        }
        if error.details:
            response["error"]["details"] = error.details
    else:
        response = {
            "success": False,
            "error": {
                "message": str(error),
                "code": "UNKNOWN_ERROR",
                "category": ErrorCategory.UNKNOWN_ERROR.value,
                "severity": ErrorSeverity.MEDIUM.value,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    if context:
        response["error"]["context"] = context

    return response


# Import requests for API error handling
try:
    import requests
except ImportError:
    # If requests is not available, create a dummy module
    class DummyRequests:
        class exceptions:
            class Timeout(Exception):
                pass

            class ConnectionError(Exception):
                pass

            class HTTPError(Exception):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.response = None

    requests = DummyRequests()
