@echo off
title Zoom Clone Pro Server
color 0A

echo ========================================
echo     ZOOM CLONE PRO - Server Startup
echo ========================================
echo.

:: Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not found! Please install Docker Desktop.
    echo Download: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: Start LiveKit with Docker
echo [1/3] Starting LiveKit Server...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start LiveKit!
    pause
    exit /b 1
)
echo [OK] LiveKit Server started on ws://localhost:7880
echo.

:: Wait for services
timeout /t 3 /nobreak >nul

:: Start Python Backend
echo [2/3] Starting Python Backend...
cd backend
python run.py
