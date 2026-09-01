@echo off
title ScrapeAgent · Desktop Agent
cd /d "%~dp0"
python desktop_gui.py
if errorlevel 1 pause
