#!/usr/bin/env python3
"""Test script for API async functionality.

This script tests the API endpoints to ensure they work correctly
with the async agent functions.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx
from httpx import ASGITransport
from video_system.api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_api_video_generation():
    """Test the API video generation endpoint."""
    logger.info("Testing API video generation endpoint...")
    
    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test video generation request
            request_data = {
                "prompt": "Create a video about artificial intelligence",
                "duration_preference": 60,
                "style": "professional",
                "voice_preference": "neutral",
                "quality": "high",
                "user_id": "test_user"
            }
            
            response = await client.post("/videos/generate", json=request_data)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.json()}")
            
            if response.status_code == 200:
                data = response.json()
                session_id = data.get('session_id')
                logger.info(f"Successfully created session: {session_id}")
                return session_id
            else:
                logger.error(f"API request failed: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"API test failed: {e}")
        return None


async def test_api_session_status(session_id: str):
    """Test the API session status endpoint."""
    logger.info("Testing API session status endpoint...")
    
    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/videos/{session_id}/status")
            logger.info(f"Status response: {response.status_code}")
            logger.info(f"Status body: {response.json()}")
            
            if response.status_code == 200:
                logger.info("Session status retrieved successfully")
                return True
            else:
                logger.error(f"Status request failed: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Status test failed: {e}")
        return False


async def test_api_health_check():
    """Test the API health check endpoint."""
    logger.info("Testing API health check endpoint...")
    
    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            logger.info(f"Health response: {response.status_code}")
            logger.info(f"Health body: {response.json()}")
            
            if response.status_code == 200:
                logger.info("Health check passed")
                return True
            else:
                logger.error(f"Health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Health check test failed: {e}")
        return False


async def main():
    """Run all API tests."""
    logger.info("Starting API async functionality tests...")
    
    # Test health check
    health_test = await test_api_health_check()
    
    # Test video generation
    session_id = await test_api_video_generation()
    
    # Test session status if we have a session
    status_test = False
    if session_id:
        status_test = await test_api_session_status(session_id)
    
    # Summary
    all_passed = health_test and session_id is not None and status_test
    logger.info("\nTest Results:")
    logger.info(f"  Health Check: {'PASSED' if health_test else 'FAILED'}")
    logger.info(f"  Video Generation: {'PASSED' if session_id else 'FAILED'}")
    logger.info(f"  Session Status: {'PASSED' if status_test else 'FAILED'}")
    logger.info(f"  Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)