#!/usr/bin/env python3
"""
Demonstration script for comprehensive error handling and resilience features.

This script showcases the error handling capabilities implemented across
the multi-agent video system, including:
- Retry mechanisms with exponential backoff
- Fallback strategies
- Circuit breaker patterns
- Health monitoring
- Graceful degradation
- Resource monitoring
- Rate limiting
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries import (
    # Error classes
    APIError,
    NetworkError,
    ValidationError,
    ProcessingError,
    ResourceError,
    RateLimitError,
    TimeoutError,
    
    # Retry and resilience
    RetryConfig,
    retry_with_exponential_backoff,
    FallbackManager,
    FallbackConfig,
    CircuitBreaker,
    
    # Monitoring and health
    ResourceMonitor,
    GracefulDegradation,
    RateLimiter,
    HealthMonitor,
    
    # Logging
    get_logger,
    initialize_logging,
    create_error_response
)


def demo_error_classes():
    """Demonstrate error class usage and serialization."""
    print("\n=== Error Classes Demo ===")
    
    # Create different types of errors
    errors = [
        APIError("Service unavailable", api_name="TestAPI", status_code=503),
        NetworkError("Connection timeout"),
        ValidationError("Invalid input format", field="email"),
        ProcessingError("Data processing failed", stage="transformation"),
        ResourceError("Insufficient memory", resource_type="memory"),
        RateLimitError("Too many requests", retry_after=60),
        TimeoutError("Operation timed out", timeout_duration=30.0)
    ]
    
    for error in errors:
        print(f"✓ {error.__class__.__name__}: {error.message}")
        print(f"  Category: {error.category.value}")
        print(f"  Severity: {error.severity.value}")
        
        # Demonstrate error response creation
        response = create_error_response(error)
        print(f"  Response: {response['success']} - {response['error']['message']}")
        print()


def demo_retry_mechanisms():
    """Demonstrate retry mechanisms with exponential backoff."""
    print("\n=== Retry Mechanisms Demo ===")
    
    # Configure retry behavior
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=True
    )
    
    # Simulate a service that fails initially but eventually succeeds
    attempt_count = 0
    
    @retry_with_exponential_backoff(
        retry_config=retry_config,
        exceptions=(ProcessingError,)
    )
    def unreliable_service():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}")
        
        if attempt_count < 3:
            raise ProcessingError(f"Service failed on attempt {attempt_count}")
        
        return f"Success after {attempt_count} attempts"
    
    try:
        result = unreliable_service()
        print(f"✓ {result}")
    except Exception as e:
        print(f"✗ Final failure: {e}")


def demo_fallback_strategies():
    """Demonstrate fallback mechanisms."""
    print("\n=== Fallback Strategies Demo ===")
    
    def primary_service():
        raise APIError("Primary service is down", api_name="Primary")
    
    def fallback_service_1():
        raise APIError("Fallback 1 is also down", api_name="Fallback1")
    
    def fallback_service_2():
        return "Fallback 2 succeeded"
    
    config = FallbackConfig(
        enabled=True,
        graceful_degradation=True
    )
    
    manager = FallbackManager(config)
    
    try:
        result = manager.execute_with_fallback(
            primary_service,
            [fallback_service_1, fallback_service_2]
        )
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"✗ All services failed: {e}")


def demo_circuit_breaker():
    """Demonstrate circuit breaker pattern."""
    print("\n=== Circuit Breaker Demo ===")
    
    failure_count = 0
    
    # Create circuit breaker with low threshold for demo
    circuit_breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=1.0
    )
    
    @circuit_breaker
    def failing_service():
        nonlocal failure_count
        failure_count += 1
        raise ProcessingError(f"Service failure #{failure_count}")
    
    # Demonstrate circuit breaker states
    print("Testing circuit breaker states:")
    
    # CLOSED state - failures increment counter
    for i in range(2):
        try:
            failing_service()
        except ProcessingError as e:
            print(f"  Failure {i+1}: {e.message}")
    
    # OPEN state - circuit breaker blocks calls
    try:
        failing_service()
    except ProcessingError as e:
        print(f"  Circuit breaker blocked: {e.message}")
    
    print(f"✓ Circuit breaker opened after {failure_count} failures")


def demo_health_monitoring():
    """Demonstrate health monitoring system."""
    print("\n=== Health Monitoring Demo ===")
    
    # Create health monitor
    monitor = HealthMonitor()
    
    # Register services with different health states
    def healthy_service():
        return {"status": "healthy", "details": {"uptime": "99.9%"}}
    
    def degraded_service():
        return {"status": "degraded", "details": {"warning": "High latency"}}
    
    def failing_service():
        raise Exception("Service is down")
    
    # Register services
    monitor.service_registry.register_service(
        "healthy_service",
        health_check_func=healthy_service,
        critical=False
    )
    
    monitor.service_registry.register_service(
        "degraded_service",
        health_check_func=degraded_service,
        critical=True
    )
    
    monitor.service_registry.register_service(
        "failing_service",
        health_check_func=failing_service,
        critical=True
    )
    
    # Perform health checks
    for service_name in ["healthy_service", "degraded_service", "failing_service"]:
        result = monitor.service_registry.perform_health_check(service_name)
        print(f"  {service_name}: {result.status.value}")
        if result.error_message:
            print(f"    Error: {result.error_message}")
        if result.details:
            print(f"    Details: {result.details}")
    
    # Get overall system status
    system_status = monitor.get_system_status()
    print(f"✓ Overall system healthy: {system_status['overall_healthy']}")


def demo_resource_monitoring():
    """Demonstrate resource monitoring."""
    print("\n=== Resource Monitoring Demo ===")
    
    try:
        monitor = ResourceMonitor()
        
        # Get current metrics
        metrics = monitor.get_current_metrics()
        print(f"  CPU Usage: {metrics.cpu_percent:.1f}%")
        print(f"  Memory Usage: {metrics.memory_percent:.1f}%")
        print(f"  Disk Usage: {metrics.disk_percent:.1f}%")
        print(f"  Available Memory: {metrics.available_memory_gb:.2f} GB")
        
        # Check for resource constraints
        constraints = monitor.check_resource_constraints()
        if constraints["healthy"]:
            print("✓ System resources are healthy")
        else:
            print("⚠ Resource constraints detected:")
            for warning in constraints["warnings"]:
                print(f"    Warning: {warning}")
            for alert in constraints["alerts"]:
                print(f"    Alert: {alert}")
        
        # Check if requests should be throttled
        should_throttle = monitor.should_throttle_requests()
        print(f"  Should throttle requests: {should_throttle}")
        
    except Exception as e:
        print(f"✗ Resource monitoring failed: {e}")


def demo_graceful_degradation():
    """Demonstrate graceful degradation."""
    print("\n=== Graceful Degradation Demo ===")
    
    degradation = GracefulDegradation()
    
    # Test different degradation levels
    levels = ["normal", "reduced_quality", "essential_only", "emergency"]
    
    for level in levels:
        degradation.set_degradation_level(level)
        settings = degradation.get_quality_settings()
        
        print(f"  Level: {level}")
        print(f"    Video Quality: {settings['video_quality']}")
        print(f"    Max Duration: {settings['max_duration']}s")
        print(f"    Skip Effects: {settings['skip_effects']}")
        print(f"    Skip Non-Essential: {degradation.should_skip_non_essential()}")
        print()


def demo_rate_limiting():
    """Demonstrate rate limiting."""
    print("\n=== Rate Limiting Demo ===")
    
    # Create rate limiter with small bucket for demo
    limiter = RateLimiter(max_tokens=3, refill_rate=1.0)
    
    print("Testing rate limiter:")
    
    # Try to acquire tokens
    for i in range(5):
        success = limiter.acquire(1)
        print(f"  Request {i+1}: {'✓ Allowed' if success else '✗ Rate limited'}")
    
    print("  Waiting for token refill...")
    time.sleep(2)  # Wait for tokens to refill
    
    success = limiter.acquire(1)
    print(f"  After refill: {'✓ Allowed' if success else '✗ Still limited'}")


def demo_agent_error_handling():
    """Demonstrate error handling in agent tools."""
    print("\n=== Agent Error Handling Demo ===")
    
    # Test web search with invalid input
    try:
        from sub_agents.research.tools.web_search import web_search
        
        print("Testing web search with empty query:")
        result = web_search("")
        print(f"  Success: {result.get('success', False)}")
        if not result.get('success'):
            print(f"  Error: {result.get('error', {}).get('message', 'Unknown error')}")
    except ImportError:
        print("  Web search tool not available")
    
    # Test script generation with invalid input
    try:
        from sub_agents.story.tools.script_generator import generate_video_script
        
        print("Testing script generation with empty research data:")
        result = generate_video_script({})
        print(f"  Success: {result.get('success', False)}")
        if not result.get('success'):
            print(f"  Error: {result.get('error', {}).get('message', 'Unknown error')}")
    except ImportError:
        print("  Script generation tool not available")


def main():
    """Run all error handling demonstrations."""
    print("Multi-Agent Video System - Error Handling & Resilience Demo")
    print("=" * 60)
    
    # Initialize logging
    initialize_logging("INFO")
    logger = get_logger("demo")
    logger.info("Starting error handling demonstration")
    
    try:
        # Run all demonstrations
        demo_error_classes()
        demo_retry_mechanisms()
        demo_fallback_strategies()
        demo_circuit_breaker()
        demo_health_monitoring()
        demo_resource_monitoring()
        demo_graceful_degradation()
        demo_rate_limiting()
        demo_agent_error_handling()
        
        print("\n" + "=" * 60)
        print("✓ Error handling demonstration completed successfully!")
        print("\nKey features demonstrated:")
        print("  • Comprehensive error classification and handling")
        print("  • Retry mechanisms with exponential backoff")
        print("  • Fallback strategies and graceful degradation")
        print("  • Circuit breaker pattern for fault isolation")
        print("  • Health monitoring and service registry")
        print("  • Resource monitoring and constraint detection")
        print("  • Rate limiting and request throttling")
        print("  • Agent-level error handling integration")
        
        logger.info("Error handling demonstration completed successfully")
        return True
        
    except Exception as e:
        print(f"\n✗ Demonstration failed: {e}")
        logger.error(f"Demonstration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)