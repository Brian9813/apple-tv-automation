@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy.ps1" %*

if errorlevel 1 (
  echo.
  echo Deployment failed.
  echo.
  echo If the failure was from sudo, rerun and enter the Pi password when prompted.
  echo.
  echo If Docker failed while Python was initializing time, update Docker/libseccomp on the Pi:
  echo   sudo apt update
  echo   sudo apt full-upgrade -y
  echo   sudo apt install -y libseccomp2
  echo   sudo reboot
  pause
  exit /b %errorlevel%
)

echo.
echo Deployment finished.
pause
