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

"""Unit tests for the Research Agent and its tools."""

import pytest
from unittest.mock import Mock, patch
import requests
from sub_agents.research.tools.web_search import web_search
from sub_agents.research.agent import research_agent


class TestSerperWebSearchTool:
    """Test cases for the Serper Web Search Tool."""
    
    @pytest.fixture
    def mock_successful_response(self):
        """Mock successful API response."""
        return {
            "organic": [
                {
                    "title": "Climate Change Effects on Agriculture",
                    "link": "https://example.com/climate-agriculture",
                    "snippet": "Climate change significantly impacts agricultural productivity...",
                    "position": 1
                },
                {
                    "title": "Sustainable Farming Practices",
                    "link": "https://example.com/sustainable-farming",
                    "snippet": "Modern sustainable farming techniques help reduce environmental impact...",
                    "position": 2
                }
            ],
            "knowledgeGraph": {
                "title": "Climate Change",
                "website": "https://climate.gov",
                "description": "Long-term shifts in global temperatures and weather patterns"
            },
            "answerBox": {
                "title": "What is Climate Change?",
                "link": "https://epa.gov/climate-change",
                "answer": "Climate change refers to long-term shifts in global temperatures and weather patterns."
            }
        }
    
    def test_tool_without_api_key(self):
        """Test tool behavior without API key."""
        with patch.dict('os.environ', {}, clear=True):
            result = web_search("test query")
            assert result["total_results"] == 0
            assert len(result["results"]) == 1
            assert result["results"][0]["type"] == "error"
            assert "SERPER_API_KEY environment variable is not set" in result["results"][0]["snippet"]
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_api_key'})
    @patch('requests.post')
    def test_successful_search(self, mock_post, mock_successful_response):
        """Test successful web search execution."""
        # Mock the API response
        mock_response = Mock()
        mock_response.json.return_value = mock_successful_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Execute search
        result = web_search("climate change agriculture", num_results=5)
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['q'] == "climate change agriculture"
        assert call_args[1]['json']['num'] == 5
        assert call_args[1]['headers']['X-API-KEY'] == "test_api_key"
        
        # Verify result structure
        assert result["search_query"] == "climate change agriculture"
        assert result["total_results"] == 4  # 2 organic + 1 knowledge graph + 1 answer box
        assert len(result["results"]) == 4
        
        # Verify answer box is first
        assert result["results"][0]['type'] == 'answer_box'
        assert "Climate change refers to" in result["results"][0]['snippet']
        
        # Verify knowledge graph is second
        assert result["results"][1]['type'] == 'knowledge_graph'
        assert result["results"][1]['title'] == "Knowledge Graph: Climate Change"
        
        # Verify organic results
        organic_results = [r for r in result["results"] if 'type' not in r]
        assert len(organic_results) == 2
        assert organic_results[0]['title'] == "Climate Change Effects on Agriculture"
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_api_key'})
    @patch('requests.post')
    def test_search_with_request_exception(self, mock_post):
        """Test search handling when API request fails."""
        # Mock request exception
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        # Execute search
        result = web_search("test query")
        
        # Verify error handling
        assert result["total_results"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]['type'] == 'error'
        assert "Failed to perform web search" in result["results"][0]['snippet']
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_api_key'})
    @patch('requests.post')
    def test_search_with_unexpected_exception(self, mock_post):
        """Test search handling with unexpected exceptions."""
        # Mock unexpected exception
        mock_post.side_effect = Exception("Unexpected error")
        
        # Execute search
        result = web_search("test query")
        
        # Verify error handling
        assert result["total_results"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]['type'] == 'error'
        assert "An unexpected error occurred" in result["results"][0]['snippet']
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_api_key'})
    @patch('requests.post')
    def test_search_with_empty_response(self, mock_post):
        """Test search with empty API response."""
        # Mock empty response
        mock_response = Mock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Execute search
        result = web_search("very specific query with no results")
        
        # Verify result
        assert result["total_results"] == 0
        assert len(result["results"]) == 0
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_api_key'})
    @patch('requests.post')
    def test_num_results_limit(self, mock_post, mock_successful_response):
        """Test that num_results is limited to 10 (Serper API max)."""
        mock_response = Mock()
        mock_response.json.return_value = mock_successful_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Request more than 10 results
        web_search("test query", num_results=15)
        
        # Verify API call limits to 10
        call_args = mock_post.call_args
        assert call_args[1]['json']['num'] == 10


class TestResearchAgent:
    """Test cases for the Research Agent."""
    
    def test_agent_initialization(self):
        """Test that research agent is properly initialized."""
        assert research_agent.name == 'research_agent'
        assert research_agent.model == 'gemini-2.5-pro'
        assert len(research_agent.tools) == 1
        # The tool is now a function, so we check if it's callable
        assert callable(research_agent.tools[0])
    
    def test_agent_instruction_content(self):
        """Test that agent has proper instructions."""
        instruction = research_agent.instruction
        assert "Research Agent" in instruction
        assert "web searches" in instruction
        assert "credible sources" in instruction
        assert "structured format" in instruction
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_key'})
    def test_agent_tool_integration(self):
        """Test that agent properly integrates with web search tool."""
        # Verify tool is accessible and callable
        web_search_tool = research_agent.tools[0]
        assert callable(web_search_tool)
        
        # Test that the tool can be called
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"organic": []}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            result = web_search_tool("test query")
            assert "search_query" in result
            assert "results" in result
            assert "total_results" in result


class TestResearchWorkflow:
    """Integration tests for research workflow."""
    
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test_key'})
    @patch('requests.post')
    def test_research_workflow_integration(self, mock_post):
        """Test complete research workflow with mocked API."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Renewable Energy Trends 2024",
                    "link": "https://energy.gov/renewable-trends",
                    "snippet": "Renewable energy adoption continues to grow globally with solar and wind leading the transformation...",
                    "position": 1
                },
                {
                    "title": "Solar Panel Efficiency Improvements",
                    "link": "https://solar-tech.com/efficiency",
                    "snippet": "New renewable energy technologies achieve 25% efficiency rates in solar panels...",
                    "position": 2
                }
            ],
            "knowledgeGraph": {
                "title": "Renewable Energy",
                "website": "https://renewable-energy.org",
                "description": "Energy from sources that are naturally replenishing"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test that the research agent can be used for a typical research task
        web_search_tool = research_agent.tools[0]
        result = web_search_tool("renewable energy trends 2024")
        
        # Verify research results are structured properly
        assert result["total_results"] > 0
        assert any("renewable energy" in r['snippet'].lower() for r in result["results"])
        assert any("solar" in r['snippet'].lower() for r in result["results"])
        
        # Verify sources are included
        assert all('link' in result for result in result["results"])
        assert all('title' in result for result in result["results"])


if __name__ == "__main__":
    pytest.main([__file__])