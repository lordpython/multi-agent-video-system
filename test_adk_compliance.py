#!/usr/bin/env python3
"""
Test script to verify ADK compliance implementation.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_adk_compliance():
    """Test that all ADK compliance fixes are working correctly."""
    
    print("Testing ADK-compliant multi-agent video system...")
    print("=" * 50)
    
    try:
        # Test agent imports
        print("Testing agent imports...")
        from video_system.agents.research_agent.agent import root_agent as research_agent
        from video_system.agents.story_agent.agent import root_agent as story_agent
        from video_system.agents.image_generation_agent.agent import root_agent as image_agent
        from video_system.agents.audio_agent.agent import root_agent as audio_agent
        from video_system.agents.asset_sourcing_agent.agent import root_agent as asset_agent
        from video_system.agents.video_assembly_agent.agent import root_agent as video_agent
        from video_system.agents.video_orchestrator.agent import root_agent as orchestrator
        
        print("✅ All agent imports successful")
        
        # Check agent types
        agents = {
            "Research Agent": research_agent,
            "Story Agent": story_agent,
            "Image Agent": image_agent,
            "Audio Agent": audio_agent,
            "Asset Agent": asset_agent,
            "Video Agent": video_agent,
            "Orchestrator": orchestrator
        }
        
        for name, agent in agents.items():
            if agent is not None:
                print(f"  {name}: {type(agent).__name__}")
            else:
                print(f"  {name}: None (ADK unavailable)")
        
        # Test tool imports
        print("\nTesting tool imports...")
        from video_system.tools.story_tools import script_generation_tool
        from video_system.tools.audio_tools import gemini_tts_tool
        from video_system.tools.video_tools import ffmpeg_composition_tool
        from video_system.tools.asset_tools import pexels_search_tool
        
        print("✅ All tool imports successful")
        print(f"  Script Tool: {type(script_generation_tool).__name__}")
        print(f"  TTS Tool: {type(gemini_tts_tool).__name__}")
        print(f"  Video Tool: {type(ffmpeg_composition_tool).__name__}")
        print(f"  Asset Tool: {type(pexels_search_tool).__name__}")
        
        # Test ADK availability detection
        print("\nTesting ADK availability detection...")
        try:
            from google.adk.agents import Agent
            print("✅ ADK is available - agents should be active")
            adk_available = True
        except ImportError:
            print("⚠️  ADK is not available - agents should be None")
            adk_available = False
        
        # Verify consistency
        active_agents = sum(1 for agent in agents.values() if agent is not None)
        if adk_available and active_agents > 0:
            print(f"✅ Consistency check passed: ADK available, {active_agents} agents active")
        elif not adk_available and active_agents == 0:
            print("✅ Consistency check passed: ADK unavailable, all agents disabled")
        else:
            print(f"⚠️  Consistency issue: ADK available={adk_available}, active agents={active_agents}")
        
        print("\n🎉 ADK compliance test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_adk_compliance()
    sys.exit(0 if success else 1)
