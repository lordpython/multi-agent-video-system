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

"""Research Agent for gathering information and context for video content with error handling."""

from google.adk.agents import LlmAgent
from .prompts import return_instructions_research
from .tools.web_search import serper_web_search_tool, check_serper_health

from video_system.shared_libraries import (
    get_health_monitor,
    get_logger
)

# Configure logger for research agent
logger = get_logger("research_agent")

# Register health checks for research services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="serper_api",
    health_check_func=check_serper_health,
    health_check_interval=300,  # Check every 5 minutes
    critical=True
)

logger.info("Research agent initialized with health monitoring")

# Research Agent with web search capabilities and error handling
research_agent = LlmAgent(
    model='gemini-2.5-pro',
    name='research_agent',
    description='Performs web searches to gather information and context for video content.',
    instruction=return_instructions_research(),
    tools=[serper_web_search_tool]
)