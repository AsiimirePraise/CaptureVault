; Inno Setup script for CaptureVault Windows installer
; Requires Inno Setup 6+: https://jrsoftware.org/isinfo.php

#define MyAppName "CaptureVault"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CaptureVault"
#define MyAppURL "https://github.com/AsiimirePraise/CaptureVault"
#define MyAppExeName "CaptureVault.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=no
OutputDir=..\dist\installer
OutputBaseFilename=CaptureVaultSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\CaptureVault.exe"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Add optional README or license files here

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := FileExists(ExpandConstant('{#SourcePath}\..\dist\CaptureVault.exe'));
  if not Result then
    MsgBox('CaptureVault.exe not found. Run PyInstaller build first.', mbError, MB_OK);
end;
