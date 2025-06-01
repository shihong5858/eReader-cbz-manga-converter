#!/usr/bin/env python3
"""
Resource Manager for handling bundle resources and paths.
Provides standardized access to bundled resources across different environments.
"""

import os
import sys
from pathlib import Path
from typing import Optional


class ResourceManager:
    """Manages resource paths for both development and packaged environments."""
    
    def __init__(self):
        self._base_path: Optional[Path] = None
        self._kcc_path: Optional[Path] = None
        self._resources_path: Optional[Path] = None
        self._initialize_paths()
    
    def _initialize_paths(self):
        """Initialize all resource paths based on current environment."""
        if getattr(sys, 'frozen', False):
            # Packaged environment (PyInstaller)
            if hasattr(sys, '_MEIPASS'):
                # Single-file bundle
                self._base_path = Path(sys._MEIPASS)
                self._resources_path = self._base_path
                self._kcc_path = self._base_path / 'kindlecomicconverter'
            else:
                # Directory bundle (macOS .app)
                executable_dir = Path(sys.executable).parent
                # Base path is Frameworks directory for resources
                self._base_path = executable_dir.parent / 'Frameworks'
                # Resources path is Resources directory for config files
                self._resources_path = executable_dir.parent / 'Resources'
                # KCC path is in Frameworks directory
                self._kcc_path = self._base_path / 'kindlecomicconverter'
        else:
            # Development environment
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent  # Go up from components/
            
            self._base_path = project_root
            self._kcc_path = project_root / 'kcc'
            self._resources_path = project_root / 'config'
    
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
        binary_path = self._base_path / binary_name
        return binary_path if binary_path.exists() else None
    
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
        if self._kcc_path.exists():
            kcc_str = str(self._kcc_path)
            if kcc_str not in sys.path:
                sys.path.insert(0, kcc_str)
            return True  # Return True if path exists, regardless of whether it was already in sys.path
        return False
    
    def setup_binary_environment(self) -> Optional[str]:
        """Setup environment for binary tools (like 7z)."""
        original_path = os.environ.get('PATH', '')
        
        if getattr(sys, 'frozen', False):
            # Add base path to PATH for binary access
            binary_dir = str(self._base_path)
            new_path = f"{binary_dir}:{original_path}"
            os.environ['PATH'] = new_path
            return original_path
        
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