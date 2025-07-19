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

"""Session management utilities for the Multi-Agent Video System.

This module provides session management capabilities including project state tracking,
persistence, progress monitoring, and cleanup functionality.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
from enum import Enum

from .models import (
    VideoGenerationRequest, VideoGenerationStatus, VideoScript, 
    AssetCollection, AudioAssets, FinalVideo, VideoStatus
)
from .error_handling import VideoSystemError, log_error
from .logging_config import get_logger

logger = get_logger(__name__)


class SessionStage(str, Enum):
    """Enumeration for session processing stages."""
    INITIALIZING = "initializing"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    ASSET_SOURCING = "asset_sourcing"
    AUDIO_GENERATION = "audio_generation"
    VIDEO_ASSEMBLY = "video_assembly"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SessionData:
    """Data class for session information."""
    session_id: str
    user_id: Optional[str]
    request: VideoGenerationRequest
    status: VideoStatus
    stage: SessionStage
    progress: float
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProjectState:
    """Data class for project state information."""
    session_id: str
    research_data: Optional[Dict[str, Any]] = None
    script: Optional[VideoScript] = None
    assets: Optional[AssetCollection] = None
    audio: Optional[AudioAssets] = None
    final_video: Optional[FinalVideo] = None
    intermediate_files: List[str] = None
    
    def __post_init__(self):
        if self.intermediate_files is None:
            self.intermediate_files = []


class SessionManager:
    """Manages video generation sessions with persistence and state tracking."""
    
    def __init__(self, storage_path: Optional[str] = None, cleanup_interval: int = 3600):
        """Initialize session manager.
        
        Args:
            storage_path: Path for session storage (defaults to ./sessions)
            cleanup_interval: Cleanup interval in seconds (default: 1 hour)
        """
        self.storage_path = Path(storage_path or "./sessions")
        self.storage_path.mkdir(exist_ok=True)
        
        self.sessions: Dict[str, SessionData] = {}
        self.project_states: Dict[str, ProjectState] = {}
        self.cleanup_interval = cleanup_interval
        self.lock = threading.RLock()
        
        # Load existing sessions
        self._load_sessions()
        
        # Start cleanup task
        self._start_cleanup_task()
        
        logger.info(f"SessionManager initialized with storage path: {self.storage_path}")
    
    def create_session(self, request: VideoGenerationRequest, user_id: Optional[str] = None) -> str:
        """Create a new video generation session.
        
        Args:
            request: Video generation request
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        with self.lock:
            session_data = SessionData(
                session_id=session_id,
                user_id=user_id,
                request=request,
                status=VideoStatus.QUEUED,
                stage=SessionStage.INITIALIZING,
                progress=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            project_state = ProjectState(session_id=session_id)
            
            self.sessions[session_id] = session_data
            self.project_states[session_id] = project_state
            
            # Persist to storage
            self._save_session(session_id)
            
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        with self.lock:
            return self.sessions.get(session_id)
    
    def get_project_state(self, session_id: str) -> Optional[ProjectState]:
        """Get project state by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Project state or None if not found
        """
        with self.lock:
            return self.project_states.get(session_id)
    
    def update_session_status(self, session_id: str, status: VideoStatus, 
                            stage: Optional[SessionStage] = None,
                            progress: Optional[float] = None,
                            error_message: Optional[str] = None,
                            estimated_completion: Optional[datetime] = None) -> bool:
        """Update session status and progress.
        
        Args:
            session_id: Session identifier
            status: New status
            stage: New processing stage
            progress: Progress percentage (0.0 to 1.0)
            error_message: Error message if failed
            estimated_completion: Estimated completion time
            
        Returns:
            True if updated successfully, False if session not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for status update")
                return False
            
            session.status = status
            if stage is not None:
                session.stage = stage
            if progress is not None:
                session.progress = max(0.0, min(1.0, progress))
            if error_message is not None:
                session.error_message = error_message
            if estimated_completion is not None:
                session.estimated_completion = estimated_completion
            
            session.updated_at = datetime.utcnow()
            
            # Persist changes
            self._save_session(session_id)
            
        logger.info(f"Updated session {session_id}: status={status}, stage={stage}, progress={progress}")
        return True
    
    def update_project_state(self, session_id: str, **kwargs) -> bool:
        """Update project state with new data.
        
        Args:
            session_id: Session identifier
            **kwargs: State data to update (research_data, script, assets, etc.)
            
        Returns:
            True if updated successfully, False if session not found
        """
        with self.lock:
            project_state = self.project_states.get(session_id)
            if not project_state:
                logger.warning(f"Project state for session {session_id} not found")
                return False
            
            # Update provided fields
            for key, value in kwargs.items():
                if hasattr(project_state, key):
                    setattr(project_state, key, value)
                    logger.debug(f"Updated project state {session_id}: {key}")
            
            # Persist changes
            self._save_session(session_id)
            
        return True
    
    def add_intermediate_file(self, session_id: str, file_path: str) -> bool:
        """Add intermediate file to project state for cleanup.
        
        Args:
            session_id: Session identifier
            file_path: Path to intermediate file
            
        Returns:
            True if added successfully, False if session not found
        """
        with self.lock:
            project_state = self.project_states.get(session_id)
            if not project_state:
                return False
            
            if file_path not in project_state.intermediate_files:
                project_state.intermediate_files.append(file_path)
                self._save_session(session_id)
                logger.debug(f"Added intermediate file {file_path} to session {session_id}")
            
        return True
    
    def get_session_status(self, session_id: str) -> Optional[VideoGenerationStatus]:
        """Get session status for API responses.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Video generation status or None if not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            
            return VideoGenerationStatus(
                session_id=session_id,
                status=session.status.value,
                progress=session.progress,
                current_stage=session.stage.value,
                estimated_completion=session.estimated_completion.isoformat() if session.estimated_completion else None,
                error_message=session.error_message
            )
    
    def list_sessions(self, user_id: Optional[str] = None, 
                     status: Optional[VideoStatus] = None,
                     limit: Optional[int] = None) -> List[SessionData]:
        """List sessions with optional filtering.
        
        Args:
            user_id: Filter by user ID
            status: Filter by status
            limit: Maximum number of sessions to return
            
        Returns:
            List of session data
        """
        with self.lock:
            sessions = list(self.sessions.values())
            
            # Apply filters
            if user_id:
                sessions = [s for s in sessions if s.user_id == user_id]
            if status:
                sessions = [s for s in sessions if s.status == status]
            
            # Sort by creation time (newest first)
            sessions.sort(key=lambda s: s.created_at, reverse=True)
            
            # Apply limit
            if limit:
                sessions = sessions[:limit]
            
        return sessions
    
    def delete_session(self, session_id: str, cleanup_files: bool = True) -> bool:
        """Delete a session and optionally clean up associated files.
        
        Args:
            session_id: Session identifier
            cleanup_files: Whether to clean up intermediate files
            
        Returns:
            True if deleted successfully, False if session not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            project_state = self.project_states.get(session_id)
            
            if not session:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
            
            # Clean up intermediate files if requested
            if cleanup_files and project_state:
                self._cleanup_session_files(project_state)
            
            # Remove from memory
            del self.sessions[session_id]
            if project_state:
                del self.project_states[session_id]
            
            # Remove from storage
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
        logger.info(f"Deleted session {session_id}")
        return True
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        with self.lock:
            for session_id, session in self.sessions.items():
                if (session.status in [VideoStatus.COMPLETED, VideoStatus.FAILED, VideoStatus.CANCELLED] and
                    session.updated_at < cutoff_time):
                    expired_sessions.append(session_id)
        
        # Delete expired sessions
        for session_id in expired_sessions:
            self.delete_session(session_id, cleanup_files=True)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        with self.lock:
            total_sessions = len(self.sessions)
            status_counts = {}
            stage_counts = {}
            
            for session in self.sessions.values():
                status_counts[session.status.value] = status_counts.get(session.status.value, 0) + 1
                stage_counts[session.stage.value] = stage_counts.get(session.stage.value, 0) + 1
            
            # Calculate average progress for active sessions
            active_sessions = [s for s in self.sessions.values() 
                             if s.status == VideoStatus.PROCESSING]
            avg_progress = (sum(s.progress for s in active_sessions) / len(active_sessions) 
                          if active_sessions else 0.0)
            
        return {
            "total_sessions": total_sessions,
            "active_sessions": len(active_sessions),
            "status_distribution": status_counts,
            "stage_distribution": stage_counts,
            "average_progress": avg_progress,
            "storage_path": str(self.storage_path)
        }
    
    def _save_session(self, session_id: str):
        """Save session data to persistent storage."""
        try:
            session = self.sessions.get(session_id)
            project_state = self.project_states.get(session_id)
            
            if not session:
                return
            
            # Prepare data for serialization
            session_dict = asdict(session)
            # Convert datetime objects to ISO format
            session_dict['created_at'] = session.created_at.isoformat()
            session_dict['updated_at'] = session.updated_at.isoformat()
            if session.estimated_completion:
                session_dict['estimated_completion'] = session.estimated_completion.isoformat()
            
            # Convert request to dict
            session_dict['request'] = session.request.model_dump()
            
            # Prepare project state
            project_dict = {}
            if project_state:
                project_dict = asdict(project_state)
                # Convert Pydantic models to dicts
                if project_state.script:
                    project_dict['script'] = project_state.script.model_dump()
                if project_state.assets:
                    project_dict['assets'] = project_state.assets.model_dump()
                if project_state.audio:
                    project_dict['audio'] = project_state.audio.model_dump()
                if project_state.final_video:
                    project_dict['final_video'] = project_state.final_video.model_dump()
            
            # Combine session and project data
            data = {
                "session": session_dict,
                "project_state": project_dict
            }
            
            # Save to file
            session_file = self.storage_path / f"{session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
    
    def _load_sessions(self):
        """Load sessions from persistent storage."""
        try:
            for session_file in self.storage_path.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    session_dict = data.get("session", {})
                    project_dict = data.get("project_state", {})
                    
                    # Reconstruct session data
                    session_id = session_dict.get("session_id")
                    if not session_id:
                        continue
                    
                    # Convert datetime strings back to datetime objects
                    session_dict['created_at'] = datetime.fromisoformat(session_dict['created_at'])
                    session_dict['updated_at'] = datetime.fromisoformat(session_dict['updated_at'])
                    if session_dict.get('estimated_completion'):
                        session_dict['estimated_completion'] = datetime.fromisoformat(session_dict['estimated_completion'])
                    
                    # Convert string enums back to enum objects
                    if 'status' in session_dict and isinstance(session_dict['status'], str):
                        session_dict['status'] = VideoStatus(session_dict['status'])
                    if 'stage' in session_dict and isinstance(session_dict['stage'], str):
                        session_dict['stage'] = SessionStage(session_dict['stage'])
                    
                    # Reconstruct request object
                    request_dict = session_dict.pop('request')
                    session_dict['request'] = VideoGenerationRequest(**request_dict)
                    
                    # Create session data
                    session_data = SessionData(**session_dict)
                    self.sessions[session_id] = session_data
                    
                    # Reconstruct project state
                    if project_dict:
                        # Reconstruct Pydantic models
                        if project_dict.get('script'):
                            project_dict['script'] = VideoScript(**project_dict['script'])
                        if project_dict.get('assets'):
                            project_dict['assets'] = AssetCollection(**project_dict['assets'])
                        if project_dict.get('audio'):
                            project_dict['audio'] = AudioAssets(**project_dict['audio'])
                        if project_dict.get('final_video'):
                            project_dict['final_video'] = FinalVideo(**project_dict['final_video'])
                        
                        project_state = ProjectState(**project_dict)
                        self.project_states[session_id] = project_state
                    else:
                        self.project_states[session_id] = ProjectState(session_id=session_id)
                    
                except Exception as e:
                    logger.error(f"Failed to load session from {session_file}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.sessions)} sessions from storage")
            
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
    
    def _cleanup_session_files(self, project_state: ProjectState):
        """Clean up intermediate files for a session."""
        for file_path in project_state.intermediate_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        def cleanup_loop():
            while True:
                try:
                    self.cleanup_expired_sessions()
                    time.sleep(self.cleanup_interval)
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        logger.info("Started session cleanup task")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def initialize_session_manager(storage_path: Optional[str] = None, 
                             cleanup_interval: int = 3600) -> SessionManager:
    """Initialize the global session manager."""
    global _session_manager
    _session_manager = SessionManager(storage_path, cleanup_interval)
    return _session_manager