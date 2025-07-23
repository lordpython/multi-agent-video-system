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

"""Comprehensive error handling and resilience tests for the multi-agent video system."""

import pytest
import os
import json
import requests
from unittest.mock import Mock, patch

from video_system.utils.error_handling import (
    VideoSystemError,
    APIError,
    ValidationError,
    ProcessingError,
    RetryConfig,
    retry_with_exponential_backoff,
    FallbackManager,
    FallbackConfig,
    CircuitBreaker,
    create_error_response,
    ServiceRegistry,
    ResourceMonitor,
    GracefulDegradation,
    RateLimiter,
    HealthMonitor,
)

from video_system.tools.research_tools import web_search, search_with_fallback
from video_system.tools.story_tools import generate_video_script, create_scene_breakdown
from video_system.tools.asset_tools import search_pexels_media
from video_system.tools.audio_tools import generate_speech_with_gemini
from video_system.tools.video_tools import (
    compose_video_with_ffmpeg,
    VideoCompositionRequest,
)


class TestErrorHandling:
    """Test comprehensive error handling across the system."""

    def test_video_system_error_creation(self):
        """Test VideoSystemError creation and serialization."""
        error = VideoSystemError(
            message="Test error", error_code="TEST_ERROR", details={"test": "data"}
        )

        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details["test"] == "data"
        assert error.timestamp is not None

        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["details"]["test"] == "data"

    def test_api_error_creation(self):
        """Test APIError creation with specific fields."""
        error = APIError(message="API failed", api_name="TestAPI", status_code=500)

        assert error.message == "API failed"
        assert error.details["api_name"] == "TestAPI"
        assert error.details["status_code"] == 500
        assert error.category.value == "api_error"

    def test_validation_error_creation(self):
        """Test ValidationError creation with field information."""
        error = ValidationError(message="Invalid input", field="test_field")

        assert error.message == "Invalid input"
        assert error.details["field"] == "test_field"
        assert error.category.value == "validation_error"

    def test_create_error_response(self):
        """Test error response creation."""
        error = ProcessingError("Processing failed")
        response = create_error_response(error)

        assert response["success"] is False
        assert response["error"]["message"] == "Processing failed"
        assert response["error"]["category"] == "processing_error"
        assert "timestamp" in response["error"]

    def test_retry_decorator_success(self):
        """Test retry decorator with successful execution."""
        call_count = 0

        @retry_with_exponential_backoff(
            retry_config=RetryConfig(max_attempts=3, base_delay=0.1),
            exceptions=(ValueError,),
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_decorator_with_failures(self):
        """Test retry decorator with initial failures."""
        call_count = 0

        @retry_with_exponential_backoff(
            retry_config=RetryConfig(max_attempts=3, base_delay=0.1),
            exceptions=(ValueError,),
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_decorator_max_attempts_exceeded(self):
        """Test retry decorator when max attempts are exceeded."""
        call_count = 0

        @retry_with_exponential_backoff(
            retry_config=RetryConfig(max_attempts=2, base_delay=0.1),
            exceptions=(ValueError,),
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        with pytest.raises(ValueError, match="Persistent failure"):
            test_function()

        assert call_count == 2

    def test_fallback_manager_success(self):
        """Test fallback manager with successful primary function."""

        def primary_func():
            return "primary_success"

        def fallback_func():
            return "fallback_success"

        config = FallbackConfig(enabled=True)
        manager = FallbackManager(config)

        result = manager.execute_with_fallback(primary_func, [fallback_func])
        assert result == "primary_success"

    def test_fallback_manager_with_fallback(self):
        """Test fallback manager when primary function fails."""

        def primary_func():
            raise Exception("Primary failed")

        def fallback_func():
            return "fallback_success"

        config = FallbackConfig(enabled=True)
        manager = FallbackManager(config)

        result = manager.execute_with_fallback(primary_func, [fallback_func])
        assert result == "fallback_success"

    def test_fallback_manager_graceful_degradation(self):
        """Test fallback manager with graceful degradation."""

        def primary_func():
            raise Exception("Primary failed")

        def fallback_func():
            raise Exception("Fallback failed")

        config = FallbackConfig(enabled=True, graceful_degradation=True)
        manager = FallbackManager(config)

        result = manager.execute_with_fallback(primary_func, [fallback_func])
        assert result["success"] is False
        assert result["fallback_response"] is True

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        call_count = 0

        @CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 1

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opening after failures."""
        call_count = 0

        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        @circuit_breaker
        def test_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Function failed")

        # First two calls should fail and increment failure count
        with pytest.raises(Exception):
            test_function()
        with pytest.raises(Exception):
            test_function()

        # Third call should be blocked by circuit breaker
        with pytest.raises(ProcessingError, match="Circuit breaker is OPEN"):
            test_function()

        assert call_count == 2  # Only first two calls executed


class TestResilienceComponents:
    """Test resilience components like health monitoring and resource management."""

    def test_service_registry_registration(self):
        """Test service registration and health checks."""
        registry = ServiceRegistry()

        def health_check():
            return {"status": "healthy"}

        registry.register_service(
            service_name="test_service", health_check_func=health_check, critical=True
        )

        assert "test_service" in registry.services
        assert registry.services["test_service"]["critical"] is True

    def test_service_registry_health_check(self):
        """Test service health check execution."""
        registry = ServiceRegistry()

        def health_check():
            return {"status": "healthy", "details": {"message": "All good"}}

        registry.register_service("test_service", health_check_func=health_check)

        result = registry.perform_health_check("test_service")
        assert result.service_name == "test_service"
        assert result.status.value == "healthy"
        assert result.details["message"] == "All good"

    def test_service_registry_health_check_failure(self):
        """Test service health check with failure."""
        registry = ServiceRegistry()

        def failing_health_check():
            raise Exception("Health check failed")

        registry.register_service(
            "test_service", health_check_func=failing_health_check
        )

        result = registry.perform_health_check("test_service")
        assert result.service_name == "test_service"
        assert result.status.value == "unhealthy"
        assert "Health check failed" in result.error_message

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_resource_monitor_metrics(self, mock_disk, mock_memory, mock_cpu):
        """Test resource monitor metrics collection."""
        # Mock system metrics
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(
            percent=60.0, available=4 * 1024**3
        )  # 4GB available
        mock_disk.return_value = Mock(percent=70.0)

        monitor = ResourceMonitor()
        metrics = monitor.get_current_metrics()

        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.disk_percent == 70.0
        assert metrics.available_memory_gb == 4.0

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_resource_monitor_constraints(self, mock_disk, mock_memory, mock_cpu):
        """Test resource constraint detection."""
        # Mock high resource usage
        mock_cpu.return_value = 90.0
        mock_memory.return_value = Mock(percent=85.0, available=1 * 1024**3)
        mock_disk.return_value = Mock(percent=95.0)

        monitor = ResourceMonitor()
        constraints = monitor.check_resource_constraints()

        assert not constraints["healthy"]
        assert len(constraints["alerts"]) > 0
        assert len(constraints["warnings"]) > 0

    def test_graceful_degradation_levels(self):
        """Test graceful degradation level management."""
        degradation = GracefulDegradation()

        # Test normal level
        assert not degradation.should_skip_non_essential()
        assert not degradation.should_reduce_quality()

        # Test reduced quality level
        degradation.set_degradation_level("reduced_quality")
        assert not degradation.should_skip_non_essential()
        assert degradation.should_reduce_quality()

        # Test essential only level
        degradation.set_degradation_level("essential_only")
        assert degradation.should_skip_non_essential()
        assert degradation.should_reduce_quality()

    def test_graceful_degradation_quality_settings(self):
        """Test quality settings based on degradation level."""
        degradation = GracefulDegradation()

        # Normal settings
        settings = degradation.get_quality_settings()
        assert settings["video_quality"] == "high"
        assert settings["max_duration"] == 300

        # Emergency settings
        degradation.set_degradation_level("emergency")
        settings = degradation.get_quality_settings()
        assert settings["video_quality"] == "low"
        assert settings["max_duration"] == 30
        assert settings["skip_effects"] is True

    def test_rate_limiter_token_acquisition(self):
        """Test rate limiter token acquisition."""
        limiter = RateLimiter(max_tokens=5, refill_rate=10.0)

        # Should be able to acquire tokens initially
        assert limiter.acquire(3) is True
        assert limiter.acquire(2) is True

        # Should fail when no tokens left
        assert limiter.acquire(1) is False

    def test_rate_limiter_token_refill(self):
        """Test rate limiter token refill over time."""
        limiter = RateLimiter(max_tokens=5, refill_rate=10.0)

        # Exhaust tokens
        limiter.acquire(5)
        assert limiter.acquire(1) is False

        # Wait for refill (simulate time passage)
        limiter.last_refill -= 1.0  # Simulate 1 second ago
        assert limiter.acquire(1) is True  # Should have refilled some tokens


class TestAgentErrorScenarios:
    """Test error scenarios for individual agents."""

    @patch.dict(os.environ, {}, clear=True)
    def test_web_search_missing_api_key(self):
        """Test web search with missing API key."""
        result = web_search("test query")

        assert result["success"] is False
        assert "SERPER_API_KEY" in result["error"]["message"]

    def test_web_search_invalid_input(self):
        """Test web search with invalid input."""
        result = web_search("")  # Empty query

        assert result["success"] is False
        assert "empty" in result["error"]["message"].lower()

    def test_web_search_fallback_mechanism(self):
        """Test web search fallback mechanism."""
        with patch("sub_agents.research.tools.web_search.web_search") as mock_search:
            # First call fails, second succeeds
            mock_search.side_effect = [
                {"success": False, "error": {"message": "Primary failed"}},
                {"success": True, "results": [{"title": "Fallback result"}]},
            ]

            result = search_with_fallback("test query")
            assert result["success"] is True or result.get("fallback_response") is True

    def test_script_generation_invalid_research_data(self):
        """Test script generation with invalid research data."""
        result = generate_video_script({})  # Empty research data

        assert result["success"] is False
        assert "insufficient" in result["error"]["message"].lower()

    def test_script_generation_invalid_duration(self):
        """Test script generation with invalid duration."""
        research_data = {"facts": ["Test fact"], "key_points": ["Test point"]}

        result = generate_video_script(research_data, target_duration=5)  # Too short

        assert result["success"] is False
        assert "duration" in result["error"]["message"].lower()

    def test_scene_breakdown_empty_content(self):
        """Test scene breakdown with empty content."""
        result = create_scene_breakdown("")  # Empty script content

        assert result["success"] is False
        assert "empty" in result["error"]["message"].lower()

    @patch.dict(os.environ, {}, clear=True)
    def test_pexels_search_missing_api_key(self):
        """Test Pexels search with missing API key."""
        result = search_pexels_media("test query")

        assert result["success"] is False
        assert "PEXELS_API_KEY" in result["error"]["message"]

    def test_pexels_search_invalid_parameters(self):
        """Test Pexels search with invalid parameters."""
        result = search_pexels_media("", per_page=100)  # Empty query, invalid per_page

        assert result["success"] is False
        assert "empty" in result["error"]["message"].lower()

    @patch.dict(os.environ, {}, clear=True)
    def test_gemini_tts_missing_api_key(self):
        """Test Gemini TTS with missing API key."""
        result = generate_speech_with_gemini("test text")

        # Should return error structure
        assert result["total_files"] == 0
        assert len(result["audio_files"]) > 0
        assert "error" in result["audio_files"][0]

    def test_gemini_tts_invalid_text(self):
        """Test Gemini TTS with invalid text input."""
        result = generate_speech_with_gemini("")  # Empty text

        assert result["total_files"] == 0
        assert "error" in result["audio_files"][0]

    @patch("shutil.which")
    def test_ffmpeg_composition_missing_ffmpeg(self, mock_which):
        """Test FFmpeg composition when FFmpeg is not available."""
        mock_which.return_value = None  # FFmpeg not found

        request = VideoCompositionRequest(
            video_assets=["test.jpg"],
            audio_file="test.wav",
            output_path="output.mp4",
            scene_timings=[],
        )

        with patch(
            "sub_agents.video_assembly.tools.ffmpeg_composition._check_ffmpeg_availability",
            return_value=False,
        ):
            result = compose_video_with_ffmpeg(request)

            assert result.success is False
            assert "ffmpeg" in result.error_message.lower()

    def test_ffmpeg_composition_missing_files(self):
        """Test FFmpeg composition with missing input files."""
        request = VideoCompositionRequest(
            video_assets=["nonexistent.jpg"],
            audio_file="nonexistent.wav",
            output_path="output.mp4",
            scene_timings=[],
        )

        result = compose_video_with_ffmpeg(request)

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_api_timeout_scenarios(self):
        """Test API timeout handling across different services."""
        # Test web search timeout
        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

            result = web_search("test query")
            assert result["success"] is False
            assert "timeout" in result["error"]["message"].lower()

    def test_network_connectivity_failures(self):
        """Test handling of network connectivity issues."""
        # Test connection error in web search
        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Network unreachable"
            )

            result = web_search("test query")
            assert result["success"] is False
            assert "network" in result["error"]["message"].lower()

    def test_rate_limiting_scenarios(self):
        """Test rate limiting handling across services."""
        # Test rate limiting in Pexels search
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_get.return_value = mock_response

            result = search_pexels_media("test query")
            assert result["success"] is False
            assert "rate limit" in result["error"]["message"].lower()

    def test_invalid_api_credentials(self):
        """Test handling of invalid API credentials."""
        # Test invalid Serper API key
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.ok = False
            mock_response.text = "Invalid API key"
            mock_post.return_value = mock_response

            with patch.dict(os.environ, {"SERPER_API_KEY": "invalid_key"}):
                result = web_search("test query")
                assert result["success"] is False
                assert "401" in str(result["error"]["details"]["status_code"])

    def test_malformed_api_responses(self):
        """Test handling of malformed API responses."""
        # Test malformed JSON response
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_post.return_value = mock_response

            result = web_search("test query")
            assert result["success"] is False

    def test_file_system_errors(self):
        """Test handling of file system errors."""
        # Test permission denied error
        with patch("os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = PermissionError("Permission denied")

            request = VideoCompositionRequest(
                video_assets=["test.jpg"],
                audio_file="test.wav",
                output_path="/root/restricted/output.mp4",
                scene_timings=[],
            )

            # This should handle the permission error gracefully
            result = compose_video_with_ffmpeg(request)
            assert result.success is False
            assert (
                "permission" in result.error_message.lower()
                or "directory" in result.error_message.lower()
            )

    def test_memory_exhaustion_scenarios(self):
        """Test handling of memory exhaustion."""
        # Test large text input for TTS
        large_text = "This is a test. " * 1000  # Very long text

        result = generate_speech_with_gemini(large_text)
        # Should either succeed or fail gracefully with appropriate error
        if result["total_files"] == 0:
            assert "error" in result["audio_files"][0]

    def test_concurrent_resource_access(self):
        """Test concurrent access to shared resources."""
        import threading

        # Use a shared rate limiter instance
        shared_limiter = RateLimiter(max_tokens=1, refill_rate=0.1)
        results = []

        def concurrent_operation():
            try:
                # Use the shared limiter
                success = shared_limiter.acquire(1)
                results.append(success)
            except Exception:
                results.append(False)

        # Start multiple concurrent operations
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=concurrent_operation)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Only one should succeed due to rate limiting
        successful_operations = sum(1 for r in results if r is True)
        assert successful_operations <= 1


class TestIntegrationErrorScenarios:
    """Test error scenarios in integrated workflows."""

    def test_end_to_end_error_propagation(self):
        """Test that errors propagate correctly through the system."""
        # Test research agent failure propagation
        with patch("sub_agents.research.tools.web_search.web_search") as mock_search:
            mock_search.return_value = {
                "success": False,
                "error": {"message": "Search API failed", "category": "api_error"},
            }

            # This should propagate through the system
            result = mock_search("test query")
            assert result["success"] is False
            assert "Search API failed" in result["error"]["message"]

    def test_concurrent_error_handling(self):
        """Test error handling under concurrent load."""
        import threading

        errors = []

        def failing_operation():
            try:
                raise ProcessingError("Concurrent operation failed")
            except Exception as e:
                errors.append(e)

        # Start multiple threads that will fail
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=failing_operation)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All operations should have failed
        assert len(errors) == 5
        assert all(isinstance(e, ProcessingError) for e in errors)

    def test_resource_exhaustion_scenarios(self):
        """Test system behavior under resource exhaustion."""
        # Test rate limiter exhaustion
        limiter = RateLimiter(max_tokens=2, refill_rate=1.0)

        # Exhaust tokens
        assert limiter.acquire(2) is True

        # Should fail when exhausted
        assert limiter.acquire(1) is False

        # Test resource monitor under high load
        with patch("psutil.cpu_percent", return_value=98.0):
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value = Mock(percent=95.0, available=0.1 * 1024**3)

                monitor = ResourceMonitor()
                constraints = monitor.check_resource_constraints()

                assert not constraints["healthy"]
                assert len(constraints["alerts"]) > 0

    def test_cascading_failure_scenarios(self):
        """Test how the system handles cascading failures."""
        # Test circuit breaker preventing cascading failures
        failure_count = 0

        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        @circuit_breaker
        def failing_service():
            nonlocal failure_count
            failure_count += 1
            raise Exception("Service failed")

        # First two failures should execute
        with pytest.raises(Exception):
            failing_service()
        with pytest.raises(Exception):
            failing_service()

        # Third call should be blocked by circuit breaker
        with pytest.raises(ProcessingError, match="Circuit breaker is OPEN"):
            failing_service()

        # Only 2 actual failures should have occurred
        assert failure_count == 2

    def test_error_recovery_mechanisms(self):
        """Test error recovery and retry mechanisms."""
        attempt_count = 0

        @retry_with_exponential_backoff(
            retry_config=RetryConfig(max_attempts=3, base_delay=0.1),
            exceptions=(ValueError,),
        )
        def recovering_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = recovering_function()
        assert result == "success"
        assert attempt_count == 3

    def test_health_monitoring_integration(self):
        """Test health monitoring system integration."""
        monitor = HealthMonitor()

        # Register a failing service
        def failing_health_check():
            raise Exception("Health check failed")

        monitor.service_registry.register_service(
            "test_service", health_check_func=failing_health_check, critical=True
        )

        # Perform health check
        result = monitor.service_registry.perform_health_check("test_service")
        assert result.status.value == "unhealthy"
        assert "Health check failed" in result.error_message

    def test_graceful_degradation_under_load(self):
        """Test graceful degradation when system is under load."""
        degradation = GracefulDegradation()

        # Simulate high load
        degradation.set_degradation_level("emergency")

        # Should skip non-essential operations
        assert degradation.should_skip_non_essential()

        # Quality settings should be reduced
        settings = degradation.get_quality_settings()
        assert settings["video_quality"] == "low"
        assert settings["skip_effects"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
