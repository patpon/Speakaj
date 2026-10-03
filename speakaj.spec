# PyInstaller spec — build with: pyinstaller speakaj.spec  (or python build.py)
import sys

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("speakaj") + collect_submodules("pynput") + ["anthropic"]
if sys.platform != "darwin":
    hiddenimports += collect_submodules("pystray")

a = Analysis(["launcher.py"], hiddenimports=hiddenimports, noarchive=False)
pyz = PYZ(a.pure)

if sys.platform == "win32":
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="Speakaj", console=False, upx=False)
else:
    exe = EXE(pyz, a.scripts, exclude_binaries=True, name="Speakaj", console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="Speakaj")
    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="Speakaj.app",
            bundle_identifier="com.patpon.speakaj",
            info_plist={
                "NSMicrophoneUsageDescription": "Speakaj ใช้ไมโครโฟนเพื่อแปลงเสียงพูดเป็นข้อความ",
                "LSUIElement": True,
                "CFBundleShortVersionString": "0.1.0",
            },
        )
