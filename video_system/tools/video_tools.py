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

"""Video tools for the video assembly agent."""

from typing import Dict, Any, List
from google.adk.tools import FunctionTool

# Import utilities from canonical paths
from video_system.utils.error_handling import get_logger

# Configure logger for video tools
logger = get_logger("video_tools")

def check_ffmpeg_health() -> Dict[str, Any]:
    """
    Check if FFmpeg is installed and operational.
    
    Returns:
        Dict[str, Any]: Status of FFmpeg installation with details
    """
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            logger.info("FFmpeg health check passed")
            return {
                "status": "healthy",
                "details": {
                    "version": result.stdout.split('\n')[0],
                    "message": "FFmpeg is installed and operational"
                }
            }
        else:
            logger.warning("FFmpeg health check failed: command returned non-zero exit code")
            return {
                "status": "unhealthy",
                "details": {
                    "error": "FFmpeg command returned error",
                    "stderr": result.stderr
                }
            }
    except FileNotFoundError:
        logger.error("FFmpeg health check failed: FFmpeg not found")
        return {
            "status": "unhealthy",
            "details": {"error": "FFmpeg not found in system path"}
        }
    except Exception as e:
        logger.error(f"FFmpeg health check failed with unexpected error: {str(e)}")
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }

def ffmpeg_composition_tool(
    video_files: List[str],
    audio_files: List[str],
    output_file: str
) -> Dict[str, Any]:
    """
    Compose video and audio files into a single video using FFmpeg.
    
    Args:
        video_files: List of video file paths to include
        audio_files: List of audio file paths to include
        output_file: Path where the output video should be saved
        context: Tool context for accessing session state
        
    Returns:
        Dict with status and output file information
    """
    try:
        import subprocess
        import os
        
        # Log operation start
        logger.info(f"Starting video composition with {len(video_files)} video files and {len(audio_files)} audio files")
        
        # Create a temporary file list for FFmpeg
        file_list = "file_list.txt"
        with open(file_list, "w") as f:
            for video in video_files:
                f.write(f"file '{video}'\n")
        
        # Concatenate videos first
        concat_video = "concat_video.mp4"
        video_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", file_list, "-c", "copy", concat_video
        ]
        
        video_process = subprocess.run(
            video_cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if video_process.returncode != 0:
            logger.error(f"Video concatenation failed: {video_process.stderr}")
            return {
                "status": "error",
                "message": "Failed to concatenate video files",
                "details": video_process.stderr
            }
        
        # Combine with audio
        if audio_files:
            # Merge the first audio file with the video
            primary_audio = audio_files[0]
            output_cmd = [
                "ffmpeg", "-y", "-i", concat_video, "-i", primary_audio,
                "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
                output_file
            ]
            
            output_process = subprocess.run(
                output_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if output_process.returncode != 0:
                logger.error(f"Audio-video merging failed: {output_process.stderr}")
                return {
                    "status": "error",
                    "message": "Failed to merge audio with video",
                    "details": output_process.stderr
                }
        else:
            # If no audio, just rename the concatenated video
            os.rename(concat_video, output_file)
        
        # Clean up temporary files
        if os.path.exists(file_list):
            os.remove(file_list)
        if os.path.exists(concat_video):
            os.remove(concat_video)
        
        logger.info(f"Video composition completed successfully: {output_file}")
        
        # Note: Session state would be updated by the agent framework
        
        return {
            "status": "success",
            "output_file": output_file,
            "duration_seconds": get_video_duration(output_file),
            "file_size_mb": os.path.getsize(output_file) / (1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Video composition failed with error: {str(e)}")
        return {
            "status": "error",
            "message": f"Video composition failed: {str(e)}"
        }

def video_synchronization_tool(
    video_path: str,
    audio_path: str,
    sync_point_seconds: float,
    output_path: str
) -> Dict[str, Any]:
    """
    Synchronize video and audio at a specific time point.
    
    Args:
        video_path: Path to the video file
        audio_path: Path to the audio file
        sync_point_seconds: Time point in seconds where synchronization should occur
        output_path: Path where the synchronized video should be saved
        context: Tool context for accessing session state
        
    Returns:
        Dict with status and output file information
    """
    try:
        import subprocess
        
        logger.info(f"Synchronizing video and audio at {sync_point_seconds} seconds")
        
        # Command to synchronize video and audio
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[1:a]adelay={int(sync_point_seconds*1000)}|{int(sync_point_seconds*1000)}[delayed_audio];[0:a][delayed_audio]amix=inputs=2:duration=longest[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac",
            output_path
        ]
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            logger.error(f"Audio-video synchronization failed: {process.stderr}")
            return {
                "status": "error",
                "message": "Failed to synchronize audio and video",
                "details": process.stderr
            }
        
        logger.info(f"Audio-video synchronization completed successfully: {output_path}")
        
        # Note: Session state would be updated by the agent framework
        
        return {
            "status": "success",
            "output_file": output_path,
            "sync_point_seconds": sync_point_seconds
        }
    except Exception as e:
        logger.error(f"Audio-video synchronization failed with error: {str(e)}")
        return {
            "status": "error",
            "message": f"Audio-video synchronization failed: {str(e)}"
        }

def transition_effects_tool(
    video_files: List[str],
    transition_type: str,
    transition_duration: float,
    output_file: str
) -> Dict[str, Any]:
    """
    Apply transition effects between video clips.
    
    Args:
        video_files: List of video file paths to include
        transition_type: Type of transition (fade, dissolve, wipe, etc.)
        transition_duration: Duration of transition in seconds
        output_file: Path where the output video should be saved
        context: Tool context for accessing session state
        
    Returns:
        Dict with status and output file information
    """
    try:
        import subprocess
        
        logger.info(f"Applying {transition_type} transitions between {len(video_files)} video files")
        
        # Build complex filter based on transition type
        filter_complex = ""
        
        if transition_type == "fade":
            # Create fade transitions between clips
            for i in range(len(video_files) - 1):
                filter_complex += f"[{i}:v]fade=t=out:st={get_video_duration(video_files[i]) - transition_duration}:d={transition_duration}[v{i}];"
                filter_complex += f"[{i+1}:v]fade=t=in:st=0:d={transition_duration}[v{i+1}];"
                if i == 0:
                    filter_complex += f"[v{i}][v{i+1}]overlay[v{i+2}];"
                else:
                    filter_complex += f"[v{i+1}][v{i+2}]overlay[v{i+3}];"
        elif transition_type == "dissolve":
            # Create dissolve transitions between clips
            for i in range(len(video_files) - 1):
                filter_complex += f"[{i}:v][{i+1}:v]xfade=transition=fade:duration={transition_duration}:offset={get_video_duration(video_files[i]) - transition_duration}[v{i+2}];"
        else:
            # Default to simple concatenation
            filter_complex = "concat=n=" + str(len(video_files)) + ":v=1:a=1"
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y"]
        
        # Add input files
        for video in video_files:
            cmd.extend(["-i", video])
        
        # Add filter complex
        cmd.extend(["-filter_complex", filter_complex])
        
        # Add output file
        cmd.extend(["-c:v", "libx264", "-preset", "medium", output_file])
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            logger.error(f"Transition effects application failed: {process.stderr}")
            return {
                "status": "error",
                "message": "Failed to apply transition effects",
                "details": process.stderr
            }
        
        logger.info(f"Transition effects applied successfully: {output_file}")
        
        # Note: Session state would be updated by the agent framework
        
        return {
            "status": "success",
            "output_file": output_file,
            "transition_type": transition_type,
            "transition_duration": transition_duration
        }
    except Exception as e:
        logger.error(f"Transition effects application failed with error: {str(e)}")
        return {
            "status": "error",
            "message": f"Transition effects application failed: {str(e)}"
        }

def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration of the video in seconds
    """
    try:
        import subprocess
        import json
        
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to get video duration: {result.stderr}")
            return 0.0
        
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        
        return duration
    except Exception as e:
        logger.error(f"Failed to get video duration: {str(e)}")
        return 0.0
def video_encoding_tool(
    input_file: str,
    output_file: str,
    quality: str = "medium",
    format: str = "mp4"
) -> Dict[str, Any]:
    """
    Encode video to specified format and quality.
    
    Args:
        input_file: Path to the input video file
        output_file: Path where the encoded video should be saved
        quality: Encoding quality (low, medium, high, ultra)
        format: Output format (mp4, webm, mov, etc.)
        
    Returns:
        Dict with status and output file information
    """
    try:
        import subprocess
        import os
        
        logger.info(f"Encoding video to {format} format with {quality} quality")
        
        # Map quality settings to FFmpeg presets
        quality_presets = {
            "low": "ultrafast",
            "medium": "medium",
            "high": "slow",
            "ultra": "veryslow"
        }
        
        # Map quality settings to bitrates
        quality_bitrates = {
            "low": "1M",
            "medium": "4M",
            "high": "8M",
            "ultra": "16M"
        }
        
        preset = quality_presets.get(quality, "medium")
        bitrate = quality_bitrates.get(quality, "4M")
        
        # Ensure output file has correct extension
        if not output_file.endswith(f".{format}"):
            output_file = f"{os.path.splitext(output_file)[0]}.{format}"
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:v", "libx264",
            "-preset", preset,
            "-b:v", bitrate,
            "-c:a", "aac",
            "-b:a", "192k",
            output_file
        ]
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            logger.error(f"Video encoding failed: {process.stderr}")
            return {
                "status": "error",
                "message": "Failed to encode video",
                "details": process.stderr
            }
        
        logger.info(f"Video encoding completed successfully: {output_file}")
        
        return {
            "status": "success",
            "output_file": output_file,
            "format": format,
            "quality": quality,
            "file_size_mb": os.path.getsize(output_file) / (1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Video encoding failed with error: {str(e)}")
        return {
            "status": "error",
            "message": f"Video encoding failed: {str(e)}"
        }

# Create FunctionTool instances
ffmpeg_composition_tool = FunctionTool(ffmpeg_composition_tool)
video_synchronization_tool = FunctionTool(video_synchronization_tool)
transition_effects_tool = FunctionTool(transition_effects_tool)
video_encoding_tool = FunctionTool(video_encoding_tool)
check_ffmpeg_health = FunctionTool(check_ffmpeg_health)