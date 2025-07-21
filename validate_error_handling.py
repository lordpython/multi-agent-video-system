#!/usr/bin/env python3
"""Simple validation script for error handling implementation."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_error_classes():
    """Test that error classes can be imported and instantiated."""
    try:
        from video_system.shared_libraries.error_handling import (
            VideoSystemError,
            APIError,
            ValidationError,
            create_error_response
        )
        
        # Test basic error creation
        error = VideoSystemError("Test error", error_code="TEST_001")
        assert error.message == "Test error"
        assert error.error_code == "TEST_001"
        
        # Test API error
        api_error = APIError("API failed", api_name="TestAPI", status_code=500)
        assert api_error.details["api_name"] == "TestAPI"
        assert api_error.details["status_code"] == 500
        
        # Test validation error
        val_error = ValidationError("Invalid input", field="test_field")
        assert val_error.details["field"] == "test_field"
        
        # Test error response creation
        response = create_error_response(error)
        assert response["success"] is False
        assert response["error"]["message"] == "Test error"
        
        print("✓ Error classes validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Error classes validation failed: {e}")
        return False

def test_retry_config():
    """Test retry configuration."""
    try:
        from video_system.shared_libraries.error_handling import RetryConfig
        
        config = RetryConfig(max_attempts=3, base_delay=1.0)
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        
        print("✓ Retry configuration validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Retry configuration validation failed: {e}")
        return False

def test_logging_config():
    """Test logging configuration."""
    try:
        from video_system.shared_libraries.logging_config import (
            StructuredFormatter,
            get_logger,
            initialize_logging
        )
        
        # Test formatter
        formatter = StructuredFormatter()
        assert formatter is not None
        
        # Test logger initialization
        initialize_logging("INFO")
        logger = get_logger("test")
        assert logger is not None
        
        print("✓ Logging configuration validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Logging configuration validation failed: {e}")
        return False

def test_resilience_components():
    """Test resilience components."""
    try:
        from video_system.shared_libraries.resilience import (
            ServiceRegistry,
            GracefulDegradation,
            RateLimiter
        )
        
        # Test service registry
        registry = ServiceRegistry()
        registry.register_service("test_service", critical=True)
        assert "test_service" in registry.services
        
        # Test graceful degradation
        degradation = GracefulDegradation()
        degradation.set_degradation_level("reduced_quality")
        assert degradation.should_reduce_quality()
        
        # Test rate limiter
        limiter = RateLimiter(max_tokens=5, refill_rate=1.0)
        assert limiter.acquire(2) is True
        
        print("✓ Resilience components validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Resilience components validation failed: {e}")
        return False

def test_agent_error_integration():
    """Test error handling integration in agents."""
    try:
        # Test that agents can import error handling utilities
        from sub_agents.research.tools.web_search import web_search
        from sub_agents.story.tools.script_generator import generate_video_script
        from sub_agents.asset_sourcing.tools.pexels_search import search_pexels_media
        
        # Test error responses for invalid inputs
        result = web_search("")  # Empty query should fail gracefully
        assert result.get("success") is False
        
        result = generate_video_script({})  # Empty research data should fail
        assert result.get("success") is False
        
        result = search_pexels_media("")  # Empty query should fail
        assert result.get("success") is False
        
        print("✓ Agent error integration validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Agent error integration validation failed: {e}")
        return False

def test_health_monitoring():
    """Test health monitoring system."""
    try:
        from video_system.shared_libraries.resilience import HealthMonitor
        
        monitor = HealthMonitor()
        
        # Test service registration
        def test_health_check():
            return {"status": "healthy"}
        
        monitor.service_registry.register_service(
            "test_service",
            health_check_func=test_health_check
        )
        
        # Test health check execution
        result = monitor.service_registry.perform_health_check("test_service")
        assert result.service_name == "test_service"
        assert result.status.value == "healthy"
        
        print("✓ Health monitoring validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Health monitoring validation failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("Validating error handling implementation...")
    print("=" * 50)
    
    tests = [
        test_error_classes,
        test_retry_config,
        test_logging_config,
        test_resilience_components,
        test_agent_error_integration,
        test_health_monitoring
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 50)
    print(f"Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All error handling components validated successfully!")
        return True
    else:
        print("✗ Some validation tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)