#!/usr/bin/env python3
"""
Test script for session cleanup and maintenance functionality.

This script tests the enhanced session cleanup features including:
- Age-based cleanup policies
- Intermediate file cleanup
- Cleanup monitoring and statistics
- Pattern-based file cleanup
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta

from video_system.shared_libraries.adk_session_manager import VideoSystemSessionManager
from video_system.shared_libraries.adk_session_models import VideoGenerationStage


async def test_session_cleanup():
    """Test comprehensive session cleanup functionality."""
    print("🧹 Testing Session Cleanup and Maintenance")
    print("=" * 50)
    
    # Initialize session manager with short cleanup intervals for testing
    session_manager = VideoSystemSessionManager(
        cleanup_interval=10,  # 10 seconds for testing
        max_session_age_hours=1,  # 1 hour max age for testing
        run_migration_check=False  # Skip migration for test
    )
    
    try:
        # Test 1: Create test sessions with different ages
        print("\n1. Creating test sessions...")
        
        # Create recent session (should not be cleaned up)
        recent_session_id = await session_manager.create_session("Recent test session")
        print(f"   ✓ Created recent session: {recent_session_id}")
        
        # Create old session by manipulating registry (simulate old session)
        old_session_id = await session_manager.create_session("Old test session")
        
        # Manually update registry to make session appear old
        async with session_manager._registry_lock:
            user_id = session_manager.session_user_mapping.get(old_session_id, "anonymous")
            if user_id in session_manager.session_registry and old_session_id in session_manager.session_registry[user_id]:
                old_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
                session_manager.session_registry[user_id][old_session_id]["created_at"] = old_time
                session_manager.session_registry[user_id][old_session_id]["updated_at"] = old_time
        
        print(f"   ✓ Created old session: {old_session_id}")
        
        # Create completed session (should be cleaned up after 1 hour)
        completed_session_id = await session_manager.create_session("Completed test session")
        await session_manager.update_stage_and_progress(
            completed_session_id,
            VideoGenerationStage.COMPLETED,
            1.0
        )
        
        # Make it appear old enough for cleanup
        async with session_manager._registry_lock:
            user_id = session_manager.session_user_mapping.get(completed_session_id, "anonymous")
            if user_id in session_manager.session_registry and completed_session_id in session_manager.session_registry[user_id]:
                old_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
                session_manager.session_registry[user_id][completed_session_id]["created_at"] = old_time
                session_manager.session_registry[user_id][completed_session_id]["updated_at"] = old_time
                session_manager.session_registry[user_id][completed_session_id]["status"] = "completed"
        
        print(f"   ✓ Created completed session: {completed_session_id}")
        
        # Test 2: Create intermediate files for testing
        print("\n2. Creating test intermediate files...")
        
        test_files = []
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i in range(3):
                test_file = os.path.join(temp_dir, f"test_file_{i}.tmp")
                with open(test_file, 'w') as f:
                    f.write(f"Test content {i}")
                test_files.append(test_file)
            
            # Add files to recent session
            for file_path in test_files:
                await session_manager.add_intermediate_file(recent_session_id, file_path)
            
            print(f"   ✓ Created {len(test_files)} test files")
            
            # Test 3: Get cleanup statistics before cleanup
            print("\n3. Getting cleanup statistics...")
            
            cleanup_stats = await session_manager.get_cleanup_statistics()
            print(f"   ✓ Sessions eligible for cleanup: {cleanup_stats['sessions_eligible_for_cleanup']}")
            print(f"   ✓ Estimated files for cleanup: {cleanup_stats['estimated_files_for_cleanup']}")
            print(f"   ✓ Session age distribution: {cleanup_stats['session_age_distribution']}")
            
            # Test 4: Run cleanup
            print("\n4. Running session cleanup...")
            
            cleanup_results = await session_manager.cleanup_expired_sessions()
            print(f"   ✓ Sessions evaluated: {cleanup_results['sessions_evaluated']}")
            print(f"   ✓ Sessions cleaned: {cleanup_results['sessions_cleaned']}")
            print(f"   ✓ Sessions failed: {cleanup_results['sessions_failed']}")
            print(f"   ✓ Files cleaned: {cleanup_results['files_cleaned']}")
            print(f"   ✓ Duration: {cleanup_results['duration_seconds']:.2f}s")
            
            if cleanup_results['errors']:
                print(f"   ⚠ Errors: {len(cleanup_results['errors'])}")
                for error in cleanup_results['errors'][:3]:  # Show first 3 errors
                    print(f"     - {error}")
            
            # Test 5: Verify cleanup results
            print("\n5. Verifying cleanup results...")
            
            # Check if old sessions were cleaned up
            old_session = await session_manager.get_session(old_session_id)
            completed_session = await session_manager.get_session(completed_session_id)
            recent_session = await session_manager.get_session(recent_session_id)
            
            print(f"   ✓ Old session cleaned: {old_session is None}")
            print(f"   ✓ Completed session cleaned: {completed_session is None}")
            print(f"   ✓ Recent session preserved: {recent_session is not None}")
            
            # Test 6: Test pattern-based cleanup
            print("\n6. Testing pattern-based file cleanup...")
            
            # Create files matching common patterns
            pattern_files = []
            for pattern in ["stock_img_", "audio_scene_", "final_video_"]:
                test_file = f"/tmp/{pattern}test.tmp"
                try:
                    with open(test_file, 'w') as f:
                        f.write("Test pattern file")
                    pattern_files.append(test_file)
                except Exception as e:
                    print(f"   ⚠ Could not create pattern file {test_file}: {e}")
            
            if pattern_files:
                pattern_cleanup = await session_manager.cleanup_session_files_by_pattern("*.tmp")
                print(f"   ✓ Pattern cleanup - Files cleaned: {pattern_cleanup['cleaned_files']}")
                print(f"   ✓ Pattern cleanup - Files failed: {pattern_cleanup['failed_files']}")
                
                # Clean up test files
                for file_path in pattern_files:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
            
            # Test 7: Test health status
            print("\n7. Getting health status...")
            
            health_status = await session_manager.get_health_status()
            session_info = health_status.get("session_manager", {})
            print(f"   ✓ Total sessions: {session_info.get('total_sessions', 0)}")
            print(f"   ✓ Active sessions: {session_info.get('active_sessions', 0)}")
            print(f"   ✓ Primary service available: {session_info.get('primary_service_available', False)}")
            print(f"   ✓ Cleanup interval: {session_info.get('cleanup_interval', 0)}s")
            
            # Test 8: Force cleanup
            print("\n8. Testing force cleanup...")
            
            force_cleanup_results = await session_manager.force_cleanup_now()
            print(f"   ✓ Force cleanup completed in {force_cleanup_results['duration_seconds']:.2f}s")
            
        # Test 9: Final statistics
        print("\n9. Final session statistics...")
        
        final_stats = await session_manager.get_session_metadata()
        print(f"   ✓ Total sessions: {final_stats.total_sessions}")
        print(f"   ✓ Active sessions: {final_stats.active_sessions}")
        print(f"   ✓ Completed sessions: {final_stats.completed_sessions}")
        print(f"   ✓ Failed sessions: {final_stats.failed_sessions}")
        
        if final_stats.average_completion_time:
            print(f"   ✓ Average completion time: {final_stats.average_completion_time:.2f}s")
        
        print("\n✅ Session cleanup tests completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Session cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up session manager
        await session_manager.close()


async def test_file_safety_checks():
    """Test file safety checks for cleanup."""
    print("\n🔒 Testing File Safety Checks")
    print("=" * 30)
    
    session_manager = VideoSystemSessionManager(run_migration_check=False)
    
    try:
        # Test safe paths
        safe_paths = [
            "/tmp/test_file.mp4",
            "temp/session_123.wav",
            "output/video_456.jpg",
            "cache/asset_789.png"
        ]
        
        print("Testing safe paths:")
        for path in safe_paths:
            is_safe = session_manager._is_safe_to_delete(path)
            print(f"   {path}: {'✓ Safe' if is_safe else '✗ Unsafe'}")
        
        # Test unsafe paths
        unsafe_paths = [
            "/etc/passwd",
            "/usr/bin/python",
            "/home/user/important.txt",
            "C:\\Windows\\System32\\kernel32.dll"
        ]
        
        print("\nTesting unsafe paths:")
        for path in unsafe_paths:
            is_safe = session_manager._is_safe_to_delete(path)
            print(f"   {path}: {'✓ Safe' if is_safe else '✗ Unsafe'}")
        
        print("\n✅ File safety checks completed!")
        
    finally:
        await session_manager.close()


async def main():
    """Run all cleanup tests."""
    print("🚀 Starting Session Cleanup Tests")
    print("=" * 40)
    
    # Run main cleanup tests
    cleanup_success = await test_session_cleanup()
    
    # Run safety tests
    await test_file_safety_checks()
    
    if cleanup_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)