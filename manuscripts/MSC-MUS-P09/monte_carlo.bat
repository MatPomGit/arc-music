@echo off
setlocal
if not "%~1"=="" goto args
:menu
 echo.
 echo MSC-MUS-P09 - Monte Carlo
 echo [1] Instalacja zaleznosci
 echo [2] Symulacja wstepna
 echo [3] Pelna symulacja
 echo [4] Test uruchomieniowy
 echo [5] Wlasna symulacja
 echo [0] Wyjscie
 choice /c 123450 /n /m "Wybierz: "
 if errorlevel 6 exit /b 0
 if errorlevel 5 goto custom
 if errorlevel 4 goto smoke
 if errorlevel 3 goto full
 if errorlevel 2 goto pilot
 if errorlevel 1 goto setup
 goto menu
:setup
 call "%~dp0..\..\run-monte-carlo.bat" P09 --setup
 goto report
:pilot
 call "%~dp0..\..\run-monte-carlo.bat" P09 --profile pilot
 goto report
:full
 call "%~dp0..\..\run-monte-carlo.bat" P09 --profile full --summary
 if errorlevel 1 goto report
 choice /c TN /n /m "Rozpoczac pelna symulacje? [T/N] "
 if errorlevel 2 goto menu
 call "%~dp0..\..\run-monte-carlo.bat" P09 --profile full
 goto report
:custom
 call "%~dp0..\..\run-monte-carlo.bat" P09 --custom
 goto report
:smoke
 call "%~dp0..\..\run-monte-carlo.bat" P09 --profile smoke
:report
 echo Kod zakonczenia: %errorlevel%
 echo Wykresy: "%~dp0results"
 pause
 goto menu
:args
 call "%~dp0..\..\run-monte-carlo.bat" P09 %*
 exit /b %errorlevel%
