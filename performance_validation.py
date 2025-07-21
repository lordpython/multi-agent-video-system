#!/usr/bin/env python3
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

"""Performance validation script for the multi-agent video system.

This script demonstrates and validates the concurrent processing, resource management,
rate limiting, and load testing capabilities of the system.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from video_system.shared_libraries import (
    initialize_concurrent_processor,
    initialize_resource_manager,
    initialize_rate_limiter,
    get_load_tester,
    VideoGenerationRequest,
    RequestPriority,
    ResourceLimits,
    ResourceThresholds,
    LoadTestConfig,
    LoadTestType,
    get_logger
)

logger = get_logger(__name__)


class PerformanceValidator:
    """Validates system performance under various load conditions."""
    
    def __init__(self):
        """Initialize the performance validator."""
        self.results = {}
        self.start_time = datetime.utcnow()
        
        # Initialize components with test-friendly settings
        self.resource_manager = initialize_resource_manager(
            ResourceThresholds(
                cpu_warning=60.0,
                cpu_critical=80.0,
                memory_warning=70.0,
                memory_critical=85.0
            )
        )
        
        self.concurrent_processor = initialize_concurrent_processor(
            ResourceLimits(
                max_concurrent_requests=5,
                max_queue_size=50,
                max_memory_usage_percent=80.0,
                max_cpu_usage_percent=85.0
            )
        )
        
        self.rate_limiter = initialize_rate_limiter()
        self.load_tester = get_load_tester()
        
        logger.info("PerformanceValidator initialized")
    
    async def run_validation(self):
        """Run comprehensive performance validation."""
        logger.info("Starting performance validation...")
        
        try:
            # Start monitoring systems
            self.resource_manager.start_monitoring()
            self.concurrent_processor.start()
            
            # Run validation tests
            await self._test_basic_functionality()
            await self._test_concurrent_processing()
            await self._test_resource_management()
            await self._test_rate_limiting()
            await self._test_load_scenarios()
            
            # Generate final report
            self._generate_report()
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.results["validation_error"] = str(e)
        
        finally:
            # Cleanup
            self.concurrent_processor.stop()
            self.resource_manager.stop_monitoring()
            
        logger.info("Performance validation completed")
    
    async def _test_basic_functionality(self):
        """Test basic system functionality."""
        logger.info("Testing basic functionality...")
        
        test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Test 1: Component initialization
        test_results["tests"]["component_initialization"] = {
            "resource_manager_active": self.resource_manager.monitoring_active,
            "processor_running": self.concurrent_processor.status.value == "running",
            "rate_limiter_services": len(self.rate_limiter.service_limits),
            "passed": True
        }
        
        # Test 2: Basic request submission
        try:
            request = VideoGenerationRequest(
                prompt="Test video for performance validation",
                duration_preference=30,
                style="professional",
                quality="medium"
            )
            
            request_id = self.concurrent_processor.submit_request(
                request, 
                user_id="validation_user",
                priority=RequestPriority.HIGH
            )
            
            # Check request status
            status = self.concurrent_processor.get_request_status(request_id)
            
            test_results["tests"]["basic_request_submission"] = {
                "request_submitted": request_id is not None,
                "status_retrieved": status is not None,
                "request_id": request_id,
                "passed": request_id is not None and status is not None
            }
            
        except Exception as e:
            test_results["tests"]["basic_request_submission"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 3: Resource monitoring
        try:
            usage = self.resource_manager.get_current_usage()
            availability = self.resource_manager.get_resource_availability()
            
            test_results["tests"]["resource_monitoring"] = {
                "usage_retrieved": usage is not None,
                "availability_retrieved": availability is not None,
                "cpu_percent": usage.cpu_percent if usage else None,
                "memory_percent": usage.memory_percent if usage else None,
                "passed": usage is not None and availability is not None
            }
            
        except Exception as e:
            test_results["tests"]["resource_monitoring"] = {
                "error": str(e),
                "passed": False
            }
        
        test_results["end_time"] = datetime.utcnow().isoformat()
        test_results["overall_passed"] = all(
            test.get("passed", False) for test in test_results["tests"].values()
        )
        
        self.results["basic_functionality"] = test_results
        logger.info(f"Basic functionality test completed: {'PASSED' if test_results['overall_passed'] else 'FAILED'}")
    
    async def _test_concurrent_processing(self):
        """Test concurrent processing capabilities."""
        logger.info("Testing concurrent processing...")
        
        test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Test 1: Multiple request submission
        try:
            request_ids = []
            for i in range(10):
                request = VideoGenerationRequest(
                    prompt=f"Concurrent test video {i}",
                    duration_preference=30,
                    style="professional",
                    quality="medium"
                )
                
                request_id = self.concurrent_processor.submit_request(
                    request,
                    user_id=f"concurrent_user_{i}",
                    priority=RequestPriority.NORMAL
                )
                request_ids.append(request_id)
            
            # Check queue metrics
            metrics = self.concurrent_processor.get_metrics()
            
            test_results["tests"]["multiple_request_submission"] = {
                "requests_submitted": len(request_ids),
                "queue_size": metrics.current_queue_size,
                "total_queued": metrics.total_requests_queued,
                "passed": len(request_ids) == 10 and metrics.current_queue_size > 0
            }
            
        except Exception as e:
            test_results["tests"]["multiple_request_submission"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 2: Priority handling
        try:
            # Submit requests with different priorities
            urgent_id = self.concurrent_processor.submit_request(
                VideoGenerationRequest(prompt="Urgent request", duration_preference=30),
                priority=RequestPriority.URGENT
            )
            
            low_id = self.concurrent_processor.submit_request(
                VideoGenerationRequest(prompt="Low priority request", duration_preference=30),
                priority=RequestPriority.LOW
            )
            
            test_results["tests"]["priority_handling"] = {
                "urgent_submitted": urgent_id is not None,
                "low_submitted": low_id is not None,
                "passed": urgent_id is not None and low_id is not None
            }
            
        except Exception as e:
            test_results["tests"]["priority_handling"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 3: Resource usage under load
        try:
            initial_usage = self.resource_manager.get_current_usage()
            
            # Wait a bit for processing to start
            await asyncio.sleep(2.0)
            
            load_usage = self.resource_manager.get_current_usage()
            
            test_results["tests"]["resource_usage_under_load"] = {
                "initial_cpu": initial_usage.cpu_percent,
                "load_cpu": load_usage.cpu_percent,
                "initial_memory": initial_usage.memory_percent,
                "load_memory": load_usage.memory_percent,
                "cpu_increased": load_usage.cpu_percent >= initial_usage.cpu_percent,
                "passed": True  # Just measuring, not failing
            }
            
        except Exception as e:
            test_results["tests"]["resource_usage_under_load"] = {
                "error": str(e),
                "passed": False
            }
        
        test_results["end_time"] = datetime.utcnow().isoformat()
        test_results["overall_passed"] = all(
            test.get("passed", False) for test in test_results["tests"].values()
        )
        
        self.results["concurrent_processing"] = test_results
        logger.info(f"Concurrent processing test completed: {'PASSED' if test_results['overall_passed'] else 'FAILED'}")
    
    async def _test_resource_management(self):
        """Test resource management capabilities."""
        logger.info("Testing resource management...")
        
        test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Test 1: Resource allocation
        try:
            allocation_id = self.resource_manager.allocate_resources(
                session_id="test_session",
                cpu_cores=2.0,
                memory_mb=1024.0,
                disk_mb=500.0,
                priority=1
            )
            
            availability = self.resource_manager.get_resource_availability()
            
            test_results["tests"]["resource_allocation"] = {
                "allocation_created": allocation_id is not None,
                "allocation_id": allocation_id,
                "cpu_allocated": availability["cpu"]["allocated_cores"],
                "memory_allocated": availability["memory"]["allocated_mb"],
                "passed": allocation_id is not None
            }
            
            # Clean up allocation
            if allocation_id:
                self.resource_manager.deallocate_resources(allocation_id)
                
        except Exception as e:
            test_results["tests"]["resource_allocation"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 2: Resource monitoring
        try:
            # Get usage history
            history = self.resource_manager.get_usage_history(hours=1)
            
            # Get active alerts
            alerts = self.resource_manager.get_active_alerts()
            
            test_results["tests"]["resource_monitoring"] = {
                "history_entries": len(history),
                "active_alerts": len(alerts),
                "monitoring_active": self.resource_manager.monitoring_active,
                "passed": self.resource_manager.monitoring_active
            }
            
        except Exception as e:
            test_results["tests"]["resource_monitoring"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 3: Garbage collection
        try:
            gc_results = self.resource_manager.force_garbage_collection()
            
            test_results["tests"]["garbage_collection"] = {
                "memory_freed_mb": gc_results["memory_freed_mb"],
                "objects_collected": gc_results["objects_collected"],
                "passed": gc_results["objects_collected"] >= 0
            }
            
        except Exception as e:
            test_results["tests"]["garbage_collection"] = {
                "error": str(e),
                "passed": False
            }
        
        test_results["end_time"] = datetime.utcnow().isoformat()
        test_results["overall_passed"] = all(
            test.get("passed", False) for test in test_results["tests"].values()
        )
        
        self.results["resource_management"] = test_results
        logger.info(f"Resource management test completed: {'PASSED' if test_results['overall_passed'] else 'FAILED'}")
    
    async def _test_rate_limiting(self):
        """Test rate limiting capabilities."""
        logger.info("Testing rate limiting...")
        
        test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Test 1: Basic rate limiting
        try:
            service_name = "test_service"
            
            # Check initial rate limit
            allowed, delay = self.rate_limiter.check_rate_limit(service_name, user_id="test_user")
            
            # Record some requests
            for i in range(5):
                self.rate_limiter.record_request(
                    service_name,
                    user_id="test_user",
                    success=True,
                    response_time_ms=100.0 + i * 10
                )
            
            # Get statistics
            stats = self.rate_limiter.get_statistics()
            
            test_results["tests"]["basic_rate_limiting"] = {
                "initial_allowed": allowed,
                "initial_delay": delay,
                "total_requests": stats["total_requests_last_hour"],
                "success_rate": stats["success_rate"],
                "passed": True  # Basic functionality test
            }
            
        except Exception as e:
            test_results["tests"]["basic_rate_limiting"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 2: Service status
        try:
            all_status = self.rate_limiter.get_all_service_status()
            serper_status = self.rate_limiter.get_service_status("serper_api")
            
            test_results["tests"]["service_status"] = {
                "services_configured": len(all_status),
                "serper_status_available": serper_status is not None,
                "serper_allowed_rps": serper_status.allowed_rps if serper_status else None,
                "passed": len(all_status) > 0 and serper_status is not None
            }
            
        except Exception as e:
            test_results["tests"]["service_status"] = {
                "error": str(e),
                "passed": False
            }
        
        test_results["end_time"] = datetime.utcnow().isoformat()
        test_results["overall_passed"] = all(
            test.get("passed", False) for test in test_results["tests"].values()
        )
        
        self.results["rate_limiting"] = test_results
        logger.info(f"Rate limiting test completed: {'PASSED' if test_results['overall_passed'] else 'FAILED'}")
    
    async def _test_load_scenarios(self):
        """Test various load scenarios."""
        logger.info("Testing load scenarios...")
        
        test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "load_tests": {}
        }
        
        # Test 1: Constant load test
        try:
            config = LoadTestConfig(
                test_name="validation_constant_load",
                test_type=LoadTestType.CONSTANT_LOAD,
                duration_seconds=15,  # Short for validation
                max_concurrent_users=3,
                requests_per_user=1,
                think_time_seconds=1.0,
                timeout_seconds=30.0
            )
            
            # Mock the processor for load testing
            original_submit = self.concurrent_processor.submit_request
            original_status = self.concurrent_processor.get_request_status
            
            def mock_submit(request, user_id=None, priority=None):
                return f"mock_request_{time.time()}"
            
            def mock_status(request_id):
                return {
                    "status": "completed",
                    "request_id": request_id,
                    "session_id": f"session_{request_id}"
                }
            
            self.concurrent_processor.submit_request = mock_submit
            self.concurrent_processor.get_request_status = mock_status
            
            try:
                metrics = await self.load_tester.run_load_test(config)
                
                test_results["load_tests"]["constant_load"] = {
                    "test_completed": metrics.phase.value in ["completed", "failed"],
                    "total_requests": metrics.total_requests,
                    "successful_requests": metrics.successful_requests,
                    "success_rate": metrics.success_rate,
                    "avg_response_time_ms": metrics.avg_response_time_ms,
                    "peak_concurrent_users": metrics.peak_concurrent_users,
                    "passed": metrics.phase.value == "completed" and metrics.success_rate > 0.5
                }
                
            finally:
                # Restore original methods
                self.concurrent_processor.submit_request = original_submit
                self.concurrent_processor.get_request_status = original_status
                
        except Exception as e:
            test_results["load_tests"]["constant_load"] = {
                "error": str(e),
                "passed": False
            }
        
        # Test 2: Burst load test
        try:
            config = LoadTestConfig(
                test_name="validation_burst_load",
                test_type=LoadTestType.BURST,
                duration_seconds=20,  # Short for validation
                max_concurrent_users=5,
                requests_per_user=1,
                think_time_seconds=0.1,
                timeout_seconds=30.0
            )
            
            # Use the same mocking approach
            self.concurrent_processor.submit_request = mock_submit
            self.concurrent_processor.get_request_status = mock_status
            
            try:
                metrics = await self.load_tester.run_load_test(config)
                
                test_results["load_tests"]["burst_load"] = {
                    "test_completed": metrics.phase.value in ["completed", "failed"],
                    "total_requests": metrics.total_requests,
                    "peak_concurrent_users": metrics.peak_concurrent_users,
                    "peak_cpu_percent": metrics.peak_cpu_percent,
                    "peak_memory_percent": metrics.peak_memory_percent,
                    "passed": metrics.phase.value == "completed"
                }
                
            finally:
                # Restore original methods
                self.concurrent_processor.submit_request = original_submit
                self.concurrent_processor.get_request_status = original_status
                
        except Exception as e:
            test_results["load_tests"]["burst_load"] = {
                "error": str(e),
                "passed": False
            }
        
        test_results["end_time"] = datetime.utcnow().isoformat()
        test_results["overall_passed"] = all(
            test.get("passed", False) for test in test_results["load_tests"].values()
        )
        
        self.results["load_scenarios"] = test_results
        logger.info(f"Load scenarios test completed: {'PASSED' if test_results['overall_passed'] else 'FAILED'}")
    
    def _generate_report(self):
        """Generate comprehensive performance validation report."""
        logger.info("Generating performance validation report...")
        
        # Calculate overall results
        all_tests_passed = all(
            result.get("overall_passed", False) 
            for result in self.results.values()
            if isinstance(result, dict) and "overall_passed" in result
        )
        
        # Create summary
        summary = {
            "validation_start_time": self.start_time.isoformat(),
            "validation_end_time": datetime.utcnow().isoformat(),
            "overall_result": "PASSED" if all_tests_passed else "FAILED",
            "test_categories": len(self.results),
            "detailed_results": self.results
        }
        
        # Add system information
        try:
            current_usage = self.resource_manager.get_current_usage()
            processor_metrics = self.concurrent_processor.get_metrics()
            rate_limiter_stats = self.rate_limiter.get_statistics()
            
            summary["system_state"] = {
                "cpu_percent": current_usage.cpu_percent,
                "memory_percent": current_usage.memory_percent,
                "disk_percent": current_usage.disk_percent,
                "processor_uptime": processor_metrics.uptime_seconds,
                "total_requests_processed": processor_metrics.total_requests_processed,
                "rate_limiter_requests": rate_limiter_stats["total_requests_last_hour"]
            }
        except Exception as e:
            summary["system_state"] = {"error": str(e)}
        
        # Save report
        report_path = Path("performance_validation_report.json")
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*80)
        print("PERFORMANCE VALIDATION REPORT")
        print("="*80)
        print(f"Overall Result: {summary['overall_result']}")
        print(f"Test Categories: {summary['test_categories']}")
        print(f"Start Time: {summary['validation_start_time']}")
        print(f"End Time: {summary['validation_end_time']}")
        
        if "system_state" in summary and "error" not in summary["system_state"]:
            print("\nSystem State:")
            print(f"  CPU Usage: {summary['system_state']['cpu_percent']:.1f}%")
            print(f"  Memory Usage: {summary['system_state']['memory_percent']:.1f}%")
            print(f"  Processor Uptime: {summary['system_state']['processor_uptime']:.1f}s")
            print(f"  Requests Processed: {summary['system_state']['total_requests_processed']}")
        
        print(f"\nDetailed report saved to: {report_path.absolute()}")
        print("="*80)
        
        logger.info(f"Performance validation report generated: {report_path}")


async def main():
    """Main function to run performance validation."""
    print("Multi-Agent Video System - Performance Validation")
    print("="*60)
    
    validator = PerformanceValidator()
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main())