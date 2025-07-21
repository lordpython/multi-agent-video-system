#!/usr/bin/env python3
"""
Test runner for canonical structure tests.

This script runs all tests that have been updated for the canonical structure.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_test_file(test_file):
    """Run a specific test file and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_file), 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True, cwd=project_root)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {test_file}: {e}")
        return False

def main():
    """Main test runner."""
    print("🧪 Running Canonical Structure Tests")
    print("=" * 60)
    
    # List of test files that have been updated for canonical structure
    canonical_test_files = [
        "tests/test_orchestration_integration.py",
        "tests/test_research_agent.py", 
        "tests/test_story_agent.py",
        "tests/test_asset_sourcing_agent.py",
        "tests/test_image_generation_agent.py",
        "tests/test_audio_agent.py",
        "tests/test_video_assembly_agent.py",
        "tests/test_api_integration.py",
        "tests/test_cli_integration.py",
        "tests/test_session_management.py",
        "tests/test_error_handling.py",
        "tests/test_models.py"
    ]
    
    results = {}
    
    for test_file in canonical_test_files:
        test_path = project_root / test_file
        if test_path.exists():
            results[test_file] = run_test_file(test_path)
        else:
            print(f"⚠️ Test file not found: {test_file}")
            results[test_file] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_file}")
    
    print(f"\n📈 Overall Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All canonical structure tests passed!")
        return 0
    else:
        print(f"⚠️ {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())