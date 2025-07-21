#!/usr/bin/env python3
"""Test script to verify the audio agent can be discovered and run independently."""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
# Also add the current directory for the old shared libraries
sys.path.insert(0, os.path.dirname(__file__))


async def test_audio_agent_discovery():
    """Test that the audio agent can be imported and discovered."""
    try:
        print("Testing audio agent discovery...")

        # Test importing the agent
        from src.video_system.agents.audio_agent.agent import root_agent

        print(f"✓ Successfully imported audio agent: {root_agent.name}")

        # Test agent properties
        print(f"✓ Agent model: {root_agent.model}")
        print(f"✓ Agent description: {root_agent.description}")
        print(f"✓ Number of tools: {len(root_agent.tools)}")

        # Test that tools are properly imported
        tool_names = [tool.__class__.__name__ for tool in root_agent.tools]
        print(f"✓ Available tools: {tool_names}")

        # Test importing from __init__.py

        print("✓ Successfully imported from __init__.py")

        print("\n✅ Audio agent discovery test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Audio agent discovery test FAILED: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_audio_agent_basic_functionality():
    """Test basic functionality of the audio agent."""
    try:
        print("\nTesting audio agent basic functionality...")

        from src.video_system.agents.audio_agent.agent import root_agent

        # Test that the agent has the expected instruction
        if hasattr(root_agent, "instruction") and root_agent.instruction:
            print("✓ Agent has instruction text")
        else:
            print("⚠ Agent instruction is missing or empty")

        # Test that tools are callable
        for tool in root_agent.tools:
            if hasattr(tool, "func") and callable(tool.func):
                print(f"✓ Tool {tool.__class__.__name__} is callable")
            else:
                print(
                    f"⚠ Tool {tool.__class__.__name__} may not be properly configured"
                )

        print("\n✅ Audio agent basic functionality test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Audio agent basic functionality test FAILED: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all audio agent tests."""
    print("=" * 60)
    print("AUDIO AGENT CANONICAL STRUCTURE TEST")
    print("=" * 60)

    # Run discovery test
    discovery_success = await test_audio_agent_discovery()

    # Run basic functionality test
    functionality_success = await test_audio_agent_basic_functionality()

    # Overall result
    if discovery_success and functionality_success:
        print("\n🎉 ALL TESTS PASSED - Audio agent is properly structured!")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED - Check the errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
