#!/usr/bin/env python3
"""
Test script for the image generation agent that actually saves generated images to files.
"""

import os
import sys
import base64
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
# Add the project root to Python path for shared_libraries
sys.path.insert(0, os.path.dirname(__file__))

from src.video_system.tools.image_tools import generate_imagen_image, generate_stable_diffusion_image

def save_base64_image(base64_data: str, filename: str) -> bool:
    """Save a base64 encoded image to a file."""
    try:
        # Decode base64 data
        image_data = base64.b64decode(base64_data)
        
        # Save to file
        with open(filename, 'wb') as f:
            f.write(image_data)
        
        print(f"✅ Image saved to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to save image: {e}")
        return False

def test_imagen_generation():
    """Test Imagen 4 image generation and save results."""
    print("🎨 Testing Imagen 4 Image Generation...")
    
    # Test prompt
    prompt = "A cool cat wearing sunglasses and a leather jacket, driving a vintage motorcycle, photorealistic, high quality"
    
    print(f"📝 Prompt: {prompt}")
    
    # Generate image
    result = generate_imagen_image(
        prompt=prompt,
        aspect_ratio="1:1",
        number_of_images=1
    )
    
    if result.get("success"):
        print(f"✅ Successfully generated {result['total_images']} image(s)")
        
        # Save each generated image
        for i, image_data in enumerate(result["images"]):
            if image_data["status"] == "success":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_image_imagen4_{timestamp}_{i+1}.jpg"
                
                print(f"💾 Saving image {i+1}...")
                print(f"   Size: {image_data['width']}x{image_data['height']}")
                print(f"   Source: {image_data['source']}")
                print(f"   Model: {image_data['model']}")
                
                if save_base64_image(image_data["base64"], filename):
                    print(f"   File size: {os.path.getsize(filename)} bytes")
                    print(f"   Location: {os.path.abspath(filename)}")
            else:
                print(f"❌ Image {i+1} failed: {image_data.get('error', 'Unknown error')}")
    else:
        print(f"❌ Image generation failed: {result}")

def test_stable_diffusion_generation():
    """Test Stable Diffusion image generation and save results."""
    print("\n🎨 Testing Stable Diffusion Image Generation...")
    
    # Test prompt
    prompt = "A cool cat wearing sunglasses and a leather jacket, driving a vintage motorcycle"
    negative_prompt = "blurry, low quality, distorted"
    
    print(f"📝 Prompt: {prompt}")
    print(f"🚫 Negative Prompt: {negative_prompt}")
    
    # Generate image
    result = generate_stable_diffusion_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=1024,
        height=1024,
        samples=1
    )
    
    if result.get("success"):
        print(f"✅ Successfully generated {result['total_images']} image(s)")
        
        # Save each generated image
        for i, image_data in enumerate(result["images"]):
            if image_data["status"] == "success":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_image_sd_{timestamp}_{i+1}.jpg"
                
                print(f"💾 Saving image {i+1}...")
                print(f"   Size: {image_data['width']}x{image_data['height']}")
                print(f"   Source: {image_data['source']}")
                print(f"   Model: {image_data['model']}")
                print(f"   Seed: {image_data['seed']}")
                
                if save_base64_image(image_data["base64"], filename):
                    print(f"   File size: {os.path.getsize(filename)} bytes")
                    print(f"   Location: {os.path.abspath(filename)}")
            else:
                print(f"❌ Image {i+1} failed: {image_data.get('error', 'Unknown error')}")
    else:
        print(f"❌ Image generation failed: {result}")

def main():
    """Main test function."""
    print("🚀 Image Generation Agent Test")
    print("=" * 50)
    
    # Check API keys
    gemini_key = os.getenv("GEMINI_API_KEY")
    stability_key = os.getenv("STABILITY_API_KEY")
    
    print(f"🔑 GEMINI_API_KEY: {'✅ Set' if gemini_key else '❌ Not set'}")
    print(f"🔑 STABILITY_API_KEY: {'✅ Set' if stability_key else '❌ Not set'}")
    print()
    
    # Test Imagen 4 if API key is available
    if gemini_key:
        test_imagen_generation()
    else:
        print("⚠️  Skipping Imagen 4 test - GEMINI_API_KEY not set")
    
    # Test Stable Diffusion if API key is available
    if stability_key:
        test_stable_diffusion_generation()
    else:
        print("⚠️  Skipping Stable Diffusion test - STABILITY_API_KEY not set")
    
    print("\n🎯 Test completed!")
    print("📁 Check the current directory for generated image files")

if __name__ == "__main__":
    main()