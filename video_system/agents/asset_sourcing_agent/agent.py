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
"""Asset Sourcing Agent for finding and managing visual assets with error handling."""

import os
import sys
from typing import Dict, Any

# -----------------------------------------------------------------------------
# Ensure canonical import paths are available
# -----------------------------------------------------------------------------
# Add the src directory to the Python path for ``video_system`` modules
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add the project root to the Python path so that ``video_system.shared_libraries``
# and the legacy ``sub_agents`` package can be imported without issues.
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Ensure the root video_system directory is accessible
video_system_root = os.path.join(project_root, "video_system")
if video_system_root not in sys.path:
    sys.path.insert(0, video_system_root)

# -----------------------------------------------------------------------------
# Imports – external ADK + shared libs
# -----------------------------------------------------------------------------
try:
    from google.adk.agents import Agent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    # Define mock class for environments without ADK
    class Agent:
        def __init__(self, **kwargs):
            pass

# Import from canonical utilities
from video_system.utils.resilience import get_health_monitor
from video_system.utils.logging_config import get_logger

# -----------------------------------------------------------------------------
# Imports – canonical utilities & tools
# -----------------------------------------------------------------------------
from video_system.tools.asset_tools import (
    pexels_search_tool,
    unsplash_search_tool,
    pixabay_search_tool,
    check_pexels_health,
)


def return_instructions_asset_sourcing() -> str:
    """Return instruction prompts for the asset sourcing agent."""

    instruction_prompt = """
    You are an Asset Sourcing Agent specialized in finding and managing visual 
    assets for video content. Your role is to:
    
    1. Search for high-quality images and videos from stock media APIs
    2. Evaluate and select the most appropriate assets for each scene
    3. Manage asset licensing and attribution requirements
    4. Optimize asset quality and format for video production
    5. Provide fallback options when primary assets are unavailable
    
    When sourcing assets:
    - Focus on high-quality, relevant visual content
    - Ensure proper licensing and attribution
    - Consider the overall visual style and consistency
    - Provide multiple options for each scene requirement
    - Optimize assets for video production workflows
    
    Your output should provide the Story and Video Assembly agents with 
    all necessary visual assets for professional video production.
    """

    return instruction_prompt


# -----------------------------------------------------------------------------
# Logging & health-monitoring setup
# -----------------------------------------------------------------------------
logger = get_logger("asset_sourcing_agent")


def check_asset_sourcing_health() -> Dict[str, Any]:
    """Perform a comprehensive health check on all asset-sourcing services."""
    try:
        pexels_status = check_pexels_health()

        # Additional services (Unsplash, Pixabay) can be incorporated similarly
        if pexels_status.get("status") == "healthy":
            return {
                "status": "healthy",
                "details": {"message": "Asset sourcing services are operational"},
            }
        elif pexels_status.get("status") == "degraded":
            return {
                "status": "degraded",
                "details": {
                    "message": "Some asset sourcing services are experiencing issues"
                },
            }
        else:
            return {
                "status": "unhealthy",
                "details": {"error": "Asset sourcing services are unavailable"},
            }

    except Exception as exc:  # pylint: disable=broad-except
        return {"status": "unhealthy", "details": {"error": str(exc)}}


# Register health checks
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="pexels_api",
    health_check_func=check_pexels_health,
    health_check_interval=300,  # every 5 minutes
    critical=True,
)
health_monitor.service_registry.register_service(
    service_name="asset_sourcing",
    health_check_func=check_asset_sourcing_health,
    health_check_interval=180,  # every 3 minutes
    critical=True,
)

logger.info("Asset sourcing agent initialized with health monitoring")

# -----------------------------------------------------------------------------
# Root ADK agent
# -----------------------------------------------------------------------------
if ADK_AVAILABLE:
    root_agent = Agent(
        model="gemini-2.5-pro",
        name="asset_sourcing_agent",
        description=(
            "Finds and manages visual assets for video content using various "
            "stock media APIs."
        ),
        instruction=return_instructions_asset_sourcing(),
        tools=[pexels_search_tool, unsplash_search_tool, pixabay_search_tool],
    )
else:
    # Fallback for environments without ADK
    root_agent = None
    logger.warning("ADK not available - asset sourcing agent disabled")
