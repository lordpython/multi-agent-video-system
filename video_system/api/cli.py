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

"""Command-line interface for the Multi-Agent Video System.

This module provides CLI commands for video generation, status checking,
and system management following ADK patterns.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.panel import Panel
from dotenv import load_dotenv


# ADK imports with proper error handling
try:
    from google.adk.runners import Runner
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService, Session
    from google.genai.types import Content, Part

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

    # Mock objects for when ADK is not available
    class MockSession:
        def __init__(self, id, state):
            self.id = id
            self.state = state
            self.last_update_time = "N/A"

    class MockSessionService:
        """A mock session service that mimics the ADK's InMemorySessionService."""

        def __init__(self):
            self._sessions: Dict[str, Dict[str, Any]] = {}

        async def create_session(
            self, app_name: str, user_id: str, state: Dict[str, Any]
        ) -> MockSession:
            import uuid

            session_id = str(uuid.uuid4())
            self._sessions[session_id] = {
                "app_name": app_name,
                "user_id": user_id,
                "state": state,
            }
            return MockSession(id=session_id, state=state)

        async def get_session(
            self, app_name: str, user_id: str, session_id: str
        ) -> Optional[MockSession]:
            session_data = self._sessions.get(session_id)
            if (
                session_data
                and session_data["app_name"] == app_name
                and session_data["user_id"] == user_id
            ):
                return MockSession(id=session_id, state=session_data["state"])
            return None

        async def delete_session(self, app_name: str, user_id: str, session_id: str):
            if session_id in self._sessions:
                del self._sessions[session_id]

    # Assign mock objects to ADK names
    Session = MockSession
    InMemorySessionService = MockSessionService

    # Define dummy classes for other ADK components to avoid runtime errors
    class Runner:
        pass

    class LlmAgent:
        pass

    class Content:
        pass

    class Part:
        pass


# Replace your current SessionService logic with:
if ADK_AVAILABLE:
    session_service = InMemorySessionService()
else:
    # Keep your MockSessionService class as is
    session_service = MockSessionService()


from video_system.utils.logging_config import get_logger
from video_system.agents.video_orchestrator.agent import root_agent

# Load environment variables
load_dotenv()

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Multi-Agent Video System CLI - Generate videos from text prompts using AI agents."""
    pass


@cli.command()
@click.option("--prompt", "-p", required=True, help="Text prompt for video generation")
@click.option(
    "--duration", "-d", default=60, type=int, help="Video duration in seconds (10-600)"
)
@click.option(
    "--style",
    "-s",
    default="professional",
    type=click.Choice(
        ["professional", "casual", "educational", "entertainment", "documentary"]
    ),
    help="Video style",
)
@click.option("--voice", "-v", default="neutral", help="Voice preference for narration")
@click.option(
    "--quality",
    "-q",
    default="high",
    type=click.Choice(["low", "medium", "high", "ultra"]),
    help="Video quality setting",
)
@click.option(
    "--wait", "-w", is_flag=True, help="Wait for completion and show progress"
)
@click.option("--output", "-o", help="Output directory for generated video")
def generate(
    prompt: str,
    duration: int,
    style: str,
    voice: str,
    quality: str,
    wait: bool,
    output: Optional[str],
):
    """Generate a video from a text prompt."""
    try:
        asyncio.run(
            _generate_async(prompt, duration, style, voice, quality, wait, output)
        )
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _generate_async(
    prompt: str,
    duration: int,
    style: str,
    voice: str,
    quality: str,
    wait: bool,
    output: Optional[str],
):
    """Asynchronous implementation of the generate command."""
    console.print("[bold blue]Starting video generation...[/bold blue]")
    console.print(f"Prompt: {prompt}")
    console.print(f"Duration: {duration}s, Style: {style}, Quality: {quality}")

    if not ADK_AVAILABLE:
        console.print(
            "[red]ADK is not available. Please install google-adk to use video generation.[/red]"
        )
        sys.exit(1)

    session = await session_service.create_session(
        app_name="video-generation-system",
        user_id="cli-user",
        state={
            "prompt": prompt,
            "duration_preference": duration,
            "style": style,
            "voice_preference": voice,
            "quality": quality,
            "current_stage": "initializing",
            "progress": 0.0,
            "status": "processing",
        },
    )

    session_id = session.id
    console.print(f"[green]Session created: {session_id}[/green]")

    console.print("[blue]Starting video processing...[/blue]")
    processing_task = asyncio.create_task(
        _process_video_generation_cli(session_service, session_id, prompt)
    )

    if wait:
        # Wait for both the progress display and the processing task to complete.
        await asyncio.gather(
            _wait_for_completion(session_service, session_id, output), processing_task
        )
    else:
        console.print(
            f"[yellow]Use 'video-cli status {session_id}' to check progress[/yellow]"
        )
        # NOTE: Without --wait, the command will exit, and the OS will likely
        # terminate the async task. For true background execution, a
        # long-running service is required. This fix addresses the crash
        # and makes the --wait flag function correctly.


@cli.command()
@click.argument("session_id", required=False)
@click.option("--all", "-a", is_flag=True, help="Show all sessions")
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--user", "-u", help="Filter by user ID")
@click.option(
    "--status-filter",
    "-s",
    type=click.Choice(["completed", "failed", "processing", "queued"]),
    help="Filter by status",
)
@click.option(
    "--limit", "-l", type=int, default=10, help="Maximum number of sessions to show"
)
def status(
    session_id: Optional[str],
    all: bool,
    watch: bool,
    user: Optional[str],
    status_filter: Optional[str],
    limit: int,
):
    """Check the status of video generation sessions."""
    try:
        asyncio.run(_status_async(session_id, all, watch, user, status_filter, limit))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _status_async(
    session_id: Optional[str],
    all: bool,
    watch: bool,
    user: Optional[str],
    status_filter: Optional[str],
    limit: int,
):
    """Async implementation of status command."""
    async with httpx.AsyncClient() as client:
        if session_id:
            if watch:
                await _watch_session_progress(session_id)
            else:
                try:
                    response = await client.get(
                        f"http://localhost:8000/videos/{session_id}/status"
                    )
                    response.raise_for_status()
                    console.print(response.json())
                except httpx.HTTPStatusError as e:
                    console.print(
                        f"[red]Error: {e.response.status_code} - {e.response.text}[/red]"
                    )
        else:
            try:
                response = await client.get("http://localhost:8000/videos/list")
                response.raise_for_status()
                sessions = response.json().get("sessions", [])

                table = Table(title="Video Generation Sessions")
                table.add_column(
                    "Session ID", justify="left", style="cyan", no_wrap=True
                )
                table.add_column("Status", justify="left", style="magenta")
                table.add_column("Stage", justify="left", style="green")
                table.add_column("Progress", justify="right", style="yellow")
                table.add_column("Created At", justify="left", style="blue")

                for session in sessions:
                    table.add_row(
                        session["session_id"],
                        session["status"],
                        session["stage"],
                        f"{session['progress']:.1%}",
                        session["created_at"],
                    )

                console.print(table)
            except httpx.HTTPStatusError as e:
                console.print(
                    f"[red]Error: {e.response.status_code} - {e.response.text}[/red]"
                )


@cli.command()
@click.argument("session_id")
@click.option("--keep-files", is_flag=True, help="Keep intermediate files")
def cancel(session_id: str, keep_files: bool):
    """Cancel a video generation session."""
    try:
        asyncio.run(_cancel_async(session_id, keep_files))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _cancel_async(session_id: str, keep_files: bool):
    """Async implementation of cancel command."""
    if not ADK_AVAILABLE:
        console.print("[red]ADK is not available. Cannot cancel session.[/red]")
        return

    session = await session_service.get_session(
        app_name="video-generation-system", user_id="cli-user", session_id=session_id
    )

    if not session:
        console.print(f"[red]Session {session_id} not found[/red]")
        sys.exit(1)

    # Update session status to cancelled
    session.state["current_stage"] = "failed"
    session.state["error_message"] = "Cancelled by user"
    session.state["progress"] = 0.0

    console.print(f"[yellow]Session {session_id} cancelled[/yellow]")

    if not keep_files:
        await session_service.delete_session(
            app_name="video-generation-system",
            user_id="cli-user",
            session_id=session_id,
        )
        console.print("[green]Session cleaned up[/green]")


@cli.command()
@click.option(
    "--max-age", default=24, type=int, help="Maximum age in hours for cleanup"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be cleaned up without doing it"
)
def cleanup(max_age: int, dry_run: bool):
    """Clean up old and completed sessions."""
    try:
        asyncio.run(_cleanup_async(max_age, dry_run))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _cleanup_async(max_age: int, dry_run: bool):
    """Async implementation of cleanup command."""
    if dry_run:
        console.print("[yellow]Dry run: Not actually cleaning up sessions.[/yellow]")
        # In a real dry run, you would list the sessions that would be deleted.
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://localhost:8000/system/cleanup?max_age_hours={max_age}"
            )
            response.raise_for_status()
            cleaned_count = response.json().get("cleaned_count", 0)
            console.print(
                f"[green]Cleaned up {cleaned_count} sessions older than {max_age} hours.[/green]"
            )
        except httpx.HTTPStatusError as e:
            console.print(
                f"[red]Error: {e.response.status_code} - {e.response.text}[/red]"
            )


@cli.command()
@click.option("--user", "-u", help="Filter by user ID")
@click.option(
    "--status-filter",
    "-s",
    type=click.Choice(["completed", "failed", "processing", "queued"]),
    help="Filter by status",
)
@click.option("--page", "-p", type=int, default=1, help="Page number")
@click.option("--page-size", type=int, default=20, help="Sessions per page")
def list(user: Optional[str], status_filter: Optional[str], page: int, page_size: int):
    """List video generation sessions with pagination and filtering."""
    try:
        asyncio.run(_list_async(user, status_filter, page, page_size))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _list_async(
    user: Optional[str], status_filter: Optional[str], page: int, page_size: int
):
    """Async implementation of list command."""
    async with httpx.AsyncClient() as client:
        try:
            params = {
                "user_id": user,
                "status": status_filter,
                "page": page,
                "page_size": page_size,
            }
            # Filter out None values
            params = {k: v for k, v in params.items() if v is not None}

            response = await client.get(
                "http://localhost:8000/videos/list", params=params
            )
            response.raise_for_status()
            sessions = response.json().get("sessions", [])

            table = Table(title="Video Generation Sessions")
            table.add_column("Session ID", justify="left", style="cyan", no_wrap=True)
            table.add_column("Status", justify="left", style="magenta")
            table.add_column("Stage", justify="left", style="green")
            table.add_column("Progress", justify="right", style="yellow")
            table.add_column("Created At", justify="left", style="blue")

            for session in sessions:
                table.add_row(
                    session["session_id"],
                    session["status"],
                    session["stage"],
                    f"{session['progress']:.1%}",
                    session["created_at"],
                )

            console.print(table)
        except httpx.HTTPStatusError as e:
            console.print(
                f"[red]Error: {e.response.status_code} - {e.response.text}[/red]"
            )


@cli.command()
def stats():
    """Show system statistics and health information."""
    try:
        asyncio.run(_stats_async())
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _stats_async():
    """Async implementation of stats command."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/system/stats")
            response.raise_for_status()
            stats_data = response.json()

            table = Table(title="System Statistics")
            table.add_column("Metric", justify="left", style="cyan")
            table.add_column("Value", justify="left", style="magenta")

            table.add_row("Total Sessions", str(stats_data.get("total_sessions", 0)))

            status_distribution = stats_data.get("status_distribution", {})
            for status, count in status_distribution.items():
                table.add_row(f"Sessions ({status})", str(count))

            console.print(table)
        except httpx.HTTPStatusError as e:
            console.print(
                f"[red]Error: {e.response.status_code} - {e.response.text}[/red]"
            )


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the API server")
@click.option("--port", default=8000, type=int, help="Port to bind the API server")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the FastAPI server for REST API access."""
    try:
        import uvicorn

        console.print(f"[bold blue]Starting API server on {host}:{port}[/bold blue]")
        console.print(
            f"[yellow]API documentation available at http://{host}:{port}/docs[/yellow]"
        )

        uvicorn.run(
            "video_system.api.endpoints:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )

    except ImportError:
        console.print(
            "[red]FastAPI and uvicorn are required to run the API server[/red]"
        )
        console.print("[yellow]Install with: pip install fastapi uvicorn[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error starting server: {str(e)}[/red]")
        sys.exit(1)


# Function removed - replaced with _show_session_status_simplified


# Obsolete functions removed - replaced with simplified versions


async def _process_video_generation_cli(session_service, session_id: str, prompt: str):
    """Background task to process video generation using ADK Runner for CLI."""
    try:
        logger.info(f"Starting CLI video generation for session {session_id}")

        # Retrieve session
        session = await session_service.get_session(
            app_name="video-generation-system",
            user_id="cli-user",
            session_id=session_id,
        )

        if not session:
            logger.error(f"Session {session_id} not found")
            return

        # Create ADK Runner with simplified root agent
        runner = Runner(
            agent=root_agent,
            app_name="video-generation-system",
            session_service=session_service,
        )

        # Create user message for the agent
        user_message = Content(parts=[Part(text=f"Generate video: {prompt}")])

        # Execute agent using ADK Runner
        logger.info(f"Invoking root agent for session {session_id}")
        async for event in runner.run_async(
            user_id="cli-user", session_id=session.id, new_message=user_message
        ):
            if event.is_final_response():
                logger.info(f"Agent completed processing for session {session_id}")
                # Final response indicates completion - state is automatically updated by ADK
                break

        logger.info(f"Completed CLI video generation for session {session_id}")

    except Exception as e:
        logger.error(f"Error in CLI video generation for session {session_id}: {e}")


async def _wait_for_completion(
    session_service, session_id: str, output_dir: Optional[str]
):
    """Wait for session completion with progress display using simplified patterns."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating video...", total=100)

        while True:
            session = await session_service.get_session(
                app_name="video-generation-system",
                user_id="cli-user",
                session_id=session_id,
            )

            if not session:
                console.print(f"[red]Session {session_id} not found[/red]")
                return

            state = session.state
            current_stage = state.get("current_stage", "unknown")
            progress_pct = int(state.get("progress", 0.0) * 100)
            error_message = state.get("error_message")

            # Update progress
            progress.update(
                task,
                completed=progress_pct,
                description=f"Stage: {current_stage.replace('_', ' ').title()}",
            )

            # Check if completed
            if current_stage == "completed":
                progress.update(task, completed=100)
                console.print("[green]✓ Video generation completed![/green]")

                # Show final video location
                final_video = state.get("final_video")
                if final_video and final_video.get("file_path"):
                    video_path = final_video["file_path"]
                    console.print(f"[blue]Video saved to: {video_path}[/blue]")

                    # Copy to output directory if specified
                    if output_dir:
                        import shutil

                        output_path = Path(output_dir)
                        output_path.mkdir(parents=True, exist_ok=True)
                        final_path = output_path / Path(video_path).name
                        shutil.copy2(video_path, final_path)
                        console.print(f"[green]Video copied to: {final_path}[/green]")

                break

            elif current_stage == "failed" or error_message:
                console.print(
                    f"[red]✗ Video generation failed: {error_message or 'Unknown error'}[/red]"
                )
                break

            await asyncio.sleep(2)


async def _show_session_status(session_id: str):
    """Show detailed status for a specific session using simplified patterns."""
    session = await session_service.get_session(
        app_name="video-generation-system", user_id="cli-user", session_id=session_id
    )

    if not session:
        console.print(f"[red]Session {session_id} not found[/red]")
        return

    state = session.state
    current_stage = state.get("current_stage", "unknown")
    progress = state.get("progress", 0.0)
    error_message = state.get("error_message")

    # Determine status
    if error_message:
        status = "failed"
    elif current_stage == "completed":
        status = "completed"
    elif current_stage == "failed":
        status = "failed"
    else:
        status = "processing"

    # Create status panel
    status_text = f"""
[bold]Session ID:[/bold] {session_id}
[bold]Status:[/bold] {status.title()}
[bold]Stage:[/bold] {current_stage.replace("_", " ").title()}
[bold]Progress:[/bold] {progress:.1%}
[bold]Updated:[/bold] {session.last_update_time}
"""

    if error_message:
        status_text += f"[bold red]Error:[/bold red] {error_message}\n"

    # Add request details
    status_text += f"""
[bold]Request Details:[/bold]
• Prompt: {state.get("prompt", "N/A")[:100]}{"..." if len(state.get("prompt", "")) > 100 else ""}
• Duration: {state.get("duration_preference", "N/A")}s
• Style: {state.get("style", "N/A")}
• Quality: {state.get("quality", "N/A")}
"""

    console.print(Panel(status_text.strip(), title="Session Status"))


async def _watch_session_progress(session_id: str):
    """Watch session progress in real-time using simplified patterns."""
    while True:
        session = await session_service.get_session(
            app_name="video-generation-system",
            user_id="cli-user",
            session_id=session_id,
        )

        if not session:
            console.print("[red]Session not found[/red]")
            break

        state = session.state
        current_stage = state.get("current_stage", "unknown")
        progress = state.get("progress", 0.0)
        error_message = state.get("error_message")

        # Clear screen and show progress
        console.clear()

        # Determine status
        if error_message:
            status = "failed"
        elif current_stage == "completed":
            status = "completed"
        elif current_stage == "failed":
            status = "failed"
        else:
            status = "processing"

        progress_text = f"""
[bold]Session:[/bold] {session_id[:8]}...
[bold]Status:[/bold] {status.title()}
[bold]Stage:[/bold] {current_stage.replace("_", " ").title()}
[bold]Progress:[/bold] {progress:.1%}
[bold]Updated:[/bold] {session.last_update_time}
"""

        if error_message:
            progress_text += f"[bold red]Error:[/bold red] {error_message}\n"

        # Create progress bar
        progress_bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
        progress_text += f"\n[blue]{progress_bar}[/blue] {progress:.1%}"

        console.print(Panel(progress_text.strip(), title="Live Progress"))

        # Check if completed
        if current_stage in ["completed", "failed"] or error_message:
            break

        await asyncio.sleep(1)


if __name__ == "__main__":
    cli()