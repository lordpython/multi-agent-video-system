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

"""Orchestration agent for the multi-agent video generation system."""

from google.adk.agents import SequentialAgent
from sub_agents.research.agent import research_agent
from sub_agents.story.agent import story_agent
from sub_agents.asset_sourcing.agent import asset_sourcing_agent
from sub_agents.image_generation.agent import image_generation_agent
from sub_agents.audio.agent import audio_agent
from sub_agents.video_assembly.agent import video_assembly_agent


# Root agent orchestrating the video generation process sequentially.
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
