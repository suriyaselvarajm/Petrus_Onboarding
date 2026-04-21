@echo off
:: ─────────────────────────────────────────────────────────────────
::  Petrus Technologies — Onboarding Tool  |  Setup Script
::  Run as Administrator for RSAT/AD module installation.
:: ─────────────────────────────────────────────────────────────────
title Petrus Onboarding Setup

:: ── Elevation check ───────────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Please right-click and choose "Run as Administrator"
    pause
    exit /b 1
)

color 0B
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   PETRUS TECHNOLOGIES — Employee Onboarding     ║
echo  ║              Setup  v1.0.0                       ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── Python ────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [X] Python 3.10+ not found.
    echo      Download: https://www.python.org/downloads/
    pause & exit /b 1
)
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYVER=%%V
echo  [OK] Python %PYVER%

:: ── pip upgrade ───────────────────────────────────────────────────
echo  Upgrading pip...
python -m pip install --upgrade pip --quiet
echo  [OK] pip upgraded

:: ── Python packages ───────────────────────────────────────────────
echo  Installing Python packages...
python -m pip install -r requirements.txt --quiet
if %errorlevel% NEQ 0 (
    echo  [X] Failed to install required packages.
    pause & exit /b 1
)
echo  [OK] Python packages installed

:: ── Azure CLI ─────────────────────────────────────────────────────
echo.
az --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [!] Azure CLI not found. Attempting install via winget...
    winget install --id Microsoft.AzureCLI -e --silent ^
        --accept-package-agreements --accept-source-agreements
    if %errorlevel% NEQ 0 (
        echo  [!] winget install failed.
        echo      Install manually: https://aka.ms/installazurecliwindows
        echo      Then re-run this script.
        pause & exit /b 1
    )
    echo  [OK] Azure CLI installed  (restart terminal if 'az' not found)
) else (
    for /f "tokens=*" %%L in ('az --version 2^>^&1 ^| findstr "azure-cli"') do (
        echo  [OK] %%L
    )
)

:: ── RSAT: Active Directory module ─────────────────────────────────
echo.
echo  Checking ActiveDirectory PowerShell module...
powershell -NoProfile -Command ^
  "if (Get-Module -ListAvailable -Name ActiveDirectory) { ^
       Write-Host '  [OK] AD module present' ^
   } else { ^
       Write-Host '  [INFO] Installing RSAT Active Directory tools...' ; ^
       $r = Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0 ; ^
       if ($LASTEXITCODE -eq 0) { Write-Host '  [OK] RSAT installed' } ^
       else { Write-Host '  [!] RSAT install failed. Enable via Settings > Optional Features.' } ^
   }"

:: ── Done ──────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Setup Complete!                                ║
echo  ║   Run the tool: python main.py                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
