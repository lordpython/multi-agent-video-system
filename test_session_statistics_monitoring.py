#!/usr/bin/env python3
"""
Test script for enhanced session statistics and monitoring functionality.

This script tests the comprehensive statistics collection, performance metrics,
health monitoring, and alerting capabilities added to VideoSystemSessionManager.
"""

import asyncio

from video_system.shared_libraries.adk_session_manager import VideoSystemSessionManager
from video_system.shared_libraries.models import VideoGenerationRequest
from video_system.shared_libraries.adk_session_models import VideoGenerationStage
from google.adk.sessions import InMemorySessionService


async def test_enhanced_statistics():
    """Test the enhanced get_statistics() method."""
    print("🔍 Testing Enhanced Session Statistics...")

    # Initialize session manager with in-memory service
    session_service = InMemorySessionService()
    session_manager = VideoSystemSessionManager(
        session_service=session_service, run_migration_check=False
    )

    try:
        # Create test sessions with different states
        test_sessions = []

        # Create completed sessions
        for i in range(3):
            request = VideoGenerationRequest(
                prompt=f"Test completed video {i}", duration_preference=30
            )
            session_id = await session_manager.create_session(request, f"user_{i}")
            test_sessions.append(session_id)

            # Simulate completion
            await session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.COMPLETED, 1.0
            )

            # Add some delay to simulate processing time
            await asyncio.sleep(0.1)

        # Create failed sessions
        for i in range(2):
            request = VideoGenerationRequest(
                prompt=f"Test failed video {i}", duration_preference=30
            )
            session_id = await session_manager.create_session(request, f"user_fail_{i}")
            test_sessions.append(session_id)

            # Simulate failure
            await session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.FAILED, 0.5, error_message="Test error"
            )

        # Create active sessions
        for i in range(4):
            request = VideoGenerationRequest(
                prompt=f"Test active video {i}", duration_preference=30
            )
            session_id = await session_manager.create_session(
                request, f"user_active_{i}"
            )
            test_sessions.append(session_id)

            # Set to processing
            await session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.RESEARCHING, 0.2
            )

        # Wait a moment for timestamps to differentiate
        await asyncio.sleep(0.2)

        # Get comprehensive statistics
        print("📊 Collecting comprehensive statistics...")
        stats = await session_manager.get_statistics()

        # Verify basic counts
        session_counts = stats.get("session_counts", {})
        assert session_counts.get("total") == 9, (
            f"Expected 9 total sessions, got {session_counts.get('total')}"
        )
        assert session_counts.get("completed") == 3, (
            f"Expected 3 completed sessions, got {session_counts.get('completed')}"
        )
        assert session_counts.get("failed") == 2, (
            f"Expected 2 failed sessions, got {session_counts.get('failed')}"
        )
        assert session_counts.get("active") == 4, (
            f"Expected 4 active sessions, got {session_counts.get('active')}"
        )

        # Verify performance metrics exist
        performance_metrics = stats.get("performance_metrics", {})
        assert "completion_times" in performance_metrics
        assert "processing_times" in performance_metrics
        assert "session_ages" in performance_metrics

        completion_times = performance_metrics["completion_times"]
        assert completion_times.get("sample_size") == 3, (
            "Should have 3 completed sessions for timing"
        )
        assert completion_times.get("average_seconds") is not None

        # Verify reliability metrics
        reliability_metrics = stats.get("reliability_metrics", {})
        expected_error_rate = 2 / 9  # 2 failed out of 9 total
        actual_error_rate = reliability_metrics.get("overall_error_rate", 0)
        assert abs(actual_error_rate - expected_error_rate) < 0.01, (
            f"Expected error rate ~{expected_error_rate:.2f}, got {actual_error_rate:.2f}"
        )

        expected_success_rate = 1.0 - expected_error_rate
        actual_success_rate = reliability_metrics.get("success_rate", 0)
        assert abs(actual_success_rate - expected_success_rate) < 0.01, (
            f"Expected success rate ~{expected_success_rate:.2f}, got {actual_success_rate:.2f}"
        )

        # Verify throughput metrics
        throughput_metrics = stats.get("throughput_metrics", {})
        assert throughput_metrics.get("sessions_last_hour") == 9, (
            "All sessions should be within last hour"
        )
        assert throughput_metrics.get("sessions_last_day") == 9, (
            "All sessions should be within last day"
        )

        # Verify distribution metrics
        distribution_metrics = stats.get("distribution_metrics", {})
        stage_distribution = distribution_metrics.get("stage_distribution", {})
        assert stage_distribution.get("completed") == 3
        assert stage_distribution.get("failed") == 2
        assert stage_distribution.get("researching") == 4

        # Verify resource metrics exist
        resource_metrics = stats.get("resource_metrics", {})
        assert "session_manager" in resource_metrics
        session_mgr_metrics = resource_metrics["session_manager"]
        assert session_mgr_metrics.get("active_sessions") == 9

        # Verify legacy metadata for backward compatibility
        legacy_metadata = stats.get("legacy_metadata", {})
        assert legacy_metadata.get("total_sessions") == 9
        assert legacy_metadata.get("completed_sessions") == 3
        assert legacy_metadata.get("failed_sessions") == 2

        print("✅ Enhanced statistics test passed!")
        print(f"   - Total sessions: {session_counts.get('total')}")
        print(f"   - Success rate: {reliability_metrics.get('success_rate', 0):.1%}")
        print(
            f"   - Average completion time: {completion_times.get('average_seconds', 0):.2f}s"
        )

        return stats

    finally:
        await session_manager.close()


async def test_performance_metrics():
    """Test performance metrics and alerting."""
    print("\n⚡ Testing Performance Metrics and Alerting...")

    session_service = InMemorySessionService()
    session_manager = VideoSystemSessionManager(
        session_service=session_service, run_migration_check=False
    )

    try:
        # Create sessions to test performance thresholds
        request = VideoGenerationRequest(
            prompt="Performance test video", duration_preference=30
        )
        session_id = await session_manager.create_session(request, "perf_user")

        # Simulate a long-running session
        await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.RESEARCHING, 0.1
        )

        # Get performance metrics
        perf_metrics = await session_manager.get_performance_metrics()

        # Verify structure
        assert "performance_status" in perf_metrics
        assert "thresholds" in perf_metrics
        assert "alerts" in perf_metrics
        assert "metrics_summary" in perf_metrics

        # Verify thresholds are defined
        thresholds = perf_metrics["thresholds"]
        assert "max_completion_time_seconds" in thresholds
        assert "max_error_rate" in thresholds
        assert "min_success_rate" in thresholds

        # Verify metrics summary
        metrics_summary = perf_metrics["metrics_summary"]
        assert "total_sessions" in metrics_summary
        assert "error_rate" in metrics_summary
        assert "success_rate" in metrics_summary

        print("✅ Performance metrics test passed!")
        print(f"   - Performance status: {perf_metrics.get('performance_status')}")
        print(f"   - Alert count: {len(perf_metrics.get('alerts', []))}")

        return perf_metrics

    finally:
        await session_manager.close()


async def test_monitoring_dashboard():
    """Test monitoring dashboard data collection."""
    print("\n📈 Testing Monitoring Dashboard Data...")

    session_service = InMemorySessionService()
    session_manager = VideoSystemSessionManager(
        session_service=session_service, run_migration_check=False
    )

    try:
        # Create a few test sessions
        for i in range(3):
            request = VideoGenerationRequest(
                prompt=f"Dashboard test video {i}", duration_preference=30
            )
            session_id = await session_manager.create_session(request, f"dash_user_{i}")

            if i == 0:
                # Complete one session
                await session_manager.update_stage_and_progress(
                    session_id, VideoGenerationStage.COMPLETED, 1.0
                )
            elif i == 1:
                # Fail one session
                await session_manager.update_stage_and_progress(
                    session_id, VideoGenerationStage.FAILED, 0.3, "Test failure"
                )
            # Leave one active

        # Get dashboard data
        dashboard_data = await session_manager.get_monitoring_dashboard_data()

        # Verify structure
        assert "timestamp" in dashboard_data
        assert "overview" in dashboard_data
        assert "session_metrics" in dashboard_data
        assert "performance_metrics" in dashboard_data
        assert "reliability_metrics" in dashboard_data
        assert "health_status" in dashboard_data
        assert "alerts" in dashboard_data

        # Verify overview data
        overview = dashboard_data["overview"]
        assert overview.get("total_sessions") == 3
        assert overview.get("active_sessions") == 1
        assert "success_rate" in overview
        assert "performance_status" in overview

        print("✅ Monitoring dashboard test passed!")
        print(f"   - Total sessions: {overview.get('total_sessions')}")
        print(f"   - Active sessions: {overview.get('active_sessions')}")
        print(f"   - Success rate: {overview.get('success_rate', 0):.1%}")

        return dashboard_data

    finally:
        await session_manager.close()


async def test_health_monitoring():
    """Test health monitoring capabilities."""
    print("\n🏥 Testing Health Monitoring...")

    session_service = InMemorySessionService()
    session_manager = VideoSystemSessionManager(
        session_service=session_service, run_migration_check=False
    )

    try:
        # Test health status
        health_status = await session_manager.get_health_status()

        # Verify health status structure
        assert "session_manager" in health_status
        session_mgr_health = health_status["session_manager"]
        assert "total_sessions" in session_mgr_health
        assert "primary_service_available" in session_mgr_health
        assert "migration_completed" in session_mgr_health

        # Test force health check
        health_check = await session_manager.force_health_check()

        # Verify health check structure
        assert "timestamp" in health_check
        assert "checks" in health_check
        assert "overall_healthy" in health_check

        # Verify individual checks
        checks = health_check["checks"]
        assert "create_session" in checks
        assert "get_session" in checks
        assert "update_session" in checks
        assert "delete_session" in checks
        assert "list_sessions" in checks

        print("✅ Health monitoring test passed!")
        print(f"   - Overall healthy: {health_check.get('overall_healthy')}")
        print(f"   - Checks performed: {len(checks)}")

        return health_status, health_check

    finally:
        await session_manager.close()


async def test_backward_compatibility():
    """Test backward compatibility with legacy SessionMetadata."""
    print("\n🔄 Testing Backward Compatibility...")

    session_service = InMemorySessionService()
    session_manager = VideoSystemSessionManager(
        session_service=session_service, run_migration_check=False
    )

    try:
        # Create test sessions
        for i in range(2):
            request = VideoGenerationRequest(
                prompt=f"Compatibility test video {i}", duration_preference=30
            )
            session_id = await session_manager.create_session(
                request, f"compat_user_{i}"
            )

            if i == 0:
                await session_manager.update_stage_and_progress(
                    session_id, VideoGenerationStage.COMPLETED, 1.0
                )

        # Test legacy SessionMetadata method
        session_metadata = await session_manager.get_session_metadata()

        # Verify it's a SessionMetadata object
        from video_system.shared_libraries.adk_session_models import SessionMetadata

        assert isinstance(session_metadata, SessionMetadata)

        # Verify basic fields
        assert session_metadata.total_sessions == 2
        assert session_metadata.completed_sessions == 1
        assert session_metadata.active_sessions == 1
        assert session_metadata.failed_sessions == 0

        print("✅ Backward compatibility test passed!")
        print(f"   - Legacy metadata total: {session_metadata.total_sessions}")
        print(f"   - Legacy metadata completed: {session_metadata.completed_sessions}")

        return session_metadata

    finally:
        await session_manager.close()


async def main():
    """Run all statistics and monitoring tests."""
    print("🚀 Starting Session Statistics and Monitoring Tests\n")

    try:
        # Run all tests
        stats = await test_enhanced_statistics()
        await test_performance_metrics()
        await test_monitoring_dashboard()
        health_status, health_check = await test_health_monitoring()
        await test_backward_compatibility()

        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        print("✅ Enhanced Statistics: PASSED")
        print("✅ Performance Metrics: PASSED")
        print("✅ Monitoring Dashboard: PASSED")
        print("✅ Health Monitoring: PASSED")
        print("✅ Backward Compatibility: PASSED")
        print("\n🎉 All session statistics and monitoring tests passed!")

        # Print sample output
        print("\n📊 Sample Statistics Output:")
        print(f"Collection time: {stats.get('collection_time_ms', 0):.2f}ms")
        print(f"Total sessions: {stats.get('session_counts', {}).get('total', 0)}")
        print(
            f"Success rate: {stats.get('reliability_metrics', {}).get('success_rate', 0):.1%}"
        )

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
