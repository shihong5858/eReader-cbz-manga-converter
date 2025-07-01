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
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_desktop_path() -> str:
    """
    Get the user's desktop directory path in a cross-platform way.
    
    Returns:
        String path to the user's desktop directory
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows: Try multiple methods in order of preference
        desktop_candidates = []
        
        # Method 1: Use Windows Shell API (most reliable)
        try:
            import winreg
            import ctypes
            from ctypes import wintypes
            
            # Try using SHGetFolderPath (Shell API)
            dll = ctypes.windll.shell32
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH + 1)
            if dll.SHGetFolderPathW(None, 0x0000, None, 0, buf) == 0:
                desktop_candidates.append(buf.value)
        except (ImportError, OSError, AttributeError):
            pass
        
        # Method 2: Try environment variables
        userprofile = os.environ.get('USERPROFILE', '')
        if userprofile:
            desktop_candidates.extend([
                os.path.join(userprofile, 'Desktop'),
                os.path.join(userprofile, 'OneDrive', 'Desktop'),  # OneDrive Desktop
                os.path.join(userprofile, '桌面'),  # Chinese Windows
                os.path.join(userprofile, 'Bureau'),  # French Windows
                os.path.join(userprofile, 'Escritorio'),  # Spanish Windows
                os.path.join(userprofile, 'Desktop'),  # Default fallback
            ])
        
        # Method 3: Try HOMEPATH + HOMEDRIVE
        homepath = os.environ.get('HOMEPATH', '')
        homedrive = os.environ.get('HOMEDRIVE', '')
        if homepath and homedrive:
            home_base = homedrive + homepath
            desktop_candidates.extend([
                os.path.join(home_base, 'Desktop'),
                os.path.join(home_base, 'OneDrive', 'Desktop'),
                os.path.join(home_base, '桌面'),
                home_base  # Fallback to home directory
            ])
        
        # Method 4: Standard expanduser fallback
        desktop_candidates.extend([
            os.path.expanduser('~/Desktop'),
            os.path.expanduser('~/OneDrive/Desktop'),
            os.path.expanduser('~')
        ])
        
        # Method 5: Try registry for known folders (Windows Vista+)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                desktop_path, _ = winreg.QueryValueEx(key, "Desktop")
                if desktop_path:
                    desktop_candidates.insert(0, desktop_path)
        except (ImportError, OSError, FileNotFoundError):
            pass
        
        # Try each candidate until we find one that exists and is writable
        for desktop_path in desktop_candidates:
            if desktop_path and os.path.exists(desktop_path):
                try:
                    # Test if we can write to this directory
                    test_file = os.path.join(desktop_path, '.write_test_ereader')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    return desktop_path
                except (PermissionError, OSError):
                    continue  # Try next candidate
        
        # Ultimate fallback for Windows
        return os.path.expanduser('~')
        
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Desktop")
        
    else:  # Linux and other Unix-like systems
        # Try XDG user dirs first, then fallback
        xdg_desktop = os.environ.get('XDG_DESKTOP_DIR')
        if xdg_desktop and os.path.exists(xdg_desktop):
            return xdg_desktop
        
        # Standard desktop path for most Linux distributions
        desktop_path = os.path.expanduser("~/Desktop")
        if os.path.exists(desktop_path):
            return desktop_path
        
        # Some distributions use different names
        for desktop_name in ['桌面', 'Bureau', 'Escritorio', 'デスクトップ']:
            alt_desktop = os.path.expanduser(f"~/{desktop_name}")
            if os.path.exists(alt_desktop):
                return alt_desktop
        
        # Fallback to home directory
        return os.path.expanduser('~')


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
        self._error_logged = False  # Track if any errors have been logged

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
        
        # Always set up file logging for error tracking, but only show in debug mode
        if log_dir is None:
            try:
                log_dir = get_desktop_path()
            except Exception:
                # Ultimate fallback
                log_dir = os.path.expanduser('~')
        
        log_dir_path = Path(log_dir)
        
        # Ensure directory exists and is writable
        try:
            log_dir_path.mkdir(exist_ok=True)
            # Test write access
            test_file = log_dir_path / '.write_test'
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            # Fallback to home directory if desktop is not writable
            log_dir_path = Path(os.path.expanduser('~'))
            try:
                log_dir_path.mkdir(exist_ok=True)
            except (PermissionError, OSError):
                # Last resort: use temp directory
                import tempfile
                log_dir_path = Path(tempfile.gettempdir())
        
        # Create timestamped log file with user-friendly name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"eReader_CBZ_Logs_{timestamp}.log"
        self._log_file_path = log_dir_path / log_filename
        
        # Setup file handler with error handling - ALWAYS create this for error tracking
        try:
            self._file_handler = logging.FileHandler(
                self._log_file_path, 
                encoding='utf-8'
            )
            self._file_handler.setLevel(logging.INFO)  # Always log INFO and above to file
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self._file_handler.setFormatter(file_formatter)
            root_logger.addHandler(self._file_handler)
            
            # Setup console handler only if debug mode is enabled
            if self._debug_mode:
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
                logger.info(f"Platform: {platform.system()} {platform.release()}")
                logger.info("Use Ctrl+Shift+D to toggle debug mode")
                logger.info("="*60)
            else:
                # In normal mode, log basic info for tracking purposes
                logger = logging.getLogger(__name__)
                logger.info("="*60)
                logger.info("eReader CBZ Manga Converter - Session Started")
                logger.info(f"Platform: {platform.system()} {platform.release()}")
                logger.info("Log file will be retained if errors occur")
                logger.info("="*60)
                
        except Exception as e:
            # If we can't create the log file, fall back to console only in debug mode
            self._log_file_path = None
            self._file_handler = None
            
            if self._debug_mode:
                self._console_handler = logging.StreamHandler(sys.stdout)
                self._console_handler.setLevel(logging.INFO)
                console_formatter = logging.Formatter(
                    '[%(levelname)s] %(name)s: %(message)s'
                )
                self._console_handler.setFormatter(console_formatter)
                root_logger.addHandler(self._console_handler)
                
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create log file: {e}")
                logger.info("Debug mode enabled with console logging only")
        
        self._logger_configured = True
        return self._log_file_path if self._debug_mode else None

    def enable_debug_mode(self):
        """Enable debug mode (console output and file logging) at runtime."""
        if not self._logger_configured:
            raise RuntimeError("Logger not configured. Call setup_logging() first.")
        
        if not self._debug_mode:
            self._debug_mode = True
            
            # Create log file when debug mode is enabled using improved path detection
            try:
                desktop_path = get_desktop_path()
            except Exception:
                desktop_path = os.path.expanduser('~')
            
            log_dir_path = Path(desktop_path)
            
            # Ensure directory exists and is writable
            try:
                log_dir_path.mkdir(exist_ok=True)
                # Test write access
                test_file = log_dir_path / '.write_test'
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError):
                # Fallback to home directory if desktop is not writable
                log_dir_path = Path(os.path.expanduser('~'))
                try:
                    log_dir_path.mkdir(exist_ok=True)
                except (PermissionError, OSError):
                    # Last resort: use temp directory
                    import tempfile
                    log_dir_path = Path(tempfile.gettempdir())
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"eReader_CBZ_Logs_{timestamp}.log"
            self._log_file_path = log_dir_path / log_filename
            
            root_logger = logging.getLogger()
            
            # Add file handler with error handling
            try:
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
                
                file_created = True
                log_location = str(self._log_file_path)
            except Exception as e:
                file_created = False
                log_location = f"Console only (file creation failed: {e})"
                self._log_file_path = None
                self._file_handler = None
            
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
            logger.info(f"Log location: {log_location}")
            logger.info(f"Platform: {platform.system()} {platform.release()}")
            if file_created:
                logger.info(f"Desktop path detected: {desktop_path}")
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

    def log_error_occurred(self):
        """Mark that an error has been logged - ensures log file is kept"""
        self._error_logged = True

    def should_keep_log_file(self) -> bool:
        """Determine if log file should be kept based on debug mode or error occurrence"""
        return self._debug_mode or self._error_logged

    def cleanup_log_file_if_needed(self):
        """Clean up log file if not needed (no debug mode and no errors)"""
        if (self._log_file_path and 
            self._log_file_path.exists() and 
            not self.should_keep_log_file()):
            try:
                # Only remove if file is small (no significant content)
                if self._log_file_path.stat().st_size < 5000:  # Less than 5KB
                    self._log_file_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors




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
    """Get a logger instance with enhanced error tracking"""
    if not _dynamic_logger._logger_configured:
        _dynamic_logger.setup_logging()
    
    logger = logging.getLogger(name)
    
    # Enhance logger with error tracking
    original_error = logger.error
    original_critical = logger.critical
    
    def error_with_tracking(*args, **kwargs):
        _dynamic_logger.log_error_occurred()
        return original_error(*args, **kwargs)
    
    def critical_with_tracking(*args, **kwargs):
        _dynamic_logger.log_error_occurred()
        return original_critical(*args, **kwargs)
    
    logger.error = error_with_tracking
    logger.critical = critical_with_tracking
    
    return logger 