#!/usr/bin/env python3
"""Test script for ADK SessionService integration.

This script tests the new ADK SessionService infrastructure to ensure
it's working correctly with the video generation system.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries.adk_config import (
    ADKConfig, get_adk_service_manager, validate_adk_configuration
)
from video_system.shared_libraries.adk_session_manager import (
    VideoSystemSessionManager, get_session_manager
)
from video_system.shared_libraries.adk_session_models import (
    VideoGenerationState, VideoGenerationStage
)
from video_system.shared_libraries.models import create_default_video_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_adk_configuration():
    """Test ADK configuration and service setup."""
    logger.info("Testing ADK configuration...")
    
    # Test configuration validation
    is_valid = validate_adk_configuration()
    logger.info(f"Configuration validation: {'PASSED' if is_valid else 'FAILED'}")
    
    # Get service manager and display environment info
    service_manager = get_adk_service_manager()
    env_info = service_manager.get_environment_info()
    
    logger.info("Environment Information:")
    for key, value in env_info.items():
        logger.info(f"  {key}: {value}")
    
    return is_valid


async def test_session_creation():
    """Test session creation and state management."""
    logger.info("Testing session creation...")
    
    try:
        # Create a video generation request
        request = create_default_video_request("Create a video about artificial intelligence")
        
        # Get session manager
        session_manager = await get_session_manager()
        
        # Create a new session
        session_id = await session_manager.create_session(request, user_id="test_user")
        logger.info(f"Created session: {session_id}")
        
        # Get session state
        state = await session_manager.get_session_state(session_id)
        if state:
            logger.info(f"Session state retrieved: stage={state.current_stage}, progress={state.progress}")
        else:
            logger.error("Failed to retrieve session state")
            return False
        
        # Update session stage
        success = await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.RESEARCHING,
            0.2
        )
        logger.info(f"Stage update: {'SUCCESS' if success else 'FAILED'}")
        
        # Get updated state
        updated_state = await session_manager.get_session_state(session_id)
        if updated_state:
            logger.info(f"Updated state: stage={updated_state.current_stage}, progress={updated_state.progress}")
        
        # Get session status
        status = await session_manager.get_session_status(session_id)
        if status:
            logger.info(f"Session status: {status.model_dump()}")
        
        # Clean up
        await session_manager.delete_session(session_id)
        logger.info("Session deleted successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Session creation test failed: {e}")
        return False


async def test_session_state_updates():
    """Test session state updates with video generation data."""
    logger.info("Testing session state updates...")
    
    try:
        session_manager = await get_session_manager()
        
        # Create session
        request = create_default_video_request("Test video about machine learning")
        session_id = await session_manager.create_session(request, user_id="test_user_2")
        
        # Test updating with research data
        from video_system.shared_libraries.models import ResearchData
        research_data = ResearchData(
            facts=["AI is transforming industries", "Machine learning is a subset of AI"],
            sources=["https://example.com/ai-facts"],
            key_points=["AI applications", "ML algorithms"],
            context={"test": True}
        )
        
        success = await session_manager.update_session_state(
            session_id,
            research_data=research_data,
            current_stage=VideoGenerationStage.SCRIPTING,
            progress=0.4
        )
        logger.info(f"Research data update: {'SUCCESS' if success else 'FAILED'}")
        
        # Verify the update
        state = await session_manager.get_session_state(session_id)
        if state and state.research_data:
            logger.info(f"Research data verified: {len(state.research_data.facts)} facts")
        
        # Test error handling
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message="Test error for demonstration"
        )
        
        final_state = await session_manager.get_session_state(session_id)
        if final_state:
            logger.info(f"Error state: {final_state.error_message}")
        
        # Clean up
        await session_manager.delete_session(session_id)
        
        return True
        
    except Exception as e:
        logger.error(f"Session state update test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting ADK SessionService integration tests...")
    
    # Test configuration
    config_test = await test_adk_configuration()
    
    # Test session creation
    session_test = await test_session_creation()
    
    # Test state updates
    state_test = await test_session_state_updates()
    
    # Summary
    all_passed = config_test and session_test and state_test
    logger.info(f"\nTest Results:")
    logger.info(f"  Configuration: {'PASSED' if config_test else 'FAILED'}")
    logger.info(f"  Session Creation: {'PASSED' if session_test else 'FAILED'}")
    logger.info(f"  State Updates: {'PASSED' if state_test else 'FAILED'}")
    logger.info(f"  Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)