import os
import sys
import zipfile
import tempfile
import shutil
import logging
import re
import html.parser
from pathlib import Path
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import QApplication
from gui.mainwindow import MainWindow

# Add KCC directory to Python path
kcc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kcc')
sys.path.append(kcc_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_paths = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for name, value in attrs:
                if name == 'src':
                    self.image_paths.append(value)

def process_with_kcc(input_file, output_dir, progress_callback=None, status_callback=None):
    try:
        if status_callback:
            status_callback("Processing EPUB file...")
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Extract EPUB contents
        with zipfile.ZipFile(input_file, 'r') as epub:
            epub.extractall(temp_dir)
        logging.info(f"Extracted EPUB contents to {temp_dir}")
        
        # Find OPF file path from container.xml
        container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
        opf_path = None
        
        if os.path.exists(container_path):
            try:
                container_tree = ET.parse(container_path)
                container_root = container_tree.getroot()
                
                # 获取命名空间
                ns = ''
                if '}' in container_root.tag:
                    ns = container_root.tag.split('}')[0] + '}'
                
                # 查找 rootfile 元素
                rootfiles = container_root.findall(f".//{ns}rootfile" if ns else ".//rootfile")
                for rootfile in rootfiles:
                    if rootfile.get('media-type') == 'application/oebps-package+xml':
                        opf_path = rootfile.get('full-path')
                        break
                
                if opf_path:
                    opf_path = os.path.join(temp_dir, opf_path)
                    logging.info(f"Found OPF file from container.xml: {opf_path}")
            except Exception as e:
                logging.error(f"Error parsing container.xml: {str(e)}")

        ordered_html_files = []
        spine_items = {}  # 用于存储 spine 中的顺序信息
        ncx_path = None  # 存储 NCX 文件路径

        # 从找到的 OPF 文件获取页面顺序
        if opf_path and os.path.exists(opf_path):
            try:
                opf_content = ET.parse(opf_path)
                opf_root = opf_content.getroot()
                
                # 获取命名空间
                ns = ''
                if '}' in opf_root.tag:
                    ns = opf_root.tag.split('}')[0] + '}'
                logging.info(f"Found XML namespace in OPF: {ns[1:-1] if ns else 'None'}")
                
                # 获取 OPF 文件所在目录，用于解析相对路径
                opf_dir = os.path.dirname(opf_path)
                
                # 首先从 manifest 获取所有项目的映射
                manifest_items = {}
                manifest = opf_root.find(f".//{ns}manifest" if ns else ".//manifest")
                if manifest is not None:
                    for item in manifest.findall(f"{ns}item" if ns else "item"):
                        item_id = item.get('id')
                        item_href = item.get('href')
                        media_type = item.get('media-type')
                        
                        if item_href:
                            # 将相对路径转换为绝对路径
                            full_path = os.path.normpath(os.path.join(opf_dir, item_href))
                            manifest_items[item_id] = os.path.relpath(full_path, temp_dir)
                            
                            # 检查是否是 NCX 文件
                            if media_type == 'application/x-dtbncx+xml':
                                ncx_path = full_path
                                logging.info(f"Found NCX file from OPF manifest: {ncx_path}")
                
                # 然后从 spine 获取阅读顺序
                spine = opf_root.find(f".//{ns}spine" if ns else ".//spine")
                if spine is not None:
                    for idx, itemref in enumerate(spine.findall(f"{ns}itemref" if ns else "itemref")):
                        idref = itemref.get('idref')
                        if idref in manifest_items:
                            href = manifest_items[idref]
                            if href.endswith('.html') or href.endswith('.xhtml'):
                                spine_items[href] = idx
                                if href not in ordered_html_files:
                                    ordered_html_files.append(href)
                                    logging.info(f"Found HTML file from OPF spine: {href}")
            except Exception as e:
                logging.error(f"Error parsing OPF file: {str(e)}")

        # 如果 spine 中没有找到页面顺序，尝试从 NCX 获取
        if not ordered_html_files and ncx_path and os.path.exists(ncx_path):
            try:
                ncx_content = ET.parse(ncx_path)
                ncx_root = ncx_content.getroot()
                
                ns = ''
                if '}' in ncx_root.tag:
                    ns = ncx_root.tag.split('}')[0] + '}'
                logging.info(f"Found XML namespace in NCX: {ns[1:-1] if ns else 'None'}")
                
                content_nodes = ncx_root.findall(f".//{ns}content" if ns else ".//content")
                for content in content_nodes:
                    src = content.get('src', '')
                    if src.startswith('../'):
                        src = src[3:]
                    # 将相对路径转换为绝对路径
                    full_path = os.path.normpath(os.path.join(os.path.dirname(ncx_path), src))
                    href = os.path.relpath(full_path, temp_dir)
                    if href not in ordered_html_files:
                        ordered_html_files.append(href)
                        logging.info(f"Found HTML file from NCX: {href}")
            except Exception as e:
                logging.error(f"Error parsing NCX file: {str(e)}")

        # If no HTML files found in OPF or NCX, get them directly from the EPUB
        if not ordered_html_files:
            for root, _, files in os.walk(os.path.join(temp_dir, 'html')):
                for file in files:
                    if file.endswith('.html') and not file.startswith('tpl_') and file != 'createby.html':
                        ordered_html_files.append(os.path.join('html', file))
            # Sort HTML files by page number if possible
            ordered_html_files.sort(key=lambda x: int(re.search(r'page-(\d+)', x).group(1)) if re.search(r'page-(\d+)', x) else float('inf'))

        logging.info(f"Found HTML files: {ordered_html_files}")
        
        # Create directory for ordered images
        ordered_images_dir = os.path.join(temp_dir, 'ordered_images')
        os.makedirs(ordered_images_dir, exist_ok=True)
        
        # Process HTML files and extract images
        image_count = 1
        processed_images = {}  # 使用字典来跟踪处理过的图片，保持顺序
        
        for html_file in ordered_html_files:
            html_path = os.path.join(temp_dir, html_file)
            if os.path.exists(html_path):
                try:
                    html_content = ET.parse(html_path)
                    html_root = html_content.getroot()
                    
                    ns = ''
                    if '}' in html_root.tag:
                        ns = html_root.tag.split('}')[0] + '}'
                    logging.info(f"Found XML namespace in HTML: {ns[1:-1] if ns else 'None'}")
                    
                    img_nodes = html_root.findall(f".//{ns}img" if ns else ".//img")
                    for img in img_nodes:
                        img_src = img.get('src', '')
                        if img_src.startswith('../'):
                            img_src = img_src[3:]
                        
                        # 将图片路径转换为绝对路径
                        full_img_path = os.path.join(os.path.dirname(html_path), img_src)
                        if not os.path.exists(full_img_path):
                            full_img_path = os.path.join(temp_dir, img_src)
                        
                        if os.path.exists(full_img_path) and img_src not in processed_images:
                            # 特殊处理封面和创建者图片
                            if 'cover' in img_src.lower():
                                new_name = "0000_cover"  # 确保封面是第一个文件
                                ext = os.path.splitext(img_src)[1]
                                new_filename = f"{new_name}{ext}"
                                new_path = os.path.join(ordered_images_dir, new_filename)
                                shutil.copy2(full_img_path, new_path)
                                processed_images[img_src] = new_filename
                                logging.info(f"Copied cover image to: {new_path}")
                            elif 'createby' in img_src.lower():
                                new_name = f"{image_count+9999:04d}_createby"  # 确保创建者图片是最后一个文件
                                ext = os.path.splitext(img_src)[1]
                                new_filename = f"{new_name}{ext}"
                                new_path = os.path.join(ordered_images_dir, new_filename)
                                shutil.copy2(full_img_path, new_path)
                                processed_images[img_src] = new_filename
                                logging.info(f"Copied createby image to: {new_path}")
                            else:
                                new_name = f"{image_count:04d}"
                                ext = os.path.splitext(img_src)[1]
                                new_filename = f"{new_name}{ext}"
                                new_path = os.path.join(ordered_images_dir, new_filename)
                                shutil.copy2(full_img_path, new_path)
                                processed_images[img_src] = new_filename
                                logging.info(f"Copied image to: {new_path}")
                                image_count += 1
                except Exception as e:
                    logging.error(f"Error processing HTML file {html_file}: {str(e)}")
                    continue
        
        logging.info(f"Total images processed: {len(processed_images)}")
        
        # Create a new ZIP file with ordered images
        ordered_zip_path = os.path.join(temp_dir, 'ordered_images.zip')
        with zipfile.ZipFile(ordered_zip_path, 'w', zipfile.ZIP_DEFLATED) as ordered_zip:
            # 获取所有图片文件并按名称排序
            image_files = []
            for filename in os.listdir(ordered_images_dir):
                if filename.endswith(('.jpg', '.jpeg', '.png')):
                    image_files.append(filename)
            
            # 按文件名排序，这样会自动按照我们的命名规则排序
            # 0000_cover.jpg 会在最前面
            # 0001.jpg, 0002.jpg 等正常页面在中间
            # 9999_createby.jpg 会在最后
            image_files.sort()
            
            # 按顺序添加所有图片，保持文件名不变以维持顺序
            for filename in image_files:
                img_path = os.path.join(ordered_images_dir, filename)
                ordered_zip.write(img_path, filename)
                logging.info(f"Added to zip: {filename}")
        
        logging.info(f"Created ordered zip file: {ordered_zip_path}")
        
        if progress_callback:
            progress_callback(50)
        
        # Run KCC on the ordered ZIP file
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + '.cbz')
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
        
        if status_callback:
            status_callback("Running KCC conversion...")
        
        logging.info(f"Running KCC with args: {kcc_args}")
        from kindlecomicconverter.comic2ebook import main as kcc_main
        success = kcc_main(kcc_args) == 0
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        if progress_callback:
            progress_callback(100)
        
        if not success:
            logging.error(f"Error: Failed to convert {os.path.basename(input_file)}")
        
        logging.info(f"Conversion completed: {success}")
        return success
        
    except Exception as e:
        logging.error(f"Error in process_with_kcc: {str(e)}")
        return False

def main():
    # 检查是否有命令行参数
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
        
        success = process_with_kcc(input_file, output_dir)
        return 0 if success else 1
    else:
        # 启动 GUI
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 