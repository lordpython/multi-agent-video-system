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

"""Pixabay API integration tool for asset sourcing agent."""

import os
import requests
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class PixabaySearchInput(BaseModel):
    """Input schema for Pixabay search tool."""
    query: str = Field(description="The search query for finding images/videos")
    per_page: int = Field(default=15, description="Number of results per page (max 200)")
    media_type: str = Field(default="photo", description="Type of media: 'photo', 'illustration', 'vector', 'video'")
    orientation: str = Field(default="all", description="Image orientation: 'all', 'horizontal', 'vertical'")
    category: str = Field(default="", description="Image category filter")


def search_pixabay_media(query: str, per_page: int = 15, media_type: str = "photo", orientation: str = "all", category: str = "") -> Dict[str, Any]:
    """
    Search Pixabay for high-quality stock photos, illustrations, vectors, and videos.
    
    Args:
        query: The search query for finding media
        per_page: Number of results per page (max 200)
        media_type: Type of media to search for ('photo', 'illustration', 'vector', 'video')
        orientation: Image orientation filter ('all', 'horizontal', 'vertical')
        category: Category filter for images
        
    Returns:
        Dict containing search results with media URLs, metadata, and usage rights
    """
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        return {
            "results": [{
                "id": "error",
                "webformatURL": "",
                "largeImageURL": "",
                "previewURL": "",
                "user": "Configuration Error",
                "userImageURL": "",
                "tags": "PIXABAY_API_KEY environment variable is not set",
                "usage_rights": "error",
                "source": "pixabay"
            }],
            "total_results": 0,
            "search_query": query,
            "per_page": per_page,
            "source": "pixabay"
        }
    
    # Determine API endpoint based on media type
    if media_type == "video":
        base_url = "https://pixabay.com/api/videos/"
    else:
        base_url = "https://pixabay.com/api/"
    
    try:
        params = {
            "key": api_key,
            "q": query,
            "per_page": min(per_page, 200),  # Pixabay API max is 200
            "safesearch": "true",
            "page": 1
        }
        
        # Add media type filter for images
        if media_type in ["photo", "illustration", "vector"]:
            params["image_type"] = media_type
        
        # Add orientation filter
        if orientation in ["horizontal", "vertical"]:
            params["orientation"] = orientation
        
        # Add category filter if specified
        if category:
            params["category"] = category
        
        response = requests.get(
            base_url,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract and format search results
        results = []
        hits = data.get("hits", [])
        
        for item in hits:
            if media_type == "video":
                # Format video results
                videos = item.get("videos", {})
                large_video = videos.get("large", {}) or videos.get("medium", {}) or videos.get("small", {})
                
                formatted_result = {
                    "id": str(item.get("id", "")),
                    "pageURL": item.get("pageURL", ""),
                    "webformatURL": large_video.get("url", ""),
                    "largeImageURL": large_video.get("url", ""),
                    "previewURL": item.get("picture_id", ""),
                    "user": item.get("user", ""),
                    "userImageURL": item.get("userImageURL", ""),
                    "tags": item.get("tags", ""),
                    "duration": item.get("duration", 0),
                    "views": item.get("views", 0),
                    "downloads": item.get("downloads", 0),
                    "favorites": item.get("favorites", 0),
                    "video_size": {
                        "width": large_video.get("width", 0),
                        "height": large_video.get("height", 0),
                        "size": large_video.get("size", 0)
                    },
                    "usage_rights": "Free for commercial and personal use. No attribution required, but appreciated.",
                    "source": "pixabay",
                    "media_type": "video"
                }
            else:
                # Format image results
                formatted_result = {
                    "id": str(item.get("id", "")),
                    "pageURL": item.get("pageURL", ""),
                    "webformatURL": item.get("webformatURL", ""),
                    "largeImageURL": item.get("largeImageURL", item.get("fullHDURL", item.get("webformatURL", ""))),
                    "previewURL": item.get("previewURL", ""),
                    "user": item.get("user", ""),
                    "userImageURL": item.get("userImageURL", ""),
                    "tags": item.get("tags", ""),
                    "type": item.get("type", media_type),
                    "views": item.get("views", 0),
                    "downloads": item.get("downloads", 0),
                    "favorites": item.get("favorites", 0),
                    "likes": item.get("likes", 0),
                    "comments": item.get("comments", 0),
                    "imageSize": item.get("imageSize", 0),
                    "imageWidth": item.get("imageWidth", 0),
                    "imageHeight": item.get("imageHeight", 0),
                    "webformatWidth": item.get("webformatWidth", 0),
                    "webformatHeight": item.get("webformatHeight", 0),
                    "usage_rights": "Free for commercial and personal use. No attribution required, but appreciated.",
                    "source": "pixabay",
                    "media_type": "image"
                }
            
            results.append(formatted_result)
        
        return {
            "results": results,
            "total_results": data.get("total", len(results)),
            "search_query": query,
            "per_page": per_page,
            "source": "pixabay"
        }
        
    except requests.exceptions.RequestException as e:
        error_result = {
            "id": "error",
            "webformatURL": "",
            "largeImageURL": "",
            "previewURL": "",
            "user": "Search Error",
            "userImageURL": "",
            "tags": f"Failed to search Pixabay: {str(e)}",
            "usage_rights": "error",
            "source": "pixabay"
        }
        
        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query,
            "per_page": per_page,
            "source": "pixabay"
        }
    
    except Exception as e:
        error_result = {
            "id": "error",
            "webformatURL": "",
            "largeImageURL": "",
            "previewURL": "",
            "user": "Unexpected Error",
            "userImageURL": "",
            "tags": f"An unexpected error occurred: {str(e)}",
            "usage_rights": "error",
            "source": "pixabay"
        }
        
        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query,
            "per_page": per_page,
            "source": "pixabay"
        }


# Create the tool function for ADK
pixabay_search_tool = search_pixabay_media