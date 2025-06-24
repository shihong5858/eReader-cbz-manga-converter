import logging
import os

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
                self.error.emit("Conversion failed")
                self.completed.emit(False)
                self.logger.error(f"Conversion failed: {os.path.basename(self.input_file)}")

        except Exception as e:
            error_msg = f"Worker error: {str(e)}"
            self.logger.error(f"Worker error for {os.path.basename(self.input_file)}: {e}")
            self.error.emit(error_msg)
            self.completed.emit(False)

    def stop(self):
        """Stop the conversion process."""
        self._stop = True
        self.logger.info(f"Conversion worker stop requested for: {os.path.basename(self.input_file)}")
