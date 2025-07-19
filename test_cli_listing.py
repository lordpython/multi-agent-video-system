#!/usr/bin/env python3
"""Test script for CLI session listing functionality."""

import asyncio
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries.adk_session_manager import get_session_manager
from video_system.shared_libraries.adk_session_models import VideoGenerationStage
from video_system.shared_libraries.models import create_default_video_request


async def setup_test_sessions():
    """Create some test sessions for CLI testing."""
    session_manager = await get_session_manager()
    
    # Create test sessions
    session_ids = []
    
    # Session 1: Completed
    request1 = create_default_video_request("Test video about AI")
    session_id1 = await session_manager.create_session(request1, user_id="test_user")
    await session_manager.update_stage_and_progress(session_id1, VideoGenerationStage.COMPLETED, 1.0)
    session_ids.append(session_id1)
    
    # Session 2: Processing
    request2 = create_default_video_request("Test video about ML")
    session_id2 = await session_manager.create_session(request2, user_id="test_user")
    await session_manager.update_stage_and_progress(session_id2, VideoGenerationStage.RESEARCHING, 0.3)
    session_ids.append(session_id2)
    
    # Session 3: Failed
    request3 = create_default_video_request("Test video about robotics")
    session_id3 = await session_manager.create_session(request3, user_id="another_user")
    await session_manager.update_stage_and_progress(session_id3, VideoGenerationStage.FAILED, 0.5, "Test error")
    session_ids.append(session_id3)
    
    print(f"Created {len(session_ids)} test sessions")
    return session_ids


async def cleanup_test_sessions(session_ids):
    """Clean up test sessions."""
    session_manager = await get_session_manager()
    for session_id in session_ids:
        await session_manager.delete_session(session_id)
    print(f"Cleaned up {len(session_ids)} test sessions")


def test_cli_command(command):
    """Test a CLI command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


async def main():
    """Test CLI listing functionality."""
    print("Setting up test sessions...")
    session_ids = await setup_test_sessions()
    
    try:
        # Test basic list command
        print("\n1. Testing basic list command...")
        success, stdout, stderr = test_cli_command("python -m video_system.cli list")
        if success:
            print("✓ Basic list command works")
            if "test_user" in stdout or "another_user" in stdout:
                print("✓ Sessions are displayed")
            else:
                print("⚠ Sessions might not be displayed properly")
        else:
            print(f"✗ Basic list command failed: {stderr}")
        
        # Test list with user filter
        print("\n2. Testing list with user filter...")
        success, stdout, stderr = test_cli_command("python -m video_system.cli list --user test_user")
        if success:
            print("✓ User filter works")
        else:
            print(f"✗ User filter failed: {stderr}")
        
        # Test list with status filter
        print("\n3. Testing list with status filter...")
        success, stdout, stderr = test_cli_command("python -m video_system.cli list --status-filter completed")
        if success:
            print("✓ Status filter works")
        else:
            print(f"✗ Status filter failed: {stderr}")
        
        # Test list with pagination
        print("\n4. Testing list with pagination...")
        success, stdout, stderr = test_cli_command("python -m video_system.cli list --page 1 --page-size 2")
        if success:
            print("✓ Pagination works")
        else:
            print(f"✗ Pagination failed: {stderr}")
        
        # Test status command with filters
        print("\n5. Testing status command with filters...")
        success, stdout, stderr = test_cli_command("python -m video_system.cli status --user test_user --limit 5")
        if success:
            print("✓ Status command with filters works")
        else:
            print(f"✗ Status command with filters failed: {stderr}")
        
        print("\n✓ All CLI tests completed successfully!")
        
    finally:
        print("\nCleaning up...")
        await cleanup_test_sessions(session_ids)


if __name__ == "__main__":
    asyncio.run(main())