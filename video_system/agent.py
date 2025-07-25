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

"""Video Orchestrator Agent - Coordinates the entire video generation process."""

try:
    from google.adk.agents import SequentialAgent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    # Define mock class for environments without ADK
    class SequentialAgent:
        def __init__(self, **kwargs):
            pass

# Import all sub-agents from their canonical locations
from video_system.agents.research_agent.agent import root_agent as research_agent
from video_system.agents.story_agent.agent import root_agent as story_agent
from video_system.agents.asset_sourcing_agent.agent import root_agent as asset_sourcing_agent
from video_system.agents.image_generation_agent.agent import root_agent as image_generation_agent
from video_system.agents.audio_agent.agent import root_agent as audio_agent
from video_system.agents.video_assembly_agent.agent import root_agent as video_assembly_agent

# Root agent orchestrating the video generation process sequentially
if ADK_AVAILABLE:
    root_agent = SequentialAgent(
        name="video_system_orchestrator",
        description="Orchestrates the entire video generation process by running sub-agents in sequence.",
        sub_agents=[
            research_agent,
            story_agent,
            asset_sourcing_agent,
            image_generation_agent,
            audio_agent,
            video_assembly_agent,
        ],
    )
else:
    # Fallback for environments without ADK
    root_agent = None
    print("Warning: ADK not available - video orchestrator disabled")
