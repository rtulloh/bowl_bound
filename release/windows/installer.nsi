; Bowl Bound per-user installer. File lists come only from the verified native ZIP.
Unicode true
!include "MUI2.nsh"
Name "Bowl Bound ${DISPLAY_VERSION}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\BowlBound"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\BowlBound"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\BowlBound.exe"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${BUNDLE_DIR}\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Bowl Bound"
  SetShellVarContext current
  ; Never overlay an unrelated directory or a running/older installation.
  ClearErrors
  FindFirst $0 $1 "$INSTDIR\*"
  IfErrors empty_directory
  check_entry:
    StrCmp $1 "" close_search
    StrCmp $1 "." next_entry
    StrCmp $1 ".." next_entry
    FindClose $0
    MessageBox MB_OK|MB_ICONSTOP "Choose an empty installation folder. Uninstall an existing Bowl Bound first; personal team libraries and saves are preserved." /SD IDOK
    SetErrorLevel 2
    Abort
  next_entry:
    FindNext $0 $1
    IfErrors close_search
    Goto check_entry
  close_search:
    FindClose $0
  empty_directory:
  ClearErrors
  !include "${INSTALL_LIST}"
  IfErrors 0 files_ok
    SetErrorLevel 1
    Abort
  files_ok:
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortCut "$SMPROGRAMS\Bowl Bound.lnk" "$INSTDIR\BowlBound.exe"
  CreateShortCut "$DESKTOP\Bowl Bound.lnk" "$INSTDIR\BowlBound.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "Bowl Bound"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${DISPLAY_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\BowlBound.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "URLInfoAbout" "https://github.com/rtulloh/bowl_bound"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  ; Exact generated file/directory removals only. Never recursively delete INSTDIR.
  !include "${UNINSTALL_LIST}"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$SMPROGRAMS\Bowl Bound.lnk"
  Delete "$DESKTOP\Bowl Bound.lnk"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  RMDir "$INSTDIR"
SectionEnd
