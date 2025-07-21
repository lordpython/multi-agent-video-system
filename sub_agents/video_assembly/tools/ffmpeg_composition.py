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

"""FFmpeg video composition tool for combining assets and audio with comprehensive error handling."""

import subprocess
import os
import json
import shutil
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from video_system.shared_libraries import (
    ProcessingError,
    ResourceError,
    ValidationError,
    TimeoutError,
    RetryConfig,
    get_logger,
    log_error,
    with_resource_check
)

# Configure logger for video composition
logger = get_logger("video_assembly.ffmpeg_composition")


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


# Configure retry settings for FFmpeg operations
ffmpeg_retry_config = RetryConfig(
    max_attempts=2,  # FFmpeg operations are expensive, limit retries
    base_delay=5.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)


@with_resource_check
def compose_video_with_ffmpeg(request: VideoCompositionRequest) -> VideoCompositionResponse:
    """
    Compose video using FFmpeg by combining visual assets with audio with comprehensive error handling.
    
    This function creates a video by:
    1. Creating a filter complex for combining multiple assets
    2. Synchronizing visual content with audio timing
    3. Applying appropriate scaling and formatting
    4. Encoding to final output format
    """
    try:
        # Input validation
        if not request.video_assets:
            error = ValidationError("No video assets provided", field="video_assets")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        if not request.audio_file:
            error = ValidationError("No audio file provided", field="audio_file")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        if not request.output_path:
            error = ValidationError("No output path provided", field="output_path")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Check if FFmpeg is available
        if not _check_ffmpeg_availability():
            error = ResourceError("FFmpeg is not available on this system", resource_type="ffmpeg")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        logger.info(f"Starting video composition with {len(request.video_assets)} assets")
        
        # Validate input files exist
        if not os.path.exists(request.audio_file):
            error = ValidationError(f"Audio file not found: {request.audio_file}", field="audio_file")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        missing_assets = [asset for asset in request.video_assets if not os.path.exists(asset)]
        if missing_assets:
            error = ValidationError(f"Missing video assets: {missing_assets}", field="video_assets")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Validate file formats
        validation_errors = _validate_media_files(request.video_assets, request.audio_file)
        if validation_errors:
            error = ValidationError(f"Media file validation failed: {'; '.join(validation_errors)}")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Check available disk space
        if not _check_disk_space(request.output_path):
            error = ResourceError("Insufficient disk space for video composition", resource_type="disk")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Create output directory if it doesn't exist
        try:
            os.makedirs(os.path.dirname(request.output_path), exist_ok=True)
        except OSError as e:
            error = ResourceError(f"Failed to create output directory: {str(e)}", resource_type="filesystem")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Build FFmpeg command for video composition
        cmd = _build_ffmpeg_composition_command(request)
        
        logger.info(f"Executing FFmpeg command with {len(cmd)} parameters")
        
        # Execute FFmpeg command with timeout and error handling
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for video processing
            )
            
            if result.returncode != 0:
                error_msg = f"FFmpeg failed with return code {result.returncode}: {result.stderr}"
                error = ProcessingError(error_msg, stage="ffmpeg_execution")
                log_error(logger, error, {"command": " ".join(cmd[:5]) + "..."})  # Log first 5 args only
                return VideoCompositionResponse(
                    success=False,
                    output_file="",
                    duration=0.0,
                    error_message=error.message
                )
            
        except subprocess.TimeoutExpired:
            error = TimeoutError("FFmpeg command timed out after 10 minutes", timeout_duration=600.0)
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Verify output file was created
        if not os.path.exists(request.output_path):
            error = ProcessingError("Output video file was not created", stage="output_verification")
            log_error(logger, error)
            return VideoCompositionResponse(
                success=False,
                output_file="",
                duration=0.0,
                error_message=error.message
            )
        
        # Get video duration and metadata
        try:
            duration = _get_video_duration(request.output_path)
            metadata = _get_video_metadata(request.output_path)
        except Exception as e:
            logger.warning(f"Failed to get video metadata: {str(e)}")
            duration = 0.0
            metadata = {}
        
        logger.info(f"Video composition successful: {request.output_path} ({duration:.2f}s)")
        
        return VideoCompositionResponse(
            success=True,
            output_file=request.output_path,
            duration=duration,
            metadata=metadata
        )
        
    except (ValidationError, ProcessingError, ResourceError, TimeoutError) as e:
        log_error(logger, e, {"output_path": request.output_path})
        return VideoCompositionResponse(
            success=False,
            output_file="",
            duration=0.0,
            error_message=e.message
        )
    
    except Exception as e:
        error = ProcessingError(f"Unexpected error during video composition: {str(e)}", original_exception=e)
        log_error(logger, error, {"output_path": request.output_path})
        return VideoCompositionResponse(
            success=False,
            output_file="",
            duration=0.0,
            error_message=error.message
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


def _check_ffmpeg_availability() -> bool:
    """Check if FFmpeg is available on the system."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _validate_media_files(video_assets: List[str], audio_file: str) -> List[str]:
    """Validate media file formats and accessibility."""
    errors = []
    
    # Check video assets
    for asset in video_assets:
        if not os.access(asset, os.R_OK):
            errors.append(f"Cannot read video asset: {asset}")
            continue
        
        # Check file extension
        ext = os.path.splitext(asset.lower())[1]
        valid_video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        valid_image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        
        if ext not in valid_video_exts and ext not in valid_image_exts:
            errors.append(f"Unsupported video asset format: {asset}")
    
    # Check audio file
    if not os.access(audio_file, os.R_OK):
        errors.append(f"Cannot read audio file: {audio_file}")
    else:
        ext = os.path.splitext(audio_file.lower())[1]
        valid_audio_exts = {'.wav', '.mp3', '.aac', '.m4a', '.ogg', '.flac'}
        
        if ext not in valid_audio_exts:
            errors.append(f"Unsupported audio format: {audio_file}")
    
    return errors


def _check_disk_space(output_path: str, min_space_gb: float = 1.0) -> bool:
    """Check if there's sufficient disk space for video output."""
    try:
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            output_dir = "."
        
        # Get disk usage
        total, used, free = shutil.disk_usage(output_dir)
        free_gb = free / (1024**3)
        
        logger.info(f"Available disk space: {free_gb:.2f} GB")
        return free_gb >= min_space_gb
    except OSError:
        # If we can't check disk space, assume it's available
        logger.warning("Could not check disk space")
        return True


def check_ffmpeg_health() -> Dict[str, Any]:
    """Perform a health check on FFmpeg availability and functionality."""
    try:
        # Check if FFmpeg is available
        if not _check_ffmpeg_availability():
            return {
                "status": "unhealthy",
                "details": {"error": "FFmpeg is not available on this system"}
            }
        
        # Check FFprobe availability
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return {
                    "status": "degraded",
                    "details": {"error": "FFprobe is not available"}
                }
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return {
                "status": "degraded",
                "details": {"error": "FFprobe is not available"}
            }
        
        return {
            "status": "healthy",
            "details": {"message": "FFmpeg and FFprobe are available and functional"}
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


from google.adk.tools import FunctionTool
# Create the tool function for ADK
ffmpeg_composition_tool = FunctionTool(compose_video_with_ffmpeg)