@echo off
:: ============================================================
::  Archives Library — Windows / WAMP One-Click Setup
::  Double-click this file OR run it from PowerShell / CMD
:: ============================================================
title Archives Library Setup

echo.
echo  ================================================
echo   Archives Library — Automated Setup
echo  ================================================
echo.

:: Move to the folder where this .bat file lives (the project root)
cd /d "%~dp0"
echo  Working directory: %CD%
echo.

:: ----------- Check Python -----------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Download from https://python.org/downloads/
    echo  Make sure to tick "Add Python to PATH" during installation.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo  [OK] Found %%i

:: ----------- Create virtual environment -----------
if not exist "venv" (
    echo  Creating virtual environment...
    python -m venv venv
)
echo  [OK] Virtual environment ready.

:: ----------- Activate venv -----------
call venv\Scripts\activate.bat

:: ----------- Upgrade pip silently -----------
python -m pip install --upgrade pip --quiet

:: ----------- Install dependencies -----------
echo  Installing dependencies (Django, mysqlclient, Pillow)...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  [WARN] mysqlclient failed. Trying binary wheel...
    pip install mysqlclient --only-binary :all:
    pip install Django Pillow
)
echo  [OK] Dependencies installed.

:: ----------- Create media directories -----------
if not exist "media\covers"  mkdir media\covers
if not exist "media\books"   mkdir media\books
if not exist "media\avatars" mkdir media\avatars
if not exist "media\authors" mkdir media\authors
echo  [OK] Media directories ready.

:: ----------- Run migrations -----------
echo  Running database migrations...
python manage.py makemigrations archives
python manage.py migrate
if errorlevel 1 (
    echo.
    echo  [ERROR] Migration failed.
    echo  Make sure WAMP is running and the database "archives_library" exists in phpMyAdmin.
    pause & exit /b 1
)
echo  [OK] Database tables created.

:: ----------- Create admin user -----------
echo  Creating admin superuser...
python manage.py create_admin
echo  [OK] Admin user ready.

echo.
echo  ================================================
echo   Setup Complete!
echo  ================================================
echo.
echo   Run the server:   python manage.py runserver
echo   Open browser:     http://127.0.0.1:8000
echo.
echo   Admin:  username=admin   password=admin123
echo.
pause
