@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Borgerflow

where python >nul 2>nul
if %errorlevel%==0 (
    python setup_and_run.py
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 setup_and_run.py
    goto :end
)

echo Python er ikke installeret.
echo Hent det fra https://www.python.org/downloads/
echo Husk at krydse af for "Add Python to PATH" under installationen.
pause
goto :end

:end
