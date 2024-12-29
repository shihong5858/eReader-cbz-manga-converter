from PySide6.QtCore import QThread, Signal
import os
import logging
import sys
import re

# Add KCC directory to Python path
kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')
sys.path.append(kcc_dir)

from main import process_with_kcc

class SingleFileWorker(QThread):
    """Worker thread for converting a single file."""
    progress = Signal(int)  # Progress percentage (0-100)
    status = Signal(str)  # Current status message
    completed = Signal(bool)  # Success status
    error = Signal(str)  # Error message
    
    # Progress steps and their corresponding percentage
    PROGRESS_STEPS = {
        "Starting conversion": 0,
        "Processing EPUB file": 10,
        "Extracting images": 20,
        "Processing images": 40,
        "Creating ZIP file": 60,
        "Running KCC conversion": 80,
        "Completed": 100
    }
    
    def __init__(self, input_file, output_dir, kcc_options):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.kcc_options = kcc_options
        self._stop = False
        self._current_step = ""
    
    def update_progress(self, message):
        """Update progress based on the current processing step."""
        message = message.strip()
        if message in self.PROGRESS_STEPS and message != self._current_step:
            self._current_step = message
            progress = self.PROGRESS_STEPS[message]
            self.progress.emit(progress)
            self.status.emit(message)
            logging.debug(f"Progress update: {message} ({progress}%)")

    def run(self):
        try:
            # Set up logging handler to capture progress messages
            class ProgressHandler(logging.Handler):
                def __init__(self, worker):
                    super().__init__()
                    self.worker = worker
                    # Regular expressions for matching progress messages
                    self.patterns = [
                        (r"Starting conversion", "Starting conversion"),
                        (r"Processing EPUB file", "Processing EPUB file"),
                        (r"Extracting images", "Extracting images"),
                        (r"Processing images", "Processing images"),
                        (r"Creating ZIP file", "Creating ZIP file"),
                        (r"Running KCC conversion", "Running KCC conversion"),
                        (r"Conversion completed", "Completed")
                    ]
                
                def emit(self, record):
                    msg = record.getMessage()
                    # Remove timestamp and log level if present
                    if ' - INFO - ' in msg:
                        msg = msg.split(' - INFO - ')[1]
                    
                    # Try to match each pattern in order
                    for pattern, step in self.patterns:
                        if re.search(pattern, msg, re.IGNORECASE):
                            self.worker.update_progress(step)
                            break
            
            # Add progress handler to root logger
            handler = ProgressHandler(self)
            logger = logging.getLogger()
            logger.addHandler(handler)
            
            try:
                # Initial progress
                self.progress.emit(0)
                self.status.emit("Starting conversion...")
                
                # Run conversion
                success = process_with_kcc(
                    self.input_file, 
                    self.output_dir,
                    progress_callback=self.progress.emit,
                    status_callback=self.status.emit
                )
                
                if success:
                    self.update_progress("Completed")
                    self.completed.emit(True)
                else:
                    self.error.emit("Conversion failed")
                    self.completed.emit(False)
                    
            finally:
                # Remove progress handler
                logger.removeHandler(handler)
                
        except Exception as e:
            logging.error(f"Error in worker: {str(e)}")
            self.error.emit(str(e))
            self.completed.emit(False)

    def stop(self):
        self._stop = True 