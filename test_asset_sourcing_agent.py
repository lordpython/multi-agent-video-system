#!/usr/bin/env python3
"""Test script to verify asset sourcing agent can be imported and discovered."""

import sys
import os

# Add paths for imports - ensure we can find both src and project root
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "src"))
sys.path.insert(0, current_dir)


def test_asset_sourcing_agent():
    """Test that the asset sourcing agent can be imported and discovered."""
    try:
        # Test direct import from canonical location
        from video_system.agents.asset_sourcing_agent.agent import root_agent

        print("✓ Successfully imported root_agent from asset_sourcing_agent")
        print(f"Agent name: {root_agent.name}")
        print(f"Agent model: {root_agent.model}")
        print(f"Agent description: {root_agent.description}")
        print(f"Number of tools: {len(root_agent.tools)}")

        # Test that it's an LlmAgent
        from google.adk.agents import LlmAgent

        if isinstance(root_agent, LlmAgent):
            print("✓ root_agent is correctly defined as LlmAgent")
        else:
            print(f"✗ root_agent is {type(root_agent)}, expected LlmAgent")
            return False

        # Test that tools are available
        if len(root_agent.tools) > 0:
            print("✓ Agent has tools configured")
            for i, tool in enumerate(root_agent.tools):
                print(
                    f"  Tool {i + 1}: {tool.name if hasattr(tool, 'name') else str(tool)}"
                )
        else:
            print("✗ Agent has no tools configured")
            return False

        print("✓ Asset sourcing agent can be discovered and run independently")
        return True

    except Exception as e:
        print(f"✗ Error importing asset sourcing agent: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_asset_sourcing_agent()
    sys.exit(0 if success else 1)
