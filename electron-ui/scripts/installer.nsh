!macro customUnInstall
  ${ifNot} ${isUpdated}
    SetShellVarContext current

    RMDir /r "$APPDATA\${APP_FILENAME}"
    RMDir /r "$APPDATA\${PRODUCT_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}"
    RMDir /r "$LOCALAPPDATA\${PRODUCT_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}-updater"
    RMDir /r "$LOCALAPPDATA\${PRODUCT_NAME}-updater"

    SetShellVarContext all

    RMDir /r "$APPDATA\${APP_FILENAME}"
    RMDir /r "$APPDATA\${PRODUCT_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}"
    RMDir /r "$LOCALAPPDATA\${PRODUCT_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}-updater"
    RMDir /r "$LOCALAPPDATA\${PRODUCT_NAME}-updater"

  ${endIf}
!macroend
