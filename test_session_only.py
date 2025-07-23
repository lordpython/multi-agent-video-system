#!/usr/bin/env python3
"""Test only the session state management functionality."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_functionality_preservation import FunctionalityPreservationTest


async def main():
    """Test only session state management."""
    print("🧪 Testing Session State Management Only")
    print("=" * 50)

    test_suite = FunctionalityPreservationTest()
    result = await test_suite.test_session_state_management()

    print("=" * 50)
    print(f"Session state management test: {'✅ PASSED' if result else '❌ FAILED'}")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
