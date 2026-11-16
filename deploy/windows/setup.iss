#ifndef AppVersion
  #define AppVersion "0.36.0"
#endif
#ifndef BundleDir
  #error BundleDir is required
#endif
#ifndef OutputDirPath
  #error OutputDirPath is required
#endif
[Setup]
AppId={{5A203140-3342-4724-B32F-76F71812EC27}
AppName=ArcReel 创作工作台
AppVersion={#AppVersion}
AppPublisher=ArcReel contributors
DefaultDirName={localappdata}\Programs\ArcReel
DefaultGroupName=ArcReel
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDirPath}
OutputBaseFilename=ArcReel-{#AppVersion}-windows-x64-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
LicenseFile={#BundleDir}\app\LICENSE
UninstallDisplayIcon={app}\ArcReel.exe
CloseApplications=yes
SetupLogging=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ArcReel"; Filename: "{app}\ArcReel.exe"
Name: "{autodesktop}\ArcReel"; Filename: "{app}\ArcReel.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ArcReel.exe"; Description: "启动 ArcReel 创作工作台"; Flags: nowait postinstall skipifsilent
