#!/usr/bin/env python3
"""Test minimal imports."""

print("Testing imports one by one...")

try:
    print("✓ os")
except Exception as e:
    print(f"✗ os: {e}")

try:
    print("✓ logging")
except Exception as e:
    print(f"✗ logging: {e}")

try:
    print("✓ asyncio")
except Exception as e:
    print(f"✗ asyncio: {e}")

try:
    print("✓ aiohttp")
except Exception as e:
    print(f"✗ aiohttp: {e}")

try:
    print("✓ aiofiles")
except Exception as e:
    print(f"✗ aiofiles: {e}")

try:
    print("✓ typing")
except Exception as e:
    print(f"✗ typing: {e}")

try:
    print("✓ pathlib")
except Exception as e:
    print(f"✗ pathlib: {e}")

try:
    print("✓ datetime")
except Exception as e:
    print(f"✗ datetime: {e}")

try:
    print("✓ uuid")
except Exception as e:
    print(f"✗ uuid: {e}")

try:
    print("✓ json")
except Exception as e:
    print(f"✗ json: {e}")

print("\nTesting video generation imports...")

try:
    print("✓ moviepy")
except Exception as e:
    print(f"✗ moviepy: {e}")

try:
    print("✓ pyttsx3")
except Exception as e:
    print(f"✗ pyttsx3: {e}")

try:
    print("✓ PIL")
except Exception as e:
    print(f"✗ PIL: {e}")

try:
    print("✓ google.adk.tools.FunctionTool")
except Exception as e:
    print(f"✗ google.adk.tools.FunctionTool: {e}")

print("\nAll imports tested!")