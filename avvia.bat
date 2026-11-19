@echo off
rem Avvio rapido del Claude Monitor.
rem   avvia.bat            monitor collegato al mod
rem   avvia.bat --demo     eventi finti
rem   avvia.bat --festa christmas
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Prima volta: creo il venv e installo le dipendenze...
    python -m venv .venv || goto :errore
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :errore
)

rem pythonw = niente console; start = il .bat esce subito e chiude la finestra.
rem Per vedere gli errori: .venv\Scripts\python.exe src\monitor.py
start "" ".venv\Scripts\pythonw.exe" src\monitor.py %*
exit /b 0

:errore
echo.
echo Qualcosa e' andato storto (vedi sopra).
pause
exit /b 1
