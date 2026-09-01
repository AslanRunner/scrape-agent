@echo off
chcp 65001 > nul
title ScrapeAgent - Desktop Local Application
color 0A
cls

:: Check Python availability
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not found in PATH.
    echo [i] Please ensure Python is installed and added to your system PATH.
    pause
    exit /b 1
)

:: Run the interactive desktop agent
python agent.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Program exited with an error code: %errorlevel%
    pause
)
