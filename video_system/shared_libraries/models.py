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

"""Core data models for the Multi-Agent Video System.

This module defines the Pydantic models used throughout the video generation
pipeline for data validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum
import re
from datetime import datetime
import uuid


class VideoStatus(str, Enum):
    """Enumeration for video generation status."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    """Enumeration for asset types."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class VideoQuality(str, Enum):
    """Enumeration for video quality settings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class VideoStyle(str, Enum):
    """Enumeration for video styles."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    DOCUMENTARY = "documentary"


class VideoGenerationRequest(BaseModel):
    """Request model for video generation."""
    prompt: str = Field(..., description="Text prompt for video generation", min_length=10, max_length=2000)
    duration_preference: Optional[int] = Field(60, description="Preferred video duration in seconds", ge=10, le=600)
    style: Optional[VideoStyle] = Field(VideoStyle.PROFESSIONAL, description="Video style preference")
    voice_preference: Optional[str] = Field("neutral", description="Voice preference for narration")
    quality: Optional[VideoQuality] = Field(VideoQuality.HIGH, description="Video quality setting")
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError('Prompt cannot be empty or whitespace only')
        return v.strip()


class VideoScene(BaseModel):
    """Model representing a single scene in the video."""
    scene_number: int = Field(..., description="Sequential scene number", ge=1)
    description: str = Field(..., description="Scene description", min_length=10, max_length=500)
    visual_requirements: List[str] = Field(..., description="List of visual requirements for the scene")
    dialogue: str = Field(..., description="Dialogue or narration text for the scene", min_length=1)
    duration: float = Field(..., description="Scene duration in seconds", gt=0, le=120)
    assets: Optional[List[str]] = Field(default=[], description="List of asset IDs for the scene")
    
    @field_validator('visual_requirements')
    @classmethod
    def validate_visual_requirements(cls, v):
        if not v:
            raise ValueError('At least one visual requirement must be specified')
        return [req.strip() for req in v if req.strip()]


class VideoScript(BaseModel):
    """Model representing the complete video script."""
    title: str = Field(..., description="Video title", min_length=1, max_length=200)
    total_duration: float = Field(..., description="Total video duration in seconds", gt=0, le=600)
    scenes: List[VideoScene] = Field(..., description="List of video scenes", min_length=1)
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    
    @field_validator('scenes')
    @classmethod
    def validate_scenes_sequence(cls, v):
        if not v:
            raise ValueError('At least one scene is required')
        
        # Check scene numbers are sequential
        expected_numbers = list(range(1, len(v) + 1))
        actual_numbers = [scene.scene_number for scene in v]
        if actual_numbers != expected_numbers:
            raise ValueError('Scene numbers must be sequential starting from 1')
        
        return v
    
    @model_validator(mode='after')
    def validate_total_duration(self):
        if self.scenes:
            scene_duration_sum = sum(scene.duration for scene in self.scenes)
            if abs(self.total_duration - scene_duration_sum) > 1.0:  # Allow 1 second tolerance
                raise ValueError('Total duration must match sum of scene durations')
        return self


class AssetItem(BaseModel):
    """Model representing a media asset."""
    asset_id: str = Field(..., description="Unique asset identifier")
    asset_type: str = Field(..., description="Asset type: 'image', 'video', 'audio'")
    source_url: str = Field(..., description="Original source URL")
    local_path: Optional[str] = Field(None, description="Local file path after download")
    usage_rights: str = Field(..., description="Usage rights information")
    metadata: Dict[str, Any] = Field(default={}, description="Additional asset metadata")


class VideoGenerationStatus(BaseModel):
    """Model representing the status of video generation."""
    session_id: str = Field(..., description="Unique session identifier")
    status: str = Field(..., description="Current status: 'processing', 'completed', 'failed'")
    progress: float = Field(..., description="Progress percentage (0.0 to 1.0)")
    current_stage: str = Field(..., description="Current processing stage")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ResearchRequest(BaseModel):
    """Request model for research agent."""
    topic: str = Field(..., description="Research topic")
    scope: Optional[str] = Field("general", description="Research scope")
    depth_requirements: Optional[str] = Field("standard", description="Depth of research required")


class ResearchData(BaseModel):
    """Response model from research agent."""
    facts: List[str] = Field(..., description="List of researched facts")
    sources: List[str] = Field(..., description="List of source URLs")
    key_points: List[str] = Field(..., description="Key points extracted")
    context: Dict[str, Any] = Field(default={}, description="Additional context information")


class ScriptRequest(BaseModel):
    """Request model for story agent."""
    research_data: ResearchData = Field(..., description="Research data to base script on")
    style_preferences: Optional[Dict[str, Any]] = Field(default={}, description="Style preferences")
    duration: Optional[int] = Field(60, description="Target duration in seconds")


class AssetRequest(BaseModel):
    """Request model for asset sourcing agent."""
    scene_descriptions: List[str] = Field(..., description="List of scene descriptions")
    style_requirements: Optional[Dict[str, Any]] = Field(default={}, description="Style requirements")
    specifications: Optional[Dict[str, Any]] = Field(default={}, description="Technical specifications")


class AssetCollection(BaseModel):
    """Response model from asset sourcing agent."""
    images: List[AssetItem] = Field(default=[], description="List of image assets")
    videos: List[AssetItem] = Field(default=[], description="List of video assets")
    metadata: Dict[str, Any] = Field(default={}, description="Collection metadata")


class AudioRequest(BaseModel):
    """Request model for audio agent."""
    script_text: str = Field(..., description="Text to convert to speech")
    voice_preferences: Optional[Dict[str, Any]] = Field(default={}, description="Voice preferences")
    timing_requirements: Optional[Dict[str, Any]] = Field(default={}, description="Timing requirements")


class AudioAssets(BaseModel):
    """Response model from audio agent."""
    voice_files: List[str] = Field(..., description="List of generated voice file paths")
    timing_data: Dict[str, Any] = Field(default={}, description="Timing synchronization data")
    synchronization_markers: List[Dict[str, Any]] = Field(default=[], description="Sync markers")


class AssemblyRequest(BaseModel):
    """Request model for video assembly agent."""
    assets: AssetCollection = Field(..., description="Collection of visual assets")
    audio: AudioAssets = Field(..., description="Audio assets")
    script: VideoScript = Field(..., description="Video script")
    specifications: Optional[Dict[str, Any]] = Field(default={}, description="Assembly specifications")


class FinalVideo(BaseModel):
    """Response model for final video."""
    video_file: str = Field(..., description="Path to final video file")
    metadata: Dict[str, Any] = Field(default={}, description="Video metadata")
    quality_metrics: Optional[Dict[str, Any]] = Field(default={}, description="Quality metrics")


# Validation utilities and helper functions

def validate_video_duration(duration: float) -> bool:
    """Validate video duration is within acceptable range."""
    return 10 <= duration <= 600


def validate_scene_duration(duration: float) -> bool:
    """Validate scene duration is within acceptable range."""
    return 0 < duration <= 120


def validate_prompt_length(prompt: str) -> bool:
    """Validate prompt length is within acceptable range."""
    return 10 <= len(prompt.strip()) <= 2000


def generate_session_id() -> str:
    """Generate a unique session ID for video generation."""
    return str(uuid.uuid4())


def calculate_total_duration(scenes: List[VideoScene]) -> float:
    """Calculate total duration from a list of scenes."""
    return sum(scene.duration for scene in scenes)


def validate_asset_url(url: str) -> bool:
    """Validate asset URL format."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$',  # path
        re.IGNORECASE
    )
    return url_pattern.match(url) is not None

def create_default_video_request(prompt: str) -> VideoGenerationRequest:
    """Create a video generation request with default values."""
    return VideoGenerationRequest(
        prompt=prompt,
        duration_preference=60,
        style=VideoStyle.PROFESSIONAL,
        voice_preference="neutral",
        quality=VideoQuality.HIGH
    )


def create_video_status(session_id: str, status: str = "queued") -> VideoGenerationStatus:
    """Create a video generation status with default values."""
    return VideoGenerationStatus(
        session_id=session_id,
        status=status,
        progress=0.0,
        current_stage="Initializing",
        estimated_completion=None,
        error_message=None
    )


def validate_scene_sequence(scenes: List[VideoScene]) -> bool:
    """Validate that scene numbers are sequential starting from 1."""
    if not scenes:
        return False
    
    expected_numbers = list(range(1, len(scenes) + 1))
    actual_numbers = [scene.scene_number for scene in scenes]
    return actual_numbers == expected_numbers


def get_asset_by_type(assets: List[AssetItem], asset_type: str) -> List[AssetItem]:
    """Filter assets by type."""
    return [asset for asset in assets if asset.asset_type == asset_type]


def validate_video_script_consistency(script: VideoScript) -> List[str]:
    """Validate video script consistency and return list of issues."""
    issues = []
    
    # Check if total duration matches scene durations
    scene_duration_sum = sum(scene.duration for scene in script.scenes)
    if abs(script.total_duration - scene_duration_sum) > 1.0:
        issues.append(f"Total duration ({script.total_duration}s) doesn't match sum of scene durations ({scene_duration_sum}s)")
    
    # Check scene sequence
    if not validate_scene_sequence(script.scenes):
        issues.append("Scene numbers are not sequential starting from 1")
    
    # Check for empty dialogue
    for i, scene in enumerate(script.scenes, 1):
        if not scene.dialogue.strip():
            issues.append(f"Scene {i} has empty dialogue")
    
    # Check for missing visual requirements
    for i, scene in enumerate(script.scenes, 1):
        if not scene.visual_requirements:
            issues.append(f"Scene {i} has no visual requirements")
    
    return issues