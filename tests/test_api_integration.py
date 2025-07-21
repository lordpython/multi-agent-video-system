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

"""Integration tests for the Multi-Agent Video System API.

This module contains comprehensive tests for the FastAPI REST interface,
including request validation, response handling, and error scenarios.
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from video_system.api import app
from video_system.shared_libraries.models import VideoGenerationRequest, VideoStatus


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_session_manager(temp_storage):
    """Create a mock session manager for testing."""
    with patch('video_system.api.get_session_manager') as mock:
        session_manager = SessionManager(storage_path=temp_storage)
        mock.return_value = session_manager
        yield session_manager


@pytest.fixture
def mock_progress_monitor():
    """Create a mock progress monitor for testing."""
    with patch('video_system.api.get_progress_monitor') as mock:
        progress_monitor = Mock()
        progress_monitor.start_session_monitoring.return_value = True
        progress_monitor.get_session_progress.return_value = {
            "session_id": "test-session",
            "overall_progress": 0.5,
            "current_stage": "scripting",
            "estimated_completion": None,
            "stage_details": {}
        }
        mock.return_value = progress_monitor
        yield progress_monitor


class TestAPIEndpoints:
    """Test class for API endpoint functionality."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Multi-Agent Video System API"
        assert data["version"] == "0.1.0"
        assert "docs_url" in data
        assert "health_url" in data
    
    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        with patch('video_system.api.check_orchestrator_health') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "details": {"message": "All systems operational"}
            }
            
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "details" in data
    
    def test_health_check_unhealthy(self, client):
        """Test health check when system is unhealthy."""
        with patch('video_system.api.check_orchestrator_health') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "details": {"error": "Service unavailable"}
            }
            
            response = client.get("/health")
            assert response.status_code == 503
            
            data = response.json()
            assert data["status"] == "unhealthy"
    
    def test_generate_video_valid_request(self, client, mock_session_manager, mock_progress_monitor):
        """Test video generation with valid request."""
        request_data = {
            "prompt": "Create a video about artificial intelligence",
            "duration_preference": 60,
            "style": "professional",
            "voice_preference": "neutral",
            "quality": "high",
            "user_id": "test-user"
        }
        
        with patch('video_system.api._process_video_generation') as mock_process:
            response = client.post("/videos/generate", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "session_id" in data
            assert data["status"] == "queued"
            assert data["message"] == "Video generation started successfully"
            assert "created_at" in data
            
            # Verify session was created
            session = mock_session_manager.get_session(data["session_id"])
            assert session is not None
            assert session.request.prompt == request_data["prompt"]
            assert session.user_id == request_data["user_id"]
            
            # Verify progress monitoring was started
            mock_progress_monitor.start_session_monitoring.assert_called_once()
    
    def test_generate_video_invalid_prompt(self, client):
        """Test video generation with invalid prompt."""
        request_data = {
            "prompt": "short",  # Too short
            "duration_preference": 60
        }
        
        response = client.post("/videos/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_generate_video_invalid_duration(self, client):
        """Test video generation with invalid duration."""
        request_data = {
            "prompt": "Create a video about artificial intelligence",
            "duration_preference": 1000  # Too long
        }
        
        response = client.post("/videos/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_generate_video_invalid_style(self, client):
        """Test video generation with invalid style."""
        request_data = {
            "prompt": "Create a video about artificial intelligence",
            "style": "invalid_style"
        }
        
        response = client.post("/videos/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_video_status_existing_session(self, client, mock_session_manager):
        """Test getting status for an existing session."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request, "test-user")
        
        response = client.get(f"/videos/{session_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "queued"
        assert data["stage"] == "initializing"
        assert data["progress"] == 0.0
        assert "created_at" in data
        assert "updated_at" in data
        assert "request_details" in data
    
    def test_get_video_status_nonexistent_session(self, client, mock_session_manager):
        """Test getting status for a nonexistent session."""
        response = client.get("/videos/nonexistent-session/status")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Session not found"
    
    def test_get_video_progress(self, client, mock_progress_monitor):
        """Test getting detailed progress information."""
        session_id = "test-session"
        
        response = client.get(f"/videos/{session_id}/progress")
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == session_id
        assert data["overall_progress"] == 0.5
        assert data["current_stage"] == "scripting"
        
        mock_progress_monitor.get_session_progress.assert_called_once_with(session_id)
    
    def test_get_video_progress_not_found(self, client, mock_progress_monitor):
        """Test getting progress for a session that's not being monitored."""
        mock_progress_monitor.get_session_progress.return_value = None
        
        response = client.get("/videos/nonexistent-session/progress")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Session not found or not being monitored"
    
    def test_cancel_video_generation(self, client, mock_session_manager, mock_progress_monitor):
        """Test cancelling a video generation session."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request)
        
        response = client.delete(f"/videos/{session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Session cancelled successfully"
        assert data["session_id"] == session_id
        
        # Verify session was cancelled
        session = mock_session_manager.get_session(session_id)
        assert session.status == VideoStatus.CANCELLED
        
        # Verify progress monitoring was completed
        mock_progress_monitor.complete_session.assert_called_once()
    
    def test_cancel_nonexistent_session(self, client, mock_session_manager):
        """Test cancelling a nonexistent session."""
        response = client.delete("/videos/nonexistent-session")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Session not found"
    
    def test_list_video_sessions(self, client, mock_session_manager):
        """Test listing video sessions."""
        # Create test sessions
        request1 = VideoGenerationRequest(prompt="Test video 1", duration_preference=60)
        request2 = VideoGenerationRequest(prompt="Test video 2", duration_preference=90)
        
        session_id1 = mock_session_manager.create_session(request1, "user1")
        session_id2 = mock_session_manager.create_session(request2, "user2")
        
        response = client.get("/videos")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["sessions"]) == 2
        
        # Check session data
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert session_id1 in session_ids
        assert session_id2 in session_ids
    
    def test_list_video_sessions_with_filters(self, client, mock_session_manager):
        """Test listing video sessions with filters."""
        # Create test sessions
        request1 = VideoGenerationRequest(prompt="Test video 1", duration_preference=60)
        request2 = VideoGenerationRequest(prompt="Test video 2", duration_preference=90)
        
        session_id1 = mock_session_manager.create_session(request1, "user1")
        session_id2 = mock_session_manager.create_session(request2, "user2")
        
        # Filter by user
        response = client.get("/videos?user_id=user1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 1
        assert data["sessions"][0]["session_id"] == session_id1
    
    def test_list_video_sessions_pagination(self, client, mock_session_manager):
        """Test listing video sessions with pagination."""
        # Create multiple test sessions
        for i in range(5):
            request = VideoGenerationRequest(
                prompt=f"Test video {i}",
                duration_preference=60
            )
            mock_session_manager.create_session(request, f"user{i}")
        
        # Test pagination
        response = client.get("/videos?page=1&page_size=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["sessions"]) == 2
        
        # Test second page
        response = client.get("/videos?page=2&page_size=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 2
        assert len(data["sessions"]) == 2
    
    def test_get_system_stats(self, client, mock_session_manager):
        """Test getting system statistics."""
        # Create some test sessions
        for i in range(3):
            request = VideoGenerationRequest(
                prompt=f"Test video {i}",
                duration_preference=60
            )
            mock_session_manager.create_session(request)
        
        with patch('video_system.api.check_orchestrator_health') as mock_health:
            mock_health.return_value = {"status": "healthy", "details": {}}
            
            response = client.get("/system/stats")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total_sessions"] == 3
            assert data["active_sessions"] == 0  # All queued
            assert "status_distribution" in data
            assert "stage_distribution" in data
            assert "system_health" in data
    
    def test_cleanup_sessions(self, client, mock_session_manager):
        """Test cleaning up expired sessions."""
        with patch.object(mock_session_manager, 'cleanup_expired_sessions') as mock_cleanup:
            mock_cleanup.return_value = 5
            
            response = client.post("/system/cleanup?max_age_hours=48")
            assert response.status_code == 200
            
            data = response.json()
            assert data["cleaned_count"] == 5
            assert data["max_age_hours"] == 48
            assert "Cleaned up 5 expired sessions" in data["message"]
            
            mock_cleanup.assert_called_once_with(48)


class TestAPIValidation:
    """Test class for API request validation."""
    
    def test_video_generation_request_validation(self, client):
        """Test comprehensive request validation."""
        # Test missing required fields
        response = client.post("/videos/generate", json={})
        assert response.status_code == 422
        
        # Test prompt length validation
        response = client.post("/videos/generate", json={"prompt": "short"})
        assert response.status_code == 422
        
        response = client.post("/videos/generate", json={"prompt": "x" * 2001})
        assert response.status_code == 422
        
        # Test duration validation
        response = client.post("/videos/generate", json={
            "prompt": "Valid prompt for testing",
            "duration_preference": 5  # Too short
        })
        assert response.status_code == 422
        
        response = client.post("/videos/generate", json={
            "prompt": "Valid prompt for testing",
            "duration_preference": 700  # Too long
        })
        assert response.status_code == 422
        
        # Test style validation
        response = client.post("/videos/generate", json={
            "prompt": "Valid prompt for testing",
            "style": "invalid_style"
        })
        assert response.status_code == 422
        
        # Test quality validation
        response = client.post("/videos/generate", json={
            "prompt": "Valid prompt for testing",
            "quality": "invalid_quality"
        })
        assert response.status_code == 422
    
    def test_pagination_validation(self, client):
        """Test pagination parameter validation."""
        # Test invalid page number
        response = client.get("/videos?page=0")
        assert response.status_code == 422
        
        # Test invalid page size
        response = client.get("/videos?page_size=0")
        assert response.status_code == 422
        
        response = client.get("/videos?page_size=101")
        assert response.status_code == 422
    
    def test_cleanup_validation(self, client):
        """Test cleanup parameter validation."""
        # Test invalid max_age_hours
        response = client.post("/system/cleanup?max_age_hours=0")
        assert response.status_code == 422


class TestAPIErrorHandling:
    """Test class for API error handling."""
    
    def test_internal_server_error_handling(self, client):
        """Test handling of internal server errors."""
        with patch('video_system.api.get_session_manager') as mock:
            mock.side_effect = Exception("Database connection failed")
            
            response = client.get("/videos")
            assert response.status_code == 500
            
            data = response.json()
            assert data["error"] == "Internal server error"
    
    def test_session_not_found_error(self, client, mock_session_manager):
        """Test handling of session not found errors."""
        response = client.get("/videos/invalid-session-id/status")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Session not found"
    
    def test_validation_error_handling(self, client):
        """Test handling of validation errors."""
        response = client.post("/videos/generate", json={
            "prompt": "Valid prompt",
            "style": "invalid_style"
        })
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data


class TestBackgroundProcessing:
    """Test class for background processing functionality."""
    
    @pytest.mark.asyncio
    async def test_process_video_generation_success(self, mock_session_manager, mock_progress_monitor):
        """Test successful background video generation processing."""
        from video_system.api import _process_video_generation
        
        session_id = "test-session"
        
        # Mock the session manager methods
        mock_session_manager.update_session_status = Mock(return_value=True)
        mock_progress_monitor.advance_to_stage = Mock(return_value=True)
        mock_progress_monitor.update_stage_progress = Mock(return_value=True)
        mock_progress_monitor.complete_session = Mock(return_value=True)
        
        # Run the background task with reduced timing for testing
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await _process_video_generation(session_id)
        
        # Verify the process completed successfully
        mock_progress_monitor.complete_session.assert_called_once_with(session_id, success=True)
    
    @pytest.mark.asyncio
    async def test_process_video_generation_failure(self, mock_session_manager, mock_progress_monitor):
        """Test background video generation processing with failure."""
        from video_system.api import _process_video_generation
        
        session_id = "test-session"
        
        # Mock failure in progress monitoring
        mock_progress_monitor.advance_to_stage.side_effect = Exception("Processing failed")
        mock_session_manager.update_session_status = Mock(return_value=True)
        mock_progress_monitor.complete_session = Mock(return_value=True)
        
        # Run the background task
        await _process_video_generation(session_id)
        
        # Verify the session was marked as failed
        mock_progress_monitor.complete_session.assert_called_once_with(
            session_id, success=False, error_message="Processing failed"
        )


if __name__ == "__main__":
    pytest.main([__file__])