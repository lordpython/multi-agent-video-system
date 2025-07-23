#!/usr/bin/env python3
"""Demo script for real video generation using actual services."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part

from video_system.agent_real import root_agent_real


async def generate_real_video(prompt: str, user_id: str = "demo_user"):
    """Generate a real video using the actual video generation services."""
    print(f"🎬 Starting REAL video generation for: '{prompt}'")
    print("=" * 60)

    # Create session service and session
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="real-video-system",
        user_id=user_id,
        state={
            "prompt": prompt,
            "generation_type": "real",
            "start_time": asyncio.get_event_loop().time(),
        },
    )

    print(f"📋 Session created: {session.id}")

    # Create runner with real agent
    runner = Runner(
        agent=root_agent_real,
        app_name="real-video-system",
        session_service=session_service,
    )

    # Create user message with explicit instruction
    user_message = Content(parts=[Part(text=f"Generate a video about: {prompt}")])

    print("🚀 Starting video generation workflow...")
    print("This may take several minutes as we:")
    print("  1. Research your topic")
    print("  2. Generate AI script")
    print("  3. Create real images")
    print("  4. Generate audio narration")
    print("  5. Assemble final video")
    print()

    try:
        # Execute agent
        final_response = None
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=user_message
        ):
            # Print progress updates
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(f"🤖 Agent: {part.text}")

            if event.is_final_response():
                final_response = event
                break

        print("\n" + "=" * 60)
        if final_response:
            print("✅ Video generation completed!")

            # Check session state for video file path
            updated_session = await session_service.get_session(
                app_name="real-video-system", user_id=user_id, session_id=session.id
            )

            # Look for video file in session state
            state = updated_session.state
            video_path = None

            # Check various possible locations for the video path
            if "final_video" in state:
                video_data = state["final_video"]
                if isinstance(video_data, dict):
                    video_path = video_data.get("video_file")

            if video_path and Path(video_path).exists():
                print(f"🎥 Your video is ready: {video_path}")
                print(
                    f"📁 File size: {Path(video_path).stat().st_size / 1024 / 1024:.1f} MB"
                )
            else:
                print("⚠️  Video file path not found in session state")
                print("Check the 'output' directory for generated files")

                # List files in output directory
                output_dir = Path("output")
                if output_dir.exists():
                    video_files = list(output_dir.glob("*.mp4"))
                    if video_files:
                        latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
                        print(f"🎥 Latest video found: {latest_video}")
        else:
            print("❌ No final response received")

    except Exception as e:
        print(f"💥 Error during video generation: {e}")
        import traceback

        traceback.print_exc()

    print("=" * 60)


async def main():
    """Main demo function."""
    print("🎬 Real Video Generation Demo")
    print("=" * 60)

    # Example prompts
    prompts = [
        "مسلسل امي السعودي",  # Your original request
        "artificial intelligence and machine learning",
        "sustainable energy solutions",
        "space exploration technologies",
    ]

    print("Available demo prompts:")
    for i, prompt in enumerate(prompts, 1):
        print(f"  {i}. {prompt}")

    print("\nChoose a prompt (1-4) or enter your own:")
    choice = input("> ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(prompts):
        selected_prompt = prompts[int(choice) - 1]
    elif choice:
        selected_prompt = choice
    else:
        selected_prompt = prompts[0]  # Default to first prompt

    print(f"\n🎯 Selected prompt: '{selected_prompt}'")

    # Generate video
    await generate_real_video(selected_prompt)


if __name__ == "__main__":
    # Check dependencies
    missing_deps = []

    try:
        import moviepy
    except ImportError:
        missing_deps.append("moviepy")

    try:
        import PIL
    except ImportError:
        missing_deps.append("pillow")

    try:
        import pyttsx3
    except ImportError:
        missing_deps.append("pyttsx3")

    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")

    if missing_deps:
        print("⚠️  Missing dependencies for real video generation:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall with: pip install " + " ".join(missing_deps))
        print("Or run: poetry install")
        sys.exit(1)

    # Run demo
    asyncio.run(main())
