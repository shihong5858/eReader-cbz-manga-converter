# eReader CBZ 漫画转换器

**中文说明** | [English](README.md)

将 EPUB/MOBI 漫画文件转换为 CBZ 格式，专为墨水屏阅读器（特别是Kobo设备）优化。

## 核心功能

- **格式转换**：将EPUB/MOBI格式漫画转换为CBZ格式，为墨水屏阅读器优化漫画阅读体验
- **修复乱序页面**：解决部分漫画转换cbz后页码顺序混乱的问题（如moe系网站epub用Calibre转换）
- **KCC 增强**：使用 Kindle Comic Converter (KCC) 进行图像增强和墨水屏阅读器分辨率适配
- **跨平台**：支持 Windows、macOS 和 Linux，支持图形界面和命令行模式

## 下载与安装

### 普通用户
从 [GitHub Releases](https://github.com/shihong5858/eReader-cbz-manga-converter/releases) 下载最新的二进制版本 - 无需安装，直接运行可执行文件即可。

### 开发者
```bash
git clone https://github.com/shihong5858/eReader-cbz-manga-converter.git
cd eReader-cbz-manga-converter
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
python build.py dev
```

## 使用方法

### 图形界面模式（推荐）
1. **输入**：点击"Browse"按钮或将 EPUB/MOBI 文件拖拽到输入区域（支持多个文件）
2. **输出**：系统会自动将输入文件所在目录设为输出目录，也可以自行指定其他目录
3. **设备**：从下拉菜单中选择您的墨水屏阅读器设备（如 Kobo Clara HD、Kindle 等常见设备）
4. **转换**：点击"Convert"按钮开始转换过程，进度条会显示总体进度

### 命令行模式
```bash
python main.py input.epub output_directory
```

### 构建可执行文件
```bash
python build.py build
```

## 开发指南

### 参与贡献
如果您想帮助开发：

1. **Fork 并克隆**仓库
2. **设置环境**：`python build.py dev`
3. **运行测试**：`python build.py check`
4. **修改代码**并彻底测试
5. **提交 PR** 并提供清晰的描述

### 项目结构
```
├── main.py              # 应用程序入口
├── build.py             # 构建和开发脚本
├── components/          # 核心转换逻辑
│   └── conversion/      # EPUB/MOBI 转换器
├── gui/                 # PySide6 图形界面
├── kcc/                 # KCC 库集成
└── config/              # 配置文件
```

### 开发命令
```bash
python build.py dev      # 安装开发依赖
python build.py run      # 从源码运行
python build.py check    # 代码质量检查
python build.py clean    # 清理构建产物
python build.py build    # 构建可执行文件
```

## KCC 集成

本项目使用 Python 实现 EPUB/MOBI 到 CBZ 的格式转换，并集成 [KindleComicConverter (KCC)](https://github.com/ciromattia/kcc) 进行图像优化和墨水屏阅读器设备适配。因此在开发中需要集成 KCC 代码。

### 设置
```bash
git submodule update --init --recursive
python build.py kcc
```

### 更新 KCC
```bash
cd kcc && git pull origin master && cd ..
git add kcc && git commit -m "Update KCC"
``` 

## 系统要求
- Python 3.8+
- 依赖项通过 pyproject.toml 自动管理

## 问题反馈与建议

如果您遇到任何bug或有改进建议，请在 [GitHub Issues](https://github.com/shihong5858/eReader-cbz-manga-converter/issues) 中报告。

## 许可证
MIT License
