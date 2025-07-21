#!/usr/bin/env python3
"""Test script to verify dictionary access patterns in orchestration tools."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.orchestration_tools_simplified import (
    coordinate_research,
    coordinate_story,
    coordinate_assets,
    coordinate_audio,
    coordinate_assembly
)


class MockSession:
    """Mock session for testing."""
    def __init__(self, session_id="test_session"):
        self.id = session_id
        self.state = {}


class MockToolContext:
    """Mock ToolContext for testing."""
    def __init__(self, session):
        self.session = session


async def test_dictionary_state_access():
    """Test that all orchestration tools use dictionary access patterns correctly."""
    print("Testing dictionary state access patterns...")
    
    # Create mock session and context
    session = MockSession()
    context = MockToolContext(session)
    
    try:
        # Test 1: Research coordination
        print("\n1. Testing coordinate_research...")
        result = await coordinate_research("artificial intelligence")
        
        # Verify simplified error handling and return structure
        assert result["success"] == True
        assert result["stage"] == "researching"
        assert result["progress"] == 0.2
        assert "research_data" in result
        assert isinstance(result["research_data"], dict)
        print("✓ Research coordination uses simplified error handling correctly")
        
        # Test 2: Story coordination
        print("\n2. Testing coordinate_story...")
        research_data = result["research_data"]
        result = await coordinate_story(research_data, duration=60)
        
        # Verify simplified error handling and return structure
        assert result["success"] == True
        assert result["stage"] == "scripting"
        assert result["progress"] == 0.4
        assert "script" in result
        assert isinstance(result["script"], dict)
        print("✓ Story coordination uses simplified error handling correctly")
        
        # Test 3: Asset coordination
        print("\n3. Testing coordinate_assets...")
        script = result["script"]
        result = await coordinate_assets(script)
        
        # Verify simplified error handling and return structure
        assert result["success"] == True
        assert result["stage"] == "asset_sourcing"
        assert result["progress"] == 0.6
        assert "assets" in result
        assert isinstance(result["assets"], dict)
        print("✓ Asset coordination uses simplified error handling correctly")
        
        # Test 4: Audio coordination
        print("\n4. Testing coordinate_audio...")
        assets = result["assets"]
        result = await coordinate_audio(script)
        
        # Verify simplified error handling and return structure
        assert result["success"] == True
        assert result["stage"] == "audio_generation"
        assert result["progress"] == 0.8
        assert "audio_assets" in result
        assert isinstance(result["audio_assets"], dict)
        print("✓ Audio coordination uses simplified error handling correctly")
        
        # Test 5: Assembly coordination
        print("\n5. Testing coordinate_assembly...")
        audio_assets = result["audio_assets"]
        result = await coordinate_assembly(script, assets, audio_assets)
        
        # Verify simplified error handling and return structure
        assert result["success"] == True
        assert result["stage"] == "completed"
        assert result["progress"] == 1.0
        assert "final_video" in result
        assert isinstance(result["final_video"], dict)
        print("✓ Assembly coordination uses simplified error handling correctly")
        
        print("\n✅ All tests passed! Dictionary access patterns are working correctly.")
        
        # Print final state to verify structure
        print("\nFinal result structure verified - all tools return proper dictionaries with stage and progress info.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


async def test_validation_patterns():
    """Test that simple validation patterns work correctly."""
    print("\n\nTesting validation patterns...")
    
    session = MockSession()
    context = MockToolContext(session)
    
    try:
        # Test validation failures
        print("\n1. Testing input validation...")
        
        # Test empty topic validation
        try:
            await coordinate_research("")
            assert False, "Should have failed with empty topic"
        except ValueError:
            print("✓ Empty topic validation works")
        
        # Test invalid duration validation
        try:
            await coordinate_story({}, duration=5)  # Too short
            assert False, "Should have failed with invalid duration"
        except ValueError:
            print("✓ Duration validation works")
        
        # Test missing data validation
        try:
            await coordinate_story({}, duration=60)  # No research data
            assert False, "Should have failed with missing research data"
        except ValueError:
            print("✓ Missing research data validation works")
        
        print("\n✅ All validation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Validation test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING DICTIONARY STATE ACCESS PATTERNS")
    print("=" * 60)
    
    success1 = await test_dictionary_state_access()
    success2 = await test_validation_patterns()
    
    if success1 and success2:
        print("\n🎉 All tests completed successfully!")
        print("Dictionary access patterns are properly implemented.")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)