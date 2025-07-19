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

"""ADK SessionService wrapper for the Multi-Agent Video System.

This module provides a high-level wrapper around ADK's SessionService
for managing video generation sessions with proper state management.
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

from google.adk.sessions import BaseSessionService, InMemorySessionService, VertexAiSessionService
from google.adk.sessions.session import Session
from google.adk.events import Event, EventActions

from .adk_session_models import VideoGenerationState, VideoGenerationStage, SessionMetadata
from .models import VideoGenerationRequest, VideoGenerationStatus
from .error_handling import VideoSystemError, log_error
from .logging_config import get_logger

logger = get_logger(__name__)


class VideoSystemSessionManager:
    """High-level session manager for video generation using ADK SessionService.
    
    This class wraps ADK's SessionService to provide video-specific session
    management with proper state handling and persistence.
    """
    
    def __init__(
        self, 
        session_service: Optional[BaseSessionService] = None,
        cleanup_interval: int = 3600,
        max_session_age_hours: int = 24
    ):
        """Initialize the video system session manager.
        
        Args:
            session_service: ADK BaseSessionService instance (auto-configured if None)
            cleanup_interval: Cleanup interval in seconds (default: 1 hour)
            max_session_age_hours: Maximum session age before cleanup (default: 24 hours)
        """
        self.session_service = session_service or self._create_session_service()
        self.cleanup_interval = cleanup_interval
        self.max_session_age_hours = max_session_age_hours
        
        # Track session to user mapping for ADK SessionService calls
        self.session_user_mapping: Dict[str, str] = {}
        
        # Session tracking for listing functionality
        # Format: {user_id: {session_id: session_metadata}}
        self.session_registry: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
        
        logger.info(f"VideoSystemSessionManager initialized with {type(self.session_service).__name__}")
    
    def _create_session_service(self) -> BaseSessionService:
        """Create and configure the appropriate SessionService based on environment."""
        # Check environment configuration
        use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "0") == "1"
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if use_vertex and project_id:
            logger.info("Configuring VertexAiSessionService for production")
            return VertexAiSessionService(
                project=project_id,
                location=location
            )
        else:
            logger.info("Configuring InMemorySessionService for development")
            return InMemorySessionService()
    
    async def create_session(
        self, 
        request: Union[VideoGenerationRequest, str], 
        user_id: Optional[str] = None
    ) -> str:
        """Create a new video generation session with proper ADK event tracking.
        
        Args:
            request: Video generation request or prompt string
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        try:
            # Convert string to VideoGenerationRequest if needed
            if isinstance(request, str):
                from .models import create_default_video_request
                video_request = create_default_video_request(request)
            else:
                video_request = request
            
            # Create initial state
            initial_state = VideoGenerationState(
                session_id="",  # Will be set after session creation
                user_id=user_id,
                request=video_request,
                current_stage=VideoGenerationStage.INITIALIZING,
                progress=0.0
            )
            
            # Create ADK session with initial state
            session = await self.session_service.create_session(
                app_name="video-generation-system",
                user_id=user_id or "anonymous",
                state=initial_state.model_dump()
            )
            
            # Track session to user mapping
            user_key = user_id or "anonymous"
            self.session_user_mapping[session.id] = user_key
            
            # Register session for listing functionality
            if user_key not in self.session_registry:
                self.session_registry[user_key] = {}
            
            self.session_registry[user_key][session.id] = {
                "session_id": session.id,
                "user_id": user_key,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "current_stage": VideoGenerationStage.INITIALIZING.value,
                "progress": 0.0,
                "prompt": video_request.prompt[:100] + ("..." if len(video_request.prompt) > 100 else ""),
                "status": "queued"
            }
            
            # Update state with actual session ID using proper event-based approach
            state_delta = {
                "session_id": session.id,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Create initialization event
            init_event = Event(
                author="video_system",
                actions=EventActions(state_delta=state_delta),
                timestamp=time.time()
            )
            
            # Append event to properly update session state
            await self.session_service.append_event(session, init_event)
            
            logger.info(f"Created video generation session {session.id} for user {user_id} with proper event tracking")
            return session.id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise VideoSystemError(f"Session creation failed: {e}")
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get ADK session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ADK Session object or None if not found
        """
        try:
            user_id = self.session_user_mapping.get(session_id, "anonymous")
            return await self.session_service.get_session(
                app_name="video-generation-system",
                user_id=user_id,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def get_session_state(self, session_id: str) -> Optional[VideoGenerationState]:
        """Get video generation state for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            VideoGenerationState or None if not found
        """
        try:
            session = await self.get_session(session_id)
            if not session or not session.state:
                return None
            
            # Convert session state dict back to VideoGenerationState
            return VideoGenerationState(**session.state)
            
        except Exception as e:
            logger.error(f"Failed to get session state {session_id}: {e}")
            return None
    
    async def update_session_state(
        self, 
        session_id: str, 
        **updates
    ) -> bool:
        """Update session state using ADK's append_event with EventActions.state_delta.
        
        Args:
            session_id: Session identifier
            **updates: State fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for state update")
                return False
            
            # Prepare state delta for updates
            state_delta = {}
            for key, value in updates.items():
                # Convert Pydantic models to dict for serialization
                if hasattr(value, 'model_dump'):
                    state_delta[key] = value.model_dump()
                elif hasattr(value, 'dict'):
                    state_delta[key] = value.dict()
                else:
                    state_delta[key] = value
            
            # Always update timestamp
            state_delta["updated_at"] = datetime.utcnow().isoformat()
            
            # Create event with state updates
            event = Event(
                author="system",
                actions=EventActions(state_delta=state_delta),
                timestamp=time.time()
            )
            
            # Append event to update session state through ADK's proper mechanism
            await self.session_service.append_event(session, event)
            
            # Update session registry for listing functionality
            await self._update_session_registry(session_id, updates)
            
            logger.debug(f"Updated session state {session_id} via append_event: {list(updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session state {session_id}: {e}")
            return False
    
    async def update_stage_and_progress(
        self, 
        session_id: str, 
        stage: VideoGenerationStage,
        progress: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update session stage and progress using ADK event-based state updates.
        
        Args:
            session_id: Session identifier
            stage: New processing stage
            progress: Progress percentage (0.0 to 1.0)
            error_message: Error message if failed
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for stage update")
                return False
            
            # Prepare state delta
            state_delta = {
                "current_stage": stage.value,  # Convert enum to string for serialization
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if progress is not None:
                state_delta["progress"] = max(0.0, min(1.0, progress))
            
            if error_message is not None:
                state_delta["error_message"] = error_message
                if stage == VideoGenerationStage.FAILED:
                    # Get current state to update error log
                    current_state = await self.get_session_state(session_id)
                    if current_state:
                        current_state.add_error(error_message)
                        state_delta["error_log"] = current_state.error_log
            
            # Create event with proper author and timestamp
            event = Event(
                author="video_system",
                actions=EventActions(state_delta=state_delta),
                timestamp=time.time()
            )
            
            # Append event to update session state
            await self.session_service.append_event(session, event)
            
            # Update session registry for listing functionality
            registry_updates = {
                "current_stage": stage.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            if progress is not None:
                registry_updates["progress"] = max(0.0, min(1.0, progress))
            if error_message is not None:
                registry_updates["error_message"] = error_message
                registry_updates["status"] = "failed"
            elif stage == VideoGenerationStage.COMPLETED:
                registry_updates["status"] = "completed"
            elif stage != VideoGenerationStage.INITIALIZING:
                registry_updates["status"] = "processing"
            
            await self._update_session_registry(session_id, registry_updates)
            
            logger.info(f"Updated session {session_id} stage to {stage.value} via append_event")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session stage {session_id}: {e}")
            return False
    
    async def get_session_status(self, session_id: str) -> Optional[VideoGenerationStatus]:
        """Get session status for API responses.
        
        Args:
            session_id: Session identifier
            
        Returns:
            VideoGenerationStatus or None if not found
        """
        try:
            state = await self.get_session_state(session_id)
            if not state:
                return None
            
            return VideoGenerationStatus(
                session_id=session_id,
                status=self._map_stage_to_status(state.current_stage),
                progress=state.progress,
                current_stage=state.current_stage.value,
                estimated_completion=state.estimated_completion.isoformat() if state.estimated_completion else None,
                error_message=state.error_message
            )
            
        except Exception as e:
            logger.error(f"Failed to get session status {session_id}: {e}")
            return None
    
    def _map_stage_to_status(self, stage: VideoGenerationStage) -> str:
        """Map video generation stage to status string."""
        if stage == VideoGenerationStage.COMPLETED:
            return "completed"
        elif stage == VideoGenerationStage.FAILED:
            return "failed"
        elif stage == VideoGenerationStage.INITIALIZING:
            return "queued"
        else:
            return "processing"
    
    async def list_sessions(
        self, 
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        status_filter: Optional[str] = None
    ) -> List[VideoGenerationState]:
        """List video generation sessions with optional filtering.
        
        Args:
            user_id: Filter by user ID (if None, returns sessions for all users)
            limit: Maximum number of sessions to return
            status_filter: Filter by status (completed, failed, processing, queued)
            
        Returns:
            List of VideoGenerationState objects
        """
        try:
            sessions = []
            
            # Determine which users to query
            users_to_query = [user_id] if user_id else list(self.session_registry.keys())
            
            # Collect session metadata from registry
            session_metadata_list = []
            for user_key in users_to_query:
                if user_key in self.session_registry:
                    for session_id, metadata in self.session_registry[user_key].items():
                        # Apply status filter if provided
                        if status_filter and metadata.get("status") != status_filter:
                            continue
                        session_metadata_list.append(metadata)
            
            # Sort by creation time (newest first)
            session_metadata_list.sort(
                key=lambda x: x.get("created_at", ""), 
                reverse=True
            )
            
            # Apply limit
            if limit:
                session_metadata_list = session_metadata_list[:limit]
            
            # Convert to VideoGenerationState objects by fetching full session data
            for metadata in session_metadata_list:
                try:
                    session_id = metadata["session_id"]
                    state = await self.get_session_state(session_id)
                    if state:
                        sessions.append(state)
                    else:
                        # Session might have been deleted, remove from registry
                        await self._remove_from_registry(session_id)
                except Exception as e:
                    logger.warning(f"Failed to get session state for {metadata['session_id']}: {e}")
                    # Remove invalid session from registry
                    await self._remove_from_registry(metadata["session_id"])
            
            logger.info(f"Listed {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str, cleanup_files: bool = True) -> bool:
        """Delete a session and optionally clean up associated files.
        
        Args:
            session_id: Session identifier
            cleanup_files: Whether to clean up intermediate files
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Get session state for file cleanup
            if cleanup_files:
                state = await self.get_session_state(session_id)
                if state and state.intermediate_files:
                    await self._cleanup_session_files(state.intermediate_files)
            
            # Delete session from ADK SessionService
            user_id = self.session_user_mapping.get(session_id, "anonymous")
            await self.session_service.delete_session(
                app_name="video-generation-system",
                user_id=user_id,
                session_id=session_id
            )
            
            # Remove from mapping and registry
            if session_id in self.session_user_mapping:
                del self.session_user_mapping[session_id]
            
            await self._remove_from_registry(session_id)
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions based on age and completion status.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            cleaned_count = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=self.max_session_age_hours)
            
            # Collect sessions to clean up
            sessions_to_cleanup = []
            
            for user_id, user_sessions in self.session_registry.items():
                for session_id, metadata in user_sessions.items():
                    try:
                        created_at_str = metadata.get("created_at")
                        if not created_at_str:
                            continue
                        
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if created_at.tzinfo:
                            created_at = created_at.replace(tzinfo=None)
                        
                        # Clean up if:
                        # 1. Session is older than max age
                        # 2. Session is completed or failed and older than 1 hour
                        status = metadata.get("status", "")
                        is_old = created_at < cutoff_time
                        is_completed_old = (
                            status in ["completed", "failed"] and 
                            created_at < (datetime.utcnow() - timedelta(hours=1))
                        )
                        
                        if is_old or is_completed_old:
                            sessions_to_cleanup.append(session_id)
                            
                    except Exception as e:
                        logger.warning(f"Error checking session {session_id} for cleanup: {e}")
                        # Add problematic sessions to cleanup list
                        sessions_to_cleanup.append(session_id)
            
            # Clean up identified sessions
            for session_id in sessions_to_cleanup:
                try:
                    success = await self.delete_session(session_id, cleanup_files=True)
                    if success:
                        cleaned_count += 1
                        logger.debug(f"Cleaned up expired session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup session {session_id}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_statistics(self) -> SessionMetadata:
        """Get session statistics based on session registry.
        
        Returns:
            SessionMetadata with current statistics
        """
        try:
            # Collect all sessions from registry
            all_sessions = []
            for user_sessions in self.session_registry.values():
                for metadata in user_sessions.values():
                    all_sessions.append(metadata)
            
            # Calculate statistics
            total_sessions = len(all_sessions)
            active_sessions = len([s for s in all_sessions if s.get("status") not in ["completed", "failed"]])
            completed_sessions = len([s for s in all_sessions if s.get("status") == "completed"])
            failed_sessions = len([s for s in all_sessions if s.get("status") == "failed"])
            
            # Calculate average completion time for completed sessions
            average_completion_time = None
            completed_with_times = []
            
            for session_meta in all_sessions:
                if session_meta.get("status") == "completed":
                    try:
                        created_at = datetime.fromisoformat(session_meta.get("created_at", ""))
                        updated_at = datetime.fromisoformat(session_meta.get("updated_at", ""))
                        completion_time = (updated_at - created_at).total_seconds()
                        completed_with_times.append(completion_time)
                    except Exception:
                        continue
            
            if completed_with_times:
                average_completion_time = sum(completed_with_times) / len(completed_with_times)
            
            metadata = SessionMetadata(
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                completed_sessions=completed_sessions,
                failed_sessions=failed_sessions,
                average_completion_time=average_completion_time
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return SessionMetadata()
    
    async def _cleanup_session_files(self, file_paths: List[str]) -> None:
        """Clean up intermediate files for a session."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_expired_sessions()
                    await asyncio.sleep(self.cleanup_interval)
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started session cleanup task")
    
    async def close(self) -> None:
        """Close the session manager and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("VideoSystemSessionManager closed")
    
    async def _update_session_registry(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session registry with new information."""
        try:
            user_id = self.session_user_mapping.get(session_id)
            if not user_id or user_id not in self.session_registry:
                return
            
            if session_id not in self.session_registry[user_id]:
                return
            
            # Update registry entry
            for key, value in updates.items():
                # Convert Pydantic models to dict for registry storage
                if hasattr(value, 'model_dump'):
                    self.session_registry[user_id][session_id][key] = value.model_dump()
                elif hasattr(value, 'dict'):
                    self.session_registry[user_id][session_id][key] = value.dict()
                else:
                    self.session_registry[user_id][session_id][key] = value
            
            # Always update the timestamp
            self.session_registry[user_id][session_id]["updated_at"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.warning(f"Failed to update session registry for {session_id}: {e}")
    
    async def _remove_from_registry(self, session_id: str) -> None:
        """Remove session from registry."""
        try:
            user_id = self.session_user_mapping.get(session_id)
            if user_id and user_id in self.session_registry:
                if session_id in self.session_registry[user_id]:
                    del self.session_registry[user_id][session_id]
                
                # Clean up empty user entries
                if not self.session_registry[user_id]:
                    del self.session_registry[user_id]
                    
        except Exception as e:
            logger.warning(f"Failed to remove session {session_id} from registry: {e}")
    
    async def list_sessions_paginated(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """List sessions with pagination support.
        
        Args:
            user_id: Filter by user ID
            page: Page number (1-based)
            page_size: Number of sessions per page
            status_filter: Filter by status
            
        Returns:
            Dictionary with sessions, pagination info, and totals
        """
        try:
            # Get all matching sessions
            all_sessions = await self.list_sessions(user_id=user_id, status_filter=status_filter)
            
            # Calculate pagination
            total_count = len(all_sessions)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # Get page of sessions
            page_sessions = all_sessions[start_idx:end_idx]
            
            return {
                "sessions": page_sessions,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "has_next": end_idx < total_count,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list sessions with pagination: {e}")
            return {
                "sessions": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }


# Global session manager instance
_session_manager: Optional[VideoSystemSessionManager] = None


async def get_session_manager() -> VideoSystemSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = VideoSystemSessionManager()
    return _session_manager


async def initialize_session_manager(
    session_service: Optional[BaseSessionService] = None,
    cleanup_interval: int = 3600,
    max_session_age_hours: int = 24
) -> VideoSystemSessionManager:
    """Initialize the global session manager."""
    global _session_manager
    _session_manager = VideoSystemSessionManager(
        session_service=session_service,
        cleanup_interval=cleanup_interval,
        max_session_age_hours=max_session_age_hours
    )
    return _session_manager