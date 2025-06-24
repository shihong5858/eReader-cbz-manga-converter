"""eReader CBZ Manga Converter - Convert EPUB files to CBZ format."""

import re
from pathlib import Path

def _get_version():
    """Get version from pyproject.toml"""
    toml_file = Path(__file__).parent / "pyproject.toml"
    if toml_file.exists():
        content = toml_file.read_text()
        # Look for version = "x.y.z" in [project] section
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)
    return "unknown"

__version__ = _get_version()
__license__ = 'MIT'
__copyright__ = '2024, eReader CBZ Manga Converter Contributors'
__docformat__ = 'restructuredtext en'
