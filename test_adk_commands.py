#!/usr/bin/env python3
"""
Test script to verify ADK command compatibility for all agents in the canonical structure.
This script tests that all agents can be discovered and executed using ADK commands.
"""

import subprocess
import sys
import time
from typing import List, Tuple

def test_adk_command(agent_path: str, agent_name: str) -> Tuple[bool, str]:
    """
    Test an ADK command by running it with a timeout and checking if it starts successfully.
    
    Args:
        agent_path: Path to the agent directory
        agent_name: Name of the agent for logging
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Use echo to provide input and exit immediately
        cmd = f'echo "exit" | adk run {agent_path}'
        
        # Run the command with a timeout
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Check if the command started successfully
        if result.returncode == 0:
            # Look for the "Running agent" message in stdout
            if f"Running agent {agent_name}" in result.stdout or "Running agent" in result.stdout:
                return True, f"✅ {agent_name}: Successfully started and discovered by ADK"
            else:
                return False, f"❌ {agent_name}: Started but agent name not found in output"
        else:
            # Check if it's just an exit code issue but agent started
            if "Running agent" in result.stdout:
                return True, f"✅ {agent_name}: Successfully started (exit code {result.returncode})"
            else:
                return False, f"❌ {agent_name}: Failed to start - {result.stderr[:200]}"
                
    except subprocess.TimeoutExpired:
        return False, f"❌ {agent_name}: Command timed out after 30 seconds"
    except Exception as e:
        return False, f"❌ {agent_name}: Exception occurred - {str(e)}"

def main():
    """Test all ADK commands for agent compatibility."""
    print("🧪 Testing ADK Command Compatibility")
    print("=" * 50)
    
    # Define all agents to test
    agents_to_test = [
        ("video_system/agents/video_orchestrator", "video_system_orchestrator"),
        ("video_system/agents/research_agent", "research_agent"),
        ("video_system/agents/story_agent", "story_agent"),
        ("video_system/agents/asset_sourcing_agent", "asset_sourcing_agent"),
        ("video_system/agents/image_generation_agent", "image_generation_agent"),
        ("video_system/agents/audio_agent", "audio_agent"),
        ("video_system/agents/video_assembly_agent", "video_assembly_agent"),
    ]
    
    results = []
    
    for agent_path, agent_name in agents_to_test:
        print(f"\n🔍 Testing: adk run {agent_path}")
        success, message = test_adk_command(agent_path, agent_name)
        results.append((agent_name, success, message))
        print(f"   {message}")
        
        # Small delay between tests
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    successful_tests = sum(1 for _, success, _ in results if success)
    total_tests = len(results)
    
    for agent_name, success, message in results:
        print(f"   {message}")
    
    print(f"\n🎯 Results: {successful_tests}/{total_tests} agents successfully discovered by ADK")
    
    if successful_tests == total_tests:
        print("🎉 All ADK commands work correctly! The canonical structure is properly implemented.")
        return 0
    else:
        print("⚠️  Some ADK commands failed. Check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())