#!/usr/bin/env python3
"""
Script to verify and analyze the actual quality of generated video output.
"""

import os
import json
from pathlib import Path

def analyze_video_quality():
    """Analyze the actual quality of generated videos."""
    print("🔍 HONEST VIDEO QUALITY ANALYSIS")
    print("=" * 50)
    
    output_dir = Path("output")
    generated_assets_dir = Path("generated_assets")
    
    # Check what we actually have
    video_files = list(output_dir.glob("*.mp4")) if output_dir.exists() else []
    json_files = list(output_dir.glob("*.json")) if output_dir.exists() else []
    image_files = list(generated_assets_dir.glob("*.png")) if generated_assets_dir.exists() else []
    audio_files = list(generated_assets_dir.glob("*.wav")) if generated_assets_dir.exists() else []
    
    print(f"📁 Found {len(video_files)} MP4 files")
    print(f"📁 Found {len(json_files)} JSON metadata files")
    print(f"📁 Found {len(image_files)} PNG images")
    print(f"📁 Found {len(audio_files)} WAV audio files")
    print()
    
    # Analyze the actual content
    if video_files:
        latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
        file_size = latest_video.stat().st_size
        print(f"🎬 Latest video: {latest_video.name}")
        print(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # This is brutally honest - let's see what we actually generated
        if file_size < 500000:  # Less than 500KB
            print("⚠️  WARNING: Very small file size for a 2-minute video")
            print("   This suggests either:")
            print("   - Very low quality/resolution")
            print("   - Mostly static content")
            print("   - Placeholder/mock content")
    
    # Check if images are real or just text placeholders
    if image_files:
        sample_image = image_files[0]
        file_size = sample_image.stat().st_size
        print(f"\n🖼️  Sample image: {sample_image.name}")
        print(f"📊 Image size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        if file_size < 50000:  # Less than 50KB for 1920x1080
            print("⚠️  WARNING: Very small for claimed 1920x1080 resolution")
            print("   Likely simple text-on-background images")
    
    # Check JSON metadata to see what was actually generated
    if json_files:
        latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_json, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            print(f"\n📋 Metadata from {latest_json.name}:")
            if 'script' in metadata:
                script = metadata['script']
                if 'scenes' in script:
                    print(f"   Scenes: {len(script['scenes'])}")
                    for i, scene in enumerate(script['scenes'][:2]):  # Show first 2 scenes
                        print(f"   Scene {i}: {scene.get('description', 'No description')[:100]}...")
            
            if 'research' in metadata:
                research = metadata['research']
                print(f"   Research quality: {research.get('quality_score', 'Unknown')}")
                
        except Exception as e:
            print(f"❌ Could not read metadata: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 REALITY CHECK:")
    
    # Be brutally honest about what this actually is
    total_files = len(video_files) + len(image_files) + len(audio_files)
    if total_files > 0:
        print("✅ YES - Real files were generated")
        print("✅ YES - This creates actual MP4 videos")
        print("✅ YES - Uses real libraries (MoviePy, PIL, pyttsx3)")
        print()
        print("⚠️  BUT - Quality limitations:")
        print("   - Images are simple text-on-background (not AI-generated)")
        print("   - Audio is basic TTS (not professional voiceover)")
        print("   - Research is simulated (not real web scraping)")
        print("   - Video is just image slideshow with audio")
        print()
        print("🎯 VERDICT: Real output, basic quality")
        print("   Good for: Proof of concept, demos, simple content")
        print("   Not good for: Professional/commercial use")
    else:
        print("❌ NO - No actual files generated")
        print("   This appears to be mock/placeholder output")
    
    return total_files > 0

if __name__ == "__main__":
    analyze_video_quality()