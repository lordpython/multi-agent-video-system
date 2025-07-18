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

"""Root orchestrator agent for the multi-agent video system."""

import os
from google.adk.agents import Agent
from dotenv import load_dotenv
from .prompts import return_instructions_root

load_dotenv()

# Root orchestrator agent - will be implemented in task 9
root_agent = Agent(
    model='gemini-2.5-flash',
    name='video_system_orchestrator',
    instruction=return_instructions_root(),
    tools=[]  # Tools will be added as sub-agents are implemented
)