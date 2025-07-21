#!/usr/bin/env python3
"""
Simple test script to run actual video generation.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
from video_system.agent import initialize_video_system

# Load environment variables
load_dotenv()

async def test_image_generation():
    """Test image generation directly."""
    print("🎨 Testing Image Generation...")
    
    try:
        from sub_agents.image_generation.tools.dalle_generation import generate_imagen_image
        from utils.image_utils import print_image_generation_summary
        
        result = generate_imagen_image(
            prompt="A beautiful mountain landscape with snow-capped peaks at sunset",
            aspect_ratio="16:9",
            number_of_images=1,
        )
        
        # Use utility function to print clean summary
        print_image_generation_summary(result, save_files=True)
            
    except Exception as e:
        print(f"❌ Image generation failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_web_search():
    """Test web search directly."""
    print("\n🔍 Testing Web Search...")
    
    try:
        from sub_agents.research.tools.web_search import web_search
        
        result = web_search(
            query="sustainable technology innovations 2024", 
            num_results=3
        )
        
        print(f"Result: {result}")
        
        if result.get("total_results", 0) > 0:
            print("✅ Web search successful")
            print(f"📊 Found {result['total_results']} result(s)")
            for i, res in enumerate(result.get("results", [])[:2], 1):
                print(f"  {i}. {res.get('title', 'N/A')[:60]}...")
        else:
            print("⚠️ Web search completed but no results returned")
            
    except Exception as e:
        print(f"❌ Web search failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_audio_generation():
    """Test audio generation directly."""
    print("\n🎵 Testing Audio Generation...")
    
    try:
        from sub_agents.audio.tools.gemini_tts import generate_speech_with_gemini
        
        result = generate_speech_with_gemini(
            text="This is a test of the audio generation system for sustainable technology.",
            voice_name="Zephyr",
        )
        
        print(f"Result: {result}")
        
        if result.get("total_files", 0) > 0:
            print("✅ Audio generation successful")
            print(f"📊 Generated {result['total_files']} audio file(s)")
            
            # Check if files were actually created
            if "audio_files" in result:
                for audio in result["audio_files"]:
                    if "file_path" in audio:
                        file_path = audio["file_path"]
                        if os.path.exists(file_path):
                            print(f"📁 Audio saved to: {file_path}")
                        else:
                            print(f"⚠️ Audio file not found: {file_path}")
        else:
            print("⚠️ Audio generation completed but no files returned")
            
    except Exception as e:
        print(f"❌ Audio generation failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("🚀 Testing Real Video Generation Components")
    print("=" * 60)
    
    # Initialize the system
    print("🔧 Initializing video system...")
    initialize_video_system()
    print("✅ System initialized")
    
    # Test individual components
    await test_image_generation()
    await test_web_search()
    await test_audio_generation()
    
    print("\n" + "=" * 60)
    print("🎉 Testing completed!")

if __name__ == "__main__":
    asyncio.run(main())