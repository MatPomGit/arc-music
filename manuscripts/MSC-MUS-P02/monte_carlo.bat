@echo off
setlocal
if not "%~1"=="" goto args
call "%~dp0..\..\run-monte-carlo.bat" P02 --profile smoke
set "rc=%errorlevel%"
echo.
pause
exit /b %rc%
:args
call "%~dp0..\..\run-monte-carlo.bat" P02 %*
exit /b %errorlevel%
