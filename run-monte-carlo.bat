@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" || exit /b 1
set "study=%~1"
if not defined study goto usage
for %%S in (P01 P02 P03 P04 P05 P06 P07 P08 P09) do if /i "%study%"=="%%S" goto valid
goto usage
:valid
set "launcher=manuscripts\MSC-MUS-%study%\monte_carlo.py"
set "venv=.venv\monte-carlo-windows\%study%"
set "venvpython=%venv%\Scripts\python.exe"
rem The original argument tail is preserved by the manuscript wrapper.
rem This entry point accepts study followed by standard runner options.
if /i "%~2"=="--setup" goto setup
if /i "%study%"=="P02" goto qualitative
if /i "%~2"=="--help" goto systempython
if /i "%~2"=="--list" goto systempython
for %%A in (%*) do if /i "%%~A"=="--summary" goto systempython
for %%A in (%*) do if /i "%%~A"=="--list" goto systempython
if not exist "%venvpython%" goto missing
set "runner=%venvpython%"
goto execute
:systempython
set "runner=python"
goto execute
:qualitative
echo P02: NOT_APPLICABLE ^(qualitative design^)
set "rc=0"
goto finish
:setup
if not "%~3"=="" goto usage
if /i "%study%"=="P02" goto qualitative
if not defined PYTHON_BIN set "PYTHON_BIN=python"
"%PYTHON_BIN%" -m venv "%venv%"
if errorlevel 1 goto failed
"%venvpython%" -m pip install -r "manuscripts\MSC-MUS-%study%\analysis\requirements.txt"
set "rc=%errorlevel%"
goto finish
:execute
rem Rebuild argument tail by forwarding via a small Python dispatcher.
"%runner%" "%~dp0monte_carlo_windows.py" %*
set "rc=%errorlevel%"
goto finish
:missing
echo Missing Windows environment. Run monte_carlo.bat --setup first.
set "rc=1"
goto finish
:usage
echo Usage: run-monte-carlo.bat P01..P09 [--setup or runner options]
set "rc=2"
goto finish
:failed
set "rc=1"
:finish
popd
exit /b %rc%
