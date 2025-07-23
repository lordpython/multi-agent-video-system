#!/usr/bin/env python3
"""Comprehensive integration tests for ADK SessionService.

This script provides comprehensive testing of the ADK SessionService integration
including all session operations, event-based state updates, session listing,
cleanup, error handling, and recovery scenarios.

Test Coverage:
- Session creation, retrieval, update, and deletion
- Event-based state updates using append_event()
- Session listing and pagination
- Session cleanup and maintenance
- Error handling and recovery scenarios
- Concurrent access protection
- Performance and reliability metrics
- Health monitoring and alerting
- Migration from legacy sessions
- Agent function integration
- CLI and API integration
- End-to-end workflow validation
"""

import asyncio
import logging
import os
import sys
import time
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import video system modules
from video_system.utils.adk_session_manager import (
    VideoSystemSessionManager,
    get_session_manager,
)
from video_system.utils.adk_session_models import (
    VideoGenerationStage,
    SessionMetadata,
)
from video_system.utils.models import (
    VideoGenerationRequest,
    ResearchData,
)
from video_system.utils.session_error_handling import (
    SessionError,
)
from video_system.utils.session_migration import SessionMigrationManager
from video_system.tools import orchestration_tools
from video_system.agents.video_orchestrator import agent
from google.adk.sessions import InMemorySessionService, BaseSessionService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockFailingSessionService(BaseSessionService):
    """Mock session service that fails operations for testing error scenarios."""

    def __init__(self, fail_operations: Optional[List[str]] = None):
        self.fail_operations = fail_operations or []
        self.call_count = {}
        self.sessions = {}

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        state: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ):
        self.call_count["create_session"] = self.call_count.get("create_session", 0) + 1
        if "create_session" in self.fail_operations:
            raise Exception("Mock create_session failure")

        # Create mock session
        from google.adk.sessions.session import Session

        session = Session(
            id=session_id or f"mock_session_{time.time()}",
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
            last_update_time=time.time(),
        )
        self.sessions[session.id] = session
        return session

    async def get_session(self, app_name: str, user_id: str, session_id: str):
        self.call_count["get_session"] = self.call_count.get("get_session", 0) + 1
        if "get_session" in self.fail_operations:
            raise Exception("Mock get_session failure")
        return self.sessions.get(session_id)

    async def append_event(self, session, event):
        self.call_count["append_event"] = self.call_count.get("append_event", 0) + 1
        if "append_event" in self.fail_operations:
            raise Exception("Mock append_event failure")
        session.events.append(event)
        if event.actions and event.actions.state_delta:
            session.state.update(event.actions.state_delta)

    async def delete_session(self, app_name: str, user_id: str, session_id: str):
        self.call_count["delete_session"] = self.call_count.get("delete_session", 0) + 1
        if "delete_session" in self.fail_operations:
            raise Exception("Mock delete_session failure")
        self.sessions.pop(session_id, None)

    async def list_sessions(self, app_name: str, user_id: str):
        self.call_count["list_sessions"] = self.call_count.get("list_sessions", 0) + 1
        if "list_sessions" in self.fail_operations:
            raise Exception("Mock list_sessions failure")
        return [
            s
            for s in self.sessions.values()
            if s.app_name == app_name and s.user_id == user_id
        ]


async def test_session_creation_and_retrieval():
    """Test comprehensive session creation and retrieval operations."""
    logger.info("🔧 Testing Session Creation and Retrieval...")

    session_manager = VideoSystemSessionManager(
        session_service=InMemorySessionService(), run_migration_check=False
    )

    try:
        # Test 1: Basic session creation
        request = VideoGenerationRequest(
            prompt="Test video about AI innovation",
            duration_preference=60,
            style="professional",
            voice_preference="natural",
        )

        session_id = await session_manager.create_session(
            request, user_id="test_user_1"
        )
        assert session_id is not None, "Session ID should not be None"
        logger.info(f"✓ Created session: {session_id}")

        # Test 2: Session retrieval
        session = await session_manager.get_session(session_id)
        assert session is not None, "Session should be retrievable"
        assert session.id == session_id, "Session ID should match"
        logger.info(f"✓ Retrieved session: {session.id}")

        # Test 3: Session state retrieval
        state = await session_manager.get_session_state(session_id)
        assert state is not None, "Session state should exist"
        assert state.current_stage == VideoGenerationStage.INITIALIZING, (
            "Initial stage should be INITIALIZING"
        )
        assert state.progress == 0.0, "Initial progress should be 0.0"
        logger.info(
            f"✓ Session state: stage={state.current_stage}, progress={state.progress}"
        )

        # Test 4: Session status
        status = await session_manager.get_session_status(session_id)
        assert status is not None, "Session status should exist"
        assert status.session_id == session_id, "Status session ID should match"
        logger.info(f"✓ Session status: {status.status}")

        # Test 5: Multiple sessions for same user
        session_id_2 = await session_manager.create_session(
            request, user_id="test_user_1"
        )
        assert session_id_2 != session_id, (
            "Different sessions should have different IDs"
        )
        logger.info(f"✓ Created second session: {session_id_2}")

        # Clean up
        await session_manager.delete_session(session_id)
        await session_manager.delete_session(session_id_2)

        return True

    except Exception as e:
        logger.error(f"Session creation/retrieval test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def test_event_based_state_updates():
    """Test event-based state updates using ADK's append_event mechanism."""
    logger.info("📝 Testing Event-Based State Updates...")

    session_manager = VideoSystemSessionManager(
        session_service=InMemorySessionService(), run_migration_check=False
    )

    try:
        # Create session
        request = VideoGenerationRequest(prompt="Event test video")
        session_id = await session_manager.create_session(request, user_id="event_user")

        # Test 1: Stage and progress updates
        success = await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.RESEARCHING, 0.25
        )
        assert success, "Stage update should succeed"

        # Verify event was created
        session = await session_manager.get_session(session_id)
        assert len(session.events) > 1, (
            "Should have initial creation event plus update event"
        )

        # Find the update event
        update_events = [
            e for e in session.events if e.actions and e.actions.state_delta
        ]
        assert len(update_events) > 0, "Should have at least one state update event"

        latest_event = update_events[-1]
        assert (
            latest_event.actions.state_delta.get("current_stage")
            == VideoGenerationStage.RESEARCHING.value
        )
        assert latest_event.actions.state_delta.get("progress") == 0.25
        logger.info("✓ Event-based stage update verified")

        # Test 2: Complex state updates with research data
        research_data = ResearchData(
            facts=["Fact 1", "Fact 2"],
            sources=["Source 1"],
            key_points=["Key point 1"],
            context={"test": True},
        )

        success = await session_manager.update_session_state(
            session_id,
            research_data=research_data,
            current_stage=VideoGenerationStage.SCRIPTING,
            progress=0.5,
            metadata={"test_update": True},
        )
        assert success, "Complex state update should succeed"

        # Verify complex update event
        session = await session_manager.get_session(session_id)
        update_events = [
            e for e in session.events if e.actions and e.actions.state_delta
        ]
        latest_event = update_events[-1]

        assert (
            latest_event.actions.state_delta.get("current_stage")
            == VideoGenerationStage.SCRIPTING.value
        )
        assert latest_event.actions.state_delta.get("progress") == 0.5
        assert "research_data" in latest_event.actions.state_delta
        logger.info("✓ Complex event-based update verified")

        # Test 3: Error state updates
        success = await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            0.5,
            error_message="Test error for event verification",
        )
        assert success, "Error state update should succeed"

        # Verify error event
        session = await session_manager.get_session(session_id)
        state = await session_manager.get_session_state(session_id)
        assert state.current_stage == VideoGenerationStage.FAILED
        assert state.error_message == "Test error for event verification"
        logger.info("✓ Error state event verified")

        # Test 4: Intermediate file tracking
        test_file = "/tmp/test_intermediate_file.mp4"
        success = await session_manager.add_intermediate_file(session_id, test_file)
        assert success, "Adding intermediate file should succeed"

        state = await session_manager.get_session_state(session_id)
        assert test_file in state.intermediate_files, (
            "Intermediate file should be tracked"
        )
        logger.info("✓ Intermediate file tracking verified")

        # Clean up
        await session_manager.delete_session(session_id)

        return True

    except Exception as e:
        logger.error(f"Event-based state updates test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def test_session_listing_and_pagination():
    """Test session listing functionality with pagination."""
    logger.info("📋 Testing Session Listing and Pagination...")

    session_manager = VideoSystemSessionManager(
        session_service=InMemorySessionService(), run_migration_check=False
    )

    try:
        # Create multiple sessions for different users
        user1_sessions = []
        user2_sessions = []

        # Create 5 sessions for user1
        for i in range(5):
            request = VideoGenerationRequest(prompt=f"User1 video {i}")
            session_id = await session_manager.create_session(
                request, user_id="list_user_1"
            )
            user1_sessions.append(session_id)

            # Set different stages
            if i % 2 == 0:
                await session_manager.update_stage_and_progress(
                    session_id, VideoGenerationStage.COMPLETED, 1.0
                )
            else:
                await session_manager.update_stage_and_progress(
                    session_id, VideoGenerationStage.RESEARCHING, 0.3
                )

        # Create 3 sessions for user2
        for i in range(3):
            request = VideoGenerationRequest(prompt=f"User2 video {i}")
            session_id = await session_manager.create_session(
                request, user_id="list_user_2"
            )
            user2_sessions.append(session_id)

        # Test 1: List all sessions
        all_sessions = await session_manager.list_sessions()
        assert len(all_sessions) >= 8, (
            f"Should have at least 8 sessions, got {len(all_sessions)}"
        )
        logger.info(f"✓ Listed all sessions: {len(all_sessions)} total")

        # Test 2: List sessions for specific user
        user1_listed = await session_manager.list_sessions(user_id="list_user_1")
        assert len(user1_listed) == 5, (
            f"User1 should have 5 sessions, got {len(user1_listed)}"
        )
        logger.info(f"✓ Listed user1 sessions: {len(user1_listed)}")

        user2_listed = await session_manager.list_sessions(user_id="list_user_2")
        assert len(user2_listed) == 3, (
            f"User2 should have 3 sessions, got {len(user2_listed)}"
        )
        logger.info(f"✓ Listed user2 sessions: {len(user2_listed)}")

        # Test 3: Filter by status
        completed_sessions = await session_manager.list_sessions(
            user_id="list_user_1", status_filter="completed"
        )
        assert len(completed_sessions) >= 2, "Should have completed sessions"
        logger.info(f"✓ Filtered completed sessions: {len(completed_sessions)}")

        processing_sessions = await session_manager.list_sessions(
            user_id="list_user_1", status_filter="processing"
        )
        assert len(processing_sessions) >= 2, "Should have processing sessions"
        logger.info(f"✓ Filtered processing sessions: {len(processing_sessions)}")

        # Test 4: Pagination
        paginated_result = await session_manager.list_sessions_paginated(
            user_id="list_user_1", page_size=2, page=1
        )

        assert paginated_result["pagination"]["total_count"] == 5, "Total should be 5"
        assert len(paginated_result["sessions"]) == 2, "Page should have 2 sessions"
        assert paginated_result["pagination"]["page"] == 1, "Page number should be 1"
        assert paginated_result["pagination"]["total_pages"] == 3, (
            "Should have 3 total pages"
        )
        logger.info("✓ Pagination working correctly")

        # Test 5: Second page
        page2_result = await session_manager.list_sessions_paginated(
            user_id="list_user_1", page_size=2, page=2
        )

        assert len(page2_result["sessions"]) == 2, "Page 2 should have 2 sessions"
        assert page2_result["pagination"]["page"] == 2, "Page number should be 2"
        logger.info("✓ Second page pagination working")

        # Clean up
        for session_id in user1_sessions + user2_sessions:
            await session_manager.delete_session(session_id)

        return True

    except Exception as e:
        logger.error(f"Session listing test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def test_session_cleanup_and_maintenance():
    """Test session cleanup and maintenance functionality."""
    logger.info("🧹 Testing Session Cleanup and Maintenance...")

    session_manager = VideoSystemSessionManager(
        session_service=InMemorySessionService(),
        cleanup_interval=10,  # Short interval for testing
        max_session_age_hours=1,
        run_migration_check=False,
    )

    try:
        # Create test sessions
        recent_session_id = await session_manager.create_session(
            VideoGenerationRequest(prompt="Recent session"), user_id="cleanup_user"
        )

        await session_manager.create_session(
            VideoGenerationRequest(prompt="Old session"), user_id="cleanup_user"
        )

        # Create intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_files = []
            for i in range(3):
                test_file = os.path.join(temp_dir, f"test_file_{i}.tmp")
                with open(test_file, "w") as f:
                    f.write(f"Test content {i}")
                test_files.append(test_file)
                await session_manager.add_intermediate_file(
                    recent_session_id, test_file
                )

            # Test 1: Get cleanup statistics
            cleanup_stats = await session_manager.get_cleanup_statistics()
            assert "sessions_eligible_for_cleanup" in cleanup_stats
            assert "estimated_files_for_cleanup" in cleanup_stats
            logger.info(
                f"✓ Cleanup statistics: {cleanup_stats['sessions_eligible_for_cleanup']} eligible"
            )

            # Test 2: Force cleanup
            cleanup_results = await session_manager.force_cleanup_now()
            assert "sessions_evaluated" in cleanup_results
            assert "duration_seconds" in cleanup_results
            logger.info(
                f"✓ Cleanup completed in {cleanup_results['duration_seconds']:.2f}s"
            )

            # Test 3: Pattern-based file cleanup
            pattern_cleanup = await session_manager.cleanup_session_files_by_pattern(
                "*.tmp"
            )
            assert "cleaned_files" in pattern_cleanup
            logger.info(
                f"✓ Pattern cleanup: {pattern_cleanup['cleaned_files']} files cleaned"
            )

        # Clean up remaining sessions
        await session_manager.delete_session(recent_session_id)

        return True

    except Exception as e:
        logger.error(f"Session cleanup test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def test_error_handling_and_recovery():
    """Test comprehensive error handling and recovery scenarios."""
    logger.info("🚨 Testing Error Handling and Recovery...")

    # Test 1: Service unavailable scenarios
    failing_service = MockFailingSessionService(["create_session"])
    session_manager = VideoSystemSessionManager(
        session_service=failing_service, enable_fallback=True, run_migration_check=False
    )

    try:
        # This should use fallback service
        request = VideoGenerationRequest(prompt="Fallback test")
        session_id = await session_manager.create_session(request, user_id="error_user")
        assert session_id is not None, "Should succeed with fallback"
        logger.info("✓ Fallback mechanism working")

        # Test 2: Session not found handling
        non_existent_session = await session_manager.get_session("non_existent_session")
        assert non_existent_session is None, "Non-existent session should return None"
        logger.info("✓ Non-existent session handled correctly")

        # Test 3: Invalid session ID handling
        try:
            await session_manager.update_session_state("", test_update=True)
            assert False, "Empty session ID should raise error"
        except (SessionError, ValueError):
            logger.info("✓ Empty session ID handled correctly")

        # Test 4: Concurrent access protection
        async def concurrent_update(update_id):
            try:
                return await session_manager.update_session_state(
                    session_id, concurrent_update_id=update_id, timestamp=time.time()
                )
            except Exception:
                return False

        # Run concurrent updates
        tasks = [concurrent_update(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_updates = sum(1 for r in results if r is True)
        logger.info(f"✓ Concurrent updates: {successful_updates}/5 successful")

        # Test 5: Health monitoring
        health_status = await session_manager.get_health_status()
        assert "session_manager" in health_status
        logger.info("✓ Health monitoring working")

        health_check = await session_manager.force_health_check()
        assert "overall_healthy" in health_check
        assert "checks" in health_check
        logger.info(f"✓ Health check: {health_check['overall_healthy']}")

        return True

    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def test_performance_and_monitoring():
    """Test performance metrics and monitoring capabilities."""
    logger.info("📊 Testing Performance and Monitoring...")

    session_manager = VideoSystemSessionManager(
        session_service=InMemorySessionService(), run_migration_check=False
    )

    try:
        # Create test sessions with different outcomes
        completed_sessions = []
        failed_sessions = []
        active_sessions = []

        # Create completed sessions
        for i in range(3):
            request = VideoGenerationRequest(prompt=f"Completed video {i}")
            session_id = await session_manager.create_session(request, f"perf_user_{i}")
            completed_sessions.append(session_id)
            await session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.COMPLETED, 1.0
            )

        # Create failed sessions
        for i in range(2):
            request = VideoGenerationRequest(prompt=f"Failed video {i}")
            session_id = await session_manager.create_session(request, f"fail_user_{i}")
            failed_sessions.append(session_id)
            await session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.FAILED, 0.5, "Test failure"
            )

        # Create active sessions
        for i in range(4):
            request = VideoGenerationRequest(prompt=f"Active video {i}")
            session_id = await session_manager.create_session(
                request, f"active_user_{i}"
            )
            active_sessions.append(session_id)
            await session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.RESEARCHING, 0.3
            )

        # Test 1: Comprehensive statistics
        stats = await session_manager.get_statistics()

        # Verify structure
        assert "session_counts" in stats
        assert "performance_metrics" in stats
        assert "reliability_metrics" in stats
        assert "throughput_metrics" in stats

        session_counts = stats["session_counts"]
        assert session_counts["total"] == 9
        assert session_counts["completed"] == 3
        assert session_counts["failed"] == 2
        assert session_counts["active"] == 4
        logger.info(f"✓ Statistics: {session_counts['total']} total sessions")

        # Test 2: Performance metrics
        perf_metrics = await session_manager.get_performance_metrics()
        assert "performance_status" in perf_metrics
        assert "thresholds" in perf_metrics
        assert "metrics_summary" in perf_metrics
        logger.info(f"✓ Performance status: {perf_metrics['performance_status']}")

        # Test 3: Monitoring dashboard data
        dashboard_data = await session_manager.get_monitoring_dashboard_data()
        assert "overview" in dashboard_data
        assert "session_metrics" in dashboard_data
        assert "health_status" in dashboard_data

        overview = dashboard_data["overview"]
        assert overview["total_sessions"] == 9
        assert overview["active_sessions"] == 4
        logger.info(f"✓ Dashboard data: {overview['success_rate']:.1%} success rate")

        # Test 4: Legacy compatibility
        session_metadata = await session_manager.get_session_metadata()
        assert isinstance(session_metadata, SessionMetadata)
        assert session_metadata.total_sessions == 9
        assert session_metadata.completed_sessions == 3
        logger.info("✓ Legacy compatibility maintained")

        # Clean up
        all_sessions = completed_sessions + failed_sessions + active_sessions
        for session_id in all_sessions:
            await session_manager.delete_session(session_id)

        return True

    except Exception as e:
        logger.error(f"Performance and monitoring test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def test_migration_integration():
    """Test migration from legacy sessions to ADK sessions."""
    logger.info("🔄 Testing Migration Integration...")

    try:
        # Create a migration manager
        migration_manager = SessionMigrationManager()

        # Test 1: Check migration status
        migration_status = await migration_manager.get_migration_status()
        assert "migration_completed" in migration_status
        logger.info(f"✓ Migration status: {migration_status['migration_completed']}")

        # Test 2: Create session manager with migration
        session_manager = VideoSystemSessionManager(
            session_service=InMemorySessionService(), run_migration_check=True
        )

        # Verify migration was checked
        assert hasattr(session_manager, "migration_completed")
        logger.info("✓ Migration check completed during initialization")

        # Test 3: Create session after migration
        request = VideoGenerationRequest(prompt="Post-migration test")
        session_id = await session_manager.create_session(
            request, user_id="migration_user"
        )
        assert session_id is not None
        logger.info(f"✓ Session created after migration: {session_id}")

        # Clean up
        await session_manager.delete_session(session_id)
        await session_manager.close()

        return True

    except Exception as e:
        logger.error(f"Migration integration test failed: {e}")
        return False


async def test_agent_function_integration():
    """Test integration with agent functions."""
    logger.info("🤖 Testing Agent Function Integration...")

    try:
        # Test 1: Agent session creation
        result = await agent.start_video_generation(
            prompt="Agent integration test video", user_id="agent_test_user"
        )

        assert result.get("success") is True, "Agent should create session successfully"
        session_id = result.get("session_id")
        assert session_id is not None, "Agent should return session ID"
        logger.info(f"✓ Agent created session: {session_id}")

        # Test 2: Workflow execution
        workflow_result = await agent.execute_complete_workflow(session_id)
        assert "session_id" in workflow_result, "Workflow should return session ID"
        logger.info("✓ Workflow execution started successfully")

        # Test 3: Session visibility across components
        session_manager = await get_session_manager()
        session = await session_manager.get_session(session_id)
        assert session is not None, "Session should be visible to session manager"
        logger.info("✓ Session visible across components")

        # Clean up
        await session_manager.delete_session(session_id)
        await session_manager.close()

        return True

    except Exception as e:
        logger.error(f"Agent function integration test failed: {e}")
        return False


async def test_orchestration_integration():
    """Test integration with orchestration tools."""
    logger.info("🎼 Testing Orchestration Integration...")

    try:
        # Test 1: Create session through orchestration
        request = VideoGenerationRequest(prompt="Orchestration test video")
        session_id = await orchestration_tools.create_session_state(
            request, user_id="orch_user"
        )
        assert session_id is not None, "Orchestration should create session"
        logger.info(f"✓ Orchestration created session: {session_id}")

        # Test 2: Update session through orchestration
        session_manager = await get_session_manager()
        success = await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.RESEARCHING, 0.25
        )
        assert success, "Orchestration should update session progress"
        logger.info("✓ Orchestration updated session progress")

        # Test 3: Get session state through orchestration
        state = await session_manager.get_session_state(session_id)
        assert state is not None, "Orchestration should retrieve session state"
        assert state.current_stage == VideoGenerationStage.RESEARCHING
        logger.info("✓ Orchestration retrieved session state")

        # Test 4: Session visibility
        session_manager = await get_session_manager()
        session = await session_manager.get_session(session_id)
        assert session is not None, "Session should be visible to session manager"
        logger.info("✓ Session visible across orchestration and session manager")

        # Clean up
        await session_manager.delete_session(session_id)
        await session_manager.close()

        return True

    except Exception as e:
        logger.error(f"Orchestration integration test failed: {e}")
        return False


async def test_end_to_end_workflow():
    """Test complete end-to-end workflow with ADK sessions."""
    logger.info("🔄 Testing End-to-End Workflow...")

    try:
        # Test 1: Start video generation
        result = await agent.start_video_generation(
            prompt="End-to-end test video about AI innovation",
            duration_preference=30,
            style="professional",
            voice_preference="natural",
            user_id="e2e_user",
        )

        assert result.get("success") is True, (
            "Video generation should start successfully"
        )
        session_id = result.get("session_id")
        logger.info(f"✓ Started video generation: {session_id}")

        # Test 2: Execute workflow
        workflow_result = await agent.execute_complete_workflow(session_id)
        assert workflow_result.get("success") is True, (
            "Workflow should execute successfully"
        )
        logger.info("✓ Workflow execution initiated")

        # Test 3: Monitor progress through session manager
        session_manager = await get_session_manager()

        # Wait a moment for initial processing
        await asyncio.sleep(0.5)

        session_status = await session_manager.get_session_status(session_id)
        assert session_status is not None, "Should be able to get session status"
        logger.info(f"✓ Session status: {session_status.status}")

        # Test 4: Verify event tracking
        session = await session_manager.get_session(session_id)
        assert len(session.events) > 0, "Session should have events"
        logger.info(f"✓ Session has {len(session.events)} events")

        # Test 5: Verify state updates
        state = await session_manager.get_session_state(session_id)
        assert state is not None, "Session should have state"
        assert state.current_stage != VideoGenerationStage.INITIALIZING, (
            "Stage should have progressed"
        )
        logger.info(f"✓ Session progressed to stage: {state.current_stage}")

        # Clean up
        await session_manager.delete_session(session_id)
        await session_manager.close()

        return True

    except Exception as e:
        logger.error(f"End-to-end workflow test failed: {e}")
        return False


async def test_advanced_error_scenarios():
    """Test advanced error handling scenarios."""
    logger.info("🚨 Testing Advanced Error Scenarios...")

    try:
        # Test 1: Service unavailable with fallback
        failing_service = MockFailingSessionService(["create_session", "get_session"])
        session_manager = VideoSystemSessionManager(
            session_service=failing_service,
            enable_fallback=True,
            run_migration_check=False,
        )

        # Should succeed with fallback
        request = VideoGenerationRequest(prompt="Fallback test")
        session_id = await session_manager.create_session(
            request, user_id="fallback_user"
        )
        assert session_id is not None, "Should succeed with fallback"
        logger.info("✓ Fallback mechanism working")

        # Test 2: Concurrent session operations
        async def concurrent_operation(op_id):
            try:
                return await session_manager.update_session_state(
                    session_id, concurrent_op=op_id, timestamp=time.time()
                )
            except Exception:
                return False

        tasks = [concurrent_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_ops = sum(1 for r in results if r is True)
        logger.info(f"✓ Concurrent operations: {successful_ops}/10 successful")

        # Test 3: Session corruption recovery
        try:
            # Simulate corrupted session data
            await session_manager.update_session_state(
                "corrupted_session_id", test=True
            )
        except (SessionError, ValueError):
            logger.info("✓ Corrupted session handled correctly")

        # Test 4: Resource exhaustion simulation
        large_sessions = []
        try:
            for i in range(50):  # Create many sessions quickly
                req = VideoGenerationRequest(prompt=f"Load test {i}")
                sid = await session_manager.create_session(req, f"load_user_{i}")
                large_sessions.append(sid)
            logger.info(f"✓ Created {len(large_sessions)} sessions under load")
        except Exception as e:
            logger.info(f"✓ Resource limits handled: {str(e)[:50]}...")

        # Clean up
        for sid in large_sessions:
            try:
                await session_manager.delete_session(sid)
            except Exception:
                pass

        await session_manager.close()

        return True

    except Exception as e:
        logger.error(f"Advanced error scenarios test failed: {e}")
        return False


async def test_performance_under_load():
    """Test performance under various load conditions."""
    logger.info("⚡ Testing Performance Under Load...")

    session_manager = VideoSystemSessionManager(
        session_service=InMemorySessionService(), run_migration_check=False
    )

    try:
        # Test 1: Session creation performance
        start_time = time.time()
        session_ids = []

        for i in range(20):
            request = VideoGenerationRequest(prompt=f"Performance test {i}")
            session_id = await session_manager.create_session(request, f"perf_user_{i}")
            session_ids.append(session_id)

        creation_time = time.time() - start_time
        avg_creation_time = creation_time / 20
        logger.info(
            f"✓ Average session creation time: {avg_creation_time * 1000:.2f}ms"
        )

        # Verify performance requirement (should be < 100ms)
        assert avg_creation_time < 0.1, (
            f"Creation time {avg_creation_time:.3f}s exceeds 100ms limit"
        )

        # Test 2: Session retrieval performance
        start_time = time.time()

        for session_id in session_ids:
            session = await session_manager.get_session(session_id)
            assert session is not None

        retrieval_time = time.time() - start_time
        avg_retrieval_time = retrieval_time / len(session_ids)
        logger.info(
            f"✓ Average session retrieval time: {avg_retrieval_time * 1000:.2f}ms"
        )

        # Verify performance requirement (should be < 50ms)
        assert avg_retrieval_time < 0.05, (
            f"Retrieval time {avg_retrieval_time:.3f}s exceeds 50ms limit"
        )

        # Test 3: Bulk operations performance
        start_time = time.time()

        # Update all sessions
        update_tasks = []
        for session_id in session_ids:
            task = session_manager.update_stage_and_progress(
                session_id, VideoGenerationStage.RESEARCHING, 0.1
            )
            update_tasks.append(task)

        await asyncio.gather(*update_tasks)
        bulk_update_time = time.time() - start_time
        logger.info(
            f"✓ Bulk update time for {len(session_ids)} sessions: {bulk_update_time:.2f}s"
        )

        # Test 4: Memory usage monitoring
        stats = await session_manager.get_statistics()
        session_count = stats.get("session_counts", {}).get("total", 0)
        assert session_count >= 20, "Should track all created sessions"
        logger.info(f"✓ Memory tracking: {session_count} sessions tracked")

        # Clean up
        for session_id in session_ids:
            await session_manager.delete_session(session_id)

        return True

    except Exception as e:
        logger.error(f"Performance under load test failed: {e}")
        return False
    finally:
        await session_manager.close()


async def run_comprehensive_integration_tests():
    """Run all comprehensive integration tests."""
    logger.info("🚀 Starting Comprehensive ADK SessionService Integration Tests")
    logger.info("=" * 80)

    tests = [
        ("Session Creation and Retrieval", test_session_creation_and_retrieval),
        ("Event-Based State Updates", test_event_based_state_updates),
        ("Session Listing and Pagination", test_session_listing_and_pagination),
        ("Session Cleanup and Maintenance", test_session_cleanup_and_maintenance),
        ("Error Handling and Recovery", test_error_handling_and_recovery),
        ("Performance and Monitoring", test_performance_and_monitoring),
        ("Migration Integration", test_migration_integration),
        ("Agent Function Integration", test_agent_function_integration),
        ("Orchestration Integration", test_orchestration_integration),
        ("End-to-End Workflow", test_end_to_end_workflow),
        ("Advanced Error Scenarios", test_advanced_error_scenarios),
        ("Performance Under Load", test_performance_under_load),
    ]

    results = {}
    total_start_time = time.time()

    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'=' * 60}")

        start_time = time.time()
        try:
            result = await test_func()
            duration = time.time() - start_time

            results[test_name] = {"passed": result, "duration": duration, "error": None}

            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status} ({duration:.2f}s)")

        except Exception as e:
            duration = time.time() - start_time
            results[test_name] = {
                "passed": False,
                "duration": duration,
                "error": str(e),
            }
            logger.error(f"{test_name}: ❌ ERROR - {str(e)}")

    total_duration = time.time() - total_start_time

    # Print comprehensive summary
    logger.info(f"\n{'=' * 80}")
    logger.info("🏁 COMPREHENSIVE TEST SUMMARY")
    logger.info(f"{'=' * 80}")

    passed_tests = sum(1 for r in results.values() if r["passed"])
    total_tests = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        duration = result["duration"]
        logger.info(f"{test_name:<40} {status} ({duration:.2f}s)")
        if result["error"]:
            logger.info(f"  └─ Error: {result['error']}")

    logger.info(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    logger.info(f"⏱️  Total execution time: {total_duration:.2f}s")

    # Generate detailed test report
    test_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": total_tests - passed_tests,
        "total_duration": total_duration,
        "test_results": results,
        "coverage_areas": [
            "Session CRUD operations",
            "Event-based state management",
            "Session listing and pagination",
            "Cleanup and maintenance",
            "Error handling and recovery",
            "Performance monitoring",
            "Migration integration",
            "Agent function integration",
            "Orchestration integration",
            "End-to-end workflows",
            "Advanced error scenarios",
            "Performance under load",
        ],
    }

    # Save test report
    report_path = "test_integration_report.json"
    try:
        with open(report_path, "w") as f:
            json.dump(test_report, f, indent=2)
        logger.info(f"📄 Test report saved to: {report_path}")
    except Exception as e:
        logger.warning(f"Could not save test report: {e}")

    if passed_tests == total_tests:
        logger.info("🎉 All integration tests passed successfully!")
        logger.info("✅ ADK SessionService integration is fully validated")
        return True
    else:
        logger.warning(f"⚠️  {total_tests - passed_tests} tests failed")
        logger.warning("❌ ADK SessionService integration needs attention")
        return False


async def main():
    """Main entry point for comprehensive integration tests."""
    try:
        success = await run_comprehensive_integration_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
