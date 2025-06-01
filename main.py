import logging
import multiprocessing
import os
import sys

from PySide6.QtWidgets import QApplication

from components.conversion import EPUBConverter
from gui.mainwindow import MainWindow

# Add KCC directory to Python path
kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')
sys.path.append(kcc_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
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
