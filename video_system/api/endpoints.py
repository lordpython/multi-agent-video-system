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

"""Enhanced API with real video generation capabilities."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from video_system.utils.models import VideoGenerationRequest
from video_system.utils.logging_config import get_logger
from video_system.agents.video_orchestrator.agent import root_agent

# ADK imports with availability check
try:
    from google.adk.runners import Runner
    from google.adk.sessions import SessionService, InMemorySessionService
    from google.genai.types import Content, Part
    from rich.console import Console

    ADK_AVAILABLE = True
except ImportError as e:
    print(f"ADK not available: {e}")
    ADK_AVAILABLE = False

    # Mock classes for development
    class Runner:
        pass

    class SessionService:
        pass

    class InMemorySessionService:
        pass

    class Content:
        pass

    class Part:
        pass

    class Console:
        def __init__(self):
            pass


# Load environment variables
load_dotenv()

console = Console()
logger = get_logger(__name__)

# Initialize ADK SessionService
if ADK_AVAILABLE:
    session_service: SessionService = InMemorySessionService()
else:
    # Mock session service for development
    class MockSessionService:
        def __init__(self):
            self.sessions = {}

        async def create_session(self, app_name: str, user_id: str, state: dict = None):
            import uuid

            session_id = str(uuid.uuid4())
            session = type(
                "Session",
                (),
                {
                    "id": session_id,
                    "app_name": app_name,
                    "user_id": user_id,
                    "state": state or {},
                    "last_update_time": datetime.now(timezone.utc).timestamp(),
                },
            )()
            self.sessions[session_id] = session
            return session

        async def get_session(self, app_name: str, user_id: str, session_id: str):
            return self.sessions.get(session_id)

        async def delete_session(self, app_name: str, user_id: str, session_id: str):
            self.sessions.pop(session_id, None)

    session_service = MockSessionService()

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Video System API (Real Generation)",
    description="AI-powered video creation platform with real video generation capabilities",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models


class VideoGenerationRequest(BaseModel):
    """API model for real video generation requests."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Text prompt for video generation",
    )
    duration_preference: Optional[int] = Field(
        60, ge=10, le=600, description="Preferred video duration in seconds"
    )
    style: Optional[str] = Field("professional", description="Video style preference")
    voice_preference: Optional[str] = Field(
        "neutral", description="Voice preference for narration"
    )
    quality: Optional[str] = Field("high", description="Video quality setting")
    user_id: Optional[str] = Field(None, description="Optional user identifier")

    @field_validator("style")
    @classmethod
    def validate_style(cls, v):
        valid_styles = [
            "professional",
            "casual",
            "educational",
            "entertainment",
            "documentary",
        ]
        if v not in valid_styles:
            raise ValueError(f"Style must be one of: {', '.join(valid_styles)}")
        return v

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v):
        valid_qualities = ["low", "medium", "high", "ultra"]
        if v not in valid_qualities:
            raise ValueError(f"Quality must be one of: {', '.join(valid_qualities)}")
        return v


class VideoGenerationResponse(BaseModel):
    """API model for video generation responses."""

    session_id: str
    status: str
    message: str
    estimated_duration_minutes: Optional[int] = None
    created_at: datetime


class SessionStatusResponse(BaseModel):
    """API model for session status responses."""

    session_id: str
    status: str
    stage: str
    progress: float
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    video_file_path: Optional[str] = None
    request_details: Dict[str, Any]


# API Endpoints


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multi-Agent Video System API",
        "version": "0.3.0",
        "description": "AI-powered video creation with real video generation capabilities",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.post("/videos/generate", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """Start video generation."""
    try:
        logger.info(f"Received video generation request: {request.prompt[:50]}...")

        agent = root_agent
        app_name = "video-generation-system"
        estimated_duration = max(2, request.duration_preference // 30)  # Rough estimate

        # Create session
        session = await session_service.create_session(
            app_name=app_name,
            user_id=request.user_id or "default",
            state={
                "prompt": request.prompt,
                "duration_preference": request.duration_preference,
                "style": request.style,
                "voice_preference": request.voice_preference,
                "quality": request.quality,
                "current_stage": "initializing",
                "progress": 0.0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "processing",
            },
        )

        logger.info(f"Created session {session.id} for video generation")

        # Start video generation asynchronously
        asyncio.create_task(
            _process_video_generation(session.id, request.prompt, agent, app_name)
        )

        return VideoGenerationResponse(
            session_id=session.id,
            status="processing",
            message="Video generation started successfully",
            estimated_duration_minutes=estimated_duration,
            created_at=datetime.now(timezone.utc),
        )

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting video generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos/{session_id}/status", response_model=SessionStatusResponse)
async def get_video_status(session_id: str = PathParam(..., description="Session ID")):
    """Get the status of a video generation session."""
    try:
        session = await session_service.get_session(
            app_name="video-generation-system",
            user_id="default",  # Or get from auth
            session_id=session_id,
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Extract status information
        state = session.state
        current_stage = state.get("current_stage", "unknown")
        progress = state.get("progress", 0.0)
        error_message = state.get("error_message")
        created_at_str = state.get("created_at")

        # Determine status
        if error_message:
            status = "failed"
        elif current_stage == "completed":
            status = "completed"
        elif current_stage == "failed":
            status = "failed"
        else:
            status = "processing"

        # Get video file path if available
        video_file_path = None
        if "final_video" in state:
            final_video_data = state["final_video"]
            if isinstance(final_video_data, dict):
                video_file_path = final_video_data.get("video_file")

        # Parse created_at timestamp
        try:
            created_at = (
                datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at_str
                else datetime.now(timezone.utc)
            )
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

        return SessionStatusResponse(
            session_id=session_id,
            status=status,
            stage=current_stage,
            progress=progress,
            created_at=created_at,
            updated_at=datetime.fromtimestamp(
                session.last_update_time, tz=timezone.utc
            ),
            error_message=error_message,
            video_file_path=video_file_path,
            request_details={
                "prompt": state.get("prompt", ""),
                "duration_preference": state.get("duration_preference", 60),
                "style": state.get("style", "professional"),
                "voice_preference": state.get("voice_preference", "neutral"),
                "quality": state.get("quality", "high"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos/{session_id}/download")
async def download_video(session_id: str = PathParam(..., description="Session ID")):
    """Download the generated video file."""
    try:
        # Find session
        session = await session_service.get_session(
            app_name="video-generation-system",
            user_id="default",  # Or get from auth
            session_id=session_id,
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        state = session.state
        if state.get("current_stage") != "completed":
            raise HTTPException(
                status_code=400, detail="Video generation not completed"
            )

        # Get video file path
        final_video_data = state.get("final_video")
        if not final_video_data or not final_video_data.get("video_file"):
            raise HTTPException(status_code=404, detail="Video file not found")

        video_path = Path(final_video_data["video_file"])
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found on disk")

        return FileResponse(
            path=str(video_path),
            filename=f"video_{session_id[:8]}.mp4",
            media_type="video/mp4",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/system/stats")
async def system_stats():
    """Get system statistics."""
    try:
        # This is a simplified implementation. In a real system, you'd query a database.
        sessions = session_service.sessions.values()

        total_sessions = len(sessions)
        status_distribution = {}

        for session in sessions:
            state = session.state
            current_stage = state.get("current_stage", "unknown")
            error_message = state.get("error_message")

            if error_message:
                status = "failed"
            elif current_stage == "completed":
                status = "completed"
            elif current_stage == "failed":
                status = "failed"
            else:
                status = "processing"

            status_distribution[status] = status_distribution.get(status, 0) + 1

        return {
            "total_sessions": total_sessions,
            "status_distribution": status_distribution,
        }

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/system/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """Clean up old and completed sessions."""
    try:
        # This is a simplified implementation. In a real system, you'd query a database.
        now = datetime.now(timezone.utc)
        cleaned_count = 0
        sessions_to_delete = []

        for session_id, session in session_service.sessions.items():
            created_at_str = session.state.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    age_hours = (now - created_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        sessions_to_delete.append(session_id)
                except (ValueError, AttributeError):
                    continue

        for session_id in sessions_to_delete:
            await session_service.delete_session(
                app_name="video-generation-system",
                user_id="default",  # or get from auth
                session_id=session_id,
            )
            cleaned_count += 1

        return {"cleaned_count": cleaned_count, "max_age_hours": max_age_hours}

    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/videos/list")
async def list_sessions():
    """List all video generation sessions."""
    try:
        # This is a simplified implementation. In a real system, you'd query a database.
        sessions = session_service.sessions.values()

        session_list = []
        for session in sessions:
            state = session.state
            current_stage = state.get("current_stage", "unknown")
            error_message = state.get("error_message")

            if error_message:
                status = "failed"
            elif current_stage == "completed":
                status = "completed"
            elif current_stage == "failed":
                status = "failed"
            else:
                status = "processing"

            session_list.append(
                {
                    "session_id": session.id,
                    "status": status,
                    "stage": current_stage,
                    "progress": state.get("progress", 0.0),
                    "created_at": state.get("created_at"),
                    "user_id": session.user_id,
                }
            )

        return {"sessions": session_list}

    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Enhanced health check with dependency status."""
    try:
        # Check session service
        test_session = await session_service.create_session(
            app_name="health-check", user_id="health", state={"test": True}
        )

        await session_service.delete_session(
            app_name="health-check", user_id="health", session_id=test_session.id
        )

        # Check video generation dependencies
        dependencies = {}

        try:
            import moviepy

            dependencies["moviepy"] = "available"
        except ImportError:
            dependencies["moviepy"] = "missing"

        try:
            import PIL

            dependencies["pillow"] = "available"
        except ImportError:
            dependencies["pillow"] = "missing"

        try:
            import pyttsx3

            dependencies["pyttsx3"] = "available"
        except ImportError:
            dependencies["pyttsx3"] = "missing"

        try:
            import numpy

            dependencies["numpy"] = "available"
        except ImportError:
            dependencies["numpy"] = "missing"

        # Determine overall health
        missing_deps = [k for k, v in dependencies.items() if v == "missing"]
        real_generation_available = len(missing_deps) == 0

        response = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {
                "session_service": "operational",
                "adk_available": ADK_AVAILABLE,
                "mock_generation": "available",
                "real_generation": "available"
                if real_generation_available
                else "limited",
                "dependencies": dependencies,
            },
        }

        if missing_deps:
            response["details"]["missing_dependencies"] = missing_deps
            response["details"]["note"] = (
                "Real video generation requires all dependencies"
            )

        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {"error": str(e)},
            },
            status_code=503,
        )


# Background task function


async def _process_video_generation(session_id: str, prompt: str, agent, app_name: str):
    """Background task to process video generation with selected agent."""
    try:
        logger.info(
            f"Starting video generation for session {session_id} with {agent.name}"
        )

        # Find session
        session = await session_service.get_session(
            app_name=app_name,
            user_id="default",  # or get from auth
            session_id=session_id,
        )

        if not session:
            logger.error(f"Session {session_id} not found")
            return

        if ADK_AVAILABLE:
            # Create ADK Runner with selected agent
            runner = Runner(
                agent=agent, app_name=app_name, session_service=session_service
            )

            # Create user message
            user_message = Content(parts=[Part(text=f"Generate video: {prompt}")])

            # Execute agent
            logger.info(f"Invoking {agent.name} for session {session_id}")
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=user_message
            ):
                if event.is_final_response():
                    logger.info(f"Agent completed processing for session {session_id}")
                    # Update session state
                    session.state["current_stage"] = "completed"
                    session.state["progress"] = 1.0
                    break
        else:
            # Mock processing
            logger.info(f"Mock processing for session {session_id}")
            await asyncio.sleep(2)
            session.state["current_stage"] = "completed"
            session.state["progress"] = 1.0

        logger.info(f"Completed video generation for session {session_id}")

    except Exception as e:
        logger.error(f"Error in video generation for session {session_id}: {e}")

        # Update session with error
        try:
            session = await session_service.get_session(
                app_name=app_name,
                user_id="default",  # or get from auth
                session_id=session_id,
            )

            if session:
                session.state["current_stage"] = "failed"
                session.state["error_message"] = str(e)
                session.state["progress"] = 0.0
        except Exception as update_error:
            logger.error(f"Failed to update session state with error: {update_error}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
