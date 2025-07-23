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

"""Error handling utilities for the video system."""

import logging
import functools
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, cast


class VideoSystemError(Exception):
    """Base exception for video system errors."""

    pass


class ConfigurationError(VideoSystemError):
    """Exception raised for configuration-related errors."""

    pass


class APIError(VideoSystemError):
    """Exception raised for API-related errors."""

    pass


class NetworkError(VideoSystemError):
    """Exception raised for network-related errors."""

    pass


class ValidationError(VideoSystemError):
    """Exception raised for validation errors."""

    pass


class ProcessingError(VideoSystemError):
    """Exception raised for processing errors."""

    pass


class ResourceError(VideoSystemError):
    """Exception raised for resource-related errors."""

    pass


class RateLimitError(VideoSystemError):
    """Exception raised when rate limits are exceeded."""

    pass


class TimeoutError(VideoSystemError):
    """Exception raised for timeout errors."""

    pass


class VideoSystemError(Exception):
    """Base exception for video system errors."""

    pass


class ConfigurationError(VideoSystemError):
    """Exception raised for configuration-related errors."""

    pass


class APIError(VideoSystemError):
    """Exception raised for API-related errors."""

    pass


class NetworkError(VideoSystemError):
    """Exception raised for network-related errors."""

    pass


class ValidationError(VideoSystemError):
    """Exception raised for validation errors."""

    pass


class ProcessingError(VideoSystemError):
    """Exception raised for processing errors."""

    pass


class ResourceError(VideoSystemError):
    """Exception raised for resource-related errors."""

    pass


class RateLimitError(VideoSystemError):
    """Exception raised when rate limits are exceeded."""

    pass


class TimeoutError(VideoSystemError):
    """Exception raised for timeout errors."""

    pass


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Name of the logger

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_error(
    logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with context information.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context information
    """
    error_message = f"Error: {str(error)}"
    if context:
        error_message += f" Context: {context}"

    logger.error(error_message)
    logger.debug(traceback.format_exc())


# Type variable for function return type
T = TypeVar("T")


def handle_api_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle API errors.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = get_logger(func.__module__)
            log_error(
                logger, e, {"function": func.__name__, "args": args, "kwargs": kwargs}
            )
            raise

    return cast(Callable[..., T], wrapper)


def create_error_response(error: Exception, status_code: int = 500) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        error: Exception that occurred
        status_code: HTTP status code

    Returns:
        Error response dictionary
    """
    return {
        "status": "error",
        "code": status_code,
        "message": str(error),
        "error_type": error.__class__.__name__,
    }


# Custom exceptions are defined above


# Configuration classes
class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        max_attempts: int = None,
        initial_delay: float = 1.0,
        base_delay: float = None,
        backoff_factor: float = 2.0,
        exponential_base: float = None,
        max_delay: float = 60.0,
        jitter: bool = False,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            max_attempts: Alternative name for max_retries
            initial_delay: Initial delay in seconds
            base_delay: Alternative name for initial_delay
            backoff_factor: Factor to multiply delay by after each retry
            exponential_base: Alternative name for backoff_factor
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to delays
        """
        # Support both parameter names for compatibility
        self.max_retries = max_attempts if max_attempts is not None else max_retries
        self.initial_delay = base_delay if base_delay is not None else initial_delay
        self.backoff_factor = (
            exponential_base if exponential_base is not None else backoff_factor
        )
        self.max_delay = max_delay
        self.jitter = jitter


class FallbackConfig:
    """Configuration for fallback behavior."""

    def __init__(
        self,
        fallback_function: Optional[Callable[..., Any]] = None,
        default_value: Any = None,
    ):
        """
        Initialize fallback configuration.

        Args:
            fallback_function: Function to call as fallback
            default_value: Default value to return if fallback function is not provided
        """
        self.fallback_function = fallback_function
        self.default_value = default_value


# Retry decorator with exponential backoff
def retry_with_exponential_backoff(
    retry_config: Optional[RetryConfig] = None,
    config: Optional[RetryConfig] = None,
    exceptions: tuple = None,
    logger: Optional[Any] = None,
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        retry_config: Retry configuration (preferred parameter name)
        config: Alternative name for retry_config
        exceptions: Tuple of exceptions to catch and retry on
        logger: Logger instance to use

    Returns:
        Decorated function
    """
    # Support both parameter names for compatibility
    retry_config = retry_config or config or RetryConfig()
    exceptions = exceptions or (NetworkError, TimeoutError)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import time
            import random

            func_logger = logger or get_logger(func.__module__)
            retries = 0
            delay = retry_config.initial_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > retry_config.max_retries:
                        func_logger.error(
                            f"Max retries ({retry_config.max_retries}) exceeded for {func.__name__}"
                        )
                        raise

                    func_logger.warning(
                        f"Retry {retries}/{retry_config.max_retries} for {func.__name__} after error: {str(e)}"
                    )

                    # Add jitter if enabled
                    actual_delay = delay
                    if retry_config.jitter:
                        actual_delay = delay * (0.5 + random.random() * 0.5)

                    time.sleep(actual_delay)
                    delay = min(
                        delay * retry_config.backoff_factor, retry_config.max_delay
                    )

        return cast(Callable[..., T], wrapper)

    return decorator


# Async retry decorator with exponential backoff
async def async_retry_with_exponential_backoff(
    func: Callable[..., Any],
    config: Optional[RetryConfig] = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        config: Retry configuration
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function
    """
    import asyncio

    if config is None:
        config = RetryConfig()

    logger = get_logger(func.__module__)
    retries = 0
    delay = config.initial_delay

    while True:
        try:
            return await func(*args, **kwargs)
        except (NetworkError, TimeoutError) as e:
            retries += 1
            if retries > config.max_retries:
                logger.error(
                    f"Max retries ({config.max_retries}) exceeded for {func.__name__}"
                )
                raise

            logger.warning(
                f"Retry {retries}/{config.max_retries} for {func.__name__} after error: {str(e)}"
            )
            await asyncio.sleep(delay)
            delay = min(delay * config.backoff_factor, config.max_delay)


# Fallback manager
class FallbackManager:
    """Manager for fallback behavior."""

    def __init__(self, config: Optional[FallbackConfig] = None):
        """
        Initialize fallback manager.

        Args:
            config: Fallback configuration
        """
        self.config = config or FallbackConfig()

    def execute_with_fallback(
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a function with fallback.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function or fallback
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = get_logger(func.__module__)
            logger.warning(
                f"Function {func.__name__} failed, using fallback. Error: {str(e)}"
            )

            if self.config.fallback_function:
                return self.config.fallback_function(*args, **kwargs)
            else:
                return self.config.default_value


# Circuit breaker pattern
class CircuitBreaker:
    """Implementation of the circuit breaker pattern."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before attempting to close the circuit
            half_open_timeout: Time in seconds to wait in half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout

        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function

        Raises:
            CircuitBreakerOpenError: If the circuit is open
        """
        import time

        logger = get_logger(func.__module__)

        current_time = time.time()

        # Check if circuit is open
        if self.state == "open":
            if current_time - self.last_failure_time > self.reset_timeout:
                logger.info(
                    f"Circuit for {func.__name__} transitioning from open to half-open"
                )
                self.state = "half-open"
            else:
                raise VideoSystemError(f"Circuit breaker for {func.__name__} is open")

        # Execute function
        try:
            result = func(*args, **kwargs)

            # Reset on success
            if self.state == "half-open":
                logger.info(
                    f"Circuit for {func.__name__} transitioning from half-open to closed"
                )
                self.state = "closed"
                self.failure_count = 0

            return result
        except Exception:
            # Handle failure
            self.failure_count += 1
            self.last_failure_time = current_time

            if self.state == "closed" and self.failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit for {func.__name__} transitioning from closed to open after {self.failure_count} failures"
                )
                self.state = "open"
            elif self.state == "half-open":
                logger.warning(
                    f"Circuit for {func.__name__} transitioning from half-open to open after failure"
                )
                self.state = "open"

            raise
