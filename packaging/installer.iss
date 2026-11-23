; Script generated for Inno Setup 6
; Application: LeMinhTTS V1
; Offline Setup Installer with Wizard, Progress, Desktop Shortcut, and Uninstaller

#define MyAppName "LeMinhTTS V2"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Lê Minh"
#define MyAppExeName "LeMinhTTS V2.exe"

[Setup]
; App Identity
AppId={{D37F8E32-4829-4B52-8E3B-9A70CD6B819E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL=mailto:leminh.vdm@gmail.com
AppSupportURL=mailto:leminh.vdm@gmail.com
AppContact=leminh.vdm@gmail.com
DefaultDirName={autopf}\LeMinhTTS
DefaultGroupName=LeMinhTTS
AllowNoIcons=yes

; Output Configuration
OutputDir=..\dist
OutputBaseFilename=LeMinhTTS_V2_Setup
SetupIconFile=..\icon_app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression & Offline Packaging
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Modern Visual Style
WizardStyle=modern
WizardSizePercent=100
DisableProgramGroupPage=no
PrivilegesRequiredOverridesAllowed=dialog

; Safety & Updates
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy all bundled distribution files including ONNX models, Qt runtime, and tools (ffmpeg, ffprobe, yt-dlp)
Source: "..\dist\LeMinhTTS V2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
