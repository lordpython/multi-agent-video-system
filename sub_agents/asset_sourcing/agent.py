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

"""Asset Sourcing Agent for finding and managing visual assets."""

from google.adk.agents import Agent
from .prompts import return_instructions_asset_sourcing
from .tools import (
    pexels_search_tool,
    unsplash_search_tool,
    pixabay_search_tool
)

# Asset Sourcing Agent with media API integration tools
asset_sourcing_agent = Agent(
    model='gemini-2.5-flash',
    name='asset_sourcing_agent',
    instruction=return_instructions_asset_sourcing(),
    tools=[
        pexels_search_tool,
        unsplash_search_tool,
        pixabay_search_tool
    ]
)