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

"""Tests for concurrent processing and resource management functionality."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from video_system.shared_libraries import (
    ConcurrentProcessor,
    ResourceManager,
    VideoGenerationRequest,
    RequestPriority,
    ProcessorStatus,
    ResourceLimits,
    ResourceThresholds,
    LoadTestConfig,
    LoadTestType,
    get_load_tester,
    initialize_concurrent_processor,
    initialize_resource_manager,
    initialize_rate_limiter,
)


class TestConcurrentProcessor:
    """Test cases for the ConcurrentProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a test processor instance."""
        limits = ResourceLimits(
            max_concurrent_requests=3,
            max_queue_size=10,
            max_memory_usage_percent=80.0,
            max_cpu_usage_percent=85.0,
        )
        return ConcurrentProcessor(limits, check_interval=1.0)

    @pytest.fixture
    def sample_request(self):
        """Create a sample video generation request."""
        return VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60,
            style="professional",
            quality="high",
        )

    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.status == ProcessorStatus.STOPPED
        assert processor.resource_limits.max_concurrent_requests == 3
        assert processor.resource_limits.max_queue_size == 10
        assert len(processor.active_tasks) == 0
        assert processor.request_queue.qsize() == 0

    def test_processor_start_stop(self, processor):
        """Test processor start and stop functionality."""
        # Test start
        assert processor.start()
        assert processor.status == ProcessorStatus.RUNNING
        assert processor.executor is not None

        # Test start when already running
        assert not processor.start()

        # Test stop
        assert processor.stop()
        assert processor.status == ProcessorStatus.STOPPED

        # Test stop when already stopped
        assert processor.stop()

    def test_submit_request(self, processor, sample_request):
        """Test request submission."""
        processor.start()

        try:
            # Submit request
            request_id = processor.submit_request(sample_request, user_id="test_user")
            assert request_id is not None
            assert isinstance(request_id, str)

            # Check queue
            assert processor.request_queue.qsize() == 1

            # Check metrics
            metrics = processor.get_metrics()
            assert metrics.total_requests_queued == 1
            assert metrics.current_queue_size == 1

        finally:
            processor.stop()

    def test_submit_request_when_stopped(self, processor, sample_request):
        """Test request submission when processor is stopped."""
        with pytest.raises(Exception):  # Should raise ProcessingError
            processor.submit_request(sample_request)

    def test_queue_capacity(self, processor, sample_request):
        """Test queue capacity limits."""
        processor.start()

        try:
            # Fill queue to capacity
            for i in range(processor.resource_limits.max_queue_size):
                processor.submit_request(sample_request, user_id=f"user_{i}")

            # Next request should fail
            with pytest.raises(Exception):  # Should raise ProcessingError
                processor.submit_request(sample_request, user_id="overflow_user")

        finally:
            processor.stop()

    def test_request_priority(self, processor, sample_request):
        """Test request priority handling."""
        processor.start()

        try:
            # Submit requests with different priorities
            processor.submit_request(sample_request, priority=RequestPriority.NORMAL)
            processor.submit_request(sample_request, priority=RequestPriority.HIGH)
            processor.submit_request(sample_request, priority=RequestPriority.URGENT)

            # Check that requests are queued
            assert processor.request_queue.qsize() == 3

            # Higher priority requests should be processed first
            # (This is tested implicitly through the priority queue implementation)

        finally:
            processor.stop()

    def test_get_request_status(self, processor, sample_request):
        """Test request status retrieval."""
        processor.start()

        try:
            request_id = processor.submit_request(sample_request, user_id="test_user")

            # Initially should be queued
            status = processor.get_request_status(request_id)
            assert status is not None
            assert status["status"] == "queued"
            assert status["request_id"] == request_id

        finally:
            processor.stop()

    def test_resource_usage_monitoring(self, processor):
        """Test resource usage monitoring."""
        usage = processor.get_resource_usage()

        assert "system" in usage
        assert "process" in usage
        assert "limits" in usage
        assert "status" in usage

        assert "cpu_percent" in usage["system"]
        assert "memory_percent" in usage["system"]
        assert "disk_percent" in usage["system"]

    def test_metrics_collection(self, processor):
        """Test metrics collection."""
        metrics = processor.get_metrics()

        assert metrics.total_requests_processed >= 0
        assert metrics.total_requests_failed >= 0
        assert metrics.total_requests_queued >= 0
        assert metrics.current_active_tasks >= 0
        assert metrics.current_queue_size >= 0
        assert metrics.uptime_seconds >= 0.0
        assert isinstance(metrics.last_updated, datetime)

    def test_pause_resume(self, processor):
        """Test processor pause and resume functionality."""
        processor.start()

        try:
            # Test pause
            assert processor.pause()
            assert processor.status == ProcessorStatus.PAUSED

            # Test pause when already paused
            assert not processor.pause()

            # Test resume
            assert processor.resume()
            assert processor.status == ProcessorStatus.RUNNING

            # Test resume when already running
            assert not processor.resume()

        finally:
            processor.stop()


class TestResourceManager:
    """Test cases for the ResourceManager."""

    @pytest.fixture
    def resource_manager(self):
        """Create a test resource manager instance."""
        thresholds = ResourceThresholds(
            cpu_warning=50.0,
            cpu_critical=70.0,
            memory_warning=60.0,
            memory_critical=80.0,
        )
        return ResourceManager(thresholds, monitoring_interval=1.0)

    def test_resource_manager_initialization(self, resource_manager):
        """Test resource manager initialization."""
        assert resource_manager.thresholds.cpu_warning == 50.0
        assert resource_manager.thresholds.cpu_critical == 70.0
        assert resource_manager.monitoring_interval == 1.0
        assert not resource_manager.monitoring_active
        assert len(resource_manager.usage_history) == 0
        assert len(resource_manager.active_alerts) == 0

    def test_start_stop_monitoring(self, resource_manager):
        """Test monitoring start and stop."""
        # Test start
        assert resource_manager.start_monitoring()
        assert resource_manager.monitoring_active
        assert resource_manager.monitor_thread is not None

        # Test start when already running
        assert not resource_manager.start_monitoring()

        # Test stop
        assert resource_manager.stop_monitoring()
        assert not resource_manager.monitoring_active

    def test_get_current_usage(self, resource_manager):
        """Test current usage retrieval."""
        usage = resource_manager.get_current_usage()

        assert isinstance(usage.timestamp, datetime)
        assert usage.cpu_percent >= 0.0
        assert usage.memory_percent >= 0.0
        assert usage.disk_percent >= 0.0
        assert usage.memory_available_gb >= 0.0
        assert usage.disk_free_gb >= 0.0

    def test_resource_allocation(self, resource_manager):
        """Test resource allocation and deallocation."""
        # Allocate resources
        allocation_id = resource_manager.allocate_resources(
            session_id="test_session",
            cpu_cores=2.0,
            memory_mb=1024.0,
            disk_mb=500.0,
            priority=1,
        )

        assert allocation_id is not None
        assert allocation_id in resource_manager.allocations

        allocation = resource_manager.allocations[allocation_id]
        assert allocation.session_id == "test_session"
        assert allocation.cpu_cores == 2.0
        assert allocation.memory_mb == 1024.0
        assert allocation.active

        # Deallocate resources
        assert resource_manager.deallocate_resources(allocation_id)
        assert allocation_id not in resource_manager.allocations

        # Try to deallocate non-existent allocation
        assert not resource_manager.deallocate_resources("non_existent")

    def test_resource_availability(self, resource_manager):
        """Test resource availability checking."""
        availability = resource_manager.get_resource_availability()

        assert "cpu" in availability
        assert "memory" in availability
        assert "disk" in availability
        assert "gpu" in availability
        assert "network" in availability

        # Check CPU availability
        cpu_info = availability["cpu"]
        assert "total_cores" in cpu_info
        assert "allocated_cores" in cpu_info
        assert "available_cores" in cpu_info
        assert "usage_percent" in cpu_info

    def test_can_allocate_resources(self, resource_manager):
        """Test resource allocation feasibility check."""
        # Should be able to allocate reasonable resources
        can_allocate, reason = resource_manager.can_allocate_resources(
            cpu_cores=1.0, memory_mb=512.0, disk_mb=100.0
        )
        assert can_allocate
        assert reason == "Resources available"

        # Should not be able to allocate excessive resources
        can_allocate, reason = resource_manager.can_allocate_resources(
            cpu_cores=1000.0,  # Excessive CPU
            memory_mb=512.0,
            disk_mb=100.0,
        )
        assert not can_allocate
        assert "Insufficient CPU cores" in reason

    def test_usage_history(self, resource_manager):
        """Test usage history tracking."""
        # Start monitoring to generate history
        resource_manager.start_monitoring()

        try:
            # Wait for some usage data
            time.sleep(2.0)

            # Get history
            history = resource_manager.get_usage_history(hours=1)
            assert len(history) > 0

            # Check that history entries are properly formatted
            for usage in history:
                assert isinstance(usage.timestamp, datetime)
                assert usage.cpu_percent >= 0.0
                assert usage.memory_percent >= 0.0

        finally:
            resource_manager.stop_monitoring()

    def test_garbage_collection(self, resource_manager):
        """Test forced garbage collection."""
        gc_results = resource_manager.force_garbage_collection()

        assert "memory_before_mb" in gc_results
        assert "memory_after_mb" in gc_results
        assert "memory_freed_mb" in gc_results
        assert "objects_collected" in gc_results

        assert gc_results["memory_before_mb"] >= 0.0
        assert gc_results["memory_after_mb"] >= 0.0
        assert gc_results["objects_collected"] >= 0

    def test_resource_optimization(self, resource_manager):
        """Test resource optimization."""
        # Add some usage history first
        resource_manager.start_monitoring()
        time.sleep(1.0)
        resource_manager.stop_monitoring()

        optimization_results = resource_manager.optimize_resources()

        assert "garbage_collection" in optimization_results
        assert "history_cleanup" in optimization_results
        assert "alert_cleanup" in optimization_results

        gc_results = optimization_results["garbage_collection"]
        assert "memory_freed_mb" in gc_results
        assert "objects_collected" in gc_results


class TestRateLimiter:
    """Test cases for the RateLimiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a test rate limiter instance."""
        return initialize_rate_limiter()

    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        assert len(rate_limiter.service_limits) > 0
        assert "serper_api" in rate_limiter.service_limits
        assert "pexels_api" in rate_limiter.service_limits
        assert "gemini_api" in rate_limiter.service_limits

    def test_check_rate_limit(self, rate_limiter):
        """Test rate limit checking."""
        # First request should be allowed
        allowed, delay = rate_limiter.check_rate_limit(
            "serper_api", user_id="test_user"
        )
        assert allowed
        assert delay == 0.0

        # Record the request
        rate_limiter.record_request(
            "serper_api", user_id="test_user", success=True, response_time_ms=100.0
        )

    def test_service_status(self, rate_limiter):
        """Test service status retrieval."""
        status = rate_limiter.get_service_status("serper_api")
        assert status is not None
        assert status.service_name == "serper_api"
        assert status.current_rps >= 0.0
        assert status.allowed_rps > 0.0
        assert status.tokens_available >= 0.0

    def test_all_service_status(self, rate_limiter):
        """Test all service status retrieval."""
        all_status = rate_limiter.get_all_service_status()
        assert isinstance(all_status, dict)
        assert len(all_status) > 0
        assert "serper_api" in all_status

    def test_statistics(self, rate_limiter):
        """Test rate limiting statistics."""
        # Record some requests
        rate_limiter.record_request("serper_api", success=True, response_time_ms=100.0)
        rate_limiter.record_request("pexels_api", success=True, response_time_ms=200.0)
        rate_limiter.record_request(
            "gemini_api", success=False, response_time_ms=5000.0
        )

        stats = rate_limiter.get_statistics()

        assert "total_requests_last_hour" in stats
        assert "rate_limited_requests" in stats
        assert "success_rate" in stats
        assert "service_statistics" in stats

        assert stats["total_requests_last_hour"] >= 3
        assert stats["success_rate"] >= 0.0
        assert stats["success_rate"] <= 100.0


@pytest.mark.asyncio
class TestLoadTester:
    """Test cases for the LoadTester."""

    @pytest.fixture
    def load_tester(self):
        """Create a test load tester instance."""
        return get_load_tester()

    @pytest.fixture
    def test_config(self):
        """Create a test load test configuration."""
        return LoadTestConfig(
            test_name="test_load_test",
            test_type=LoadTestType.CONSTANT_LOAD,
            duration_seconds=10,  # Short duration for testing
            max_concurrent_users=2,
            ramp_up_seconds=2,
            requests_per_user=1,
            think_time_seconds=0.5,
            timeout_seconds=30.0,
        )

    def test_load_tester_initialization(self, load_tester):
        """Test load tester initialization."""
        assert len(load_tester.active_tests) == 0
        assert len(load_tester.test_history) == 0
        assert load_tester.resource_manager is not None
        assert load_tester.rate_limiter is not None

    async def test_constant_load_test(self, load_tester, test_config):
        """Test constant load test execution."""
        # Mock the concurrent processor to avoid actual video processing
        with patch(
            "video_system.shared_libraries.concurrent_processor.get_concurrent_processor"
        ) as mock_processor:
            mock_instance = Mock()
            mock_instance.submit_request.return_value = "test_request_id"
            mock_instance.get_request_status.return_value = {
                "status": "completed",
                "request_id": "test_request_id",
            }
            mock_processor.return_value = mock_instance

            # Run the load test
            metrics = await load_tester.run_load_test(test_config)

            assert metrics.test_name == "test_load_test"
            assert metrics.test_type == LoadTestType.CONSTANT_LOAD
            assert metrics.total_requests >= 0
            assert metrics.phase.value in ["completed", "failed"]

    def test_get_test_status(self, load_tester):
        """Test test status retrieval."""
        # Should return None for non-existent test
        status = load_tester.get_test_status("non_existent_test")
        assert status is None

    def test_get_all_test_results(self, load_tester):
        """Test all test results retrieval."""
        results = load_tester.get_all_test_results()
        assert isinstance(results, list)

    def test_export_test_results(self, load_tester, tmp_path):
        """Test test results export."""
        # Should return False for non-existent test
        export_path = tmp_path / "test_results.json"
        success = load_tester.export_test_results("non_existent_test", str(export_path))
        assert not success


class TestIntegration:
    """Integration tests for concurrent processing components."""

    def test_processor_with_resource_manager(self):
        """Test processor integration with resource manager."""
        # Initialize components
        resource_manager = initialize_resource_manager()
        processor = initialize_concurrent_processor()

        # Start monitoring
        resource_manager.start_monitoring()
        processor.start()

        try:
            # Test that they work together
            usage = resource_manager.get_current_usage()
            assert usage is not None

            processor_usage = processor.get_resource_usage()
            assert processor_usage is not None

            # Both should report similar system metrics
            assert (
                abs(usage.cpu_percent - processor_usage["system"]["cpu_percent"]) < 10.0
            )

        finally:
            processor.stop()
            resource_manager.stop_monitoring()

    def test_rate_limiter_with_processor(self):
        """Test rate limiter integration with processor."""
        rate_limiter = initialize_rate_limiter()
        processor = initialize_concurrent_processor()

        processor.start()

        try:
            # Check rate limits before submitting requests
            allowed, delay = rate_limiter.check_rate_limit(
                "video_processing", user_id="test_user"
            )
            assert allowed

            # Submit a request
            request = VideoGenerationRequest(
                prompt="Test video", duration_preference=30, style="professional"
            )

            request_id = processor.submit_request(request, user_id="test_user")
            assert request_id is not None

            # Record the request in rate limiter
            rate_limiter.record_request(
                "video_processing", user_id="test_user", success=True
            )

        finally:
            processor.stop()

    @pytest.mark.asyncio
    async def test_load_tester_with_all_components(self):
        """Test load tester integration with all components."""
        # Initialize all components
        resource_manager = initialize_resource_manager()
        initialize_rate_limiter()
        processor = initialize_concurrent_processor()
        load_tester = get_load_tester()

        # Start components
        resource_manager.start_monitoring()
        processor.start()

        try:
            # Create a minimal load test
            config = LoadTestConfig(
                test_name="integration_test",
                test_type=LoadTestType.CONSTANT_LOAD,
                duration_seconds=5,
                max_concurrent_users=1,
                requests_per_user=1,
                timeout_seconds=10.0,
            )

            # Mock the processor to avoid actual processing
            with (
                patch.object(processor, "submit_request") as mock_submit,
                patch.object(processor, "get_request_status") as mock_status,
            ):
                mock_submit.return_value = "test_request_id"
                mock_status.return_value = {
                    "status": "completed",
                    "request_id": "test_request_id",
                }

                # Run load test
                metrics = await load_tester.run_load_test(config)

                assert metrics.test_name == "integration_test"
                assert metrics.phase.value in ["completed", "failed"]

        finally:
            processor.stop()
            resource_manager.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__])
