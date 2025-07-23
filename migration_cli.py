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

"""CLI tool for managing session migration in the Multi-Agent Video System."""

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.json import JSON

# Add the video_system to the path
sys.path.insert(0, str(Path(__file__).parent / "video_system"))

from video_system.shared_libraries.adk_session_manager import get_session_manager
from video_system.shared_libraries.session_migration import get_migration_manager

console = Console()


@click.group()
def cli():
    """Session Migration Management CLI for Multi-Agent Video System."""
    pass


@cli.command()
def status():
    """Check migration status."""

    async def _status():
        try:
            session_manager = await get_session_manager()
            migration_status = await session_manager.get_migration_status()

            console.print("\n[bold blue]Session Migration Status[/bold blue]")
            console.print("=" * 50)

            # Display migration completion status
            if migration_status.get("runtime_migration", {}).get("completed"):
                console.print("[green]✓[/green] Migration check completed")
            else:
                console.print(
                    "[yellow]⏳[/yellow] Migration check in progress or not started"
                )

            # Display migration results
            runtime_results = migration_status.get("runtime_migration", {}).get(
                "results"
            )
            if runtime_results:
                if runtime_results.get("migration_needed"):
                    migrated = runtime_results.get("migrated_sessions", 0)
                    failed = runtime_results.get("failed_migrations", 0)
                    console.print(f"[green]Sessions migrated:[/green] {migrated}")
                    if failed > 0:
                        console.print(f"[red]Failed migrations:[/red] {failed}")
                else:
                    console.print("[green]✓[/green] No migration needed")

            # Display legacy path information
            legacy_paths = migration_status.get("legacy_paths_checked", [])
            if legacy_paths:
                console.print("\n[bold]Legacy Path Check:[/bold]")
                table = Table()
                table.add_column("Path")
                table.add_column("Exists")
                table.add_column("Files")

                for path_info in legacy_paths:
                    exists = "✓" if path_info["exists"] else "✗"
                    file_count = str(path_info.get("file_count", 0))
                    table.add_row(path_info["path"], exists, file_count)

                console.print(table)

            # Display last migration log
            if migration_status.get("last_migration"):
                console.print("\n[bold]Last Migration Log:[/bold]")
                last_migration = migration_status["last_migration"]

                info_table = Table()
                info_table.add_column("Field")
                info_table.add_column("Value")

                info_table.add_row(
                    "Started", last_migration.get("migration_started", "N/A")
                )
                info_table.add_row(
                    "Completed", last_migration.get("migration_completed", "N/A")
                )
                info_table.add_row(
                    "Total Sessions", str(last_migration.get("total_sessions", 0))
                )

                console.print(info_table)

                # Show results summary
                results = last_migration.get("results", [])
                if results:
                    success_count = len(
                        [r for r in results if r.get("status") == "success"]
                    )
                    error_count = len(
                        [r for r in results if r.get("status") == "error"]
                    )

                    console.print(
                        f"\n[green]Successful migrations:[/green] {success_count}"
                    )
                    console.print(f"[red]Failed migrations:[/red] {error_count}")

            # Display errors if any
            if runtime_results and runtime_results.get("errors"):
                console.print("\n[bold red]Migration Errors:[/bold red]")
                for error in runtime_results["errors"]:
                    console.print(f"[red]• {error}[/red]")

        except Exception as e:
            console.print(f"[red]Error checking migration status: {e}[/red]")
            sys.exit(1)

    asyncio.run(_status())


@cli.command()
@click.option("--confirm", is_flag=True, help="Confirm the remigration operation")
def remigrate(confirm):
    """Force remigration of sessions."""
    if not confirm:
        console.print(
            "[yellow]This will force remigration of all legacy sessions.[/yellow]"
        )
        console.print("[yellow]Use --confirm to proceed.[/yellow]")
        return

    async def _remigrate():
        try:
            console.print("[blue]Starting forced remigration...[/blue]")

            session_manager = await get_session_manager()
            results = await session_manager.force_remigration()

            if results.get("error"):
                console.print(f"[red]Migration failed: {results['error']}[/red]")
                sys.exit(1)

            console.print("\n[bold green]Remigration Results[/bold green]")
            console.print("=" * 30)

            if results.get("migration_needed"):
                migrated = results.get("migrated_sessions", 0)
                failed = results.get("failed_migrations", 0)

                console.print(f"[green]Sessions migrated:[/green] {migrated}")
                if failed > 0:
                    console.print(f"[red]Failed migrations:[/red] {failed}")

                    # Show errors
                    errors = results.get("errors", [])
                    if errors:
                        console.print("\n[bold red]Errors:[/bold red]")
                        for error in errors[:5]:  # Show first 5 errors
                            console.print(f"[red]• {error}[/red]")
                        if len(errors) > 5:
                            console.print(
                                f"[red]... and {len(errors) - 5} more errors[/red]"
                            )
            else:
                console.print("[green]✓[/green] No migration needed")

        except Exception as e:
            console.print(f"[red]Error during remigration: {e}[/red]")
            sys.exit(1)

    asyncio.run(_remigrate())


@cli.command()
def discover():
    """Discover legacy session data without migrating."""

    async def _discover():
        try:
            migration_manager = get_migration_manager()

            console.print("[blue]Discovering legacy session data...[/blue]")

            # Use internal discovery method
            legacy_sessions = await migration_manager._discover_legacy_sessions()

            console.print(
                f"\n[bold]Found {len(legacy_sessions)} legacy sessions[/bold]"
            )

            if legacy_sessions:
                table = Table()
                table.add_column("Session ID")
                table.add_column("User ID")
                table.add_column("Status")
                table.add_column("Progress")
                table.add_column("Created")

                for session in legacy_sessions[:10]:  # Show first 10
                    table.add_row(
                        session.session_id[:12] + "..."
                        if len(session.session_id) > 15
                        else session.session_id,
                        session.user_id or "N/A",
                        session.status or "unknown",
                        f"{session.progress:.1%}" if session.progress else "N/A",
                        str(session.created_at)[:19] if session.created_at else "N/A",
                    )

                console.print(table)

                if len(legacy_sessions) > 10:
                    console.print(
                        f"[dim]... and {len(legacy_sessions) - 10} more sessions[/dim]"
                    )
            else:
                console.print("[green]✓[/green] No legacy sessions found")

        except Exception as e:
            console.print(f"[red]Error discovering legacy sessions: {e}[/red]")
            sys.exit(1)

    asyncio.run(_discover())


@cli.command()
@click.option("--output", "-o", help="Output file for detailed migration log")
def log(output):
    """Show detailed migration log."""

    async def _log():
        try:
            migration_manager = get_migration_manager()
            status = await migration_manager.get_migration_status()

            last_migration = status.get("last_migration")
            if not last_migration:
                console.print("[yellow]No migration log found[/yellow]")
                return

            if output:
                # Save to file
                with open(output, "w") as f:
                    json.dump(last_migration, f, indent=2, default=str)
                console.print(f"[green]Migration log saved to {output}[/green]")
            else:
                # Display in console
                console.print("[bold]Migration Log Details[/bold]")
                console.print(JSON.from_data(last_migration))

        except Exception as e:
            console.print(f"[red]Error reading migration log: {e}[/red]")
            sys.exit(1)

    asyncio.run(_log())


@cli.command()
def cleanup():
    """Clean up migration artifacts and temporary files."""

    async def _cleanup():
        try:
            console.print("[blue]Cleaning up migration artifacts...[/blue]")

            # Clean up temporary migration files
            cleanup_paths = [
                Path("data/migration_log.json"),
                Path("data/.migration_completed"),
                Path("temp/session_states.json"),
                Path("cache/orchestration_sessions.json"),
            ]

            cleaned_count = 0
            for path in cleanup_paths:
                if path.exists():
                    try:
                        path.unlink()
                        console.print(f"[green]✓[/green] Removed {path}")
                        cleaned_count += 1
                    except Exception as e:
                        console.print(f"[red]✗[/red] Failed to remove {path}: {e}")

            if cleaned_count == 0:
                console.print("[green]✓[/green] No migration artifacts found")
            else:
                console.print(
                    f"\n[green]Cleaned up {cleaned_count} migration artifacts[/green]"
                )

        except Exception as e:
            console.print(f"[red]Error during cleanup: {e}[/red]")
            sys.exit(1)

    asyncio.run(_cleanup())


if __name__ == "__main__":
    cli()
