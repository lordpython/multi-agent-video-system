#!/usr/bin/env python3
"""Comprehensive test for async agent integration.

This script tests the complete async integration including:
- Agent functions
- CLI integration
- API integration
- Session management
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.agent import start_video_generation, execute_complete_workflow
from video_system.orchestration_tools import (
    coordinate_research,
    coordinate_story,
    coordinate_assets,
    coordinate_audio,
    coordinate_assembly,
    get_session_status,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_complete_workflow():
    """Test the complete async workflow from start to finish."""
    logger.info("Testing complete async workflow...")

    try:
        # Step 1: Start video generation
        logger.info("Step 1: Starting video generation...")
        result = await start_video_generation(
            prompt="Create an educational video about renewable energy",
            duration_preference=90,
            style="educational",
            voice_preference="neutral",
            quality="high",
            user_id="integration_test",
        )

        if not result.get("success"):
            logger.error(
                f"Failed to start video generation: {result.get('error_message')}"
            )
            return False

        session_id = result["session_id"]
        logger.info(f"✓ Video generation started, session: {session_id}")

        # Step 2: Execute workflow
        logger.info("Step 2: Executing complete workflow...")
        workflow_result = await execute_complete_workflow(
            session_id, user_id="integration_test"
        )

        if not workflow_result.get("success"):
            logger.error(
                f"Failed to execute workflow: {workflow_result.get('error_message')}"
            )
            return False

        logger.info("✓ Workflow execution started")

        # Step 3: Test orchestration tools
        logger.info("Step 3: Testing orchestration tools...")

        # Research phase
        research_result = await coordinate_research("renewable energy", session_id)
        if not research_result.get("success"):
            logger.error(f"Research failed: {research_result.get('error_message')}")
            return False
        logger.info("✓ Research coordination completed")

        # Story phase
        story_result = await coordinate_story(
            research_result["research_data"], session_id, 90
        )
        if not story_result.get("success"):
            logger.error(f"Story failed: {story_result.get('error_message')}")
            return False
        logger.info("✓ Story coordination completed")

        # Assets phase
        assets_result = await coordinate_assets(story_result["script"], session_id)
        if not assets_result.get("success"):
            logger.error(f"Assets failed: {assets_result.get('error_message')}")
            return False
        logger.info("✓ Assets coordination completed")

        # Audio phase
        audio_result = await coordinate_audio(story_result["script"], session_id)
        if not audio_result.get("success"):
            logger.error(f"Audio failed: {audio_result.get('error_message')}")
            return False
        logger.info("✓ Audio coordination completed")

        # Assembly phase
        assembly_result = await coordinate_assembly(
            story_result["script"],
            assets_result["assets"],
            audio_result["audio_assets"],
            session_id,
        )
        if not assembly_result.get("success"):
            logger.error(f"Assembly failed: {assembly_result.get('error_message')}")
            return False
        logger.info("✓ Assembly coordination completed")

        # Step 4: Check final status
        logger.info("Step 4: Checking final session status...")
        status_result = await get_session_status(session_id)
        if not status_result.get("success"):
            logger.error(f"Status check failed: {status_result.get('error_message')}")
            return False

        final_status = status_result["status"]
        logger.info(f"✓ Final session status: {final_status['status']}")

        return True

    except Exception as e:
        logger.error(f"Complete workflow test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling in async functions."""
    logger.info("Testing error handling...")

    try:
        # Test invalid prompt
        result = await start_video_generation(
            prompt="",  # Empty prompt should fail
            duration_preference=60,
            style="professional",
            voice_preference="neutral",
            quality="high",
        )

        if result.get("success"):
            logger.error("Expected failure for empty prompt, but got success")
            return False

        logger.info("✓ Empty prompt validation works correctly")

        # Test invalid duration
        result = await start_video_generation(
            prompt="Valid prompt",
            duration_preference=1000,  # Too long, should fail
            style="professional",
            voice_preference="neutral",
            quality="high",
        )

        if result.get("success"):
            logger.error("Expected failure for invalid duration, but got success")
            return False

        logger.info("✓ Duration validation works correctly")

        # Test invalid session ID
        workflow_result = await execute_complete_workflow("invalid-session-id")

        if workflow_result.get("success"):
            logger.error("Expected failure for invalid session ID, but got success")
            return False

        logger.info("✓ Invalid session ID handling works correctly")

        return True

    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    logger.info("Starting comprehensive async integration tests...")

    # Test complete workflow
    workflow_test = await test_complete_workflow()

    # Test error handling
    error_test = await test_error_handling()

    # Summary
    all_passed = workflow_test and error_test
    logger.info("\nIntegration Test Results:")
    logger.info(f"  Complete Workflow: {'PASSED' if workflow_test else 'FAILED'}")
    logger.info(f"  Error Handling: {'PASSED' if error_test else 'FAILED'}")
    logger.info(
        f"  Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}"
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
