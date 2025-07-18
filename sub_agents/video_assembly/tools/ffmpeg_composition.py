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

"""FFmpeg video composition tool for combining assets and audio."""

import subprocess
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
# Tool class not needed - using function-based tools

logger = logging.getLogger(__name__)


class VideoCompositionRequest(BaseModel):
    """Request model for video composition."""
    video_assets: List[str] = Field(..., description="List of video/image asset file paths")
    audio_file: str = Field(..., description="Path to audio file")
    output_path: str = Field(..., description="Output video file path")
    scene_timings: List[Dict[str, Any]] = Field(..., description="Scene timing information")
    resolution: Optional[str] = Field("1920x1080", description="Output video resolution")
    fps: Optional[int] = Field(30, description="Frames per second")
    quality: Optional[str] = Field("high", description="Video quality setting")


class VideoCompositionResponse(BaseModel):
    """Response model for video composition."""
    success: bool = Field(..., description="Whether composition was successful")
    output_file: str = Field(..., description="Path to composed video file")
    duration: float = Field(..., description="Duration of composed video in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


def compose_video_with_ffmpeg(request: VideoCompositionRequest) -> VideoCompositionResponse:
    """
    Compose video using FFmpeg by combining visual assets with audio.
    
    This function creates a video by:
    1. Creating a filter complex for combining multiple assets
    2. Synchronizing visual content with audio timing
    3. Applying appropriate scaling and formatting
    4. Encoding to final output format
    """
    try:
        # Validate input files exist
        if not os.path.exists(request.audio_file):
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=f"Audio file not found: {request.audio_file}"
            )
        
        missing_assets = [asset for asset in request.video_assets if not os.path.exists(asset)]
        if missing_assets:
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=f"Missing video assets: {missing_assets}"
            )
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(request.output_path), exist_ok=True)
        
        # Build FFmpeg command for video composition
        cmd = _build_ffmpeg_composition_command(request)
        
        logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
        
        # Execute FFmpeg command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = f"FFmpeg failed with return code {result.returncode}: {result.stderr}"
            logger.error(error_msg)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error_msg
            )
        
        # Get video duration
        duration = _get_video_duration(request.output_path)
        
        # Get video metadata
        metadata = _get_video_metadata(request.output_path)
        
        logger.info(f"Video composition successful: {request.output_path}")
        
        return VideoCompositionResponse(
            success=True,
            output_file=request.output_path,
            duration=duration,
            metadata=metadata
        )
        
    except subprocess.TimeoutExpired:
        error_msg = "FFmpeg command timed out after 5 minutes"
        logger.error(error_msg)
        return VideoCompositionResponse(
            success=False,
            output_file="",
            duration=0.0,
            error_message=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error during video composition: {str(e)}"
        logger.error(error_msg)
        return VideoCompositionResponse(
            success=False,
            output_file="",
            duration=0.0,
            error_message=error_msg
        )


def _build_ffmpeg_composition_command(request: VideoCompositionRequest) -> List[str]:
    """Build FFmpeg command for video composition."""
    cmd = ["ffmpeg", "-y"]  # -y to overwrite output file
    
    # Add input files
    for asset in request.video_assets:
        cmd.extend(["-i", asset])
    
    # Add audio input
    cmd.extend(["-i", request.audio_file])
    
    # Build filter complex for combining assets
    filter_complex = _build_filter_complex(request)
    if filter_complex:
        cmd.extend(["-filter_complex", filter_complex])
    
    # Set video codec and quality
    quality_settings = _get_quality_settings(request.quality)
    cmd.extend(quality_settings)
    
    # Set output format and resolution
    cmd.extend([
        "-s", request.resolution,
        "-r", str(request.fps),
        "-c:a", "aac",
        "-b:a", "128k"
    ])
    
    # Output file
    cmd.append(request.output_path)
    
    return cmd


def _build_filter_complex(request: VideoCompositionRequest) -> str:
    """Build FFmpeg filter complex for combining multiple assets with timing."""
    if not request.scene_timings:
        # Simple concatenation if no timing info
        return f"concat=n={len(request.video_assets)}:v=1:a=0[v]"
    
    # Build complex filter with timing
    filters = []
    
    # Scale all inputs to same resolution
    for i, _ in enumerate(request.video_assets):
        filters.append(f"[{i}:v]scale={request.resolution}[v{i}]")
    
    # Create timed segments based on scene timings
    concat_inputs = []
    for i, timing in enumerate(request.scene_timings):
        start_time = timing.get('start_time', 0)
        duration = timing.get('duration', 5)  # Default 5 seconds
        
        if i < len(request.video_assets):
            # For images, create video segment with specified duration
            if _is_image_file(request.video_assets[i]):
                filters.append(f"[v{i}]loop=loop=-1:size={request.fps * int(duration)}:start=0[loop{i}]")
                concat_inputs.append(f"[loop{i}]")
            else:
                # For videos, trim to specified duration
                filters.append(f"[v{i}]trim=duration={duration}[trim{i}]")
                concat_inputs.append(f"[trim{i}]")
    
    # Concatenate all segments
    if concat_inputs:
        concat_filter = "".join(concat_inputs) + f"concat=n={len(concat_inputs)}:v=1:a=0[v]"
        filters.append(concat_filter)
    
    return ";".join(filters)


def _is_image_file(file_path: str) -> bool:
    """Check if file is an image based on extension."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    return os.path.splitext(file_path.lower())[1] in image_extensions


def _get_quality_settings(quality: str) -> List[str]:
    """Get FFmpeg quality settings based on quality level."""
    quality_map = {
        "low": ["-c:v", "libx264", "-crf", "28", "-preset", "fast"],
        "medium": ["-c:v", "libx264", "-crf", "23", "-preset", "medium"],
        "high": ["-c:v", "libx264", "-crf", "18", "-preset", "slow"],
        "ultra": ["-c:v", "libx264", "-crf", "15", "-preset", "veryslow"]
    }
    return quality_map.get(quality, quality_map["high"])


def _get_video_duration(video_path: str) -> float:
    """Get video duration using FFprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}")
    
    return 0.0


def _get_video_metadata(video_path: str) -> Dict[str, Any]:
    """Get video metadata using FFprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # Extract relevant metadata
            format_info = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )
            
            return {
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")),
                "codec": video_stream.get("codec_name", "unknown")
            }
    except Exception as e:
        logger.warning(f"Could not get video metadata: {e}")
    
    return {}


# Create the tool function for ADK
ffmpeg_composition_tool = compose_video_with_ffmpeg