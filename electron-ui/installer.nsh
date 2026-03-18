!include LogicLib.nsh

Var /GLOBAL vcRedistExitCode
Var /GLOBAL vcRedistPath

!macro InstallVCRedist
  StrCpy $vcRedistPath "$INSTDIR\resources\windows-prereqs\vc_redist.x64.exe"
  ${IfNot} ${FileExists} $vcRedistPath
    MessageBox MB_ICONSTOP "Microsoft Visual C++ x64 Redistributable is missing from the installer package.$\r$\n$\r$\nExpected: $vcRedistPath"
    Abort
  ${EndIf}

  DetailPrint "Installing Microsoft Visual C++ x64 Redistributable..."
  ExecWait '"$vcRedistPath" /install /passive /norestart' $vcRedistExitCode

  ${If} $vcRedistExitCode == 0
    Goto VCRedistDone
  ${EndIf}
  ${If} $vcRedistExitCode == 1638
    Goto VCRedistDone
  ${EndIf}
  ${If} $vcRedistExitCode == 3010
    MessageBox MB_ICONINFORMATION "Microsoft Visual C++ x64 Redistributable was installed successfully, but Windows needs a restart before HWPX MCP can run reliably."
    Goto VCRedistDone
  ${EndIf}
  ${If} $vcRedistExitCode == 1618
    MessageBox MB_ICONSTOP "Another Windows installation is already in progress. Close other installers and run HWPX MCP Setup again."
    Abort
  ${EndIf}

  MessageBox MB_ICONSTOP "Microsoft Visual C++ x64 Redistributable installation failed (exit code $vcRedistExitCode)."
  Abort

  VCRedistDone:
!macroend

!macro customInstall
  !insertmacro InstallVCRedist
!macroend
