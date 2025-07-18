#!/usr/bin/env python3
"""
Live test script for the multi-agent video system.
This script tests the Image Generation and Audio agents with real API calls.
"""

import os
import sys
import base64
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from sub_agents.image_generation.tools.dalle_generation import generate_imagen_image
from sub_agents.audio.tools.gemini_tts import generate_speech_with_gemini
from sub_agents.audio.tools.audio_processing import calculate_audio_timing

def test_imagen_generation():
    """Test Google Imagen 4 image generation."""
    print("🎨 Testing Google Imagen 4 Image Generation...")
    print("-" * 50)
    
    # Test prompt
    prompt = "A beautiful mountain landscape with snow-capped peaks, clear blue sky, and green valleys below, professional photography style"
    
    try:
        result = generate_imagen_image(
            prompt=prompt,
            aspect_ratio="16:9",
            number_of_images=1,
            person_generation="ALLOW_ADULT",
            output_mime_type="image/jpeg"
        )
        
        print(f"✅ Generation Status: {result.get('source', 'unknown')}")
        print(f"📊 Total Images: {result.get('total_images', 0)}")
        print(f"🎯 Prompt: {result.get('prompt', 'N/A')[:100]}...")
        
        if result.get('total_images', 0) > 0:
            image = result['images'][0]
            if image.get('status') == 'success':
                print(f"✅ Image Status: {image['status']}")
                print(f"📐 Dimensions: {image.get('width', 'N/A')}x{image.get('height', 'N/A')}")
                print(f"🎨 Model: {image.get('model', 'N/A')}")
                print(f"📄 Format: {image.get('mime_type', 'N/A')}")
                print(f"💾 Base64 Length: {len(image.get('base64', ''))} characters")
                
                # Save image to file
                if image.get('base64'):
                    image_data = base64.b64decode(image['base64'])
                    output_path = "test_imagen_output.jpg"
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                    print(f"💾 Image saved to: {output_path}")
                    
            else:
                print(f"❌ Image Error: {image.get('error', 'Unknown error')}")
        else:
            print(f"❌ Generation Error: {result.get('images', [{}])[0].get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()

def test_gemini_tts():
    """Test Google Gemini TTS speech generation."""
    print("🎤 Testing Google Gemini TTS Speech Generation...")
    print("-" * 50)
    
    # Test text
    text = "Hello! This is a test of Google's Gemini text-to-speech system. The voice should sound natural and clear."
    
    try:
        result = generate_speech_with_gemini(
            text=text,
            voice_name="Zephyr",
            temperature=1.0,
            output_format="wav"
        )
        
        print(f"✅ Generation Status: {result.get('source', 'unknown')}")
        print(f"🎵 Total Audio Files: {result.get('total_files', 0)}")
        print(f"📝 Text: {result.get('text', 'N/A')[:100]}...")
        
        if result.get('total_files', 0) > 0:
            audio = result['audio_files'][0]
            if audio.get('status') == 'success':
                print(f"✅ Audio Status: {audio['status']}")
                print(f"🎙️ Voice: {audio.get('voice_name', 'N/A')}")
                print(f"🎨 Model: {audio.get('model', 'N/A')}")
                print(f"📄 Format: {audio.get('mime_type', 'N/A')}")
                print(f"⏱️ Estimated Duration: {audio.get('duration_estimate', 'N/A')} seconds")
                print(f"💾 Base64 Length: {len(audio.get('base64', ''))} characters")
                
                # Save audio to file
                if audio.get('audio_data'):
                    output_path = f"test_tts_output{audio.get('file_extension', '.wav')}"
                    with open(output_path, 'wb') as f:
                        f.write(audio['audio_data'])
                    print(f"💾 Audio saved to: {output_path}")
                    
            else:
                print(f"❌ Audio Error: {audio.get('error', 'Unknown error')}")
        else:
            print(f"❌ Generation Error: {result.get('audio_files', [{}])[0].get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()

def test_audio_timing():
    """Test audio timing calculation."""
    print("⏰ Testing Audio Timing Calculation...")
    print("-" * 50)
    
    # Sample script scenes
    script_scenes = [
        {
            "scene_number": 1,
            "description": "Opening scene with mountain landscape",
            "dialogue": "Welcome to our journey through the beautiful mountains.",
            "duration": 5.0
        },
        {
            "scene_number": 2,
            "description": "Detailed view of snow-capped peaks",
            "dialogue": "These magnificent peaks have stood for millions of years, shaped by ice and wind.",
            "duration": 8.0
        },
        {
            "scene_number": 3,
            "description": "Valley view with green meadows",
            "dialogue": "Below, the valleys burst with life and color during the spring season.",
            "duration": 6.0
        }
    ]
    
    try:
        result = calculate_audio_timing(script_scenes, 60.0)
        
        print(f"✅ Timing Status: {result.get('status', 'unknown')}")
        print(f"🎬 Scene Count: {result.get('scene_count', 0)}")
        print(f"🎵 Audio Segments Needed: {result.get('audio_segments_needed', 0)}")
        print(f"⏱️ Total Duration: {result.get('total_duration', 0):.2f} seconds")
        
        if result.get('status') == 'success':
            print("\n📋 Timing Segments:")
            for segment in result.get('timing_segments', []):
                print(f"  Scene {segment.get('scene_number', 'N/A')}: "
                      f"{segment.get('start_time', 0):.2f}s - {segment.get('end_time', 0):.2f}s "
                      f"({segment.get('duration', 0):.2f}s)")
                print(f"    Dialogue: {segment.get('dialogue', 'N/A')[:60]}...")
                print()
        else:
            print(f"❌ Timing Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()

def check_environment():
    """Check if required environment variables are set."""
    print("🔧 Checking Environment Configuration...")
    print("-" * 50)
    
    required_vars = {
        'GEMINI_API_KEY': 'Google Gemini API (for both Imagen 4 and TTS)',
        'PEXELS_API_KEY': 'Pexels stock photos',
        'UNSPLASH_ACCESS_KEY': 'Unsplash stock photos',
        'PIXABAY_API_KEY': 'Pixabay stock photos'
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set ({description})")
        else:
            print(f"❌ {var}: Not set ({description})")
            all_set = False
    
    print()
    return all_set

def main():
    """Main test function."""
    print("🚀 Multi-Agent Video System - Live Agent Testing")
    print("=" * 60)
    print()
    
    # Check environment
    if not check_environment():
        print("⚠️  Some environment variables are missing. Tests may fail.")
        print()
    
    # Test each component
    test_imagen_generation()
    test_gemini_tts()
    test_audio_timing()
    
    print("🎉 Live testing complete!")
    print("Check the generated files:")
    print("  - test_imagen_output.jpg (if image generation succeeded)")
    print("  - test_tts_output.wav (if TTS generation succeeded)")

if __name__ == "__main__":
    main()