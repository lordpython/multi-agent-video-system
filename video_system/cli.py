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
import json
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from dotenv import load_dotenv

from .shared_libraries.models import VideoGenerationRequest
from .shared_libraries.adk_session_manager import get_session_manager
from .shared_libraries.adk_session_models import VideoGenerationStage
from .shared_libraries.progress_monitor import get_progress_monitor
from .agent import initialize_video_system, root_agent
from .shared_libraries.logging_config import get_logger

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
@click.option('--prompt', '-p', required=True, help='Text prompt for video generation')
@click.option('--duration', '-d', default=60, type=int, help='Video duration in seconds (10-600)')
@click.option('--style', '-s', default='professional', 
              type=click.Choice(['professional', 'casual', 'educational', 'entertainment', 'documentary']),
              help='Video style')
@click.option('--voice', '-v', default='neutral', help='Voice preference for narration')
@click.option('--quality', '-q', default='high',
              type=click.Choice(['low', 'medium', 'high', 'ultra']),
              help='Video quality setting')
@click.option('--wait', '-w', is_flag=True, help='Wait for completion and show progress')
@click.option('--output', '-o', help='Output directory for generated video')
def generate(prompt: str, duration: int, style: str, voice: str, quality: str, 
            wait: bool, output: Optional[str]):
    """Generate a video from a text prompt."""
    try:
        console.print(f"[bold blue]Starting video generation...[/bold blue]")
        console.print(f"Prompt: {prompt}")
        console.print(f"Duration: {duration}s, Style: {style}, Quality: {quality}")
        
        # Initialize system
        initialize_video_system()
        
        # Create video generation request
        request = VideoGenerationRequest(
            prompt=prompt,
            duration_preference=duration,
            style=style,
            voice_preference=voice,
            quality=quality
        )
        
        # Start generation using the root agent (async)
        from .agent import start_video_generation
        result = asyncio.run(start_video_generation(
            prompt=prompt,
            duration_preference=duration,
            style=style,
            voice_preference=voice,
            quality=quality
        ))
        
        if not result.get('success'):
            console.print(f"[red]Failed to start video generation: {result.get('error_message')}[/red]")
            sys.exit(1)
        
        session_id = result['session_id']
        console.print(f"[green]Session created: {session_id}[/green]")
        
        # Now trigger the actual workflow execution (async)
        console.print("[blue]Starting video processing...[/blue]")
        from .agent import execute_complete_workflow
        workflow_result = asyncio.run(execute_complete_workflow(session_id))
        
        if workflow_result.get('success'):
            console.print("[green]Video processing started successfully![/green]")
        else:
            console.print(f"[yellow]Note: {workflow_result.get('error_message')}[/yellow]")
        
        if wait:
            asyncio.run(_wait_for_completion(session_id, output))
        else:
            console.print(f"[yellow]Use 'video-cli status {session_id}' to check progress[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--all', '-a', is_flag=True, help='Show all sessions')
@click.option('--watch', '-w', is_flag=True, help='Watch progress in real-time')
@click.option('--user', '-u', help='Filter by user ID')
@click.option('--status-filter', '-s', 
              type=click.Choice(['completed', 'failed', 'processing', 'queued']),
              help='Filter by status')
@click.option('--limit', '-l', type=int, default=10, help='Maximum number of sessions to show')
def status(session_id: Optional[str], all: bool, watch: bool, user: Optional[str], 
          status_filter: Optional[str], limit: int):
    """Check the status of video generation sessions."""
    try:
        asyncio.run(_status_async(session_id, all, watch, user, status_filter, limit))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _status_async(session_id: Optional[str], all: bool, watch: bool, 
                      user: Optional[str], status_filter: Optional[str], limit: int):
    """Async implementation of status command."""
    session_manager = await get_session_manager()
    progress_monitor = get_progress_monitor()
    
    if session_id:
        if watch:
            await _watch_session_progress(session_id)
        else:
            await _show_session_status(session_id)
    else:
        # Show sessions with filtering
        if all:
            limit = None  # No limit when showing all
        
        sessions = await session_manager.list_sessions(
            user_id=user, 
            limit=limit,
            status_filter=status_filter
        )
        
        if not sessions:
            filter_desc = []
            if user:
                filter_desc.append(f"user '{user}'")
            if status_filter:
                filter_desc.append(f"status '{status_filter}'")
            
            filter_text = " with " + " and ".join(filter_desc) if filter_desc else ""
            console.print(f"[yellow]No sessions found{filter_text}[/yellow]")
            return
        
        # Show title with filter information
        title_parts = ["Sessions"]
        if user:
            title_parts.append(f"for user '{user}'")
        if status_filter:
            title_parts.append(f"with status '{status_filter}'")
        if limit and len(sessions) >= limit:
            title_parts.append(f"(showing {limit} most recent)")
        
        title = " ".join(title_parts) + ":"
        console.print(f"[bold]{title}[/bold]")
        _display_sessions_table(sessions)


@cli.command()
@click.argument('session_id')
@click.option('--keep-files', is_flag=True, help='Keep intermediate files')
def cancel(session_id: str, keep_files: bool):
    """Cancel a video generation session."""
    try:
        asyncio.run(_cancel_async(session_id, keep_files))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _cancel_async(session_id: str, keep_files: bool):
    """Async implementation of cancel command."""
    session_manager = await get_session_manager()
    session = await session_manager.get_session(session_id)
    
    if not session:
        console.print(f"[red]Session {session_id} not found[/red]")
        sys.exit(1)
    
    # Update session status to cancelled
    from .shared_libraries.adk_session_models import VideoGenerationStage
    await session_manager.update_stage_and_progress(
        session_id, 
        VideoGenerationStage.FAILED,
        error_message="Cancelled by user"
    )
    
    console.print(f"[yellow]Session {session_id} cancelled[/yellow]")
    
    if not keep_files:
        await session_manager.delete_session(session_id, cleanup_files=True)
        console.print("[green]Session files cleaned up[/green]")


@cli.command()
@click.option('--max-age', default=24, type=int, help='Maximum age in hours for cleanup')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned up without doing it')
def cleanup(max_age: int, dry_run: bool):
    """Clean up old and completed sessions."""
    try:
        asyncio.run(_cleanup_async(max_age, dry_run))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _cleanup_async(max_age: int, dry_run: bool):
    """Async implementation of cleanup command."""
    session_manager = await get_session_manager()
    
    if dry_run:
        console.print(f"[yellow]Dry run: Would clean up sessions older than {max_age} hours[/yellow]")
        # TODO: Implement dry run logic
        return
    
    cleaned_count = await session_manager.cleanup_expired_sessions()
    console.print(f"[green]Cleaned up {cleaned_count} expired sessions[/green]")


@cli.command()
@click.option('--user', '-u', help='Filter by user ID')
@click.option('--status-filter', '-s', 
              type=click.Choice(['completed', 'failed', 'processing', 'queued']),
              help='Filter by status')
@click.option('--page', '-p', type=int, default=1, help='Page number')
@click.option('--page-size', type=int, default=20, help='Sessions per page')
def list(user: Optional[str], status_filter: Optional[str], page: int, page_size: int):
    """List video generation sessions with pagination and filtering."""
    try:
        asyncio.run(_list_async(user, status_filter, page, page_size))
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


async def _list_async(user: Optional[str], status_filter: Optional[str], page: int, page_size: int):
    """Async implementation of list command."""
    session_manager = await get_session_manager()
    
    # Get paginated results
    result = await session_manager.list_sessions_paginated(
        user_id=user,
        page=page,
        page_size=page_size,
        status_filter=status_filter
    )
    
    sessions = result["sessions"]
    pagination = result["pagination"]
    
    if not sessions:
        filter_desc = []
        if user:
            filter_desc.append(f"user '{user}'")
        if status_filter:
            filter_desc.append(f"status '{status_filter}'")
        
        filter_text = " with " + " and ".join(filter_desc) if filter_desc else ""
        console.print(f"[yellow]No sessions found{filter_text}[/yellow]")
        return
    
    # Show title with pagination info
    title_parts = ["Sessions"]
    if user:
        title_parts.append(f"for user '{user}'")
    if status_filter:
        title_parts.append(f"with status '{status_filter}'")
    
    title = " ".join(title_parts)
    console.print(f"[bold]{title}[/bold]")
    
    # Display sessions table
    _display_sessions_table(sessions)
    
    # Show pagination info
    pagination_text = f"Page {pagination['page']} of {pagination['total_pages']} "
    pagination_text += f"({pagination['total_count']} total sessions)"
    
    if pagination['has_prev'] or pagination['has_next']:
        pagination_text += " - Use "
        if pagination['has_prev']:
            pagination_text += f"--page {pagination['page'] - 1} for previous"
        if pagination['has_prev'] and pagination['has_next']:
            pagination_text += ", "
        if pagination['has_next']:
            pagination_text += f"--page {pagination['page'] + 1} for next"
    
    console.print(f"[dim]{pagination_text}[/dim]")


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
    session_manager = await get_session_manager()
    stats = await session_manager.get_statistics()
    
    # Create statistics panel
    stats_text = f"""
[bold]Session Statistics:[/bold]
• Total Sessions: {stats.total_sessions}
• Active Sessions: {stats.active_sessions}
• Completed Sessions: {stats.completed_sessions}
• Failed Sessions: {stats.failed_sessions}
"""
    
    if stats.average_completion_time:
        stats_text += f"• Average Completion Time: {stats.average_completion_time:.1f}s\n"
    
    console.print(Panel(stats_text.strip(), title="System Statistics"))
    
    # Check system health
    from .agent import check_orchestrator_health
    health = check_orchestrator_health()
    
    health_color = {
        "healthy": "green",
        "degraded": "yellow", 
        "unhealthy": "red"
    }.get(health["status"], "white")
    
    console.print(f"\n[bold]System Health:[/bold] [{health_color}]{health['status'].upper()}[/{health_color}]")
    
    if health.get("details"):
        details = health["details"]
        if "unhealthy_services" in details:
            console.print(f"[red]Unhealthy Services: {', '.join(details['unhealthy_services'])}[/red]")
        elif "message" in details:
            console.print(f"[green]{details['message']}[/green]")


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind the API server')
@click.option('--port', default=8000, type=int, help='Port to bind the API server')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def serve(host: str, port: int, reload: bool):
    """Start the FastAPI server for REST API access."""
    try:
        import uvicorn
        from .api import app
        
        console.print(f"[bold blue]Starting API server on {host}:{port}[/bold blue]")
        console.print(f"[yellow]API documentation available at http://{host}:{port}/docs[/yellow]")
        
        uvicorn.run(
            "video_system.api:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except ImportError:
        console.print("[red]FastAPI and uvicorn are required to run the API server[/red]")
        console.print("[yellow]Install with: pip install fastapi uvicorn[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error starting server: {str(e)}[/red]")
        sys.exit(1)


async def _wait_for_completion(session_id: str, output_dir: Optional[str]):
    """Wait for session completion with progress display."""
    session_manager = await get_session_manager()
    progress_monitor = get_progress_monitor()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Generating video...", total=100)
        
        while True:
            state = await session_manager.get_session_state(session_id)
            if not state:
                console.print(f"[red]Session {session_id} not found[/red]")
                return
            
            # Update progress
            progress_pct = int(state.progress * 100)
            progress.update(task, completed=progress_pct, 
                          description=f"Stage: {state.current_stage.value.replace('_', ' ').title()}")
            
            # Check if completed
            if state.is_completed():
                progress.update(task, completed=100)
                console.print(f"[green]✓ Video generation completed![/green]")
                
                # Show final video location
                if state.final_video:
                    video_path = state.final_video.file_path
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
                
            elif state.is_failed():
                console.print(f"[red]✗ Video generation failed: {state.error_message}[/red]")
                break
                
            elif state.current_stage == VideoGenerationStage.FAILED:
                console.print(f"[yellow]⚠ Video generation cancelled[/yellow]")
                break
            
            await asyncio.sleep(2)


async def _show_session_status(session_id: str):
    """Show detailed status for a specific session."""
    session_manager = await get_session_manager()
    progress_monitor = get_progress_monitor()
    
    state = await session_manager.get_session_state(session_id)
    if not state:
        console.print(f"[red]Session {session_id} not found[/red]")
        return
    
    # Get detailed progress
    progress_info = progress_monitor.get_session_progress(session_id)
    
    # Create status panel
    stage_value = state.current_stage.value
    status_value = "completed" if state.is_completed() else "failed" if state.is_failed() else "processing"
    
    status_text = f"""
[bold]Session ID:[/bold] {session_id}
[bold]Status:[/bold] {status_value.title()}
[bold]Stage:[/bold] {stage_value.replace('_', ' ').title()}
[bold]Progress:[/bold] {state.progress:.1%}
[bold]Created:[/bold] {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Updated:[/bold] {state.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    if state.estimated_completion:
        status_text += f"[bold]Estimated Completion:[/bold] {state.estimated_completion.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    if state.error_message:
        status_text += f"[bold red]Error:[/bold red] {state.error_message}\n"
    
    # Add request details
    status_text += f"""
[bold]Request Details:[/bold]
• Prompt: {state.request.prompt[:100]}{'...' if len(state.request.prompt) > 100 else ''}
• Duration: {state.request.duration_preference}s
• Style: {state.request.style}
• Quality: {state.request.quality}
"""
    
    console.print(Panel(status_text.strip(), title=f"Session Status"))
    
    # Show stage progress if available
    if progress_info and progress_info.get('stage_details'):
        _display_stage_progress(progress_info['stage_details'])


async def _show_all_sessions():
    """Show all sessions in a table."""
    session_manager = await get_session_manager()
    sessions = await session_manager.list_sessions()
    
    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return
    
    console.print(f"[bold]All Sessions ({len(sessions)} total):[/bold]")
    _display_sessions_table(sessions)


def _display_sessions_table(sessions):
    """Display sessions in a formatted table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Session ID", style="cyan", width=36)
    table.add_column("Status", style="green", width=12)
    table.add_column("Stage", style="yellow", width=15)
    table.add_column("Progress", style="blue", width=10)
    table.add_column("Created", style="white", width=16)
    table.add_column("Prompt", style="white")
    
    for state in sessions:
        # Color code status
        status_value = "completed" if state.is_completed() else "failed" if state.is_failed() else "processing"
        status_color = {
            "completed": "green",
            "failed": "red",
            "cancelled": "yellow",
            "processing": "blue",
            "queued": "cyan"
        }.get(status_value, "white")
        
        stage_value = state.current_stage.value
        
        table.add_row(
            state.session_id[:8] + "...",
            f"[{status_color}]{status_value.title()}[/{status_color}]",
            stage_value.replace('_', ' ').title(),
            f"{state.progress:.1%}",
            state.created_at.strftime('%m-%d %H:%M'),
            state.request.prompt[:50] + ("..." if len(state.request.prompt) > 50 else "")
        )
    
    console.print(table)


def _display_stage_progress(stage_details: Dict[str, Any]):
    """Display detailed stage progress."""
    table = Table(show_header=True, header_style="bold magenta", title="Stage Progress")
    table.add_column("Stage", style="cyan")
    table.add_column("Progress", style="green")
    table.add_column("Weight", style="yellow")
    table.add_column("Status", style="blue")
    
    for stage_name, details in stage_details.items():
        progress = details['progress']
        weight = details['weight']
        
        # Determine status
        if progress >= 1.0:
            status = "[green]Complete[/green]"
        elif progress > 0.0:
            status = "[yellow]In Progress[/yellow]"
        else:
            status = "[white]Pending[/white]"
        
        table.add_row(
            stage_name.replace('_', ' ').title(),
            f"{progress:.1%}",
            f"{weight:.1%}",
            status
        )
    
    console.print(table)


async def _watch_session_progress(session_id: str):
    """Watch session progress in real-time."""
    session_manager = await get_session_manager()
    
    async def generate_progress_display():
        while True:
            state = await session_manager.get_session_state(session_id)
            if not state:
                yield Panel("[red]Session not found[/red]", title="Error")
                break
            
            # Create progress display
            status_value = "completed" if state.is_completed() else "failed" if state.is_failed() else "processing"
            progress_text = f"""
[bold]Session:[/bold] {session_id[:8]}...
[bold]Status:[/bold] {status_value.title()}
[bold]Stage:[/bold] {state.current_stage.value.replace('_', ' ').title()}
[bold]Progress:[/bold] {state.progress:.1%}
[bold]Updated:[/bold] {state.updated_at.strftime('%H:%M:%S')}
"""
            
            if state.estimated_completion:
                progress_text += f"[bold]ETA:[/bold] {state.estimated_completion.strftime('%H:%M:%S')}\n"
            
            if state.error_message:
                progress_text += f"[bold red]Error:[/bold red] {state.error_message}\n"
            
            # Create progress bar
            progress_bar = "█" * int(state.progress * 20) + "░" * (20 - int(state.progress * 20))
            progress_text += f"\n[blue]{progress_bar}[/blue] {state.progress:.1%}"
            
            yield Panel(progress_text.strip(), title="Live Progress")
            
            # Check if completed
            if state.is_completed() or state.is_failed():
                break
            
            await asyncio.sleep(1)
    
    # For now, we'll use a simpler approach since Live doesn't work well with async generators
    while True:
        state = await session_manager.get_session_state(session_id)
        if not state:
            console.print("[red]Session not found[/red]")
            break
        
        # Clear screen and show progress
        console.clear()
        status_value = "completed" if state.is_completed() else "failed" if state.is_failed() else "processing"
        progress_text = f"""
[bold]Session:[/bold] {session_id[:8]}...
[bold]Status:[/bold] {status_value.title()}
[bold]Stage:[/bold] {state.current_stage.value.replace('_', ' ').title()}
[bold]Progress:[/bold] {state.progress:.1%}
[bold]Updated:[/bold] {state.updated_at.strftime('%H:%M:%S')}
"""
        
        if state.estimated_completion:
            progress_text += f"[bold]ETA:[/bold] {state.estimated_completion.strftime('%H:%M:%S')}\n"
        
        if state.error_message:
            progress_text += f"[bold red]Error:[/bold red] {state.error_message}\n"
        
        # Create progress bar
        progress_bar = "█" * int(state.progress * 20) + "░" * (20 - int(state.progress * 20))
        progress_text += f"\n[blue]{progress_bar}[/blue] {state.progress:.1%}"
        
        console.print(Panel(progress_text.strip(), title="Live Progress"))
        
        # Check if completed
        if state.is_completed() or state.is_failed():
            break
        
        await asyncio.sleep(1)


if __name__ == '__main__':
    cli()