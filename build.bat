@echo off
REM ===================================================================
REM  Build the Operations Assistant into a single Windows .exe.
REM  Run this on a Windows PC that has Python 3.11+ installed.
REM ===================================================================

echo Creating a clean virtual environment...
python -m venv build-env || goto :error
call build-env\Scripts\activate.bat || goto :error

echo Installing dependencies...
python -m pip install --upgrade pip || goto :error
pip install -r requirements.txt || goto :error
pip install pyinstaller==6.10.0 || goto :error

echo Building the executable (this can take a few minutes)...
pyinstaller --noconfirm --clean OperationsAssistant.spec || goto :error

echo.
echo ============================================================
echo  Done! Your program is here:
echo      dist\OperationsAssistant.exe
echo  Double-click it to run.
echo ============================================================
goto :eof

:error
echo.
echo Build failed. See the messages above.
exit /b 1
