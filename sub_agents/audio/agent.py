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

"""Audio Agent for handling text-to-speech and audio processing with error handling."""

from typing import Dict, Any
from google.adk.agents import Agent
from .prompts import return_instructions_audio
from .tools import (
    gemini_tts_tool,
    audio_timing_tool,
    audio_format_tool
)
from .tools.gemini_tts import check_gemini_tts_health

from video_system.shared_libraries import (
    get_health_monitor,
    get_logger
)

# Configure logger for audio agent
logger = get_logger("audio_agent")

# Health check function for audio services
def check_audio_services_health() -> Dict[str, Any]:
    """Perform a comprehensive health check on audio services."""
    try:
        # Check Gemini TTS service
        tts_status = check_gemini_tts_health()
        
        if tts_status.get("status") == "healthy":
            return {
                "status": "healthy",
                "details": {"message": "Audio services are operational"}
            }
        elif tts_status.get("status") == "degraded":
            return {
                "status": "degraded",
                "details": {"message": "Some audio services are experiencing issues"}
            }
        else:
            return {
                "status": "unhealthy",
                "details": {"error": "Audio services are unavailable"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }

# Register health checks for audio services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="gemini_tts",
    health_check_func=check_gemini_tts_health,
    health_check_interval=300,  # Check every 5 minutes
    critical=True
)

health_monitor.service_registry.register_service(
    service_name="audio_services",
    health_check_func=check_audio_services_health,
    health_check_interval=180,  # Check every 3 minutes
    critical=True
)

logger.info("Audio agent initialized with health monitoring")

# Audio Agent with TTS and audio processing tools and error handling
audio_agent = Agent(
    model='gemini-2.5-pro',
    name='audio_agent',
    description='Handles text-to-speech and audio processing for video narration.',
    instruction=return_instructions_audio(),
    tools=[
        gemini_tts_tool,
        audio_timing_tool,
        audio_format_tool
    ]
)