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

"""Pexels API integration tool for asset sourcing agent."""

import os
import requests
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class PexelsSearchInput(BaseModel):
    """Input schema for Pexels search tool."""
    query: str = Field(description="The search query for finding images/videos")
    per_page: int = Field(default=15, description="Number of results per page (max 80)")
    media_type: str = Field(default="photos", description="Type of media: 'photos' or 'videos'")
    orientation: str = Field(default="all", description="Image orientation: 'all', 'landscape', 'portrait', 'square'")


def search_pexels_media(query: str, per_page: int = 15, media_type: str = "photos", orientation: str = "all") -> Dict[str, Any]:
    """
    Search Pexels for high-quality stock photos and videos.
    
    Args:
        query: The search query for finding media
        per_page: Number of results per page (max 80)
        media_type: Type of media to search for ('photos' or 'videos')
        orientation: Image orientation filter ('all', 'landscape', 'portrait', 'square')
        
    Returns:
        Dict containing search results with media URLs, metadata, and usage rights
    """
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return {
            "results": [{
                "id": "error",
                "url": "",
                "src": {"large": "", "medium": "", "small": ""},
                "photographer": "Configuration Error",
                "photographer_url": "",
                "alt": "PEXELS_API_KEY environment variable is not set",
                "usage_rights": "error",
                "source": "pexels"
            }],
            "total_results": 0,
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "pexels"
        }
    
    # Determine API endpoint based on media type
    if media_type == "videos":
        base_url = "https://api.pexels.com/videos/search"
    else:
        base_url = "https://api.pexels.com/v1/search"
    
    try:
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
        
        response = requests.get(
            base_url,
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract and format search results
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
            "source": "pexels"
        }
        
    except requests.exceptions.RequestException as e:
        error_result = {
            "id": "error",
            "url": "",
            "src": {"large": "", "medium": "", "small": ""},
            "photographer": "Search Error",
            "photographer_url": "",
            "alt": f"Failed to search Pexels: {str(e)}",
            "usage_rights": "error",
            "source": "pexels"
        }
        
        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "pexels"
        }
    
    except Exception as e:
        error_result = {
            "id": "error",
            "url": "",
            "src": {"large": "", "medium": "", "small": ""},
            "photographer": "Unexpected Error",
            "photographer_url": "",
            "alt": f"An unexpected error occurred: {str(e)}",
            "usage_rights": "error",
            "source": "pexels"
        }
        
        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "pexels"
        }


# Create the tool function for ADK
pexels_search_tool = search_pexels_media