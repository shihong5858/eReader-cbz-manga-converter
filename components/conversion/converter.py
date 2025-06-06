import io
import logging
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Import ResourceManager
from ..resource_manager import get_resource_manager

# Initialize ResourceManager
resource_manager = get_resource_manager()

# Add KCC module path using ResourceManager
if not resource_manager.add_kcc_to_path():
    print(f"Warning: KCC path not found at {resource_manager.kcc_path}")

class EPUBConverter:
    """EPUB to CBZ converter with progress tracking"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

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
        try:
            if status_callback:
                status_callback("Starting conversion")
            if progress_callback:
                progress_callback(0)

            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()

            if status_callback:
                status_callback("Processing EPUB file")
            if progress_callback:
                progress_callback(5)

            # Extract EPUB contents
            with zipfile.ZipFile(input_file, 'r') as epub:
                epub.extractall(temp_dir)
            self.logger.info(f"Extracted EPUB contents to {temp_dir}")

            if status_callback:
                status_callback("Extracting images")
            if progress_callback:
                progress_callback(10)

            # Process EPUB structure
            ordered_html_files = self._process_epub_structure(temp_dir)

            if status_callback:
                status_callback("Processing images")
            if progress_callback:
                progress_callback(20)

            # Extract and order images
            ordered_images_dir = self._extract_images(temp_dir, ordered_html_files)

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

            # Clean up
            shutil.rmtree(temp_dir)

            if success:
                if status_callback:
                    status_callback("Completed")
                if progress_callback:
                    progress_callback(100)

            return success

        except Exception as e:
            self.logger.error(f"Error in conversion process: {str(e)}")
            return False

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
                        return os.path.join(temp_dir, opf_path)
        except Exception as e:
            self.logger.error(f"Error parsing container.xml: {str(e)}")

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

        except Exception as e:
            self.logger.error(f"Error processing OPF file: {str(e)}")

        return ordered_html_files

    def _create_cbz(self, ordered_images_dir, input_file, output_directory, progress_callback, status_callback):
        """Create CBZ file using KCC"""
        try:
            self.logger.info("="*50)
            self.logger.info("Starting _create_cbz method")
            
            # Create output filename
            output_file = os.path.join(
                output_directory,
                os.path.splitext(os.path.basename(input_file))[0] + '.cbz'
            )
            self.logger.info(f"Output file: {output_file}")

            # Create ZIP file with ordered images
            ordered_zip_path = os.path.join(os.path.dirname(ordered_images_dir), 'ordered_images.zip')
            self.logger.info(f"Creating temporary ZIP: {ordered_zip_path}")
            
            with zipfile.ZipFile(ordered_zip_path, 'w', zipfile.ZIP_DEFLATED) as ordered_zip:
                image_files = sorted([
                    f for f in os.listdir(ordered_images_dir)
                    if f.endswith(('.jpg', '.jpeg', '.png'))
                ])

                self.logger.info(f"Found {len(image_files)} image files to package")
                total_files = len(image_files)
                for i, filename in enumerate(image_files, 1):
                    img_path = os.path.join(ordered_images_dir, filename)
                    ordered_zip.write(img_path, filename)
                    if progress_callback:
                        zip_progress = 40 + (10 * i / total_files)
                        progress_callback(int(zip_progress))

            self.logger.info(f"ZIP creation completed: {os.path.getsize(ordered_zip_path)} bytes")

            if status_callback:
                status_callback("Running KCC conversion...")
            if progress_callback:
                progress_callback(50)

            self.logger.info("="*30 + " KCC EXECUTION START " + "="*30)
            
            # Set up environment using ResourceManager
            original_cwd = os.getcwd()
            original_path = resource_manager.setup_binary_environment()
            
            self.logger.info(f"Original CWD: {original_cwd}")
            if original_path:
                self.logger.info(f"Environment setup completed")
                
                # Check 7z binary
                z7_path = resource_manager.get_binary_path('7z')
                if z7_path:
                    self.logger.info(f"7z binary found: {z7_path}")
                    self.logger.info(f"7z file size: {z7_path.stat().st_size} bytes")
                    self.logger.info(f"7z executable: {os.access(z7_path, os.X_OK)}")
                else:
                    self.logger.warning("7z binary not found")
            
            try:
                # Switch to KCC working directory using ResourceManager
                kcc_working_dir = resource_manager.get_working_directory()
                
                self.logger.info(f"KCC working directory: {kcc_working_dir}")
                self.logger.info(f"KCC working dir exists: {kcc_working_dir.exists()}")
                
                if kcc_working_dir.exists():
                    os.chdir(str(kcc_working_dir))
                    self.logger.info(f"Changed to KCC working dir: {os.getcwd()}")
                else:
                    self.logger.warning(f"KCC working directory not found, staying in: {os.getcwd()}")

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

                self.logger.info(f"KCC arguments: {kcc_args}")
                self.logger.info("Attempting to import KCC...")
                
                try:
                    from kindlecomicconverter.comic2ebook import main as kcc_main
                    self.logger.info("KCC import successful")
                except ImportError as e:
                    self.logger.error(f"KCC import failed: {e}")
                    self.logger.error(f"Current sys.path: {sys.path}")
                    raise

                # Check if 7z command is available
                self.logger.info("Checking 7z command availability...")
                import subprocess
                try:
                    result = subprocess.run(['which', '7z'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info(f"7z command found at: {result.stdout.strip()}")
                    else:
                        self.logger.warning("7z command not found with 'which'")
                    
                    # Also try running 7z directly
                    result = subprocess.run(['7z'], capture_output=True, text=True, timeout=5)
                    self.logger.info(f"7z test run exit code: {result.returncode}")
                    if result.stdout:
                        self.logger.info(f"7z stdout: {result.stdout[:200]}...")
                    if result.stderr:
                        self.logger.info(f"7z stderr: {result.stderr[:200]}...")
                        
                except Exception as e:
                    self.logger.error(f"Error checking 7z: {e}")

                # Log current environment
                self.logger.info(f"Current PATH: {os.environ.get('PATH', 'NOT_SET')}")
                self.logger.info(f"Current working dir: {os.getcwd()}")
                self.logger.info(f"Input ZIP file: {ordered_zip_path}")
                self.logger.info(f"Input ZIP exists: {os.path.exists(ordered_zip_path)}")
                self.logger.info(f"Output file target: {output_file}")
                self.logger.info(f"Output dir exists: {os.path.exists(os.path.dirname(output_file))}")
                self.logger.info(f"Output dir writable: {os.access(os.path.dirname(output_file), os.W_OK)}")

                self.logger.info("Starting KCC execution...")
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
                    
                    self.logger.info("Executing KCC with redirected output...")
                    
                    try:
                        kcc_result = kcc_main(kcc_args)
                        execution_time = time.time() - start_time
                        self.logger.info(f"KCC completed in {execution_time:.2f}s with result: {kcc_result}")
                        success = kcc_result == 0
                    except SystemExit as e:
                        execution_time = time.time() - start_time
                        self.logger.info(f"KCC SystemExit in {execution_time:.2f}s with code: {e.code}")
                        success = e.code == 0
                    except Exception as e:
                        execution_time = time.time() - start_time
                        self.logger.error(f"KCC exception in {execution_time:.2f}s: {e}")
                        import traceback
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                        success = False
                
                finally:
                    # Restore stdout/stderr
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    # Log captured output
                    stdout_content = captured_stdout.getvalue()
                    stderr_content = captured_stderr.getvalue()
                    
                    if stdout_content:
                        self.logger.info("KCC STDOUT:")
                        for line in stdout_content.strip().split('\n'):
                            if line.strip():
                                self.logger.info(f"  {line}")
                    else:
                        self.logger.info("KCC STDOUT: (empty)")
                    
                    if stderr_content:
                        self.logger.error("KCC STDERR:")
                        for line in stderr_content.strip().split('\n'):
                            if line.strip():
                                self.logger.error(f"  {line}")
                    else:
                        self.logger.info("KCC STDERR: (empty)")

                self.logger.info(f"Final KCC success status: {success}")

            finally:
                # Restore environment using ResourceManager
                self.logger.info("Restoring environment...")
                os.chdir(original_cwd)
                self.logger.info(f"Restored CWD: {os.getcwd()}")
                resource_manager.restore_environment(original_path)
                if original_path:
                    self.logger.info("Restored PATH")

            self.logger.info("="*30 + " KCC EXECUTION END " + "="*30)

            # Clean up temporary zip file
            self.logger.info(f"Cleaning up temporary ZIP: {ordered_zip_path}")
            os.remove(ordered_zip_path)

            # Check if output file was created
            if os.path.exists(output_file):
                output_size = os.path.getsize(output_file)
                self.logger.info(f"Output CBZ created successfully: {output_size} bytes")
            else:
                self.logger.error(f"Output CBZ file not created: {output_file}")

            self.logger.info(f"_create_cbz returning success: {success}")
            return success

        except Exception as e:
            self.logger.error(f"Error in _create_cbz: {str(e)}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

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
        os.makedirs(ordered_images_dir, exist_ok=True)

        image_count = 1
        processed_images = {}
        current_file = 0

        for html_file in ordered_html_files:
            current_file += 1
            html_path = os.path.join(temp_dir, html_file)
            if os.path.exists(html_path):
                try:
                    html_content = ET.parse(html_path)
                    html_root = html_content.getroot()

                    ns = ''
                    if '}' in html_root.tag:
                        ns = html_root.tag.split('}')[0] + '}'

                    img_nodes = html_root.findall(f".//{ns}img" if ns else ".//img")
                    for img in img_nodes:
                        img_src = img.get('src', '')
                        if img_src.startswith('../'):
                            img_src = img_src[3:]

                        # Convert image path to absolute path
                        full_img_path = os.path.join(os.path.dirname(html_path), img_src)
                        if not os.path.exists(full_img_path):
                            full_img_path = os.path.join(temp_dir, img_src)

                        if os.path.exists(full_img_path) and img_src not in processed_images:
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

                except Exception as e:
                    self.logger.error(f"Error processing HTML file {html_file}: {str(e)}")
                    continue

        return ordered_images_dir
