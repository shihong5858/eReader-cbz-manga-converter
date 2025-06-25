import logging
import os
import sys
import datetime
import tempfile

from PySide6.QtCore import QThread, Signal

from .converter import EPUBConverter
from ..logger_config import get_logger


class ConversionWorker(QThread):
    """Worker thread for converting a single file with progress tracking."""

    # Signals for communication with GUI
    progress = Signal(int)  # Progress percentage (0-100)
    status = Signal(str)    # Current status message
    completed = Signal(bool)  # Success status
    error = Signal(str)     # Error message

    # Progress steps and their corresponding percentage
    PROGRESS_STEPS = {
        "Starting conversion": 0,
        "Processing EPUB file": 5,
        "Extracting images": 10,
        "Processing images": 20,
        "Creating ZIP file": 40,
        "Running KCC conversion": 50,
        "Preparing source images": 55,
        "Checking images": 60,
        "Processing KCC images": 65,
        "Creating CBZ file": 85,
        "Completed": 100
    }

    def __init__(self, input_file, output_dir):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self._stop = False
        self._current_step = ""
        self._current_progress = 0
        self.converter = EPUBConverter()
        self.logger = get_logger(__name__)

    def update_progress(self, message):
        """Update progress based on the current processing step."""
        try:
            if isinstance(message, (int, float)):
                # Handle numeric progress updates
                progress = int(message)
                # Directly emit the progress value if it's a numeric update
                self._current_progress = progress
                self.progress.emit(self._current_progress)
            else:
                # Handle status message updates
                message = str(message).strip()

                # Special handling for KCC status messages
                if "Preparing source images" in message:
                    message = "Preparing source images"
                elif "Checking images" in message:
                    message = "Checking images"
                elif "Processing images" in message:
                    message = "Processing KCC images"
                elif "Creating CBZ file" in message:
                    message = "Creating CBZ file"

                if message in self.PROGRESS_STEPS:
                    self._current_step = message
                    self._current_progress = self.PROGRESS_STEPS[message]
                    self.progress.emit(self._current_progress)
                    self.status.emit(message)
        except Exception as e:
            self.logger.warning(f"Error updating progress: {e}")

    def _write_worker_error_log(self, error_msg, traceback_info=None):
        """Write worker-level error log"""
        try:
            # Determine log path
            if sys.platform == "win32":
                desktop_path = os.environ.get('USERPROFILE', os.path.expanduser('~'))
                desktop_path = os.path.join(desktop_path, 'Desktop')
            else:
                desktop_path = os.path.expanduser("~/Desktop")
            
            if not os.path.exists(desktop_path):
                desktop_path = tempfile.gettempdir()
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            error_log_path = os.path.join(desktop_path, f"eReader_Worker_Error_{timestamp}.txt")
            
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write("eReader CBZ Manga Converter - Worker Error Log\n")
                f.write("=" * 60 + "\n")
                f.write(f"Time: {datetime.datetime.now()}\n")
                f.write(f"Platform: {sys.platform}\n")
                f.write(f"Input file: {self.input_file}\n")
                f.write(f"Output directory: {self.output_dir}\n")
                f.write(f"Error: {error_msg}\n")
                f.write("=" * 60 + "\n\n")
                
                if traceback_info:
                    f.write("Traceback:\n")
                    f.write(traceback_info)
                    f.write("\n")
                
                f.write("Environment:\n")
                f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                f.write(f"Executable: {sys.executable}\n")
                f.write(f"PATH: {os.environ.get('PATH', 'Not set')}\n")
            
            self.status.emit(f"Worker error log saved to: {error_log_path}")
            print(f"[WORKER ERROR LOG] Error log written to: {error_log_path}")
        except Exception as e:
            print(f"[ERROR] Failed to write worker error log: {e}")

    def run(self):
        """Run the conversion process."""
        try:
            self.logger.info(f"Starting conversion worker for: {os.path.basename(self.input_file)}")
            
            # Initial progress
            self.update_progress("Starting conversion")

            # Run conversion
            success = self.converter.convert(
                self.input_file,
                self.output_dir,
                progress_callback=self.update_progress,
                status_callback=self.status.emit
            )

            if success:
                self.update_progress("Completed")
                self.completed.emit(True)
                self.logger.info(f"Conversion completed successfully: {os.path.basename(self.input_file)}")
            else:
                error_msg = "Conversion failed - check error log on Desktop"
                self.error.emit(error_msg)
                self.completed.emit(False)
                self.logger.error(f"Conversion failed: {os.path.basename(self.input_file)}")

        except Exception as e:
            import traceback
            error_msg = f"Worker error: {str(e)}"
            self.logger.error(f"Worker error for {os.path.basename(self.input_file)}: {e}")
            
            # Write detailed error log
            self._write_worker_error_log(error_msg, traceback.format_exc())
            
            self.error.emit(error_msg)
            self.completed.emit(False)

    def stop(self):
        """Stop the conversion process."""
        self._stop = True
        self.logger.info(f"Conversion worker stop requested for: {os.path.basename(self.input_file)}")
