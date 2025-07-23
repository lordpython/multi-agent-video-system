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

from typing import Dict, Any
from google.adk.agents import Agent
from .prompts import return_instructions_asset_sourcing
from .tools import pexels_search_tool, unsplash_search_tool, pixabay_search_tool
from .tools.pexels_search import check_pexels_health

from video_system.shared_libraries import get_health_monitor, get_logger

# Configure logger for asset sourcing agent
logger = get_logger("asset_sourcing_agent")


# Health check functions for asset sourcing services
def check_asset_sourcing_health() -> Dict[str, Any]:
    """Perform a comprehensive health check on asset sourcing services."""
    try:
        # Check individual services
        pexels_status = check_pexels_health()

        # For now, we'll focus on Pexels as the primary service
        # Additional services (Unsplash, Pixabay) can be added similarly

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
    except Exception as e:
        return {"status": "unhealthy", "details": {"error": str(e)}}


# Register health checks for asset sourcing services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="pexels_api",
    health_check_func=check_pexels_health,
    health_check_interval=300,  # Check every 5 minutes
    critical=True,
)

health_monitor.service_registry.register_service(
    service_name="asset_sourcing",
    health_check_func=check_asset_sourcing_health,
    health_check_interval=180,  # Check every 3 minutes
    critical=True,
)

logger.info("Asset sourcing agent initialized with health monitoring")

# Asset Sourcing Agent with media API integration tools and error handling
asset_sourcing_agent = Agent(
    model="gemini-2.5-pro",
    name="asset_sourcing_agent",
    description="Finds and manages visual assets for video content using various stock media APIs.",
    instruction=return_instructions_asset_sourcing(),
    tools=[pexels_search_tool, unsplash_search_tool, pixabay_search_tool],
)
