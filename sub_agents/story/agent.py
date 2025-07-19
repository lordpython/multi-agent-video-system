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

"""Story Agent for creating scripts and narrative structure with error handling."""

from google.adk.agents import Agent
from .prompts import return_instructions_story
from .tools import (
    script_generation_tool,
    scene_breakdown_tool,
    visual_description_tool,
    visual_enhancement_tool
)

from typing import Dict, Any
from video_system.shared_libraries import (
    get_health_monitor,
    get_logger,
    ProcessingError,
    log_error
)

# Configure logger for story agent
logger = get_logger("story_agent")

# Health check function for story generation services
def check_story_generation_health() -> Dict[str, Any]:
    """Perform a health check on story generation capabilities."""
    try:
        # Test script generation with minimal data
        test_data = {
            "facts": ["Test fact for health check"],
            "key_points": ["Test key point for health check"],
            "sources": [],
            "context": {"topic": "health check"}
        }
        
        result = script_generation_tool(test_data, target_duration=30, style="professional")
        
        if result.get("success", False):
            return {
                "status": "healthy",
                "details": {"message": "Story generation is working normally"}
            }
        else:
            return {
                "status": "degraded",
                "details": {"error": "Story generation returned error response"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }

# Register health checks for story services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="story_generation",
    health_check_func=check_story_generation_health,
    health_check_interval=300,  # Check every 5 minutes
    critical=True
)

logger.info("Story agent initialized with health monitoring")

# Story Agent with script generation and visual description tools
story_agent = Agent(
    model='gemini-2.5-flash',
    name='story_agent',
    instruction=return_instructions_story(),
    tools=[
        script_generation_tool,
        scene_breakdown_tool,
        visual_description_tool,
        visual_enhancement_tool
    ]
)