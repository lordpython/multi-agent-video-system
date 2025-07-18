# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Audio processing tools for timing and format conversion."""

import os
import tempfile
import subprocess
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class AudioTimingInput(BaseModel):
    """Input schema for audio timing tool."""
    script_scenes: List[Dict[str, Any]] = Field(description="List of video scenes with dialogue and timing")
    total_video_duration: float = Field(description="Total target video duration in seconds")


class AudioFormatInput(BaseModel):
    """Input schema for audio format conversion tool."""
    audio_data: bytes = Field(description="Raw audio data to convert")
    input_format: str = Field(default="wav", description="Input audio format")
    output_format: str = Field(default="mp3", description="Output audio format")
    bitrate: str = Field(default="128k", description="Audio bitrate for compression")


def calculate_audio_timing(script_scenes: List[Dict[str, Any]], total_video_duration: float) -> Dict[str, Any]:
    """
    Calculate precise timing for audio segments based on video scenes.
    
    Args:
        script_scenes: List of video scenes with dialogue and timing information
        total_video_duration: Total target video duration in seconds
        
    Returns:
        Dict containing timing information for each audio segment
    """
    try:
        if not script_scenes:
            return {
                "timing_segments": [],
                "total_duration": 0.0,
                "error": "No script scenes provided",
                "status": "error"
            }
        
        timing_segments = []
        current_time = 0.0
        
        # Calculate proportional timing for each scene
        total_scene_duration = sum(scene.get("duration", 0) for scene in script_scenes)
        
        if total_scene_duration == 0:
            # If no durations specified, distribute evenly
            scene_duration = total_video_duration / len(script_scenes)
            for i, scene in enumerate(script_scenes):
                timing_segment = {
                    "scene_number": scene.get("scene_number", i + 1),
                    "start_time": current_time,
                    "end_time": current_time + scene_duration,
                    "duration": scene_duration,
                    "dialogue": scene.get("dialogue", ""),
                    "description": scene.get("description", ""),
                    "audio_file_needed": bool(scene.get("dialogue", "").strip())
                }
                timing_segments.append(timing_segment)
                current_time += scene_duration
        else:
            # Scale durations to fit total video duration
            scale_factor = total_video_duration / total_scene_duration
            
            for i, scene in enumerate(script_scenes):
                scene_duration = scene.get("duration", 0) * scale_factor
                timing_segment = {
                    "scene_number": scene.get("scene_number", i + 1),
                    "start_time": current_time,
                    "end_time": current_time + scene_duration,
                    "duration": scene_duration,
                    "dialogue": scene.get("dialogue", ""),
                    "description": scene.get("description", ""),
                    "audio_file_needed": bool(scene.get("dialogue", "").strip()),
                    "visual_requirements": scene.get("visual_requirements", [])
                }
                timing_segments.append(timing_segment)
                current_time += scene_duration
        
        return {
            "timing_segments": timing_segments,
            "total_duration": current_time,
            "scene_count": len(script_scenes),
            "audio_segments_needed": len([seg for seg in timing_segments if seg["audio_file_needed"]]),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "timing_segments": [],
            "total_duration": 0.0,
            "error": f"Failed to calculate audio timing: {str(e)}",
            "status": "error"
        }


def convert_audio_format(
    audio_data: bytes, 
    input_format: str = "wav", 
    output_format: str = "mp3", 
    bitrate: str = "128k"
) -> Dict[str, Any]:
    """
    Convert audio data between different formats using FFmpeg.
    
    Args:
        audio_data: Raw audio data to convert
        input_format: Input audio format
        output_format: Output audio format
        bitrate: Audio bitrate for compression
        
    Returns:
        Dict containing converted audio data and metadata
    """
    try:
        if not audio_data:
            return {
                "converted_audio": b"",
                "base64": "",
                "error": "No audio data provided",
                "status": "error"
            }
        
        # Check if FFmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "converted_audio": audio_data,  # Return original if FFmpeg not available
                "base64": "",
                "warning": "FFmpeg not available, returning original audio data",
                "status": "warning"
            }
        
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix=f".{input_format}", delete=False) as input_file:
            input_file.write(audio_data)
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-acodec", get_audio_codec(output_format),
                "-b:a", bitrate,
                "-y",  # Overwrite output file
                output_path
            ]
            
            # Run FFmpeg conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                return {
                    "converted_audio": audio_data,  # Return original on error
                    "base64": "",
                    "error": f"FFmpeg conversion failed: {result.stderr}",
                    "status": "error"
                }
            
            # Read converted audio data
            with open(output_path, "rb") as f:
                converted_audio = f.read()
            
            # Convert to base64 for storage/transmission
            import base64
            base64_audio = base64.b64encode(converted_audio).decode('utf-8')
            
            return {
                "converted_audio": converted_audio,
                "base64": base64_audio,
                "input_format": input_format,
                "output_format": output_format,
                "bitrate": bitrate,
                "original_size": len(audio_data),
                "converted_size": len(converted_audio),
                "compression_ratio": len(audio_data) / len(converted_audio) if converted_audio else 1.0,
                "status": "success"
            }
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except OSError:
                pass  # Ignore cleanup errors
        
    except subprocess.TimeoutExpired:
        return {
            "converted_audio": audio_data,  # Return original on timeout
            "base64": "",
            "error": "Audio conversion timed out",
            "status": "error"
        }
    except Exception as e:
        return {
            "converted_audio": audio_data,  # Return original on error
            "base64": "",
            "error": f"Failed to convert audio format: {str(e)}",
            "status": "error"
        }


def get_audio_codec(format_name: str) -> str:
    """
    Get the appropriate audio codec for a given format.
    
    Args:
        format_name: Audio format name
        
    Returns:
        FFmpeg codec name
    """
    codec_map = {
        "mp3": "libmp3lame",
        "aac": "aac",
        "ogg": "libvorbis",
        "wav": "pcm_s16le",
        "flac": "flac",
        "m4a": "aac"
    }
    
    return codec_map.get(format_name.lower(), "libmp3lame")


def synchronize_audio_with_video(
    audio_segments: List[Dict[str, Any]], 
    video_timing: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Synchronize audio segments with video timing markers.
    
    Args:
        audio_segments: List of audio segments with timing information
        video_timing: List of video timing markers
        
    Returns:
        Dict containing synchronized timing information
    """
    try:
        synchronized_segments = []
        
        for i, audio_segment in enumerate(audio_segments):
            # Find corresponding video timing
            video_marker = None
            if i < len(video_timing):
                video_marker = video_timing[i]
            
            sync_segment = {
                "segment_id": i,
                "audio_start": audio_segment.get("start_time", 0.0),
                "audio_end": audio_segment.get("end_time", 0.0),
                "audio_duration": audio_segment.get("duration", 0.0),
                "video_start": video_marker.get("start_time", 0.0) if video_marker else 0.0,
                "video_end": video_marker.get("end_time", 0.0) if video_marker else 0.0,
                "sync_offset": 0.0,  # Can be adjusted for fine-tuning
                "fade_in": 0.1,  # 100ms fade in
                "fade_out": 0.1,  # 100ms fade out
                "volume": 1.0,  # Full volume
                "dialogue": audio_segment.get("dialogue", ""),
                "synchronized": True
            }
            
            synchronized_segments.append(sync_segment)
        
        return {
            "synchronized_segments": synchronized_segments,
            "total_segments": len(synchronized_segments),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "synchronized_segments": [],
            "total_segments": 0,
            "error": f"Failed to synchronize audio with video: {str(e)}",
            "status": "error"
        }


# Create the tool functions for ADK
audio_timing_tool = calculate_audio_timing
audio_format_tool = convert_audio_format