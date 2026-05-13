@echo off
title Vega Elite :: Setup
color 0A
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [xx] Python introuvable.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [xx] Echec installation dependances.
    pause
    exit /b 1
)

if not exist ".env" copy /Y ".env.example" ".env" >nul
if not exist "tokens.txt" type nul > tokens.txt
if not exist "proxies.txt" type nul > proxies.txt
if not exist "hits.txt" type nul > hits.txt

echo [++] Setup OK.
pause
