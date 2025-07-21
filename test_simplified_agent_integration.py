#!/usr/bin/env python3
"""Test script to verify simplified agent integration works."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.agent_simplified import root_agent_simplified


async def test_agent_tools():
    """Test that the simplified agent has the correct tools configured."""
    print("Testing simplified agent configuration...")
    
    # Check that agent has tools
    assert hasattr(root_agent_simplified, 'tools'), "Agent should have tools"
    assert len(root_agent_simplified.tools) == 5, f"Expected 5 tools, got {len(root_agent_simplified.tools)}"
    
    # Check tool names
    tool_names = []
    for tool in root_agent_simplified.tools:
        if hasattr(tool, 'func') and hasattr(tool.func, '__name__'):
            tool_names.append(tool.func.__name__)
    
    expected_tools = [
        'coordinate_research',
        'coordinate_story', 
        'coordinate_assets',
        'coordinate_audio',
        'coordinate_assembly'
    ]
    
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
    
    print("✅ Agent has all required tools configured correctly")
    
    # Check agent configuration
    assert root_agent_simplified.name == 'video_system_orchestrator_simplified'
    assert root_agent_simplified.model == 'gemini-2.5-pro'
    assert root_agent_simplified.instruction is not None
    
    print("✅ Agent configuration is correct")
    print(f"Agent name: {root_agent_simplified.name}")
    print(f"Agent model: {root_agent_simplified.model}")
    print(f"Number of tools: {len(root_agent_simplified.tools)}")
    print(f"Tool names: {tool_names}")
    
    return True


async def main():
    """Run agent integration tests."""
    print("=" * 60)
    print("TESTING SIMPLIFIED AGENT INTEGRATION")
    print("=" * 60)
    
    success = await test_agent_tools()
    
    if success:
        print("\n🎉 Agent integration tests completed successfully!")
        print("Simplified agent is properly configured with error-handling-free tools.")
        return 0
    else:
        print("\n💥 Agent integration tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)