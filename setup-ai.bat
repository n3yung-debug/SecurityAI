@echo off
REM ===================================================================
REM  One-time setup of the free local-AI engine on the HOST PC.
REM  Run this once on the machine that hosts Operations Assistant.
REM ===================================================================

where ollama >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Ollama is not installed yet.
  echo  1^) Download it ^(free^) from:  https://ollama.com/download
  echo  2^) Install it, then run this script again.
  echo.
  pause
  exit /b 1
)

echo Installing the answer-writing model (llama3.1:8b)...
echo This is a one-time download of several GB. Please wait.
ollama pull llama3.1:8b || goto :error

echo.
echo Installing the smart-search model (nomic-embed-text)...
ollama pull nomic-embed-text || goto :error

echo.
echo ============================================================
echo  Local AI is ready.
echo  Start OperationsAssistant.exe -- it detects the models
echo  automatically and the header will show "Local AI: On".
echo ============================================================
echo.
echo  Want higher quality and have a strong GPU? You can also try:
echo      ollama pull llama3.1:70b
echo  then set OA_CHAT_MODEL=llama3.1:70b before launching.
pause
goto :eof

:error
echo.
echo Something went wrong pulling the models. Check your internet
echo connection and that Ollama is running, then try again.
pause
exit /b 1
