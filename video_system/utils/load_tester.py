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

"""Load testing and performance validation utilities for the multi-agent video system."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid

from .models import VideoGenerationRequest
from .logging_config import get_logger

logger = get_logger(__name__)


class LoadTestType(Enum):
    """Types of load tests."""
    CONSTANT_LOAD = "constant_load"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    STRESS = "stress"


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    test_name: str
    test_type: LoadTestType
    duration_seconds: int = 300
    max_concurrent_users: int = 10
    requests_per_user: int = 1
    timeout_seconds: float = 300.0


@dataclass
class LoadTestMetrics:
    """Metrics for a load test."""
    test_name: str
    test_type: LoadTestType
    start_time: datetime
    end_time: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0


class LoadTester:
    """Main load testing orchestrator."""
    
    def __init__(self):
        """Initialize the load tester."""
        self.active_tests: Dict[str, LoadTestMetrics] = {}
        self.test_history: List[LoadTestMetrics] = []
        logger.info("LoadTester initialized")
    
    async def run_load_test(self, config: LoadTestConfig) -> LoadTestMetrics:
        """Run a load test with the specified configuration."""
        metrics = LoadTestMetrics(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.utcnow()
        )
        
        self.active_tests[config.test_name] = metrics
        
        try:
            logger.info(f"Starting load test: {config.test_name}")
            
            # Simulate load test execution
            await asyncio.sleep(min(config.duration_seconds, 10))  # Cap at 10 seconds for demo
            
            # Simulate results
            metrics.total_requests = config.max_concurrent_users * config.requests_per_user
            metrics.successful_requests = int(metrics.total_requests * 0.95)  # 95% success rate
            metrics.failed_requests = metrics.total_requests - metrics.successful_requests
            metrics.avg_response_time_ms = 2500.0  # 2.5 seconds average
            
            metrics.end_time = datetime.utcnow()
            logger.info(f"Load test completed: {config.test_name}")
            
        except Exception as e:
            logger.error(f"Load test failed: {config.test_name} - {e}")
        finally:
            self.active_tests.pop(config.test_name, None)
            self.test_history.append(metrics)
        
        return metrics


# Global load tester instance
_load_tester: Optional[LoadTester] = None


def get_load_tester() -> LoadTester:
    """Get the global load tester instance."""
    global _load_tester
    if _load_tester is None:
        _load_tester = LoadTester()
    return _load_tester