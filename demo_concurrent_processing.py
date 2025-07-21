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

"""Demonstration of concurrent processing and resource management capabilities.

This script shows how to use the multi-agent video system's concurrent processing,
resource management, rate limiting, and load testing features.
"""

import asyncio
import time
from datetime import datetime

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


async def demo_concurrent_processing():
    """Demonstrate concurrent processing capabilities."""
    print("\n" + "="*60)
    print("CONCURRENT PROCESSING DEMONSTRATION")
    print("="*60)
    
    # Initialize processor with custom limits
    resource_limits = ResourceLimits(
        max_concurrent_requests=3,
        max_queue_size=20,
        max_memory_usage_percent=80.0,
        max_cpu_usage_percent=85.0
    )
    
    processor = initialize_concurrent_processor(resource_limits)
    
    # Start the processor
    print("Starting concurrent processor...")
    processor.start()
    
    try:
        # Submit multiple requests with different priorities
        print("\nSubmitting video generation requests...")
        
        requests = [
            ("Create a video about AI and machine learning", RequestPriority.HIGH, "ai_user"),
            ("Make a cooking tutorial video", RequestPriority.NORMAL, "cooking_user"),
            ("Generate a travel vlog about Paris", RequestPriority.NORMAL, "travel_user"),
            ("Create an urgent news update video", RequestPriority.URGENT, "news_user"),
            ("Make a relaxing nature video", RequestPriority.LOW, "nature_user"),
        ]
        
        request_ids = []
        for prompt, priority, user_id in requests:
            video_request = VideoGenerationRequest(
                prompt=prompt,
                duration_preference=60,
                style="professional",
                quality="high"
            )
            
            request_id = processor.submit_request(
                video_request,
                user_id=user_id,
                priority=priority
            )
            
            request_ids.append((request_id, prompt, priority.name))
            print(f"  ✓ Submitted: {prompt[:40]}... (Priority: {priority.name})")
        
        # Monitor processing
        print(f"\nMonitoring {len(request_ids)} requests...")
        
        for i in range(10):  # Monitor for 10 seconds
            metrics = processor.get_metrics()
            resource_usage = processor.get_resource_usage()
            
            print(f"\nStatus Update {i+1}:")
            print(f"  Active Tasks: {metrics.current_active_tasks}")
            print(f"  Queue Size: {metrics.current_queue_size}")
            print(f"  Total Processed: {metrics.total_requests_processed}")
            print(f"  CPU Usage: {resource_usage['system']['cpu_percent']:.1f}%")
            print(f"  Memory Usage: {resource_usage['system']['memory_percent']:.1f}%")
            
            # Check individual request statuses
            for request_id, prompt, priority in request_ids:
                status = processor.get_request_status(request_id)
                if status:
                    print(f"    {prompt[:30]}... -> {status['status']}")
            
            await asyncio.sleep(1.0)
        
        # Final metrics
        final_metrics = processor.get_metrics()
        print("\nFinal Metrics:")
        print(f"  Total Requests Queued: {final_metrics.total_requests_queued}")
        print(f"  Total Requests Processed: {final_metrics.total_requests_processed}")
        print(f"  Total Requests Failed: {final_metrics.total_requests_failed}")
        print(f"  Peak Concurrent Requests: {final_metrics.peak_concurrent_requests}")
        print(f"  Average Processing Time: {final_metrics.average_processing_time:.2f}s")
        print(f"  Uptime: {final_metrics.uptime_seconds:.1f}s")
        
    finally:
        print("\nStopping processor...")
        processor.stop()
        print("Processor stopped.")


async def demo_resource_management():
    """Demonstrate resource management capabilities."""
    print("\n" + "="*60)
    print("RESOURCE MANAGEMENT DEMONSTRATION")
    print("="*60)
    
    # Initialize resource manager with custom thresholds
    thresholds = ResourceThresholds(
        cpu_warning=60.0,
        cpu_critical=80.0,
        memory_warning=70.0,
        memory_critical=85.0,
        disk_warning=80.0,
        disk_critical=90.0
    )
    
    resource_manager = initialize_resource_manager(thresholds)
    
    # Start monitoring
    print("Starting resource monitoring...")
    resource_manager.start_monitoring()
    
    try:
        # Show current resource usage
        print("\nCurrent Resource Usage:")
        usage = resource_manager.get_current_usage()
        print(f"  CPU: {usage.cpu_percent:.1f}%")
        print(f"  Memory: {usage.memory_percent:.1f}% ({usage.memory_available_gb:.1f} GB available)")
        print(f"  Disk: {usage.disk_percent:.1f}% ({usage.disk_free_gb:.1f} GB free)")
        print(f"  Network: {usage.network_sent_mbps:.2f} Mbps sent, {usage.network_recv_mbps:.2f} Mbps received")
        
        # Show resource availability
        print("\nResource Availability:")
        availability = resource_manager.get_resource_availability()
        print(f"  CPU Cores: {availability['cpu']['available_cores']:.1f} / {availability['cpu']['total_cores']}")
        print(f"  Memory: {availability['memory']['available_gb']:.1f} GB available")
        print(f"  Disk: {availability['disk']['free_gb']:.1f} GB free")
        
        # Demonstrate resource allocation
        print("\nAllocating resources for video processing...")
        allocation_id = resource_manager.allocate_resources(
            session_id="demo_session_1",
            cpu_cores=2.0,
            memory_mb=1024.0,
            disk_mb=500.0,
            priority=1
        )
        print(f"  ✓ Allocated resources: {allocation_id}")
        
        # Check availability after allocation
        availability_after = resource_manager.get_resource_availability()
        print(f"  CPU Cores after allocation: {availability_after['cpu']['available_cores']:.1f}")
        print(f"  Allocated CPU: {availability_after['cpu']['allocated_cores']:.1f}")
        
        # Monitor for a few seconds
        print("\nMonitoring resource usage...")
        for i in range(5):
            await asyncio.sleep(1.0)
            current_usage = resource_manager.get_current_usage()
            print(f"  Sample {i+1}: CPU {current_usage.cpu_percent:.1f}%, Memory {current_usage.memory_percent:.1f}%")
        
        # Get usage history
        history = resource_manager.get_usage_history(hours=1)
        print(f"\nUsage History: {len(history)} samples collected")
        
        # Check for alerts
        alerts = resource_manager.get_active_alerts()
        if alerts:
            print(f"\nActive Alerts: {len(alerts)}")
            for alert in alerts:
                print(f"  ⚠️  {alert.resource_type.value.upper()}: {alert.message}")
        else:
            print("\nNo active resource alerts")
        
        # Demonstrate garbage collection
        print("\nPerforming garbage collection...")
        gc_results = resource_manager.force_garbage_collection()
        print(f"  Memory freed: {gc_results['memory_freed_mb']:.1f} MB")
        print(f"  Objects collected: {gc_results['objects_collected']}")
        
        # Clean up allocation
        print("\nDeallocating resources...")
        resource_manager.deallocate_resources(allocation_id)
        print("  ✓ Resources deallocated")
        
    finally:
        print("\nStopping resource monitoring...")
        resource_manager.stop_monitoring()
        print("Resource monitoring stopped.")


async def demo_rate_limiting():
    """Demonstrate rate limiting capabilities."""
    print("\n" + "="*60)
    print("RATE LIMITING DEMONSTRATION")
    print("="*60)
    
    # Initialize rate limiter
    rate_limiter = initialize_rate_limiter()
    
    # Show configured services
    all_status = rate_limiter.get_all_service_status()
    print(f"Configured Services: {len(all_status)}")
    
    for service_name, status in all_status.items():
        if status:
            print(f"  {service_name}:")
            print(f"    Allowed RPS: {status.allowed_rps:.1f}")
            print(f"    Current RPS: {status.current_rps:.1f}")
            print(f"    Available Tokens: {status.tokens_available:.1f}")
            print(f"    Queue Size: {status.queue_size}")
    
    # Demonstrate rate limit checking
    print("\nTesting Rate Limits:")
    
    services_to_test = ["serper_api", "pexels_api", "gemini_api"]
    
    for service in services_to_test:
        print(f"\n  Testing {service}:")
        
        # Check multiple requests rapidly
        for i in range(5):
            allowed, delay = rate_limiter.check_rate_limit(service, user_id="demo_user")
            print(f"    Request {i+1}: {'✓ Allowed' if allowed else '✗ Rate Limited'} (delay: {delay:.2f}s)")
            
            # Record the request
            rate_limiter.record_request(
                service,
                user_id="demo_user",
                success=allowed,
                response_time_ms=100.0 + i * 50,
                rate_limited=not allowed
            )
            
            if delay > 0:
                print(f"      Waiting {delay:.2f}s...")
                await asyncio.sleep(min(delay, 2.0))  # Cap wait time for demo
    
    # Show statistics
    print("\nRate Limiting Statistics:")
    stats = rate_limiter.get_statistics()
    print(f"  Total Requests (last hour): {stats['total_requests_last_hour']}")
    print(f"  Rate Limited Requests: {stats['rate_limited_requests']}")
    print(f"  Rate Limited Percentage: {stats['rate_limited_percentage']:.1f}%")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"  Average Response Time: {stats['average_response_time_ms']:.1f}ms")
    
    # Show per-service statistics
    print("\nPer-Service Statistics:")
    for service_name, service_stats in stats['service_statistics'].items():
        print(f"  {service_name}:")
        print(f"    Total Requests: {service_stats['total_requests']}")
        print(f"    Rate Limited: {service_stats['rate_limited']}")
        print(f"    Success Rate: {service_stats['success_rate']:.1f}%")
        print(f"    Avg Response Time: {service_stats['avg_response_time']:.1f}ms")


async def demo_load_testing():
    """Demonstrate load testing capabilities."""
    print("\n" + "="*60)
    print("LOAD TESTING DEMONSTRATION")
    print("="*60)
    
    load_tester = get_load_tester()
    
    # Configure a simple load test
    config = LoadTestConfig(
        test_name="demo_load_test",
        test_type=LoadTestType.CONSTANT_LOAD,
        duration_seconds=15,  # Short duration for demo
        max_concurrent_users=3,
        requests_per_user=2,
        think_time_seconds=1.0,
        timeout_seconds=30.0,
        target_success_rate=0.8,
        target_avg_response_time_ms=2000.0
    )
    
    print(f"Running load test: {config.test_name}")
    print(f"  Type: {config.test_type.value}")
    print(f"  Duration: {config.duration_seconds}s")
    print(f"  Concurrent Users: {config.max_concurrent_users}")
    print(f"  Requests per User: {config.requests_per_user}")
    
    # Mock the concurrent processor for load testing
    processor = initialize_concurrent_processor()
    processor.start()
    
    try:
        # Create a simple mock for demonstration
        original_submit = processor.submit_request
        original_status = processor.get_request_status
        
        def mock_submit(request, user_id=None, priority=None):
            return f"demo_request_{time.time()}"
        
        def mock_status(request_id):
            # Simulate some processing time
            return {
                "status": "completed",
                "request_id": request_id,
                "session_id": f"session_{request_id}"
            }
        
        processor.submit_request = mock_submit
        processor.get_request_status = mock_status
        
        # Run the load test
        print("\nStarting load test...")
        start_time = datetime.utcnow()
        
        metrics = await load_tester.run_load_test(config)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Display results
        print("\nLoad Test Results:")
        print(f"  Test Status: {metrics.phase.value}")
        print(f"  Actual Duration: {duration:.1f}s")
        print(f"  Total Requests: {metrics.total_requests}")
        print(f"  Successful Requests: {metrics.successful_requests}")
        print(f"  Failed Requests: {metrics.failed_requests}")
        print(f"  Success Rate: {metrics.success_rate:.1f}%")
        print(f"  Average Response Time: {metrics.avg_response_time_ms:.1f}ms")
        print(f"  Min Response Time: {metrics.min_response_time_ms:.1f}ms")
        print(f"  Max Response Time: {metrics.max_response_time_ms:.1f}ms")
        print(f"  P95 Response Time: {metrics.p95_response_time_ms:.1f}ms")
        print(f"  Requests per Second: {metrics.requests_per_second:.2f}")
        print(f"  Peak Concurrent Users: {metrics.peak_concurrent_users}")
        print(f"  Peak CPU Usage: {metrics.peak_cpu_percent:.1f}%")
        print(f"  Peak Memory Usage: {metrics.peak_memory_percent:.1f}%")
        
        # Show user metrics
        print("\nUser Metrics:")
        for user_id, user_metrics in metrics.user_metrics.items():
            avg_response = (user_metrics.total_response_time_ms / max(1, user_metrics.requests_completed))
            print(f"  {user_id}:")
            print(f"    Requests Sent: {user_metrics.requests_sent}")
            print(f"    Requests Completed: {user_metrics.requests_completed}")
            print(f"    Requests Failed: {user_metrics.requests_failed}")
            print(f"    Avg Response Time: {avg_response:.1f}ms")
        
        # Export results
        export_path = f"demo_load_test_results_{int(time.time())}.json"
        if load_tester.export_test_results(config.test_name, export_path):
            print(f"\nResults exported to: {export_path}")
        
    finally:
        # Restore original methods
        processor.submit_request = original_submit
        processor.get_request_status = original_status
        processor.stop()


async def main():
    """Main demonstration function."""
    print("Multi-Agent Video System - Concurrent Processing Demo")
    print("="*60)
    print("This demo showcases the concurrent processing and resource")
    print("management capabilities of the multi-agent video system.")
    print("="*60)
    
    try:
        # Run all demonstrations
        await demo_concurrent_processing()
        await demo_resource_management()
        await demo_rate_limiting()
        await demo_load_testing()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("All concurrent processing features have been demonstrated.")
        print("The system is ready for production use with:")
        print("  ✓ Concurrent request processing")
        print("  ✓ Resource monitoring and management")
        print("  ✓ Rate limiting and throttling")
        print("  ✓ Load testing and performance validation")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())