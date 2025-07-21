#!/usr/bin/env python3
"""
Targeted test to identify specific issues with the canonical structure.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import canonical structure components
from video_system.agents.video_orchestrator.agent import root_agent as video_orchestrator
from video_system.agents.research_agent.agent import root_agent as research_agent

# Import ADK components
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part


async def test_orchestrator_issue():
    """Test the specific orchestrator coordination issue."""
    print("🔍 Testing orchestrator coordination issue...")
    
    session_service = InMemorySessionService()
    app_name = "video-generation-system"
    user_id = "test-user-001"
    
    # Create session
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id="orchestrator-test",
        state={"prompt": "Create a short video about renewable energy"}
    )
    
    print(f"✅ Session created: {session.id}")
    print(f"📊 Orchestrator agent name: {video_orchestrator.name}")
    print(f"📊 Orchestrator agent type: {type(video_orchestrator)}")
    print(f"📊 Orchestrator has sub_agents: {hasattr(video_orchestrator, 'sub_agents')}")
    
    if hasattr(video_orchestrator, 'sub_agents'):
        print(f"📊 Number of sub-agents: {len(video_orchestrator.sub_agents)}")
        for i, agent in enumerate(video_orchestrator.sub_agents):
            print(f"  - Sub-agent {i}: {agent.name} ({type(agent)})")
    
    # Create runner
    runner = Runner(
        agent=video_orchestrator,
        app_name=app_name,
        session_service=session_service
    )
    
    print("✅ Runner created")
    
    # Test message
    content = Content(parts=[Part(text="Create a 30-second video about solar power benefits")])
    
    print("🚀 Running orchestrator...")
    
    # Run orchestrator and collect events
    events = []
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content
        ):
            events.append(event)
            print(f"📨 Event: author={event.author}, type={type(event)}")
            if event.is_final_response():
                print("🏁 Final response received")
                break
    except Exception as e:
        print(f"❌ Error during orchestrator run: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"📊 Total events: {len(events)}")
    
    # Check session state
    updated_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session.id
    )
    
    print(f"📊 Final session state keys: {list(updated_session.state.keys())}")
    
    return len(events) > 0


async def test_error_handling_issue():
    """Test the error handling issue."""
    print("\n🛡️ Testing error handling issue...")
    
    session_service = InMemorySessionService()
    app_name = "video-generation-system"
    user_id = "test-user-001"
    
    # Test 1: Try to get non-existent session
    try:
        invalid_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id="non-existent-session"
        )
        print("❌ Should have raised error for non-existent session")
        print(f"📊 Got session instead: {invalid_session}")
        return False
    except Exception as e:
        print(f"✅ Correctly handled non-existent session: {type(e).__name__}: {e}")
        return True


async def test_agent_discovery_issue():
    """Test the agent discovery issue."""
    print("\n🔍 Testing agent discovery issue...")
    
    agents = {
        "video_orchestrator": video_orchestrator,
        "research_agent": research_agent,
    }
    
    for agent_name, agent in agents.items():
        print(f"\n📋 Testing {agent_name}:")
        print(f"  - Type: {type(agent)}")
        print(f"  - Has name: {hasattr(agent, 'name')}")
        if hasattr(agent, 'name'):
            print(f"  - Name value: '{agent.name}'")
        print(f"  - Has model: {hasattr(agent, 'model')}")
        if hasattr(agent, 'model'):
            print(f"  - Model value: '{agent.model}'")
        print(f"  - Has instruction: {hasattr(agent, 'instruction')}")
        if hasattr(agent, 'instruction'):
            print(f"  - Instruction length: {len(str(agent.instruction))}")
        
        # Check if it's a SequentialAgent
        if hasattr(agent, 'sub_agents'):
            print(f"  - Is SequentialAgent with {len(agent.sub_agents)} sub-agents")
    
    return True


async def main():
    """Main test execution."""
    print("🎯 Targeted Issue Investigation")
    print("=" * 50)
    
    # Test orchestrator issue
    orchestrator_ok = await test_orchestrator_issue()
    
    # Test error handling issue
    error_handling_ok = await test_error_handling_issue()
    
    # Test agent discovery issue
    discovery_ok = await test_agent_discovery_issue()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print(f"  - Orchestrator coordination: {'✅ OK' if orchestrator_ok else '❌ FAILED'}")
    print(f"  - Error handling: {'✅ OK' if error_handling_ok else '❌ FAILED'}")
    print(f"  - Agent discovery: {'✅ OK' if discovery_ok else '❌ FAILED'}")


if __name__ == "__main__":
    asyncio.run(main())