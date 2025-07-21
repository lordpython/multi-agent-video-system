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

"""Integration test for session migration with the actual session manager."""

import asyncio
import json
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the video_system to the path
sys.path.insert(0, str(Path(__file__).parent / "video_system"))

from video_system.shared_libraries.adk_session_manager import VideoSystemSessionManager
from google.adk.sessions import InMemorySessionService


async def test_migration_integration():
    """Test migration integration with VideoSystemSessionManager."""
    print("Testing migration integration with VideoSystemSessionManager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create legacy session data
        sessions_dir = temp_path / "data" / "sessions"
        sessions_dir.mkdir(parents=True)
        
        legacy_sessions = [
            {
                "session_id": "integration_test_001",
                "user_id": "test_user_1",
                "prompt": "Create a video about machine learning",
                "status": "processing",
                "progress": 0.6,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "request": {
                    "prompt": "Create a video about machine learning",
                    "duration_preference": 90,
                    "style": "educational",
                    "voice_preference": "professional",
                    "quality": "high"
                },
                "research_data": {
                    "facts": ["ML is a subset of AI", "Neural networks are key"],
                    "sources": ["https://example.com/ml"],
                    "key_points": ["Supervised learning", "Unsupervised learning"],
                    "context": {"research_quality": "high"}
                }
            },
            {
                "session_id": "integration_test_002",
                "user_id": "test_user_2",
                "prompt": "Create a video about climate change",
                "status": "completed",
                "progress": 1.0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "request": {
                    "prompt": "Create a video about climate change",
                    "duration_preference": 120,
                    "style": "documentary",
                    "voice_preference": "authoritative",
                    "quality": "ultra"
                }
            }
        ]
        
        # Save legacy sessions
        for i, session_data in enumerate(legacy_sessions):
            with open(sessions_dir / f"legacy_session_{i+1}.json", 'w') as f:
                json.dump(session_data, f, indent=2)
        
        # Change to temp directory for migration
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Create session manager with migration enabled
            session_service = InMemorySessionService()
            session_manager = VideoSystemSessionManager(
                session_service=session_service,
                run_migration_check=True  # Enable migration
            )
            
            # Wait a bit for migration to complete
            await asyncio.sleep(0.5)
            
            # Check migration status
            migration_status = await session_manager.get_migration_status()
            print(f"Migration status: {migration_status}")
            
            # Verify migration completed
            assert migration_status["runtime_migration"]["completed"], "Migration should be completed"
            
            migration_results = migration_status["runtime_migration"]["results"]
            if migration_results.get("migration_needed"):
                assert migration_results["migrated_sessions"] == 2, f"Expected 2 migrated sessions, got {migration_results['migrated_sessions']}"
                print(f"✓ Successfully migrated {migration_results['migrated_sessions']} sessions")
            else:
                print("✓ No migration was needed")
            
            # List sessions to verify they were migrated
            all_sessions = await session_manager.list_sessions()
            print(f"Found {len(all_sessions)} sessions after migration")
            
            # Verify session data
            for session_state in all_sessions:
                print(f"Session {session_state.session_id}: {session_state.request.prompt[:50]}...")
                assert session_state.request.prompt in [
                    "Create a video about machine learning",
                    "Create a video about climate change"
                ], f"Unexpected prompt: {session_state.request.prompt}"
            
            # Test session retrieval by user
            user1_sessions = await session_manager.list_sessions(user_id="test_user_1")
            user2_sessions = await session_manager.list_sessions(user_id="test_user_2")
            
            print(f"User 1 sessions: {len(user1_sessions)}")
            print(f"User 2 sessions: {len(user2_sessions)}")
            
            # Verify user-specific sessions
            if migration_results and migration_results.get("migration_needed"):
                assert len(user1_sessions) >= 1, "User 1 should have at least 1 session"
                assert len(user2_sessions) >= 1, "User 2 should have at least 1 session"
            
            # Test session statistics
            stats = await session_manager.get_statistics()
            print(f"Session statistics: {stats}")
            
            await session_manager.close()
            
        finally:
            os.chdir(original_cwd)
    
    print("✓ Migration integration test passed")


async def test_no_migration_needed():
    """Test that system works correctly when no migration is needed."""
    print("Testing system behavior when no migration is needed...")
    
    # Create session manager in clean environment
    session_service = InMemorySessionService()
    session_manager = VideoSystemSessionManager(
        session_service=session_service,
        run_migration_check=True
    )
    
    # Wait for migration check
    await asyncio.sleep(0.5)
    
    # Check migration status
    migration_status = await session_manager.get_migration_status()
    
    # Should complete without needing migration
    assert migration_status["runtime_migration"]["completed"], "Migration check should complete"
    
    migration_results = migration_status["runtime_migration"]["results"]
    assert not migration_results.get("migration_needed", True), "No migration should be needed"
    
    # Should be able to create new sessions normally
    session_id = await session_manager.create_session("Test prompt for new session")
    assert session_id, "Should be able to create new session"
    
    # Verify session exists
    session_state = await session_manager.get_session_state(session_id)
    assert session_state is not None, "Session should exist"
    assert session_state.request.prompt == "Test prompt for new session"
    
    await session_manager.close()
    
    print("✓ No migration needed test passed")


async def run_integration_tests():
    """Run all integration tests."""
    print("Running migration integration tests...\n")
    
    try:
        await test_migration_integration()
        await test_no_migration_needed()
        
        print("\n✅ All migration integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_integration_tests())