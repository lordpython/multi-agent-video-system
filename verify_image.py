#!/usr/bin/env python3
"""
Simple script to verify the generated image.
"""

import os
from pathlib import Path
from PIL import Image


def verify_image():
    """Verify the generated image file."""
    image_path = Path("generated_images/test_image_1.jpg")

    if not image_path.exists():
        print("❌ Image file not found!")
        return

    try:
        # Open and verify the image
        with Image.open(image_path) as img:
            print("✅ Image successfully loaded!")
            print(f"📏 Dimensions: {img.size[0]}x{img.size[1]}")
            print(f"🎨 Mode: {img.mode}")
            print(f"📁 Format: {img.format}")
            print(f"💾 File size: {os.path.getsize(image_path)} bytes")

            # Show basic image info
            print("🖼️ Image appears to be valid and viewable")

    except Exception as e:
        print(f"❌ Error opening image: {e}")


if __name__ == "__main__":
    verify_image()
