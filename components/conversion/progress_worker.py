from PySide6.QtCore import QThread, Signal
import logging
from .converter import EPUBConverter

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
    
    def update_progress(self, message):
        """Update progress based on the current processing step."""
        if isinstance(message, (int, float)):
            # Handle numeric progress updates
            progress = int(message)
            # Directly emit the progress value if it's a numeric update
            self._current_progress = progress
            self.progress.emit(self._current_progress)
            logging.debug(f"Progress update: {progress}%")
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
                logging.debug(f"Status update: {message} ({self._current_progress}%)")
    
    def run(self):
        """Run the conversion process."""
        try:
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
            else:
                self.error.emit("Conversion failed")
                self.completed.emit(False)
                
        except Exception as e:
            logging.error(f"Error in worker: {str(e)}")
            self.error.emit(str(e))
            self.completed.emit(False)
    
    def stop(self):
        """Stop the conversion process."""
        self._stop = True 