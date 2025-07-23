#!/usr/bin/env python3
"""
Full Video Generation Test

This script demonstrates the complete multi-agent video generation workflow
using the canonical structure.
"""

import asyncio
import sys
import random
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import canonical structure components
from video_system.agents.video_orchestrator.agent import (
    root_agent as video_orchestrator,
)
from video_system.tools.orchestration_tools import (
    start_video_generation,
    execute_complete_workflow,
    get_session_status,
)
from video_system.utils.models import VideoGenerationRequest, VideoStyle, VideoQuality

# Random video topics for demonstration
RANDOM_TOPICS = [
    "The future of renewable energy and sustainable technology",
    "How artificial intelligence is transforming healthcare",
    "The science behind climate change and global warming",
    "Space exploration and the search for extraterrestrial life",
    "The evolution of transportation: from horses to autonomous vehicles",
    "Ocean conservation and marine biodiversity protection",
    "The impact of social media on modern communication",
    "Quantum computing and its potential applications",
    "The history and cultural significance of coffee around the world",
    "Urban farming and sustainable food production in cities",
]

RANDOM_STYLES = [
    VideoStyle.EDUCATIONAL,
    VideoStyle.DOCUMENTARY,
    VideoStyle.PROFESSIONAL,
    VideoStyle.ENTERTAINMENT,
]

RANDOM_VOICES = ["neutral", "professional", "friendly", "authoritative"]

RANDOM_QUALITIES = [VideoQuality.HIGH, VideoQuality.MEDIUM, VideoQuality.ULTRA]


def generate_random_video_request():
    """Generate a random video generation request."""
    topic = random.choice(RANDOM_TOPICS)
    style = random.choice(RANDOM_STYLES)
    voice = random.choice(RANDOM_VOICES)
    quality = random.choice(RANDOM_QUALITIES)
    duration = random.choice([30, 60, 90, 120])

    return VideoGenerationRequest(
        prompt=f"Create an engaging video about: {topic}",
        duration_preference=duration,
        style=style,
        voice_preference=voice,
        quality=quality,
    )


async def test_full_video_generation():
    """Test the complete video generation workflow."""
    print("🎬 Multi-Agent Video Generation System")
    print("=" * 60)

    # Generate random video request
    request = generate_random_video_request()

    print("📋 Video Generation Request:")
    print(f"  📝 Prompt: {request.prompt}")
    print(f"  ⏱️ Duration: {request.duration_preference} seconds")
    print(f"  🎨 Style: {request.style.value}")
    print(f"  🎤 Voice: {request.voice_preference}")
    print(f"  📺 Quality: {request.quality.value}")
    print()

    try:
        # Step 1: Start video generation
        print("🚀 Step 1: Starting video generation...")
        session_result = start_video_generation(
            prompt=request.prompt,
            duration_preference=request.duration_preference,
            style=request.style.value,
            voice_preference=request.voice_preference,
            quality=request.quality.value,
        )

        if not session_result.get("success", False):
            print(
                f"❌ Failed to start video generation: {session_result.get('error_message', 'Unknown error')}"
            )
            return False

        session_id = session_result["session_id"]
        print(f"✅ Session created: {session_id}")
        print()

        # Step 2: Execute complete workflow
        print("⚙️ Step 2: Executing complete workflow...")
        workflow_result = execute_complete_workflow(session_id=session_id)

        if not workflow_result.get("success", False):
            print(
                f"❌ Workflow execution failed: {workflow_result.get('error_message', 'Unknown error')}"
            )
            return False

        print("✅ Workflow execution started")
        print()

        # Step 3: Monitor progress
        print("📊 Step 3: Monitoring progress...")
        max_checks = 10
        check_count = 0

        while check_count < max_checks:
            status_result = get_session_status(session_id=session_id)

            if status_result.get("success", False):
                status = status_result["status"]
                print(f"  📈 Status: {status.get('status', 'unknown')}")
                print(f"  🎯 Stage: {status.get('current_stage', 'unknown')}")
                print(f"  📊 Progress: {status.get('progress', 0):.1%}")

                if status.get("status") == "completed":
                    print("🎉 Video generation completed!")
                    break
                elif status.get("status") == "failed":
                    print(
                        f"❌ Video generation failed: {status.get('error_message', 'Unknown error')}"
                    )
                    return False
            else:
                print(
                    f"⚠️ Could not get status: {status_result.get('error_message', 'Unknown error')}"
                )

            check_count += 1
            if check_count < max_checks:
                print("  ⏳ Waiting for next update...")
                await asyncio.sleep(2)

        if check_count >= max_checks:
            print("⏰ Monitoring timeout reached")

        print()

        # Step 4: Final status check
        print("🏁 Step 4: Final status check...")
        final_status = get_session_status(session_id=session_id)

        if final_status.get("success", False):
            status = final_status["status"]
            print(f"  📋 Final Status: {status.get('status', 'unknown')}")
            print(f"  📊 Final Progress: {status.get('progress', 0):.1%}")

            if status.get("status") == "completed":
                print("✅ Video generation workflow completed successfully!")
                return True
            else:
                print(
                    f"⚠️ Video generation ended with status: {status.get('status', 'unknown')}"
                )
                return False
        else:
            print(
                f"❌ Could not get final status: {final_status.get('error_message', 'Unknown error')}"
            )
            return False

    except Exception as e:
        print(f"💥 Unexpected error during video generation: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_agent_tools():
    """Test individual agent tools."""
    print("🔧 Testing Individual Agent Tools")
    print("=" * 60)

    # Test video orchestrator tools
    print("🎭 Video Orchestrator Tools:")
    tools = video_orchestrator.tools
    print(f"  📦 Total tools: {len(tools)}")

    for i, tool in enumerate(tools, 1):
        tool_name = getattr(tool, "__name__", str(tool))
        print(f"  {i}. {tool_name}")

    print()

    # Test agent configuration
    print("⚙️ Agent Configuration:")
    print(f"  🏷️ Name: {video_orchestrator.name}")
    print(f"  🤖 Model: {video_orchestrator.model}")
    print(f"  📝 Instruction length: {len(video_orchestrator.instruction)} characters")
    print()

    return True


async def main():
    """Main test execution."""
    print("🎯 Full Multi-Agent Video Generation Test")
    print("=" * 80)
    print()

    # Test 1: Agent tools
    tools_success = await test_agent_tools()

    # Test 2: Full video generation
    generation_success = await test_full_video_generation()

    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"🔧 Agent Tools Test: {'✅ PASSED' if tools_success else '❌ FAILED'}")
    print(
        f"🎬 Video Generation Test: {'✅ PASSED' if generation_success else '❌ FAILED'}"
    )
    print()

    if tools_success and generation_success:
        print("🎉 ALL TESTS PASSED! The multi-agent video system is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
