"""Build a standalone Speakaj app with PyInstaller.

    python build.py   ->  dist/Speakaj.exe (Windows) or dist/Speakaj.app (macOS)
"""

import PyInstaller.__main__

if __name__ == "__main__":
    PyInstaller.__main__.run(["speakaj.spec", "--noconfirm", "--clean"])
