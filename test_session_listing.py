#!/usr/bin/env python3
"""Test script for session listing functionality.

This script tests the new session listing implementation with filtering,
pagination, and registry management.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries.adk_session_manager import (
    VideoSystemSessionManager, get_session_manager
)
from video_system.shared_libraries.adk_session_models import VideoGenerationStage
from video_system.shared_libraries.models import create_default_video_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_session_listing():
    """Test session listing functionality."""
    logger.info("Testing session listing functionality...")
    
    try:
        session_manager = await get_session_manager()
        
        # Create multiple test sessions
        session_ids = []
        users = ["user1", "user2", "user1"]  # user1 has 2 sessions, user2 has 1
        prompts = [
            "Create a video about AI",
            "Make a video about machine learning", 
            "Generate a video about robotics"
        ]
        
        for i, (user, prompt) in enumerate(zip(users, prompts)):
            request = create_default_video_request(prompt)
            session_id = await session_manager.create_session(request, user_id=user)
            session_ids.append(session_id)
            logger.info(f"Created session {i+1}: {session_id} for {user}")
        
        # Update sessions to different stages
        await session_manager.update_stage_and_progress(
            session_ids[0], VideoGenerationStage.COMPLETED, 1.0
        )
        await session_manager.update_stage_and_progress(
            session_ids[1], VideoGenerationStage.RESEARCHING, 0.3
        )
        await session_manager.update_stage_and_progress(
            session_ids[2], VideoGenerationStage.FAILED, 0.5, "Test error"
        )
        
        logger.info("Updated session stages")
        
        # Test 1: List all sessions
        all_sessions = await session_manager.list_sessions()
        logger.info(f"All sessions: {len(all_sessions)} found")
        assert len(all_sessions) == 3, f"Expected 3 sessions, got {len(all_sessions)}"
        
        # Test 2: List sessions by user
        user1_sessions = await session_manager.list_sessions(user_id="user1")
        logger.info(f"User1 sessions: {len(user1_sessions)} found")
        assert len(user1_sessions) == 2, f"Expected 2 sessions for user1, got {len(user1_sessions)}"
        
        user2_sessions = await session_manager.list_sessions(user_id="user2")
        logger.info(f"User2 sessions: {len(user2_sessions)} found")
        assert len(user2_sessions) == 1, f"Expected 1 session for user2, got {len(user2_sessions)}"
        
        # Test 3: List sessions by status
        completed_sessions = await session_manager.list_sessions(status_filter="completed")
        logger.info(f"Completed sessions: {len(completed_sessions)} found")
        assert len(completed_sessions) == 1, f"Expected 1 completed session, got {len(completed_sessions)}"
        
        failed_sessions = await session_manager.list_sessions(status_filter="failed")
        logger.info(f"Failed sessions: {len(failed_sessions)} found")
        assert len(failed_sessions) == 1, f"Expected 1 failed session, got {len(failed_sessions)}"
        
        processing_sessions = await session_manager.list_sessions(status_filter="processing")
        logger.info(f"Processing sessions: {len(processing_sessions)} found")
        assert len(processing_sessions) == 1, f"Expected 1 processing session, got {len(processing_sessions)}"
        
        # Test 4: Test pagination
        paginated_result = await session_manager.list_sessions_paginated(
            page=1, page_size=2
        )
        sessions_page1 = paginated_result["sessions"]
        pagination = paginated_result["pagination"]
        
        logger.info(f"Page 1: {len(sessions_page1)} sessions")
        logger.info(f"Pagination info: {pagination}")
        
        assert len(sessions_page1) == 2, f"Expected 2 sessions on page 1, got {len(sessions_page1)}"
        assert pagination["total_count"] == 3, f"Expected total count 3, got {pagination['total_count']}"
        assert pagination["total_pages"] == 2, f"Expected 2 total pages, got {pagination['total_pages']}"
        assert pagination["has_next"] == True, f"Expected has_next=True"
        assert pagination["has_prev"] == False, f"Expected has_prev=False"
        
        # Test page 2
        paginated_result_page2 = await session_manager.list_sessions_paginated(
            page=2, page_size=2
        )
        sessions_page2 = paginated_result_page2["sessions"]
        pagination2 = paginated_result_page2["pagination"]
        
        logger.info(f"Page 2: {len(sessions_page2)} sessions")
        assert len(sessions_page2) == 1, f"Expected 1 session on page 2, got {len(sessions_page2)}"
        assert pagination2["has_next"] == False, f"Expected has_next=False on page 2"
        assert pagination2["has_prev"] == True, f"Expected has_prev=True on page 2"
        
        # Test 5: Combined filtering (user + status)
        user1_completed = await session_manager.list_sessions(
            user_id="user1", status_filter="completed"
        )
        logger.info(f"User1 completed sessions: {len(user1_completed)} found")
        assert len(user1_completed) == 1, f"Expected 1 completed session for user1, got {len(user1_completed)}"
        
        # Test 6: Test statistics
        stats = await session_manager.get_statistics()
        logger.info(f"Statistics: {stats.model_dump()}")
        
        assert stats.total_sessions == 3, f"Expected 3 total sessions in stats, got {stats.total_sessions}"
        assert stats.completed_sessions == 1, f"Expected 1 completed session in stats, got {stats.completed_sessions}"
        assert stats.failed_sessions == 1, f"Expected 1 failed session in stats, got {stats.failed_sessions}"
        assert stats.active_sessions == 1, f"Expected 1 active session in stats, got {stats.active_sessions}"
        
        # Test 7: Test limit functionality
        limited_sessions = await session_manager.list_sessions(limit=2)
        logger.info(f"Limited sessions (2): {len(limited_sessions)} found")
        assert len(limited_sessions) == 2, f"Expected 2 sessions with limit, got {len(limited_sessions)}"
        
        # Clean up test sessions
        for session_id in session_ids:
            await session_manager.delete_session(session_id)
        
        logger.info("All session listing tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Session listing test failed: {e}")
        return False


async def test_session_registry_management():
    """Test session registry management functionality."""
    logger.info("Testing session registry management...")
    
    try:
        session_manager = await get_session_manager()
        
        # Create a session
        request = create_default_video_request("Test registry management")
        session_id = await session_manager.create_session(request, user_id="registry_test")
        
        # Verify session is in registry
        sessions = await session_manager.list_sessions(user_id="registry_test")
        assert len(sessions) == 1, f"Expected 1 session in registry, got {len(sessions)}"
        
        # Update session and verify registry is updated
        await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.SCRIPTING, 0.4
        )
        
        updated_sessions = await session_manager.list_sessions(user_id="registry_test")
        assert len(updated_sessions) == 1, f"Expected 1 session after update, got {len(updated_sessions)}"
        assert updated_sessions[0].current_stage == VideoGenerationStage.SCRIPTING
        assert updated_sessions[0].progress == 0.4
        
        # Delete session and verify it's removed from registry
        await session_manager.delete_session(session_id)
        
        final_sessions = await session_manager.list_sessions(user_id="registry_test")
        assert len(final_sessions) == 0, f"Expected 0 sessions after deletion, got {len(final_sessions)}"
        
        logger.info("Session registry management tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Session registry management test failed: {e}")
        return False


async def main():
    """Run all session listing tests."""
    logger.info("Starting session listing tests...")
    
    # Test session listing functionality
    listing_test = await test_session_listing()
    
    # Test registry management
    registry_test = await test_session_registry_management()
    
    # Summary
    all_passed = listing_test and registry_test
    logger.info(f"\nTest Results:")
    logger.info(f"  Session Listing: {'PASSED' if listing_test else 'FAILED'}")
    logger.info(f"  Registry Management: {'PASSED' if registry_test else 'FAILED'}")
    logger.info(f"  Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)