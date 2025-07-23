#!/usr/bin/env python3
"""Test script to verify CLI commands work with canonical structure."""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path for video_system imports
sys.path.insert(0, str(Path(__file__).parent))


async def test_cli_imports():
    """Test that CLI can import agents from canonical locations."""
    try:
        print("Testing CLI imports...")

        # Test importing the CLI
        from video_system.api.cli import cli, root_agent

        print("✓ CLI imported successfully")
        print(f"✓ CLI root agent: {root_agent.name}")

        # Test that CLI commands are available
        import click

        click.Context(cli)
        commands = list(cli.commands.keys())
        print(f"✓ Available CLI commands: {', '.join(commands)}")

        expected_commands = [
            "generate",
            "status",
            "cancel",
            "cleanup",
            "list",
            "stats",
            "serve",
        ]
        missing_commands = [cmd for cmd in expected_commands if cmd not in commands]
        if missing_commands:
            print(f"✗ Missing commands: {', '.join(missing_commands)}")
            return False

        print("✓ All expected CLI commands are available")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


async def test_cli_help():
    """Test that CLI help works."""
    try:
        print("\nTesting CLI help...")

        from video_system.api.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        if result.exit_code == 0:
            print("✓ CLI help command works")
            return True
        else:
            print(f"✗ CLI help failed with exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            return False

    except Exception as e:
        print(f"✗ CLI help test error: {e}")
        return False


async def test_cli_serve_help():
    """Test that CLI serve command help works."""
    try:
        print("\nTesting CLI serve help...")

        from video_system.api.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])

        if result.exit_code == 0:
            print("✓ CLI serve help command works")
            return True
        else:
            print(f"✗ CLI serve help failed with exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            return False

    except Exception as e:
        print(f"✗ CLI serve help test error: {e}")
        return False


async def test_api_module_path():
    """Test that the API module path is correct for uvicorn."""
    try:
        print("\nTesting API module path...")

        # Test that the module path used in CLI serve command is correct
        from video_system.api.endpoints import app

        print("✓ API endpoints module can be imported")
        print(f"✓ FastAPI app available: {app.title}")

        # Test the module path string that would be used by uvicorn
        module_path = "video_system.api.endpoints:app"
        module_name, app_name = module_path.split(":")

        # Try to import the module dynamically
        import importlib

        module = importlib.import_module(module_name)
        app_obj = getattr(module, app_name)

        print(f"✓ Module path '{module_path}' is valid")
        print(f"✓ App object type: {type(app_obj)}")

        return True

    except Exception as e:
        print(f"✗ API module path test error: {e}")
        return False


async def main():
    """Run all CLI tests."""
    print("=" * 60)
    print("Testing CLI with Canonical Structure")
    print("=" * 60)

    tests = [
        test_cli_imports,
        test_cli_help,
        test_cli_serve_help,
        test_api_module_path,
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✓ All {total} CLI tests passed!")
        print("✓ CLI works with canonical structure")
        return True
    else:
        print(f"✗ {total - passed} out of {total} CLI tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
