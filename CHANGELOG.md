# Changelog

## [1.2.4] - 2025-06-24

### Fixed
- GitHub Actions 7z detection using dynamic 'which' command lookup
- macOS Intel/ARM build file name collisions in releases
- Comprehensive 7z verification steps in all build environments
- Ensure both macOS Intel and ARM versions are available in releases
- Resolved 7z symlink packaging issues in PyInstaller builds
- Improved 7z binary detection and packaging in macOS and Linux builds
- Enhanced runtime 7z path resolution for packaged applications

## [1.2.3] - 2025-06-24

### Added
- Dynamic debug mode with hidden keyboard shortcut (Ctrl+Shift+D)
- Runtime logging system for distributed application troubleshooting

### Fixed
- Unified version management across all project files
- Build artifacts now use consistent version numbering
- KCC 7z command not found issue in GitHub compiled versions (macOS App Bundle PATH configuration)

## [1.2.2] - 2025-06-02

### Fixed
- ResourceManager path handling for macOS app bundle structure
- KCC import issues in App Translocation environment
- 50% crash issue during conversion process in macOS app
- Path consistency between Frameworks and Resources directories

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