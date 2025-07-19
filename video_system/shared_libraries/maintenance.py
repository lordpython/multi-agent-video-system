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

"""Cleanup and maintenance utilities for the Multi-Agent Video System.

This module provides cleanup and maintenance functionality for managing
temporary files, expired sessions, and system resources.
"""

import os
import shutil
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import psutil
import logging

from .session_manager import SessionManager, get_session_manager
from .models import VideoStatus
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CleanupStats:
    """Statistics from cleanup operations."""
    files_deleted: int = 0
    directories_deleted: int = 0
    bytes_freed: int = 0
    sessions_cleaned: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class SystemHealth:
    """System health information."""
    disk_usage_percent: float
    memory_usage_percent: float
    cpu_usage_percent: float
    active_sessions: int
    total_sessions: int
    storage_size_mb: float
    temp_files_count: int
    temp_files_size_mb: float


class MaintenanceManager:
    """Manages cleanup and maintenance operations for the video system."""
    
    def __init__(self, session_manager: Optional[SessionManager] = None,
                 temp_dir: Optional[str] = None,
                 max_disk_usage: float = 85.0,
                 max_memory_usage: float = 90.0):
        """Initialize maintenance manager.
        
        Args:
            session_manager: Session manager instance
            temp_dir: Temporary directory path (defaults to ./temp)
            max_disk_usage: Maximum disk usage percentage before cleanup
            max_memory_usage: Maximum memory usage percentage before cleanup
        """
        self.session_manager = session_manager or get_session_manager()
        self.temp_dir = Path(temp_dir or "./temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.max_disk_usage = max_disk_usage
        self.max_memory_usage = max_memory_usage
        
        # Cleanup configuration
        self.cleanup_config = {
            "expired_sessions_hours": 24,
            "temp_files_hours": 6,
            "failed_sessions_hours": 12,
            "completed_sessions_hours": 48,
            "log_files_days": 7
        }
        
        # Maintenance thread
        self.maintenance_thread = None
        self.maintenance_interval = 3600  # 1 hour
        self.running = False
        
        logger.info(f"MaintenanceManager initialized with temp_dir: {self.temp_dir}")
    
    def start_maintenance(self, interval: int = 3600):
        """Start automatic maintenance operations.
        
        Args:
            interval: Maintenance interval in seconds
        """
        if self.running:
            logger.warning("Maintenance already running")
            return
        
        self.maintenance_interval = interval
        self.running = True
        
        def maintenance_loop():
            while self.running:
                try:
                    self.run_maintenance()
                    time.sleep(self.maintenance_interval)
                except Exception as e:
                    logger.error(f"Error in maintenance loop: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        self.maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
        self.maintenance_thread.start()
        
        logger.info(f"Started automatic maintenance with {interval}s interval")
    
    def stop_maintenance(self):
        """Stop automatic maintenance operations."""
        self.running = False
        if self.maintenance_thread:
            self.maintenance_thread.join(timeout=5)
        logger.info("Stopped automatic maintenance")
    
    def run_maintenance(self) -> Dict[str, Any]:
        """Run comprehensive maintenance operations.
        
        Returns:
            Dictionary with maintenance results
        """
        logger.info("Starting maintenance operations")
        start_time = time.time()
        
        results = {
            "start_time": datetime.utcnow().isoformat(),
            "operations": {}
        }
        
        try:
            # Check system health
            health = self.get_system_health()
            results["system_health"] = health.__dict__
            
            # Clean up expired sessions
            session_stats = self.cleanup_expired_sessions()
            results["operations"]["session_cleanup"] = session_stats.__dict__
            
            # Clean up temporary files
            temp_stats = self.cleanup_temp_files()
            results["operations"]["temp_cleanup"] = temp_stats.__dict__
            
            # Clean up log files
            log_stats = self.cleanup_log_files()
            results["operations"]["log_cleanup"] = log_stats.__dict__
            
            # Optimize storage if needed
            if health.disk_usage_percent > self.max_disk_usage:
                storage_stats = self.optimize_storage()
                results["operations"]["storage_optimization"] = storage_stats.__dict__
            
            # Calculate total cleanup stats
            total_stats = CleanupStats()
            for op_stats in results["operations"].values():
                if isinstance(op_stats, dict):
                    total_stats.files_deleted += op_stats.get("files_deleted", 0)
                    total_stats.directories_deleted += op_stats.get("directories_deleted", 0)
                    total_stats.bytes_freed += op_stats.get("bytes_freed", 0)
                    total_stats.sessions_cleaned += op_stats.get("sessions_cleaned", 0)
                    total_stats.errors.extend(op_stats.get("errors", []))
            
            results["total_stats"] = total_stats.__dict__
            results["duration_seconds"] = time.time() - start_time
            results["status"] = "completed"
            
            logger.info(f"Maintenance completed in {results['duration_seconds']:.2f}s: "
                       f"{total_stats.files_deleted} files, {total_stats.bytes_freed} bytes freed")
            
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"Maintenance failed: {e}")
        
        return results
    
    def cleanup_expired_sessions(self) -> CleanupStats:
        """Clean up expired sessions based on configuration.
        
        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        
        try:
            # Get all sessions
            sessions = self.session_manager.list_sessions()
            now = datetime.utcnow()
            
            for session in sessions:
                should_delete = False
                age_hours = (now - session.updated_at).total_seconds() / 3600
                
                # Check deletion criteria
                if session.status == VideoStatus.FAILED:
                    should_delete = age_hours > self.cleanup_config["failed_sessions_hours"]
                elif session.status == VideoStatus.COMPLETED:
                    should_delete = age_hours > self.cleanup_config["completed_sessions_hours"]
                elif session.status in [VideoStatus.CANCELLED]:
                    should_delete = age_hours > self.cleanup_config["expired_sessions_hours"]
                
                if should_delete:
                    try:
                        # Get project state to calculate freed space
                        project_state = self.session_manager.get_project_state(session.session_id)
                        if project_state:
                            for file_path in project_state.intermediate_files:
                                if os.path.exists(file_path):
                                    stats.bytes_freed += os.path.getsize(file_path)
                                    stats.files_deleted += 1
                        
                        # Delete session
                        if self.session_manager.delete_session(session.session_id, cleanup_files=True):
                            stats.sessions_cleaned += 1
                            logger.debug(f"Cleaned up expired session {session.session_id}")
                        
                    except Exception as e:
                        error_msg = f"Failed to cleanup session {session.session_id}: {e}"
                        stats.errors.append(error_msg)
                        logger.warning(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to cleanup expired sessions: {e}"
            stats.errors.append(error_msg)
            logger.error(error_msg)
        
        return stats
    
    def cleanup_temp_files(self) -> CleanupStats:
        """Clean up temporary files older than configured threshold.
        
        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        
        try:
            cutoff_time = time.time() - (self.cleanup_config["temp_files_hours"] * 3600)
            
            for root, dirs, files in os.walk(self.temp_dir):
                # Clean up files
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            stats.files_deleted += 1
                            stats.bytes_freed += file_size
                            logger.debug(f"Deleted temp file: {file_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete temp file {file_path}: {e}"
                        stats.errors.append(error_msg)
                
                # Clean up empty directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if os.path.getmtime(dir_path) < cutoff_time and not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            stats.directories_deleted += 1
                            logger.debug(f"Deleted empty temp directory: {dir_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete temp directory {dir_path}: {e}"
                        stats.errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to cleanup temp files: {e}"
            stats.errors.append(error_msg)
            logger.error(error_msg)
        
        return stats
    
    def cleanup_log_files(self) -> CleanupStats:
        """Clean up old log files.
        
        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        
        try:
            log_dir = Path("./logs")
            if not log_dir.exists():
                return stats
            
            cutoff_time = time.time() - (self.cleanup_config["log_files_days"] * 24 * 3600)
            
            for log_file in log_dir.glob("*.log*"):
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        stats.files_deleted += 1
                        stats.bytes_freed += file_size
                        logger.debug(f"Deleted old log file: {log_file}")
                except Exception as e:
                    error_msg = f"Failed to delete log file {log_file}: {e}"
                    stats.errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to cleanup log files: {e}"
            stats.errors.append(error_msg)
            logger.error(error_msg)
        
        return stats
    
    def optimize_storage(self) -> CleanupStats:
        """Optimize storage by removing oldest completed sessions.
        
        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        
        try:
            # Get completed sessions sorted by age
            sessions = self.session_manager.list_sessions(status=VideoStatus.COMPLETED)
            sessions.sort(key=lambda s: s.updated_at)
            
            # Remove oldest sessions until disk usage is acceptable
            for session in sessions:
                health = self.get_system_health()
                if health.disk_usage_percent <= self.max_disk_usage:
                    break
                
                try:
                    # Calculate space that will be freed
                    project_state = self.session_manager.get_project_state(session.session_id)
                    if project_state:
                        for file_path in project_state.intermediate_files:
                            if os.path.exists(file_path):
                                stats.bytes_freed += os.path.getsize(file_path)
                                stats.files_deleted += 1
                    
                    # Delete session
                    if self.session_manager.delete_session(session.session_id, cleanup_files=True):
                        stats.sessions_cleaned += 1
                        logger.info(f"Optimized storage by removing session {session.session_id}")
                
                except Exception as e:
                    error_msg = f"Failed to optimize session {session.session_id}: {e}"
                    stats.errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to optimize storage: {e}"
            stats.errors.append(error_msg)
            logger.error(error_msg)
        
        return stats
    
    def get_system_health(self) -> SystemHealth:
        """Get current system health information.
        
        Returns:
            System health data
        """
        try:
            # Disk usage
            disk_usage = psutil.disk_usage('.')
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            
            # CPU usage
            cpu_usage_percent = psutil.cpu_percent(interval=1)
            
            # Session statistics
            session_stats = self.session_manager.get_statistics()
            active_sessions = session_stats.get("active_sessions", 0)
            total_sessions = session_stats.get("total_sessions", 0)
            
            # Storage size
            storage_size_mb = self._get_directory_size(self.session_manager.storage_path) / (1024 * 1024)
            
            # Temp files
            temp_files_count, temp_files_size = self._get_temp_files_info()
            temp_files_size_mb = temp_files_size / (1024 * 1024)
            
            return SystemHealth(
                disk_usage_percent=disk_usage_percent,
                memory_usage_percent=memory_usage_percent,
                cpu_usage_percent=cpu_usage_percent,
                active_sessions=active_sessions,
                total_sessions=total_sessions,
                storage_size_mb=storage_size_mb,
                temp_files_count=temp_files_count,
                temp_files_size_mb=temp_files_size_mb
            )
        
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return SystemHealth(0, 0, 0, 0, 0, 0, 0, 0)
    
    def force_cleanup_session(self, session_id: str) -> bool:
        """Force cleanup of a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if cleaned up successfully
        """
        try:
            return self.session_manager.delete_session(session_id, cleanup_files=True)
        except Exception as e:
            logger.error(f"Failed to force cleanup session {session_id}: {e}")
            return False
    
    def cleanup_orphaned_files(self, directory: str) -> CleanupStats:
        """Clean up orphaned files in a directory.
        
        Args:
            directory: Directory to clean up
            
        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return stats
            
            # Get all active session IDs
            active_sessions = set()
            for session in self.session_manager.list_sessions():
                active_sessions.add(session.session_id)
            
            # Check files for orphaned session references
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    try:
                        # Check if filename contains a session ID that's no longer active
                        filename = file_path.name
                        for session_id in active_sessions:
                            if session_id in filename:
                                break
                        else:
                            # File doesn't belong to any active session
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            stats.files_deleted += 1
                            stats.bytes_freed += file_size
                            logger.debug(f"Deleted orphaned file: {file_path}")
                    
                    except Exception as e:
                        error_msg = f"Failed to check/delete file {file_path}: {e}"
                        stats.errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to cleanup orphaned files in {directory}: {e}"
            stats.errors.append(error_msg)
            logger.error(error_msg)
        
        return stats
    
    def get_maintenance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive maintenance report.
        
        Returns:
            Maintenance report dictionary
        """
        try:
            health = self.get_system_health()
            session_stats = self.session_manager.get_statistics()
            
            # Calculate recommendations
            recommendations = []
            if health.disk_usage_percent > self.max_disk_usage:
                recommendations.append("High disk usage - consider running storage optimization")
            if health.memory_usage_percent > self.max_memory_usage:
                recommendations.append("High memory usage - consider restarting services")
            if health.temp_files_count > 1000:
                recommendations.append("Large number of temp files - consider cleanup")
            if session_stats["total_sessions"] > 10000:
                recommendations.append("Large number of sessions - consider archiving old sessions")
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "system_health": health.__dict__,
                "session_statistics": session_stats,
                "maintenance_config": self.cleanup_config,
                "recommendations": recommendations,
                "maintenance_running": self.running
            }
        
        except Exception as e:
            logger.error(f"Failed to generate maintenance report: {e}")
            return {"error": str(e)}
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of a directory in bytes."""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Failed to calculate directory size for {directory}: {e}")
        return total_size
    
    def _get_temp_files_info(self) -> Tuple[int, int]:
        """Get count and total size of temporary files."""
        count = 0
        total_size = 0
        try:
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    count += 1
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Failed to get temp files info: {e}")
        return count, total_size


# Global maintenance manager instance
_maintenance_manager: Optional[MaintenanceManager] = None


def get_maintenance_manager() -> MaintenanceManager:
    """Get the global maintenance manager instance."""
    global _maintenance_manager
    if _maintenance_manager is None:
        _maintenance_manager = MaintenanceManager()
    return _maintenance_manager


def initialize_maintenance_manager(session_manager: Optional[SessionManager] = None,
                                 temp_dir: Optional[str] = None,
                                 **kwargs) -> MaintenanceManager:
    """Initialize the global maintenance manager."""
    global _maintenance_manager
    _maintenance_manager = MaintenanceManager(session_manager, temp_dir, **kwargs)
    return _maintenance_manager


# Convenience functions

def run_maintenance() -> Dict[str, Any]:
    """Run maintenance operations."""
    return get_maintenance_manager().run_maintenance()


def get_system_health() -> SystemHealth:
    """Get system health information."""
    return get_maintenance_manager().get_system_health()


def cleanup_session(session_id: str) -> bool:
    """Force cleanup of a session."""
    return get_maintenance_manager().force_cleanup_session(session_id)


def start_auto_maintenance(interval: int = 3600):
    """Start automatic maintenance."""
    get_maintenance_manager().start_maintenance(interval)


def stop_auto_maintenance():
    """Stop automatic maintenance."""
    get_maintenance_manager().stop_maintenance()