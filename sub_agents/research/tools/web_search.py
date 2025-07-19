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

"""Web search tool using Serper API for research agent with comprehensive error handling."""

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


class SerperSearchInput(BaseModel):
    """Input schema for Serper search tool."""
    query: str = Field(description="The search query to execute")
    num_results: int = Field(default=10, description="Number of search results to return (max 10)")


# Configure logger for this module
logger = get_logger("research.web_search")

# Configure retry behavior for web search
search_retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)


@with_rate_limit(tokens=1)
@retry_with_exponential_backoff(
    retry_config=search_retry_config,
    exceptions=(requests.exceptions.RequestException, APIError, NetworkError),
    logger=logger
)
@handle_api_errors
def _perform_serper_search(query: str, num_results: int, api_key: str) -> Dict[str, Any]:
    """
    Internal function to perform the actual Serper API search with error handling.
    
    Args:
        query: The search query to execute
        num_results: Number of search results to return
        api_key: Serper API key
        
    Returns:
        Dict containing search results
        
    Raises:
        APIError: For API-related errors
        NetworkError: For network-related errors
        TimeoutError: For timeout errors
        RateLimitError: For rate limiting errors
    """
    base_url = "https://google.serper.dev/search"
    
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": query,
        "num": min(num_results, 10)  # Serper API max is 10
    }
    
    logger.info(f"Performing web search for query: '{query}' with {num_results} results")
    
    try:
        response = requests.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Handle specific HTTP status codes
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitError(
                "Serper API rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status_code == 401:
            raise APIError("Invalid Serper API key", api_name="Serper", status_code=401)
        elif response.status_code == 403:
            raise APIError("Serper API access forbidden", api_name="Serper", status_code=403)
        elif not response.ok:
            raise APIError(
                f"Serper API returned status {response.status_code}: {response.text}",
                api_name="Serper",
                status_code=response.status_code
            )
        
        data = response.json()
        logger.info(f"Successfully retrieved search results for query: '{query}'")
        return data
        
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"Serper API request timed out: {str(e)}", timeout_duration=30.0)
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"Failed to connect to Serper API: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Serper API request failed: {str(e)}", api_name="Serper")


def _format_search_results(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Format the raw Serper API response into a standardized format.
    
    Args:
        data: Raw response from Serper API
        query: Original search query
        
    Returns:
        Formatted search results
    """
    results = []
    organic_results = data.get("organic", [])
    
    # Process organic search results
    for result in organic_results:
        formatted_result = {
            "title": result.get("title", ""),
            "link": result.get("link", ""),
            "snippet": result.get("snippet", ""),
            "position": result.get("position", 0),
            "type": "organic"
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
    
    # Include related searches if available
    related_searches = []
    if "relatedSearches" in data:
        for related in data["relatedSearches"]:
            related_searches.append(related.get("query", ""))
    
    return {
        "results": results,
        "total_results": len(results),
        "search_query": query,
        "related_searches": related_searches,
        "success": True
    }


def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    Search the web for information on a given topic using Serper API with comprehensive error handling.
    
    Args:
        query: The search query to execute
        num_results: Number of search results to return (max 10)
        
    Returns:
        Dict containing search results, total_results, search_query, and success status
    """
    # Input validation
    if not query or not query.strip():
        error = ValidationError("Search query cannot be empty", field="query")
        log_error(logger, error)
        return create_error_response(error)
    
    if num_results < 1 or num_results > 10:
        error = ValidationError("Number of results must be between 1 and 10", field="num_results")
        log_error(logger, error)
        return create_error_response(error)
    
    # Check for API key
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        error = APIError(
            "SERPER_API_KEY environment variable is not set",
            api_name="Serper"
        )
        log_error(logger, error)
        return create_error_response(error)
    
    try:
        # Perform the search with error handling and retries
        raw_data = _perform_serper_search(query.strip(), num_results, api_key)
        
        # Format the results
        formatted_results = _format_search_results(raw_data, query.strip())
        
        logger.info(f"Web search completed successfully for query: '{query}' - {len(formatted_results['results'])} results")
        return formatted_results
        
    except (APIError, NetworkError, TimeoutError, RateLimitError) as e:
        # These are already properly formatted VideoSystemError instances
        log_error(logger, e, {"query": query, "num_results": num_results})
        return create_error_response(e)
    
    except Exception as e:
        # Handle any unexpected errors
        error = APIError(f"Unexpected error during web search: {str(e)}", api_name="Serper")
        log_error(logger, error, {"query": query, "num_results": num_results})
        return create_error_response(error)


def search_with_fallback(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    Search with fallback to alternative search strategies if primary search fails.
    
    Args:
        query: The search query to execute
        num_results: Number of search results to return
        
    Returns:
        Dict containing search results or fallback response
    """
    try:
        # Try primary search
        return web_search(query, num_results)
    except Exception as e:
        logger.warning(f"Primary web search failed, attempting fallback: {str(e)}")
        
        # Fallback: Try with simplified query
        try:
            simplified_query = " ".join(query.split()[:5])  # Take first 5 words
            logger.info(f"Attempting fallback search with simplified query: '{simplified_query}'")
            return web_search(simplified_query, min(num_results, 5))
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {str(fallback_error)}")
            
            # Return graceful degradation response
            return {
                "results": [{
                    "title": "Search Temporarily Unavailable",
                    "link": "",
                    "snippet": "Web search is temporarily unavailable. Please try again later.",
                    "position": 0,
                    "type": "fallback"
                }],
                "total_results": 0,
                "search_query": query,
                "success": False,
                "fallback_response": True,
                "error": "All search attempts failed"
            }


# Health check function for the web search service
def check_serper_health() -> Dict[str, Any]:
    """
    Perform a health check on the Serper API service.
    
    Returns:
        Dict containing health status
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {
            "status": "unhealthy",
            "details": {"error": "API key not configured"}
        }
    
    try:
        # Perform a simple test search
        test_result = web_search("test", 1)
        if test_result.get("success", False):
            return {
                "status": "healthy",
                "details": {"message": "Serper API is responding normally"}
            }
        else:
            return {
                "status": "degraded",
                "details": {"error": "Serper API returned error response"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


# Create the tool function for ADK
serper_web_search_tool = web_search