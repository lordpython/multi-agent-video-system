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

"""Integration tests for the Multi-Agent Video System CLI.

This module contains comprehensive tests for the command-line interface,
including command execution, output validation, and error handling.
"""

import tempfile
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from video_system.api.cli import cli
from video_system.utils.models import VideoGenerationRequest, VideoStatus
from video_system.utils.adk_session_models import VideoGenerationStage as SessionStage


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_session_manager(temp_storage):
    """Create a mock session manager for testing."""
    with patch('video_system.cli.get_session_manager') as mock:
        session_manager = SessionManager(storage_path=temp_storage)
        mock.return_value = session_manager
        yield session_manager


@pytest.fixture
def mock_progress_monitor():
    """Create a mock progress monitor for testing."""
    with patch('video_system.cli.get_progress_monitor') as mock:
        progress_monitor = Mock()
        progress_monitor.get_session_progress.return_value = {
            "session_id": "test-session",
            "overall_progress": 0.5,
            "current_stage": "scripting",
            "estimated_completion": None,
            "stage_details": {
                "researching": {"progress": 1.0, "weight": 0.15},
                "scripting": {"progress": 0.5, "weight": 0.20},
                "asset_sourcing": {"progress": 0.0, "weight": 0.25}
            }
        }
        mock.return_value = progress_monitor
        yield progress_monitor


@pytest.fixture
def mock_initialize_system():
    """Mock the system initialization."""
    with patch('video_system.cli.initialize_video_system') as mock:
        yield mock


class TestCLICommands:
    """Test class for CLI command functionality."""
    
    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Multi-Agent Video System CLI" in result.output
        assert "generate" in result.output
        assert "status" in result.output
        assert "cancel" in result.output
        assert "cleanup" in result.output
        assert "stats" in result.output
        assert "serve" in result.output
    
    def test_generate_command_basic(self, runner, mock_session_manager, mock_initialize_system):
        """Test basic video generation command."""
        result = runner.invoke(cli, [
            'generate',
            '--prompt', 'Create a video about artificial intelligence',
            '--duration', '60',
            '--style', 'professional'
        ])
        
        assert result.exit_code == 0
        assert "Starting video generation" in result.output
        assert "Session created:" in result.output
        assert "Use 'video-cli status" in result.output
        
        # Verify session was created
        assert len(mock_session_manager.sessions) == 1
        session = list(mock_session_manager.sessions.values())[0]
        assert session.request.prompt == "Create a video about artificial intelligence"
        assert session.request.duration_preference == 60
        assert session.request.style == "professional"
    
    def test_generate_command_with_all_options(self, runner, mock_session_manager, mock_initialize_system):
        """Test video generation command with all options."""
        result = runner.invoke(cli, [
            'generate',
            '--prompt', 'Create an educational video about machine learning',
            '--duration', '120',
            '--style', 'educational',
            '--voice', 'female',
            '--quality', 'ultra'
        ])
        
        assert result.exit_code == 0
        
        # Verify session was created with correct parameters
        session = list(mock_session_manager.sessions.values())[0]
        assert session.request.prompt == "Create an educational video about machine learning"
        assert session.request.duration_preference == 120
        assert session.request.style == "educational"
        assert session.request.voice_preference == "female"
        assert session.request.quality == "ultra"
    
    def test_generate_command_invalid_style(self, runner, mock_initialize_system):
        """Test video generation command with invalid style."""
        result = runner.invoke(cli, [
            'generate',
            '--prompt', 'Create a video about AI',
            '--style', 'invalid_style'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--style'" in result.output
    
    def test_generate_command_invalid_quality(self, runner, mock_initialize_system):
        """Test video generation command with invalid quality."""
        result = runner.invoke(cli, [
            'generate',
            '--prompt', 'Create a video about AI',
            '--quality', 'invalid_quality'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--quality'" in result.output
    
    def test_generate_command_missing_prompt(self, runner):
        """Test video generation command without required prompt."""
        result = runner.invoke(cli, ['generate'])
        
        assert result.exit_code != 0
        assert "Missing option '--prompt'" in result.output
    
    def test_status_command_specific_session(self, runner, mock_session_manager):
        """Test status command for a specific session."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request, "test-user")
        
        result = runner.invoke(cli, ['status', session_id])
        
        assert result.exit_code == 0
        assert "Session Status" in result.output
        assert session_id[:8] in result.output
        assert "Queued" in result.output
        assert "Initializing" in result.output
    
    def test_status_command_nonexistent_session(self, runner, mock_session_manager):
        """Test status command for a nonexistent session."""
        result = runner.invoke(cli, ['status', 'nonexistent-session'])
        
        assert result.exit_code == 0
        assert "Session nonexistent-session not found" in result.output
    
    def test_status_command_all_sessions(self, runner, mock_session_manager):
        """Test status command to show all sessions."""
        # Create test sessions
        for i in range(3):
            request = VideoGenerationRequest(
                prompt=f"Test video {i}",
                duration_preference=60
            )
            mock_session_manager.create_session(request, f"user{i}")
        
        result = runner.invoke(cli, ['status', '--all'])
        
        assert result.exit_code == 0
        assert "All Sessions (3 total)" in result.output
        assert "Session ID" in result.output
        assert "Status" in result.output
        assert "Progress" in result.output
    
    def test_status_command_recent_sessions(self, runner, mock_session_manager):
        """Test status command to show recent sessions."""
        # Create test sessions
        for i in range(2):
            request = VideoGenerationRequest(
                prompt=f"Test video {i}",
                duration_preference=60
            )
            mock_session_manager.create_session(request, f"user{i}")
        
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert "Recent Sessions" in result.output
        assert "Session ID" in result.output
    
    def test_status_command_no_sessions(self, runner, mock_session_manager):
        """Test status command when no sessions exist."""
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert "No sessions found" in result.output
    
    def test_cancel_command_existing_session(self, runner, mock_session_manager):
        """Test cancelling an existing session."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request)
        
        result = runner.invoke(cli, ['cancel', session_id])
        
        assert result.exit_code == 0
        assert f"Session {session_id} cancelled" in result.output
        assert "Session files cleaned up" in result.output
        
        # Verify session was cancelled (should be deleted)
        assert mock_session_manager.get_session(session_id) is None
    
    def test_cancel_command_keep_files(self, runner, mock_session_manager):
        """Test cancelling a session while keeping files."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request)
        
        result = runner.invoke(cli, ['cancel', session_id, '--keep-files'])
        
        assert result.exit_code == 0
        assert f"Session {session_id} cancelled" in result.output
        assert "Session files cleaned up" not in result.output
        
        # Verify session was cancelled but not deleted
        session = mock_session_manager.get_session(session_id)
        assert session is not None
        assert session.status == VideoStatus.CANCELLED
    
    def test_cancel_command_nonexistent_session(self, runner, mock_session_manager):
        """Test cancelling a nonexistent session."""
        result = runner.invoke(cli, ['cancel', 'nonexistent-session'])
        
        assert result.exit_code == 1
        assert "Session nonexistent-session not found" in result.output
    
    def test_cleanup_command(self, runner, mock_session_manager):
        """Test cleanup command."""
        with patch.object(mock_session_manager, 'cleanup_expired_sessions') as mock_cleanup:
            mock_cleanup.return_value = 5
            
            result = runner.invoke(cli, ['cleanup', '--max-age', '48'])
            
            assert result.exit_code == 0
            assert "Cleaned up 5 expired sessions" in result.output
            
            mock_cleanup.assert_called_once_with(48)
    
    def test_cleanup_command_dry_run(self, runner, mock_session_manager):
        """Test cleanup command with dry run."""
        result = runner.invoke(cli, ['cleanup', '--dry-run'])
        
        assert result.exit_code == 0
        assert "Dry run: Would clean up sessions" in result.output
    
    def test_stats_command(self, runner, mock_session_manager):
        """Test stats command."""
        # Create some test sessions
        for i in range(3):
            request = VideoGenerationRequest(
                prompt=f"Test video {i}",
                duration_preference=60
            )
            mock_session_manager.create_session(request)
        
        with patch('video_system.cli.check_orchestrator_health') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "details": {"message": "All systems operational"}
            }
            
            result = runner.invoke(cli, ['stats'])
            
            assert result.exit_code == 0
            assert "System Statistics" in result.output
            assert "Total Sessions: 3" in result.output
            assert "System Health: HEALTHY" in result.output
    
    def test_stats_command_unhealthy_system(self, runner, mock_session_manager):
        """Test stats command with unhealthy system."""
        with patch('video_system.cli.check_orchestrator_health') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "details": {"unhealthy_services": ["serper_api", "ffmpeg"]}
            }
            
            result = runner.invoke(cli, ['stats'])
            
            assert result.exit_code == 0
            assert "System Health: UNHEALTHY" in result.output
            assert "Unhealthy Services: serper_api, ffmpeg" in result.output


class TestCLIProgressDisplay:
    """Test class for CLI progress display functionality."""
    
    def test_wait_for_completion_success(self, runner, mock_session_manager, mock_initialize_system):
        """Test waiting for completion with successful generation."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request)
        
        # Mock the session progression
        def mock_get_session(sid):
            session = mock_session_manager.sessions[sid]
            # Simulate progression
            if not hasattr(mock_get_session, 'call_count'):
                mock_get_session.call_count = 0
            mock_get_session.call_count += 1
            
            if mock_get_session.call_count <= 2:
                session.status = VideoStatus.PROCESSING
                session.progress = 0.5
                session.stage = SessionStage.SCRIPTING
            else:
                session.status = VideoStatus.COMPLETED
                session.progress = 1.0
                session.stage = SessionStage.COMPLETED
            
            return session
        
        with patch.object(mock_session_manager, 'get_session', side_effect=mock_get_session):
            with patch('time.sleep'):  # Speed up the test
                result = runner.invoke(cli, [
                    'generate',
                    '--prompt', 'Test video about AI',
                    '--wait'
                ])
        
        assert result.exit_code == 0
        assert "Video generation completed!" in result.output
    
    def test_wait_for_completion_failure(self, runner, mock_session_manager, mock_initialize_system):
        """Test waiting for completion with failed generation."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request)
        
        # Mock the session failure
        def mock_get_session(sid):
            session = mock_session_manager.sessions[sid]
            session.status = VideoStatus.FAILED
            session.error_message = "Processing failed"
            return session
        
        with patch.object(mock_session_manager, 'get_session', side_effect=mock_get_session):
            with patch('time.sleep'):  # Speed up the test
                result = runner.invoke(cli, [
                    'generate',
                    '--prompt', 'Test video about AI',
                    '--wait'
                ])
        
        assert result.exit_code == 0
        assert "Video generation failed: Processing failed" in result.output
    
    def test_watch_session_progress(self, runner, mock_session_manager):
        """Test watching session progress in real-time."""
        # Create a test session
        request = VideoGenerationRequest(
            prompt="Test video about AI",
            duration_preference=60
        )
        session_id = mock_session_manager.create_session(request)
        
        # Mock session progression
        call_count = 0
        def mock_get_session(sid):
            nonlocal call_count
            call_count += 1
            session = mock_session_manager.sessions[sid]
            
            if call_count <= 2:
                session.status = VideoStatus.PROCESSING
                session.progress = 0.3
                session.stage = SessionStage.SCRIPTING
            else:
                session.status = VideoStatus.COMPLETED
                session.progress = 1.0
                session.stage = SessionStage.COMPLETED
            
            return session
        
        with patch.object(mock_session_manager, 'get_session', side_effect=mock_get_session):
            with patch('time.sleep'):  # Speed up the test
                result = runner.invoke(cli, ['status', session_id, '--watch'])
        
        assert result.exit_code == 0
        # The watch command should show live progress updates


class TestCLIErrorHandling:
    """Test class for CLI error handling."""
    
    def test_generate_command_system_error(self, runner, mock_initialize_system):
        """Test generate command with system initialization error."""
        mock_initialize_system.side_effect = Exception("System initialization failed")
        
        result = runner.invoke(cli, [
            'generate',
            '--prompt', 'Test video about AI'
        ])
        
        assert result.exit_code == 1
        assert "Error: System initialization failed" in result.output
    
    def test_status_command_system_error(self, runner):
        """Test status command with system error."""
        with patch('video_system.cli.get_session_manager') as mock:
            mock.side_effect = Exception("Database connection failed")
            
            result = runner.invoke(cli, ['status'])
            
            assert result.exit_code == 1
            assert "Error: Database connection failed" in result.output
    
    def test_cancel_command_system_error(self, runner):
        """Test cancel command with system error."""
        with patch('video_system.cli.get_session_manager') as mock:
            mock.side_effect = Exception("Database connection failed")
            
            result = runner.invoke(cli, ['cancel', 'test-session'])
            
            assert result.exit_code == 1
            assert "Error: Database connection failed" in result.output
    
    def test_cleanup_command_system_error(self, runner):
        """Test cleanup command with system error."""
        with patch('video_system.cli.get_session_manager') as mock:
            mock.side_effect = Exception("Database connection failed")
            
            result = runner.invoke(cli, ['cleanup'])
            
            assert result.exit_code == 1
            assert "Error: Database connection failed" in result.output
    
    def test_stats_command_system_error(self, runner):
        """Test stats command with system error."""
        with patch('video_system.cli.get_session_manager') as mock:
            mock.side_effect = Exception("Database connection failed")
            
            result = runner.invoke(cli, ['stats'])
            
            assert result.exit_code == 1
            assert "Error: Database connection failed" in result.output


class TestCLIServeCommand:
    """Test class for CLI serve command."""
    
    def test_serve_command_basic(self, runner):
        """Test basic serve command."""
        with patch('uvicorn.run') as mock_run:
            result = runner.invoke(cli, ['serve'])
            
            assert result.exit_code == 0
            assert "Starting API server on 127.0.0.1:8000" in result.output
            assert "API documentation available at" in result.output
            
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert kwargs['host'] == '127.0.0.1'
            assert kwargs['port'] == 8000
            assert kwargs['reload'] is False
    
    def test_serve_command_with_options(self, runner):
        """Test serve command with custom options."""
        with patch('uvicorn.run') as mock_run:
            result = runner.invoke(cli, [
                'serve',
                '--host', '0.0.0.0',
                '--port', '9000',
                '--reload'
            ])
            
            assert result.exit_code == 0
            
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert kwargs['host'] == '0.0.0.0'
            assert kwargs['port'] == 9000
            assert kwargs['reload'] is True
    
    def test_serve_command_missing_dependencies(self, runner):
        """Test serve command when FastAPI dependencies are missing."""
        with patch('video_system.cli.uvicorn', None):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'uvicorn'")):
                result = runner.invoke(cli, ['serve'])
                
                assert result.exit_code == 1
                assert "FastAPI and uvicorn are required" in result.output
                assert "Install with: pip install fastapi uvicorn" in result.output


if __name__ == "__main__":
    pytest.main([__file__])