@echo off
REM ===================================================================
REM  Let other PCs on the local network reach the Assistant (TCP 8731).
REM  RIGHT-CLICK this file and choose "Run as administrator".
REM  You only need to do this once on the HOST PC.
REM ===================================================================

netsh advfirewall firewall add rule name="Operations Assistant" ^
  dir=in action=allow protocol=TCP localport=8731

if errorlevel 1 (
  echo.
  echo Failed to add the firewall rule. Make sure you ran this
  echo file as administrator (right-click -^> Run as administrator).
  pause
  exit /b 1
)

echo.
echo Done. Port 8731 is now open for the local network.
pause
