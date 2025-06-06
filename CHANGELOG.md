# Changelog

## [1.2.1] - 2025-06-02

- Fixed 50% crash issue during conversion process in macOS app

## [1.2.0] - 2025-06-01

- Cleaned up dependencies and reduced repository size
- KCC integration migrated to Git Submodule
- Unified KCC setup in build.py
- Fixed GitHub Actions runner issues

## [1.1.0] - 2025-06-01

### Added
- Modern pyproject.toml configuration
- Unified build system with `build.py`
- Code quality tools (Ruff, MyPy)
- Organized directory structure
- Development workflow improvements

### Changed
- Migrated from setup.py to pyproject.toml
- Reorganized build artifacts
- Updated documentation

### Fixed
- PyInstaller multiprocessing issues
- Cross-platform compatibility
- Code quality improvements

## [1.0.0] - 2025-05-30

### Added
- Initial release
- EPUB to CBZ conversion
- Cross-platform support (Windows, macOS, Linux)
- PySide6 GUI interface
- KCC integration for image optimization
- Automated builds with GitHub Actions 