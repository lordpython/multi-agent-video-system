#!/usr/bin/env python3
"""Test real video generation tools directly."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.orchestration_tools_simple_real import (
    coordinate_research_real,
    coordinate_story_real,
    coordinate_assets_real,
    coordinate_audio_real,
    coordinate_assembly_real,
)


async def test_real_video_generation():
    """Test the real video generation tools directly."""
    print("🧪 Testing Real Video Generation Tools")
    print("=" * 50)

    topic = "مسلسل امي السعودي"
    duration = 120

    try:
        # Step 1: Research
        print(f"1. 🔍 Researching topic: {topic}")
        research_result = await coordinate_research_real(topic)
        print(f"   ✅ Research completed: {research_result['message']}")
        research_data = research_result["research_data"]

        # Step 2: Story
        print(f"2. 📝 Creating script (duration: {duration}s)")
        story_result = await coordinate_story_real(research_data, duration)
        print(f"   ✅ Script created: {story_result['message']}")
        script = story_result["script"]
        print(f"   📊 Script has {len(script['scenes'])} scenes")

        # Step 3: Assets
        print("3. 🎨 Generating visual assets")
        assets_result = await coordinate_assets_real(script)
        print(f"   ✅ Assets generated: {assets_result['message']}")
        assets = assets_result["assets"]
        print(f"   📊 Generated {len(assets['images'])} images")

        # Step 4: Audio
        print("4. 🎵 Generating audio")
        audio_result = await coordinate_audio_real(script)
        print(f"   ✅ Audio generated: {audio_result['message']}")
        audio_assets = audio_result["audio_assets"]
        print(f"   📊 Audio duration: {audio_assets['narration']['duration']}s")

        # Step 5: Assembly
        print("5. 🎬 Assembling final video")
        assembly_result = await coordinate_assembly_real(script, assets, audio_assets)
        print(f"   ✅ Video assembled: {assembly_result['message']}")
        final_video = assembly_result["final_video"]

        print("\n" + "=" * 50)
        print("🎉 VIDEO GENERATION COMPLETED!")
        print(f"📁 Video file: {final_video['video_file']}")

        # Check if file exists
        video_path = Path(final_video["video_file"])
        if video_path.exists():
            file_size = video_path.stat().st_size
            print(f"📊 File size: {file_size / 1024 / 1024:.1f} MB")
            print(f"🎯 Video format: {final_video['metadata']['format']}")
            print(f"⏱️  Duration: {final_video['metadata']['duration']}s")
        else:
            print("⚠️  Video file not found on disk")

        print("=" * 50)

        return final_video["video_file"]

    except Exception as e:
        print(f"💥 Error during video generation: {e}")
        import traceback

        traceback.print_exc()
        return None


async def main():
    """Main test function."""
    video_path = await test_real_video_generation()

    if video_path:
        print(f"\n✅ SUCCESS: Video generated at {video_path}")

        # List all generated files
        print("\n📁 Generated files:")

        output_dir = Path("output")
        if output_dir.exists():
            for file_path in output_dir.iterdir():
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"  - {file_path.name} ({size} bytes)")

        assets_dir = Path("generated_assets")
        if assets_dir.exists():
            for file_path in assets_dir.iterdir():
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"  - {file_path.name} ({size} bytes)")
    else:
        print("\n❌ FAILED: Video generation failed")


if __name__ == "__main__":
    asyncio.run(main())
