import logging
import multiprocessing
import os
import sys
import datetime

# Import ResourceManager early
from components.resource_manager import get_resource_manager

# Initialize ResourceManager and get paths
resource_manager = get_resource_manager()

# Fix working directory for PyInstaller using ResourceManager
def fix_working_directory():
    if getattr(sys, 'frozen', False):
        base_path = resource_manager.base_path
        os.chdir(str(base_path))

# Fix working directory immediately
fix_working_directory()

# Setup detailed logging to file
def setup_logging():
    """Setup logging to both console and file for debugging"""
    # Create log file on Desktop
    desktop_path = os.path.expanduser("~/Desktop")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"eReader_CBZ_Debug_{timestamp}.log"
    log_file_path = os.path.join(desktop_path, log_filename)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("eReader CBZ Manga Converter - Debug Session Started")
    logger.info(f"Log file: {log_file_path}")
    
    # Log ResourceManager debug info
    debug_info = resource_manager.debug_info()
    for key, value in debug_info.items():
        logger.info(f"{key}: {value}")
    
    logger.info("="*60)

# Setup logging immediately
setup_logging()

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

from PySide6.QtWidgets import QApplication

from components.conversion import EPUBConverter
from gui.mainwindow import MainWindow

logger = logging.getLogger(__name__)

# Add KCC directory to Python path using ResourceManager
kcc_added = resource_manager.add_kcc_to_path()
logger.info(f"KCC directory path: {resource_manager.kcc_path}")
logger.info(f"KCC directory exists: {resource_manager.kcc_path.exists()}")
logger.info(f"Added KCC to sys.path: {kcc_added}")

if not kcc_added:
    logger.error(f"KCC directory not found or could not be added: {resource_manager.kcc_path}")

def main():
    # Set multiprocessing start method for KCC compatibility
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Already set, ignore
        pass
    
    # Check if this is a multiprocessing child process
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('--multiprocessing') or arg.startswith('tracker_fd=') or arg.startswith('pipe_handle='):
                return 0

    # Check for command line arguments
    # Filter out PyInstaller and macOS specific arguments
    filtered_args = []
    for i, arg in enumerate(sys.argv):
        # Skip the script name itself
        if i == 0:
            filtered_args.append(arg)
            continue

        # Skip PyInstaller multiprocessing arguments
        if arg.startswith('--multiprocessing'):
            continue
        if arg.startswith('tracker_fd='):
            continue
        if arg.startswith('pipe_handle='):
            continue
        if arg.startswith('-'):
            continue

        filtered_args.append(arg)

    # Only treat as command-line mode if we have exactly 3 arguments (script + 2 params)
    # and the arguments don't look like GUI arguments
    if len(filtered_args) == 3:
        input_file = filtered_args[1]
        output_dir = filtered_args[2]

        print(f"Input file: {input_file}")
        print(f"Output directory: {output_dir}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        converter = EPUBConverter()
        success = converter.convert(input_file, output_dir)
        return 0 if success else 1
    else:
        # Start GUI
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app.exec()

if __name__ == "__main__":
    # Protect multiprocessing
    multiprocessing.freeze_support()
    sys.exit(main())
