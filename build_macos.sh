#!/bin/bash

# 启用错误检查
set -e

# 输出执行的命令
set -x

# 清理之前的构建
echo "正在清理之前的构建..."
rm -rf build dist

# 确保 Python 环境正确
echo "检查 Python 环境..."
which python
python --version

# 创建新的虚拟环境
echo "创建虚拟环境..."
python -m venv venv
source venv/bin/activate

# 升级 pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt
pip install py2app

# 确保所有必需的文件都存在
echo "检查必需文件..."
if [ ! -f "main.py" ]; then
    echo "错误: main.py 不存在"
    exit 1
fi

if [ ! -f "device_info.json" ]; then
    echo "错误: device_info.json 不存在"
    exit 1
fi

# 构建应用
echo "开始构建应用..."
python setup.py py2app -A

echo "构建完成！应用程序在 dist 文件夹中。" 