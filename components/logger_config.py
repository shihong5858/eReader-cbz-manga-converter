"""
Dynamic Logging Configuration Module

This module provides a centralized logging system that can:
1. Dynamically enable/disable debug mode
2. Always log to file for user support
3. Control console output to not disturb users
4. Provide easy access to log files when needed
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class DynamicLogger:
    """
    Dynamic logging system that provides:
    - File logging always enabled (for user support)
    - Console logging controlled by debug mode
    - Runtime debug mode switching
    - Easy log file access for troubleshooting
    """

    def __init__(self):
        self._debug_mode = False
        self._logger_configured = False
        self._log_file_path: Optional[Path] = None
        self._file_handler: Optional[logging.FileHandler] = None
        self._console_handler: Optional[logging.StreamHandler] = None

    def setup_logging(self, debug_mode: bool = False, log_dir: Optional[str] = None) -> Optional[Path]:
        """
        Setup the logging system.
        
        Args:
            debug_mode: Whether to enable debug mode (console output)
            log_dir: Directory to store log files (defaults to user's Desktop)
            
        Returns:
            Path to the log file if debug mode is enabled, None otherwise
        """
        self._debug_mode = debug_mode
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Only create file handler if debug mode is enabled
        if self._debug_mode:
            # Determine log directory
            if log_dir is None:
                # Default to Desktop for easy user access
                log_dir = os.path.expanduser("~/Desktop")
            
            log_dir_path = Path(log_dir)
            log_dir_path.mkdir(exist_ok=True)
            
            # Create timestamped log file with user-friendly name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"eReader_CBZ_Logs_{timestamp}.log"
            self._log_file_path = log_dir_path / log_filename
            
            # Setup file handler
            self._file_handler = logging.FileHandler(
                self._log_file_path, 
                encoding='utf-8'
            )
            self._file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self._file_handler.setFormatter(file_formatter)
            root_logger.addHandler(self._file_handler)
            
            # Setup console handler
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '[%(levelname)s] %(name)s: %(message)s'
            )
            self._console_handler.setFormatter(console_formatter)
            root_logger.addHandler(self._console_handler)
            
            # Log initial setup information
            logger = logging.getLogger(__name__)
            logger.info("="*60)
            logger.info("eReader CBZ Manga Converter - Debug Session Started")
            logger.info(f"Log file saved to: {self._log_file_path}")
            logger.info("Use Ctrl+Shift+D to toggle debug mode")
            logger.info("="*60)
        else:
            # No file logging in normal mode, only basic console for errors
            self._log_file_path = None
            self._file_handler = None
            self._console_handler = None
        
        self._logger_configured = True
        return self._log_file_path

    def enable_debug_mode(self):
        """Enable debug mode (console output and file logging) at runtime."""
        if not self._logger_configured:
            raise RuntimeError("Logger not configured. Call setup_logging() first.")
        
        if not self._debug_mode:
            self._debug_mode = True
            
            # Create log file when debug mode is enabled
            desktop_path = os.path.expanduser("~/Desktop")
            log_dir_path = Path(desktop_path)
            log_dir_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"eReader_CBZ_Logs_{timestamp}.log"
            self._log_file_path = log_dir_path / log_filename
            
            root_logger = logging.getLogger()
            
            # Add file handler
            self._file_handler = logging.FileHandler(
                self._log_file_path, 
                encoding='utf-8'
            )
            self._file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self._file_handler.setFormatter(file_formatter)
            root_logger.addHandler(self._file_handler)
            
            # Add console handler
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '[%(levelname)s] %(name)s: %(message)s'
            )
            self._console_handler.setFormatter(console_formatter)
            root_logger.addHandler(self._console_handler)
            
            logger = logging.getLogger(__name__)
            logger.info("="*60)
            logger.info("eReader CBZ Manga Converter - Debug Mode Enabled")
            logger.info(f"Log file created: {self._log_file_path}")
            logger.info("="*60)

    def disable_debug_mode(self):
        """Disable debug mode (console output and file logging) at runtime."""
        if not self._logger_configured:
            raise RuntimeError("Logger not configured. Call setup_logging() first.")
        
        if self._debug_mode:
            self._debug_mode = False
            
            root_logger = logging.getLogger()
            
            # Remove console handler
            if self._console_handler:
                root_logger.removeHandler(self._console_handler)
                self._console_handler = None
            
            # Remove file handler
            if self._file_handler:
                # Log final message before closing
                logger = logging.getLogger(__name__)
                logger.info("Debug mode DISABLED - Closing log file")
                logger.info("="*60)
                
                root_logger.removeHandler(self._file_handler)
                self._file_handler.close()
                self._file_handler = None
                self._log_file_path = None

    def is_debug_enabled(self) -> bool:
        """Check if debug mode is currently enabled."""
        return self._debug_mode

    def get_log_file_path(self) -> Optional[Path]:
        """Get the current log file path."""
        return self._log_file_path

    def log_system_info(self):
        """Log system information for debugging."""
        logger = logging.getLogger(__name__)
        
        # Import here to avoid circular imports
        from .resource_manager import get_resource_manager
        
        resource_manager = get_resource_manager()
        debug_info = resource_manager.debug_info()
        
        logger.info("System Information:")
        logger.info(f"  Platform: {sys.platform}")
        logger.info(f"  Python: {sys.version}")
        logger.info(f"  Executable: {sys.executable}")
        
        logger.info("Application Information:")
        for key, value in debug_info.items():
            logger.info(f"  {key}: {value}")




# Global logger instance
_dynamic_logger = DynamicLogger()

def setup_logging(debug_mode: bool = False, log_dir: Optional[str] = None) -> Optional[Path]:
    """Setup the global logging system."""
    return _dynamic_logger.setup_logging(debug_mode, log_dir)

def enable_debug():
    """Enable debug mode globally."""
    _dynamic_logger.enable_debug_mode()

def disable_debug():
    """Disable debug mode globally."""
    _dynamic_logger.disable_debug_mode()

def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return _dynamic_logger.is_debug_enabled()

def get_log_file() -> Optional[Path]:
    """Get the current log file path."""
    return _dynamic_logger.get_log_file_path()



def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name) 