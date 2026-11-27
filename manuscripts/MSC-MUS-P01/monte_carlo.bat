@echo off
setlocal
if not "%~1"=="" goto args
:menu
 echo.
 echo MSC-MUS-P01 - Monte Carlo
 echo [1] Instalacja zaleznosci
 echo [2] Symulacja wstepna
 echo [3] Pelna symulacja
 echo [4] Test uruchomieniowy
 echo [0] Wyjscie
 choice /c 12340 /n /m "Wybierz: "
 if errorlevel 5 exit /b 0
 if errorlevel 4 goto smoke
 if errorlevel 3 goto full
 if errorlevel 2 goto pilot
 if errorlevel 1 goto setup
 goto menu
:setup
 call "%~dp0..\..\run-monte-carlo.bat" P01 --setup
 goto report
:pilot
 call "%~dp0..\..\run-monte-carlo.bat" P01 --profile pilot
 goto report
:full
 call "%~dp0..\..\run-monte-carlo.bat" P01 --profile full --summary
 if errorlevel 1 goto report
 choice /c TN /n /m "Rozpoczac pelna symulacje? [T/N] "
 if errorlevel 2 goto menu
 call "%~dp0..\..\run-monte-carlo.bat" P01 --profile full
 goto report
:smoke
 call "%~dp0..\..\run-monte-carlo.bat" P01 --profile smoke
:report
 echo Kod zakonczenia: %errorlevel%
 echo Wykresy: "%~dp0results"
 pause
 goto menu
:args
 call "%~dp0..\..\run-monte-carlo.bat" P01 %*
 exit /b %errorlevel%
