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

"""Video encoding utilities for optimizing and formatting final video output."""

import subprocess
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
# Tool class not needed - using function-based tools

logger = logging.getLogger(__name__)


class EncodingRequest(BaseModel):
    """Request model for video encoding."""

    input_file: str = Field(..., description="Path to input video file")
    output_file: str = Field(..., description="Path to output encoded video file")
    format: Optional[str] = Field(
        "mp4", description="Output video format (mp4, webm, avi)"
    )
    quality: Optional[str] = Field(
        "high", description="Encoding quality (low, medium, high, ultra)"
    )
    resolution: Optional[str] = Field(
        None, description="Target resolution (e.g., '1920x1080')"
    )
    bitrate: Optional[str] = Field(None, description="Target bitrate (e.g., '5M')")
    fps: Optional[int] = Field(None, description="Target frames per second")
    audio_quality: Optional[str] = Field("high", description="Audio encoding quality")
    optimize_for: Optional[str] = Field(
        "quality", description="Optimization target: 'quality', 'size', 'streaming'"
    )


class EncodingResponse(BaseModel):
    """Response model for video encoding."""

    success: bool = Field(..., description="Whether encoding was successful")
    output_file: str = Field(..., description="Path to encoded video file")
    original_size: int = Field(..., description="Original file size in bytes")
    encoded_size: int = Field(..., description="Encoded file size in bytes")
    compression_ratio: float = Field(..., description="Compression ratio achieved")
    encoding_time: float = Field(..., description="Time taken for encoding in seconds")
    video_info: Dict[str, Any] = Field(
        default={}, description="Video information after encoding"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")


def encode_video(request: EncodingRequest) -> EncodingResponse:
    """
    Encode video with specified quality and format settings.

    This function:
    1. Analyzes input video properties
    2. Applies appropriate encoding settings based on requirements
    3. Optimizes for specified target (quality/size/streaming)
    4. Encodes video using FFmpeg with optimal parameters
    5. Provides detailed encoding statistics
    """
    try:
        import time

        start_time = time.time()

        logger.info(f"Starting video encoding: {request.input_file}")

        # Validate input file
        if not os.path.exists(request.input_file):
            return EncodingResponse(
                success=False,
                output_file="",
                original_size=0,
                encoded_size=0,
                compression_ratio=0.0,
                encoding_time=0.0,
                error_message=f"Input file not found: {request.input_file}",
            )

        # Get original file size and info
        original_size = os.path.getsize(request.input_file)
        original_info = _get_video_info(request.input_file)

        # Create output directory
        os.makedirs(os.path.dirname(request.output_file), exist_ok=True)

        # Build encoding command
        cmd = _build_encoding_command(request, original_info)

        logger.info(f"Executing encoding command: {' '.join(cmd)}")

        # Execute encoding
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )

        if result.returncode != 0:
            error_msg = f"Video encoding failed: {result.stderr}"
            logger.error(error_msg)
            return EncodingResponse(
                success=False,
                output_file="",
                original_size=original_size,
                encoded_size=0,
                compression_ratio=0.0,
                encoding_time=time.time() - start_time,
                error_message=error_msg,
            )

        # Get encoded file info
        encoded_size = os.path.getsize(request.output_file)
        encoded_info = _get_video_info(request.output_file)
        compression_ratio = original_size / encoded_size if encoded_size > 0 else 0.0
        encoding_time = time.time() - start_time

        logger.info(f"Encoding completed successfully in {encoding_time:.2f}s")
        logger.info(
            f"Size reduction: {original_size} -> {encoded_size} bytes (ratio: {compression_ratio:.2f})"
        )

        return EncodingResponse(
            success=True,
            output_file=request.output_file,
            original_size=original_size,
            encoded_size=encoded_size,
            compression_ratio=compression_ratio,
            encoding_time=encoding_time,
            video_info=encoded_info,
        )

    except subprocess.TimeoutExpired:
        error_msg = "Video encoding timed out after 30 minutes"
        logger.error(error_msg)
        return EncodingResponse(
            success=False,
            output_file="",
            original_size=0,
            encoded_size=0,
            compression_ratio=0.0,
            encoding_time=0.0,
            error_message=error_msg,
        )
    except Exception as e:
        error_msg = f"Error during video encoding: {str(e)}"
        logger.error(error_msg)
        return EncodingResponse(
            success=False,
            output_file="",
            original_size=0,
            encoded_size=0,
            compression_ratio=0.0,
            encoding_time=0.0,
            error_message=error_msg,
        )


def _build_encoding_command(
    request: EncodingRequest, original_info: Dict[str, Any]
) -> List[str]:
    """Build FFmpeg encoding command based on request parameters."""
    cmd = ["ffmpeg", "-y", "-i", request.input_file]

    # Get encoding settings based on quality and optimization target
    video_settings = _get_video_encoding_settings(request, original_info)
    audio_settings = _get_audio_encoding_settings(request.audio_quality)

    # Add video encoding settings
    cmd.extend(video_settings)

    # Add audio encoding settings
    cmd.extend(audio_settings)

    # Add format-specific settings
    format_settings = _get_format_settings(request.format)
    cmd.extend(format_settings)

    # Add output file
    cmd.append(request.output_file)

    return cmd


def _get_video_encoding_settings(
    request: EncodingRequest, original_info: Dict[str, Any]
) -> List[str]:
    """Get video encoding settings based on quality and optimization."""
    settings = []

    # Choose codec based on format and optimization
    if request.format == "webm":
        settings.extend(["-c:v", "libvpx-vp9"])
    else:
        settings.extend(["-c:v", "libx264"])

    # Quality settings based on optimization target
    if request.optimize_for == "size":
        quality_settings = _get_size_optimized_settings(request.quality)
    elif request.optimize_for == "streaming":
        quality_settings = _get_streaming_optimized_settings(request.quality)
    else:  # quality optimization
        quality_settings = _get_quality_optimized_settings(request.quality)

    settings.extend(quality_settings)

    # Resolution settings
    if request.resolution:
        settings.extend(["-s", request.resolution])
    elif request.optimize_for == "size":
        # Reduce resolution for size optimization
        original_width = original_info.get("width", 1920)
        original_info.get("height", 1080)
        if original_width > 1280:
            settings.extend(["-s", "1280x720"])

    # Frame rate settings
    if request.fps:
        settings.extend(["-r", str(request.fps)])
    elif request.optimize_for == "size":
        settings.extend(["-r", "24"])  # Lower fps for size optimization

    # Bitrate settings
    if request.bitrate:
        settings.extend(["-b:v", request.bitrate])

    return settings


def _get_quality_optimized_settings(quality: str) -> List[str]:
    """Get quality-optimized encoding settings."""
    quality_map = {
        "low": ["-crf", "28", "-preset", "fast"],
        "medium": ["-crf", "23", "-preset", "medium"],
        "high": ["-crf", "18", "-preset", "slow"],
        "ultra": ["-crf", "15", "-preset", "veryslow"],
    }
    return quality_map.get(quality, quality_map["high"])


def _get_size_optimized_settings(quality: str) -> List[str]:
    """Get size-optimized encoding settings."""
    quality_map = {
        "low": ["-crf", "32", "-preset", "fast"],
        "medium": ["-crf", "28", "-preset", "medium"],
        "high": ["-crf", "25", "-preset", "medium"],
        "ultra": ["-crf", "22", "-preset", "slow"],
    }
    return quality_map.get(quality, quality_map["medium"])


def _get_streaming_optimized_settings(quality: str) -> List[str]:
    """Get streaming-optimized encoding settings."""
    quality_map = {
        "low": ["-crf", "26", "-preset", "fast", "-tune", "zerolatency"],
        "medium": ["-crf", "23", "-preset", "fast", "-tune", "zerolatency"],
        "high": ["-crf", "20", "-preset", "medium", "-tune", "zerolatency"],
        "ultra": ["-crf", "18", "-preset", "medium", "-tune", "zerolatency"],
    }
    return quality_map.get(quality, quality_map["medium"])


def _get_audio_encoding_settings(audio_quality: str) -> List[str]:
    """Get audio encoding settings."""
    quality_map = {
        "low": ["-c:a", "aac", "-b:a", "96k"],
        "medium": ["-c:a", "aac", "-b:a", "128k"],
        "high": ["-c:a", "aac", "-b:a", "192k"],
        "ultra": ["-c:a", "aac", "-b:a", "256k"],
    }
    return quality_map.get(audio_quality, quality_map["high"])


def _get_format_settings(format: str) -> List[str]:
    """Get format-specific encoding settings."""
    format_map = {
        "mp4": ["-f", "mp4", "-movflags", "+faststart"],
        "webm": ["-f", "webm"],
        "avi": ["-f", "avi"],
        "mkv": ["-f", "matroska"],
    }
    return format_map.get(format, format_map["mp4"])


def _get_video_info(video_path: str) -> Dict[str, Any]:
    """Get detailed video information using FFprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)

            format_info = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            audio_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
                {},
            )

            return {
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": eval(video_stream.get("r_frame_rate", "0/1"))
                if video_stream.get("r_frame_rate")
                else 0,
                "video_codec": video_stream.get("codec_name", "unknown"),
                "audio_codec": audio_stream.get("codec_name", "unknown"),
                "audio_bitrate": int(audio_stream.get("bit_rate", 0))
                if audio_stream.get("bit_rate")
                else 0,
            }
    except Exception as e:
        logger.warning(f"Could not get video info: {e}")

    return {}


# Additional utility functions


def get_recommended_settings(file_size_mb: float, target_use: str) -> Dict[str, Any]:
    """Get recommended encoding settings based on file size and target use."""
    if target_use == "web":
        if file_size_mb > 100:
            return {
                "quality": "medium",
                "optimize_for": "size",
                "resolution": "1280x720",
            }
        else:
            return {"quality": "high", "optimize_for": "quality"}
    elif target_use == "mobile":
        return {
            "quality": "medium",
            "optimize_for": "size",
            "resolution": "854x480",
            "fps": 24,
        }
    elif target_use == "archive":
        return {"quality": "ultra", "optimize_for": "quality"}
    else:
        return {"quality": "high", "optimize_for": "quality"}


def estimate_encoding_time(duration_seconds: float, quality: str) -> float:
    """Estimate encoding time based on video duration and quality."""
    # Rough estimates based on typical encoding speeds
    speed_multipliers = {
        "low": 0.5,  # 2x realtime
        "medium": 1.0,  # 1x realtime
        "high": 2.0,  # 0.5x realtime
        "ultra": 4.0,  # 0.25x realtime
    }

    multiplier = speed_multipliers.get(quality, 1.0)
    return duration_seconds * multiplier


from google.adk.tools import FunctionTool

# Create the tool function for ADK
video_encoding_tool = FunctionTool(encode_video)
