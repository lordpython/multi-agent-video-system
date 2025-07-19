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

"""FastAPI REST API interface for the Multi-Agent Video System.

This module provides REST API endpoints for video generation, status checking,
and system management with comprehensive request validation and error handling.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Path as PathParam
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from .shared_libraries.models import (
    VideoGenerationRequest, VideoGenerationStatus, VideoStatus
)
from .shared_libraries.adk_session_manager import get_session_manager
from .shared_libraries.adk_session_models import VideoGenerationStage
from .shared_libraries.progress_monitor import get_progress_monitor
from .agent import initialize_video_system, check_orchestrator_health
from .shared_libraries.logging_config import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Initialize system on startup
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the video system on startup."""
    try:
        initialize_video_system()
        logger.info("Video system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize video system: {e}")
        raise
    yield

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Video System API",
    description="AI-powered video creation platform built on Google's Agent Development Kit (ADK) framework",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models

class VideoGenerationRequestAPI(BaseModel):
    """API model for video generation requests."""
    prompt: str = Field(..., min_length=10, max_length=2000, description="Text prompt for video generation")
    duration_preference: Optional[int] = Field(60, ge=10, le=600, description="Preferred video duration in seconds")
    style: Optional[str] = Field("professional", description="Video style preference")
    voice_preference: Optional[str] = Field("neutral", description="Voice preference for narration")
    quality: Optional[str] = Field("high", description="Video quality setting")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    
    @field_validator('style')
    @classmethod
    def validate_style(cls, v):
        valid_styles = ["professional", "casual", "educational", "entertainment", "documentary"]
        if v not in valid_styles:
            raise ValueError(f"Style must be one of: {', '.join(valid_styles)}")
        return v
    
    @field_validator('quality')
    @classmethod
    def validate_quality(cls, v):
        valid_qualities = ["low", "medium", "high", "ultra"]
        if v not in valid_qualities:
            raise ValueError(f"Quality must be one of: {', '.join(valid_qualities)}")
        return v


class VideoGenerationResponseAPI(BaseModel):
    """API model for video generation responses."""
    session_id: str
    status: str
    message: str
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class SessionStatusResponseAPI(BaseModel):
    """API model for session status responses."""
    session_id: str
    status: str
    stage: str
    progress: float
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    request_details: Dict[str, Any]


class SessionListResponseAPI(BaseModel):
    """API model for session list responses."""
    sessions: List[SessionStatusResponseAPI]
    total_count: int
    page: int
    page_size: int


class SystemStatsResponseAPI(BaseModel):
    """API model for system statistics responses."""
    total_sessions: int
    active_sessions: int
    status_distribution: Dict[str, int]
    stage_distribution: Dict[str, int]
    average_progress: float
    system_health: Dict[str, Any]


class HealthCheckResponseAPI(BaseModel):
    """API model for health check responses."""
    status: str
    timestamp: datetime
    details: Dict[str, Any]


# API Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multi-Agent Video System API",
        "version": "0.1.0",
        "description": "AI-powered video creation platform",
        "docs_url": "/docs",
        "health_url": "/health"
    }


@app.post("/videos/generate", response_model=VideoGenerationResponseAPI)
async def generate_video(request: VideoGenerationRequestAPI, background_tasks: BackgroundTasks):
    """Start video generation from a text prompt."""
    try:
        logger.info(f"Received video generation request: {request.prompt[:50]}...")
        
        # Create video generation request
        video_request = VideoGenerationRequest(
            prompt=request.prompt,
            duration_preference=request.duration_preference,
            style=request.style,
            voice_preference=request.voice_preference,
            quality=request.quality
        )
        
        # Use the agent function to create session and start generation
        from .agent import start_video_generation
        result = await start_video_generation(
            prompt=video_request.prompt,
            duration_preference=video_request.duration_preference,
            style=video_request.style,
            voice_preference=video_request.voice_preference,
            quality=video_request.quality,
            user_id=request.user_id or "default"
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error_message', 'Failed to start video generation'))
        
        session_id = result['session_id']
        
        # Start progress monitoring
        progress_monitor = get_progress_monitor()
        progress_monitor.start_session_monitoring(session_id)
        
        # Start background processing
        background_tasks.add_task(_process_video_generation, session_id)
        
        # Get session status
        session_manager = await get_session_manager()
        session_status = await session_manager.get_session_status(session_id)
        
        return VideoGenerationResponseAPI(
            session_id=session_id,
            status=session_status.status if session_status else "queued",
            message="Video generation started successfully",
            created_at=datetime.now(timezone.utc),
            estimated_completion=None
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting video generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos/{session_id}/status", response_model=SessionStatusResponseAPI)
async def get_video_status(session_id: str = PathParam(..., description="Session ID")):
    """Get the status of a video generation session."""
    try:
        session_manager = await get_session_manager()
        state = await session_manager.get_session_state(session_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        status_value = "completed" if state.is_completed() else "failed" if state.is_failed() else "processing"
        
        return SessionStatusResponseAPI(
            session_id=session_id,
            status=status_value,
            stage=state.current_stage.value,
            progress=state.progress,
            created_at=state.created_at,
            updated_at=state.updated_at,
            estimated_completion=state.estimated_completion,
            error_message=state.error_message,
            request_details=state.request.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos/{session_id}/progress", response_model=Dict[str, Any])
async def get_video_progress(session_id: str = PathParam(..., description="Session ID")):
    """Get detailed progress information for a video generation session."""
    try:
        progress_monitor = get_progress_monitor()
        progress_info = progress_monitor.get_session_progress(session_id)
        
        if not progress_info:
            raise HTTPException(status_code=404, detail="Session not found or not being monitored")
        
        return progress_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos/{session_id}/download")
async def download_video(session_id: str = PathParam(..., description="Session ID")):
    """Download the generated video file."""
    try:
        session_manager = await get_session_manager()
        state = await session_manager.get_session_state(session_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not state.is_completed():
            raise HTTPException(status_code=400, detail="Video generation not completed")
        
        # Get final video file
        if not state.final_video:
            raise HTTPException(status_code=404, detail="Video file not found")
        
        video_path = Path(state.final_video.file_path)
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found on disk")
        
        return FileResponse(
            path=str(video_path),
            filename=f"video_{session_id[:8]}.mp4",
            media_type="video/mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/videos/{session_id}")
async def cancel_video_generation(session_id: str = PathParam(..., description="Session ID")):
    """Cancel a video generation session."""
    try:
        session_manager = await get_session_manager()
        state = await session_manager.get_session_state(session_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session status to cancelled
        success = await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message="Cancelled by user request"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel session")
        
        # Stop progress monitoring
        progress_monitor = get_progress_monitor()
        progress_monitor.complete_session(session_id, success=False, error_message="Cancelled by user")
        
        return {"message": "Session cancelled successfully", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos", response_model=SessionListResponseAPI)
async def list_video_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status (completed, failed, processing, queued)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
):
    """List video generation sessions with optional filtering and pagination."""
    try:
        session_manager = await get_session_manager()
        
        # Use the new paginated listing functionality
        result = await session_manager.list_sessions_paginated(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status
        )
        
        sessions = result["sessions"]
        pagination = result["pagination"]
        
        # Convert to API response format
        session_responses = []
        for state in sessions:
            status_value = "completed" if state.is_completed() else "failed" if state.is_failed() else "processing"
            session_responses.append(SessionStatusResponseAPI(
                session_id=state.session_id,
                status=status_value,
                stage=state.current_stage.value,
                progress=state.progress,
                created_at=state.created_at,
                updated_at=state.updated_at,
                estimated_completion=state.estimated_completion,
                error_message=state.error_message,
                request_details=state.request.model_dump()
            ))
        
        return SessionListResponseAPI(
            sessions=session_responses,
            total_count=pagination["total_count"],
            page=pagination["page"],
            page_size=pagination["page_size"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/system/stats", response_model=SystemStatsResponseAPI)
async def get_system_stats():
    """Get system statistics and health information."""
    try:
        session_manager = await get_session_manager()
        stats = await session_manager.get_statistics()
        health = check_orchestrator_health()
        
        return SystemStatsResponseAPI(
            total_sessions=stats.total_sessions,
            active_sessions=stats.active_sessions,
            status_distribution={"completed": stats.completed_sessions, "failed": stats.failed_sessions, "active": stats.active_sessions},
            stage_distribution={},  # Not available in new model
            average_progress=0.0,  # Not available in new model
            system_health=health
        )
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", response_model=HealthCheckResponseAPI)
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        health = check_orchestrator_health()
        
        # Determine HTTP status code based on health
        status_code = 200
        if health["status"] == "degraded":
            status_code = 200  # Still operational
        elif health["status"] == "unhealthy":
            status_code = 503  # Service unavailable
        
        response = HealthCheckResponseAPI(
            status=health["status"],
            timestamp=datetime.now(timezone.utc),
            details=health.get("details", {})
        )
        
        # Convert to dict with proper datetime serialization
        response_dict = response.model_dump()
        response_dict["timestamp"] = response.timestamp.isoformat()
        
        return JSONResponse(content=response_dict, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {"error": str(e)}
            },
            status_code=503
        )


@app.post("/system/cleanup")
async def cleanup_sessions(max_age_hours: int = Query(24, ge=1, description="Maximum age in hours")):
    """Clean up old and completed sessions."""
    try:
        session_manager = await get_session_manager()
        cleaned_count = await session_manager.cleanup_expired_sessions()
        
        return {
            "message": f"Cleaned up {cleaned_count} expired sessions",
            "cleaned_count": cleaned_count,
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Background task functions

async def _process_video_generation(session_id: str):
    """Background task to process video generation."""
    try:
        logger.info(f"Starting background video generation for session {session_id}")
        
        # Use the agent function to execute the workflow
        from .agent import execute_complete_workflow
        workflow_result = await execute_complete_workflow(session_id)
        
        if not workflow_result.get('success'):
            logger.error(f"Workflow execution failed: {workflow_result.get('error_message')}")
            return
        
        session_manager = await get_session_manager()
        progress_monitor = get_progress_monitor()
        
        # Simulate the video generation workflow
        # In a real implementation, this would call the actual agent coordination tools
        
        stages = [
            (VideoGenerationStage.RESEARCHING, 15),
            (VideoGenerationStage.SCRIPTING, 20),
            (VideoGenerationStage.ASSET_SOURCING, 25),
            (VideoGenerationStage.AUDIO_GENERATION, 20),
            (VideoGenerationStage.VIDEO_ASSEMBLY, 15),
            (VideoGenerationStage.FINALIZING, 5)
        ]
        
        for stage, duration in stages:
            # Advance to stage
            await session_manager.update_stage_and_progress(session_id, stage, 0.0)
            progress_monitor.advance_to_stage(session_id, stage)
            
            # Simulate processing with progress updates
            for i in range(duration):
                await asyncio.sleep(1)  # Simulate work
                progress = (i + 1) / duration
                progress_monitor.update_stage_progress(session_id, stage, progress)
        
        # Complete the session
        await session_manager.update_stage_and_progress(session_id, VideoGenerationStage.COMPLETED, 1.0)
        progress_monitor.complete_session(session_id, success=True)
        
        logger.info(f"Completed video generation for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in background video generation for session {session_id}: {e}")
        
        # Mark session as failed
        session_manager = await get_session_manager()
        progress_monitor = get_progress_monitor()
        
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message=str(e)
        )
        progress_monitor.complete_session(session_id, success=False, error_message=str(e))


# Error handlers

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": "The requested resource was not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)