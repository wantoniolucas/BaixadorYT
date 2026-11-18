@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m pip install --upgrade "yt-dlp[default]"
  if errorlevel 1 goto erro
  py -3 baixador_yt.py
  goto fim
)
python -m pip install --upgrade "yt-dlp[default]"
if errorlevel 1 goto erro
python baixador_yt.py
goto fim
:erro
echo.
echo ERRO: confira se o Python 3.11+ esta instalado e conectado a internet.
pause
:fim
