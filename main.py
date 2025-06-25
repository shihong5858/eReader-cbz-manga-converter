import logging
import multiprocessing
import os
import sys
import datetime

# Import PySide6 at top level for PyInstaller dependency detection
from PySide6.QtWidgets import QApplication

# Fix working directory for PyInstaller
def fix_working_directory():
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            app_dir = sys._MEIPASS
        else:
            app_dir = os.path.dirname(sys.executable)
        os.chdir(app_dir)

# Fix working directory immediately
fix_working_directory()

# Import the new dynamic logging system
from components.logger_config import setup_logging, get_logger

# Setup logging immediately (always save to desktop, debug mode starts off)
log_file_path = setup_logging(debug_mode=False)
logger = get_logger(__name__)

# Log system information for debugging
from components.logger_config import _dynamic_logger
_dynamic_logger.log_system_info()

# Fix numpy/OpenBLAS stack overflow on macOS ARM64 BEFORE importing any modules
if sys.platform == "darwin":
    # Limit OpenBLAS threads to prevent stack overflow in packaged app
    # But allow limited parallelism to avoid KCC multiprocessing deadlocks
    os.environ['OPENBLAS_NUM_THREADS'] = '2'
    os.environ['MKL_NUM_THREADS'] = '2'
    os.environ['NUMEXPR_NUM_THREADS'] = '2' 
    os.environ['OMP_NUM_THREADS'] = '2'
    os.environ['VECLIB_MAXIMUM_THREADS'] = '2'
    # Also set numpy specific thread controls
    os.environ['NPY_NUM_BUILD_JOBS'] = '2'
    # Set multiprocessing method to avoid issues in packaged app
    os.environ['MP_START_METHOD'] = 'spawn'

# Add KCC directory to Python path
if getattr(sys, 'frozen', False):
    logger.info("Running in packaged/frozen environment")
    # In packaged environment
    if hasattr(sys, '_MEIPASS'):
        logger.info(f"PyInstaller environment detected: {sys._MEIPASS}")
        kcc_dir = os.path.join(sys._MEIPASS, 'kindlecomicconverter')
        # Add 7z to PATH for KCC support in packaged environment
        # Try different possible locations for 7z in the packaged app
        import platform
        if platform.system() == "Windows":
            z7_candidates = [
                os.path.join(sys._MEIPASS, '7z.exe'),
                os.path.join(sys._MEIPASS, 'bin', '7z.exe'),
                os.path.join(sys._MEIPASS, 'tools', '7z.exe'),
            ]
        else:
            z7_candidates = [
                os.path.join(sys._MEIPASS, '7z'),
                os.path.join(sys._MEIPASS, 'bin', '7z'),
            ]
        
        z7_found = False
        for z7_path in z7_candidates:
            logger.info(f"Looking for 7z at: {z7_path}")
            if os.path.exists(z7_path):
                old_path = os.environ.get('PATH', '')
                z7_dir = os.path.dirname(z7_path)
                os.environ['PATH'] = z7_dir + os.pathsep + old_path
                logger.info(f"Added 7z to PATH: {z7_path}")
                logger.info(f"Updated PATH: {os.environ['PATH'][:200]}...")
                z7_found = True
                break
        
        if not z7_found:
            logger.warning(f"7z not found in packaged environment, tried: {z7_candidates}")
    else:
        logger.info("App Bundle environment detected")
        app_dir = os.path.dirname(sys.executable)
        resources_dir = os.path.join(os.path.dirname(app_dir), 'Resources')
        logger.info(f"App dir: {app_dir}")
        logger.info(f"Resources dir: {resources_dir}")
        kcc_dir = os.path.join(resources_dir, 'kindlecomicconverter')
        # Add 7z to PATH for KCC support in App Bundle
        # Try different possible locations for 7z in the App Bundle
        import platform
        if platform.system() == "Windows":
            z7_candidates = [
                os.path.join(resources_dir, '7z.exe'),
                os.path.join(resources_dir, 'bin', '7z.exe'),
                os.path.join(app_dir, '7z.exe'),  # Sometimes in the same dir as executable
            ]
        else:
            z7_candidates = [
                os.path.join(resources_dir, '7z'),
                os.path.join(resources_dir, 'bin', '7z'),
                os.path.join(app_dir, '7z'),  # Sometimes in the same dir as executable
            ]
        
        z7_found = False
        for z7_path in z7_candidates:
            logger.info(f"Looking for 7z at: {z7_path}")
            if os.path.exists(z7_path):
                old_path = os.environ.get('PATH', '')
                z7_dir = os.path.dirname(z7_path)
                os.environ['PATH'] = z7_dir + os.pathsep + old_path
                logger.info(f"Added 7z to PATH: {z7_path}")
                logger.info(f"Updated PATH: {os.environ['PATH'][:200]}...")
                z7_found = True
                break
        
        if not z7_found:
            logger.warning(f"7z not found in App Bundle, tried: {z7_candidates}")
else:
    logger.info("Running in development environment")
    # Development environment
    kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')

logger.info(f"KCC directory path: {kcc_dir}")
logger.info(f"KCC directory exists: {os.path.exists(kcc_dir)}")

if os.path.exists(kcc_dir):
    sys.path.insert(0, kcc_dir)
    logger.info(f"Added KCC to sys.path: {kcc_dir}")
else:
    logger.error(f"KCC directory not found: {kcc_dir}")

def setup_global_exception_handler():
    """Setup global exception handler to catch and log all unhandled exceptions"""
    import traceback
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Write error log to desktop
        try:
            import platform
            if platform.system() == "Windows":
                desktop_path = os.environ.get('USERPROFILE', os.path.expanduser('~'))
                desktop_path = os.path.join(desktop_path, 'Desktop')
            else:
                desktop_path = os.path.expanduser("~/Desktop")
            
            if not os.path.exists(desktop_path):
                desktop_path = os.path.dirname(sys.executable)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            error_log_path = os.path.join(desktop_path, f"eReader_Critical_Error_{timestamp}.txt")
            
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write("eReader CBZ Manga Converter - Critical Error\n")
                f.write("=" * 60 + "\n")
                f.write(f"Time: {datetime.datetime.now()}\n")
                f.write(f"Platform: {platform.system()}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Executable: {sys.executable}\n")
                f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                if hasattr(sys, '_MEIPASS'):
                    f.write(f"_MEIPASS: {sys._MEIPASS}\n")
                f.write("=" * 60 + "\n\n")
                f.write("Exception:\n")
                f.write(f"Type: {exc_type.__name__}\n")
                f.write(f"Value: {exc_value}\n\n")
                f.write("Traceback:\n")
                f.write(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                f.write("\n")
                f.write("Environment:\n")
                f.write(f"PATH: {os.environ.get('PATH', 'Not set')}\n")
                f.write(f"Current directory: {os.getcwd()}\n")
            
            print(f"[CRITICAL ERROR] Error log written to: {error_log_path}")
        except Exception as e:
            print(f"[ERROR] Failed to write critical error log: {e}")
    
    sys.excepthook = handle_exception

def main():
    # Set multiprocessing start method for KCC compatibility
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Already set, ignore
        pass
    
    # Setup global exception handler
    setup_global_exception_handler()
    
    # Check if this is a multiprocessing child process - if so, exit early
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('--multiprocessing') or arg.startswith('tracker_fd=') or arg.startswith('pipe_handle='):
                logger.info("Detected multiprocessing child process, exiting early")
                return 0

    logger.info("Starting main application...")
    
    try:
        # Import GUI after path setup
        from gui.mainwindow import MainWindow
        
        # Create application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Application started successfully")
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    # CRITICAL: Protect multiprocessing to prevent infinite instances
    multiprocessing.freeze_support()
    sys.exit(main())
