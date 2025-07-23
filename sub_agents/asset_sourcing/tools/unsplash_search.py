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

"""Unsplash API integration tool for asset sourcing agent."""

import os
import requests
from typing import Dict, Any
from pydantic import BaseModel, Field


class UnsplashSearchInput(BaseModel):
    """Input schema for Unsplash search tool."""

    query: str = Field(description="The search query for finding images")
    per_page: int = Field(default=15, description="Number of results per page (max 30)")
    orientation: str = Field(
        default="all",
        description="Image orientation: 'all', 'landscape', 'portrait', 'squarish'",
    )
    color: str = Field(
        default="any",
        description="Color filter: 'any', 'black_and_white', 'black', 'white', 'yellow', 'orange', 'red', 'purple', 'magenta', 'green', 'teal', 'blue'",
    )


def search_unsplash_photos(
    query: str, per_page: int = 15, orientation: str = "all", color: str = "any"
) -> Dict[str, Any]:
    """
    Search Unsplash for high-quality stock photos.

    Args:
        query: The search query for finding images
        per_page: Number of results per page (max 30)
        orientation: Image orientation filter ('all', 'landscape', 'portrait', 'squarish')
        color: Color filter for images

    Returns:
        Dict containing search results with image URLs, metadata, and usage rights
    """
    api_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not api_key:
        return {
            "results": [
                {
                    "id": "error",
                    "urls": {
                        "raw": "",
                        "full": "",
                        "regular": "",
                        "small": "",
                        "thumb": "",
                    },
                    "user": {
                        "name": "Configuration Error",
                        "username": "",
                        "links": {"html": ""},
                    },
                    "alt_description": "UNSPLASH_ACCESS_KEY environment variable is not set",
                    "description": "API key configuration error",
                    "usage_rights": "error",
                    "source": "unsplash",
                }
            ],
            "total_results": 0,
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "unsplash",
        }

    base_url = "https://api.unsplash.com/search/photos"

    try:
        headers = {"Authorization": f"Client-ID {api_key}"}

        params = {
            "query": query,
            "per_page": min(per_page, 30),  # Unsplash API max is 30
            "page": 1,
        }

        # Add orientation filter if specified
        if orientation in ["landscape", "portrait", "squarish"]:
            params["orientation"] = orientation

        # Add color filter if specified
        if color != "any":
            params["color"] = color

        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Extract and format search results
        results = []
        photos = data.get("results", [])

        for photo in photos:
            user_info = photo.get("user", {})
            urls = photo.get("urls", {})

            formatted_result = {
                "id": photo.get("id", ""),
                "urls": {
                    "raw": urls.get("raw", ""),
                    "full": urls.get("full", ""),
                    "regular": urls.get("regular", ""),
                    "small": urls.get("small", ""),
                    "thumb": urls.get("thumb", ""),
                },
                "user": {
                    "name": user_info.get("name", ""),
                    "username": user_info.get("username", ""),
                    "links": {"html": user_info.get("links", {}).get("html", "")},
                },
                "alt_description": photo.get(
                    "alt_description",
                    photo.get(
                        "description",
                        f"Photo by {user_info.get('name', 'Unknown')} on Unsplash",
                    ),
                ),
                "description": photo.get("description", ""),
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
                "color": photo.get("color", "#000000"),
                "blur_hash": photo.get("blur_hash", ""),
                "likes": photo.get("likes", 0),
                "download_url": urls.get("full", ""),
                "usage_rights": "Free for commercial and personal use. Attribution required: Photo by [photographer] on Unsplash",
                "source": "unsplash",
                "media_type": "image",
            }

            results.append(formatted_result)

        return {
            "results": results,
            "total_results": data.get("total", len(results)),
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "unsplash",
        }

    except requests.exceptions.RequestException as e:
        error_result = {
            "id": "error",
            "urls": {"raw": "", "full": "", "regular": "", "small": "", "thumb": ""},
            "user": {"name": "Search Error", "username": "", "links": {"html": ""}},
            "alt_description": f"Failed to search Unsplash: {str(e)}",
            "description": "Search request failed",
            "usage_rights": "error",
            "source": "unsplash",
        }

        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "unsplash",
        }

    except Exception as e:
        error_result = {
            "id": "error",
            "urls": {"raw": "", "full": "", "regular": "", "small": "", "thumb": ""},
            "user": {"name": "Unexpected Error", "username": "", "links": {"html": ""}},
            "alt_description": f"An unexpected error occurred: {str(e)}",
            "description": "Unexpected error during search",
            "usage_rights": "error",
            "source": "unsplash",
        }

        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query,
            "page": 1,
            "per_page": per_page,
            "source": "unsplash",
        }


from google.adk.tools import FunctionTool

# Create the tool function for ADK
unsplash_search_tool = FunctionTool(search_unsplash_photos)
