import io
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Import ResourceManager
from ..resource_manager import get_resource_manager
from ..logger_config import get_logger

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
        try:
            self.logger.info(f"Starting conversion: {os.path.basename(input_file)}")
            
            if status_callback:
                status_callback("Starting conversion")
            if progress_callback:
                progress_callback(0)

            # Validate input file
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Input file not found: {input_file}")
            if not input_file.lower().endswith('.epub'):
                raise ValueError(f"Invalid input file format: {input_file}")

            # Validate output directory
            if not os.path.exists(output_directory):
                try:
                    os.makedirs(output_directory, exist_ok=True)
                    self.logger.info(f"Created output directory: {output_directory}")
                except Exception as e:
                    raise PermissionError(f"Cannot create output directory: {e}")

            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()
            self.logger.info(f"Created temporary directory: {temp_dir}")

            if status_callback:
                status_callback("Processing EPUB file")
            if progress_callback:
                progress_callback(5)

            # Extract EPUB contents
            try:
                with zipfile.ZipFile(input_file, 'r') as epub:
                    epub.extractall(temp_dir)
                self.logger.info("Successfully extracted EPUB contents")
            except zipfile.BadZipFile as e:
                raise ValueError(f"Invalid EPUB file: {e}")
            except Exception as e:
                raise RuntimeError(f"Failed to extract EPUB: {e}")

            if status_callback:
                status_callback("Extracting images")
            if progress_callback:
                progress_callback(10)

            # Process EPUB structure
            try:
                ordered_html_files = self._process_epub_structure(temp_dir)
                if not ordered_html_files:
                    self.logger.warning("No HTML files found in EPUB")
            except Exception as e:
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
                    raise ValueError("No images found in EPUB file")
                self.logger.info(f"Extracted {image_count} images")
            except Exception as e:
                raise RuntimeError(f"Failed to extract images: {e}")

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
                status_callback
            )

            if success:
                self.logger.info(f"Conversion completed successfully: {os.path.basename(input_file)}")
                if status_callback:
                    status_callback("Completed")
                if progress_callback:
                    progress_callback(100)
            else:
                self.logger.error(f"Conversion failed: {os.path.basename(input_file)}")

            return success

        except Exception as e:
            self.logger.error(f"Conversion failed for {os.path.basename(input_file)}: {str(e)}")
            if status_callback:
                status_callback(f"Error: {str(e)}")
            return False
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary directory: {e}")

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

    def _create_cbz(self, ordered_images_dir, input_file, output_directory, progress_callback, status_callback):
        """Create CBZ file using KCC"""
        ordered_zip_path = None
        try:
            self.logger.info("Starting CBZ creation process")
            
            # Create output filename
            output_file = os.path.join(
                output_directory,
                os.path.splitext(os.path.basename(input_file))[0] + '.cbz'
            )

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

                self.logger.info(f"Created temporary ZIP with {len(image_files)} images")
            except Exception as e:
                raise RuntimeError(f"Failed to create temporary ZIP: {e}")

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
                    raise RuntimeError(f"KCC working directory not found: {kcc_working_dir}")
                
                try:
                    os.chdir(str(kcc_working_dir))
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
                    raise RuntimeError(f"Failed to change to KCC directory: {e}")

                # Verify 7z availability before KCC execution
                import subprocess
                z7_cmd = '7z.exe' if platform.system() == "Windows" else '7z'
                
                try:
                    # Test if 7z is available
                    result = subprocess.run([z7_cmd], capture_output=True, timeout=5)
                    self.logger.debug(f"7z tool is available for KCC")
                except FileNotFoundError:
                    self.logger.warning(f"7z not found in PATH, attempting to locate it")
                    # 7z not found in PATH, try to locate it
                    z7_path = resource_manager.get_binary_path('7z')
                    if z7_path and z7_path.exists():
                        # Add the directory containing 7z to PATH
                        z7_dir = str(z7_path.parent)
                        current_path = os.environ.get('PATH', '')
                        path_sep = ';' if platform.system() == "Windows" else ':'
                        os.environ['PATH'] = f"{z7_dir}{path_sep}{current_path}"
                        self.logger.info(f"Added 7z directory to PATH: {z7_dir}")
                        
                        # Test again with proper command
                        z7_test_cmd = z7_path.name if z7_path.name.endswith('.exe') else z7_cmd
                        try:
                            result = subprocess.run([z7_test_cmd], capture_output=True, timeout=5)
                            self.logger.debug(f"7z tool is now available after PATH update")
                        except FileNotFoundError:
                            self.logger.error(f"7z still not found after PATH update")
                    else:
                        self.logger.error(f"7z binary not found in bundle")
                except subprocess.TimeoutExpired:
                    self.logger.debug(f"7z tool is available (timeout during help display is normal)")
                except Exception as e:
                    self.logger.error(f"Error testing 7z availability: {e}")

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
                    from kindlecomicconverter.comic2ebook import main as kcc_main  # type: ignore
                except ImportError as e:
                    raise RuntimeError(f"KCC module not found: {e}")

                self.logger.info("Starting KCC conversion...")
                start_time = time.time()
                
                # Windows-specific: Add retry logic and better temp file handling
                if platform.system() == "Windows":
                    import tempfile
                    import atexit
                    import gc
                    
                    # Force garbage collection to free any file handles
                    gc.collect()
                    
                    # Set more permissive umask for temp files on Windows
                    old_umask = None
                    try:
                        import stat
                        old_umask = os.umask(0)
                        os.umask(stat.S_IWGRP | stat.S_IWOTH)
                    except (AttributeError, OSError):
                        # umask not available on Windows, that's fine
                        pass
                    
                    # Set temp directory with proper permissions
                    original_temp = tempfile.gettempdir()
                    try:
                        # Ensure temp directory is writable
                        temp_test = tempfile.mkdtemp(prefix='KCC_test_')
                        os.rmdir(temp_test)
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Temp directory permission issue: {e}")
                
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
                    
                    # Retry logic for Windows permission issues
                    max_retries = 3 if platform.system() == "Windows" else 1
                    retry_delay = 1.0  # seconds
                    
                    for attempt in range(max_retries):
                        try:
                            kcc_result = kcc_main(kcc_args)
                            success = kcc_result == 0
                            self.logger.debug(f"KCC main returned: {kcc_result}")
                            break  # Success, exit retry loop
                        except SystemExit as e:
                            success = e.code == 0
                            self.logger.debug(f"KCC exited with code: {e.code}")
                            break  # SystemExit is final, don't retry
                        except (OSError, PermissionError) as e:
                            if attempt < max_retries - 1:
                                self.logger.warning(f"KCC permission error (attempt {attempt + 1}/{max_retries}): {e}")
                                self.logger.info(f"Retrying in {retry_delay} seconds...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                
                                # Force cleanup and garbage collection between retries
                                if platform.system() == "Windows":
                                    import gc
                                    gc.collect()
                                continue
                            else:
                                self.logger.error(f"KCC execution failed after {max_retries} attempts: {e}")
                                success = False
                                break
                        except Exception as e:
                            self.logger.error(f"KCC execution error: {e}")
                            success = False
                            
                            # Log subprocess errors for debugging if available
                            cmd = getattr(e, 'cmd', None)
                            if cmd:
                                self.logger.error(f"Command that failed: {cmd}")
                            returncode = getattr(e, 'returncode', None)
                            if returncode is not None:
                                self.logger.error(f"Return code: {returncode}")
                            stderr = getattr(e, 'stderr', None)
                            if stderr:
                                self.logger.error(f"Process stderr: {stderr}")
                            stdout = getattr(e, 'stdout', None)
                            if stdout:
                                self.logger.error(f"Process stdout: {stdout}")
                            break  # Don't retry on unexpected errors
                
                finally:
                    # Restore stdout/stderr
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    # Restore Windows umask if it was changed
                    if platform.system() == "Windows" and 'old_umask' in locals() and old_umask is not None:
                        try:
                            os.umask(old_umask)
                        except (AttributeError, OSError):
                            pass
                    
                    execution_time = time.time() - start_time
                    self.logger.info(f"KCC completed in {execution_time:.2f}s")
                    
                                                        # Log captured output for debugging
                    stdout_content = captured_stdout.getvalue()
                    stderr_content = captured_stderr.getvalue()
                    
                    if stdout_content:
                        self.logger.debug("KCC stdout:")
                        for line in stdout_content.strip().split('\n')[:10]:  # Limit to first 10 lines
                            if line.strip():
                                self.logger.debug(f"  {line}")
                    
                    if stderr_content and not success:
                        self.logger.error("KCC stderr:")
                        for line in stderr_content.strip().split('\n')[:10]:  # Limit to first 10 lines
                            if line.strip():
                                self.logger.error(f"  {line}")

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
                self.logger.info(f"CBZ file created successfully: {output_size} bytes")
            else:
                self.logger.error(f"CBZ file was not created: {output_file}")
                success = False

            return success

        except Exception as e:
            self.logger.error(f"Error creating CBZ: {str(e)}")
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
            def extract_page_number(filename):
                match = re.search(r'page-(\d+)', filename)
                return int(match.group(1)) if match else float('inf')
            ordered_html_files.sort(key=extract_page_number)

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
                        
                    # Convert image path to absolute path
                    full_img_path = os.path.normpath(os.path.join(os.path.dirname(html_path), img_src))
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
