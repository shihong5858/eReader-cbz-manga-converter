#!/usr/bin/env python3
"""
eReader CBZ Manga Converter - Build & Development Script

Unified script for all development tasks:
    python build.py run          # Run application from source
    python build.py build        # Build application for current platform
    python build.py build-mac    # Build for macOS
    python build.py build-win    # Build for Windows
    python build.py build-linux  # Build for Linux
    python build.py clean        # Clean build artifacts
    python build.py dev          # Install in development mode
    python build.py check        # Check code quality
    python build.py kcc          # Setup KCC environment
"""

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Get version from pyproject.toml
def get_version():
    """Get version from pyproject.toml"""
    toml_file = Path("pyproject.toml")
    if toml_file.exists():
        content = toml_file.read_text(encoding='utf-8')
        # Look for version = "x.y.z" in [project] section
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)
    return "unknown"

VERSION = get_version()

# Build configuration - simplified to just build/ and dist/
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
SPEC_DIR = Path("build/specs")

# Ensure build directories exist
BUILD_DIR.mkdir(exist_ok=True)
DIST_DIR.mkdir(exist_ok=True)
SPEC_DIR.mkdir(exist_ok=True, parents=True)


def print_step(message: str):
    """Print a build step with formatting."""
    print(f"\n[BUILD] {message}")


def print_success(message: str):
    """Print a success message."""
    print(f"[SUCCESS] {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"[ERROR] {message}")


def run_command(cmd, cwd=None):
    """Run command and handle errors"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return None


def run_app():
    """Run the application from source."""
    print_step("Starting eReader CBZ Manga Converter...")
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
        print_success("Application completed")
    except subprocess.CalledProcessError as e:
        print_error(f"Application failed: {e}")
        sys.exit(1)


def clean_build():
    """Clean build artifacts and temporary files."""
    print_step("Cleaning build artifacts...")

    # Standard directories to clean - removed TEMP_DIR
    dirs_to_clean = [
        BUILD_DIR,
        DIST_DIR,
        Path("eReader_CBZ_Manga_Converter.egg-info"),
        Path("__pycache__"),
    ]

    # Files to clean
    files_to_clean = [
        "*.spec",
        ".DS_Store",
        "*.pyc",
    ]

    # Clean directories
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Cleaned {dir_path}/")

    # Clean __pycache__ recursively
    for root, dirs, _ in os.walk("."):
        for dir_name in dirs[:]:  # Copy list to modify during iteration
            if dir_name == "__pycache__":
                full_path = Path(root) / dir_name
                shutil.rmtree(full_path)
                print(f"  Cleaned {full_path}")
                dirs.remove(dir_name)  # Don't recurse into deleted directory

    # Clean specific files
    for pattern in files_to_clean:
        for file_path in Path(".").glob(pattern):
            if file_path.is_file():
                file_path.unlink()
                print(f"  Cleaned {file_path}")

    print_success("Build cleanup completed")


def install_dev():
    """Install package in development mode."""
    print_step("Installing in development mode...")
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]
        subprocess.run(cmd, check=True)
        print_success("Development installation completed")
    except subprocess.CalledProcessError as e:
        print_error(f"Development installation failed: {e}")
        sys.exit(1)


def check_quality():
    """Check code quality with ruff and mypy if available."""
    print_step("Checking code quality...")

    success = True

    # Only check our own code, exclude third-party KCC library
    our_code = ["main.py", "build.py", "components/", "gui/"]

    # Run ruff
    if shutil.which("ruff"):
        try:
            cmd = ["ruff", "check"] + our_code
            subprocess.run(cmd, check=True, capture_output=True)
            print_success("Ruff checks passed!")
        except subprocess.CalledProcessError:
            print_error("Ruff found issues")
            success = False
    else:
        print("  Ruff not available")

    # Run mypy
    if shutil.which("mypy"):
        try:
            # Check each file individually with explicit package bases to avoid naming issues
            mypy_files = ["main.py", "build.py"]
            mypy_dirs = ["components", "gui"]

            for file in mypy_files:
                subprocess.run(["mypy", file, "--ignore-missing-imports", "--explicit-package-bases"],
                             check=True, capture_output=True)

            for dir_name in mypy_dirs:
                subprocess.run(["mypy", dir_name, "--ignore-missing-imports", "--explicit-package-bases"],
                             check=True, capture_output=True)

            print_success("MyPy checks passed!")
        except subprocess.CalledProcessError:
            print_error("MyPy found issues")
            success = False
    else:
        print("  MyPy not available")

    return success


def get_hidden_imports() -> List[str]:
    """Get list of hidden imports for PyInstaller."""
    return [
        "_cffi_backend",
        "html.parser",
        "xml.etree.ElementTree",
        "xml.dom",
        "lxml",
        "ebooklib",
        "bs4",
        "PIL",
        "PIL.Image",
        "PIL.ImageFile",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageOps",
        "PIL.ImageChops",
        "PIL.ImageFilter",
        "PIL.ImageEnhance",
        "Pillow",
        "zipfile",
        "tempfile",
        "shutil",
        "queue",
        "kindlecomicconverter",
        "kindlecomicconverter.comic2ebook",
        "kindlecomicconverter.comic2panel",
        "kindlecomicconverter.shared",
        "kindlecomicconverter.startup",
        "uuid",
        "natsort",
        "slugify",
        "psutil",
        "multiprocessing",
        "pathlib",
        "glob",
        "stat",
        "argparse",
        "time",
        "copy",
        "re",
        "subprocess",
        "html",
        "mozjpeg_lossless_optimization",
        "requests",
        "packaging",
        "distro",
        "numpy",
        "cffi",
        "fastnumbers",
    ]


def get_data_files(target_platform: str) -> List[str]:
    """Get data files for PyInstaller."""
    separator = ";" if target_platform == "win32" else ":"

    data_files = [
        f"components{separator}components",
        f"gui{separator}gui",
        f"kcc/kindlecomicconverter{separator}kindlecomicconverter",
        f"config/device_info.json{separator}.",
    ]

    # Add 7z binary for KCC support
    z7_path = None
    
    def find_real_7z_binary(candidate_path):
        """Find the real 7z binary, following shell scripts if needed."""
        if not os.path.exists(candidate_path):
            return None
            
        # On Windows, prefer .exe files but accept non-.exe if they exist
        if target_platform == "win32" or os.name == 'nt':
            if not candidate_path.endswith('.exe'):
                exe_path = candidate_path + '.exe'
                if os.path.exists(exe_path):
                    candidate_path = exe_path
                    print(f"[INFO] Using .exe version: {exe_path}")
                elif not os.path.exists(candidate_path):
                    print(f"[WARNING] Windows 7z path not found: {candidate_path} or {exe_path}")
                    return None
                # If original path exists, continue with it (e.g., Git Bash environment)
        
        # Check if it's a shell script that points to the real binary (Unix systems)
        if not (target_platform == "win32" or os.name == 'nt'):
            try:
                with open(candidate_path, 'r') as f:
                    content = f.read()
                
                # Look for shell script pattern like p7zip uses
                if content.startswith('#!') and '/lib/p7zip/7z' in content:
                    # Extract the real binary path from the shell script
                    import re
                    match = re.search(r'"([^"]*lib/p7zip/7z)"', content)
                    if match:
                        real_binary = match.group(1)
                        if os.path.exists(real_binary):
                            print(f"[INFO] Found real 7z binary via shell script: {real_binary}")
                            return real_binary
            except:
                pass
        
        # Check file size - real 7z binary should be substantial
        try:
            size = os.path.getsize(candidate_path)
            if size < 1024:  # Less than 1KB is likely a script
                print(f"[WARNING] 7z at {candidate_path} is too small ({size} bytes), likely a script")
                return None
        except:
            pass
        
        return candidate_path
    
    # Try to find 7z using which command first
    try:
        result = subprocess.run(["which", "7z"], capture_output=True, text=True)
        if result.returncode == 0:
            candidate = result.stdout.strip()
            print(f"[INFO] Found 7z using which: {candidate}")
            z7_path = find_real_7z_binary(candidate)
            if z7_path:
                print(f"[INFO] Real 7z binary: {z7_path}")
            elif (target_platform == "win32" or os.name == 'nt') and os.path.exists(candidate):
                # On Windows, if validation failed but file exists, use it anyway (Git Bash scenario)
                print(f"[INFO] Using which result despite validation (Git Bash environment): {candidate}")
                z7_path = candidate
    except Exception as e:
        print(f"[WARNING] which command failed: {e}")
    
    # If which didn't work or found a script, try direct locations
    if not z7_path:
        if target_platform == "win32" or os.name == 'nt':
            # Windows locations
            z7_locations = [
                "C:/Program Files/7-Zip/7z.exe",
                "C:/Program Files (x86)/7-Zip/7z.exe",
                "C:/ProgramData/chocolatey/bin/7z.exe",
                "C:/ProgramData/chocolatey/lib/7zip*/tools/7z.exe",
                "C:/tools/7zip/7z.exe",
            ]
        else:
            # Unix/Linux/macOS locations
            z7_locations = [
                # Try the real binary locations first (macOS homebrew)
                "/opt/homebrew/Cellar/p7zip/*/lib/p7zip/7z",
                "/usr/local/Cellar/p7zip/*/lib/p7zip/7z", 
                # Linux package manager locations
                "/usr/bin/7z",
                "/usr/local/bin/7z",
                # Symlinked locations (macOS)
                "/opt/homebrew/bin/7z", 
                "/usr/local/bin/7z",
            ]
        
        import glob
        for location_pattern in z7_locations:
            # Handle glob patterns
            if '*' in location_pattern:
                matches = glob.glob(location_pattern)
                for match in sorted(matches, reverse=True):  # Use latest version
                    z7_path = find_real_7z_binary(match)
                    if z7_path:
                        print(f"[INFO] Found 7z via pattern {location_pattern}: {z7_path}")
                        break
            else:
                z7_path = find_real_7z_binary(location_pattern)
                if z7_path:
                    print(f"[INFO] Found 7z at {location_pattern}: {z7_path}")
                    break
            
            if z7_path:
                break
    
    if z7_path and os.path.exists(z7_path):
        data_files.append(f"{z7_path}{separator}.")
        print(f"[INFO] Adding 7z binary: {z7_path}")
        
        # Check for and add required libraries in the same directory
        z7_dir = os.path.dirname(z7_path)
        system_dirs = ["/usr/bin", "/bin", "/usr/local/bin"]
        
        # Don't package system directories or Windows Program Files
        if (z7_dir not in system_dirs and 
            not z7_dir.lower().startswith("c:/program files") and 
            not z7_dir.lower().startswith("c:\\program files")):
            
            print(f"[INFO] Checking 7z directory for dependencies: {z7_dir}")
            
            if target_platform == "win32" or os.name == 'nt':
                # Windows dependencies
                dep_files = ["7z.dll", "7za.exe", "7zr.exe"]
            else:
                # Unix dependencies  
                dep_files = ["7z.so", "7za", "7zr"]
            
            for dep_file in dep_files:
                dep_path = os.path.join(z7_dir, dep_file)
                if os.path.exists(dep_path):
                    data_files.append(f"{dep_path}{separator}.")
                    print(f"[INFO] Adding 7z dependency: {dep_path}")
                else:
                    print(f"[INFO] Optional dependency not found: {dep_path}")
        else:
            print(f"[INFO] Skipping dependency check for system directory: {z7_dir}")
    else:
        print("[WARNING] 7z binary not found, KCC may fail")
        print("[WARNING] Checked locations and 'which 7z' command")

    return data_files


def get_build_command(target_platform: Optional[str] = None) -> List[str]:
    """Get PyInstaller command for the target platform."""
    if target_platform is None:
        target_platform = sys.platform

    # Base command
    cmd = ["pyinstaller"]

    # Hidden imports
    for import_name in get_hidden_imports():
        cmd.extend(["--hidden-import", import_name])

    # Data files
    for data_file in get_data_files(target_platform):
        cmd.extend(["--add-data", data_file])

    # Common options
    cmd.extend([
        "-y",  # Overwrite output directory
        "-w",  # Windowed mode (no console)
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}/work",
    ])

    # Platform-specific options
    if target_platform == "darwin":  # macOS
        cmd.extend([
            "-D",  # Create directory bundle
            "-i", "assets/app.icns",
            "-n", "eReader CBZ Manga Converter",  # Internal name without version
        ])
    elif target_platform == "win32":  # Windows
        cmd.extend([
            "-F",  # Create one-file executable
            "-n", f"eReader_CBZ_Manga_Converter_{VERSION}",
            "--noupx",
        ])
    else:  # Linux
        cmd.extend([
            "-F",  # Create one-file executable
            "-n", f"eReader_CBZ_Manga_Converter_{VERSION}",
        ])

    # Source file
    cmd.append("main.py")

    return cmd


def build_package(target_platform: Optional[str] = None):
    """Build the package using PyInstaller."""
    if target_platform is None:
        target_platform = sys.platform

    print_step(f"Building eReader CBZ Manga Converter for {target_platform}...")

    # Set environment variables to fix numpy/OpenBLAS stack overflow issues
    env = os.environ.copy()
    if target_platform == "darwin":  # macOS specific fixes
        # Limit OpenBLAS threads to prevent stack overflow
        # But allow limited parallelism to avoid KCC multiprocessing deadlocks
        env['OPENBLAS_NUM_THREADS'] = '2'
        env['MKL_NUM_THREADS'] = '2'
        env['NUMEXPR_NUM_THREADS'] = '2'
        env['OMP_NUM_THREADS'] = '2'
        # Use single-threaded BLAS to avoid arm64 stack issues
        env['VECLIB_MAXIMUM_THREADS'] = '2'
        print("[INFO] Set limited thread limits to prevent OpenBLAS stack overflow on ARM64")

    # Create build directories
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    (BUILD_DIR / "work").mkdir(exist_ok=True)

    cmd = get_build_command(target_platform)

    print(f"  Running: {' '.join(cmd[:5])}... (with {len(cmd)-5} more args)")

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            env=env  # Pass modified environment
        )
        print_success("Build completed successfully!")

        # Handle macOS .app bundle
        if target_platform == "darwin":
            app_name = "eReader CBZ Manga Converter"
            expected_path = DIST_DIR / f"{app_name}.app"
            
            if expected_path.exists():
                print(f"  [INFO] Found .app bundle: {app_name}.app")
                
                # Update Info.plist with correct version
                info_plist_path = expected_path / "Contents/Info.plist"
                if info_plist_path.exists():
                    try:
                        import plistlib
                        
                        # Read current Info.plist
                        with open(info_plist_path, 'rb') as f:
                            plist_data = plistlib.load(f)
                        
                        # Update version information
                        plist_data['CFBundleShortVersionString'] = VERSION
                        plist_data['CFBundleVersion'] = VERSION
                        
                        # Write back
                        with open(info_plist_path, 'wb') as f:
                            plistlib.dump(plist_data, f)
                        
                        print(f"  [INFO] Updated Info.plist with version {VERSION}")
                        
                    except Exception as e:
                        print(f"  [WARNING] Failed to update Info.plist: {e}")
                
                # Remove extra directory if it exists
                extra_dir = DIST_DIR / app_name
                if extra_dir.exists() and extra_dir.is_dir():
                    import shutil
                    shutil.rmtree(extra_dir)
                    print(f"  [INFO] Removed extra directory: {app_name}")
                
                # Code signing
                try:
                    print("  [INFO] Signing app to prevent App Translocation...")
                    sign_result = subprocess.run(
                        ["codesign", "--force", "--deep", "--sign", "-", str(expected_path)],
                        capture_output=True, text=True
                    )
                    if sign_result.returncode == 0:
                        print("  [INFO] App signed successfully")
                    else:
                        print(f"  [WARNING] Code signing failed: {sign_result.stderr}")
                except Exception as e:
                    print(f"  [WARNING] Code signing failed: {e}")
            else:
                print(f"  [WARNING] Expected .app bundle not found: {app_name}")

        # Move spec file to our organized location
        spec_files = list(Path(".").glob("*.spec"))
        if spec_files and SPEC_DIR.exists():
            for spec_file in spec_files:
                new_location = SPEC_DIR / spec_file.name
                spec_file.rename(new_location)
                print(f"  [INFO] Moved {spec_file.name} to {SPEC_DIR}/")

        # Create DMG for macOS if appdmg is available
        if target_platform == "darwin" and shutil.which("appdmg"):
            create_macos_dmg()

        # Show build output location
        print(f"  [INFO] Output location: {DIST_DIR.absolute()}")

    except subprocess.CalledProcessError as e:
        print_error(f"Build failed: {e}")
        if e.stderr:
            print(f"Error details:\n{e.stderr}")
        sys.exit(1)


def create_macos_dmg():
    """Create DMG installer for macOS with architecture-specific naming."""
    print_step("Creating macOS DMG installer...")
    
    app_name = "eReader CBZ Manga Converter"
    app_path = DIST_DIR / f"{app_name}.app"
    
    if not app_path.exists():
        print_error(f"{app_path} not found")
        return

    # Detect macOS architecture for proper file naming
    import platform
    arch = platform.machine().lower()
    if arch in ['arm64', 'aarch64']:
        arch_suffix = "arm"
    elif arch in ['x86_64', 'amd64']:
        arch_suffix = "intel"
    else:
        arch_suffix = arch  # fallback to actual architecture name

    # Check if appdmg is available
    if shutil.which("appdmg"):
        print("[INFO] Attempting to create DMG with appdmg...")
        installer_config = Path("config/installer.json")
        
        if installer_config.exists():
            try:
                dmg_name = f"eReader_CBZ_Manga_Converter_macOS_{arch_suffix}_{VERSION}.dmg"
                dmg_path = DIST_DIR / dmg_name
                
                print(f"[INFO] Running appdmg from {Path.cwd()}")
                print(f"[INFO] Config: {installer_config.absolute()}")
                print(f"[INFO] Output: {dmg_path.absolute()}")
                print(f"[INFO] Architecture: {arch} -> {arch_suffix}")
                
                dmg_cmd = ["appdmg", str(installer_config.absolute()), str(dmg_path.absolute())]
                result = subprocess.run(dmg_cmd, check=True, capture_output=True, text=True, cwd=Path.cwd())
                
                print_success(f"Created DMG: {dmg_name}")
                dmg_size_mb = dmg_path.stat().st_size / (1024 * 1024)
                print(f"[INFO] DMG size: {dmg_size_mb:.1f} MB")
                
                # Show appdmg output for debugging
                if result.stdout:
                    print(f"[INFO] appdmg output: {result.stdout}")
                    
                return
                
            except subprocess.CalledProcessError as e:
                print_error(f"DMG creation failed: {e}")
                if e.stderr:
                    print(f"[ERROR] stderr: {e.stderr}")
                if e.stdout:
                    print(f"[INFO] stdout: {e.stdout}")
                print("[INFO] Falling back to ZIP creation...")
        else:
            print("[WARNING] config/installer.json not found, falling back to ZIP creation")
    else:
        print("[INFO] appdmg not available, creating ZIP instead...")
    
    # Fallback to ZIP creation with architecture-specific naming
    zip_name = f"eReader_CBZ_Manga_Converter_macOS_{arch_suffix}_{VERSION}.zip"
    zip_path = DIST_DIR / zip_name
    
    try:
        import zipfile
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk(app_path):
                for file in files:
                    file_path = Path(root) / file
                    arc_name = file_path.relative_to(DIST_DIR)
                    zipf.write(file_path, arc_name)
        
        print_success(f"Created ZIP: {zip_name}")
        print(f"[INFO] Architecture: {arch} -> {arch_suffix}")
        
        # Get file size
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"[INFO] ZIP size: {size_mb:.1f} MB")
        
    except Exception as e:
        print_error(f"ZIP creation failed: {e}")


def setup_kcc():
    """Setup KCC environment"""
    print_step("Setting up KCC (KindleComicConverter) environment")

    # Check if kcc submodule exists
    kcc_path = Path("kcc")
    if not kcc_path.exists():
        print_error("KCC submodule not found. Please run:")
        print("   git submodule update --init --recursive")
        return False

    # Check kcc directory content
    if not (kcc_path / "kindlecomicconverter").exists():
        print_error("KCC submodule content incomplete. Please update submodule:")
        print("   git submodule update --init --recursive")
        return False

    print("[INFO] KCC submodule correctly configured")

    # Install KCC dependencies
    kcc_requirements = kcc_path / "requirements.txt"
    if kcc_requirements.exists():
        print("[INFO] Installing KCC dependencies...")
        output = run_command([sys.executable, "-m", "pip", "install", "-r", str(kcc_requirements)])
        if output is not None:
            print("[INFO] KCC dependencies installed successfully")
        else:
            print("[WARNING] KCC dependencies installation failed, please check manually")

    # Configure Python path (at runtime)
    print("[INFO] Configuring Python path...")

    # Check if KCC module can be imported
    try:
        sys.path.insert(0, str(kcc_path.absolute()))
        import kindlecomicconverter
        print("[INFO] KCC module import successful")
        print(f"[INFO] Version: {getattr(kindlecomicconverter, '__version__', 'unknown')}")
    except ImportError as e:
        print_error(f"KCC module import failed: {e}")
        return False

    print_success("KCC setup completed")
    print("[INFO] Usage: sys.path.insert(0, 'kcc') then import KCC modules")
    print("[INFO] Example: from kindlecomicconverter.comic2ebook import main as kcc_main")

    return True


def check_system_requirements():
    """Check system requirements"""
    print("[INFO] Checking system requirements...")

    # Check Python version
    # Note: Project requires Python 3.8+ as specified in pyproject.toml
    print(f"[INFO] Python version: {sys.version}")

    # Check optional dependencies
    optional_tools = {
        "7z": "7-Zip compression tool (recommended for more format support)",
        "kindlegen": "KindleGen (for MOBI format generation)"
    }

    for tool, description in optional_tools.items():
        if subprocess.run(["which", tool], capture_output=True).returncode == 0:
            print(f"[INFO] {tool}: installed")
        else:
            print(f"[WARNING] {tool}: not installed - {description}")

    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("""
eReader CBZ Manga Converter - Build & Development Script

Usage:
    python build.py <command>

Commands:
    run          Run the application from source
    build        Build application for current platform
    build-mac    Build for macOS
    build-win    Build for Windows
    build-linux  Build for Linux
    clean        Clean build artifacts
    dev          Install in development mode
    check        Check code quality
    kcc          Setup KCC environment

Examples:
    python build.py run
    python build.py build
    python build.py clean
    python build.py kcc
        """)
        return

    command = sys.argv[1]

    if command == "run":
        run_app()
    elif command == "build":
        build_package()
    elif command == "build-mac":
        build_package("darwin")
    elif command == "build-win":
        build_package("win32")
    elif command == "build-linux":
        build_package("linux")
    elif command == "clean":
        clean_build()
    elif command == "dev":
        install_dev()
    elif command == "check":
        check_quality()
    elif command == "kcc":
        if not check_system_requirements():
            sys.exit(1)
        if setup_kcc():
            print_success("KCC environment setup completed!")
        else:
            print_error("KCC setup failed, please check error messages")
            sys.exit(1)
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Run 'python build.py' for help")

    if command not in ["run", "kcc"]:  # Don't show completion message for run and kcc commands
        print_success("Operation completed!")


if __name__ == "__main__":
    main()
