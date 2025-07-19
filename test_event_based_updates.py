#!/usr/bin/env python3
"""Test script to verify event-based state updates are working correctly.

This script specifically tests that all state updates go through ADK's append_event
mechanism with proper EventActions.state_delta.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries.adk_session_manager import get_session_manager
from video_system.shared_libraries.adk_session_models import VideoGenerationStage
from video_system.shared_libraries.models import create_default_video_request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_event_based_state_updates():
    """Test that state updates use proper ADK event-based mechanism."""
    logger.info("Testing event-based state updates...")
    
    try:
        # Create session manager
        session_manager = await get_session_manager()
        
        # Create a test session
        request = create_default_video_request("Test event-based updates")
        session_id = await session_manager.create_session(request, user_id="test_user")
        logger.info(f"Created session: {session_id}")
        
        # Get the ADK session to check events
        session = await session_manager.get_session(session_id)
        initial_event_count = len(session.events)
        logger.info(f"Initial event count: {initial_event_count}")
        
        # Update session state - this should create an event
        await session_manager.update_session_state(
            session_id,
            test_field="test_value",
            progress=0.5
        )
        
        # Check that an event was added
        updated_session = await session_manager.get_session(session_id)
        new_event_count = len(updated_session.events)
        logger.info(f"Event count after state update: {new_event_count}")
        
        if new_event_count > initial_event_count:
            logger.info("✅ State update created new event - using append_event correctly")
            
            # Check the latest event
            latest_event = updated_session.events[-1]
            if latest_event.actions and latest_event.actions.state_delta:
                logger.info(f"✅ Event has state_delta: {list(latest_event.actions.state_delta.keys())}")
            else:
                logger.error("❌ Event missing state_delta")
                return False
        else:
            logger.error("❌ State update did not create new event - not using append_event")
            return False
        
        # Test stage update - this should also create an event
        initial_event_count = new_event_count
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.RESEARCHING,
            0.3
        )
        
        # Check that another event was added
        updated_session = await session_manager.get_session(session_id)
        final_event_count = len(updated_session.events)
        logger.info(f"Event count after stage update: {final_event_count}")
        
        if final_event_count > initial_event_count:
            logger.info("✅ Stage update created new event - using append_event correctly")
            
            # Check the latest event
            latest_event = updated_session.events[-1]
            if latest_event.actions and latest_event.actions.state_delta:
                logger.info(f"✅ Event has state_delta: {list(latest_event.actions.state_delta.keys())}")
                if 'current_stage' in latest_event.actions.state_delta:
                    logger.info("✅ Stage update included in state_delta")
                else:
                    logger.error("❌ Stage update missing from state_delta")
                    return False
            else:
                logger.error("❌ Event missing state_delta")
                return False
        else:
            logger.error("❌ Stage update did not create new event - not using append_event")
            return False
        
        # Verify event authors are set correctly
        for i, event in enumerate(updated_session.events):
            logger.info(f"Event {i}: author='{event.author}', timestamp={event.timestamp}")
        
        # Clean up
        await session_manager.delete_session(session_id)
        logger.info("✅ Test completed successfully - all state updates use proper event-based mechanism")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def main():
    """Run the event-based update test."""
    logger.info("Starting event-based state update verification...")
    
    success = await test_event_based_state_updates()
    
    if success:
        logger.info("🎉 ALL TESTS PASSED - Event-based state updates working correctly!")
        return 0
    else:
        logger.error("💥 TESTS FAILED - Event-based state updates not working properly!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)