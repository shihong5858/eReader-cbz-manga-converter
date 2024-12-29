from setuptools import setup
import os
import shiboken6

# 获取 shiboken6 库文件的路径
shiboken6_path = os.path.dirname(shiboken6.__file__)
shiboken6_lib = os.path.join(shiboken6_path, 'libshiboken6.abi3.6.6.dylib')

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PySide6', 'ebooklib', 'PIL', 'py7zr'],
    'includes': ['shiboken6'],
    'qt_plugins': ['platforms', 'styles'],
    'strip': True,
    'plist': {
        'CFBundleName': 'Kobo Manga Converter',
        'CFBundleDisplayName': 'Kobo Manga Converter',
        'CFBundleIdentifier': 'com.kobo.mangaconverter',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
    },
}

setup(
    app=APP,
    name='Kobo Manga Converter',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 