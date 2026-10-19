# PyInstaller spec — build with: pyinstaller speakaj.spec  (or python build.py)
import os
import re
import sys

from PyInstaller.utils.hooks import collect_submodules

with open(os.path.join(SPECPATH, "speakaj", "__init__.py"), encoding="utf-8") as f:
    VERSION = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)

hiddenimports = collect_submodules("speakaj") + collect_submodules("pynput") + ["anthropic"]
if sys.platform != "darwin":
    hiddenimports += collect_submodules("pystray")

# Modules nothing in Speakaj uses; leaving them out makes the app smaller.
excludes = ["matplotlib", "scipy", "pandas", "IPython", "pytest", "unittest", "pydoc", "test"]

# Windows file properties (Details tab). An .exe with no publisher or version
# info looks more like malware to antivirus heuristics, so fill them in.
version_info = None
if sys.platform == "win32":
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
    )

    nums = tuple(int(n) for n in re.findall(r"\d+", VERSION)[:4])
    nums += (0,) * (4 - len(nums))
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=nums, prodvers=nums),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "patpon"),
                StringStruct("FileDescription", "Speakaj - speech to text typing"),
                StringStruct("FileVersion", VERSION),
                StringStruct("InternalName", "Speakaj"),
                StringStruct("LegalCopyright", "MIT License - https://github.com/patpon/Speakaj"),
                StringStruct("OriginalFilename", "Speakaj.exe"),
                StringStruct("ProductName", "Speakaj"),
                StringStruct("ProductVersion", VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )

a = Analysis(["launcher.py"], hiddenimports=hiddenimports, excludes=excludes, noarchive=False)
pyz = PYZ(a.pure)

# One folder (not --onefile) on every platform: a onefile .exe unpacks ~40 MB
# to a temp folder on every launch, and antivirus rescans it each time, which
# made startup take many seconds on Windows. The installer ships the folder.
exe = EXE(pyz, a.scripts, exclude_binaries=True, name="Speakaj", console=False, upx=False, version=version_info)
coll = COLLECT(exe, a.binaries, a.datas, name="Speakaj", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Speakaj.app",
        bundle_identifier="com.patpon.speakaj",
        info_plist={
            "NSMicrophoneUsageDescription": "Speakaj ใช้ไมโครโฟนเพื่อแปลงเสียงพูดเป็นข้อความ",
            "LSUIElement": True,
            "CFBundleShortVersionString": VERSION,
        },
    )
