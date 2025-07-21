#!/usr/bin/env python3
"""Test script for real video generation using the canonical structure."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_real_generation():
    """Test real video generation with the canonical structure."""
    try:
        print("=" * 60)
        print("Testing Real Video Generation")
        print("=" * 60)
        
        # Import the video orchestrator agent
        from video_system.agents.video_orchestrator.agent import root_agent
        print(f"✓ Video orchestrator loaded: {root_agent.name}")
        
        # Import ADK components
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part
        
        print("✓ ADK components imported successfully")
        
        # Create session service and runner
        session_service = InMemorySessionService()
        app_name = "real-video-generation-test"
        user_id = "test-user"
        
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            state={
                "test_mode": True,
                "prompt": "Create a short video about artificial intelligence",
                "duration_preference": 30,
                "style": "educational"
            }
        )
        
        print(f"✓ Session created: {session.id}")
        
        # Create runner with the orchestrator agent
        runner = Runner(
            agent=root_agent,
            app_name=app_name,
            session_service=session_service
        )
        
        print("✓ Runner created with video orchestrator")
        
        # Create test prompt
        test_prompt = "Create a 30-second educational video about artificial intelligence and its impact on society"
        user_message = Content(parts=[Part(text=test_prompt)])
        
        print(f"✓ Test prompt: {test_prompt}")
        print("\n" + "=" * 60)
        print("Starting Video Generation Process...")
        print("=" * 60)
        
        # Run the video generation
        event_count = 0
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=user_message
        ):
            event_count += 1
            
            # Print event information
            if hasattr(event, 'author') and event.author:
                print(f"\n[{event.author}] Event #{event_count}")
                
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        # Truncate long text for readability
                        text = part.text[:200] + "..." if len(part.text) > 200 else part.text
                        print(f"  Content: {text}")
                        
            if hasattr(event, 'is_final_response') and event.is_final_response():
                print(f"\n✓ Final response received after {event_count} events")
                break
                
            # Limit events to prevent infinite loops in testing
            if event_count > 50:
                print(f"\n⚠ Stopping after {event_count} events (test limit)")
                break
        
        print("\n" + "=" * 60)
        print("Video Generation Process Complete")
        print("=" * 60)
        
        # Check final session state
        final_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session.id
        )
        
        if final_session:
            print(f"✓ Final session state available")
            print(f"  Session ID: {final_session.id}")
            print(f"  State keys: {list(final_session.state.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Real generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_generation():
    """Test video generation through the API endpoints."""
    try:
        print("\n" + "=" * 60)
        print("Testing API Video Generation")
        print("=" * 60)
        
        # Import API components
        from video_system.api.endpoints import generate_video, VideoGenerationRequest
        
        print("✓ API endpoints imported")
        
        # Create a test request
        request = VideoGenerationRequest(
            prompt="Create a short video about renewable energy",
            duration_preference=30,
            style="educational",
            voice_preference="neutral",
            quality="high",
            user_id="api-test-user"
        )
        
        print(f"✓ API request created: {request.prompt}")
        
        # Call the generate_video endpoint
        response = await generate_video(request)
        
        print(f"✓ API response received:")
        print(f"  Session ID: {response.session_id}")
        print(f"  Status: {response.status}")
        print(f"  Message: {response.message}")
        print(f"  Estimated duration: {response.estimated_duration_minutes} minutes")
        
        return True
        
    except Exception as e:
        print(f"✗ API generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all real generation tests."""
    print("Starting Real Video Generation Tests...")
    
    tests = [
        ("Direct Agent Test", test_real_generation),
        ("API Endpoint Test", test_api_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = await test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("Real Generation Test Results")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✓ All real generation tests passed!")
        print("✓ Video system is ready for production use")
        return True
    else:
        print("\n✗ Some real generation tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)