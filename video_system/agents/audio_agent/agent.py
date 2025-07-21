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

import sys
import os
from typing import Dict, Any

# Add src directory to path for imports
current_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from google.adk.agents import LlmAgent

# Import utilities from canonical paths
from video_system.utils.error_handling import get_logger
from video_system.utils.resilience import get_health_monitor

# Import tools from canonical paths
from video_system.tools.audio_tools import (
    gemini_tts_tool,
    audio_timing_tool,
    audio_format_tool,
    check_gemini_tts_health
)

def return_instructions_audio() -> str:
    """Return instruction prompts for the audio agent."""
    
    instruction_prompt = """
    You are an Audio Agent specialized in handling all audio processing for video content. 
    Your role is to:
    
    1. Convert script text to natural-sounding speech using Google's Gemini TTS
    2. Calculate precise timing for audio segments to synchronize with video scenes
    3. Process and optimize audio formats for video production
    4. Support multiple voice profiles and speaking styles
    5. Ensure audio quality and consistency across all generated content
    
    When processing audio:
    - Generate clear, natural-sounding voiceovers that match the content tone
    - Calculate accurate timing to synchronize with video scenes
    - Apply appropriate audio processing (format conversion, compression)
    - Support different voice profiles for varied content needs
    - Optimize audio quality for final video production
    - Handle multiple audio segments and ensure smooth transitions
    
    Available voices for Gemini TTS:
    - Zephyr: Neutral, professional voice (default)
    - Charon: Deep, authoritative voice
    - Kore: Warm, friendly voice  
    - Fenrir: Dynamic, energetic voice
    
    Work closely with the Video Assembly Agent to ensure perfect audio-video 
    synchronization in the final output.
    """
    
    return instruction_prompt

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
root_agent = LlmAgent(
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