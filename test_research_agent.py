#!/usr/bin/env python3
"""
Test script to verify the research agent can be discovered and run independently.
"""

import sys
import os
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

def test_research_agent_import():
    """Test that the research agent can be imported successfully."""
    print("🧪 Testing Research Agent Import")
    print("=" * 50)
    
    try:
        from src.video_system.agents.research_agent.agent import root_agent
        print(f"✅ Research agent imported successfully: {root_agent.name}")
        print(f"✅ Agent type: {type(root_agent).__name__}")
        print(f"✅ Agent description: {root_agent.description}")
        print(f"✅ Agent model: {root_agent.model}")
        print(f"✅ Number of tools: {len(root_agent.tools) if root_agent.tools else 0}")
        return True
    except Exception as e:
        print(f"❌ Failed to import research agent: {str(e)}")
        return False

async def test_research_agent_execution():
    """Test that the research agent can execute a simple query."""
    print("\n🧪 Testing Research Agent Execution")
    print("=" * 50)
    
    try:
        from src.video_system.agents.research_agent.agent import root_agent
        
        # Create session service and session
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="test_research_agent",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Create runner
        runner = Runner(
            agent=root_agent,
            app_name="test_research_agent", 
            session_service=session_service
        )
        
        # Test query
        test_query = "What is artificial intelligence?"
        print(f"🔍 Testing query: '{test_query}'")
        
        # Create content
        content = types.Content(
            role='user',
            parts=[types.Part(text=test_query)]
        )
        
        # Run the agent
        events = runner.run_async(
            user_id="test_user",
            session_id="test_session", 
            new_message=content
        )
        
        response_found = False
        async for event in events:
            if event.is_final_response():
                response_text = event.content.parts[0].text if event.content and event.content.parts else "No response"
                print(f"✅ Agent responded: {response_text[:100]}...")
                response_found = True
                break
        
        if not response_found:
            print("❌ No response received from agent")
            return False
            
        print("✅ Research agent execution test passed")
        return True
        
    except Exception as e:
        print(f"❌ Research agent execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_adk_discovery():
    """Test that ADK can discover the research agent."""
    print("\n🧪 Testing ADK Discovery")
    print("=" * 50)
    
    # Check if the agent directory structure is correct
    agent_dir = "src/video_system/agents/research_agent"
    
    if not os.path.exists(agent_dir):
        print(f"❌ Agent directory does not exist: {agent_dir}")
        return False
    
    agent_file = os.path.join(agent_dir, "agent.py")
    if not os.path.exists(agent_file):
        print(f"❌ Agent file does not exist: {agent_file}")
        return False
        
    init_file = os.path.join(agent_dir, "__init__.py")
    if not os.path.exists(init_file):
        print(f"❌ Init file does not exist: {init_file}")
        return False
    
    # Check that init file has correct import
    with open(init_file, 'r') as f:
        init_content = f.read()
        if "from . import agent" not in init_content:
            print("❌ Init file does not contain 'from . import agent'")
            return False
    
    # Check that agent file has root_agent
    with open(agent_file, 'r') as f:
        agent_content = f.read()
        if "root_agent =" not in agent_content:
            print("❌ Agent file does not contain 'root_agent =' definition")
            return False
    
    print("✅ Agent directory structure is correct")
    print("✅ Agent file contains root_agent definition")
    print("✅ Init file contains correct import")
    print("✅ Ready for ADK discovery")
    
    return True

async def main():
    """Run all tests."""
    print("🧪 Testing Research Agent Migration to Canonical Structure")
    print("=" * 70)
    
    # Test 1: Import
    import_success = test_research_agent_import()
    
    # Test 2: ADK Discovery Structure
    discovery_success = test_adk_discovery()
    
    # Test 3: Execution
    execution_success = await test_research_agent_execution() if import_success else False
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Import Test: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"ADK Discovery Test: {'✅ PASS' if discovery_success else '❌ FAIL'}")
    print(f"Execution Test: {'✅ PASS' if execution_success else '❌ FAIL'}")
    
    all_passed = import_success and discovery_success and execution_success
    
    if all_passed:
        print("\n🎉 SUCCESS: All tests passed!")
        print("✅ Research agent is properly migrated to canonical structure")
        print("✅ Research agent can be discovered and run independently")
        print("✅ Ready for ADK commands like 'adk run src/video_system/agents/research_agent'")
    else:
        print("\n💥 FAILURE: Some tests failed!")
        print("❌ Research agent migration needs fixes")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)