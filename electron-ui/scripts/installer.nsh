!macro customUnInstall
  ${ifNot} ${isUpdated}
    SetShellVarContext current

    RMDir /r "$APPDATA\${APP_FILENAME}"
    RMDir /r "$APPDATA\${APP_PRODUCT_FILENAME}"
    RMDir /r "$APPDATA\${APP_PACKAGE_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}"
    RMDir /r "$LOCALAPPDATA\${APP_PRODUCT_FILENAME}"
    RMDir /r "$LOCALAPPDATA\${APP_PACKAGE_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}-updater"
    RMDir /r "$LOCALAPPDATA\${APP_PRODUCT_FILENAME}-updater"
    RMDir /r "$LOCALAPPDATA\${APP_PACKAGE_NAME}-updater"

    SetShellVarContext all

    RMDir /r "$APPDATA\${APP_FILENAME}"
    RMDir /r "$APPDATA\${APP_PRODUCT_FILENAME}"
    RMDir /r "$APPDATA\${APP_PACKAGE_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}"
    RMDir /r "$LOCALAPPDATA\${APP_PRODUCT_FILENAME}"
    RMDir /r "$LOCALAPPDATA\${APP_PACKAGE_NAME}"

    RMDir /r "$LOCALAPPDATA\${APP_FILENAME}-updater"
    RMDir /r "$LOCALAPPDATA\${APP_PRODUCT_FILENAME}-updater"
    RMDir /r "$LOCALAPPDATA\${APP_PACKAGE_NAME}-updater"

    SetShellVarContext lastused
  ${endIf}
!macroend
