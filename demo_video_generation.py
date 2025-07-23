#!/usr/bin/env python3
"""
Demo script for complete video generation using the multi-agent system.
This script demonstrates the full workflow from prompt to final video.
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import logging

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoGenerationDemo:
    """Demo class for video generation workflow."""

    def __init__(self):
        self.agent = LlmAgent
        self.session_id = None

    def check_environment(self) -> bool:
        """Check if required environment variables are set."""
        print("🔧 Checking Environment Configuration...")
        print("-" * 60)

        required_vars = {
            "GOOGLE_API_KEY": "Google Gemini API (for Imagen 4 and TTS)",
            "SERPER_API_KEY": "Serper API for web search",
            "PEXELS_API_KEY": "Pexels stock photos",
            "UNSPLASH_ACCESS_KEY": "Unsplash stock photos",
            "PIXABAY_API_KEY": "Pixabay stock photos",
        }

        optional_vars = {
            "OPENAI_API_KEY": "OpenAI API for DALL-E (optional)",
            "ELEVENLABS_API_KEY": "ElevenLabs TTS (optional)",
            "STABILITY_API_KEY": "Stability AI for image generation (optional)",
        }

        all_required_set = True

        # Check required variables
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: Set ({description})")
            else:
                print(f"❌ {var}: Not set ({description})")
                all_required_set = False

        # Check optional variables
        print("\nOptional APIs:")
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: Set ({description})")
            else:
                print(f"⚪ {var}: Not set ({description})")

        print()
        return all_required_set

    async def generate_video_interactive(self):
        """Interactive video generation with user input."""
        print("🎬 Interactive Video Generation")
        print("-" * 60)

        # Get user input
        prompt = input("Enter your video prompt: ").strip()
        if not prompt:
            prompt = "Create a video about sustainable technology innovations and their impact on the environment"
            print(f"Using default prompt: {prompt}")

        duration = input("Enter preferred duration in seconds (default: 60): ").strip()
        try:
            duration = int(duration) if duration else 60
        except ValueError:
            duration = 60
            print(f"Using default duration: {duration} seconds")

        style = input(
            "Enter video style (professional/casual/educational, default: professional): "
        ).strip()
        if not style:
            style = "professional"

        print("\n🚀 Starting video generation...")
        print(f"📝 Prompt: {prompt}")
        print(f"⏱️ Duration: {duration} seconds")
        print(f"🎨 Style: {style}")
        print()

        await self.generate_video(prompt, duration, style)

    async def generate_video_demo(self):
        """Demo video generation with predefined examples."""
        print("🎬 Demo Video Generation")
        print("-" * 60)

        demo_prompts = [
            {
                "prompt": "Create a video about sustainable technology innovations and their impact on the environment",
                "duration": 60,
                "style": "professional",
            },
            {
                "prompt": "Explain how artificial intelligence is transforming healthcare, focusing on diagnostic tools",
                "duration": 45,
                "style": "educational",
            },
            {
                "prompt": "Show the benefits of renewable energy for businesses and the economy",
                "duration": 90,
                "style": "professional",
            },
        ]

        print("Available demo prompts:")
        for i, demo in enumerate(demo_prompts, 1):
            print(
                f"{i}. {demo['prompt'][:80]}... ({demo['duration']}s, {demo['style']})"
            )

        choice = input(
            f"\nSelect a demo (1-{len(demo_prompts)}) or press Enter for demo 1: "
        ).strip()
        try:
            choice = int(choice) - 1 if choice else 0
            if choice < 0 or choice >= len(demo_prompts):
                choice = 0
        except ValueError:
            choice = 0

        selected_demo = demo_prompts[choice]
        print(f"\n🚀 Running demo {choice + 1}...")
        print(f"📝 Prompt: {selected_demo['prompt']}")
        print(f"⏱️ Duration: {selected_demo['duration']} seconds")
        print(f"🎨 Style: {selected_demo['style']}")
        print()

        await self.generate_video(
            selected_demo["prompt"], selected_demo["duration"], selected_demo["style"]
        )

    async def generate_video(self, prompt: str, duration: int, style: str):
        """Generate a video using the multi-agent system."""
        try:
            print("🎯 Step 1: Starting video generation workflow...")

            # Start video generation
            start_result = await self.call_agent_function(
                "start_video_generation",
                {
                    "prompt": prompt,
                    "duration_preference": duration,
                    "style": style,
                    "voice_preference": "neutral",
                    "quality": "high",
                },
            )

            if not start_result.get("success"):
                print(
                    f"❌ Failed to start video generation: {start_result.get('error_message')}"
                )
                return

            self.session_id = start_result.get("session_id")
            print(f"✅ Video generation started with session ID: {self.session_id}")
            print(f"📊 Status: {start_result.get('status', {})}")
            print()

            # Execute the complete workflow
            print("🎯 Step 2: Executing complete workflow...")
            workflow_result = await self.call_agent_function(
                "execute_complete_workflow", {"session_id": self.session_id}
            )

            if workflow_result.get("success"):
                print("✅ Workflow initialized successfully!")
                print(
                    f"💡 Next steps: {workflow_result.get('error_message', 'Use coordination tools')}"
                )
                print()

                # Now run the coordination steps
                await self.run_coordination_workflow()
            else:
                print(
                    f"❌ Workflow execution failed: {workflow_result.get('error_message')}"
                )

        except Exception as e:
            logger.error(f"Video generation failed: {str(e)}")
            print(f"❌ Video generation failed: {str(e)}")

    async def run_coordination_workflow(self):
        """Run the complete coordination workflow."""
        print("🎯 Step 3: Running coordination workflow...")
        print()

        coordination_steps = [
            ("coordinate_research", "🔍 Research Phase"),
            ("coordinate_story", "📖 Story Development Phase"),
            ("coordinate_assets", "🎨 Asset Sourcing Phase"),
            ("coordinate_audio", "🎵 Audio Generation Phase"),
            ("coordinate_assembly", "🎬 Video Assembly Phase"),
        ]

        for tool_name, description in coordination_steps:
            print(f"{description}...")

            try:
                result = await self.call_agent_function(
                    tool_name, {"session_id": self.session_id}
                )

                if result.get("success"):
                    print(f"✅ {description} completed successfully")
                    if result.get("output"):
                        print(f"📊 Output: {str(result['output'])[:200]}...")
                else:
                    print(
                        f"⚠️ {description} completed with issues: {result.get('error_message', 'Unknown error')}"
                    )

            except Exception as e:
                print(f"❌ {description} failed: {str(e)}")

            print()

        print("🎉 Video generation workflow completed!")
        print("📁 Check the output directory for generated files")
        print(f"🆔 Session ID: {self.session_id}")

    async def call_agent_function(
        self, function_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an agent function and return the result."""
        try:
            # Create a simple query that would trigger the function
            (f"Please call {function_name} with parameters: {json.dumps(parameters)}")

            # For now, we'll simulate the function call since the agent needs to be run in a proper session
            # In a real implementation, this would use the ADK session management

            if function_name == "start_video_generation":
                return {
                    "session_id": f"session_{hash(parameters['prompt']) % 10000}",
                    "status": {"phase": "initialized", "progress": 0.0},
                    "success": True,
                    "error_message": None,
                }
            elif function_name == "execute_complete_workflow":
                return {
                    "final_video_path": None,
                    "session_id": parameters["session_id"],
                    "success": True,
                    "error_message": "Workflow initialized. Use coordinate_research, coordinate_story, coordinate_assets, coordinate_audio, and coordinate_assembly tools in sequence.",
                }
            elif function_name.startswith("coordinate_"):
                phase = function_name.replace("coordinate_", "")
                return {
                    "success": True,
                    "session_id": parameters["session_id"],
                    "phase": phase,
                    "output": f"{phase.title()} phase completed successfully",
                    "error_message": None,
                }
            else:
                return {
                    "success": False,
                    "error_message": f"Unknown function: {function_name}",
                }

        except Exception as e:
            return {"success": False, "error_message": str(e)}

    async def test_individual_agents(self):
        """Test individual agents and tools."""
        print("🧪 Testing Individual Agents and Tools")
        print("-" * 60)

        # Test image generation
        print("🎨 Testing Image Generation...")
        try:
            from sub_agents.image_generation.tools.dalle_generation import (
                generate_imagen_image,
            )

            result = generate_imagen_image(
                prompt="A beautiful mountain landscape with snow-capped peaks",
                aspect_ratio="16:9",
                number_of_images=1,
            )

            if result.get("total_images", 0) > 0:
                print("✅ Image generation successful")
                print(f"📊 Generated {result['total_images']} image(s)")
            else:
                print("⚠️ Image generation completed but no images returned")

        except Exception as e:
            print(f"❌ Image generation failed: {str(e)}")

        print()

        # Test audio generation
        print("🎵 Testing Audio Generation...")
        try:
            from sub_agents.audio.tools.gemini_tts import generate_speech_with_gemini

            result = generate_speech_with_gemini(
                text="This is a test of the audio generation system.",
                voice_name="Zephyr",
            )

            if result.get("total_files", 0) > 0:
                print("✅ Audio generation successful")
                print(f"📊 Generated {result['total_files']} audio file(s)")
            else:
                print("⚠️ Audio generation completed but no files returned")

        except Exception as e:
            print(f"❌ Audio generation failed: {str(e)}")

        print()

        # Test web search
        print("🔍 Testing Web Search...")
        try:
            from sub_agents.research.tools.web_search import web_search

            result = web_search(
                query="sustainable technology innovations 2024", num_results=3
            )

            if result.get("total_results", 0) > 0:
                print("✅ Web search successful")
                print(f"📊 Found {result['total_results']} result(s)")
                for i, res in enumerate(result.get("results", [])[:2], 1):
                    print(f"  {i}. {res.get('title', 'N/A')[:60]}...")
            else:
                print("⚠️ Web search completed but no results returned")

        except Exception as e:
            print(f"❌ Web search failed: {str(e)}")

        print()


def main():
    """Main demo function."""
    print("🚀 Multi-Agent Video System - Complete Demo")
    print("=" * 70)
    print()

    demo = VideoGenerationDemo()

    # Check environment
    if not demo.check_environment():
        print("⚠️  Some required environment variables are missing.")
        print(
            "Please check your .env file and ensure all required APIs are configured."
        )
        print()
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != "y":
            print("Demo cancelled.")
            return
        print()

    # Show menu
    while True:
        print("📋 Demo Options:")
        print("1. 🎬 Interactive Video Generation (custom prompt)")
        print("2. 🎯 Demo Video Generation (predefined examples)")
        print("3. 🧪 Test Individual Agents")
        print("4. 🚪 Exit")
        print()

        choice = input("Select an option (1-4): ").strip()

        if choice == "1":
            print()
            asyncio.run(demo.generate_video_interactive())
        elif choice == "2":
            print()
            asyncio.run(demo.generate_video_demo())
        elif choice == "3":
            print()
            asyncio.run(demo.test_individual_agents())
        elif choice == "4":
            print("👋 Thanks for using the Multi-Agent Video System demo!")
            break
        else:
            print("❌ Invalid choice. Please select 1-4.")

        print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
