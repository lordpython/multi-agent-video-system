"""Research tools module.

This module provides research tools for the research agent.
"""

from typing import Dict, Any
from google.adk.tools import FunctionTool

def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    Search the web for information using Serper API.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        Dict containing search results
    """
    # Mock implementation for testing
    results = [
        {
            "title": f"Result {i} for {query}",
            "link": f"https://example.com/result{i}",
            "snippet": f"This is result {i} about {query}",
            "position": i
        }
        for i in range(1, min(num_results + 1, 11))
    ]
    
    return {
        "results": results,
        "total_results": len(results),
        "search_query": query,
        "success": True
    }

# Create FunctionTool object
serper_web_search_tool = FunctionTool(web_search)

__all__ = [
    "serper_web_search_tool",
]