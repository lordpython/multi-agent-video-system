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

"""Tests for configuration validation and management."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import yaml

from video_system.shared_libraries.config_manager import (
    ConfigurationManager,
    VideoSystemConfig,
    GoogleCloudConfig,
    ExternalAPIConfig,
    VideoProcessingConfig,
    Environment,
    LogLevel,
    VideoQuality,
    get_config_manager,
    validate_system_configuration,
    initialize_configuration
)
from video_system.shared_libraries.error_handling import ConfigurationError


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear any existing global config manager
        import video_system.shared_libraries.config_manager as config_module
        config_module._config_manager = None
    
    def test_default_configuration(self):
        """Test loading default configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigurationManager()
            config = config_manager.config
            
            assert isinstance(config, VideoSystemConfig)
            assert config.development.environment == Environment.PRODUCTION
            assert config.logging.log_level == LogLevel.INFO
            assert config.video_processing.video_quality == VideoQuality.HIGH
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        test_env = {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'GOOGLE_CLOUD_LOCATION': 'us-west1',
            'SERPER_API_KEY': 'test-serper-key',
            'LOG_LEVEL': 'DEBUG',
            'MAX_CONCURRENT_REQUESTS': '20',
            'ENABLE_RATE_LIMITING': 'false',
            'VIDEO_QUALITY': 'medium',
            'DEFAULT_VIDEO_RESOLUTION': '1280x720',
            'ENVIRONMENT': 'development',
            'DEBUG_MODE': 'true'
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            config_manager = ConfigurationManager()
            config = config_manager.config
            
            assert config.google_cloud.project_id == 'test-project'
            assert config.google_cloud.location == 'us-west1'
            assert config.external_apis.serper_api_key == 'test-serper-key'
            assert config.logging.log_level == LogLevel.DEBUG
            assert config.performance.max_concurrent_requests == 20
            assert config.performance.enable_rate_limiting is False
            assert config.video_processing.video_quality == VideoQuality.MEDIUM
            assert config.video_processing.default_video_resolution == '1280x720'
            assert config.development.environment == Environment.DEVELOPMENT
            assert config.development.debug_mode is True
    
    def test_json_config_file_loading(self):
        """Test loading configuration from JSON file."""
        config_data = {
            'google_cloud': {
                'project_id': 'json-project',
                'location': 'europe-west1'
            },
            'performance': {
                'max_concurrent_requests': 15
            },
            'video_processing': {
                'video_quality': 'ultra',
                'default_video_fps': 60
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigurationManager(config_file=config_file)
            config = config_manager.config
            
            assert config.google_cloud.project_id == 'json-project'
            assert config.google_cloud.location == 'europe-west1'
            assert config.performance.max_concurrent_requests == 15
            assert config.video_processing.video_quality == VideoQuality.ULTRA
            assert config.video_processing.default_video_fps == 60
        finally:
            os.unlink(config_file)
    
    def test_yaml_config_file_loading(self):
        """Test loading configuration from YAML file."""
        config_data = {
            'google_cloud': {
                'project_id': 'yaml-project',
                'use_vertexai': False
            },
            'logging': {
                'log_level': 'WARNING',
                'enable_structured_logging': False
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigurationManager(config_file=config_file)
            config = config_manager.config
            
            assert config.google_cloud.project_id == 'yaml-project'
            assert config.google_cloud.use_vertexai is False
            assert config.logging.log_level == LogLevel.WARNING
            assert config.logging.enable_structured_logging is False
        finally:
            os.unlink(config_file)
    
    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        env_content = """
GOOGLE_CLOUD_PROJECT=env-project
SERPER_API_KEY=env-serper-key
MAX_CONCURRENT_REQUESTS=25
ENABLE_HEALTH_CHECKS=false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file = f.name
        
        try:
            config_manager = ConfigurationManager(env_file=env_file)
            config = config_manager.config
            
            assert config.google_cloud.project_id == 'env-project'
            assert config.external_apis.serper_api_key == 'env-serper-key'
            assert config.performance.max_concurrent_requests == 25
            assert config.monitoring.enable_health_checks is False
        finally:
            os.unlink(env_file)
    
    def test_configuration_precedence(self):
        """Test that file configuration takes precedence over environment."""
        # Set environment variable
        with patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'env-project'}, clear=True):
            # Create config file with different value
            config_data = {
                'google_cloud': {
                    'project_id': 'file-project'
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config_data, f)
                config_file = f.name
            
            try:
                config_manager = ConfigurationManager(config_file=config_file)
                config = config_manager.config
                
                # File config should take precedence
                assert config.google_cloud.project_id == 'file-project'
            finally:
                os.unlink(config_file)
    
    def test_invalid_config_file(self):
        """Test handling of invalid configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_file = f.name
        
        try:
            with pytest.raises(ConfigurationError):
                ConfigurationManager(config_file=config_file)
        finally:
            os.unlink(config_file)
    
    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        # Should not raise error, just skip file loading
        config_manager = ConfigurationManager(config_file="nonexistent.json")
        config = config_manager.config
        assert isinstance(config, VideoSystemConfig)
    
    def test_boolean_environment_parsing(self):
        """Test parsing of boolean environment variables."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('off', False),
            ('invalid', False)  # Default to False for invalid values
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'DEBUG_MODE': env_value}, clear=True):
                config_manager = ConfigurationManager()
                assert config_manager.config.development.debug_mode == expected
    
    def test_integer_environment_parsing(self):
        """Test parsing of integer environment variables."""
        test_cases = [
            ('10', 10),
            ('0', 0),
            ('-5', -5),
            ('invalid', 10)  # Should use default for invalid values
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'MAX_CONCURRENT_REQUESTS': env_value}, clear=True):
                config_manager = ConfigurationManager()
                actual = config_manager.config.performance.max_concurrent_requests
                assert actual == expected
    
    def test_float_environment_parsing(self):
        """Test parsing of float environment variables."""
        test_cases = [
            ('1.5', 1.5),
            ('0.0', 0.0),
            ('-2.5', -2.5),
            ('invalid', 10.0)  # Should use default for invalid values
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'DEFAULT_REQUESTS_PER_SECOND': env_value}, clear=True):
                config_manager = ConfigurationManager()
                actual = config_manager.config.performance.default_requests_per_second
                assert actual == expected


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        import video_system.shared_libraries.config_manager as config_module
        config_module._config_manager = None
    
    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        valid_env = {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'SERPER_API_KEY': 'test-key',
            'GEMINI_API_KEY': 'test-gemini-key',
            'PEXELS_API_KEY': 'test-pexels-key',
            'FFMPEG_PATH': '/usr/bin/ffmpeg'
        }
        
        with patch.dict(os.environ, valid_env, clear=True):
            with patch('pathlib.Path.exists', return_value=True):
                config_manager = ConfigurationManager()
                issues = config_manager.validate_configuration()
                
                # Should have no critical issues
                assert len(issues) == 0
    
    def test_missing_required_api_keys(self):
        """Test validation with missing required API keys."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigurationManager()
            issues = config_manager.validate_configuration()
            
            # Should report missing required API keys
            issue_text = ' '.join(issues)
            assert 'SERPER_API_KEY' in issue_text
            assert 'GEMINI_API_KEY' in issue_text
    
    def test_missing_stock_media_apis(self):
        """Test validation with no stock media APIs configured."""
        env_with_required = {
            'SERPER_API_KEY': 'test-key',
            'GEMINI_API_KEY': 'test-gemini-key'
        }
        
        with patch.dict(os.environ, env_with_required, clear=True):
            config_manager = ConfigurationManager()
            issues = config_manager.validate_configuration()
            
            # Should report missing stock media APIs
            issue_text = ' '.join(issues)
            assert 'stock media API' in issue_text.lower()
    
    def test_invalid_staging_bucket(self):
        """Test validation of invalid staging bucket format."""
        invalid_env = {
            'STAGING_BUCKET': 'invalid-bucket-format'
        }
        
        with patch.dict(os.environ, invalid_env, clear=True):
            config_manager = ConfigurationManager()
            issues = config_manager.validate_configuration()
            
            # Should report invalid staging bucket format
            issue_text = ' '.join(issues)
            assert 'gs://' in issue_text
    
    def test_missing_ffmpeg(self):
        """Test validation with missing FFmpeg."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('pathlib.Path.exists', return_value=False):
                config_manager = ConfigurationManager()
                issues = config_manager.validate_configuration()
                
                # Should report missing FFmpeg
                issue_text = ' '.join(issues)
                assert 'FFmpeg' in issue_text
    
    def test_invalid_video_resolution(self):
        """Test validation of invalid video resolution."""
        invalid_env = {
            'DEFAULT_VIDEO_RESOLUTION': 'invalid-resolution'
        }
        
        with patch.dict(os.environ, invalid_env, clear=True):
            config_manager = ConfigurationManager()
            issues = config_manager.validate_configuration()
            
            # Should report invalid resolution format
            issue_text = ' '.join(issues)
            assert 'resolution' in issue_text.lower()
    
    def test_vertex_ai_missing_project(self):
        """Test validation of Vertex AI config without project ID."""
        vertex_env = {
            'GOOGLE_GENAI_USE_VERTEXAI': 'true'
            # Missing GOOGLE_CLOUD_PROJECT
        }
        
        with patch.dict(os.environ, vertex_env, clear=True):
            config_manager = ConfigurationManager()
            issues = config_manager.validate_configuration()
            
            # Should report missing project ID
            issue_text = ' '.join(issues)
            assert 'Project ID' in issue_text
    
    def test_ml_dev_missing_api_key(self):
        """Test validation of ML Dev config without API key."""
        ml_dev_env = {
            'GOOGLE_GENAI_USE_VERTEXAI': 'false'
            # Missing GOOGLE_API_KEY
        }
        
        with patch.dict(os.environ, ml_dev_env, clear=True):
            config_manager = ConfigurationManager()
            issues = config_manager.validate_configuration()
            
            # Should report missing API key
            issue_text = ' '.join(issues)
            assert 'API Key' in issue_text


class TestConfigurationUtilities:
    """Test configuration utility functions."""
    
    def setup_method(self):
        """Set up test environment."""
        import video_system.shared_libraries.config_manager as config_module
        config_module._config_manager = None
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_validate_system_configuration(self):
        """Test system configuration validation function."""
        with patch.dict(os.environ, {}, clear=True):
            issues = validate_system_configuration()
            
            # Should return list of issues
            assert isinstance(issues, list)
            assert len(issues) > 0  # Should have some validation issues
    
    def test_initialize_configuration(self):
        """Test configuration initialization function."""
        test_env = {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'SERPER_API_KEY': 'test-key',
            'GEMINI_API_KEY': 'test-gemini-key',
            'PEXELS_API_KEY': 'test-pexels-key'
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            config = initialize_configuration()
            
            assert isinstance(config, VideoSystemConfig)
            assert config.google_cloud.project_id == 'test-project'
    
    def test_config_summary(self):
        """Test configuration summary generation."""
        test_env = {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'SERPER_API_KEY': 'test-key',
            'DEBUG_MODE': 'true'
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            config_manager = ConfigurationManager()
            summary = config_manager.get_config_summary()
            
            assert isinstance(summary, dict)
            assert 'environment' in summary
            assert 'google_cloud' in summary
            assert 'api_keys_configured' in summary
            assert summary['debug_mode'] is True
            assert summary['google_cloud']['project_id'] == 'test-project'
            
            # Should not contain sensitive data
            assert 'test-key' not in str(summary)
    
    def test_save_config_to_file(self):
        """Test saving configuration to file."""
        with patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project'}, clear=True):
            config_manager = ConfigurationManager()
            
            # Test YAML format
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml_file = f.name
            
            try:
                config_manager.save_config_to_file(yaml_file, format='yaml')
                
                # Verify file was created and contains expected content
                assert Path(yaml_file).exists()
                
                with open(yaml_file, 'r') as f:
                    saved_config = yaml.safe_load(f)
                
                assert isinstance(saved_config, dict)
                assert 'google_cloud' in saved_config
                
                # Should not contain sensitive data
                config_str = str(saved_config)
                assert '[REDACTED]' in config_str or 'test-project' in config_str
                
            finally:
                if Path(yaml_file).exists():
                    os.unlink(yaml_file)
            
            # Test JSON format
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json_file = f.name
            
            try:
                config_manager.save_config_to_file(json_file, format='json')
                
                # Verify file was created
                assert Path(json_file).exists()
                
                with open(json_file, 'r') as f:
                    saved_config = json.load(f)
                
                assert isinstance(saved_config, dict)
                assert 'google_cloud' in saved_config
                
            finally:
                if Path(json_file).exists():
                    os.unlink(json_file)
    
    def test_save_config_invalid_format(self):
        """Test saving configuration with invalid format."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigurationManager()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                test_file = f.name
            
            try:
                with pytest.raises(ConfigurationError):
                    config_manager.save_config_to_file(test_file, format='invalid')
            finally:
                if Path(test_file).exists():
                    os.unlink(test_file)


class TestConfigurationModels:
    """Test configuration model validation."""
    
    def test_google_cloud_config_validation(self):
        """Test Google Cloud configuration validation."""
        # Valid staging bucket
        config = GoogleCloudConfig(staging_bucket="gs://my-bucket")
        assert config.staging_bucket == "gs://my-bucket"
        
        # Invalid staging bucket
        with pytest.raises(ValueError):
            GoogleCloudConfig(staging_bucket="invalid-bucket")
    
    def test_video_processing_config_validation(self):
        """Test video processing configuration validation."""
        # Valid resolution
        config = VideoProcessingConfig(default_video_resolution="1920x1080")
        assert config.default_video_resolution == "1920x1080"
        
        # Invalid resolution format
        with pytest.raises(ValueError):
            VideoProcessingConfig(default_video_resolution="invalid")
        
        # Invalid resolution values
        with pytest.raises(ValueError):
            VideoProcessingConfig(default_video_resolution="0x0")
    
    def test_storage_config_directory_creation(self):
        """Test storage configuration directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            from video_system.shared_libraries.config_manager import StorageConfig
            
            config = StorageConfig(
                video_output_dir=temp_path / "output",
                temp_dir=temp_path / "temp",
                asset_cache_dir=temp_path / "cache",
                session_data_dir=temp_path / "sessions"
            )
            
            # Directories should not exist initially
            assert not config.video_output_dir.exists()
            assert not config.temp_dir.exists()
            
            # Create directories
            config.create_directories()
            
            # Directories should now exist
            assert config.video_output_dir.exists()
            assert config.temp_dir.exists()
            assert config.asset_cache_dir.exists()
            assert config.session_data_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__])