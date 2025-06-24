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
    # In packaged environment
    if hasattr(sys, '_MEIPASS'):
        kcc_dir = os.path.join(sys._MEIPASS, 'kindlecomicconverter')
        # Add 7z to PATH for KCC support in packaged environment
        z7_path = os.path.join(sys._MEIPASS, '7z')
        if os.path.exists(z7_path):
            os.environ['PATH'] = os.path.dirname(z7_path) + os.pathsep + os.environ.get('PATH', '')
            logger.info(f"Added 7z to PATH: {z7_path}")
        else:
            logger.warning(f"7z not found in packaged environment: {z7_path}")
    else:
        app_dir = os.path.dirname(sys.executable)
        resources_dir = os.path.join(os.path.dirname(app_dir), 'Resources')
        kcc_dir = os.path.join(resources_dir, 'kindlecomicconverter')
        # Add 7z to PATH for KCC support in App Bundle
        z7_path = os.path.join(resources_dir, '7z')
        if os.path.exists(z7_path):
            os.environ['PATH'] = os.path.dirname(z7_path) + os.pathsep + os.environ.get('PATH', '')
            logger.info(f"Added 7z to PATH: {z7_path}")
        else:
            logger.warning(f"7z not found in App Bundle: {z7_path}")
else:
    # Development environment
    kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')

logger.info(f"KCC directory path: {kcc_dir}")
logger.info(f"KCC directory exists: {os.path.exists(kcc_dir)}")

if os.path.exists(kcc_dir):
    sys.path.insert(0, kcc_dir)
    logger.info(f"Added KCC to sys.path: {kcc_dir}")
else:
    logger.error(f"KCC directory not found: {kcc_dir}")

def main():
    # Set multiprocessing start method for KCC compatibility
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Already set, ignore
        pass
    
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
