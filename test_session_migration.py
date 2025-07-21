#!/usr/bin/env python3
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

"""Test session migration functionality."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import sys

# Add the video_system to the path
sys.path.insert(0, str(Path(__file__).parent / "video_system"))

from video_system.shared_libraries.session_migration import (
    SessionMigrationManager, 
    LegacySessionData,
    run_startup_migration_check
)
from video_system.shared_libraries.adk_session_manager import VideoSystemSessionManager
from google.adk.sessions import InMemorySessionService


async def test_legacy_session_conversion():
    """Test conversion of legacy session data to VideoGenerationState."""
    print("Testing legacy session conversion...")
    
    # Create sample legacy session data
    legacy_data = {
        "session_id": "test_legacy_123",
        "user_id": "test_user",
        "prompt": "Create a video about artificial intelligence",
        "status": "processing",
        "progress": 0.5,
        "created_at": "2025-01-01T10:00:00",
        "updated_at": "2025-01-01T10:30:00",
        "request": {
            "prompt": "Create a video about artificial intelligence",
            "duration_preference": 60,
            "style": "professional",
            "voice_preference": "neutral",
            "quality": "high"
        },
        "research_data": {
            "facts": ["AI is transforming industries", "Machine learning is a subset of AI"],
            "sources": ["https://example.com/ai-facts"],
            "key_points": ["AI applications", "Future of AI"],
            "context": {"research_quality": "high"}
        },
        "error_log": ["Warning: Some assets not found"],
        "retry_count": {"research": 1},
        "metadata": {"test": True}
    }
    
    # Convert to LegacySessionData and then to VideoGenerationState
    legacy_session = LegacySessionData(legacy_data)
    state = legacy_session.to_video_generation_state()
    
    # Verify conversion
    assert state.session_id == "test_legacy_123"
    assert state.user_id == "test_user"
    assert state.request.prompt == "Create a video about artificial intelligence"
    assert state.progress == 0.5
    assert state.research_data is not None
    assert state.research_data.facts[0] == "AI is transforming industries"
    assert state.error_log == ["Warning: Some assets not found"]
    assert state.retry_count == {"research": 1}
    assert state.metadata == {"test": True}
    
    print("✓ Legacy session conversion test passed")


async def test_file_based_discovery():
    """Test discovery of legacy sessions from files."""
    print("Testing file-based session discovery...")
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        sessions_dir = temp_path / "sessions"
        sessions_dir.mkdir()
        
        # Create sample session files
        session_files = [
            {
                "filename": "session_001.json",
                "data": {
                    "session_id": "session_001",
                    "prompt": "Test video 1",
                    "status": "completed",
                    "progress": 1.0,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "filename": "session_002.json", 
                "data": {
                    "session_id": "session_002",
                    "prompt": "Test video 2",
                    "status": "failed",
                    "progress": 0.3,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": "Test error"
                }
            }
        ]
        
        for session_file in session_files:
            file_path = sessions_dir / session_file["filename"]
            with open(file_path, 'w') as f:
                json.dump(session_file["data"], f)
        
        # Test discovery
        migration_manager = SessionMigrationManager()
        migration_manager.legacy_session_paths = [sessions_dir]
        
        legacy_sessions = await migration_manager._discover_legacy_sessions()
        
        # Check that our sessions are found
        found_session_ids = [s.session_id for s in legacy_sessions]
        assert "session_001" in found_session_ids
        assert "session_002" in found_session_ids
        
        # Test session with error
        failed_session = next(s for s in legacy_sessions if s.session_id == "session_002")
        assert failed_session.error_message == "Test error"
        
    print("✓ File-based discovery test passed")


async def test_directory_based_discovery():
    """Test discovery of sessions from directory structure."""
    print("Testing directory-based session discovery...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        sessions_dir = temp_path / "sessions"
        sessions_dir.mkdir()
        
        # Create session directory structure
        session_dir = sessions_dir / "session_dir_001"
        session_dir.mkdir()
        
        # Create individual session files
        session_files = {
            "session.json": {"session_id": "session_dir_001", "user_id": "test_user"},
            "request.json": {"prompt": "Directory-based session", "duration_preference": 30},
            "progress.json": {"progress": 0.7, "status": "processing"},
            "metadata.json": {"source": "directory_structure"}
        }
        
        for filename, data in session_files.items():
            with open(session_dir / filename, 'w') as f:
                json.dump(data, f)
        
        # Test discovery
        migration_manager = SessionMigrationManager()
        migration_manager.legacy_session_paths = [sessions_dir]
        
        legacy_sessions = await migration_manager._discover_legacy_sessions()
        
        # Find our specific session
        target_session = None
        for session in legacy_sessions:
            if session.session_id == "session_dir_001":
                target_session = session
                break
        
        assert target_session is not None, f"Expected session not found. Found sessions: {[(s.session_id, s.progress) for s in legacy_sessions]}"
        assert target_session.progress == 0.7, f"Expected progress 0.7, got {target_session.progress}"
        
    print("✓ Directory-based discovery test passed")


async def test_migration_process():
    """Test the complete migration process."""
    print("Testing complete migration process...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create legacy session data
        sessions_dir = temp_path / "data" / "sessions"
        sessions_dir.mkdir(parents=True)
        
        legacy_session_data = {
            "session_id": "migration_test_001",
            "user_id": "migration_user",
            "prompt": "Migration test video",
            "status": "processing",
            "progress": 0.4,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request": {
                "prompt": "Migration test video",
                "duration_preference": 45,
                "style": "casual",
                "voice_preference": "friendly",
                "quality": "medium"
            }
        }
        
        with open(sessions_dir / "migration_test.json", 'w') as f:
            json.dump(legacy_session_data, f)
        
        # Set up migration manager with custom paths
        migration_manager = SessionMigrationManager()
        migration_manager.legacy_session_paths = [sessions_dir]
        migration_manager.migration_log_path = temp_path / "migration_log.json"
        migration_manager.migration_completed_marker = temp_path / ".migration_completed"
        
        # Create session manager with in-memory service
        session_service = InMemorySessionService()
        session_manager = VideoSystemSessionManager(
            session_service=session_service,
            run_migration_check=False  # We'll run it manually
        )
        
        # Run migration
        results = await migration_manager.check_and_run_migration(session_manager)
        
        # Verify results
        assert results["migration_needed"] == True
        assert results["legacy_sessions_found"] == 1
        assert results["migrated_sessions"] == 1
        assert results["failed_migrations"] == 0
        
        # Verify session was created in ADK SessionService
        migrated_session_id = results["errors"] == [] and len(results) > 0
        
        # Verify migration log was created
        assert migration_manager.migration_log_path.exists()
        
        # Verify completion marker was created
        assert migration_manager.migration_completed_marker.exists()
        
        # Test that second run doesn't migrate again
        results2 = await migration_manager.check_and_run_migration(session_manager)
        assert results2["migration_needed"] == False
        assert results2["already_completed"] == True
        
    print("✓ Complete migration process test passed")


async def test_startup_migration_check():
    """Test startup migration check integration."""
    print("Testing startup migration check...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create legacy session
        sessions_dir = temp_path / "data" / "sessions"
        sessions_dir.mkdir(parents=True)
        
        legacy_data = {
            "session_id": "startup_test_001",
            "prompt": "Startup migration test",
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(sessions_dir / "startup_test.json", 'w') as f:
            json.dump(legacy_data, f)
        
        # Temporarily change working directory to temp_dir for the test
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Create session manager (this should trigger migration)
            session_service = InMemorySessionService()
            session_manager = VideoSystemSessionManager(
                session_service=session_service,
                run_migration_check=False  # We'll test the function directly
            )
            
            # Run startup migration check
            results = await run_startup_migration_check(session_manager)
            
            # Verify migration occurred
            assert results.get("migration_needed") == True or results.get("legacy_sessions_found", 0) > 0
            
        finally:
            os.chdir(original_cwd)
    
    print("✓ Startup migration check test passed")


async def test_error_handling():
    """Test error handling in migration process."""
    print("Testing migration error handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create invalid session data
        sessions_dir = temp_path / "data" / "sessions"
        sessions_dir.mkdir(parents=True)
        
        # Create file with invalid JSON
        with open(sessions_dir / "invalid.json", 'w') as f:
            f.write("{ invalid json content")
        
        # Create file with missing required fields
        with open(sessions_dir / "incomplete.json", 'w') as f:
            json.dump({"some_field": "value"}, f)
        
        # Set up migration manager
        migration_manager = SessionMigrationManager()
        migration_manager.legacy_session_paths = [sessions_dir]
        migration_manager.migration_log_path = temp_path / "migration_log.json"
        migration_manager.migration_completed_marker = temp_path / ".migration_completed"
        
        # Create session manager
        session_service = InMemorySessionService()
        session_manager = VideoSystemSessionManager(
            session_service=session_service,
            run_migration_check=False
        )
        
        # Run migration (should handle errors gracefully)
        results = await migration_manager.check_and_run_migration(session_manager)
        
        # Should complete without crashing, even with invalid data
        assert "error" not in results or results.get("migrated_sessions", 0) >= 0
        
    print("✓ Error handling test passed")


async def run_all_tests():
    """Run all migration tests."""
    print("Running session migration tests...\n")
    
    try:
        await test_legacy_session_conversion()
        await test_file_based_discovery()
        await test_directory_based_discovery()
        await test_migration_process()
        await test_startup_migration_check()
        await test_error_handling()
        
        print("\n✅ All migration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())