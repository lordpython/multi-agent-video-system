# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Configuration package for the video system.

This package contains ADK-specific configuration utilities.
"""

from .adk_config import (
    ADKConfig,
    SessionServiceFactory,
    ADKServiceManager,
    get_adk_service_manager,
    initialize_adk_services,
    get_session_service,
    validate_adk_configuration,
)

__all__ = [
    "ADKConfig",
    "SessionServiceFactory",
    "ADKServiceManager",
    "get_adk_service_manager",
    "initialize_adk_services",
    "get_session_service",
    "validate_adk_configuration",
]
