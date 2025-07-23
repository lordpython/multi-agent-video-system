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

import os
import vertexai
from vertexai import agent_engines
from google.adk.sessions import VertexAiSessionService
from dotenv import load_dotenv
import json
import asyncio


def pretty_print_event(event):
    """Pretty prints an event with truncation for long content."""
    if "content" not in event:
        print(f"[{event.get('author', 'unknown')}]: {event}")
        return

    author = event.get("author", "unknown")
    parts = event["content"].get("parts", [])

    for part in parts:
        if "text" in part:
            text = part["text"]
            # Truncate long text to 200 characters
            if len(text) > 200:
                text = text[:197] + "..."
            print(f"[{author}]: {text}")
        elif "functionCall" in part:
            func_call = part["functionCall"]
            print(f"[{author}]: Function call: {func_call.get('name', 'unknown')}")
            # Truncate args if too long
            args = json.dumps(func_call.get("args", {}))
            if len(args) > 100:
                args = args[:97] + "..."
            print(f"  Args: {args}")
        elif "functionResponse" in part:
            func_response = part["functionResponse"]
            print(
                f"[{author}]: Function response: {func_response.get('name', 'unknown')}"
            )
            # Truncate response if too long
            response = json.dumps(func_response.get("response", {}))
            if len(response) > 100:
                response = response[:97] + "..."
            print(f"  Response: {response}")


load_dotenv()

vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION"),
)

session_service = VertexAiSessionService(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION"),
)
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")

session = asyncio.run(
    session_service.create_session(
        app_name=AGENT_ENGINE_ID,
        user_id="123",
    )
)

agent_engine = agent_engines.get(AGENT_ENGINE_ID)

queries = [
    "Hi, I'd like to create a video about sustainable technology innovations.",
    "Create a 60-second video about the benefits of renewable energy for businesses.",
    "Generate a video explaining how AI is transforming healthcare, focusing on diagnostic tools.",
    "Thanks, that's all I need for now. Goodbye!",
]

for query in queries:
    print(f"\n[user]: {query}")
    for event in agent_engine.stream_query(
        user_id="123",
        session_id=session.id,
        message=query,
    ):
        pretty_print_event(event)
