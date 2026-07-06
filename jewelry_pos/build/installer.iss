; Inno Setup script for KaratPOS.
;
; Build order:
;   1. venv\Scripts\python.exe -m PyInstaller build\jewelry_pos.spec ^
;        --distpath dist --workpath build\work --noconfirm
;   2. Open this file in Inno Setup Compiler (or run ISCC.exe installer.iss)
;      from the jewelry_pos\build\ directory.
;   3. Output: jewelry_pos\build\output\JewelryPOS_Setup.exe
;
; The database and backups are NOT installed into Program Files --
; they are created by the app itself, next to KaratPOS.exe, on first
; run (see app/utils/config.py). Installing into Program Files is
; still fine because Windows treats a per-machine install folder as
; writable for the installing user by default; for stricter lockdown
; environments, change DefaultDirName below to {localappdata}\KaratPOS.

#define MyAppName "KaratPOS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "KaratPOS"
#define MyAppExeName "KaratPOS.exe"

[Setup]
AppId={{8F2B6C1A-4E3D-4F5A-9B7C-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=JewelryPOS_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; The entire one-folder PyInstaller build, produced by the build step above.
Source: "..\dist\KaratPOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove app-generated data on uninstall only if the user opts in via a
; separate "clean uninstall" — by default we leave data/ in place so a
; reinstall/upgrade doesn't destroy the shop's sales history.
; Type: filesandordirs; Name: "{app}\data"
