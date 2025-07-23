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

"""Video synchronization tool for aligning visual content with audio timing."""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
# Tool class not needed - using function-based tools

logger = logging.getLogger(__name__)


class SynchronizationRequest(BaseModel):
    """Request model for video synchronization."""

    scenes: List[Dict[str, Any]] = Field(
        ..., description="List of scene information with timing"
    )
    audio_segments: List[Dict[str, Any]] = Field(
        ..., description="Audio segment timing information"
    )
    visual_assets: List[str] = Field(..., description="List of visual asset file paths")
    target_duration: float = Field(
        ..., description="Target total video duration in seconds"
    )


class SynchronizationResponse(BaseModel):
    """Response model for video synchronization."""

    success: bool = Field(..., description="Whether synchronization was successful")
    synchronized_timeline: List[Dict[str, Any]] = Field(
        ..., description="Synchronized timeline with precise timing"
    )
    total_duration: float = Field(..., description="Total synchronized duration")
    adjustments_made: List[str] = Field(
        default=[], description="List of adjustments made during sync"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")


def synchronize_video_timeline(
    request: SynchronizationRequest,
) -> SynchronizationResponse:
    """
    Synchronize visual assets with audio segments to create precise timeline.

    This function:
    1. Analyzes audio segment durations and timing
    2. Maps visual assets to corresponding audio segments
    3. Calculates precise start/end times for each visual element
    4. Handles timing adjustments and transitions
    5. Creates a synchronized timeline for video assembly
    """
    try:
        logger.info("Starting video timeline synchronization")

        # Validate inputs
        if not request.scenes or not request.audio_segments:
            return SynchronizationResponse(
                success=False,
                synchronized_timeline=[],
                total_duration=0.0,
                error_message="Missing scenes or audio segments for synchronization",
            )

        # Calculate audio timing
        audio_timeline = _calculate_audio_timeline(request.audio_segments)

        # Map scenes to audio segments
        scene_mapping = _map_scenes_to_audio(request.scenes, audio_timeline)

        # Create synchronized timeline
        synchronized_timeline = _create_synchronized_timeline(
            scene_mapping, request.visual_assets, audio_timeline
        )

        # Apply timing adjustments
        adjusted_timeline, adjustments = _apply_timing_adjustments(
            synchronized_timeline, request.target_duration
        )

        # Calculate total duration
        total_duration = _calculate_total_duration(adjusted_timeline)

        logger.info(f"Synchronization completed. Total duration: {total_duration}s")

        return SynchronizationResponse(
            success=True,
            synchronized_timeline=adjusted_timeline,
            total_duration=total_duration,
            adjustments_made=adjustments,
        )

    except Exception as e:
        error_msg = f"Error during video synchronization: {str(e)}"
        logger.error(error_msg)
        return SynchronizationResponse(
            success=False,
            synchronized_timeline=[],
            total_duration=0.0,
            error_message=error_msg,
        )


def _calculate_audio_timeline(
    audio_segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Calculate precise timing for audio segments."""
    timeline = []
    current_time = 0.0

    for i, segment in enumerate(audio_segments):
        duration = segment.get("duration", 0.0)

        timeline_entry = {
            "segment_id": i,
            "start_time": current_time,
            "end_time": current_time + duration,
            "duration": duration,
            "text": segment.get("text", ""),
            "audio_file": segment.get("audio_file", ""),
            "scene_number": segment.get("scene_number", i + 1),
        }

        timeline.append(timeline_entry)
        current_time += duration

    return timeline


def _map_scenes_to_audio(
    scenes: List[Dict[str, Any]], audio_timeline: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Map video scenes to corresponding audio segments."""
    scene_mapping = []

    for scene in scenes:
        scene_number = scene.get("scene_number", 1)

        # Find corresponding audio segment
        audio_segment = next(
            (seg for seg in audio_timeline if seg["scene_number"] == scene_number), None
        )

        if audio_segment:
            mapping = {
                "scene_number": scene_number,
                "description": scene.get("description", ""),
                "visual_requirements": scene.get("visual_requirements", []),
                "assets": scene.get("assets", []),
                "audio_start": audio_segment["start_time"],
                "audio_end": audio_segment["end_time"],
                "audio_duration": audio_segment["duration"],
                "audio_file": audio_segment["audio_file"],
                "dialogue": scene.get("dialogue", audio_segment["text"]),
            }
            scene_mapping.append(mapping)
        else:
            logger.warning(f"No audio segment found for scene {scene_number}")

    return scene_mapping


def _create_synchronized_timeline(
    scene_mapping: List[Dict[str, Any]],
    visual_assets: List[str],
    audio_timeline: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Create synchronized timeline with visual and audio elements."""
    timeline = []

    for i, scene in enumerate(scene_mapping):
        # Assign visual assets to scene
        scene_assets = _assign_assets_to_scene(scene, visual_assets, i)

        timeline_entry = {
            "scene_number": scene["scene_number"],
            "start_time": scene["audio_start"],
            "end_time": scene["audio_end"],
            "duration": scene["audio_duration"],
            "visual_assets": scene_assets,
            "audio_file": scene["audio_file"],
            "dialogue": scene["dialogue"],
            "description": scene["description"],
            "transition_type": _determine_transition_type(i, len(scene_mapping)),
            "transition_duration": 0.5,  # Default transition duration
        }

        timeline.append(timeline_entry)

    return timeline


def _assign_assets_to_scene(
    scene: Dict[str, Any], visual_assets: List[str], scene_index: int
) -> List[str]:
    """Assign visual assets to a specific scene."""
    scene_assets = []

    # Use scene-specific assets if available
    if scene.get("assets"):
        scene_assets = scene["assets"]
    else:
        # Distribute available assets across scenes
        assets_per_scene = max(
            1, len(visual_assets) // len(scene.get("visual_requirements", [1]))
        )
        start_idx = scene_index * assets_per_scene
        end_idx = min(start_idx + assets_per_scene, len(visual_assets))
        scene_assets = visual_assets[start_idx:end_idx]

    return scene_assets


def _determine_transition_type(scene_index: int, total_scenes: int) -> str:
    """Determine appropriate transition type for scene."""
    if scene_index == 0:
        return "fade_in"
    elif scene_index == total_scenes - 1:
        return "fade_out"
    else:
        # Vary transitions for visual interest
        transitions = ["crossfade", "slide", "zoom", "fade"]
        return transitions[scene_index % len(transitions)]


def _apply_timing_adjustments(
    timeline: List[Dict[str, Any]], target_duration: float
) -> tuple[List[Dict[str, Any]], List[str]]:
    """Apply timing adjustments to match target duration."""
    adjustments = []
    current_duration = _calculate_total_duration(timeline)

    if abs(current_duration - target_duration) < 1.0:
        # Duration is close enough, no adjustments needed
        return timeline, adjustments

    # Calculate adjustment factor
    adjustment_factor = (
        target_duration / current_duration if current_duration > 0 else 1.0
    )

    adjusted_timeline = []
    current_time = 0.0

    for entry in timeline:
        # Adjust duration proportionally
        original_duration = entry["duration"]
        adjusted_duration = original_duration * adjustment_factor

        adjusted_entry = entry.copy()
        adjusted_entry.update(
            {
                "start_time": current_time,
                "end_time": current_time + adjusted_duration,
                "duration": adjusted_duration,
                "original_duration": original_duration,
            }
        )

        adjusted_timeline.append(adjusted_entry)
        current_time += adjusted_duration

        if abs(adjusted_duration - original_duration) > 0.1:
            adjustments.append(
                f"Scene {entry['scene_number']}: duration adjusted from "
                f"{original_duration:.2f}s to {adjusted_duration:.2f}s"
            )

    return adjusted_timeline, adjustments


def _calculate_total_duration(timeline: List[Dict[str, Any]]) -> float:
    """Calculate total duration of timeline."""
    if not timeline:
        return 0.0

    return max(entry.get("end_time", 0.0) for entry in timeline)


from google.adk.tools import FunctionTool

# Create the tool function for ADK
video_synchronization_tool = FunctionTool(synchronize_video_timeline)
