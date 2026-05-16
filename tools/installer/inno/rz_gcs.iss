; ════════════════════════════════════════════════════════════════════════
;  RZ GCS — Windows Installer (Inno Setup 6+)
; ════════════════════════════════════════════════════════════════════════
;
;  Build:
;     iscc tools\installer\inno\rz_gcs.iss
;  Output:
;     tools\installer\out\RZ-GCS-Setup-0.2.0.exe
;
;  Prerequisite: PyInstaller has produced dist\RZGCS\.
;
;  Upgrade semantics
;  -----------------
;  - The fixed {#AppId} GUID is what makes Inno Setup treat re-installs
;    of newer versions as in-place upgrades (uninstalls the old version
;    silently before copying the new files).
;  - The in-app updater (tools/ui/updater.py) calls this installer with
;    /SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS so users get a
;    seamless one-click upgrade flow.
; ════════════════════════════════════════════════════════════════════════

#define AppName        "RZ GCS"
#define AppPublisher   "RZ Solutions"
#define AppVersion     "0.2.0"
#define AppURL         "https://github.com/joeldjio/uavresearchproject"
#define AppExeName     "RZ GCS.exe"
; Stable, randomly-generated GUID. DO NOT change this once published
; — it would break upgrade detection on existing installs.
#define AppId          "{{8F7E2D14-3A6B-4F2C-9B4E-RZGCS00000001}"

#define ProjectRoot    "..\..\.."
#define DistRoot       ProjectRoot + "\dist\RZGCS"
#define AssetsDir      "..\assets"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\RZ Solutions\RZ GCS
DefaultGroupName=RZ Solutions
DisableProgramGroupPage=no
LicenseFile={#ProjectRoot}\LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\out
OutputBaseFilename=RZ-GCS-Setup-{#AppVersion}
SetupIconFile={#AssetsDir}\rz_icon.ico
; ── Silent / in-place upgrade support (used by the in-app updater) ──
; CloseApplications=force lets us replace _internal/ even while the
; previous RZ GCS.exe was running, and RestartApplications=yes brings
; it back up after the upgrade finishes.
CloseApplications=force
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=yes
WizardImageFile={#AssetsDir}\wizard_large.bmp
WizardSmallImageFile={#AssetsDir}\wizard_small.bmp
WizardStyle=modern
WizardSizePercent=120
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no
DisableDirPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german";  MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; \
    GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Create a &Quick Launch shortcut"; \
    GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#DistRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\LICENSE";   DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} (Legacy Widget UI)"; Filename: "{app}\{#AppExeName}"; \
    Parameters: "--legacy"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "Launch {#AppName}"; \
    Flags: postinstall skipifsilent nowait

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Code]
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  if Version.NTPlatform and (Version.Major < 10) then
  begin
    MsgBox('RZ GCS requires Windows 10 or later (uses Qt 6 / WebEngine).',
           mbCriticalError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;
