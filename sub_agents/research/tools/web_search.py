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

"""Web search tool using Serper API for research agent."""

import os
import requests
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class SerperSearchInput(BaseModel):
    """Input schema for Serper search tool."""
    query: str = Field(description="The search query to execute")
    num_results: int = Field(default=10, description="Number of search results to return (max 10)")


def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    Search the web for information on a given topic using Serper API.
    
    Args:
        query: The search query to execute
        num_results: Number of search results to return (max 10)
        
    Returns:
        Dict containing search results, total_results, and search_query
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {
            "results": [{
                "title": "Configuration Error",
                "link": "",
                "snippet": "SERPER_API_KEY environment variable is not set",
                "position": 0,
                "type": "error"
            }],
            "total_results": 0,
            "search_query": query
        }
    
    base_url = "https://google.serper.dev/search"
    
    try:
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": min(num_results, 10)  # Serper API max is 10
        }
        
        response = requests.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract and format search results
        results = []
        organic_results = data.get("organic", [])
        
        for result in organic_results:
            formatted_result = {
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "position": result.get("position", 0)
            }
            results.append(formatted_result)
        
        # Include knowledge graph if available
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            knowledge_result = {
                "title": f"Knowledge Graph: {kg.get('title', '')}",
                "link": kg.get("website", ""),
                "snippet": kg.get("description", ""),
                "position": 0,
                "type": "knowledge_graph"
            }
            results.insert(0, knowledge_result)
        
        # Include answer box if available
        if "answerBox" in data:
            answer = data["answerBox"]
            answer_result = {
                "title": f"Answer: {answer.get('title', '')}",
                "link": answer.get("link", ""),
                "snippet": answer.get("snippet", "") or answer.get("answer", ""),
                "position": 0,
                "type": "answer_box"
            }
            results.insert(0, answer_result)
        
        return {
            "results": results,
            "total_results": len(results),
            "search_query": query
        }
        
    except requests.exceptions.RequestException as e:
        # Return error information in a structured way
        error_result = {
            "title": "Search Error",
            "link": "",
            "snippet": f"Failed to perform web search: {str(e)}",
            "position": 0,
            "type": "error"
        }
        
        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query
        }
    
    except Exception as e:
        # Handle any other unexpected errors
        error_result = {
            "title": "Unexpected Error",
            "link": "",
            "snippet": f"An unexpected error occurred: {str(e)}",
            "position": 0,
            "type": "error"
        }
        
        return {
            "results": [error_result],
            "total_results": 0,
            "search_query": query
        }


# Create the tool function for ADK
serper_web_search_tool = web_search