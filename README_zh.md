# eReader CBZ 漫画转换器

**中文说明** | [English](README.md)

将 EPUB/MOBI 漫画文件转换为 CBZ 格式，专为电子阅读器优化，特别是 Kobo 设备。

## 核心功能

- **格式转换**：将 EPUB/MOBI 漫画转换为 CBZ 格式，为 Kobo 电子阅读器优化阅读体验
- **修复乱序漫画**：专门处理来自 moe 系列网站的页面顺序混乱的漫画
- **KCC 增强**：使用 Kindle Comic Converter (KCC) 进行图像优化
- **跨平台**：支持 Windows、macOS 和 Linux，支持图形界面和命令行模式

## 快速开始

### 安装
```bash
git clone https://github.com/shihong5858/eReader-cbz-manga-converter.git
cd eReader-cbz-manga-converter
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
python build.py dev
```

### 使用方法
```bash
# 图形界面模式
python build.py run

# 命令行模式
python main.py input.epub output_directory

# 构建可执行文件
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

## 系统要求
- Python 3.8+
- 依赖项通过 pyproject.toml 自动管理

## 许可证
MIT License 