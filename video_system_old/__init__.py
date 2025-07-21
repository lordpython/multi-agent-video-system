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

import logging

# Attempt to import ADK components with graceful error handling
try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService, Session
    from google.genai.types import Content, Part
    ADK_AVAILABLE = True
except ImportError:
    logging.warning("ADK components not found. Using mock objects for development.")
    # Define mock objects for development without ADK installed
    class Agent:
        def __init__(self, *args, **kwargs):
            pass

    class Runner:
        def __init__(self, *args, **kwargs):
            pass

    class Session:
        pass

    class InMemorySessionService:
        def __init__(self, *args, **kwargs):
            pass
    
    class Content:
        def __init__(self, *args, **kwargs):
            pass
    
    class Part:
        def __init__(self, *args, **kwargs):
            pass
    
    ADK_AVAILABLE = False

from .agent import root_agent

__all__ = ['root_agent', 'Agent', 'Runner', 'Session', 'InMemorySessionService', 'Content', 'Part', 'ADK_AVAILABLE']

logging.info("Video system package initialized.")