#!/usr/bin/env python3
"""Test script to verify session management fixes."""

import asyncio
import logging
from video_system.shared_libraries.adk_session_manager import get_session_manager
from video_system.shared_libraries.models import VideoGenerationRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_session_management():
    """Test session creation, lookup, and state management."""
    print("🔧 Testing Session Management Fixes...")
    
    try:
        # Get session manager
        session_manager = await get_session_manager()
        print("✅ Session manager initialized")
        
        # Create a test request
        request = VideoGenerationRequest(
            prompt="Test video generation for session management",
            duration_preference=60,
            style="professional"
        )
        
        # Test 1: Create session
        print("\n1. Testing session creation...")
        session_id = await session_manager.create_session(request, "test_user")
        print(f"✅ Session created: {session_id}")
        
        # Test 2: Retrieve session immediately
        print("\n2. Testing immediate session retrieval...")
        session = await session_manager.get_session(session_id)
        if session:
            print(f"✅ Session retrieved: {session.id}")
        else:
            print("❌ Session not found immediately after creation")
            return False
        
        # Test 3: Get session state
        print("\n3. Testing session state retrieval...")
        state = await session_manager.get_session_state(session_id)
        if state:
            print(f"✅ Session state retrieved: {state.current_stage}")
        else:
            print("❌ Session state not found")
            return False
        
        # Test 4: Update session state
        print("\n4. Testing session state update...")
        from video_system.shared_libraries.adk_session_models import VideoGenerationStage
        success = await session_manager.update_stage_and_progress(
            session_id, 
            VideoGenerationStage.RESEARCHING, 
            0.1
        )
        if success:
            print("✅ Session state updated successfully")
        else:
            print("❌ Session state update failed")
            return False
        
        # Test 5: Verify state update
        print("\n5. Testing state update verification...")
        updated_state = await session_manager.get_session_state(session_id)
        if updated_state and updated_state.current_stage == VideoGenerationStage.RESEARCHING:
            print(f"✅ State update verified: {updated_state.current_stage}")
        else:
            print("❌ State update verification failed")
            return False
        
        # Test 6: Test session not found scenario
        print("\n6. Testing session not found handling...")
        non_existent = await session_manager.get_session("non-existent-session")
        if non_existent is None:
            print("✅ Non-existent session handled correctly")
        else:
            print("❌ Non-existent session should return None")
            return False
        
        # Test 7: Test session listing
        print("\n7. Testing session listing...")
        sessions = await session_manager.list_sessions(user_id="test_user")
        if sessions and len(sessions) > 0:
            print(f"✅ Session listing works: {len(sessions)} sessions found")
        else:
            print("❌ Session listing failed")
            return False
        
        # Cleanup
        print("\n8. Cleaning up...")
        await session_manager.delete_session(session_id)
        print("✅ Session deleted")
        
        print("\n🎉 All session management tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
        logger.exception("Session management test error")
        return False

async def test_video_generation_workflow():
    """Test the video generation workflow session integration."""
    print("\n🎬 Testing Video Generation Workflow...")
    
    try:
        # Test session creation through the agent
        from video_system.agent import start_video_generation
        
        result = await start_video_generation(
            prompt="Test video about sustainable technology",
            duration_preference=30,
            style="professional",
            user_id="workflow_test_user"
        )
        
        if result.get('success'):
            session_id = result['session_id']
            print(f"✅ Video generation session created: {session_id}")
            
            # Test session retrieval through orchestration tools
            from video_system.orchestration_tools import get_session_state
            
            state = await get_session_state(session_id)
            if state:
                print(f"✅ Session state accessible through orchestration: {state.current_stage}")
            else:
                print("❌ Session state not accessible through orchestration")
                return False
            
            # Test workflow execution
            from video_system.agent import execute_complete_workflow
            
            workflow_result = await execute_complete_workflow(session_id)
            if workflow_result.get('success'):
                print("✅ Workflow execution started successfully")
            else:
                print(f"❌ Workflow execution failed: {workflow_result.get('error_message')}")
                return False
            
            # Cleanup
            session_manager = await get_session_manager()
            await session_manager.delete_session(session_id)
            print("✅ Workflow session cleaned up")
            
            return True
        else:
            print(f"❌ Video generation session creation failed: {result.get('error_message')}")
            return False
            
    except Exception as e:
        print(f"❌ Video generation workflow test failed: {e}")
        logger.exception("Video generation workflow test error")
        return False

async def main():
    """Run all session management tests."""
    print("🚀 Starting Session Management Fix Verification")
    print("=" * 60)
    
    # Test basic session management
    session_test_passed = await test_session_management()
    
    # Test video generation workflow
    workflow_test_passed = await test_video_generation_workflow()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Session Management: {'✅ PASSED' if session_test_passed else '❌ FAILED'}")
    print(f"  Video Generation Workflow: {'✅ PASSED' if workflow_test_passed else '❌ FAILED'}")
    
    if session_test_passed and workflow_test_passed:
        print("\n🎉 All tests passed! Session management is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Session management needs attention.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)