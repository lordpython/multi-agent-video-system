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

"""Unit tests for the Asset Sourcing Agent and its tools."""

import pytest
from unittest.mock import Mock, patch
import requests
from sub_agents.asset_sourcing.tools.pexels_search import search_pexels_media
from sub_agents.asset_sourcing.tools.unsplash_search import search_unsplash_photos
from sub_agents.asset_sourcing.tools.pixabay_search import search_pixabay_media
from sub_agents.asset_sourcing.agent import asset_sourcing_agent


class TestPexelsSearchTool:
    """Test cases for the Pexels Search Tool."""
    
    @pytest.fixture
    def mock_pexels_photos_response(self):
        """Mock successful Pexels photos API response."""
        return {
            "total_results": 100,
            "page": 1,
            "per_page": 15,
            "photos": [
                {
                    "id": 123456,
                    "width": 1920,
                    "height": 1080,
                    "url": "https://www.pexels.com/photo/test-photo-123456/",
                    "photographer": "John Doe",
                    "photographer_url": "https://www.pexels.com/@johndoe",
                    "photographer_id": 12345,
                    "avg_color": "#2C5F41",
                    "src": {
                        "original": "https://images.pexels.com/photos/123456/original.jpg",
                        "large2x": "https://images.pexels.com/photos/123456/large2x.jpg",
                        "large": "https://images.pexels.com/photos/123456/large.jpg",
                        "medium": "https://images.pexels.com/photos/123456/medium.jpg",
                        "small": "https://images.pexels.com/photos/123456/small.jpg",
                        "portrait": "https://images.pexels.com/photos/123456/portrait.jpg",
                        "landscape": "https://images.pexels.com/photos/123456/landscape.jpg",
                        "tiny": "https://images.pexels.com/photos/123456/tiny.jpg"
                    },
                    "liked": False,
                    "alt": "Beautiful landscape with mountains and trees"
                }
            ]
        }
    
    @pytest.fixture
    def mock_pexels_videos_response(self):
        """Mock successful Pexels videos API response."""
        return {
            "total_results": 50,
            "page": 1,
            "per_page": 15,
            "videos": [
                {
                    "id": 789012,
                    "width": 1920,
                    "height": 1080,
                    "duration": 30,
                    "full_res": None,
                    "tags": ["nature", "landscape", "mountains"],
                    "url": "https://www.pexels.com/video/test-video-789012/",
                    "image": "https://images.pexels.com/videos/789012/preview.jpg",
                    "avg_color": None,
                    "user": {
                        "id": 67890,
                        "name": "Jane Smith",
                        "url": "https://www.pexels.com/@janesmith"
                    },
                    "video_files": [
                        {
                            "id": 112233,
                            "quality": "hd",
                            "file_type": "video/mp4",
                            "width": 1920,
                            "height": 1080,
                            "fps": 30.0,
                            "link": "https://player.vimeo.com/external/test.mp4"
                        }
                    ]
                }
            ]
        }
    
    def test_pexels_search_without_api_key(self):
        """Test Pexels search behavior without API key."""
        with patch.dict('os.environ', {}, clear=True):
            result = search_pexels_media("test query")
            assert result["total_results"] == 0
            assert len(result["results"]) == 1
            assert result["results"][0]["usage_rights"] == "error"
            assert "PEXELS_API_KEY environment variable is not set" in result["results"][0]["alt"]
    
    @patch.dict('os.environ', {'PEXELS_API_KEY': 'test_api_key'})
    @patch('requests.get')
    def test_pexels_photos_search_success(self, mock_get, mock_pexels_photos_response):
        """Test successful Pexels photos search."""
        mock_response = Mock()
        mock_response.json.return_value = mock_pexels_photos_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_pexels_media("mountains", per_page=15, media_type="photos")
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "mountains" in call_args[1]['params']['query']
        assert call_args[1]['params']['per_page'] == 15
        assert call_args[1]['headers']['Authorization'] == "test_api_key"
        
        # Verify result structure
        assert result["total_results"] == 100
        assert result["source"] == "pexels"
        assert len(result["results"]) == 1
        
        # Verify asset structure
        asset = result["results"][0]
        assert asset["id"] == "123456"
        assert asset["media_type"] == "image"
        assert asset["source"] == "pexels"
        assert asset["alt"] == "Beautiful landscape with mountains and trees"
        assert "Free for commercial and personal use" in asset["usage_rights"]
        assert asset["photographer"] == "John Doe"
        assert "large" in asset["src"]
    
    @patch.dict('os.environ', {'PEXELS_API_KEY': 'test_api_key'})
    @patch('requests.get')
    def test_pexels_videos_search_success(self, mock_get, mock_pexels_videos_response):
        """Test successful Pexels videos search."""
        mock_response = Mock()
        mock_response.json.return_value = mock_pexels_videos_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_pexels_media("nature", media_type="videos")
        
        # Verify result structure
        assert result["source"] == "pexels"
        assert len(result["results"]) == 1
        
        # Verify video asset structure
        asset = result["results"][0]
        assert asset["id"] == "789012"
        assert asset["media_type"] == "video"
        assert asset["duration"] == 30
        assert "large" in asset["src"]
    
    @patch.dict('os.environ', {'PEXELS_API_KEY': 'test_api_key'})
    @patch('requests.get')
    def test_pexels_search_with_request_exception(self, mock_get):
        """Test Pexels search handling when API request fails."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = search_pexels_media("test query")
        
        assert result["total_results"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]["usage_rights"] == "error"
        assert "Failed to search Pexels" in result["results"][0]["alt"]
    
    @patch.dict('os.environ', {'PEXELS_API_KEY': 'test_api_key'})
    @patch('requests.get')
    def test_pexels_search_empty_response(self, mock_get):
        """Test Pexels search with empty response."""
        mock_response = Mock()
        mock_response.json.return_value = {"photos": [], "total_results": 0}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_pexels_media("very specific query with no results")
        
        assert result["total_results"] == 0
        assert len(result["results"]) == 0


class TestUnsplashSearchTool:
    """Test cases for the Unsplash Search Tool."""
    
    @pytest.fixture
    def mock_unsplash_response(self):
        """Mock successful Unsplash API response."""
        return {
            "total": 200,
            "total_pages": 14,
            "results": [
                {
                    "id": "abc123",
                    "slug": "beautiful-sunset-abc123",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-02T00:00:00Z",
                    "promoted_at": None,
                    "width": 4000,
                    "height": 3000,
                    "color": "#2C5F41",
                    "blur_hash": "LGF5]+Yk^6#M@-5c,1J5@[or[Q6.",
                    "description": "A beautiful sunset over the ocean",
                    "alt_description": "sunset over ocean waves",
                    "urls": {
                        "raw": "https://images.unsplash.com/photo-abc123?ixid=raw",
                        "full": "https://images.unsplash.com/photo-abc123?ixid=full",
                        "regular": "https://images.unsplash.com/photo-abc123?ixid=regular",
                        "small": "https://images.unsplash.com/photo-abc123?ixid=small",
                        "thumb": "https://images.unsplash.com/photo-abc123?ixid=thumb",
                        "small_s3": "https://s3.us-west-2.amazonaws.com/images.unsplash.com/small/photo-abc123"
                    },
                    "links": {
                        "self": "https://api.unsplash.com/photos/abc123",
                        "html": "https://unsplash.com/photos/abc123",
                        "download": "https://unsplash.com/photos/abc123/download",
                        "download_location": "https://api.unsplash.com/photos/abc123/download"
                    },
                    "likes": 150,
                    "liked_by_user": False,
                    "user": {
                        "id": "user123",
                        "username": "photographer123",
                        "name": "Amazing Photographer",
                        "first_name": "Amazing",
                        "last_name": "Photographer",
                        "twitter_username": "photographer123",
                        "portfolio_url": "https://example.com",
                        "bio": "Professional photographer",
                        "location": "California, USA",
                        "links": {
                            "self": "https://api.unsplash.com/users/photographer123",
                            "html": "https://unsplash.com/@photographer123",
                            "photos": "https://api.unsplash.com/users/photographer123/photos"
                        }
                    }
                }
            ]
        }
    
    def test_unsplash_search_without_api_key(self):
        """Test Unsplash search behavior without API key."""
        with patch.dict('os.environ', {}, clear=True):
            result = search_unsplash_photos("test query")
            assert result["total_results"] == 0
            assert len(result["results"]) == 1
            assert result["results"][0]["usage_rights"] == "error"
            assert "UNSPLASH_ACCESS_KEY environment variable is not set" in result["results"][0]["alt_description"]
    
    @patch.dict('os.environ', {'UNSPLASH_ACCESS_KEY': 'test_access_key'})
    @patch('requests.get')
    def test_unsplash_search_success(self, mock_get, mock_unsplash_response):
        """Test successful Unsplash search."""
        mock_response = Mock()
        mock_response.json.return_value = mock_unsplash_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_unsplash_photos("sunset", per_page=15, orientation="landscape")
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['query'] == "sunset"
        assert call_args[1]['params']['per_page'] == 15
        assert call_args[1]['params']['orientation'] == "landscape"
        assert call_args[1]['headers']['Authorization'] == "Client-ID test_access_key"
        
        # Verify result structure
        assert result["total_results"] == 200
        assert result["source"] == "unsplash"
        assert len(result["results"]) == 1
        
        # Verify asset structure
        asset = result["results"][0]
        assert asset["id"] == "abc123"
        assert asset["media_type"] == "image"
        assert asset["source"] == "unsplash"
        assert asset["alt_description"] == "A beautiful sunset over the ocean"
        assert "Free for commercial and personal use" in asset["usage_rights"]
        assert asset["photographer"] == "Amazing Photographer"
        assert "large" in asset["src"]
    
    @patch.dict('os.environ', {'UNSPLASH_ACCESS_KEY': 'test_access_key'})
    @patch('requests.get')
    def test_unsplash_search_with_color_filter(self, mock_get, mock_unsplash_response):
        """Test Unsplash search with color filter."""
        mock_response = Mock()
        mock_response.json.return_value = mock_unsplash_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_unsplash_photos("nature", color="green")
        
        # Verify color parameter is included
        call_args = mock_get.call_args
        assert call_args[1]['params']['color'] == "green"
        assert result["source"] == "unsplash"


class TestPixabaySearchTool:
    """Test cases for the Pixabay Search Tool."""
    
    @pytest.fixture
    def mock_pixabay_photos_response(self):
        """Mock successful Pixabay photos API response."""
        return {
            "total": 500,
            "totalHits": 500,
            "hits": [
                {
                    "id": 987654,
                    "pageURL": "https://pixabay.com/photos/landscape-mountains-987654/",
                    "type": "photo",
                    "tags": "landscape, mountains, nature",
                    "previewURL": "https://cdn.pixabay.com/photo/987654_150.jpg",
                    "previewWidth": 150,
                    "previewHeight": 100,
                    "webformatURL": "https://pixabay.com/get/987654_640.jpg",
                    "webformatWidth": 640,
                    "webformatHeight": 427,
                    "largeImageURL": "https://pixabay.com/get/987654_1280.jpg",
                    "fullHDURL": "https://pixabay.com/get/987654_1920.jpg",
                    "vectorURL": "",
                    "views": 1000,
                    "downloads": 500,
                    "favorites": 50,
                    "likes": 100,
                    "comments": 10,
                    "user_id": 12345,
                    "user": "nature_lover",
                    "userImageURL": "https://cdn.pixabay.com/user/2023/01/01/profile.jpg"
                }
            ]
        }
    
    @pytest.fixture
    def mock_pixabay_videos_response(self):
        """Mock successful Pixabay videos API response."""
        return {
            "total": 100,
            "totalHits": 100,
            "hits": [
                {
                    "id": 456789,
                    "pageURL": "https://pixabay.com/videos/ocean-waves-456789/",
                    "type": "film",
                    "tags": "ocean, waves, water",
                    "duration": 25,
                    "picture_id": "987654_1280.jpg",
                    "videos": {
                        "large": {
                            "url": "https://player.vimeo.com/external/large.mp4",
                            "width": 1920,
                            "height": 1080,
                            "size": 15000000
                        },
                        "medium": {
                            "url": "https://player.vimeo.com/external/medium.mp4",
                            "width": 1280,
                            "height": 720,
                            "size": 8000000
                        },
                        "small": {
                            "url": "https://player.vimeo.com/external/small.mp4",
                            "width": 640,
                            "height": 360,
                            "size": 3000000
                        },
                        "tiny": {
                            "url": "https://player.vimeo.com/external/tiny.mp4",
                            "width": 480,
                            "height": 270,
                            "size": 1500000
                        }
                    },
                    "views": 2000,
                    "downloads": 100,
                    "favorites": 25,
                    "likes": 75,
                    "user_id": 67890,
                    "user": "video_creator",
                    "userImageURL": "https://cdn.pixabay.com/user/2023/01/01/profile2.jpg"
                }
            ]
        }
    
    def test_pixabay_search_without_api_key(self):
        """Test Pixabay search behavior without API key."""
        with patch.dict('os.environ', {}, clear=True):
            result = search_pixabay_media("test query")
            assert result["total_results"] == 0
            assert len(result["results"]) == 1
            assert result["results"][0]["usage_rights"] == "error"
            assert "PIXABAY_API_KEY environment variable is not set" in result["results"][0]["tags"]
    
    @patch.dict('os.environ', {'PIXABAY_API_KEY': 'test_api_key'})
    @patch('requests.get')
    def test_pixabay_photos_search_success(self, mock_get, mock_pixabay_photos_response):
        """Test successful Pixabay photos search."""
        mock_response = Mock()
        mock_response.json.return_value = mock_pixabay_photos_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_pixabay_media("mountains", media_type="photo", category="nature")
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['q'] == "mountains"
        assert call_args[1]['params']['image_type'] == "photo"
        assert call_args[1]['params']['category'] == "nature"
        assert call_args[1]['params']['key'] == "test_api_key"
        
        # Verify result structure
        assert result["total_results"] == 500
        assert result["source"] == "pixabay"
        assert len(result["results"]) == 1
        
        # Verify asset structure
        asset = result["results"][0]
        assert asset["id"] == "987654"
        assert asset["media_type"] == "image"
        assert asset["source"] == "pixabay"
        assert "landscape, mountains, nature" in asset["tags"]
        assert "Free for commercial and personal use" in asset["usage_rights"]
        assert "largeImageURL" in asset
    
    @patch.dict('os.environ', {'PIXABAY_API_KEY': 'test_api_key'})
    @patch('requests.get')
    def test_pixabay_videos_search_success(self, mock_get, mock_pixabay_videos_response):
        """Test successful Pixabay videos search."""
        mock_response = Mock()
        mock_response.json.return_value = mock_pixabay_videos_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = search_pixabay_media("ocean", media_type="video")
        
        # Verify result structure
        assert result["total_results"] > 0
        assert result["source"] == "pixabay"
        assert len(result["results"]) == 1
        
        # Verify video asset structure
        asset = result["results"][0]
        assert asset["id"] == "456789"
        assert asset["media_type"] == "video"
        assert asset["source"] == "pixabay"
        assert asset["duration"] == 25
        assert "largeImageURL" in asset


class TestAssetSourcingAgent:
    """Test cases for the Asset Sourcing Agent integration."""
    
    def test_asset_sourcing_agent_initialization(self):
        """Test that the asset sourcing agent is properly initialized."""
        assert asset_sourcing_agent.name == "asset_sourcing_agent"
        assert asset_sourcing_agent.model == "gemini-2.5-flash"
        assert len(asset_sourcing_agent.tools) == 3
        
        # Check tool functions
        tool_names = [tool.__name__ for tool in asset_sourcing_agent.tools]
        expected_tools = [
            "search_pexels_media",
            "search_unsplash_photos",
            "search_pixabay_media"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_asset_sourcing_agent_instruction_content(self):
        """Test that the asset sourcing agent has comprehensive instructions."""
        instruction = asset_sourcing_agent.instruction
        
        # Check for key instruction components
        assert "Asset Sourcing Agent" in instruction
        assert "visual" in instruction.lower() and "assets" in instruction.lower()
        assert "visual requirements" in instruction.lower()
        assert "stock media" in instruction.lower()
        assert "pexels" in instruction.lower()
        assert "unsplash" in instruction.lower()
        assert "pixabay" in instruction.lower()


class TestAssetSourcingWorkflow:
    """Integration tests for asset sourcing workflow."""
    
    @patch.dict('os.environ', {
        'PEXELS_API_KEY': 'test_pexels_key',
        'UNSPLASH_ACCESS_KEY': 'test_unsplash_key',
        'PIXABAY_API_KEY': 'test_pixabay_key'
    })
    @patch('requests.get')
    def test_multi_provider_asset_search(self, mock_get):
        """Test asset search across multiple providers."""
        # Mock responses for different providers
        def mock_get_side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            if "pexels.com" in url:
                mock_response.json.return_value = {
                    "photos": [{
                        "id": 123,
                        "width": 1920,
                        "height": 1080,
                        "url": "https://pexels.com/photo/123/",
                        "photographer": "Test Photographer",
                        "photographer_url": "https://pexels.com/@test",
                        "src": {
                            "original": "https://images.pexels.com/123/original.jpg",
                            "large": "https://images.pexels.com/123/large.jpg"
                        },
                        "alt": "Test landscape photo"
                    }],
                    "total_results": 100
                }
            elif "unsplash.com" in url:
                mock_response.json.return_value = {
                    "results": [{
                        "id": "abc123",
                        "description": "Test sunset photo",
                        "alt_description": "beautiful sunset",
                        "urls": {
                            "raw": "https://images.unsplash.com/abc123?raw",
                            "full": "https://images.unsplash.com/abc123?full"
                        },
                        "user": {
                            "name": "Test User",
                            "username": "testuser"
                        },
                        "width": 4000,
                        "height": 3000
                    }],
                    "total": 200
                }
            elif "pixabay.com" in url:
                mock_response.json.return_value = {
                    "hits": [{
                        "id": 987654,
                        "type": "photo",
                        "tags": "nature, landscape",
                        "webformatURL": "https://pixabay.com/get/987654_640.jpg",
                        "largeImageURL": "https://pixabay.com/get/987654_1280.jpg",
                        "user": "nature_lover",
                        "views": 1000,
                        "downloads": 500
                    }],
                    "total": 300
                }
            
            return mock_response
        
        mock_get.side_effect = mock_get_side_effect
        
        # Test searches across all providers
        pexels_result = search_pexels_media("landscape")
        unsplash_result = search_unsplash_photos("sunset")
        pixabay_result = search_pixabay_media("nature")
        
        # Verify all searches succeeded
        assert pexels_result["total_results"] > 0
        assert unsplash_result["total_results"] > 0
        assert pixabay_result["total_results"] > 0
        
        # Verify each provider returned assets
        assert len(pexels_result["results"]) > 0
        assert len(unsplash_result["results"]) > 0
        assert len(pixabay_result["results"]) > 0
        
        # Verify provider-specific properties
        assert pexels_result["results"][0]["source"] == "pexels"
        assert unsplash_result["results"][0]["source"] == "unsplash"
        assert pixabay_result["results"][0]["source"] == "pixabay"
    
    def test_asset_format_standardization(self):
        """Test that assets from different providers follow standard format."""
        required_fields = [
            "id", "media_type", "source", "usage_rights"
        ]
        
        # Test with mocked data (using fixtures from above tests)
        with patch.dict('os.environ', {'PEXELS_API_KEY': 'test_key'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "photos": [{
                        "id": 123,
                        "width": 1920,
                        "height": 1080,
                        "url": "https://pexels.com/photo/123/",
                        "photographer": "Test Photographer",
                        "photographer_url": "https://pexels.com/@test",
                        "src": {
                            "original": "https://images.pexels.com/123/original.jpg",
                            "large": "https://images.pexels.com/123/large.jpg"
                        },
                        "alt": "Test photo"
                    }],
                    "total_results": 1
                }
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                result = search_pexels_media("test")
                assert result["total_results"] > 0
                
                asset = result["results"][0]
                for field in required_fields:
                    assert field in asset, f"Missing required field: {field}"
                
                # Verify asset type consistency
                assert asset["media_type"] in ["image", "video"]
                assert asset["source"] == "pexels"
    
    def test_error_handling_scenarios(self):
        """Test error handling across different failure scenarios."""
        # Test missing API keys
        with patch.dict('os.environ', {}, clear=True):
            pexels_result = search_pexels_media("test")
            unsplash_result = search_unsplash_photos("test")
            pixabay_result = search_pixabay_media("test")
            
            assert pexels_result.get("total_results", 0) == 0
            assert unsplash_result.get("total_results", 0) == 0
            assert pixabay_result.get("total_results", 0) == 0
            
            assert "PEXELS_API_KEY" in pexels_result["results"][0]["alt"]
            assert "UNSPLASH_ACCESS_KEY" in unsplash_result["results"][0]["alt_description"]
            assert "PIXABAY_API_KEY" in pixabay_result["results"][0]["tags"]
        
        # Test network failures
        with patch.dict('os.environ', {'PEXELS_API_KEY': 'test_key'}):
            with patch('requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
                
                result = search_pexels_media("test")
                assert result.get("total_results", 0) == 0
                assert "Failed to search Pexels" in result["results"][0]["alt"]
    
    @patch.dict('os.environ', {
        'PEXELS_API_KEY': 'test_pexels_key',
        'UNSPLASH_ACCESS_KEY': 'test_unsplash_key',
        'PIXABAY_API_KEY': 'test_pixabay_key'
    })
    def test_asset_sourcing_agent_tool_integration(self):
        """Test that asset sourcing agent properly integrates with all tools."""
        # Verify all tools are accessible and callable
        tools = asset_sourcing_agent.tools
        assert len(tools) == 3
        
        for tool in tools:
            assert callable(tool)
        
        # Test that tools can be called individually
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"photos": [], "total_results": 0}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Find and test pexels tool
            pexels_tool = next(tool for tool in tools if tool.__name__ == "search_pexels_media")
            result = pexels_tool("test query")
            assert result["total_results"] == 0
            assert "results" in result


# Sample data for testing
SAMPLE_SCENE_REQUIREMENTS = {
    "scene_number": 1,
    "description": "Opening scene showing technology and innovation",
    "visual_requirements": [
        "Modern office environment",
        "Technology equipment and screens",
        "Professional business setting",
        "Clean and modern aesthetic"
    ],
    "duration": 15.0,
    "style": "professional"
}

SAMPLE_ASSET_SEARCH_QUERIES = [
    "modern office technology",
    "business professionals working",
    "computer screens and data",
    "innovation and technology"
]


if __name__ == "__main__":
    # Run basic functionality tests
    print("Running Asset Sourcing Agent tests...")
    
    # Test individual tools
    print("\n1. Testing Pexels search tool...")
    try:
        pexels_result = search_pexels_media("technology", per_page=5)
        if pexels_result.get("total_results", 0) > 0:
            print("✓ Pexels search successful")
            print(f"  Found {len(pexels_result['results'])} assets")
        else:
            print("✗ Pexels search failed:", pexels_result.get("results", [{}])[0].get("alt", "Unknown error"))
    except Exception as e:
        print("✗ Pexels search error:", str(e))
    
    print("\n2. Testing Unsplash search tool...")
    try:
        unsplash_result = search_unsplash_photos("business", per_page=5)
        if unsplash_result.get("total_results", 0) > 0:
            print("✓ Unsplash search successful")
            print(f"  Found {len(unsplash_result['results'])} assets")
        else:
            print("✗ Unsplash search failed:", unsplash_result.get("results", [{}])[0].get("alt_description", "Unknown error"))
    except Exception as e:
        print("✗ Unsplash search error:", str(e))
    
    print("\n3. Testing Pixabay search tool...")
    try:
        pixabay_result = search_pixabay_media("office", per_page=5)
        if pixabay_result.get("total_results", 0) > 0:
            print("✓ Pixabay search successful")
            print(f"  Found {len(pixabay_result['results'])} assets")
        else:
            print("✗ Pixabay search failed:", pixabay_result.get("results", [{}])[0].get("tags", "Unknown error"))
    except Exception as e:
        print("✗ Pixabay search error:", str(e))
    
    # Test agent initialization
    print("\n4. Testing Asset Sourcing Agent initialization...")
    try:
        assert asset_sourcing_agent.name == "asset_sourcing_agent"
        assert len(asset_sourcing_agent.tools) == 3
        print("✓ Asset Sourcing Agent initialized successfully")
        print(f"  Agent has {len(asset_sourcing_agent.tools)} tools")
    except Exception as e:
        print("✗ Asset Sourcing Agent initialization error:", str(e))
    
    print("\nAsset Sourcing Agent tests completed!")