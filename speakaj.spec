# PyInstaller spec — build with: pyinstaller speakaj.spec  (or python build.py)
import sys

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("speakaj") + collect_submodules("pynput") + ["anthropic"]
if sys.platform != "darwin":
    hiddenimports += collect_submodules("pystray")

# Modules nothing in Speakaj uses; leaving them out makes the app smaller.
excludes = ["matplotlib", "scipy", "pandas", "IPython", "pytest", "unittest", "pydoc", "test"]

a = Analysis(["launcher.py"], hiddenimports=hiddenimports, excludes=excludes, noarchive=False)
pyz = PYZ(a.pure)

# One folder (not --onefile) on every platform: a onefile .exe unpacks ~40 MB
# to a temp folder on every launch, and antivirus rescans it each time, which
# made startup take many seconds on Windows. The installer ships the folder.
exe = EXE(pyz, a.scripts, exclude_binaries=True, name="Speakaj", console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Speakaj", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Speakaj.app",
        bundle_identifier="com.patpon.speakaj",
        info_plist={
            "NSMicrophoneUsageDescription": "Speakaj ใช้ไมโครโฟนเพื่อแปลงเสียงพูดเป็นข้อความ",
            "LSUIElement": True,
            "CFBundleShortVersionString": "0.2.5",
        },
    )
