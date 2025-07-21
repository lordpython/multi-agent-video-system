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

"""Integration tests for session management functionality."""

import pytest
import tempfile
import shutil
import time
import os
from datetime import datetime, timedelta

from video_system.shared_libraries import (
    SessionManager, ProgressMonitor, MaintenanceManager,
    VideoGenerationRequest, VideoStatus, SessionStage,
    VideoScript, VideoScene
)


class TestSessionManager:
    """Test cases for SessionManager."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def session_manager(self, temp_storage):
        """Create SessionManager instance with temporary storage."""
        return SessionManager(storage_path=temp_storage, cleanup_interval=10)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample video generation request."""
        return VideoGenerationRequest(
            prompt="Create a video about artificial intelligence",
            duration_preference=60,
            style="professional",
            voice_preference="neutral",
            quality="high"
        )
    
    def test_create_session(self, session_manager, sample_request):
        """Test session creation."""
        session_id = session_manager.create_session(sample_request, user_id="test_user")
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID length
        
        # Verify session exists
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == "test_user"
        assert session.request.prompt == sample_request.prompt
        assert session.status == VideoStatus.QUEUED
        assert session.stage == SessionStage.INITIALIZING
        assert session.progress == 0.0
    
    def test_get_project_state(self, session_manager, sample_request):
        """Test project state retrieval."""
        session_id = session_manager.create_session(sample_request)
        
        project_state = session_manager.get_project_state(session_id)
        assert project_state is not None
        assert project_state.session_id == session_id
        assert project_state.research_data is None
        assert project_state.script is None
        assert project_state.intermediate_files == []
    
    def test_update_session_status(self, session_manager, sample_request):
        """Test session status updates."""
        session_id = session_manager.create_session(sample_request)
        
        # Update status
        success = session_manager.update_session_status(
            session_id=session_id,
            status=VideoStatus.PROCESSING,
            stage=SessionStage.RESEARCHING,
            progress=0.25,
            error_message=None
        )
        
        assert success is True
        
        # Verify update
        session = session_manager.get_session(session_id)
        assert session.status == VideoStatus.PROCESSING
        assert session.stage == SessionStage.RESEARCHING
        assert session.progress == 0.25
        assert session.error_message is None
    
    def test_update_project_state(self, session_manager, sample_request):
        """Test project state updates."""
        session_id = session_manager.create_session(sample_request)
        
        # Create sample script
        script = VideoScript(
            title="AI Video",
            total_duration=60.0,
            scenes=[
                VideoScene(
                    scene_number=1,
                    description="Introduction to AI",
                    visual_requirements=["AI graphics", "tech background"],
                    dialogue="Welcome to our AI overview",
                    duration=30.0
                ),
                VideoScene(
                    scene_number=2,
                    description="AI applications",
                    visual_requirements=["application examples"],
                    dialogue="AI has many applications",
                    duration=30.0
                )
            ]
        )
        
        # Update project state
        success = session_manager.update_project_state(
            session_id=session_id,
            script=script,
            research_data={"topic": "AI", "sources": ["source1", "source2"]}
        )
        
        assert success is True
        
        # Verify update
        project_state = session_manager.get_project_state(session_id)
        assert project_state.script is not None
        assert project_state.script.title == "AI Video"
        assert len(project_state.script.scenes) == 2
        assert project_state.research_data["topic"] == "AI"
    
    def test_add_intermediate_file(self, session_manager, sample_request, temp_storage):
        """Test adding intermediate files."""
        session_id = session_manager.create_session(sample_request)
        
        # Create a temporary file
        temp_file = os.path.join(temp_storage, "temp_file.txt")
        with open(temp_file, 'w') as f:
            f.write("test content")
        
        # Add to session
        success = session_manager.add_intermediate_file(session_id, temp_file)
        assert success is True
        
        # Verify file is tracked
        project_state = session_manager.get_project_state(session_id)
        assert temp_file in project_state.intermediate_files
    
    def test_get_session_status(self, session_manager, sample_request):
        """Test getting session status for API responses."""
        session_id = session_manager.create_session(sample_request)
        
        # Update status
        session_manager.update_session_status(
            session_id=session_id,
            status=VideoStatus.PROCESSING,
            stage=SessionStage.SCRIPTING,
            progress=0.5
        )
        
        # Get status
        status = session_manager.get_session_status(session_id)
        assert status is not None
        assert status.session_id == session_id
        assert status.status == VideoStatus.PROCESSING.value
        assert status.current_stage == SessionStage.SCRIPTING.value
        assert status.progress == 0.5
    
    def test_list_sessions(self, session_manager, sample_request):
        """Test listing sessions with filters."""
        # Create multiple sessions
        session1 = session_manager.create_session(sample_request, user_id="user1")
        session2 = session_manager.create_session(sample_request, user_id="user2")
        session3 = session_manager.create_session(sample_request, user_id="user1")
        
        # Update one session status
        session_manager.update_session_status(session2, VideoStatus.COMPLETED)
        
        # Test listing all sessions
        all_sessions = session_manager.list_sessions()
        assert len(all_sessions) == 3
        
        # Test filtering by user
        user1_sessions = session_manager.list_sessions(user_id="user1")
        assert len(user1_sessions) == 2
        
        # Test filtering by status
        completed_sessions = session_manager.list_sessions(status=VideoStatus.COMPLETED)
        assert len(completed_sessions) == 1
        assert completed_sessions[0].session_id == session2
        
        # Test limit
        limited_sessions = session_manager.list_sessions(limit=2)
        assert len(limited_sessions) == 2
    
    def test_delete_session(self, session_manager, sample_request, temp_storage):
        """Test session deletion with file cleanup."""
        session_id = session_manager.create_session(sample_request)
        
        # Add intermediate file
        temp_file = os.path.join(temp_storage, "temp_file.txt")
        with open(temp_file, 'w') as f:
            f.write("test content")
        session_manager.add_intermediate_file(session_id, temp_file)
        
        # Verify file exists
        assert os.path.exists(temp_file)
        
        # Delete session
        success = session_manager.delete_session(session_id, cleanup_files=True)
        assert success is True
        
        # Verify session is gone
        session = session_manager.get_session(session_id)
        assert session is None
        
        # Verify file is cleaned up
        assert not os.path.exists(temp_file)
    
    def test_persistence(self, temp_storage, sample_request):
        """Test session persistence across manager instances."""
        # Create session with first manager
        manager1 = SessionManager(storage_path=temp_storage)
        session_id = manager1.create_session(sample_request, user_id="test_user")
        
        # Update session
        manager1.update_session_status(
            session_id=session_id,
            status=VideoStatus.PROCESSING,
            stage=SessionStage.RESEARCHING,
            progress=0.3
        )
        
        # Create second manager (should load existing sessions)
        manager2 = SessionManager(storage_path=temp_storage)
        
        # Verify session exists in second manager
        session = manager2.get_session(session_id)
        assert session is not None
        assert session.user_id == "test_user"
        assert session.status == VideoStatus.PROCESSING
        assert session.stage == SessionStage.RESEARCHING
        assert session.progress == 0.3
    
    def test_cleanup_expired_sessions(self, session_manager, sample_request):
        """Test cleanup of expired sessions."""
        # Create sessions
        session1 = session_manager.create_session(sample_request)
        session2 = session_manager.create_session(sample_request)
        
        # Mark one as completed and old
        session_manager.update_session_status(session1, VideoStatus.COMPLETED)
        session = session_manager.get_session(session1)
        session.updated_at = datetime.utcnow() - timedelta(hours=50)  # Older than 48 hours
        
        # Run cleanup
        cleaned_count = session_manager.cleanup_expired_sessions(max_age_hours=48)
        
        # Verify cleanup
        assert cleaned_count == 1
        assert session_manager.get_session(session1) is None
        assert session_manager.get_session(session2) is not None
    
    def test_get_statistics(self, session_manager, sample_request):
        """Test getting session statistics."""
        # Create sessions with different statuses
        session1 = session_manager.create_session(sample_request)
        session2 = session_manager.create_session(sample_request)
        session3 = session_manager.create_session(sample_request)
        
        session_manager.update_session_status(session1, VideoStatus.PROCESSING, progress=0.5)
        session_manager.update_session_status(session2, VideoStatus.COMPLETED, progress=1.0)
        session_manager.update_session_status(session3, VideoStatus.PROCESSING, progress=0.3)
        
        # Get statistics
        stats = session_manager.get_statistics()
        
        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 2
        assert stats["status_distribution"]["processing"] == 2
        assert stats["status_distribution"]["completed"] == 1
        assert stats["average_progress"] == 0.4  # (0.5 + 0.3) / 2


class TestProgressMonitor:
    """Test cases for ProgressMonitor."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def session_manager(self, temp_storage):
        """Create SessionManager instance."""
        return SessionManager(storage_path=temp_storage)
    
    @pytest.fixture
    def progress_monitor(self, session_manager):
        """Create ProgressMonitor instance."""
        return ProgressMonitor(session_manager)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample video generation request."""
        return VideoGenerationRequest(
            prompt="Test video",
            duration_preference=60
        )
    
    def test_start_session_monitoring(self, progress_monitor, session_manager, sample_request):
        """Test starting progress monitoring for a session."""
        session_id = session_manager.create_session(sample_request)
        
        success = progress_monitor.start_session_monitoring(session_id)
        assert success is True
        
        # Verify monitoring is active
        active_sessions = progress_monitor.get_active_sessions()
        assert session_id in active_sessions
    
    def test_update_stage_progress(self, progress_monitor, session_manager, sample_request):
        """Test updating stage progress."""
        session_id = session_manager.create_session(sample_request)
        progress_monitor.start_session_monitoring(session_id)
        
        # Update progress
        success = progress_monitor.update_stage_progress(
            session_id=session_id,
            stage=SessionStage.RESEARCHING,
            progress=0.5
        )
        assert success is True
        
        # Verify session status was updated
        session = session_manager.get_session(session_id)
        assert session.status == VideoStatus.PROCESSING
        assert session.stage == SessionStage.RESEARCHING
    
    def test_advance_to_stage(self, progress_monitor, session_manager, sample_request):
        """Test advancing to a new stage."""
        session_id = session_manager.create_session(sample_request)
        progress_monitor.start_session_monitoring(session_id)
        
        # Advance to scripting stage
        success = progress_monitor.advance_to_stage(session_id, SessionStage.SCRIPTING)
        assert success is True
        
        # Verify session was updated
        session = session_manager.get_session(session_id)
        assert session.stage == SessionStage.SCRIPTING
        
        # Verify previous stages are marked complete
        progress_info = progress_monitor.get_session_progress(session_id)
        assert progress_info["stage_details"]["initializing"]["progress"] == 1.0
        assert progress_info["stage_details"]["researching"]["progress"] == 1.0
    
    def test_complete_session(self, progress_monitor, session_manager, sample_request):
        """Test completing session monitoring."""
        session_id = session_manager.create_session(sample_request)
        progress_monitor.start_session_monitoring(session_id)
        
        # Complete successfully
        success = progress_monitor.complete_session(session_id, success=True)
        assert success is True
        
        # Verify session status
        session = session_manager.get_session(session_id)
        assert session.status == VideoStatus.COMPLETED
        assert session.stage == SessionStage.COMPLETED
        assert session.progress == 1.0
        
        # Verify monitoring stopped
        active_sessions = progress_monitor.get_active_sessions()
        assert session_id not in active_sessions
    
    def test_complete_session_with_failure(self, progress_monitor, session_manager, sample_request):
        """Test completing session with failure."""
        session_id = session_manager.create_session(sample_request)
        progress_monitor.start_session_monitoring(session_id)
        
        # Update some progress first
        progress_monitor.update_stage_progress(session_id, SessionStage.RESEARCHING, 0.3)
        
        # Complete with failure
        error_message = "Test error"
        success = progress_monitor.complete_session(
            session_id=session_id,
            success=False,
            error_message=error_message
        )
        assert success is True
        
        # Verify session status
        session = session_manager.get_session(session_id)
        assert session.status == VideoStatus.FAILED
        assert session.stage == SessionStage.FAILED
        assert session.error_message == error_message
        assert session.progress < 1.0  # Should preserve partial progress
    
    def test_get_session_progress(self, progress_monitor, session_manager, sample_request):
        """Test getting detailed session progress."""
        session_id = session_manager.create_session(sample_request)
        progress_monitor.start_session_monitoring(session_id)
        
        # Update some progress
        progress_monitor.update_stage_progress(session_id, SessionStage.RESEARCHING, 0.5)
        progress_monitor.advance_to_stage(session_id, SessionStage.SCRIPTING)
        progress_monitor.update_stage_progress(session_id, SessionStage.SCRIPTING, 0.3)
        
        # Get progress info
        progress_info = progress_monitor.get_session_progress(session_id)
        
        assert progress_info is not None
        assert progress_info["session_id"] == session_id
        assert progress_info["current_stage"] == SessionStage.SCRIPTING.value
        assert progress_info["overall_progress"] > 0
        assert "stage_details" in progress_info
        assert "estimated_completion" in progress_info
    
    def test_custom_stage_weights(self, progress_monitor, session_manager, sample_request):
        """Test custom stage weights."""
        session_id = session_manager.create_session(sample_request)
        
        # Custom weights (emphasize video assembly)
        custom_weights = {
            SessionStage.INITIALIZING: 0.05,
            SessionStage.RESEARCHING: 0.10,
            SessionStage.SCRIPTING: 0.15,
            SessionStage.ASSET_SOURCING: 0.20,
            SessionStage.AUDIO_GENERATION: 0.15,
            SessionStage.VIDEO_ASSEMBLY: 0.30,  # Higher weight
            SessionStage.FINALIZING: 0.05
        }
        
        success = progress_monitor.start_session_monitoring(
            session_id=session_id,
            stage_weights=custom_weights
        )
        assert success is True
        
        # Complete all stages except video assembly
        for stage in [SessionStage.INITIALIZING, SessionStage.RESEARCHING, 
                     SessionStage.SCRIPTING, SessionStage.ASSET_SOURCING, 
                     SessionStage.AUDIO_GENERATION]:
            progress_monitor.advance_to_stage(session_id, stage)
            progress_monitor.update_stage_progress(session_id, stage, 1.0)
        
        # Check overall progress (should be 70% since video assembly is 30%)
        progress_info = progress_monitor.get_session_progress(session_id)
        assert abs(progress_info["overall_progress"] - 0.7) < 0.01


class TestMaintenanceManager:
    """Test cases for MaintenanceManager."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def session_manager(self, temp_storage):
        """Create SessionManager instance."""
        return SessionManager(storage_path=temp_storage)
    
    @pytest.fixture
    def maintenance_manager(self, session_manager, temp_dir):
        """Create MaintenanceManager instance."""
        return MaintenanceManager(
            session_manager=session_manager,
            temp_dir=temp_dir
        )
    
    @pytest.fixture
    def sample_request(self):
        """Create sample video generation request."""
        return VideoGenerationRequest(
            prompt="Test video",
            duration_preference=60
        )
    
    def test_get_system_health(self, maintenance_manager):
        """Test getting system health information."""
        health = maintenance_manager.get_system_health()
        
        assert isinstance(health.disk_usage_percent, float)
        assert isinstance(health.memory_usage_percent, float)
        assert isinstance(health.cpu_usage_percent, float)
        assert isinstance(health.active_sessions, int)
        assert isinstance(health.total_sessions, int)
        assert isinstance(health.storage_size_mb, float)
        assert isinstance(health.temp_files_count, int)
        assert isinstance(health.temp_files_size_mb, float)
    
    def test_cleanup_temp_files(self, maintenance_manager, temp_dir):
        """Test cleaning up temporary files."""
        # Create some temporary files
        old_file = os.path.join(temp_dir, "old_file.txt")
        new_file = os.path.join(temp_dir, "new_file.txt")
        
        with open(old_file, 'w') as f:
            f.write("old content")
        with open(new_file, 'w') as f:
            f.write("new content")
        
        # Make old file actually old
        old_time = time.time() - (7 * 3600)  # 7 hours ago
        os.utime(old_file, (old_time, old_time))
        
        # Run cleanup
        stats = maintenance_manager.cleanup_temp_files()
        
        # Verify old file was deleted, new file remains
        assert not os.path.exists(old_file)
        assert os.path.exists(new_file)
        assert stats.files_deleted >= 1
        assert stats.bytes_freed > 0
    
    def test_cleanup_expired_sessions(self, maintenance_manager, session_manager, sample_request):
        """Test cleaning up expired sessions."""
        # Create sessions
        session1 = session_manager.create_session(sample_request)
        session2 = session_manager.create_session(sample_request)
        
        # Mark one as completed and old
        session_manager.update_session_status(session1, VideoStatus.COMPLETED)
        session = session_manager.get_session(session1)
        session.updated_at = datetime.utcnow() - timedelta(hours=50)
        
        # Run cleanup
        stats = maintenance_manager.cleanup_expired_sessions()
        
        # Verify cleanup
        assert stats.sessions_cleaned >= 1
        assert session_manager.get_session(session1) is None
        assert session_manager.get_session(session2) is not None
    
    def test_force_cleanup_session(self, maintenance_manager, session_manager, sample_request):
        """Test force cleanup of a specific session."""
        session_id = session_manager.create_session(sample_request)
        
        # Verify session exists
        assert session_manager.get_session(session_id) is not None
        
        # Force cleanup
        success = maintenance_manager.force_cleanup_session(session_id)
        assert success is True
        
        # Verify session is gone
        assert session_manager.get_session(session_id) is None
    
    def test_run_maintenance(self, maintenance_manager):
        """Test running comprehensive maintenance."""
        results = maintenance_manager.run_maintenance()
        
        assert results["status"] == "completed"
        assert "system_health" in results
        assert "operations" in results
        assert "total_stats" in results
        assert "duration_seconds" in results
        
        # Check that all expected operations ran
        operations = results["operations"]
        assert "session_cleanup" in operations
        assert "temp_cleanup" in operations
        assert "log_cleanup" in operations
    
    def test_get_maintenance_report(self, maintenance_manager):
        """Test generating maintenance report."""
        report = maintenance_manager.get_maintenance_report()
        
        assert "timestamp" in report
        assert "system_health" in report
        assert "session_statistics" in report
        assert "maintenance_config" in report
        assert "recommendations" in report
        assert "maintenance_running" in report
    
    def test_auto_maintenance(self, maintenance_manager):
        """Test automatic maintenance start/stop."""
        # Start maintenance
        maintenance_manager.start_maintenance(interval=1)  # 1 second for testing
        assert maintenance_manager.running is True
        
        # Wait a bit
        time.sleep(2)
        
        # Stop maintenance
        maintenance_manager.stop_maintenance()
        assert maintenance_manager.running is False


class TestIntegration:
    """Integration tests for session management components."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample video generation request."""
        return VideoGenerationRequest(
            prompt="Create an educational video about machine learning",
            duration_preference=120,
            style="educational"
        )
    
    def test_full_session_lifecycle(self, temp_storage, sample_request):
        """Test complete session lifecycle with all components."""
        # Initialize components
        session_manager = SessionManager(storage_path=temp_storage)
        progress_monitor = ProgressMonitor(session_manager)
        maintenance_manager = MaintenanceManager(session_manager)
        
        # Create session
        session_id = session_manager.create_session(sample_request, user_id="test_user")
        
        # Start monitoring
        progress_monitor.start_session_monitoring(session_id)
        
        # Simulate workflow progression
        stages = [
            SessionStage.RESEARCHING,
            SessionStage.SCRIPTING,
            SessionStage.ASSET_SOURCING,
            SessionStage.AUDIO_GENERATION,
            SessionStage.VIDEO_ASSEMBLY,
            SessionStage.FINALIZING
        ]
        
        for i, stage in enumerate(stages):
            # Advance to stage
            progress_monitor.advance_to_stage(session_id, stage)
            
            # Simulate progress within stage
            for progress in [0.3, 0.6, 1.0]:
                progress_monitor.update_stage_progress(session_id, stage, progress)
                time.sleep(0.1)  # Small delay to simulate work
        
        # Complete session
        progress_monitor.complete_session(session_id, success=True)
        
        # Verify final state
        session = session_manager.get_session(session_id)
        assert session.status == VideoStatus.COMPLETED
        assert session.progress == 1.0
        
        # Test maintenance
        health = maintenance_manager.get_system_health()
        assert health.total_sessions == 1
        
        # Run maintenance
        results = maintenance_manager.run_maintenance()
        assert results["status"] == "completed"
    
    def test_error_handling_integration(self, temp_storage, sample_request):
        """Test error handling across components."""
        session_manager = SessionManager(storage_path=temp_storage)
        progress_monitor = ProgressMonitor(session_manager)
        
        # Create session
        session_id = session_manager.create_session(sample_request)
        progress_monitor.start_session_monitoring(session_id)
        
        # Simulate partial progress
        progress_monitor.advance_to_stage(session_id, SessionStage.RESEARCHING)
        progress_monitor.update_stage_progress(session_id, SessionStage.RESEARCHING, 0.8)
        
        # Simulate failure
        error_message = "API rate limit exceeded"
        progress_monitor.complete_session(
            session_id=session_id,
            success=False,
            error_message=error_message
        )
        
        # Verify error state
        session = session_manager.get_session(session_id)
        assert session.status == VideoStatus.FAILED
        assert session.error_message == error_message
        assert session.progress < 1.0
    
    def test_concurrent_sessions(self, temp_storage, sample_request):
        """Test handling multiple concurrent sessions."""
        session_manager = SessionManager(storage_path=temp_storage)
        progress_monitor = ProgressMonitor(session_manager)
        
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = session_manager.create_session(
                sample_request, 
                user_id=f"user_{i}"
            )
            session_ids.append(session_id)
            progress_monitor.start_session_monitoring(session_id)
        
        # Progress each session to different stages
        for i, session_id in enumerate(session_ids):
            stage = [SessionStage.RESEARCHING, SessionStage.SCRIPTING, SessionStage.ASSET_SOURCING][i]
            progress_monitor.advance_to_stage(session_id, stage)
            progress_monitor.update_stage_progress(session_id, stage, 0.5)
        
        # Verify all sessions are tracked
        active_sessions = progress_monitor.get_active_sessions()
        assert len(active_sessions) == 3
        
        # Complete one session
        progress_monitor.complete_session(session_ids[0], success=True)
        
        # Verify statistics
        stats = session_manager.get_statistics()
        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 2  # One completed
        assert stats["status_distribution"]["completed"] == 1
        assert stats["status_distribution"]["processing"] == 2


if __name__ == "__main__":
    pytest.main([__file__])