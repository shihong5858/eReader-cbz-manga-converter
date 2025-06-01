# eReader CBZ Manga Converter

[中文说明](README_zh.md) | **English**

Convert EPUB/MOBI manga files to CBZ format optimized for eReaders, especially Kobo devices.

## Core Features

- **Format conversion**: Convert EPUB/MOBI manga to CBZ format optimized for Kobo eReaders
- **Fix scrambled manga**: Specially designed to handle manga from moe-series websites with mixed-up page orders
- **KCC enhancement**: Use Kindle Comic Converter (KCC) for image optimization
- **Cross-platform**: Works on Windows, macOS, and Linux with both GUI and command-line modes

## Quick Start

### Installation
```bash
git clone https://github.com/shihong5858/eReader-cbz-manga-converter.git
cd eReader-cbz-manga-converter
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
python build.py dev
```

### Usage
```bash
# GUI mode
python build.py run

# Command line
python main.py input.epub output_directory

# Build executable
python build.py build
```

## Development

### Contributing
To help with development:

1. **Fork and clone** the repository
2. **Set up environment**: `python build.py dev`
3. **Run tests**: `python build.py check`
4. **Make changes** and test thoroughly
5. **Submit pull request** with clear description

### Project Structure
```
├── main.py              # Application entry point
├── build.py             # Build and development script
├── components/          # Core conversion logic
│   └── conversion/      # EPUB/MOBI converter
├── gui/                 # PySide6 GUI interface
├── kcc/                 # KCC library integration
└── config/              # Configuration files
```

### Development Commands
```bash
python build.py dev      # Install dev dependencies
python build.py run      # Run from source
python build.py check    # Code quality checks
python build.py clean    # Clean build artifacts
python build.py build    # Build executable
```

## Requirements
- Python 3.8+
- Dependencies automatically managed via pyproject.toml

## License
MIT License 