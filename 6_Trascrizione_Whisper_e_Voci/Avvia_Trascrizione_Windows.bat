@echo off
title SegretarIA - Trascrizione Locale Windows
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_transcribe_runner.ps1"
if %errorlevel% neq 0 (
    echo.
    echo ======================================================================
    echo Premere un tasto per chiudere...
    echo ======================================================================
    pause >nul
)
