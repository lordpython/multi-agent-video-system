#!/usr/bin/env python3
"""Basic test script for session management functionality."""

import tempfile
import shutil
from video_system.shared_libraries import (
    SessionManager,
    ProgressMonitor,
    MaintenanceManager,
    VideoGenerationRequest,
    VideoStatus,
    SessionStage,
)


def test_basic_session_functionality():
    """Test basic session management functionality."""
    print("Testing basic session management functionality...")

    # Create temporary storage
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")

    try:
        # Initialize session manager
        session_manager = SessionManager(storage_path=temp_dir)

        # Create a video generation request
        request = VideoGenerationRequest(
            prompt="Create an educational video about machine learning basics",
            duration_preference=90,
            style="educational",
        )

        # Create session
        session_id = session_manager.create_session(request, user_id="test_user")
        print(f"Created session: {session_id}")

        # Get session
        session = session_manager.get_session(session_id)
        print(
            f"Session status: {session.status}, stage: {session.stage}, progress: {session.progress}"
        )

        # Update session status
        session_manager.update_session_status(
            session_id=session_id,
            status=VideoStatus.PROCESSING,
            stage=SessionStage.RESEARCHING,
            progress=0.25,
        )

        # Get updated session
        session = session_manager.get_session(session_id)
        print(
            f"Updated session status: {session.status}, stage: {session.stage}, progress: {session.progress}"
        )

        # Test progress monitoring
        progress_monitor = ProgressMonitor(session_manager)
        progress_monitor.start_session_monitoring(session_id)

        # Advance through stages
        stages = [
            SessionStage.SCRIPTING,
            SessionStage.ASSET_SOURCING,
            SessionStage.AUDIO_GENERATION,
        ]
        for stage in stages:
            progress_monitor.advance_to_stage(session_id, stage)
            progress_monitor.update_stage_progress(session_id, stage, 0.8)
            print(f"Advanced to stage: {stage}")

        # Get progress info
        progress_info = progress_monitor.get_session_progress(session_id)
        print(f"Overall progress: {progress_info['overall_progress']:.2f}")

        # Complete session
        progress_monitor.complete_session(session_id, success=True)

        # Verify completion
        session = session_manager.get_session(session_id)
        print(f"Final session status: {session.status}, progress: {session.progress}")

        # Test maintenance
        maintenance_manager = MaintenanceManager(session_manager, temp_dir=temp_dir)
        health = maintenance_manager.get_system_health()
        print(
            f"System health - Sessions: {health.total_sessions}, Disk usage: {health.disk_usage_percent:.1f}%"
        )

        # Get statistics
        stats = session_manager.get_statistics()
        print(f"Session statistics: {stats}")

        print("✅ All basic tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Cleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    test_basic_session_functionality()
