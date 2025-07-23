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

"""Transition effects tool for applying smooth transitions between video scenes."""

import subprocess
import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
# Tool class not needed - using function-based tools

logger = logging.getLogger(__name__)


class TransitionRequest(BaseModel):
    """Request model for applying transitions."""

    input_segments: List[str] = Field(
        ..., description="List of video segment file paths"
    )
    transition_types: List[str] = Field(
        ..., description="List of transition types for each segment"
    )
    transition_durations: List[float] = Field(
        ..., description="Duration of each transition in seconds"
    )
    output_path: str = Field(..., description="Output video file path")
    resolution: Optional[str] = Field(
        "1920x1080", description="Output video resolution"
    )
    fps: Optional[int] = Field(30, description="Frames per second")


class TransitionResponse(BaseModel):
    """Response model for transition application."""

    success: bool = Field(
        ..., description="Whether transitions were applied successfully"
    )
    output_file: str = Field(..., description="Path to video with transitions")
    total_duration: float = Field(
        ..., description="Total duration of video with transitions"
    )
    transitions_applied: List[str] = Field(
        default=[], description="List of transitions that were applied"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")


def apply_video_transitions(request: TransitionRequest) -> TransitionResponse:
    """
    Apply smooth transitions between video segments using FFmpeg.

    This function:
    1. Validates input video segments
    2. Creates FFmpeg filter complex for transitions
    3. Applies specified transition effects between segments
    4. Renders final video with smooth transitions
    """
    try:
        logger.info("Starting transition application")

        # Validate inputs
        if len(request.input_segments) < 2:
            return TransitionResponse(
                success=False,
                output_file="",
                total_duration=0.0,
                error_message="At least 2 video segments required for transitions",
            )

        # Check if all input files exist
        missing_files = [f for f in request.input_segments if not os.path.exists(f)]
        if missing_files:
            return TransitionResponse(
                success=False,
                output_file="",
                total_duration=0.0,
                error_message=f"Missing input files: {missing_files}",
            )

        # Create output directory
        os.makedirs(os.path.dirname(request.output_path), exist_ok=True)

        # Build FFmpeg command with transitions
        cmd = _build_transition_command(request)

        logger.info(f"Executing FFmpeg transition command: {' '.join(cmd)}")

        # Execute FFmpeg command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for complex transitions
        )

        if result.returncode != 0:
            error_msg = f"FFmpeg transition failed: {result.stderr}"
            logger.error(error_msg)
            return TransitionResponse(
                success=False,
                output_file="",
                total_duration=0.0,
                error_message=error_msg,
            )

        # Get output video duration
        duration = _get_video_duration(request.output_path)

        # List applied transitions
        transitions_applied = _get_applied_transitions(request.transition_types)

        logger.info(f"Transitions applied successfully: {request.output_path}")

        return TransitionResponse(
            success=True,
            output_file=request.output_path,
            total_duration=duration,
            transitions_applied=transitions_applied,
        )

    except subprocess.TimeoutExpired:
        error_msg = "FFmpeg transition command timed out"
        logger.error(error_msg)
        return TransitionResponse(
            success=False, output_file="", total_duration=0.0, error_message=error_msg
        )
    except Exception as e:
        error_msg = f"Error applying transitions: {str(e)}"
        logger.error(error_msg)
        return TransitionResponse(
            success=False, output_file="", total_duration=0.0, error_message=error_msg
        )


def _build_transition_command(request: TransitionRequest) -> List[str]:
    """Build FFmpeg command for applying transitions."""
    cmd = ["ffmpeg", "-y"]

    # Add input files
    for segment in request.input_segments:
        cmd.extend(["-i", segment])

    # Build filter complex for transitions
    filter_complex = _build_transition_filter_complex(request)
    cmd.extend(["-filter_complex", filter_complex])

    # Set output parameters
    cmd.extend(
        [
            "-map",
            "[final]",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-s",
            request.resolution,
            "-r",
            str(request.fps),
            request.output_path,
        ]
    )

    return cmd


def _build_transition_filter_complex(request: TransitionRequest) -> str:
    """Build FFmpeg filter complex for transitions between segments."""
    filters = []

    # Scale all inputs to same resolution
    for i in range(len(request.input_segments)):
        filters.append(f"[{i}:v]scale={request.resolution}[v{i}]")

    # Apply transitions between consecutive segments
    current_output = "v0"

    for i in range(1, len(request.input_segments)):
        transition_type = (
            request.transition_types[i - 1]
            if i - 1 < len(request.transition_types)
            else "crossfade"
        )
        transition_duration = (
            request.transition_durations[i - 1]
            if i - 1 < len(request.transition_durations)
            else 1.0
        )

        transition_filter = _get_transition_filter(
            current_output, f"v{i}", transition_type, transition_duration
        )

        output_name = f"trans{i}" if i < len(request.input_segments) - 1 else "final"
        filters.append(f"{transition_filter}[{output_name}]")
        current_output = output_name

    return ";".join(filters)


def _get_transition_filter(
    input1: str, input2: str, transition_type: str, duration: float
) -> str:
    """Get FFmpeg filter for specific transition type."""
    transition_filters = {
        "crossfade": f"[{input1}][{input2}]xfade=transition=fade:duration={duration}:offset=0",
        "fade_in": f"[{input1}][{input2}]xfade=transition=fadein:duration={duration}:offset=0",
        "fade_out": f"[{input1}][{input2}]xfade=transition=fadeout:duration={duration}:offset=0",
        "slide": f"[{input1}][{input2}]xfade=transition=slideleft:duration={duration}:offset=0",
        "wipe": f"[{input1}][{input2}]xfade=transition=wipeleft:duration={duration}:offset=0",
        "zoom": f"[{input1}][{input2}]xfade=transition=zoomin:duration={duration}:offset=0",
        "dissolve": f"[{input1}][{input2}]xfade=transition=dissolve:duration={duration}:offset=0",
        "pixelize": f"[{input1}][{input2}]xfade=transition=pixelize:duration={duration}:offset=0",
        "radial": f"[{input1}][{input2}]xfade=transition=radial:duration={duration}:offset=0",
        "smooth": f"[{input1}][{input2}]xfade=transition=smoothleft:duration={duration}:offset=0",
    }

    return transition_filters.get(transition_type, transition_filters["crossfade"])


def _get_video_duration(video_path: str) -> float:
    """Get video duration using FFprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}")

    return 0.0


def _get_applied_transitions(transition_types: List[str]) -> List[str]:
    """Get list of transitions that were applied."""
    unique_transitions = list(set(transition_types))
    return [f"{t.replace('_', ' ').title()} transition" for t in unique_transitions]


# Additional utility functions for transition management


def get_available_transitions() -> List[str]:
    """Get list of available transition types."""
    return [
        "crossfade",
        "fade_in",
        "fade_out",
        "slide",
        "wipe",
        "zoom",
        "dissolve",
        "pixelize",
        "radial",
        "smooth",
    ]


def suggest_transition_for_content(scene_description: str) -> str:
    """Suggest appropriate transition based on scene content."""
    description_lower = scene_description.lower()

    if "dramatic" in description_lower or "intense" in description_lower:
        return "zoom"
    elif "peaceful" in description_lower or "calm" in description_lower:
        return "dissolve"
    elif "action" in description_lower or "fast" in description_lower:
        return "slide"
    elif "emotional" in description_lower:
        return "fade_in"
    else:
        return "crossfade"  # Default safe choice


def calculate_optimal_transition_duration(segment_duration: float) -> float:
    """Calculate optimal transition duration based on segment length."""
    # Transition should be 5-10% of segment duration, with reasonable bounds
    optimal_duration = segment_duration * 0.075  # 7.5%

    # Clamp between 0.5 and 3.0 seconds
    return max(0.5, min(3.0, optimal_duration))


from google.adk.tools import FunctionTool

# Create the tool function for ADK
transition_effects_tool = FunctionTool(apply_video_transitions)
