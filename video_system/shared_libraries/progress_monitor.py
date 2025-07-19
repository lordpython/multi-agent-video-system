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

"""Progress monitoring utilities for the Multi-Agent Video System.

This module provides progress tracking and monitoring capabilities for video
generation workflows, including stage-based progress calculation and time estimation.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import threading

from .adk_session_manager import VideoSystemSessionManager, get_session_manager
from .adk_session_models import VideoGenerationStage
from .models import VideoStatus
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StageProgress:
    """Progress information for a processing stage."""
    stage: VideoGenerationStage
    weight: float  # Relative weight of this stage (0.0 to 1.0)
    progress: float  # Progress within this stage (0.0 to 1.0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_duration: Optional[float] = None  # in seconds


class ProgressMonitor:
    """Monitors and tracks progress for video generation sessions."""
    
    # Default stage weights (sum should equal 1.0)
    DEFAULT_STAGE_WEIGHTS = {
        VideoGenerationStage.INITIALIZING: 0.05,
        VideoGenerationStage.RESEARCHING: 0.15,
        VideoGenerationStage.SCRIPTING: 0.20,
        VideoGenerationStage.ASSET_SOURCING: 0.25,
        VideoGenerationStage.AUDIO_GENERATION: 0.15,
        VideoGenerationStage.VIDEO_ASSEMBLY: 0.15,
        VideoGenerationStage.FINALIZING: 0.05
    }
    
    # Estimated durations for each stage (in seconds)
    DEFAULT_STAGE_DURATIONS = {
        VideoGenerationStage.INITIALIZING: 5,
        VideoGenerationStage.RESEARCHING: 30,
        VideoGenerationStage.SCRIPTING: 45,
        VideoGenerationStage.ASSET_SOURCING: 60,
        VideoGenerationStage.AUDIO_GENERATION: 40,
        VideoGenerationStage.VIDEO_ASSEMBLY: 90,
        VideoGenerationStage.FINALIZING: 10
    }
    
    def __init__(self, session_manager: Optional[VideoSystemSessionManager] = None):
        """Initialize progress monitor.
        
        Args:
            session_manager: Session manager instance (uses global if None)
        """
        self.session_manager = session_manager
        self.stage_progress: Dict[str, Dict[VideoGenerationStage, StageProgress]] = {}
        self.lock = threading.RLock()
        
        logger.info("ProgressMonitor initialized")
    
    def start_session_monitoring(self, session_id: str, 
                                stage_weights: Optional[Dict[VideoGenerationStage, float]] = None,
                                stage_durations: Optional[Dict[VideoGenerationStage, float]] = None) -> bool:
        """Start monitoring progress for a session.
        
        Args:
            session_id: Session identifier
            stage_weights: Custom stage weights (uses defaults if None)
            stage_durations: Custom stage durations (uses defaults if None)
            
        Returns:
            True if monitoring started successfully
        """
        with self.lock:
            if session_id in self.stage_progress:
                logger.warning(f"Progress monitoring already active for session {session_id}")
                return False
            
            weights = stage_weights or self.DEFAULT_STAGE_WEIGHTS
            durations = stage_durations or self.DEFAULT_STAGE_DURATIONS
            
            # Validate weights sum to 1.0
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"Stage weights sum to {total_weight}, normalizing to 1.0")
                weights = {stage: weight / total_weight for stage, weight in weights.items()}
            
            # Initialize stage progress
            stage_progress = {}
            for stage in VideoGenerationStage:
                if stage in [VideoGenerationStage.COMPLETED, VideoGenerationStage.FAILED]:
                    continue
                
                stage_progress[stage] = StageProgress(
                    stage=stage,
                    weight=weights.get(stage, 0.0),
                    progress=0.0,
                    estimated_duration=durations.get(stage, 30.0)
                )
            
            self.stage_progress[session_id] = stage_progress
            
        logger.info(f"Started progress monitoring for session {session_id}")
        return True
    
    def update_stage_progress(self, session_id: str, stage: VideoGenerationStage, 
                            progress: float, details: Optional[str] = None) -> bool:
        """Update progress for a specific stage.
        
        Args:
            session_id: Session identifier
            stage: Processing stage
            progress: Progress within stage (0.0 to 1.0)
            details: Optional progress details
            
        Returns:
            True if updated successfully
        """
        with self.lock:
            if session_id not in self.stage_progress:
                logger.warning(f"No progress monitoring active for session {session_id}")
                return False
            
            stage_info = self.stage_progress[session_id].get(stage)
            if not stage_info:
                logger.warning(f"Stage {stage} not found for session {session_id}")
                return False
            
            # Update stage progress
            old_progress = stage_info.progress
            stage_info.progress = max(0.0, min(1.0, progress))
            
            # Set start time if this is the first progress update
            if old_progress == 0.0 and progress > 0.0:
                stage_info.start_time = datetime.utcnow()
            
            # Set end time if stage is complete
            if progress >= 1.0 and stage_info.end_time is None:
                stage_info.end_time = datetime.utcnow()
            
            # Calculate overall session progress
            overall_progress = self._calculate_overall_progress(session_id)
            
            # Update session manager (commented out for now - async conversion needed)
            # if self.session_manager:
            #     await self.session_manager.update_stage_and_progress(
            #         session_id=session_id,
            #         stage=stage,
            #         progress=overall_progress
            #     )
            
        logger.debug(f"Updated stage progress for session {session_id}: {stage}={progress:.2f}")
        return True
    
    def advance_to_stage(self, session_id: str, stage: VideoGenerationStage) -> bool:
        """Advance session to a new processing stage.
        
        Args:
            session_id: Session identifier
            stage: New processing stage
            
        Returns:
            True if advanced successfully
        """
        with self.lock:
            if session_id not in self.stage_progress:
                logger.warning(f"No progress monitoring active for session {session_id}")
                return False
            
            # Mark previous stages as complete
            stage_order = list(VideoGenerationStage)
            current_stage_index = stage_order.index(stage)
            
            for i, prev_stage in enumerate(stage_order[:current_stage_index]):
                if prev_stage in self.stage_progress[session_id]:
                    prev_stage_info = self.stage_progress[session_id][prev_stage]
                    if prev_stage_info.progress < 1.0:
                        prev_stage_info.progress = 1.0
                        if prev_stage_info.end_time is None:
                            prev_stage_info.end_time = datetime.utcnow()
            
            # Start the new stage
            if stage in self.stage_progress[session_id]:
                stage_info = self.stage_progress[session_id][stage]
                if stage_info.start_time is None:
                    stage_info.start_time = datetime.utcnow()
            
            # Calculate estimated completion time
            estimated_completion = self._calculate_estimated_completion(session_id)
            
            # Update session manager (commented out for now - async conversion needed)
            overall_progress = self._calculate_overall_progress(session_id)
            # if self.session_manager:
            #     await self.session_manager.update_stage_and_progress(
            #         session_id=session_id,
            #         stage=stage,
            #         progress=overall_progress,
            #         estimated_completion=estimated_completion
            #     )
            
        logger.info(f"Advanced session {session_id} to stage {stage}")
        return True
    
    def complete_session(self, session_id: str, success: bool = True, 
                        error_message: Optional[str] = None) -> bool:
        """Mark session as completed or failed.
        
        Args:
            session_id: Session identifier
            success: Whether session completed successfully
            error_message: Error message if failed
            
        Returns:
            True if completed successfully
        """
        with self.lock:
            if session_id not in self.stage_progress:
                logger.warning(f"No progress monitoring active for session {session_id}")
                return False
            
            # Mark all stages as complete if successful
            if success:
                for stage_info in self.stage_progress[session_id].values():
                    stage_info.progress = 1.0
                    if stage_info.end_time is None:
                        stage_info.end_time = datetime.utcnow()
            
            # Update session manager (commented out for now - async conversion needed)
            stage = VideoGenerationStage.COMPLETED if success else VideoGenerationStage.FAILED
            progress = 1.0 if success else self._calculate_overall_progress(session_id)
            
            # if self.session_manager:
            #     await self.session_manager.update_stage_and_progress(
            #         session_id=session_id,
            #         stage=stage,
            #         progress=progress,
            #         error_message=error_message
            #     )
            
            # Clean up monitoring data
            del self.stage_progress[session_id]
            
        logger.info(f"Completed session {session_id}: success={success}")
        return True
    
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed progress information for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Progress information dictionary or None if not found
        """
        with self.lock:
            if session_id not in self.stage_progress:
                return None
            
            overall_progress = self._calculate_overall_progress(session_id)
            estimated_completion = self._calculate_estimated_completion(session_id)
            
            # Get current stage
            current_stage = None
            for stage, stage_info in self.stage_progress[session_id].items():
                if 0 < stage_info.progress < 1.0:
                    current_stage = stage
                    break
            
            # If no active stage, find the next stage
            if current_stage is None:
                for stage, stage_info in self.stage_progress[session_id].items():
                    if stage_info.progress == 0.0:
                        current_stage = stage
                        break
            
            # Build stage details
            stage_details = {}
            for stage, stage_info in self.stage_progress[session_id].items():
                stage_details[stage.value] = {
                    "progress": stage_info.progress,
                    "weight": stage_info.weight,
                    "start_time": stage_info.start_time.isoformat() if stage_info.start_time else None,
                    "end_time": stage_info.end_time.isoformat() if stage_info.end_time else None,
                    "estimated_duration": stage_info.estimated_duration
                }
            
            return {
                "session_id": session_id,
                "overall_progress": overall_progress,
                "current_stage": current_stage.value if current_stage else None,
                "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
                "stage_details": stage_details
            }
    
    def get_active_sessions(self) -> List[str]:
        """Get list of sessions currently being monitored.
        
        Returns:
            List of session IDs
        """
        with self.lock:
            return list(self.stage_progress.keys())
    
    def stop_session_monitoring(self, session_id: str) -> bool:
        """Stop monitoring progress for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if stopped successfully
        """
        with self.lock:
            if session_id not in self.stage_progress:
                return False
            
            del self.stage_progress[session_id]
            
        logger.info(f"Stopped progress monitoring for session {session_id}")
        return True
    
    def _calculate_overall_progress(self, session_id: str) -> float:
        """Calculate overall progress for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Overall progress (0.0 to 1.0)
        """
        if session_id not in self.stage_progress:
            return 0.0
        
        total_progress = 0.0
        for stage_info in self.stage_progress[session_id].values():
            total_progress += stage_info.progress * stage_info.weight
        
        return min(1.0, total_progress)
    
    def _calculate_estimated_completion(self, session_id: str) -> Optional[datetime]:
        """Calculate estimated completion time for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Estimated completion time or None if cannot be calculated
        """
        if session_id not in self.stage_progress:
            return None
        
        now = datetime.utcnow()
        total_remaining_time = 0.0
        
        for stage_info in self.stage_progress[session_id].values():
            if stage_info.progress >= 1.0:
                continue  # Stage is complete
            
            remaining_progress = 1.0 - stage_info.progress
            stage_remaining_time = remaining_progress * stage_info.estimated_duration
            
            # Adjust based on actual performance if stage has started
            if stage_info.start_time and stage_info.progress > 0:
                elapsed_time = (now - stage_info.start_time).total_seconds()
                if stage_info.progress > 0:
                    estimated_total_time = elapsed_time / stage_info.progress
                    stage_remaining_time = max(0, estimated_total_time - elapsed_time)
            
            total_remaining_time += stage_remaining_time
        
        if total_remaining_time > 0:
            return now + timedelta(seconds=total_remaining_time)
        
        return None


# Global progress monitor instance
_progress_monitor: Optional[ProgressMonitor] = None


def get_progress_monitor() -> ProgressMonitor:
    """Get the global progress monitor instance."""
    global _progress_monitor
    if _progress_monitor is None:
        _progress_monitor = ProgressMonitor()
    return _progress_monitor


def initialize_progress_monitor(session_manager: Optional[VideoSystemSessionManager] = None) -> ProgressMonitor:
    """Initialize the global progress monitor."""
    global _progress_monitor
    _progress_monitor = ProgressMonitor(session_manager)
    return _progress_monitor


# Convenience functions for common operations

def start_monitoring(session_id: str, **kwargs) -> bool:
    """Start monitoring progress for a session."""
    return get_progress_monitor().start_session_monitoring(session_id, **kwargs)


def update_progress(session_id: str, stage: VideoGenerationStage, progress: float, details: Optional[str] = None) -> bool:
    """Update progress for a session stage."""
    return get_progress_monitor().update_stage_progress(session_id, stage, progress, details)


def advance_stage(session_id: str, stage: VideoGenerationStage) -> bool:
    """Advance session to a new stage."""
    return get_progress_monitor().advance_to_stage(session_id, stage)


def complete_monitoring(session_id: str, success: bool = True, error_message: Optional[str] = None) -> bool:
    """Complete monitoring for a session."""
    return get_progress_monitor().complete_session(session_id, success, error_message)


def get_progress(session_id: str) -> Optional[Dict[str, Any]]:
    """Get progress information for a session."""
    return get_progress_monitor().get_session_progress(session_id)