# eReader CBZ Manga Converter

[中文说明](README_zh.md) | **English**

Convert EPUB/MOBI manga files to CBZ format optimized for eReaders, especially Kobo devices.

## Core Features

- **Format conversion**: Convert EPUB/MOBI format manga to CBZ format, optimized for eReaders manga reading experience
- **Fix scrambled pages**: Fix page ordering issues when converting to CBZ (some EPUBs converted with Calibre to CBZ would end up with wrong page ordering)
- **KCC enhancement**: Use Kindle Comic Converter (KCC) for image enhancement and eReader resolution adaptation
- **Cross-platform**: Works on Windows, macOS, and Linux with both GUI and command-line modes

## Download & Installation

### For Regular Users
Download the latest binary release from [GitHub Releases](https://github.com/shihong5858/eReader-cbz-manga-converter/releases) - no installation required, just run the executable.

### For Developers
```bash
git clone https://github.com/shihong5858/eReader-cbz-manga-converter.git
cd eReader-cbz-manga-converter
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
python build.py dev
```

## How to Use

### GUI Mode (Recommended)
1. **Input**: Click "Browse" button or drag and drop EPUB/MOBI files into the input area (supports multiple files)
2. **Output**: The system automatically sets the input file's directory as output, but you can specify a different directory
3. **Device**: Select your eReader device from the dropdown (common devices like Kobo Clara HD, Kindle, etc.)
4. **Convert**: Click "Convert" button to start the conversion process, progress bar will show overall progress

### Command Line Mode
```bash
python main.py input.epub output_directory
```

### Build Executable
```bash
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

## KCC Integration

This project implements EPUB/MOBI to CBZ format conversion using Python, and integrates [KindleComicConverter (KCC)](https://github.com/ciromattia/kcc) for image optimization and eReader device adaptation. Therefore, KCC code integration is required during development.

### Setup
```bash
git submodule update --init --recursive
python build.py kcc
```

### Update KCC
```bash
cd kcc && git pull origin master && cd ..
git add kcc && git commit -m "Update KCC"
```

## Requirements
- Python 3.8+
- Dependencies automatically managed via pyproject.toml

## Bug Reports & Suggestions

If you encounter any bugs or have suggestions for improvement, please report them in [GitHub Issues](https://github.com/shihong5858/eReader-cbz-manga-converter/issues).

## License
MIT License 