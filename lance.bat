@echo off
title Vega Elite :: Checker
color 0C
cd /d "%~dp0"

if not exist ".env" (
    echo [xx] .env manquant. Lance setup.bat.
    pause
    exit /b 1
)
if not exist "tokens.txt" (
    echo [xx] tokens.txt manquant. Lance setup.bat.
    pause
    exit /b 1
)

python checker.py
pause
