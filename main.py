import os
import sys
import logging
import time
import io
import threading
import queue
from contextlib import contextmanager
from worker import SingleFileWorker

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@contextmanager
def capture_output():
    """Capture stdout in a thread-safe way."""
    # Create a pipe to capture output
    stdout_fd = sys.stdout.fileno()
    read_fd, write_fd = os.pipe()
    
    # Create a queue for the output
    output_queue = queue.Queue()
    
    def reader():
        """Read from the pipe and put into queue."""
        with os.fdopen(read_fd, 'r') as pipe_read:
            for line in pipe_read:
                if line.strip():
                    output_queue.put(line.strip())
                    logging.info(line.strip())
    
    # Start reader thread
    reader_thread = threading.Thread(target=reader)
    reader_thread.daemon = True
    reader_thread.start()
    
    try:
        # Redirect stdout to the pipe
        os.dup2(write_fd, stdout_fd)
        yield output_queue
    finally:
        # Restore stdout
        os.close(write_fd)
        reader_thread.join(timeout=1)

def process_with_kcc(input_file, output_file, kcc_options):
    try:
        # Add KCC directory to Python path
        kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')
        sys.path.append(kcc_dir)
        
        from kindlecomicconverter.comic2ebook import main as kcc_main
        
        # Convert paths to absolute paths and normalize them
        input_file = os.path.abspath(os.path.normpath(input_file))
        output_file = os.path.abspath(os.path.normpath(output_file))
        
        # Ensure input file exists
        if not os.path.exists(input_file):
            logging.error(f"Input file does not exist: {input_file}")
            return False
        
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_file)
            os.makedirs(output_dir, exist_ok=True)
            
            # Remove output file if it already exists
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    logging.warning(f"Failed to remove existing output file: {str(e)}")
            
            # Split KCC options into a list and ensure input/output files are correctly placed
            kcc_args = kcc_options.split()
            
            # Remove any existing -o or output file
            if '-o' in kcc_args:
                idx = kcc_args.index('-o')
                if idx + 1 < len(kcc_args):
                    kcc_args.pop(idx + 1)  # Remove output file
                kcc_args.pop(idx)  # Remove -o
            
            # Add input and output files
            kcc_args.extend([input_file, '-o', output_file])
            
            logging.info(f"Running KCC with args: {kcc_args}")
            
            # Capture and process output in real-time
            with capture_output() as output_queue:
                # Call KCC's main function
                kcc_main(kcc_args)
                
                # Wait for file system
                time.sleep(1)
            
            # Check for output file
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logging.info(f"KCC processing completed successfully for {input_file}")
                return True
            else:
                logging.error(f"KCC processing failed: output file not found or empty for {input_file}")
                return False
            
        finally:
            # Clean up temporary files
            if 'temp_dir' in locals() and temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logging.info(f"Cleaned up KCC temporary directory: {temp_dir}")
                except Exception as e:
                    logging.warning(f"Failed to clean up temporary directory: {str(e)}")
    
    except Exception as e:
        logging.error(f"Error in process_with_kcc: {str(e)}")
        return False

def convert_epub_to_cbz(input_file, output_dir, kcc_options):
    """Synchronously convert a single EPUB file to CBZ."""
    try:
        # Create output filename
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}.cbz")
        
        # Process with KCC
        success = process_with_kcc(input_file, output_file, kcc_options)
        
        if success:
            return True, None
        else:
            return False, f"Failed to convert {os.path.basename(input_file)}"
            
    except Exception as e:
        logging.error(f"Error converting {input_file}: {str(e)}")
        return False, str(e)

def main():
    # Check if input file is provided as command line argument
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if not os.path.exists(input_file):
            print(f"Error: Input file {input_file} does not exist!")
            return
        
        # Use the second argument as output directory if provided, otherwise use input file's directory
        output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(input_file)
        
        print(f"Input file: {input_file}")
        print(f"Output directory: {output_dir}")
        
        # Use default KCC options for command line mode
        default_options = "-p KoC -f CBZ --hq -mu --cropping 1 --croppingpower 1 --gamma 1.6"
        worker = SingleFileWorker(input_file, output_dir, default_options)
        
        # Set up signal handlers for clean shutdown
        import signal
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal. Cleaning up...")
            worker.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Connect signals
            worker.progress.connect(lambda x: print(f"Progress: {x}%"))
            worker.completed.connect(lambda x: print(f"Conversion completed: {x}"))
            worker.error.connect(lambda x: print(f"Error: {x}"))
            
            # Run worker directly
            worker.run()
            
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt. Cleaning up...")
            worker.stop()
            sys.exit(0)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)
            
        finally:
            # Ensure cleanup
            worker.cleanup()
        
        return

    # No command line arguments, start GUI
    try:
        from gui.gui import run_gui
        run_gui()
    except ImportError as e:
        print(f"Error starting GUI: {str(e)}")
        print("Please ensure PySide6 is installed for GUI support.")
        sys.exit(1)

if __name__ == "__main__":
    main() 