@echo off
title SegretarIA - Scarico Automatico USB Windows (Test Visibile)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_usb_recorder_ingest.ps1"
pause
