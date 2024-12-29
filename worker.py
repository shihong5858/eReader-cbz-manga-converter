from PySide6.QtCore import QThread, Signal
import logging
import re

class SingleFileWorker(QThread):
    """Worker thread for converting a single file."""
    progress = Signal(int)  # Progress percentage (0-100)
    status = Signal(str)  # Current status message
    completed = Signal(bool)  # Success status
    error = Signal(str)  # Error message
    
    # Progress steps and their corresponding percentage
    PROGRESS_STEPS = {
        "Starting conversion": 0,
        "Preparing source images": 10,
        "Checking images": 20,
        "Processing images": 60,
        "Creating CBZ file": 90,
        "Completed": 100
    }
    
    def __init__(self, input_file, output_dir, kcc_options):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.kcc_options = kcc_options
        self._is_running = True
        self._current_step = ""
        
    def stop(self):
        """Stop the worker thread."""
        self._is_running = False
    
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
        """Run the conversion process."""
        try:
            # Set up logging handler to capture progress messages
            class ProgressHandler(logging.Handler):
                def __init__(self, worker):
                    super().__init__()
                    self.worker = worker
                    # Regular expressions for matching progress messages
                    self.patterns = [
                        (r"Working on .+", "Starting conversion"),
                        (r"Preparing source images", "Preparing source images"),
                        (r"Checking images", "Checking images"),
                        (r"Processing images", "Processing images"),
                        (r"Creating CBZ file", "Creating CBZ file"),
                        (r"KCC processing completed successfully", "Completed")
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
                from main import convert_epub_to_cbz
                success, error = convert_epub_to_cbz(self.input_file, self.output_dir, self.kcc_options)
                
                if success:
                    self.update_progress("Completed")
                    self.completed.emit(True)
                else:
                    self.error.emit(error if error else "Unknown error occurred")
                    self.completed.emit(False)
                    
            finally:
                # Remove progress handler
                logger.removeHandler(handler)
                
        except Exception as e:
            self.error.emit(str(e))
            self.completed.emit(False) 