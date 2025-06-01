#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地跨平台构建脚本
用法: python build_cross_platform.py
"""

import os
import sys
import platform
import subprocess

def check_pyinstaller():
    """检查PyInstaller是否安装"""
    try:
        subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True)
        print("✅ PyInstaller 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ PyInstaller 未安装")
        print("请运行: pip install pyinstaller")
        return False

def build_for_platform():
    """为当前平台构建"""
    if not check_pyinstaller():
        return False
        
    platform_name = platform.system().lower()
    arch = platform.machine()
    
    print(f"🚀 开始为 {platform_name} ({arch}) 构建...")
    
    # 基础PyInstaller命令
    cmd = [
        'pyinstaller',
        '--onedir',  # 创建目录而不是单文件
        '--windowed',  # 无控制台窗口
        '--name', f'eReader-CBZ-Manga-Converter-{platform_name}-{arch}',
        '--add-data', 'components:components' if platform_name != 'windows' else 'components;components',
        '--add-data', 'gui:gui' if platform_name != 'windows' else 'gui;gui',
    ]
    
    # 添加图标
    if os.path.exists('app.icns'):
        cmd.extend(['--icon', 'app.icns'])
    
    # 添加主文件
    cmd.append('main.py')
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ 构建成功!")
        print(f"📁 输出目录: dist/")
        
        # 显示生成的文件
        dist_dir = 'dist'
        if os.path.exists(dist_dir):
            print("\n📄 生成的文件:")
            for item in os.listdir(dist_dir):
                item_path = os.path.join(dist_dir, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}/")
                else:
                    size = os.path.getsize(item_path) / (1024*1024)  # MB
                    print(f"  📄 {item} ({size:.1f}MB)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False

def main():
    print("🔨 eReader CBZ Manga Converter - 跨平台构建工具")
    print("=" * 50)
    
    # 显示当前环境信息
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python版本: {sys.version.split()[0]}")
    print()
    
    # 检查必要文件
    required_files = ['main.py', 'requirements.txt']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
        return
    
    # 开始构建
    success = build_for_platform()
    
    if success:
        print("\n🎉 构建完成!")
        print("💡 提示:")
        print("  - 在 dist/ 目录中找到构建的应用")
        print("  - 可以分发给同平台的用户使用")
        print("  - 要构建其他平台版本，请使用 GitHub Actions")
    else:
        print("\n💥 构建失败，请检查错误信息")

if __name__ == '__main__':
    main() 