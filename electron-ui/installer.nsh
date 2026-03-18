!include LogicLib.nsh

!define LOCAL_MODEL_ID "Qwen/Qwen2.5-1.5B-Instruct"
!define LOCAL_MODEL_DIR_NAME "Qwen__Qwen2.5-1.5B-Instruct"

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

!macro InstallLocalModel
  StrCpy $1 "$LOCALAPPDATA\HWPX MCP\models\${LOCAL_MODEL_DIR_NAME}"

  ${If} ${FileExists} "$1\config.json"
  ${AndIf} ${FileExists} "$1\tokenizer_config.json"
  ${AndIf} ${FileExists} "$1\model.safetensors"
    DetailPrint "Local Qwen model already installed"
    Goto LocalModelDone
  ${EndIf}

  StrCpy $2 "$INSTDIR\resources\backend-win\python\python.exe"
  ${IfNot} ${FileExists} $2
    MessageBox MB_ICONSTOP "Bundled backend Python runtime is missing.$\r$\n$\r$\nExpected: $2"
    Abort
  ${EndIf}

  StrCpy $3 "$INSTDIR\resources\windows-prereqs\install-local-model.py"
  ${IfNot} ${FileExists} $3
    MessageBox MB_ICONSTOP "Installer model helper is missing.$\r$\n$\r$\nExpected: $3"
    Abort
  ${EndIf}

  DetailPrint "Downloading local Qwen model. This can take several minutes..."
  ExecWait '"$2" "$3" "$INSTDIR\resources\backend-win" "${LOCAL_MODEL_ID}" "${LOCAL_MODEL_DIR_NAME}" "$LOCALAPPDATA\HWPX MCP\models"' $0

  ${If} $0 == 0
    Goto LocalModelDone
  ${EndIf}

  MessageBox MB_ICONSTOP "Local Qwen model installation failed (exit code $0). Check your internet connection and run HWPX MCP Setup again."
  Abort

  LocalModelDone:
!macroend

!macro customInstall
  !insertmacro InstallVCRedist
  !insertmacro InstallLocalModel
!macroend
