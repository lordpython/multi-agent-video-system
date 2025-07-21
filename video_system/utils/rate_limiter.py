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

"""Rate limiting and API throttling system for the multi-agent video system.

This module provides rate limiting capabilities for API calls, request throttling,
and adaptive rate limiting based on service health and response times.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from .logging_config import get_logger

logger = get_logger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


class ThrottleAction(Enum):
    """Actions to take when rate limit is exceeded."""
    REJECT = "reject"
    QUEUE = "queue"
    DELAY = "delay"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    requests_per_minute: float = 600.0
    requests_per_hour: float = 36000.0
    burst_size: int = 20
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    throttle_action: ThrottleAction = ThrottleAction.DELAY
    max_queue_size: int = 100
    max_delay_seconds: float = 30.0


@dataclass
class ServiceLimits:
    """Rate limits for specific services."""
    service_name: str
    config: RateLimitConfig
    priority: int = 1  # 1 = highest, 5 = lowest
    adaptive_enabled: bool = True
    health_threshold: float = 0.8  # Health score threshold for adaptive limiting


@dataclass
class RequestRecord:
    """Record of a rate-limited request."""
    timestamp: datetime
    service_name: str
    user_id: Optional[str]
    success: bool
    response_time_ms: float
    rate_limited: bool = False


@dataclass
class RateLimitStatus:
    """Current rate limit status for a service."""
    service_name: str
    current_rps: float
    allowed_rps: float
    requests_in_window: int
    tokens_available: float
    queue_size: int
    last_request: Optional[datetime]
    adaptive_multiplier: float = 1.0


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: float, refill_rate: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_available_tokens(self) -> float:
        """Get number of available tokens.
        
        Returns:
            Number of available tokens
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            return min(self.capacity, self.tokens + elapsed * self.refill_rate)
    
    def time_until_tokens(self, tokens: float = 1.0) -> float:
        """Get time until specified tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens are available
        """
        available = self.get_available_tokens()
        if available >= tokens:
            return 0.0
        
        needed = tokens - available
        return needed / self.refill_rate


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size_seconds: float):
        """Initialize sliding window counter.
        
        Args:
            window_size_seconds: Size of the sliding window
        """
        self.window_size = window_size_seconds
        self.requests = deque()
        self.lock = threading.Lock()
    
    def add_request(self, timestamp: Optional[datetime] = None) -> int:
        """Add a request to the window.
        
        Args:
            timestamp: Request timestamp (defaults to now)
            
        Returns:
            Current count in window
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        with self.lock:
            # Add new request
            self.requests.append(timestamp)
            
            # Remove old requests outside window
            cutoff = timestamp - timedelta(seconds=self.window_size)
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            return len(self.requests)
    
    def get_count(self) -> int:
        """Get current count in window.
        
        Returns:
            Number of requests in current window
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_size)
        
        with self.lock:
            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            return len(self.requests)
    
    def get_rate(self) -> float:
        """Get current rate (requests per second).
        
        Returns:
            Current rate in requests per second
        """
        count = self.get_count()
        return count / self.window_size


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits based on service health."""
    
    def __init__(self, base_config: RateLimitConfig):
        """Initialize adaptive rate limiter.
        
        Args:
            base_config: Base rate limit configuration
        """
        self.base_config = base_config
        self.current_multiplier = 1.0
        self.response_times = deque(maxlen=100)
        self.success_rate = deque(maxlen=100)
        self.last_adjustment = datetime.utcnow()
        self.lock = threading.Lock()
    
    def record_request(self, success: bool, response_time_ms: float):
        """Record a request for adaptive adjustment.
        
        Args:
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
        """
        with self.lock:
            self.response_times.append(response_time_ms)
            self.success_rate.append(1.0 if success else 0.0)
    
    def get_current_limits(self) -> RateLimitConfig:
        """Get current rate limits with adaptive adjustments.
        
        Returns:
            Adjusted rate limit configuration
        """
        self._adjust_limits()
        
        adjusted_config = RateLimitConfig(
            requests_per_second=self.base_config.requests_per_second * self.current_multiplier,
            requests_per_minute=self.base_config.requests_per_minute * self.current_multiplier,
            requests_per_hour=self.base_config.requests_per_hour * self.current_multiplier,
            burst_size=max(1, int(self.base_config.burst_size * self.current_multiplier)),
            strategy=self.base_config.strategy,
            throttle_action=self.base_config.throttle_action,
            max_queue_size=self.base_config.max_queue_size,
            max_delay_seconds=self.base_config.max_delay_seconds
        )
        
        return adjusted_config
    
    def _adjust_limits(self):
        """Adjust rate limits based on service health."""
        now = datetime.utcnow()
        
        # Only adjust every 30 seconds
        if (now - self.last_adjustment).total_seconds() < 30:
            return
        
        with self.lock:
            if not self.response_times or not self.success_rate:
                return
            
            # Calculate health metrics
            avg_response_time = sum(self.response_times) / len(self.response_times)
            current_success_rate = sum(self.success_rate) / len(self.success_rate)
            
            # Determine adjustment based on health
            health_score = self._calculate_health_score(avg_response_time, current_success_rate)
            
            # Adjust multiplier based on health
            if health_score > 0.9:
                # Service is healthy, can increase limits
                self.current_multiplier = min(2.0, self.current_multiplier * 1.1)
            elif health_score > 0.7:
                # Service is okay, maintain current limits
                pass
            elif health_score > 0.5:
                # Service is struggling, reduce limits slightly
                self.current_multiplier = max(0.1, self.current_multiplier * 0.9)
            else:
                # Service is unhealthy, reduce limits significantly
                self.current_multiplier = max(0.1, self.current_multiplier * 0.5)
            
            self.last_adjustment = now
            
            logger.debug(f"Adaptive rate limiter adjusted: health={health_score:.2f}, multiplier={self.current_multiplier:.2f}")
    
    def _calculate_health_score(self, avg_response_time: float, success_rate: float) -> float:
        """Calculate service health score.
        
        Args:
            avg_response_time: Average response time in milliseconds
            success_rate: Success rate (0.0 to 1.0)
            
        Returns:
            Health score (0.0 to 1.0)
        """
        # Response time component (lower is better)
        # Assume 1000ms is baseline, 5000ms is very poor
        response_score = max(0.0, 1.0 - (avg_response_time - 1000) / 4000)
        response_score = max(0.0, min(1.0, response_score))
        
        # Success rate component
        success_score = success_rate
        
        # Combined health score (weighted average)
        health_score = (response_score * 0.4) + (success_score * 0.6)
        
        return health_score


class RateLimiter:
    """Main rate limiter that manages limits for multiple services."""
    
    def __init__(self):
        """Initialize the rate limiter."""
        self.service_limits: Dict[str, ServiceLimits] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        self.adaptive_limiters: Dict[str, AdaptiveRateLimiter] = {}
        self.request_queues: Dict[str, deque] = defaultdict(deque)
        self.request_history: List[RequestRecord] = []
        self.lock = threading.RLock()
        
        # Global user-based limiting
        self.user_windows: Dict[str, SlidingWindowCounter] = {}
        self.user_limits = RateLimitConfig(
            requests_per_second=5.0,
            requests_per_minute=300.0,
            requests_per_hour=18000.0
        )
        
        logger.info("RateLimiter initialized")
    
    def add_service_limits(self, service_limits: ServiceLimits):
        """Add rate limits for a service.
        
        Args:
            service_limits: Service rate limit configuration
        """
        service_name = service_limits.service_name
        
        with self.lock:
            self.service_limits[service_name] = service_limits
            
            # Initialize rate limiting components
            config = service_limits.config
            
            if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                self.token_buckets[service_name] = TokenBucket(
                    capacity=config.burst_size,
                    refill_rate=config.requests_per_second
                )
            
            if config.strategy in [RateLimitStrategy.SLIDING_WINDOW, RateLimitStrategy.ADAPTIVE]:
                self.sliding_windows[service_name] = SlidingWindowCounter(60.0)  # 1 minute window
            
            if service_limits.adaptive_enabled:
                self.adaptive_limiters[service_name] = AdaptiveRateLimiter(config)
        
        logger.info(f"Added rate limits for service: {service_name}")
    
    def check_rate_limit(self, 
                        service_name: str, 
                        user_id: Optional[str] = None,
                        tokens: float = 1.0) -> Tuple[bool, float]:
        """Check if a request is within rate limits.
        
        Args:
            service_name: Name of the service
            user_id: Optional user identifier
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, delay_seconds)
        """
        with self.lock:
            # Check service-specific limits
            service_allowed, service_delay = self._check_service_limit(service_name, tokens)
            
            # Check user-specific limits
            user_allowed, user_delay = self._check_user_limit(user_id, tokens)
            
            # Both must be allowed
            allowed = service_allowed and user_allowed
            delay = max(service_delay, user_delay)
            
            return allowed, delay
    
    def record_request(self, 
                      service_name: str,
                      user_id: Optional[str] = None,
                      success: bool = True,
                      response_time_ms: float = 0.0,
                      rate_limited: bool = False):
        """Record a request for rate limiting and adaptive adjustment.
        
        Args:
            service_name: Name of the service
            user_id: Optional user identifier
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
            rate_limited: Whether the request was rate limited
        """
        record = RequestRecord(
            timestamp=datetime.utcnow(),
            service_name=service_name,
            user_id=user_id,
            success=success,
            response_time_ms=response_time_ms,
            rate_limited=rate_limited
        )
        
        with self.lock:
            self.request_history.append(record)
            
            # Limit history size
            if len(self.request_history) > 10000:
                self.request_history = self.request_history[-5000:]
            
            # Update adaptive limiter
            if service_name in self.adaptive_limiters:
                self.adaptive_limiters[service_name].record_request(success, response_time_ms)
    
    def get_service_status(self, service_name: str) -> Optional[RateLimitStatus]:
        """Get current rate limit status for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Rate limit status or None if service not found
        """
        with self.lock:
            if service_name not in self.service_limits:
                return None
            
            service_limits = self.service_limits[service_name]
            config = service_limits.config
            
            # Get current configuration (with adaptive adjustments)
            if service_name in self.adaptive_limiters:
                current_config = self.adaptive_limiters[service_name].get_current_limits()
            else:
                current_config = config
            
            # Get current metrics
            current_rps = 0.0
            requests_in_window = 0
            tokens_available = 0.0
            
            if service_name in self.sliding_windows:
                window = self.sliding_windows[service_name]
                current_rps = window.get_rate()
                requests_in_window = window.get_count()
            
            if service_name in self.token_buckets:
                bucket = self.token_buckets[service_name]
                tokens_available = bucket.get_available_tokens()
            
            queue_size = len(self.request_queues[service_name])
            
            # Get last request time
            last_request = None
            for record in reversed(self.request_history):
                if record.service_name == service_name:
                    last_request = record.timestamp
                    break
            
            adaptive_multiplier = 1.0
            if service_name in self.adaptive_limiters:
                adaptive_multiplier = self.adaptive_limiters[service_name].current_multiplier
            
            return RateLimitStatus(
                service_name=service_name,
                current_rps=current_rps,
                allowed_rps=current_config.requests_per_second,
                requests_in_window=requests_in_window,
                tokens_available=tokens_available,
                queue_size=queue_size,
                last_request=last_request,
                adaptive_multiplier=adaptive_multiplier
            )
    
    def get_all_service_status(self) -> Dict[str, RateLimitStatus]:
        """Get rate limit status for all services.
        
        Returns:
            Dictionary of service statuses
        """
        with self.lock:
            return {
                service_name: self.get_service_status(service_name)
                for service_name in self.service_limits.keys()
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.lock:
            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)
            
            # Filter recent requests
            recent_requests = [
                r for r in self.request_history
                if r.timestamp >= last_hour
            ]
            
            # Calculate statistics
            total_requests = len(recent_requests)
            rate_limited_requests = sum(1 for r in recent_requests if r.rate_limited)
            successful_requests = sum(1 for r in recent_requests if r.success)
            
            avg_response_time = 0.0
            if recent_requests:
                avg_response_time = sum(r.response_time_ms for r in recent_requests) / len(recent_requests)
            
            # Service-specific statistics
            service_stats = {}
            for service_name in self.service_limits.keys():
                service_requests = [r for r in recent_requests if r.service_name == service_name]
                service_stats[service_name] = {
                    "total_requests": len(service_requests),
                    "rate_limited": sum(1 for r in service_requests if r.rate_limited),
                    "success_rate": sum(1 for r in service_requests if r.success) / max(1, len(service_requests)),
                    "avg_response_time": sum(r.response_time_ms for r in service_requests) / max(1, len(service_requests))
                }
            
            return {
                "total_requests_last_hour": total_requests,
                "rate_limited_requests": rate_limited_requests,
                "rate_limited_percentage": (rate_limited_requests / max(1, total_requests)) * 100,
                "successful_requests": successful_requests,
                "success_rate": (successful_requests / max(1, total_requests)) * 100,
                "average_response_time_ms": avg_response_time,
                "service_statistics": service_stats,
                "active_services": len(self.service_limits),
                "total_history_records": len(self.request_history)
            }
    
    def _check_service_limit(self, service_name: str, tokens: float) -> Tuple[bool, float]:
        """Check service-specific rate limits.
        
        Args:
            service_name: Name of the service
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, delay_seconds)
        """
        if service_name not in self.service_limits:
            return True, 0.0
        
        service_limits = self.service_limits[service_name]
        config = service_limits.config
        
        # Get current configuration (with adaptive adjustments)
        if service_name in self.adaptive_limiters:
            current_config = self.adaptive_limiters[service_name].get_current_limits()
        else:
            current_config = config
        
        # Check based on strategy
        if current_config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if service_name in self.token_buckets:
                bucket = self.token_buckets[service_name]
                if bucket.consume(tokens):
                    return True, 0.0
                else:
                    delay = bucket.time_until_tokens(tokens)
                    return False, min(delay, current_config.max_delay_seconds)
        
        elif current_config.strategy in [RateLimitStrategy.SLIDING_WINDOW, RateLimitStrategy.ADAPTIVE]:
            if service_name in self.sliding_windows:
                window = self.sliding_windows[service_name]
                current_rate = window.get_rate()
                
                if current_rate < current_config.requests_per_second:
                    window.add_request()
                    return True, 0.0
                else:
                    # Calculate delay based on current rate
                    delay = (current_rate - current_config.requests_per_second) / current_config.requests_per_second
                    return False, min(delay, current_config.max_delay_seconds)
        
        return True, 0.0
    
    def _check_user_limit(self, user_id: Optional[str], tokens: float) -> Tuple[bool, float]:
        """Check user-specific rate limits.
        
        Args:
            user_id: User identifier
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, delay_seconds)
        """
        if not user_id:
            return True, 0.0
        
        # Get or create user window
        if user_id not in self.user_windows:
            self.user_windows[user_id] = SlidingWindowCounter(60.0)  # 1 minute window
        
        window = self.user_windows[user_id]
        current_rate = window.get_rate()
        
        if current_rate < self.user_limits.requests_per_second:
            window.add_request()
            return True, 0.0
        else:
            delay = (current_rate - self.user_limits.requests_per_second) / self.user_limits.requests_per_second
            return False, min(delay, self.user_limits.max_delay_seconds)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def initialize_rate_limiter() -> RateLimiter:
    """Initialize the global rate limiter with default service limits."""
    global _rate_limiter
    _rate_limiter = RateLimiter()
    
    # Add default service limits
    default_services = [
        ServiceLimits(
            service_name="serper_api",
            config=RateLimitConfig(
                requests_per_second=2.0,
                requests_per_minute=100.0,
                burst_size=5,
                strategy=RateLimitStrategy.TOKEN_BUCKET
            ),
            priority=1,
            adaptive_enabled=True
        ),
        ServiceLimits(
            service_name="pexels_api",
            config=RateLimitConfig(
                requests_per_second=5.0,
                requests_per_minute=200.0,
                burst_size=10,
                strategy=RateLimitStrategy.TOKEN_BUCKET
            ),
            priority=2,
            adaptive_enabled=True
        ),
        ServiceLimits(
            service_name="gemini_api",
            config=RateLimitConfig(
                requests_per_second=10.0,
                requests_per_minute=600.0,
                burst_size=20,
                strategy=RateLimitStrategy.ADAPTIVE
            ),
            priority=1,
            adaptive_enabled=True
        ),
        ServiceLimits(
            service_name="video_processing",
            config=RateLimitConfig(
                requests_per_second=1.0,
                requests_per_minute=30.0,
                burst_size=3,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                throttle_action=ThrottleAction.QUEUE
            ),
            priority=1,
            adaptive_enabled=False
        )
    ]
    
    for service_limits in default_services:
        _rate_limiter.add_service_limits(service_limits)
    
    logger.info("Rate limiter initialized with default service limits")
    return _rate_limiter