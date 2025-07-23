#!/usr/bin/env python3
"""Test script to verify orchestration tools use event-based state updates."""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.orchestration_tools import (
    create_session_state,
    coordinate_research,
    get_session_state,
)
from video_system.shared_libraries.models import create_default_video_request
from video_system.shared_libraries.adk_session_manager import get_session_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_orchestration_event_updates():
    """Test that orchestration tools use proper event-based state updates."""
    logger.info("Testing orchestration tools event-based updates...")

    try:
        # Create a test session
        request = create_default_video_request("Test orchestration events")
        session_id = await create_session_state(request, user_id="test_user")
        logger.info(f"Created session: {session_id}")

        # Get session manager to check events
        session_manager = await get_session_manager()
        session = await session_manager.get_session(session_id)
        initial_event_count = len(session.events)
        logger.info(f"Initial event count: {initial_event_count}")

        # Run coordinate_research which should update state via events
        result = await coordinate_research("artificial intelligence", session_id)
        logger.info(f"Research coordination result: {result['success']}")

        # Check that events were added
        updated_session = await session_manager.get_session(session_id)
        final_event_count = len(updated_session.events)
        logger.info(f"Event count after research coordination: {final_event_count}")

        if final_event_count > initial_event_count:
            logger.info(
                "✅ Orchestration tools created new events - using append_event correctly"
            )

            # Check the latest events for proper state_delta
            new_events = updated_session.events[initial_event_count:]
            for i, event in enumerate(new_events):
                if event.actions and event.actions.state_delta:
                    logger.info(
                        f"✅ Event {i} has state_delta: {list(event.actions.state_delta.keys())}"
                    )
                else:
                    logger.warning(f"⚠️ Event {i} missing state_delta")
        else:
            logger.error(
                "❌ Orchestration tools did not create new events - not using append_event"
            )
            return False

        # Verify the session state was updated correctly
        final_state = await get_session_state(session_id)
        if (
            final_state
            and hasattr(final_state, "research_data")
            and final_state.research_data
        ):
            logger.info("✅ Session state updated with research data")
        else:
            logger.error("❌ Session state not updated properly")
            return False

        # Clean up
        await session_manager.delete_session(session_id)
        logger.info("✅ Orchestration event test completed successfully")

        return True

    except Exception as e:
        logger.error(f"❌ Orchestration event test failed: {e}")
        return False


async def main():
    """Run the orchestration event test."""
    logger.info("Starting orchestration tools event verification...")

    success = await test_orchestration_event_updates()

    if success:
        logger.info("🎉 ORCHESTRATION EVENT TESTS PASSED!")
        return 0
    else:
        logger.error("💥 ORCHESTRATION EVENT TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
