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

"""ADK Session models for the Multi-Agent Video System.

This module defines the session state models used with ADK SessionService
for managing video generation context and state.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .models import (
    VideoGenerationRequest, VideoScript, AssetCollection, 
    AudioAssets, FinalVideo, ResearchData
)


class VideoGenerationStage(str, Enum):
    """Enumeration for video generation stages."""
    INITIALIZING = "initializing"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    ASSET_SOURCING = "asset_sourcing"
    AUDIO_GENERATION = "audio_generation"
    VIDEO_ASSEMBLY = "video_assembly"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoGenerationState(BaseModel):
    """Session state model for video generation process.
    
    This model represents the complete state of a video generation session
    that can be persisted and retrieved using ADK SessionService.
    """
    
    # Core session information
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Video generation request and configuration
    request: VideoGenerationRequest = Field(..., description="Original video generation request")
    
    # Processing state
    current_stage: VideoGenerationStage = Field(
        VideoGenerationStage.INITIALIZING, 
        description="Current processing stage"
    )
    progress: float = Field(0.0, description="Progress percentage (0.0 to 1.0)", ge=0.0, le=1.0)
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Generated content at each stage
    research_data: Optional[ResearchData] = Field(None, description="Research results")
    script: Optional[VideoScript] = Field(None, description="Generated video script")
    assets: Optional[AssetCollection] = Field(None, description="Sourced visual assets")
    audio_assets: Optional[AudioAssets] = Field(None, description="Generated audio assets")
    final_video: Optional[FinalVideo] = Field(None, description="Final assembled video")
    
    # Error handling and retry tracking
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    retry_count: Dict[str, int] = Field(default_factory=dict, description="Retry count per stage")
    error_log: List[str] = Field(default_factory=list, description="History of errors encountered")
    
    # File management
    intermediate_files: List[str] = Field(
        default_factory=list, 
        description="List of intermediate files for cleanup"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    
    def update_stage(self, stage: VideoGenerationStage, progress: Optional[float] = None) -> None:
        """Update the current stage and optionally progress."""
        self.current_stage = stage
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error_message: str, stage: Optional[str] = None) -> None:
        """Add an error to the error log."""
        self.error_log.append(f"[{datetime.utcnow().isoformat()}] {error_message}")
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
        
        if stage:
            if stage not in self.retry_count:
                self.retry_count[stage] = 0
            self.retry_count[stage] += 1
    
    def add_intermediate_file(self, file_path: str) -> None:
        """Add an intermediate file path for cleanup."""
        if file_path not in self.intermediate_files:
            self.intermediate_files.append(file_path)
            self.updated_at = datetime.utcnow()
    
    def is_completed(self) -> bool:
        """Check if video generation is completed."""
        return self.current_stage == VideoGenerationStage.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if video generation has failed."""
        return self.current_stage == VideoGenerationStage.FAILED
    
    def get_stage_progress_mapping(self) -> Dict[VideoGenerationStage, float]:
        """Get the progress mapping for each stage."""
        return {
            VideoGenerationStage.INITIALIZING: 0.0,
            VideoGenerationStage.RESEARCHING: 0.1,
            VideoGenerationStage.SCRIPTING: 0.3,
            VideoGenerationStage.ASSET_SOURCING: 0.5,
            VideoGenerationStage.AUDIO_GENERATION: 0.7,
            VideoGenerationStage.VIDEO_ASSEMBLY: 0.9,
            VideoGenerationStage.FINALIZING: 0.95,
            VideoGenerationStage.COMPLETED: 1.0,
            VideoGenerationStage.FAILED: 0.0
        }
    
    def update_progress_for_stage(self) -> None:
        """Update progress based on current stage."""
        stage_progress = self.get_stage_progress_mapping()
        self.progress = stage_progress.get(self.current_stage, self.progress)
        self.updated_at = datetime.utcnow()


class SessionMetadata(BaseModel):
    """Metadata for session management."""
    
    total_sessions: int = Field(0, description="Total number of sessions")
    active_sessions: int = Field(0, description="Number of active sessions")
    completed_sessions: int = Field(0, description="Number of completed sessions")
    failed_sessions: int = Field(0, description="Number of failed sessions")
    average_completion_time: Optional[float] = Field(None, description="Average completion time in seconds")
    
    def update_counts(self, sessions: List[VideoGenerationState]) -> None:
        """Update counts based on current sessions."""
        self.total_sessions = len(sessions)
        self.active_sessions = len([s for s in sessions if not s.is_completed() and not s.is_failed()])
        self.completed_sessions = len([s for s in sessions if s.is_completed()])
        self.failed_sessions = len([s for s in sessions if s.is_failed()])
        
        # Calculate average completion time for completed sessions
        completed = [s for s in sessions if s.is_completed() and s.created_at and s.updated_at]
        if completed:
            completion_times = [(s.updated_at - s.created_at).total_seconds() for s in completed]
            self.average_completion_time = sum(completion_times) / len(completion_times)