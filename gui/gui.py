import sys
from PySide6.QtWidgets import QApplication
from .mainwindow import MainWindow

def run_gui():
    """Start the GUI application."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_()) 