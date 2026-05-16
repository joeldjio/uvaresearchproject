; ═══════════════════════════════════════════════════════════════════════
;  DroneResearch GCS — Windows Installer (Inno Setup 6+)
; ═══════════════════════════════════════════════════════════════════════
;
;  Build:
;     iscc tools\installer\inno\droneresearch_gcs.iss
;  Output:
;     tools\installer\out\DroneResearch-GCS-Setup-0.2.0.exe
;
;  Prerequisite: PyInstaller has produced dist\DroneResearchGCS\.
; ═══════════════════════════════════════════════════════════════════════

#define AppName        "DroneResearch GCS"
#define AppPublisher   "RZ Aerospace Research"
#define AppVersion     "0.2.0"
#define AppURL         "https://github.com/joeldjio/uavresearchproject"
#define AppExeName     "DroneResearch.exe"
#define AppId          "{{C7E2A3B4-1D2E-4F5A-8B9C-DRONERESEARCH-GCS}"

#define ProjectRoot    "..\..\.."
#define DistRoot       ProjectRoot + "\dist\DroneResearchGCS"
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
DefaultDirName={autopf}\DroneResearch GCS
DefaultGroupName=DroneResearch
DisableProgramGroupPage=no
LicenseFile={#ProjectRoot}\LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\out
OutputBaseFilename=DroneResearch-GCS-Setup-{#AppVersion}
SetupIconFile={#AssetsDir}\rz_icon.ico
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
Name: "associate";   Description: "Associate &.drscenario files with {#AppName}"; \
    GroupDescription: "File associations:"; Flags: unchecked

[Files]
Source: "{#DistRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\LICENSE";   DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} (Legacy Widget UI)"; Filename: "{app}\{#AppExeName}"; \
    Parameters: "--legacy"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Documentation"; Filename: "{app}\README.md"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Registry]
; .drscenario file association (optional)
Root: HKCU; Subkey: "Software\Classes\.drscenario"; \
    ValueType: string; ValueName: ""; ValueData: "DroneResearch.Scenario"; \
    Tasks: associate; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\DroneResearch.Scenario"; \
    ValueType: string; ValueName: ""; ValueData: "DroneResearch Scenario"; \
    Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\DroneResearch.Scenario\DefaultIcon"; \
    ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; \
    Tasks: associate
Root: HKCU; Subkey: "Software\Classes\DroneResearch.Scenario\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; \
    Tasks: associate

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
    MsgBox('DroneResearch GCS requires Windows 10 or later (uses Qt 6 / WebEngine).',
           mbCriticalError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;
