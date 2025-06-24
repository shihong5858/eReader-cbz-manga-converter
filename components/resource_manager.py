#!/usr/bin/env python3
"""
Resource Manager for handling bundle resources and paths.
Provides standardized access to bundled resources across different environments.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional


class ResourceManager:
    """Manages resource paths for both development and packaged environments."""
    
    def __init__(self):
        # Setup logger
        self.logger = logging.getLogger(__name__)
        
        self._base_path: Optional[Path] = None
        self._kcc_path: Optional[Path] = None
        self._resources_path: Optional[Path] = None
        self._initialize_paths()
    
    def _initialize_paths(self):
        """Initialize all resource paths based on current environment."""
        # Import here to avoid circular imports
        from .logger_config import is_debug_enabled
        
        # Only log detailed info in debug mode
        if is_debug_enabled():
            self.logger.debug("="*60)
            self.logger.debug("ResourceManager: Initializing paths...")
            self.logger.debug(f"sys.frozen: {getattr(sys, 'frozen', False)}")
            self.logger.debug(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not set')}")
            self.logger.debug(f"sys.executable: {sys.executable}")
        
        if getattr(sys, 'frozen', False):
            # Packaged environment (PyInstaller)
            if is_debug_enabled():
                self.logger.debug("Detected packaged environment (PyInstaller)")
            
            # Check if this is a macOS App Bundle by looking at the executable path
            executable_path = Path(sys.executable)
            is_macos_app_bundle = (
                '.app' in str(executable_path) and 
                'Contents/MacOS' in str(executable_path)
            )
            
            if is_debug_enabled():
                self.logger.debug(f"Executable path: {executable_path}")
                self.logger.debug(f"Has _MEIPASS: {hasattr(sys, '_MEIPASS')}")
                self.logger.debug(f"Is macOS App Bundle: {is_macos_app_bundle}")
            
            if is_macos_app_bundle:
                # macOS App Bundle - use proper directory structure
                executable_dir = executable_path.parent  # MacOS
                app_contents = executable_dir.parent     # Contents
                
                # For macOS App Bundle, put everything in Resources
                self._resources_path = app_contents / 'Resources'
                self._base_path = self._resources_path  # Use Resources for binaries too
                self._kcc_path = self._resources_path / 'kindlecomicconverter'
                
                if is_debug_enabled():
                    self.logger.debug("Using macOS App Bundle configuration")
                    self.logger.debug(f"Executable directory: {executable_dir}")
                    self.logger.debug(f"App Contents: {app_contents}")
                    self.logger.debug(f"macOS bundle base_path (Resources): {self._base_path}")
                    self.logger.debug(f"macOS bundle resources_path (Resources): {self._resources_path}")
                    self.logger.debug(f"macOS bundle kcc_path: {self._kcc_path}")
            elif hasattr(sys, '_MEIPASS'):
                # PyInstaller single-file bundle
                self._base_path = Path(sys._MEIPASS)
                self._resources_path = self._base_path
                self._kcc_path = self._base_path / 'kindlecomicconverter'
                
                if is_debug_enabled():
                    self.logger.debug("Using PyInstaller single-file bundle configuration")
                    self.logger.debug(f"Single-file base_path: {self._base_path}")
                    self.logger.debug(f"Single-file resources_path: {self._resources_path}")
                    self.logger.debug(f"Single-file kcc_path: {self._kcc_path}")
            else:
                # Other directory bundle
                executable_dir = Path(sys.executable).parent
                
                # Try to detect if we're in a special directory structure
                if (executable_dir.parent / 'Resources').exists():
                    # Looks like an app bundle without proper detection
                    self._resources_path = executable_dir.parent / 'Resources'
                    self._base_path = self._resources_path
                    self._kcc_path = self._resources_path / 'kindlecomicconverter'
                else:
                    # Standard directory bundle
                    self._base_path = executable_dir
                    self._resources_path = executable_dir
                    self._kcc_path = executable_dir / 'kindlecomicconverter'
                
                if is_debug_enabled():
                    self.logger.debug("Using other directory bundle configuration")
                    self.logger.debug(f"base_path: {self._base_path}")
                    self.logger.debug(f"resources_path: {self._resources_path}")
                    self.logger.debug(f"kcc_path: {self._kcc_path}")
        else:
            # Development environment
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent  # Go up from components/
            
            self._base_path = project_root
            self._kcc_path = project_root / 'kcc'
            self._resources_path = project_root / 'config'
            
            if is_debug_enabled():
                self.logger.debug("Detected development environment")
                self.logger.debug(f"Development base_path: {self._base_path}")
                self.logger.debug(f"Development kcc_path: {self._kcc_path}")
                self.logger.debug(f"Development resources_path: {self._resources_path}")
        
        # Only verify essential paths, skip detailed logging in normal mode
        if not self._kcc_path.exists():
            self.logger.error(f"KCC directory not found: {self._kcc_path}")
        elif is_debug_enabled():
            # Only show detailed verification in debug mode
            self.logger.debug("Path verification:")
            self.logger.debug(f"base_path exists: {self._base_path.exists()} -> {self._base_path}")
            self.logger.debug(f"kcc_path exists: {self._kcc_path.exists()} -> {self._kcc_path}")
            self.logger.debug(f"resources_path exists: {self._resources_path.exists()} -> {self._resources_path}")
            
            # Check for essential KCC files in debug mode only
            essential_files = ['kindlecomicconverter', '__init__.py', 'comic2ebook.py']
            for essential in essential_files:
                essential_path = self._kcc_path / essential
                self.logger.debug(f"Essential {essential}: {'EXISTS' if essential_path.exists() else 'MISSING'}")
                
        if is_debug_enabled():
            self.logger.debug("="*60)
    
    @property
    def base_path(self) -> Path:
        """Get the base resource path."""
        return self._base_path
    
    @property
    def kcc_path(self) -> Path:
        """Get the KCC (KindleComicConverter) path."""
        return self._kcc_path
    
    @property
    def resources_path(self) -> Path:
        """Get the resources directory path."""
        return self._resources_path
    
    def get_binary_path(self, binary_name: str) -> Optional[Path]:
        """Get path to a bundled binary."""
        from .logger_config import is_debug_enabled
        import platform
        
        # Add .exe extension for Windows if not already present
        if platform.system() == "Windows" and not binary_name.endswith('.exe'):
            binary_name_exe = binary_name + '.exe'
        else:
            binary_name_exe = binary_name
        
        # Check multiple possible locations for both with and without .exe
        candidate_paths = []
        for base_path in [self._base_path, self._resources_path]:
            candidate_paths.append(base_path / binary_name_exe)
            if platform.system() == "Windows" and binary_name != binary_name_exe:
                candidate_paths.append(base_path / binary_name)  # Also try without .exe
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in candidate_paths:
            if str(path) not in seen:
                seen.add(str(path))
                unique_paths.append(path)
        
        for binary_path in unique_paths:
            if binary_path.exists():
                # Additional validation for binary files
                try:
                    stat_info = binary_path.stat()
                    if is_debug_enabled():
                        self.logger.debug(f"Found {binary_name} at {binary_path}: {stat_info.st_size} bytes")
                    
                    # Check if it's a reasonable size for a binary (more than 1KB)
                    if stat_info.st_size < 1024:
                        if is_debug_enabled():
                            self.logger.debug(f"Binary {binary_name} too small ({stat_info.st_size} bytes), might be corrupted")
                        continue
                    
                    return binary_path
                except Exception as e:
                    if is_debug_enabled():
                        self.logger.debug(f"Error checking {binary_path}: {e}")
                    continue
        
        return None
    
    def get_config_file(self, filename: str) -> Optional[Path]:
        """Get path to a configuration file."""
        # Try in resources directory first
        config_path = self._resources_path / filename
        if config_path.exists():
            return config_path
        
        # Fallback to base path for bundled files
        fallback_path = self._base_path / filename
        return fallback_path if fallback_path.exists() else None
    
    def add_kcc_to_path(self) -> bool:
        """Add KCC path to sys.path if it exists."""
        from .logger_config import is_debug_enabled
        
        if self._kcc_path.exists():
            kcc_str = str(self._kcc_path)
            
            if kcc_str not in sys.path:
                sys.path.insert(0, kcc_str)
                if is_debug_enabled():
                    self.logger.debug(f"Added KCC to sys.path: {kcc_str}")
            
            # Test import after adding to path
            try:
                import kindlecomicconverter
                if is_debug_enabled():
                    self.logger.debug(f"KCC import successful! Version: {getattr(kindlecomicconverter, '__version__', 'unknown')}")
                
                # Test specific module
                from kindlecomicconverter import comic2ebook
                if is_debug_enabled():
                    self.logger.debug("comic2ebook module import successful!")
                
            except ImportError as e:
                self.logger.error(f"KCC import failed: {e}")
                if is_debug_enabled():
                    self.logger.debug(f"Current sys.path: {sys.path[:5]}...")
                    init_file = self._kcc_path / 'kindlecomicconverter' / '__init__.py'
                    self.logger.debug(f"kindlecomicconverter/__init__.py exists: {init_file.exists()}")
                
            except Exception as e:
                self.logger.error(f"Unexpected error testing KCC import: {e}")
            
            return True
        else:
            self.logger.error(f"KCC path does not exist: {self._kcc_path}")
        return False
    
    def setup_binary_environment(self) -> Optional[str]:
        """Setup environment for binary tools (like 7z)."""
        from .logger_config import is_debug_enabled
        
        original_path = os.environ.get('PATH', '')
        
        if is_debug_enabled():
            self.logger.debug("🔧 Setting up binary environment...")
            self.logger.debug(f"  frozen: {getattr(sys, 'frozen', False)}")
            self.logger.debug(f"  has _MEIPASS: {hasattr(sys, '_MEIPASS')}")
            self.logger.debug(f"  base_path: {self._base_path}")
            self.logger.debug(f"  resources_path: {self._resources_path}")
        
        if getattr(sys, 'frozen', False):
            paths_to_add = []
            
            # Add base path to PATH for binary access
            paths_to_add.append(str(self._base_path))
            if is_debug_enabled():
                self.logger.debug(f"  Added base_path: {self._base_path}")
            
            # For different directory structures, add appropriate paths
            if str(self._base_path) != str(self._resources_path):
                paths_to_add.append(str(self._resources_path))
                if is_debug_enabled():
                    self.logger.debug(f"  Added additional resources directory: {self._resources_path}")
            else:
                if is_debug_enabled():
                    self.logger.debug("  Base path and resources path are the same, no need to add twice")
            
            # Create new PATH with all directories
            new_path = ':'.join(paths_to_add) + ':' + original_path
            os.environ['PATH'] = new_path
            
            if is_debug_enabled():
                self.logger.debug(f"🔧 Updated PATH with binary directories: {paths_to_add}")
                self.logger.debug(f"  Original PATH length: {len(original_path)} chars")
                self.logger.debug(f"  New PATH length: {len(new_path)} chars")
                
            return original_path
        else:
            if is_debug_enabled():
                self.logger.debug("  Not in frozen environment, no PATH changes needed")
        
        return None
    
    def restore_environment(self, original_path: Optional[str]):
        """Restore original environment."""
        if original_path is not None:
            os.environ['PATH'] = original_path
    
    def get_working_directory(self) -> Path:
        """Get appropriate working directory for KCC operations."""
        # Always return the KCC path itself as the working directory
        return self._kcc_path
    
    def debug_info(self) -> dict:
        """Get debug information about current paths."""
        return {
            'frozen': getattr(sys, 'frozen', False),
            'has_meipass': hasattr(sys, '_MEIPASS'),
            'meipass': getattr(sys, '_MEIPASS', None),
            'executable': sys.executable,
            'base_path': str(self._base_path),
            'kcc_path': str(self._kcc_path),
            'resources_path': str(self._resources_path),
            'base_exists': self._base_path.exists(),
            'kcc_exists': self._kcc_path.exists(),
            'resources_exists': self._resources_path.exists(),
        }


# Global instance
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get the global ResourceManager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


# Convenience functions
def get_kcc_path() -> Path:
    """Get KCC path using ResourceManager."""
    return get_resource_manager().kcc_path


def get_config_file(filename: str) -> Optional[Path]:
    """Get configuration file path using ResourceManager."""
    return get_resource_manager().get_config_file(filename)


def get_binary_path(binary_name: str) -> Optional[Path]:
    """Get binary path using ResourceManager."""
    return get_resource_manager().get_binary_path(binary_name)


def add_kcc_to_path() -> bool:
    """Add KCC to sys.path using ResourceManager."""
    return get_resource_manager().add_kcc_to_path() 