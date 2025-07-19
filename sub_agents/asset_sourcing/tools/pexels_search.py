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

"""Pexels API integration tool for asset sourcing agent with comprehensive error handling."""

import os
import requests
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from video_system.shared_libraries import (
    APIError,
    NetworkError,
    ValidationError,
    RateLimitError,
    TimeoutError,
    RetryConfig,
    retry_with_exponential_backoff,
    handle_api_errors,
    create_error_response,
    get_logger,
    log_error,
    with_rate_limit
)


class PexelsSearchInput(BaseModel):
    """Input schema for Pexels search tool."""
    query: str = Field(description="The search query for finding images/videos")
    per_page: int = Field(default=15, description="Number of results per page (max 80)")
    media_type: str = Field(default="photos", description="Type of media: 'photos' or 'videos'")
    orientation: str = Field(default="all", description="Image orientation: 'all', 'landscape', 'portrait', 'square'")


# Configure logger and retry settings
logger = get_logger("asset_sourcing.pexels")

pexels_retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)


@with_rate_limit(tokens=1)
@retry_with_exponential_backoff(
    retry_config=pexels_retry_config,
    exceptions=(requests.exceptions.RequestException, APIError, NetworkError),
    logger=logger
)
@handle_api_errors
def _perform_pexels_search(query: str, per_page: int, media_type: str, orientation: str, api_key: str) -> Dict[str, Any]:
    """Internal function to perform Pexels API search with error handling."""
    # Determine API endpoint based on media type
    if media_type == "videos":
        base_url = "https://api.pexels.com/videos/search"
    else:
        base_url = "https://api.pexels.com/v1/search"
    
    headers = {
        "Authorization": api_key
    }
    
    params = {
        "query": query,
        "per_page": min(per_page, 80),  # Pexels API max is 80
        "page": 1
    }
    
    # Add orientation filter for photos only
    if media_type == "photos" and orientation in ["landscape", "portrait", "square"]:
        params["orientation"] = orientation
    
    logger.info(f"Searching Pexels for {media_type}: '{query}' with {per_page} results")
    
    try:
        response = requests.get(
            base_url,
            headers=headers,
            params=params,
            timeout=30
        )
        
        # Handle specific HTTP status codes
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitError(
                "Pexels API rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status_code == 401:
            raise APIError("Invalid Pexels API key", api_name="Pexels", status_code=401)
        elif response.status_code == 403:
            raise APIError("Pexels API access forbidden", api_name="Pexels", status_code=403)
        elif not response.ok:
            raise APIError(
                f"Pexels API returned status {response.status_code}: {response.text}",
                api_name="Pexels",
                status_code=response.status_code
            )
        
        data = response.json()
        logger.info(f"Successfully retrieved {len(data.get('photos' if media_type == 'photos' else 'videos', []))} results from Pexels")
        return data
        
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"Pexels API request timed out: {str(e)}", timeout_duration=30.0)
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"Failed to connect to Pexels API: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Pexels API request failed: {str(e)}", api_name="Pexels")


def search_pexels_media(query: str, per_page: int = 15, media_type: str = "photos", orientation: str = "all") -> Dict[str, Any]:
    """
    Search Pexels for high-quality stock photos and videos with comprehensive error handling.
    
    Args:
        query: The search query for finding media
        per_page: Number of results per page (max 80)
        media_type: Type of media to search for ('photos' or 'videos')
        orientation: Image orientation filter ('all', 'landscape', 'portrait', 'square')
        
    Returns:
        Dict containing search results with media URLs, metadata, and usage rights
    """
    # Input validation
    if not query or not query.strip():
        error = ValidationError("Search query cannot be empty", field="query")
        log_error(logger, error)
        return create_error_response(error)
    
    if not (1 <= per_page <= 80):
        error = ValidationError("per_page must be between 1 and 80", field="per_page")
        log_error(logger, error)
        return create_error_response(error)
    
    if media_type not in ["photos", "videos"]:
        error = ValidationError("media_type must be 'photos' or 'videos'", field="media_type")
        log_error(logger, error)
        return create_error_response(error)
    
    if orientation not in ["all", "landscape", "portrait", "square"]:
        error = ValidationError("orientation must be 'all', 'landscape', 'portrait', or 'square'", field="orientation")
        log_error(logger, error)
        return create_error_response(error)
    
    # Check for API key
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        error = APIError(
            "PEXELS_API_KEY environment variable is not set",
            api_name="Pexels"
        )
        log_error(logger, error)
        return create_error_response(error)
    
    try:
        # Perform the search with error handling and retries
        raw_data = _perform_pexels_search(query.strip(), per_page, media_type, orientation, api_key)
        
        # Format the results
        formatted_results = _format_pexels_results(raw_data, query.strip(), per_page, media_type)
        
        logger.info(f"Pexels search completed successfully for query: '{query}' - {len(formatted_results['results'])} results")
        return formatted_results
        
    except (APIError, NetworkError, TimeoutError, RateLimitError) as e:
        # These are already properly formatted VideoSystemError instances
        log_error(logger, e, {"query": query, "per_page": per_page, "media_type": media_type})
        return create_error_response(e)
    
    except Exception as e:
        # Handle any unexpected errors
        error = APIError(f"Unexpected error during Pexels search: {str(e)}", api_name="Pexels")
        log_error(logger, error, {"query": query, "per_page": per_page, "media_type": media_type})
        return create_error_response(error)


def _format_pexels_results(data: Dict[str, Any], query: str, per_page: int, media_type: str) -> Dict[str, Any]:
    """Format raw Pexels API response into standardized format."""
    results = []
    media_items = data.get("photos" if media_type == "photos" else "videos", [])
    
    for item in media_items:
        if media_type == "videos":
            # Format video results
            video_files = item.get("video_files", [])
            hd_video = next((vf for vf in video_files if vf.get("quality") == "hd"), video_files[0] if video_files else {})
            
            formatted_result = {
                "id": str(item.get("id", "")),
                "url": item.get("url", ""),
                "src": {
                    "large": hd_video.get("link", ""),
                    "medium": hd_video.get("link", ""),
                    "small": hd_video.get("link", "")
                },
                "photographer": item.get("user", {}).get("name", ""),
                "photographer_url": item.get("user", {}).get("url", ""),
                "alt": f"Video by {item.get('user', {}).get('name', 'Unknown')} from Pexels",
                "width": hd_video.get("width", 0),
                "height": hd_video.get("height", 0),
                "duration": item.get("duration", 0),
                "usage_rights": "Free for commercial and personal use. Attribution appreciated but not required.",
                "source": "pexels",
                "media_type": "video"
            }
        else:
            # Format photo results
            formatted_result = {
                "id": str(item.get("id", "")),
                "url": item.get("url", ""),
                "src": {
                    "large": item.get("src", {}).get("large", ""),
                    "medium": item.get("src", {}).get("medium", ""),
                    "small": item.get("src", {}).get("small", "")
                },
                "photographer": item.get("photographer", ""),
                "photographer_url": item.get("photographer_url", ""),
                "alt": item.get("alt", f"Photo by {item.get('photographer', 'Unknown')} from Pexels"),
                "width": item.get("width", 0),
                "height": item.get("height", 0),
                "usage_rights": "Free for commercial and personal use. Attribution appreciated but not required.",
                "source": "pexels",
                "media_type": "image"
            }
        
        results.append(formatted_result)
    
    return {
        "results": results,
        "total_results": data.get("total_results", len(results)),
        "search_query": query,
        "page": data.get("page", 1),
        "per_page": data.get("per_page", per_page),
        "source": "pexels",
        "success": True
    }


def check_pexels_health() -> Dict[str, Any]:
    """Perform a health check on the Pexels API service."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return {
            "status": "unhealthy",
            "details": {"error": "API key not configured"}
        }
    
    try:
        # Perform a simple test search
        test_result = search_pexels_media("test", 1, "photos")
        if test_result.get("success", False):
            return {
                "status": "healthy",
                "details": {"message": "Pexels API is responding normally"}
            }
        else:
            return {
                "status": "degraded",
                "details": {"error": "Pexels API returned error response"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


# Create the tool function for ADK
pexels_search_tool = search_pexels_media