import os
import sys
import logging
from PySide6.QtWidgets import QApplication
from gui.mainwindow import MainWindow
from components.conversion import EPUBConverter

# Add KCC directory to Python path
kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')
sys.path.append(kcc_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Check for command line arguments
    if len(sys.argv) > 1:
        if len(sys.argv) != 3:
            print("Usage: python script.py <input_file> <output_dir>")
            return 1
        
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        
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
    sys.exit(main()) 