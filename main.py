import logging
import multiprocessing
import os
import sys

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

# Add KCC directory to Python path
if getattr(sys, 'frozen', False):
    # In packaged environment
    if hasattr(sys, '_MEIPASS'):
        kcc_dir = os.path.join(sys._MEIPASS, 'kindlecomicconverter')
    else:
        app_dir = os.path.dirname(sys.executable)
        resources_dir = os.path.join(os.path.dirname(app_dir), 'Resources')
        kcc_dir = os.path.join(resources_dir, 'kindlecomicconverter')
else:
    # Development environment
    kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')

if os.path.exists(kcc_dir):
    sys.path.insert(0, kcc_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
