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
Source: "..\dist\Speakaj.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Speakaj"; Filename: "{app}\Speakaj.exe"
Name: "{group}\Uninstall Speakaj"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Speakaj"; Filename: "{app}\Speakaj.exe"; Tasks: desktopicon
Name: "{userstartup}\Speakaj"; Filename: "{app}\Speakaj.exe"; Tasks: startup

[Run]
Filename: "{app}\Speakaj.exe"; Description: "Start Speakaj now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Speakaj.exe"; Flags: runhidden; RunOnceId: "StopSpeakaj"

[UninstallDelete]
; Remove settings, demo code, API keys and history so nothing is left behind.
Type: filesandordirs; Name: "{%USERPROFILE}\.speakaj"
