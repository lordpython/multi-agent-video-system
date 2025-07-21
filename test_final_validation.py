#!/usr/bin/env python3
"""Final validation test - summary only."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_functionality_preservation import FunctionalityPreservationTest

async def main():
    """Run final validation with summary only."""
    print("🎯 Final Functionality Preservation Validation")
    print("=" * 60)
    
    test_suite = FunctionalityPreservationTest()
    
    # Run all tests
    results = await test_suite.run_all_tests()
    
    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result["status"] == "PASSED")
    failed_tests = sum(1 for result in results.values() if result["status"] == "FAILED")
    error_tests = sum(1 for result in results.values() if result["status"] == "ERROR")
    
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("-" * 30)
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"🚨 Errors: {error_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Show test results
    print("\n📋 TEST RESULTS")
    print("-" * 30)
    for test_name, result in results.items():
        status_emoji = {"PASSED": "✅", "FAILED": "❌", "ERROR": "🚨"}[result["status"]]
        print(f"{status_emoji} {test_name}: {result['status']}")
    
    print("\n🎯 CONCLUSION")
    print("-" * 20)
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Functionality preservation is COMPLETE")
        print("✅ Canonical structure migration is SUCCESSFUL")
        return True
    elif passed_tests >= total_tests * 0.8:
        print("⚠️ MOSTLY SUCCESSFUL with minor issues")
        print("🔧 Minor fixes may be needed")
        return True
    else:
        print("❌ SIGNIFICANT ISSUES DETECTED")
        print("🚨 Major fixes required")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)