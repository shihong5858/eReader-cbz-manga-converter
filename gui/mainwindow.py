import json
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from components.conversion import ConversionWorker
from components.resource_manager import get_resource_manager
from components.logger_config import enable_debug, disable_debug, is_debug_enabled

# Set system monospace font based on platform
if sys.platform == "darwin":
    SYSTEM_MONOSPACE_FONT = "Menlo"  # macOS system monospace font
else:
    SYSTEM_MONOSPACE_FONT = "monospace"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_title = "EPUB to CBZ Converter"
        self.setWindowTitle(self.base_title)
        self.logger = logging.getLogger(__name__)

        # Set initial window size including the hidden options area
        self.initial_height = 480  # Decreased by 10px
        self.setGeometry(100, 100, 600, self.initial_height)
        self.setMinimumWidth(600)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)  # Fixed spacing between major sections
        main_layout.setContentsMargins(15, 5, 15, 15)

        # Description section with fixed height
        description_section = QWidget()
        description_layout = QVBoxLayout(description_section)
        description_layout.setContentsMargins(0, 0, 0, 0)
        description_layout.setSpacing(0)

        description_label = QLabel("Convert your EPUB files to CBZ format with optimized settings for Kobo devices.")
        description_label.setStyleSheet("""
            font-size: 14px;
            color: #666;
            padding: 0;
            margin: 0;
            min-height: 30px;
            max-height: 30px;
            line-height: 30px;
        """)
        description_label.setAlignment(Qt.AlignCenter)
        description_layout.addWidget(description_label)
        description_section.setFixedHeight(30)
        main_layout.addWidget(description_section)

        # Add path selection area
        paths_layout = QVBoxLayout()
        paths_layout.setSpacing(10)
        paths_layout.setContentsMargins(0, 0, 0, 0)

        # Create a container for paths section with fixed height
        paths_section = QWidget()
        paths_section.setLayout(paths_layout)
        paths_section.setFixedHeight(220)  # Decreased from 230 to 220

        # Add input path selection
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_label = QLabel("Input:")
        input_label.setStyleSheet("font-weight: bold;")
        input_label.setFixedWidth(50)  # Set fixed width for alignment
        input_layout.addWidget(input_label)

        # Create input button and path label
        self.select_input_button = QPushButton("Browse")
        self.select_input_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                background: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        self.select_input_button.clicked.connect(self.select_input_path)
        input_layout.addWidget(self.select_input_button)

        self.input_path_label = QLabel()
        self.input_path_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: {SYSTEM_MONOSPACE_FONT};
                margin-left: 10px;
                padding: 4px 8px;
                background: transparent;
                border-radius: 3px;
                min-height: 20px;
                line-height: 20px;
            }}
            QLabel[hasPath="true"] {{
                background: #666;
            }}
            QLabel[hasPath="true"]:hover {{
                background: #777;
            }}
            QLabel[clickable="false"] {{
                background: #cccccc !important;
            }}
        """)
        self.input_path_label.setProperty("hasPath", False)
        self.input_path_label.setProperty("clickable", True)
        self.input_path_label.setCursor(Qt.PointingHandCursor)
        self.input_path_label.mousePressEvent = self.handle_input_path_click
        input_layout.addWidget(self.input_path_label)
        input_layout.addStretch()
        paths_layout.addLayout(input_layout)

        # Add drag-drop area with fixed height
        self.drop_area = QLabel("Drag and drop EPUB file here\nor click to select")
        self.drop_area.setStyleSheet("""
            QLabel {
                padding: 20px;
                background: #f8f8f8;
                font-size: 16px;
                color: #666;
                border-radius: 5px;
            }
            QLabel[disabled="true"] {
                background: #e0e0e0;
                color: #999;
            }
        """)
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setFixedHeight(110)  # Decreased from 120 to 110
        self.drop_area.setProperty("disabled", False)
        self.drop_area.setCursor(Qt.PointingHandCursor)
        paths_layout.addWidget(self.drop_area)

        # Make drop area clickable
        self.drop_area.mousePressEvent = self.handle_drop_area_click

        # Output path selection with fixed margins
        output_layout = QHBoxLayout()
        output_layout.setSpacing(10)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_label = QLabel("Output:")
        output_label.setStyleSheet("font-weight: bold;")
        output_label.setFixedWidth(50)  # Set fixed width for alignment
        output_layout.addWidget(output_label)

        # Create output button and path label
        self.output_button = QPushButton("Browse")
        self.output_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                background: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        self.output_button.clicked.connect(self.select_output_path)
        output_layout.addWidget(self.output_button)

        # Add path display
        self.output_path = QLabel()
        self.output_path.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: {SYSTEM_MONOSPACE_FONT};
                margin-left: 10px;
                padding: 4px 8px;
                background: transparent;
                border-radius: 3px;
                min-height: 20px;
                line-height: 20px;
            }}
            QLabel[hasPath="true"] {{
                background: #666;
            }}
            QLabel[hasPath="true"]:hover {{
                background: #777;
            }}
            QLabel[clickable="false"] {{
                background: #cccccc !important;
            }}
        """)
        self.output_path.setProperty("hasPath", False)
        self.output_path.setProperty("clickable", True)
        self.output_path.setCursor(Qt.PointingHandCursor)
        self.output_path.mousePressEvent = self.handle_output_path_click
        output_layout.addWidget(self.output_path)
        output_layout.addStretch()
        paths_layout.addLayout(output_layout)

        main_layout.addWidget(paths_section)

        # Create a container for device and progress sections
        device_progress_container = QWidget()
        device_progress_layout = QVBoxLayout(device_progress_container)
        device_progress_layout.setSpacing(10)
        device_progress_layout.setContentsMargins(0, 0, 0, 0)

        # Add device selection in a fixed height container
        self.device_section = QWidget()
        device_layout = QVBoxLayout(self.device_section)
        device_layout.setSpacing(0)
        device_layout.setContentsMargins(0, 0, 0, 0)

        # Device selection row
        device_row = QHBoxLayout()
        device_row.setSpacing(10)
        device_row.setContentsMargins(0, 0, 0, 0)
        device_label = QLabel("Device:")
        device_label.setStyleSheet("font-weight: bold;")
        device_row.addWidget(device_label)

        self.device_combo = QComboBox()
        if sys.platform == "darwin":
            self.device_combo.setStyle(QStyleFactory.create("macOS"))
        self.device_combo.setMinimumWidth(200)
        self.device_combo.setMaximumWidth(300)
        self.device_combo.setFixedHeight(32)
        self.load_device_info()
        self.device_combo.currentIndexChanged.connect(self.update_options_from_device)
        device_row.addWidget(self.device_combo)

        # Add Options button
        self.options_button = QPushButton("Options")
        if sys.platform == "darwin":
            self.options_button.setStyle(QStyleFactory.create("macOS"))
            self.options_button.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.options_button.setFixedSize(80, 32)
        device_row.setAlignment(self.options_button, Qt.AlignVCenter)
        self.options_button.setCheckable(True)
        self.options_button.setChecked(False)
        self.options_button.clicked.connect(self.toggle_options)
        device_row.addWidget(self.options_button)
        device_row.addStretch()
        device_layout.addLayout(device_row)

        # Add a fixed spacer
        spacer = QWidget()
        spacer.setFixedHeight(10)
        device_layout.addWidget(spacer)

        # Add options container
        self.options_container = QWidget()
        options_container_layout = QVBoxLayout(self.options_container)
        options_container_layout.setSpacing(5)
        options_container_layout.setContentsMargins(0, 0, 0, 0)

        options_label = QLabel("Conversion Options:")
        options_label.setStyleSheet("font-weight: bold;")
        self.options_input = QLineEdit()
        self.options_input.setText("-p KoC -f CBZ --hq -mu --cropping 1 --croppingpower 1 --gamma 1.6")
        self.options_input.setPlaceholderText("Enter KCC options...")
        self.options_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background: white;
                color: #333;
            }
        """)
        options_container_layout.addWidget(options_label)
        options_container_layout.addWidget(self.options_input)
        device_layout.addWidget(self.options_container)

        # Initially hide options
        self.options_container.hide()
        self.device_section.setFixedHeight(50)  # Height without options
        self.options_height = 70  # Restored to original height

        # Add progress section with fixed margins
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        # Create a horizontal layout for progress label and status
        progress_label_layout = QHBoxLayout()
        progress_label_layout.setSpacing(5)
        progress_label_layout.setContentsMargins(0, 0, 0, 5)
        self.progress_label = QLabel("Progress:")
        self.progress_label.setStyleSheet("font-weight: bold;")
        progress_label_layout.addWidget(self.progress_label)

        self.progress_status = QLabel()
        self.progress_status.setStyleSheet("color: #666;")
        progress_label_layout.addWidget(self.progress_status)
        progress_label_layout.addStretch()
        progress_layout.addLayout(progress_label_layout)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                margin: 0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        progress_section = QWidget()
        progress_section.setLayout(progress_layout)
        progress_section.setFixedHeight(80)  # Fixed height for progress section

        # Add sections to the container
        device_progress_layout.addWidget(self.device_section)
        device_progress_layout.addWidget(progress_section)

        # Add container to main layout
        main_layout.addWidget(device_progress_container)

        # Add convert button with fixed spacing
        main_layout.addSpacing(10)
        self.convert_button = QPushButton("Convert")
        self.convert_button.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border: none;
                border-radius: 5px;
                background: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        self.convert_button.clicked.connect(self.start_conversion)
        main_layout.addWidget(self.convert_button)

        # Initialize state
        self.input_files = []
        self.current_file_index = 0
        self.worker = None
        self.update_convert_button_state()
        
        # Setup hidden debug controls
        self._setup_hidden_debug_controls()
        
        # Update title based on initial debug state
        self._update_title_for_debug_state()

    def select_input_path(self, event=None):
        dialog = QFileDialog(self)

        # Use native dialog on macOS with support for both files and directories
        if sys.platform == "darwin":
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
            # First try to select files
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("EPUB files (*.epub)")
        else:
            # For other platforms, use custom dialog
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("EPUB files (*.epub);;All files (*.*)")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            paths = dialog.selectedFiles()
            if not paths and sys.platform == "darwin":
                # If no files selected, try directory selection
                dialog.setFileMode(QFileDialog.FileMode.Directory)
                dialog.setNameFilter("")
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    paths = dialog.selectedFiles()

            if paths:
                # Handle both files and directories
                processed_paths = []
                for path in paths:
                    if os.path.isdir(path):
                        # If it's a directory, recursively find all EPUB files
                        for root, _, files in os.walk(path):
                            for file in files:
                                if file.lower().endswith('.epub'):
                                    processed_paths.append(os.path.join(root, file))
                    elif path.lower().endswith('.epub'):
                        # If it's an EPUB file, add it directly
                        processed_paths.append(path)

                if processed_paths:
                    # Sort paths to ensure consistent order
                    processed_paths.sort()
                    self.handle_selected_paths(processed_paths)

    def handle_selected_paths(self, paths):
        # Reset progress and status
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.progress_status.clear()
        self.input_files = paths

        self.logger.info(f"Selected {len(paths)} file(s) for conversion")

        # Update input path label and hide browse button
        if len(paths) == 1:
            display_text = os.path.basename(paths[0])
        else:
            display_text = f"{len(paths)} files selected"

        self.input_path_label.setText(display_text)
        self.input_path_label.setProperty("hasPath", True)
        self.input_path_label.style().unpolish(self.input_path_label)
        self.input_path_label.style().polish(self.input_path_label)

        # Hide input browse button
        self.select_input_button.hide()

        # Set default output directory if not set
        if not self.output_path.text():
            default_output = os.path.dirname(paths[0])
            self.output_path.setText(default_output)
            self.output_path.setProperty("hasPath", True)
            self.output_path.style().unpolish(self.output_path)
            self.output_path.style().polish(self.output_path)
            # Hide output browse button
            self.output_button.hide()

        # Update status
        if len(paths) == 1:
            self.progress_status.setText(f"Ready to convert: {display_text}")
        else:
            self.progress_status.setText(f"Ready to convert {len(paths)} files")

        self.update_convert_button_state()

    def select_output_path(self, event=None):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        if path:
            self.output_path.setText(path)
            self.output_path.setProperty("hasPath", True)
            self.output_path.style().unpolish(self.output_path)
            self.output_path.style().polish(self.output_path)

            self.update_convert_button_state()

    def handle_output_path_click(self, event):
        if self.output_path.property("clickable"):
            self.select_output_path()

    def handle_input_path_click(self, event):
        if self.input_path_label.property("clickable"):
            self.select_input_path()

    def handle_drop_area_click(self, event):
        if not self.drop_area.property("disabled"):
            self.select_input_path()

    def start_conversion(self):
        if not self.input_files or not self.output_path.text():
            self.logger.warning("Cannot start conversion: missing input files or output path")
            return

        try:
            # Validate output directory exists and is writable
            output_dir = self.output_path.text()
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.logger.info(f"Created output directory: {output_dir}")
                except Exception as e:
                    self.logger.error(f"Cannot create output directory: {e}")
                    self.handle_error(f"Cannot create output directory: {e}")
                    return
            
            if not os.access(output_dir, os.W_OK):
                self.logger.error(f"Output directory is not writable: {output_dir}")
                self.handle_error("Output directory is not writable")
                return

            self.logger.info(f"Starting conversion of {len(self.input_files)} file(s)")
            
            # Reset progress and status
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0%")
            self.progress_status.clear()

            # Disable UI elements during conversion
            self.convert_button.setEnabled(False)
            self.select_input_button.setEnabled(False)
            self.output_button.setEnabled(False)
            self.options_input.setEnabled(False)

            # Disable clicking on path labels
            self.input_path_label.setProperty("clickable", False)
            self.output_path.setProperty("clickable", False)
            self.input_path_label.setCursor(Qt.ArrowCursor)
            self.output_path.setCursor(Qt.ArrowCursor)
            self.input_path_label.style().unpolish(self.input_path_label)
            self.input_path_label.style().polish(self.input_path_label)
            self.output_path.style().unpolish(self.output_path)
            self.output_path.style().polish(self.output_path)

            # Disable drag-drop area
            self.drop_area.setProperty("disabled", True)
            self.drop_area.setCursor(Qt.ArrowCursor)
            self.drop_area.style().unpolish(self.drop_area)
            self.drop_area.style().polish(self.drop_area)

            self.current_file_index = 0
            self.process_next_file()
            
        except Exception as e:
            self.logger.error(f"Error starting conversion: {e}")
            self.handle_error(f"Error starting conversion: {e}")
            self.conversion_completed()

    def process_next_file(self):
        if self.current_file_index >= len(self.input_files):
            self.conversion_completed()
            return

        input_file = self.input_files[self.current_file_index]
        output_dir = self.output_path.text()

        # Update status for current file
        current_file = os.path.basename(input_file)
        total_files = len(self.input_files)
        self.progress_status.setText(f"Converting file {self.current_file_index + 1} of {total_files}: {current_file}")

        # Create and configure worker
        self.worker = ConversionWorker(input_file, output_dir)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.completed.connect(self.file_processed)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def update_progress(self, progress):
        """Update progress bar and status."""
        # Ensure progress is an integer
        try:
            progress = int(progress)
        except (TypeError, ValueError):
            return

        total_files = len(self.input_files)
        if total_files == 1:
            # Single file mode
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"{progress}%")
        else:
            # Multiple files mode - calculate overall progress
            # Each file contributes (100/total_files)% to the total progress
            file_weight = 100.0 / total_files
            # Calculate progress: completed files + current file progress
            completed_files_progress = self.current_file_index * file_weight
            current_file_progress = (progress * file_weight) / 100
            total_progress = completed_files_progress + current_file_progress

            # Ensure progress value is valid
            total_progress = max(0, min(100, total_progress))

            self.progress_bar.setValue(int(total_progress))
            self.progress_bar.setFormat(f"{int(total_progress)}%")

            current_file = os.path.basename(self.input_files[self.current_file_index])
            self.progress_status.setText(
                f"File {self.current_file_index + 1} of {total_files} - {current_file} ({progress}%)"
            )

    def update_status(self, status):
        """Update the status label with current progress information."""
        current_file = os.path.basename(self.input_files[self.current_file_index])
        total_files = len(self.input_files)
        if total_files == 1:
            self.progress_status.setText(f"{status} - {current_file}")
        else:
            self.progress_status.setText(
                f"File {self.current_file_index + 1} of {total_files} - {status} - {current_file}"
            )

    def handle_error(self, error_msg):
        """Handle error messages from the worker."""
        total_files = len(self.input_files)
        if total_files == 1:
            self.progress_status.setText(f"Error: {error_msg}")
        else:
            self.progress_status.setText(
                f"Error in file {self.current_file_index + 1} of {total_files}: {error_msg}"
            )
        self.logger.error(f"Conversion error: {error_msg}")

    def file_processed(self, success):
        """Handle file processing completion."""
        # Clean up worker
        if self.worker:
            self.worker.quit()
            self.worker.wait()
            self.worker = None

        if success:
            self.current_file_index += 1
            # Update progress for multiple files
            if len(self.input_files) > 1:
                progress = (self.current_file_index * 100) / len(self.input_files)
                self.progress_bar.setValue(int(progress))
                self.progress_bar.setFormat(f"{int(progress)}%")
                self.progress_status.setText(
                    f"Completed {self.current_file_index} of {len(self.input_files)} files"
                )

            # Process next file
            QTimer.singleShot(100, self.process_next_file)
        else:
            self.conversion_completed()

    def conversion_completed(self):
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("100%")

        # Re-enable UI elements after conversion
        self.convert_button.setEnabled(True)
        self.select_input_button.setEnabled(True)
        self.output_button.setEnabled(True)
        self.options_input.setEnabled(True)

        # Re-enable clicking on path labels
        self.input_path_label.setProperty("clickable", True)
        self.output_path.setProperty("clickable", True)
        self.input_path_label.setCursor(Qt.PointingHandCursor)
        self.output_path.setCursor(Qt.PointingHandCursor)
        self.input_path_label.style().unpolish(self.input_path_label)
        self.input_path_label.style().polish(self.input_path_label)
        self.output_path.style().unpolish(self.output_path)
        self.output_path.style().polish(self.output_path)

        # Re-enable drag-drop area
        self.drop_area.setProperty("disabled", False)
        self.drop_area.setCursor(Qt.PointingHandCursor)
        self.drop_area.style().unpolish(self.drop_area)
        self.drop_area.style().polish(self.drop_area)

        # Update status
        total_files = len(self.input_files)
        if self.current_file_index == total_files:
            if total_files == 1:
                self.progress_status.setText("Conversion completed successfully!")
            else:
                self.progress_status.setText(f"All {total_files} files converted successfully!")
        else:
            self.progress_status.setText(
                f"Completed with errors ({self.current_file_index} of {total_files} files)"
            )

        # Reset state
        self.input_files = []
        self.current_file_index = 0
        self.input_path_label.setText("")
        self.input_path_label.setProperty("hasPath", False)
        self.input_path_label.style().unpolish(self.input_path_label)
        self.input_path_label.style().polish(self.input_path_label)

        # Show input browse button again
        self.select_input_button.show()

        # Update convert button state after resetting input files
        self.update_convert_button_state()

    def update_convert_button_state(self):
        has_input = bool(self.input_files)
        has_output = bool(self.output_path.text())

        self.convert_button.setEnabled(has_input and has_output)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not self.drop_area.property("disabled") and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if all(url.toLocalFile().lower().endswith('.epub') for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.drop_area.property("disabled"):
            paths = []
            for url in event.mimeData().urls():
                local_file = url.toLocalFile()
                if os.path.isfile(local_file) and local_file.lower().endswith('.epub'):
                    paths.append(local_file)
                elif os.path.isdir(local_file):
                    paths.append(local_file)

            if paths:
                # Reset progress bar before handling new files
                self.progress_bar.setValue(0)
                self.progress_bar.setFormat("0%")
                self.progress_status.clear()
                self.handle_selected_paths(paths)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()

    def load_device_info(self):
        """Load device information from JSON file and populate the combo box."""
        try:
            # Use ResourceManager to find device_info.json
            resource_manager = get_resource_manager()
            device_info_path = resource_manager.get_config_file('device_info.json')
            
            if not device_info_path:
                self.logger.error("Device info file not found")
                
                # Try some fallback locations
                fallback_paths = [
                    'config/device_info.json',
                    'device_info.json',
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'device_info.json'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'device_info.json')
                ]
                
                for fallback in fallback_paths:
                    if os.path.exists(fallback):
                        device_info_path = Path(fallback)
                        self.logger.info(f"Found device_info.json at fallback location: {device_info_path}")
                        break
                
                if not device_info_path:
                    self.logger.error("device_info.json not found in any location")
                    self.device_combo.addItem("Error: Device info not found", "error")
                    return

            self.logger.info(f"Loading device info from: {device_info_path}")
            
            try:
                with open(device_info_path, 'r', encoding='utf-8') as f:
                    device_data = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in device info file: {e}")
                self.device_combo.addItem("Error: Invalid device info file", "error")
                return
            except Exception as e:
                self.logger.error(f"Error reading device info file: {e}")
                self.device_combo.addItem("Error: Cannot read device info", "error")
                return

            # Store device info for later use
            self.device_info = device_data

            # Clear existing items
            self.device_combo.clear()

            # Sort devices by name for better user experience
            sorted_devices = sorted(device_data.items(), key=lambda x: x[1].get('name', x[0]))

            for device_id, device_info in sorted_devices:
                device_name = device_info.get('name', device_id)
                self.device_combo.addItem(device_name, device_id)

            # Set default device (Kobo Clara HD)
            default_index = self.device_combo.findData("KoC")
            if default_index != -1:
                self.device_combo.setCurrentIndex(default_index)

            self.logger.info(f"Loaded {len(device_data)} device configurations")

        except Exception as e:
            self.logger.error(f"Unexpected error loading device info: {e}")
            # Add error item to combo box
            self.device_combo.clear()
            self.device_combo.addItem(f"Error: {str(e)}", "error")
            # Initialize empty device_info to prevent AttributeError
            self.device_info = {}

    def update_options_from_device(self):
        """Update conversion options based on selected device."""
        device_code = self.device_combo.currentData()
        if device_code and hasattr(self, 'device_info') and device_code in self.device_info:
            device = self.device_info[device_code]
            options = f"-p {device_code} -f CBZ --hq -mu --cropping 1 --croppingpower 1 --gamma {device.get('sharpness', '1.8')}"
            self.options_input.setText(options)

    def toggle_options(self):
        """Toggle the visibility of conversion options."""
        if self.options_button.isChecked():
            # Show options and increase section height
            self.options_container.show()
            self.device_section.setFixedHeight(50 + self.options_height)
            # Adjust window height exactly by options_height
            self.setFixedHeight(self.height() + self.options_height)
        else:
            # Hide options and restore original height
            self.options_container.hide()
            self.device_section.setFixedHeight(50)
            # Decrease window height exactly by options_height
            self.setFixedHeight(self.height() - self.options_height)

    def _setup_hidden_debug_controls(self):
        """Setup hidden debug controls via keyboard shortcuts."""
        # Ctrl+Shift+D: Toggle debug mode
        debug_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        debug_shortcut.activated.connect(self._toggle_debug_mode)

    def _update_title_for_debug_state(self):
        """Update window title based on debug state."""
        if is_debug_enabled():
            self.setWindowTitle(f"{self.base_title} [DEBUG]")
        else:
            self.setWindowTitle(self.base_title)

    def _toggle_debug_mode(self):
        """Hidden debug mode toggle via keyboard shortcut."""
        try:
            if is_debug_enabled():
                disable_debug()
                self.logger.info("Debug mode disabled via keyboard shortcut")
                status_text = "Debug mode disabled"
            else:
                enable_debug()
                self.logger.info("Debug mode enabled via keyboard shortcut")
                
                # Import here to avoid circular imports
                from components.logger_config import get_log_file
                
                # Get the actual log file path to provide user feedback
                log_file_path = get_log_file()
                if log_file_path:
                    # Extract just the directory name for display
                    log_dir = log_file_path.parent.name
                    if log_dir.lower() == 'desktop':
                        status_text = "Debug mode enabled (log file created on Desktop)"
                    else:
                        status_text = f"Debug mode enabled (log file created in {log_dir})"
                else:
                    status_text = "Debug mode enabled (console logging only)"
            
            # Update window title based on new debug state
            self._update_title_for_debug_state()
            
            # Briefly show status
            if hasattr(self, 'progress_status'):
                self.progress_status.setText(status_text)
                QTimer.singleShot(5000, lambda: self.progress_status.setText(""))  # Show for 5 seconds
                
        except Exception as e:
            self.logger.error(f"Failed to toggle debug mode: {e}")
            # Show error to user
            if hasattr(self, 'progress_status'):
                self.progress_status.setText("Failed to toggle debug mode")
                QTimer.singleShot(3000, lambda: self.progress_status.setText(""))


