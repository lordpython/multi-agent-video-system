#!/usr/bin/env python3
"""Test script for async agent functions.

This script tests the async agent functions to ensure they work correctly
with the ADK SessionService integration.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.agent import start_video_generation, execute_complete_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_start_video_generation():
    """Test the async start_video_generation function."""
    logger.info("Testing start_video_generation...")
    
    try:
        result = await start_video_generation(
            prompt="Create a video about artificial intelligence and machine learning",
            duration_preference=60,
            style="professional",
            voice_preference="neutral",
            quality="high",
            user_id="test_user"
        )
        
        logger.info(f"start_video_generation result: {result}")
        
        if result.get('success'):
            session_id = result.get('session_id')
            logger.info(f"Successfully created session: {session_id}")
            return session_id
        else:
            logger.error(f"start_video_generation failed: {result.get('error_message')}")
            return None
            
    except Exception as e:
        logger.error(f"start_video_generation test failed: {e}")
        return None


async def test_execute_complete_workflow(session_id: str):
    """Test the async execute_complete_workflow function."""
    logger.info("Testing execute_complete_workflow...")
    
    try:
        result = await execute_complete_workflow(session_id, user_id="test_user")
        
        logger.info(f"execute_complete_workflow result: {result}")
        
        if result.get('success'):
            logger.info("Workflow execution started successfully")
            return True
        else:
            logger.error(f"execute_complete_workflow failed: {result.get('error_message')}")
            return False
            
    except Exception as e:
        logger.error(f"execute_complete_workflow test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting async agent function tests...")
    
    # Test start_video_generation
    session_id = await test_start_video_generation()
    
    if not session_id:
        logger.error("Failed to create session, skipping workflow test")
        return 1
    
    # Test execute_complete_workflow
    workflow_success = await test_execute_complete_workflow(session_id)
    
    # Summary
    all_passed = session_id is not None and workflow_success
    logger.info(f"\nTest Results:")
    logger.info(f"  start_video_generation: {'PASSED' if session_id else 'FAILED'}")
    logger.info(f"  execute_complete_workflow: {'PASSED' if workflow_success else 'FAILED'}")
    logger.info(f"  Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)