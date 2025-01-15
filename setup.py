from setuptools import setup
import os
import shiboken6

# Get shiboken6 library path
shiboken6_path = os.path.dirname(shiboken6.__file__)
shiboken6_lib = os.path.join(shiboken6_path, 'libshiboken6.abi3.6.6.dylib')

APP = ['main.py']
DATA_FILES = [
    ('', ['device_info.json']),
    ('gui', ['gui/device_info.json']),
    ('kcc', ['kcc/kindlecomicconverter/image.py',
             'kcc/kindlecomicconverter/shared.py',
             'kcc/kindlecomicconverter/comic2ebook.py']),
]

OPTIONS = {
    'packages': ['PySide6', 'ebooklib', 'PIL', 'py7zr', 'kcc'],
    'includes': ['shiboken6'],
    'excludes': ['tkinter', 'matplotlib'],
    'qt_plugins': ['platforms', 'styles', 'imageformats'],
    'strip': True,
    'iconfile': 'app.icns',
    'semi_standalone': True,
    'site_packages': True,
    'plist': {
        'CFBundleName': 'Kobo Manga Converter',
        'CFBundleDisplayName': 'Kobo Manga Converter',
        'CFBundleIdentifier': 'com.kobo.mangaconverter',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'LSBackgroundOnly': False,
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName': 'Comic Book Archive',
            'CFBundleTypeExtensions': ['cbz', 'zip'],
            'CFBundleTypeRole': 'Viewer',
        }],
    },
}

setup(
    app=APP,
    name='Kobo Manga Converter',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 