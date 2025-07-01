import logging
import os
import time
import threading

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
        "Processing with KCC": 55,
        "Optimizing images": 65,
        "Creating CBZ file": 80,
        "Finalizing conversion": 90,
        "Nearly complete": 95,
        "Completed": 100
    }

    def __init__(self, input_file, output_dir):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self._stop = False
        self._current_step = ""
        self._current_progress = 0
        self._last_progress_time = time.time()
        self._progress_lock = threading.Lock()
        self.converter = EPUBConverter()
        self.logger = get_logger(__name__)

    def update_progress(self, message):
        """Update progress based on the current processing step."""
        try:
            with self._progress_lock:
                current_time = time.time()
                
                if isinstance(message, (int, float)):
                    # Handle numeric progress updates
                    progress = int(message)
                    # Ensure progress only moves forward
                    if progress > self._current_progress:
                        self._current_progress = progress
                        self.progress.emit(self._current_progress)
                        self._last_progress_time = current_time
                else:
                    # Handle status message updates
                    message = str(message).strip()

                    # Special handling for KCC status messages
                    if "Preparing source images" in message:
                        message = "Processing with KCC"
                    elif "Checking images" in message:
                        message = "Optimizing images"
                    elif "Processing images" in message:
                        message = "Optimizing images"
                    elif "Creating CBZ file" in message:
                        message = "Creating CBZ file"
                    elif "timeout" in message.lower() or "error" in message.lower():
                        # Handle error/timeout messages
                        self.logger.warning(f"Error status update: {message}")

                    if message in self.PROGRESS_STEPS:
                        new_progress = self.PROGRESS_STEPS[message]
                        # Only update if progress moves forward
                        if new_progress > self._current_progress:
                            self._current_step = message
                            self._current_progress = new_progress
                            self.progress.emit(self._current_progress)
                            self.status.emit(message)
                            self._last_progress_time = current_time
                    else:
                        # For unrecognized status messages, just emit them
                        self.status.emit(message)
                        
        except Exception as e:
            self.logger.warning(f"Error updating progress: {e}")

    def _check_progress_timeout(self):
        """Check if progress has been stuck for too long"""
        with self._progress_lock:
            current_time = time.time()
            if current_time - self._last_progress_time > 120:  # 2 minutes without progress
                self.logger.warning("Progress appears to be stuck, attempting to continue...")
                # Try to advance progress slightly
                if self._current_progress < 95:
                    self._current_progress = min(95, self._current_progress + 5)
                    self.progress.emit(self._current_progress)
                    self.status.emit("Continuing conversion...")
                    self._last_progress_time = current_time

    def run(self):
        """Run the conversion process."""
        start_time = time.time()
        timeout_timer = None
        
        try:
            self.logger.info(f"Starting conversion worker for: {os.path.basename(self.input_file)}")
            
            # Start a timer to check for progress timeouts
            def check_timeout():
                if not self._stop:
                    self._check_progress_timeout()
                    # Schedule next check
                    nonlocal timeout_timer
                    timeout_timer = threading.Timer(30.0, check_timeout)
                    timeout_timer.start()
            
            timeout_timer = threading.Timer(30.0, check_timeout)
            timeout_timer.start()
            
            # Initial progress
            self.update_progress("Starting conversion")

            # Run conversion with enhanced error handling
            try:
                success = self.converter.convert(
                    self.input_file,
                    self.output_dir,
                    progress_callback=self.update_progress,
                    status_callback=self.status.emit
                )
            except Exception as conversion_error:
                self.logger.error(f"Conversion exception: {conversion_error}")
                success = False
                error_msg = f"Conversion failed: {str(conversion_error)}"
                self.error.emit(error_msg)

            elapsed_time = time.time() - start_time
            self.logger.info(f"Conversion took {elapsed_time:.2f} seconds")

            if success:
                self.update_progress("Completed")
                self.completed.emit(True)
                self.logger.info(f"Conversion completed successfully: {os.path.basename(self.input_file)}")
            else:
                if not self._stop:  # Only emit error if not stopped by user
                    if elapsed_time > 300:  # 5 minutes
                        error_msg = "Conversion timed out - the file may be too large or complex"
                    else:
                        error_msg = "Conversion failed - check the input file and try again"
                    self.error.emit(error_msg)
                self.completed.emit(False)
                self.logger.error(f"Conversion failed: {os.path.basename(self.input_file)}")

        except Exception as e:
            error_msg = f"Worker error: {str(e)}"
            self.logger.error(f"Worker error for {os.path.basename(self.input_file)}: {e}")
            if not self._stop:
                self.error.emit(error_msg)
            self.completed.emit(False)
        finally:
            # Clean up timeout timer
            if timeout_timer:
                timeout_timer.cancel()

    def stop(self):
        """Stop the conversion process."""
        self._stop = True
        self.logger.info(f"Conversion worker stop requested for: {os.path.basename(self.input_file)}")
        # Force thread to quit after a reasonable timeout
        self.quit()
        if not self.wait(5000):  # Wait 5 seconds for clean shutdown
            self.terminate()
            self.logger.warning("Conversion worker had to be terminated forcefully")
