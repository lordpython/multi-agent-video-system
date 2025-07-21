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

import sys
import os
# Add the src directory to the Python path for video_system modules
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, src_path)
# Add the project root to the Python path for video_system.shared_libraries
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

from google.adk.agents import LlmAgent
from src.video_system.utils.prompts import return_instructions_story
from src.video_system.tools.story_tools import (
    script_generation_tool,
    scene_breakdown_tool,
    visual_description_tool,
    visual_enhancement_tool,
    story_health_check_tool
)

from video_system.shared_libraries import (
    get_health_monitor,
    get_logger
)

# Configure logger for story agent
logger = get_logger("story_agent")

# Register health checks for story services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="story_generation",
    health_check_func=story_health_check_tool.func,  # Access the underlying function
    health_check_interval=300,  # Check every 5 minutes
    critical=True
)

logger.info("Story agent initialized with health monitoring")

# Story Agent with script generation and visual description tools
root_agent = LlmAgent(
    model='gemini-2.5-pro',
    name='story_agent',
    description='Creates scripts and narrative structure for video content.',
    instruction=return_instructions_story(),
    tools=[
        script_generation_tool,
        scene_breakdown_tool,
        visual_description_tool,
        visual_enhancement_tool
    ]
)