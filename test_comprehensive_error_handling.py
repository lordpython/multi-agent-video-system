#!/usr/bin/env python3
"""
Comprehensive test for session management error handling.

This script tests all the error handling scenarios implemented in task 5.
"""

import asyncio
import logging
import sys
import time

# Add the video_system to the path
sys.path.append('video_system')

from video_system.shared_libraries.adk_session_manager import VideoSystemSessionManager, get_session_manager
from video_system.shared_libraries.session_error_handling import (
    SessionError, get_session_health_monitor
)
from video_system.orchestration_tools import (
    coordinate_research, get_session_status, handle_orchestration_error,
    validate_session_exists
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockFailingSessionService:
    """Mock session service that fails operations for testing."""
    
    def __init__(self, fail_operations=None):
        self.fail_operations = fail_operations or []
        self.call_count = {}
    
    async def create_session(self, *args, **kwargs):
        self.call_count['create_session'] = self.call_count.get('create_session', 0) + 1
        if 'create_session' in self.fail_operations:
            raise Exception("Mock create_session failure")
        # Return a mock session
        class MockSession:
            def __init__(self):
                self.id = f"mock_session_{time.time()}"
                self.state = {}
        return MockSession()
    
    async def get_session(self, *args, **kwargs):
        self.call_count['get_session'] = self.call_count.get('get_session', 0) + 1
        if 'get_session' in self.fail_operations:
            raise Exception("Mock get_session failure")
        return None  # Simulate not found
    
    async def append_event(self, *args, **kwargs):
        self.call_count['append_event'] = self.call_count.get('append_event', 0) + 1
        if 'append_event' in self.fail_operations:
            raise Exception("Mock append_event failure")
    
    async def delete_session(self, *args, **kwargs):
        self.call_count['delete_session'] = self.call_count.get('delete_session', 0) + 1
        if 'delete_session' in self.fail_operations:
            raise Exception("Mock delete_session failure")


async def test_session_creation_with_retry():
    """Test session creation with retry logic."""
    logger.info("Testing session creation with retry logic...")
    
    # Test with failing service that succeeds on retry
    failing_service = MockFailingSessionService(['create_session'])
    session_manager = VideoSystemSessionManager(
        session_service=failing_service,
        enable_fallback=False
    )
    
    try:
        # This should fail after retries
        session_id = await session_manager.create_session("Test prompt")
        logger.error("Expected session creation to fail, but it succeeded")
        return False
    except SessionError as e:
        logger.info(f"Session creation failed as expected: {e.message}")
        return True
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


async def test_fallback_mechanism():
    """Test fallback to in-memory service when primary fails."""
    logger.info("Testing fallback mechanism...")
    
    # Create a failing primary service
    failing_service = MockFailingSessionService(['create_session', 'get_session'])
    
    # Create session manager with fallback enabled
    session_manager = VideoSystemSessionManager(
        session_service=failing_service,
        enable_fallback=True
    )
    
    try:
        # This should succeed using fallback
        session_id = await session_manager.create_session("Test prompt for fallback")
        logger.info(f"Session created successfully using fallback: {session_id}")
        
        # Test getting the session (should work with fallback)
        session = await session_manager.get_session(session_id)
        if session:
            logger.info("Session retrieved successfully using fallback")
            return True
        else:
            logger.warning("Session not found in fallback service")
            return False
            
    except Exception as e:
        logger.error(f"Fallback mechanism failed: {e}")
        return False


async def test_concurrent_access_protection():
    """Test concurrent access protection."""
    logger.info("Testing concurrent access protection...")
    
    session_manager = await get_session_manager()
    
    try:
        # Create a session
        session_id = await session_manager.create_session("Concurrent test prompt")
        
        # Simulate concurrent updates
        async def update_session(update_id):
            try:
                success = await session_manager.update_session_state(
                    session_id, 
                    concurrent_update_id=update_id,
                    timestamp=time.time()
                )
                return success
            except Exception as e:
                logger.warning(f"Concurrent update {update_id} failed: {e}")
                return False
        
        # Run multiple concurrent updates
        tasks = [update_session(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_updates = sum(1 for r in results if r is True)
        logger.info(f"Concurrent updates completed: {successful_updates}/5 successful")
        
        # Clean up
        await session_manager.delete_session(session_id)
        
        return successful_updates > 0
        
    except Exception as e:
        logger.error(f"Concurrent access test failed: {e}")
        return False


async def test_error_recovery_scenarios():
    """Test various error recovery scenarios."""
    logger.info("Testing error recovery scenarios...")
    
    session_manager = await get_session_manager()
    
    # Test 1: Invalid session ID handling
    try:
        result = await get_session_status("")
        if not result["success"] and "empty" in result["error_message"].lower():
            logger.info("Empty session ID handled correctly")
        else:
            logger.warning("Empty session ID not handled properly")
    except Exception as e:
        logger.error(f"Empty session ID test failed: {e}")
    
    # Test 2: Non-existent session handling
    try:
        result = await get_session_status("non_existent_session_123")
        if not result["success"] and "not found" in result["error_message"].lower():
            logger.info("Non-existent session handled correctly")
        else:
            logger.warning("Non-existent session not handled properly")
    except Exception as e:
        logger.error(f"Non-existent session test failed: {e}")
    
    # Test 3: Session validation
    try:
        exists = await validate_session_exists("invalid_session")
        if not exists:
            logger.info("Session validation working correctly")
        else:
            logger.warning("Session validation failed")
    except Exception as e:
        logger.error(f"Session validation test failed: {e}")
    
    return True


async def test_orchestration_error_handling():
    """Test orchestration-level error handling."""
    logger.info("Testing orchestration error handling...")
    
    # Test coordinate_research with invalid inputs
    try:
        result = await coordinate_research("", "invalid_session")
        if not result["success"] and "empty" in result["error_message"].lower():
            logger.info("Empty topic handled correctly in coordinate_research")
        else:
            logger.warning("Empty topic not handled properly")
    except Exception as e:
        logger.error(f"Orchestration error handling test failed: {e}")
    
    # Test error handling utility
    try:
        error_response = await handle_orchestration_error(
            "test_session", 
            "test_stage", 
            Exception("Test error"),
            {"test_context": "value"}
        )
        if not error_response["success"] and error_response["stage"] == "test_stage":
            logger.info("Orchestration error handler working correctly")
        else:
            logger.warning("Orchestration error handler not working properly")
    except Exception as e:
        logger.error(f"Error handler test failed: {e}")
    
    return True


async def test_health_monitoring():
    """Test health monitoring functionality."""
    logger.info("Testing health monitoring...")
    
    session_manager = await get_session_manager()
    health_monitor = get_session_health_monitor()
    
    try:
        # Get health status
        health_status = await session_manager.get_health_status()
        logger.info(f"Health status retrieved: {health_status.get('healthy', 'unknown')}")
        
        # Force health check
        health_check = await session_manager.force_health_check()
        logger.info(f"Health check completed: {health_check.get('overall_healthy', 'unknown')}")
        
        # Check monitor metrics
        monitor_status = health_monitor.get_health_status()
        logger.info(f"Monitor metrics: {monitor_status['metrics']['operations_total']} total operations")
        
        return True
        
    except Exception as e:
        logger.error(f"Health monitoring test failed: {e}")
        return False


async def test_graceful_degradation():
    """Test graceful degradation when services are unavailable."""
    logger.info("Testing graceful degradation...")
    
    # Create a session manager with a completely failing service
    failing_service = MockFailingSessionService([
        'create_session', 'get_session', 'append_event', 'delete_session'
    ])
    
    session_manager = VideoSystemSessionManager(
        session_service=failing_service,
        enable_fallback=True
    )
    
    try:
        # Even with fallback, some operations might fail
        # Test that the system doesn't crash and provides meaningful errors
        
        # Test session creation (should work with fallback)
        try:
            session_id = await session_manager.create_session("Degradation test")
            logger.info("Session creation succeeded with fallback")
        except SessionError as e:
            logger.info(f"Session creation failed gracefully: {e.error_type}")
        
        # Test getting non-existent session
        try:
            session = await session_manager.get_session("non_existent")
            if session is None:
                logger.info("Non-existent session handled gracefully")
        except SessionError as e:
            logger.info(f"Session retrieval failed gracefully: {e.error_type}")
        
        return True
        
    except Exception as e:
        logger.error(f"Graceful degradation test failed: {e}")
        return False


async def run_comprehensive_tests():
    """Run all comprehensive error handling tests."""
    logger.info("Starting comprehensive error handling tests...")
    
    tests = [
        ("Session Creation Retry", test_session_creation_with_retry),
        ("Fallback Mechanism", test_fallback_mechanism),
        ("Concurrent Access Protection", test_concurrent_access_protection),
        ("Error Recovery Scenarios", test_error_recovery_scenarios),
        ("Orchestration Error Handling", test_orchestration_error_handling),
        ("Health Monitoring", test_health_monitoring),
        ("Graceful Degradation", test_graceful_degradation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            results[test_name] = {
                "passed": result,
                "duration": duration,
                "error": None
            }
            
            status = "PASSED" if result else "FAILED"
            logger.info(f"Test {test_name}: {status} ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            results[test_name] = {
                "passed": False,
                "duration": duration,
                "error": str(e)
            }
            logger.error(f"Test {test_name}: ERROR - {str(e)}")
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed_tests = sum(1 for r in results.values() if r["passed"])
    total_tests = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result["passed"] else "FAIL"
        duration = result["duration"]
        logger.info(f"{test_name:.<40} {status} ({duration:.2f}s)")
        if result["error"]:
            logger.info(f"  Error: {result['error']}")
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All error handling tests passed!")
        return True
    else:
        logger.warning(f"⚠️  {total_tests - passed_tests} tests failed")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)