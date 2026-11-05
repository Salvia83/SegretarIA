@echo off
title Installazione Avvio Automatico Nascosto - SegretarIA USB
set "SCRIPT_PATH=%~dp0windows_usb_recorder_ingest.ps1"
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SegretarIA_USB_Watcher.vbs"

echo Chiusura eventuali finestre visibili precedenti...
powershell.exe -NoProfile -Command "Get-WmiObject Win32_Process -Filter \"Name='powershell.exe' AND CommandLine LIKE '%%windows_usb_recorder_ingest%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo Creazione avvio automatico invisibile in Esecuzione Automatica di Windows...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%SCRIPT_PATH%""", 0, False
) > "%STARTUP_VBS%"

echo Avvio immediato del guardiano invisibile in background...
wscript.exe "%STARTUP_VBS%"

echo.
echo ============================================================================
echo FATTO!
echo  1. La finestra visibile e' stata sostituita dal servizio INVISIBILE.
echo  2. Partira' DA SOLO e completamente nascosto ogni volta che accendi Windows!
echo ============================================================================
echo.
pause
