#!/usr/bin/env python3
"""Test minimal imports."""

print("Testing imports one by one...")

try:
    import os
    print("✓ os")
except Exception as e:
    print(f"✗ os: {e}")

try:
    import logging
    print("✓ logging")
except Exception as e:
    print(f"✗ logging: {e}")

try:
    import asyncio
    print("✓ asyncio")
except Exception as e:
    print(f"✗ asyncio: {e}")

try:
    import aiohttp
    print("✓ aiohttp")
except Exception as e:
    print(f"✗ aiohttp: {e}")

try:
    import aiofiles
    print("✓ aiofiles")
except Exception as e:
    print(f"✗ aiofiles: {e}")

try:
    from typing import Dict, Any, List
    print("✓ typing")
except Exception as e:
    print(f"✗ typing: {e}")

try:
    from pathlib import Path
    print("✓ pathlib")
except Exception as e:
    print(f"✗ pathlib: {e}")

try:
    from datetime import datetime
    print("✓ datetime")
except Exception as e:
    print(f"✗ datetime: {e}")

try:
    import uuid
    print("✓ uuid")
except Exception as e:
    print(f"✗ uuid: {e}")

try:
    import json
    print("✓ json")
except Exception as e:
    print(f"✗ json: {e}")

print("\nTesting video generation imports...")

try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip, 
        TextClip, concatenate_videoclips
    )
    print("✓ moviepy")
except Exception as e:
    print(f"✗ moviepy: {e}")

try:
    import pyttsx3
    print("✓ pyttsx3")
except Exception as e:
    print(f"✗ pyttsx3: {e}")

try:
    from PIL import Image, ImageDraw, ImageFont
    print("✓ PIL")
except Exception as e:
    print(f"✗ PIL: {e}")

try:
    from google.adk.tools import FunctionTool
    print("✓ google.adk.tools.FunctionTool")
except Exception as e:
    print(f"✗ google.adk.tools.FunctionTool: {e}")

print("\nAll imports tested!")