#!/usr/bin/env python3
"""
Test script to verify that the simplified system works after cleanup.
This tests that all imports work and basic functionality is available.
"""

import sys
import asyncio
from pathlib import Path

# Add the project to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all simplified imports work."""
    print("Testing imports...")
    
    try:
        # Test API import
        from video_system.api_simplified import app
        print("✓ API simplified import successful")
        
        # Test agent import
        from video_system.agent_simplified import root_agent_simplified
        print("✓ Agent simplified import successful")
        
        # Test orchestration tools import
        from video_system.orchestration_tools_simplified import coordinate_research_tool
        print("✓ Orchestration tools simplified import successful")
        
        # Test CLI import
        from video_system.cli import cli
        print("✓ CLI import successful")
        
        # Test main module import
        from video_system import root_agent
        print("✓ Main module import successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

async def test_basic_functionality():
    """Test basic functionality of simplified components."""
    print("\nTesting basic functionality...")
    
    try:
        # Test orchestration tool
        from video_system.orchestration_tools_simplified import coordinate_research
        
        result = await coordinate_research("test topic")
        assert result["success"] == True
        assert "research_data" in result
        print("✓ Research coordination tool works")
        
        # Test agent creation
        from video_system.agent_simplified import root_agent_simplified
        assert root_agent_simplified.name == "video_system_orchestrator_simplified"
        assert len(root_agent_simplified.tools) == 5
        print("✓ Root agent created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

def test_no_deleted_imports():
    """Test that deleted modules are not importable."""
    print("\nTesting that deleted modules are not accessible...")
    
    deleted_modules = [
        "video_system.shared_libraries.adk_session_manager",
        "video_system.shared_libraries.adk_session_models", 
        "video_system.shared_libraries.session_error_handling",
        "video_system.shared_libraries.session_migration",
        "video_system.shared_libraries.maintenance",
        "video_system.shared_libraries.progress_monitor"
    ]
    
    success = True
    for module in deleted_modules:
        try:
            __import__(module)
            print(f"✗ {module} should not be importable (it was deleted)")
            success = False
        except (ImportError, ModuleNotFoundError):
            print(f"✓ {module} correctly not importable")
    
    return success

async def main():
    """Run all tests."""
    print("=== Simplified System Cleanup Test ===\n")
    
    # Test imports
    imports_ok = test_imports()
    
    # Test functionality
    functionality_ok = await test_basic_functionality()
    
    # Test deleted modules
    deleted_ok = test_no_deleted_imports()
    
    # Summary
    print(f"\n=== Test Results ===")
    print(f"Imports: {'✓ PASS' if imports_ok else '✗ FAIL'}")
    print(f"Functionality: {'✓ PASS' if functionality_ok else '✗ FAIL'}")
    print(f"Deleted modules: {'✓ PASS' if deleted_ok else '✗ FAIL'}")
    
    all_passed = imports_ok and functionality_ok and deleted_ok
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)