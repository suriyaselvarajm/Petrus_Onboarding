@echo off
:: ─────────────────────────────────────────────────────────────────
::  Petrus Technologies — Onboarding Tool  |  Build Script
:: ─────────────────────────────────────────────────────────────────
title Petrus Onboarding Build

echo.
echo  [1/3] Installing PyInstaller...
python -m pip install pyinstaller --quiet
if %errorlevel% NEQ 0 (
    echo  [X] Failed to install PyInstaller.
    pause & exit /b 1
)

echo  [2/3] Building executable...
:: --onefile: Bundles everything into a single .exe
:: --windowed: Hides the console window on launch
:: --add-data: Includes the logo.png in the bundle
:: --name: Sets the output filename
pyinstaller --noconfirm --onefile --windowed ^
    --add-data "logo.png;." ^
    --name "PetrusOnboarding" ^
    main.py

if %errorlevel% NEQ 0 (
    echo.
    echo  [X] Build failed! Check the output above for errors.
    pause & exit /b 1
)

echo.
echo  [3/3] Success!
echo  ─────────────────────────────────────────────────────────────────
echo   Your application is ready:
echo   Location: %~dp0dist\PetrusOnboarding.exe
echo  ─────────────────────────────────────────────────────────────────
echo.
echo  NOTE: The other laptop MUST have:
echo  1. Azure CLI installed (az login)
echo  2. RSAT (Active Directory module) enabled
echo  3. Connection to the local network/VPN for AD access
echo.
pause
