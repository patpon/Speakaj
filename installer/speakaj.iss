; Inno Setup script — builds Speakaj-Setup.exe (run by .github/workflows/release.yml)
; Per-user install: no admin prompt, uninstall from Settings > Apps.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E3B1C52-9F0A-4C1E-A6E1-5D3B7A2C8F41}
AppName=Speakaj
AppVersion={#AppVersion}
AppPublisher=patpon
AppPublisherURL=https://github.com/patpon/Speakaj
DefaultDirName={localappdata}\Programs\Speakaj
DefaultGroupName=Speakaj
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Speakaj-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Speakaj
UninstallDisplayIcon={app}\Speakaj.exe
CloseApplications=force

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce
Name: "startup"; Description: "Start Speakaj when Windows starts"; Flags: checkedonce

[Files]
Source: "..\dist\Speakaj\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Speakaj"; Filename: "{app}\Speakaj.exe"
Name: "{group}\Uninstall Speakaj"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Speakaj"; Filename: "{app}\Speakaj.exe"; Tasks: desktopicon
Name: "{userstartup}\Speakaj"; Filename: "{app}\Speakaj.exe"; Tasks: startup

[Run]
Filename: "{app}\Speakaj.exe"; Description: "Start Speakaj now"; Flags: nowait postinstall skipifsilent

[Code]
// Close a running Speakaj before copying files. Without this an upgrade
// fails with "MoveFile failed; code 183" because Speakaj.exe is locked
// (Speakaj lives in the tray, so the Restart Manager cannot close it).
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM Speakaj.exe', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
  Sleep(1500);
  Result := '';
end;

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM Speakaj.exe"; Flags: runhidden; RunOnceId: "StopSpeakaj"

[InstallDelete]
; Leftovers from the old single-file build are replaced by the folder build.
Type: files; Name: "{app}\Speakaj.exe"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
; Remove settings, demo code, API keys and history so nothing is left behind.
Type: filesandordirs; Name: "{%USERPROFILE}\.speakaj"
