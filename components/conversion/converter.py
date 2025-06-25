import io
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
import datetime

# Import ResourceManager
from ..resource_manager import get_resource_manager
from ..logger_config import get_logger, is_debug_enabled

# Initialize ResourceManager
resource_manager = get_resource_manager()

# Add KCC module path using ResourceManager
if not resource_manager.add_kcc_to_path():
    logger = get_logger(__name__)
    logger.warning(f"KCC path not found at {resource_manager.kcc_path}")

class EPUBConverter:
    """EPUB to CBZ converter with progress tracking"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def convert(self, input_file, output_directory, progress_callback=None, status_callback=None):
        """
        Convert EPUB file to CBZ format

        Args:
            input_file (str): Path to input EPUB file
            output_directory (str): Path to output directory
            progress_callback (callable): Callback for progress updates (0-100)
            status_callback (callable): Callback for status message updates

        Returns:
            bool: True if conversion successful, False otherwise
        """
        temp_dir = None
        conversion_log = []  # Store conversion logs for error reporting
        
        try:
            # Store conversion start info
            conversion_log.append(f"Starting conversion: {os.path.basename(input_file)}")
            conversion_log.append(f"Output directory: {output_directory}")
            conversion_log.append(f"Platform: {platform.system()}")
            
            self.logger.info(f"Starting conversion: {os.path.basename(input_file)}")
            
            if status_callback:
                status_callback("Starting conversion")
            if progress_callback:
                progress_callback(0)

            # Validate input file
            if not os.path.exists(input_file):
                error_msg = f"Input file not found: {input_file}"
                conversion_log.append(f"ERROR: {error_msg}")
                raise FileNotFoundError(error_msg)
            if not input_file.lower().endswith('.epub'):
                error_msg = f"Invalid input file format: {input_file}"
                conversion_log.append(f"ERROR: {error_msg}")
                raise ValueError(error_msg)

            # Validate output directory
            if not os.path.exists(output_directory):
                try:
                    os.makedirs(output_directory, exist_ok=True)
                    conversion_log.append(f"Created output directory: {output_directory}")
                    self.logger.info(f"Created output directory: {output_directory}")
                except Exception as e:
                    error_msg = f"Cannot create output directory: {e}"
                    conversion_log.append(f"ERROR: {error_msg}")
                    raise PermissionError(error_msg)

            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()
            conversion_log.append(f"Created temporary directory: {temp_dir}")
            self.logger.info(f"Created temporary directory: {temp_dir}")

            if status_callback:
                status_callback("Processing EPUB file")
            if progress_callback:
                progress_callback(5)

            # Extract EPUB contents
            try:
                with zipfile.ZipFile(input_file, 'r') as epub:
                    epub.extractall(temp_dir)
                conversion_log.append("Successfully extracted EPUB contents")
                self.logger.info("Successfully extracted EPUB contents")
            except zipfile.BadZipFile as e:
                error_msg = f"Invalid EPUB file: {e}"
                conversion_log.append(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
            except Exception as e:
                error_msg = f"Failed to extract EPUB: {e}"
                conversion_log.append(f"ERROR: {error_msg}")
                raise RuntimeError(error_msg)

            if status_callback:
                status_callback("Extracting images")
            if progress_callback:
                progress_callback(10)

            # Process EPUB structure
            try:
                ordered_html_files = self._process_epub_structure(temp_dir)
                if not ordered_html_files:
                    conversion_log.append("WARNING: No HTML files found in EPUB")
                    self.logger.warning("No HTML files found in EPUB")
            except Exception as e:
                conversion_log.append(f"ERROR: Error processing EPUB structure: {e}")
                self.logger.error(f"Error processing EPUB structure: {e}")
                ordered_html_files = []

            if status_callback:
                status_callback("Processing images")
            if progress_callback:
                progress_callback(20)

            # Extract and order images
            try:
                ordered_images_dir = self._extract_images(temp_dir, ordered_html_files)
                image_count = len([f for f in os.listdir(ordered_images_dir) 
                                 if f.endswith(('.jpg', '.jpeg', '.png'))])
                if image_count == 0:
                    error_msg = "No images found in EPUB file"
                    conversion_log.append(f"ERROR: {error_msg}")
                    raise ValueError(error_msg)
                conversion_log.append(f"Extracted {image_count} images")
                self.logger.info(f"Extracted {image_count} images")
            except Exception as e:
                error_msg = f"Failed to extract images: {e}"
                conversion_log.append(f"ERROR: {error_msg}")
                raise RuntimeError(error_msg)

            if status_callback:
                status_callback("Creating ZIP file")
            if progress_callback:
                progress_callback(40)

            # Create CBZ file
            success = self._create_cbz(
                ordered_images_dir,
                input_file,
                output_directory,
                progress_callback,
                status_callback,
                conversion_log  # Pass conversion log to CBZ creation
            )

            if success:
                conversion_log.append(f"Conversion completed successfully: {os.path.basename(input_file)}")
                self.logger.info(f"Conversion completed successfully: {os.path.basename(input_file)}")
                if status_callback:
                    status_callback("Completed")
                if progress_callback:
                    progress_callback(100)
            else:
                conversion_log.append(f"Conversion failed: {os.path.basename(input_file)}")
                self.logger.error(f"Conversion failed: {os.path.basename(input_file)}")
                
                # Write error log even when returning False without exception
                self._write_error_log(input_file, output_directory, conversion_log, status_callback)

            return success

        except Exception as e:
            error_msg = f"Conversion failed for {os.path.basename(input_file)}: {str(e)}"
            conversion_log.append(f"ERROR: {error_msg}")
            self.logger.error(error_msg)
            if status_callback:
                status_callback(f"Error: {str(e)}")
            
            # Write error log on exception
            self._write_error_log(input_file, output_directory, conversion_log, status_callback)
            
            return False
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary directory: {e}")

    def _write_error_log(self, input_file, output_directory, conversion_log, status_callback=None):
        """Write error log to desktop or temp directory"""
        from ..logger_config import is_debug_enabled
        
        # Always write error log when conversion fails, regardless of debug mode
        if conversion_log:
            try:
                # Write conversion log to desktop for debugging
                # Use more reliable method for Windows desktop path
                if platform.system() == "Windows":
                    # Try Windows-specific environment variables first
                    desktop_path = os.environ.get('USERPROFILE')
                    if desktop_path:
                        desktop_path = os.path.join(desktop_path, 'Desktop')
                    else:
                        # Fallback to expanduser
                        desktop_path = os.path.expanduser("~/Desktop")
                else:
                    desktop_path = os.path.expanduser("~/Desktop")
                
                # Ensure desktop directory exists
                if not os.path.exists(desktop_path):
                    # Try to create it or use temp directory as fallback
                    try:
                        os.makedirs(desktop_path, exist_ok=True)
                    except:
                        desktop_path = tempfile.gettempdir()
                        print(f"[WARNING] Using temp directory for error log: {desktop_path}")
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                error_log_path = os.path.join(desktop_path, f"eReader_CBZ_Error_{timestamp}.txt")
                
                with open(error_log_path, 'w', encoding='utf-8') as f:
                    f.write("eReader CBZ Manga Converter - Conversion Error Log\n")
                    f.write("=" * 60 + "\n")
                    f.write(f"Time: {datetime.datetime.now()}\n")
                    f.write(f"Platform: {platform.system()}\n")
                    f.write(f"Python: {sys.version}\n")
                    f.write(f"Input file: {input_file}\n")
                    f.write(f"Output directory: {output_directory}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write("Conversion Log:\n")
                    for log_entry in conversion_log:
                        f.write(f"{log_entry}\n")
                    
                    # Add PATH info for debugging
                    f.write("\n" + "=" * 60 + "\n")
                    f.write("Environment Information:\n")
                    f.write(f"PATH: {os.environ.get('PATH', 'Not set')}\n")
                    f.write(f"Current directory: {os.getcwd()}\n")
                    
                    # Add frozen state info
                    f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                    if hasattr(sys, '_MEIPASS'):
                        f.write(f"_MEIPASS: {sys._MEIPASS}\n")
                    f.write(f"Executable: {sys.executable}\n")
                
                # Update status to inform user about error log
                if status_callback:
                    status_callback(f"Error log saved to: {error_log_path}")
                    
                print(f"[ERROR LOG] Conversion error log written to: {error_log_path}")
            except Exception as log_error:
                self.logger.error(f"Failed to write error log: {log_error}")
                if status_callback:
                    status_callback(f"Failed to write error log: {log_error}")

    def _process_epub_structure(self, temp_dir):
        """Process EPUB structure and return ordered HTML files"""
        # Find OPF file path from container.xml
        container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
        opf_path = self._find_opf_path(container_path, temp_dir)

        ordered_html_files = []
        if opf_path:
            ordered_html_files = self._process_opf_file(opf_path, temp_dir)

        # If no HTML files found, get them directly from the EPUB
        if not ordered_html_files:
            ordered_html_files = self._find_html_files_directly(temp_dir)

        return ordered_html_files

    def _find_opf_path(self, container_path, temp_dir):
        """Find OPF file path from container.xml"""
        if not os.path.exists(container_path):
            self.logger.warning("container.xml not found")
            return None

        try:
            container_tree = ET.parse(container_path)
            container_root = container_tree.getroot()

            ns = ''
            if '}' in container_root.tag:
                ns = container_root.tag.split('}')[0] + '}'

            rootfiles = container_root.findall(f".//{ns}rootfile" if ns else ".//rootfile")
            for rootfile in rootfiles:
                if rootfile.get('media-type') == 'application/oebps-package+xml':
                    opf_path = rootfile.get('full-path')
                    if opf_path:
                        full_opf_path = os.path.join(temp_dir, opf_path)
                        if os.path.exists(full_opf_path):
                            return full_opf_path
                        else:
                            self.logger.warning(f"OPF file not found: {full_opf_path}")
        except ET.ParseError as e:
            self.logger.error(f"Invalid XML in container.xml: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing container.xml: {e}")

        return None

    def _process_opf_file(self, opf_path, temp_dir):
        """Process OPF file and return ordered HTML files"""
        ordered_html_files = []
        try:
            opf_content = ET.parse(opf_path)
            opf_root = opf_content.getroot()

            ns = ''
            if '}' in opf_root.tag:
                ns = opf_root.tag.split('}')[0] + '}'

            manifest_items = self._process_manifest(opf_root, ns, opf_path, temp_dir)
            ordered_html_files = self._process_spine(opf_root, ns, manifest_items)

        except ET.ParseError as e:
            self.logger.error(f"Invalid XML in OPF file: {e}")
        except Exception as e:
            self.logger.error(f"Error processing OPF file: {e}")

        return ordered_html_files

    def _create_cbz(self, ordered_images_dir, input_file, output_directory, progress_callback, status_callback, conversion_log=None):
        """Create CBZ file using KCC"""
        ordered_zip_path = None
        if conversion_log is None:
            conversion_log = []
            
        try:
            self.logger.info("Starting CBZ creation process")
            conversion_log.append("Starting CBZ creation process")
            
            # Create output filename
            output_file = os.path.join(
                output_directory,
                os.path.splitext(os.path.basename(input_file))[0] + '.cbz'
            )
            conversion_log.append(f"Output file: {output_file}")

            # Create ZIP file with ordered images
            ordered_zip_path = os.path.join(os.path.dirname(ordered_images_dir), 'ordered_images.zip')
            
            try:
                with zipfile.ZipFile(ordered_zip_path, 'w', zipfile.ZIP_DEFLATED) as ordered_zip:
                    image_files = sorted([
                        f for f in os.listdir(ordered_images_dir)
                        if f.endswith(('.jpg', '.jpeg', '.png'))
                    ])

                    if not image_files:
                        raise ValueError("No image files found to package")

                    total_files = len(image_files)
                    for i, filename in enumerate(image_files, 1):
                        img_path = os.path.join(ordered_images_dir, filename)
                        if not os.path.exists(img_path):
                            self.logger.warning(f"Image file not found: {img_path}")
                            continue
                        ordered_zip.write(img_path, filename)
                        if progress_callback:
                            zip_progress = 40 + (10 * i / total_files)
                            progress_callback(int(zip_progress))

                conversion_log.append(f"Created temporary ZIP with {len(image_files)} images")
                self.logger.info(f"Created temporary ZIP with {len(image_files)} images")
            except Exception as e:
                error_msg = f"Failed to create temporary ZIP: {e}"
                conversion_log.append(f"ERROR: {error_msg}")
                raise RuntimeError(error_msg)

            if status_callback:
                status_callback("Running KCC conversion...")
            if progress_callback:
                progress_callback(50)

            # Set up environment using ResourceManager
            original_cwd = os.getcwd()
            original_path = resource_manager.setup_binary_environment()
            
            try:
                # Switch to KCC working directory using ResourceManager
                kcc_working_dir = resource_manager.get_working_directory()
                
                if not kcc_working_dir.exists():
                    error_msg = f"KCC working directory not found: {kcc_working_dir}"
                    conversion_log.append(f"ERROR: {error_msg}")
                    raise RuntimeError(error_msg)
                
                try:
                    os.chdir(str(kcc_working_dir))
                    conversion_log.append(f"Changed to KCC working directory: {kcc_working_dir}")
                    self.logger.info(f"Changed to KCC working directory: {kcc_working_dir}")
                    
                    # For macOS App Bundle, ensure 7z.so is accessible from current directory
                    if (getattr(sys, 'frozen', False) and 
                        platform.system() == "Darwin" and
                        '.app/Contents/' in sys.executable):  # macOS App Bundle
                        
                        z7_so_source = resource_manager.base_path / "7z.so"
                        z7_so_target = Path.cwd() / "7z.so"
                        
                        # Check alternative source locations if primary not found
                        if not z7_so_source.exists():
                            alt_locations = [
                                resource_manager.base_path.parent / "Frameworks" / "7z.so",
                                resource_manager.resources_path / "7z.so",
                            ]
                            for alt_path in alt_locations:
                                if alt_path.exists():
                                    z7_so_source = alt_path
                                    break
                        
                        # Set up 7z.so in working directory if needed
                        if z7_so_source.exists() and not z7_so_target.exists():
                            try:
                                import shutil
                                shutil.copy2(str(z7_so_source), str(z7_so_target))
                                self.logger.info(f"Copied 7z.so to working directory: {z7_so_target}")
                            except Exception as copy_e:
                                self.logger.warning(f"Failed to copy 7z.so: {copy_e}")
                                # Try creating symlink instead
                                try:
                                    z7_so_target.symlink_to(z7_so_source)
                                    self.logger.info(f"Created 7z.so symlink: {z7_so_target} -> {z7_so_source}")
                                except Exception as link_e:
                                    self.logger.error(f"Failed to create 7z.so symlink: {link_e}")
                        elif z7_so_target.exists():
                            self.logger.debug(f"7z.so already exists in working directory: {z7_so_target}")
                        elif not z7_so_source.exists():
                            self.logger.error(f"7z.so source not found: {z7_so_source}")
                            
                except Exception as e:
                    error_msg = f"Failed to change to KCC directory: {e}"
                    conversion_log.append(f"ERROR: {error_msg}")
                    raise RuntimeError(error_msg)

                # Verify 7z availability before KCC execution
                import subprocess
                z7_cmd = '7z.exe' if platform.system() == "Windows" else '7z'
                
                try:
                    # Test if 7z is available
                    conversion_log.append(f"Testing 7z availability with command: {z7_cmd}")
                    result = subprocess.run([z7_cmd], capture_output=True, timeout=5)
                    conversion_log.append(f"7z tool is available for KCC")
                    self.logger.debug(f"7z tool is available for KCC")
                except FileNotFoundError:
                    conversion_log.append(f"WARNING: 7z not found in PATH, attempting to locate it")
                    self.logger.warning(f"7z not found in PATH, attempting to locate it")
                    # 7z not found in PATH, try to locate it
                    z7_path = resource_manager.get_binary_path('7z')
                    if z7_path and z7_path.exists():
                        # Add the directory containing 7z to PATH
                        z7_dir = str(z7_path.parent)
                        current_path = os.environ.get('PATH', '')
                        # Use os.pathsep for cross-platform compatibility
                        os.environ['PATH'] = f"{z7_dir}{os.pathsep}{current_path}"
                        conversion_log.append(f"Added 7z directory to PATH: {z7_dir}")
                        self.logger.info(f"Added 7z directory to PATH: {z7_dir}")
                        
                        # Test again with proper command
                        z7_test_cmd = z7_path.name if z7_path.name.endswith('.exe') else z7_cmd
                        try:
                            result = subprocess.run([z7_test_cmd], capture_output=True, timeout=5)
                            conversion_log.append(f"7z tool is now available after PATH update")
                            self.logger.debug(f"7z tool is now available after PATH update")
                        except FileNotFoundError:
                            error_msg = f"7z still not found after PATH update"
                            conversion_log.append(f"ERROR: {error_msg}")
                            self.logger.error(error_msg)
                    else:
                        error_msg = f"7z binary not found in bundle"
                        conversion_log.append(f"ERROR: {error_msg}")
                        self.logger.error(error_msg)
                except subprocess.TimeoutExpired:
                    conversion_log.append(f"7z tool is available (timeout during help display is normal)")
                    self.logger.debug(f"7z tool is available (timeout during help display is normal)")
                except Exception as e:
                    error_msg = f"Error testing 7z availability: {e}"
                    conversion_log.append(f"ERROR: {error_msg}")
                    self.logger.error(error_msg)

                # Run KCC conversion
                kcc_args = [
                    '-p', 'KoC',
                    '-f', 'CBZ',
                    '--hq',
                    '-mu',
                    '--cropping', '1',
                    '--croppingpower', '1',
                    '--gamma', '1.6',
                    ordered_zip_path,
                    '-o', output_file
                ]

                try:
                    from kindlecomicconverter.comic2ebook import main as kcc_main
                    conversion_log.append("KCC module imported successfully")
                except ImportError as e:
                    error_msg = f"KCC module not found: {e}"
                    conversion_log.append(f"ERROR: {error_msg}")
                    raise RuntimeError(error_msg)

                conversion_log.append("Starting KCC conversion...")
                self.logger.info("Starting KCC conversion...")
                import time
                start_time = time.time()
                
                # Capture KCC stdout/stderr
                captured_stdout = io.StringIO()
                captured_stderr = io.StringIO()
                
                # Save original stdout/stderr
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                
                try:
                    # Redirect stdout/stderr to capture KCC output
                    sys.stdout = captured_stdout
                    sys.stderr = captured_stderr
                    
                    try:
                        kcc_result = kcc_main(kcc_args)
                        success = kcc_result == 0
                        conversion_log.append(f"KCC main returned: {kcc_result}")
                        self.logger.debug(f"KCC main returned: {kcc_result}")
                    except SystemExit as e:
                        success = e.code == 0
                        conversion_log.append(f"KCC exited with code: {e.code}")
                        self.logger.debug(f"KCC exited with code: {e.code}")
                    except Exception as e:
                        error_msg = f"KCC execution error: {e}"
                        conversion_log.append(f"ERROR: {error_msg}")
                        self.logger.error(error_msg)
                        success = False
                        
                        # Log subprocess errors for debugging
                        if hasattr(e, 'cmd') and hasattr(e, 'returncode'):
                            conversion_log.append(f"Command that failed: {e.cmd}")
                            conversion_log.append(f"Return code: {e.returncode}")
                            self.logger.error(f"Command that failed: {e.cmd}")
                            self.logger.error(f"Return code: {e.returncode}")
                            if hasattr(e, 'stderr') and e.stderr:
                                conversion_log.append(f"Process stderr: {e.stderr}")
                                self.logger.error(f"Process stderr: {e.stderr}")
                            if hasattr(e, 'stdout') and e.stdout:
                                conversion_log.append(f"Process stdout: {e.stdout}")
                                self.logger.error(f"Process stdout: {e.stdout}")
                
                finally:
                    # Restore stdout/stderr
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    execution_time = time.time() - start_time
                    conversion_log.append(f"KCC completed in {execution_time:.2f}s")
                    self.logger.info(f"KCC completed in {execution_time:.2f}s")
                    
                    # Log captured output for debugging
                    stdout_content = captured_stdout.getvalue()
                    stderr_content = captured_stderr.getvalue()
                    
                    if stdout_content:
                        self.logger.debug("KCC stdout:")
                        conversion_log.append("KCC stdout:")
                        for line in stdout_content.strip().split('\n')[:10]:  # Limit to first 10 lines
                            if line.strip():
                                self.logger.debug(f"  {line}")
                                conversion_log.append(f"  {line}")
                    
                    if stderr_content and not success:
                        self.logger.error("KCC stderr:")
                        conversion_log.append("KCC stderr:")
                        for line in stderr_content.strip().split('\n')[:10]:  # Limit to first 10 lines
                            if line.strip():
                                self.logger.error(f"  {line}")
                                conversion_log.append(f"  {line}")

            finally:
                # Restore environment using ResourceManager
                try:
                    os.chdir(original_cwd)
                    resource_manager.restore_environment(original_path)
                except Exception as e:
                    self.logger.warning(f"Failed to restore environment: {e}")

            # Verify output file was created
            if os.path.exists(output_file):
                output_size = os.path.getsize(output_file)
                conversion_log.append(f"CBZ file created successfully: {output_size} bytes")
                self.logger.info(f"CBZ file created successfully: {output_size} bytes")
            else:
                conversion_log.append(f"ERROR: CBZ file was not created: {output_file}")
                self.logger.error(f"CBZ file was not created: {output_file}")
                success = False

            return success

        except Exception as e:
            error_msg = f"Error creating CBZ: {str(e)}"
            conversion_log.append(f"ERROR: {error_msg}")
            self.logger.error(error_msg)
            return False
        finally:
            # Clean up temporary zip file
            if ordered_zip_path and os.path.exists(ordered_zip_path):
                try:
                    os.remove(ordered_zip_path)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary ZIP: {e}")

    def _process_manifest(self, opf_root, ns, opf_path, temp_dir):
        """Process manifest section of OPF file"""
        manifest_items = {}
        manifest = opf_root.find(f".//{ns}manifest" if ns else ".//manifest")
        if manifest is not None:
            for item in manifest.findall(f"{ns}item" if ns else "item"):
                item_id = item.get('id')
                item_href = item.get('href')

                if item_href:
                    # Convert relative path to absolute path
                    full_path = os.path.normpath(os.path.join(os.path.dirname(opf_path), item_href))
                    manifest_items[item_id] = os.path.relpath(full_path, temp_dir)

        return manifest_items

    def _process_spine(self, opf_root, ns, manifest_items):
        """Process spine section of OPF file"""
        ordered_html_files = []
        spine = opf_root.find(f".//{ns}spine" if ns else ".//spine")
        if spine is not None:
            for itemref in spine.findall(f"{ns}itemref" if ns else "itemref"):
                idref = itemref.get('idref')
                if idref in manifest_items:
                    href = manifest_items[idref]
                    if href.endswith('.html') or href.endswith('.xhtml'):
                        if href not in ordered_html_files:
                            ordered_html_files.append(href)

        return ordered_html_files

    def _find_html_files_directly(self, temp_dir):
        """Find HTML files directly in the EPUB structure"""
        ordered_html_files = []
        html_dir = os.path.join(temp_dir, 'html')

        if os.path.exists(html_dir):
            for file in os.listdir(html_dir):
                if file.endswith('.html') and not file.startswith('tpl_') and file != 'createby.html':
                    ordered_html_files.append(os.path.join('html', file))

            # Sort HTML files by page number if possible
            ordered_html_files.sort(key=lambda x: int(re.search(r'page-(\d+)', x).group(1)) if re.search(r'page-(\d+)', x) else float('inf'))

        return ordered_html_files

    def _extract_images(self, temp_dir, ordered_html_files):
        """Extract and order images from HTML files"""
        ordered_images_dir = os.path.join(temp_dir, 'ordered_images')
        
        try:
            os.makedirs(ordered_images_dir, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create images directory: {e}")

        image_count = 1
        processed_images = {}
        total_images_processed = 0

        for html_file in ordered_html_files:
            html_path = os.path.join(temp_dir, html_file)
            if not os.path.exists(html_path):
                self.logger.warning(f"HTML file not found: {html_file}")
                continue
                
            try:
                html_content = ET.parse(html_path)
                html_root = html_content.getroot()

                ns = ''
                if '}' in html_root.tag:
                    ns = html_root.tag.split('}')[0] + '}'

                img_nodes = html_root.findall(f".//{ns}img" if ns else ".//img")
                for img in img_nodes:
                    img_src = img.get('src', '')
                    if not img_src:
                        continue
                        
                    if img_src.startswith('../'):
                        img_src = img_src[3:]

                    # Convert image path to absolute path
                    full_img_path = os.path.join(os.path.dirname(html_path), img_src)
                    if not os.path.exists(full_img_path):
                        full_img_path = os.path.join(temp_dir, img_src)

                    if os.path.exists(full_img_path) and img_src not in processed_images:
                        try:
                            # Special handling for cover and creator images
                            if 'cover' in img_src.lower():
                                new_name = "0000_cover"
                                ext = os.path.splitext(img_src)[1]
                                new_filename = f"{new_name}{ext}"
                            elif 'createby' in img_src.lower():
                                new_name = f"{image_count+9999:04d}_createby"
                                ext = os.path.splitext(img_src)[1]
                                new_filename = f"{new_name}{ext}"
                            else:
                                new_name = f"{image_count:04d}"
                                ext = os.path.splitext(img_src)[1]
                                new_filename = f"{new_name}{ext}"
                                image_count += 1

                            new_path = os.path.join(ordered_images_dir, new_filename)
                            shutil.copy2(full_img_path, new_path)
                            processed_images[img_src] = new_filename
                            total_images_processed += 1
                        except Exception as e:
                            self.logger.warning(f"Failed to copy image {img_src}: {e}")
                            continue
                    elif not os.path.exists(full_img_path):
                        self.logger.warning(f"Image file not found: {img_src}")

            except ET.ParseError as e:
                self.logger.error(f"Invalid XML in HTML file {html_file}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Error processing HTML file {html_file}: {e}")
                continue

        if total_images_processed == 0:
            raise ValueError("No images were successfully extracted from EPUB")
            
        self.logger.info(f"Successfully extracted {total_images_processed} images")
        return ordered_images_dir
