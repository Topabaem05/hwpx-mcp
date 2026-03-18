!include LogicLib.nsh

!macro InstallVCRedist
  StrCpy $1 "$INSTDIR\resources\windows-prereqs\vc_redist.x64.exe"
  ${IfNot} ${FileExists} $1
    MessageBox MB_ICONSTOP "Microsoft Visual C++ x64 Redistributable is missing from the installer package.$\r$\n$\r$\nExpected: $1"
    Abort
  ${EndIf}

  DetailPrint "Installing Microsoft Visual C++ x64 Redistributable..."
  ExecWait '"$1" /install /passive /norestart' $0

  ${If} $0 == 0
    Goto VCRedistDone
  ${EndIf}
  ${If} $0 == 1638
    Goto VCRedistDone
  ${EndIf}
  ${If} $0 == 3010
    MessageBox MB_ICONINFORMATION "Microsoft Visual C++ x64 Redistributable was installed successfully, but Windows needs a restart before HWPX MCP can run reliably."
    Goto VCRedistDone
  ${EndIf}
  ${If} $0 == 1618
    MessageBox MB_ICONSTOP "Another Windows installation is already in progress. Close other installers and run HWPX MCP Setup again."
    Abort
  ${EndIf}

  MessageBox MB_ICONSTOP "Microsoft Visual C++ x64 Redistributable installation failed (exit code $0)."
  Abort

  VCRedistDone:
!macroend

!macro customInstall
  !insertmacro InstallVCRedist
!macroend
