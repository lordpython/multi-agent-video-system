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

"""ADK configuration utilities for the Multi-Agent Video System.

This module provides configuration utilities for setting up ADK services
including SessionService and other ADK components.
"""

import os
import logging
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

from google.adk.sessions import (
    BaseSessionService,
    InMemorySessionService,
    VertexAiSessionService,
)


logger = logging.getLogger(__name__)


class ADKConfig(BaseSettings):
    """Configuration settings for ADK services."""

    # Google Cloud settings
    google_cloud_project: Optional[str] = Field(None, env="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field("us-central1", env="GOOGLE_CLOUD_LOCATION")

    # ADK settings
    use_vertex_ai: bool = Field(False, env="GOOGLE_GENAI_USE_VERTEXAI")

    # Session service settings
    session_cleanup_interval: int = Field(
        3600, description="Session cleanup interval in seconds"
    )
    max_session_age_hours: int = Field(
        24, description="Maximum session age before cleanup"
    )

    # Development settings
    development_mode: bool = Field(True, env="DEVELOPMENT_MODE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


class SessionServiceFactory:
    """Factory for creating appropriate SessionService instances."""

    @staticmethod
    def create_session_service(
        config: Optional[ADKConfig] = None,
    ) -> BaseSessionService:
        """Create and configure the appropriate SessionService.

        Args:
            config: ADK configuration (auto-loaded if None)

        Returns:
            Configured BaseSessionService instance
        """
        if config is None:
            config = ADKConfig()

        # Determine which SessionService to use
        if config.use_vertex_ai and config.google_cloud_project:
            logger.info("Creating VertexAiSessionService for production use")
            return SessionServiceFactory._create_vertex_session_service(config)
        else:
            logger.info("Creating InMemorySessionService for development use")
            return SessionServiceFactory._create_memory_session_service(config)

    @staticmethod
    def _create_vertex_session_service(config: ADKConfig) -> VertexAiSessionService:
        """Create VertexAiSessionService for production use."""
        try:
            return VertexAiSessionService(
                project=config.google_cloud_project,
                location=config.google_cloud_location,
            )
        except Exception as e:
            logger.error(f"Failed to create VertexAiSessionService: {e}")
            logger.warning("Falling back to InMemorySessionService")
            return SessionServiceFactory._create_memory_session_service(config)

    @staticmethod
    def _create_memory_session_service(config: ADKConfig) -> InMemorySessionService:
        """Create InMemorySessionService for development use."""
        if not config.development_mode:
            logger.warning(
                "Using InMemorySessionService in production mode. "
                "All session data will be lost on restart!"
            )

        return InMemorySessionService()


class ADKServiceManager:
    """Manager for ADK services and configuration."""

    def __init__(self, config: Optional[ADKConfig] = None):
        """Initialize ADK service manager.

        Args:
            config: ADK configuration (auto-loaded if None)
        """
        self.config = config or ADKConfig()
        self._session_service: Optional[BaseSessionService] = None

        logger.info(
            f"ADK Service Manager initialized with config: {self._get_config_summary()}"
        )

    def _get_config_summary(self) -> str:
        """Get a summary of the current configuration."""
        return (
            f"project={self.config.google_cloud_project}, "
            f"location={self.config.google_cloud_location}, "
            f"use_vertex_ai={self.config.use_vertex_ai}, "
            f"development_mode={self.config.development_mode}"
        )

    def get_session_service(self) -> BaseSessionService:
        """Get or create the BaseSessionService instance."""
        if self._session_service is None:
            self._session_service = SessionServiceFactory.create_session_service(
                self.config
            )
        return self._session_service

    def validate_configuration(self) -> bool:
        """Validate the current ADK configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check if we have required settings for Vertex AI
            if self.config.use_vertex_ai:
                if not self.config.google_cloud_project:
                    logger.error(
                        "GOOGLE_CLOUD_PROJECT is required when using Vertex AI"
                    )
                    return False

                # Try to create a session service to validate credentials
                try:
                    session_service = SessionServiceFactory.create_session_service(
                        self.config
                    )
                    logger.info("ADK configuration validation successful")
                    return True
                except Exception as e:
                    logger.error(f"Failed to validate Vertex AI configuration: {e}")
                    return False
            else:
                # In-memory mode doesn't require special validation
                logger.info("Using in-memory mode, configuration is valid")
                return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def get_environment_info(self) -> dict:
        """Get information about the current environment setup."""
        return {
            "config": {
                "google_cloud_project": self.config.google_cloud_project,
                "google_cloud_location": self.config.google_cloud_location,
                "use_vertex_ai": self.config.use_vertex_ai,
                "development_mode": self.config.development_mode,
                "session_cleanup_interval": self.config.session_cleanup_interval,
                "max_session_age_hours": self.config.max_session_age_hours,
            },
            "session_service_type": type(self.get_session_service()).__name__,
            "environment_variables": {
                "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "GOOGLE_CLOUD_LOCATION": os.getenv("GOOGLE_CLOUD_LOCATION"),
                "GOOGLE_GENAI_USE_VERTEXAI": os.getenv("GOOGLE_GENAI_USE_VERTEXAI"),
                "DEVELOPMENT_MODE": os.getenv("DEVELOPMENT_MODE"),
            },
        }


# Global service manager instance
_service_manager: Optional[ADKServiceManager] = None


def get_adk_service_manager() -> ADKServiceManager:
    """Get the global ADK service manager instance."""
    global _service_manager
    if _service_manager is None:
        _service_manager = ADKServiceManager()
    return _service_manager


def initialize_adk_services(config: Optional[ADKConfig] = None) -> ADKServiceManager:
    """Initialize ADK services with the given configuration."""
    global _service_manager
    _service_manager = ADKServiceManager(config)
    return _service_manager


def get_session_service() -> BaseSessionService:
    """Get the configured BaseSessionService instance."""
    return get_adk_service_manager().get_session_service()


def validate_adk_configuration() -> bool:
    """Validate the current ADK configuration."""
    return get_adk_service_manager().validate_configuration()
