@echo off
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller "yt-dlp[default]"
if errorlevel 1 goto erro
py -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all yt_dlp --name BaixadorYT baixador_yt.py
if errorlevel 1 goto erro
echo.
echo EXE gerado na pasta dist\BaixadorYT.exe
pause
goto fim
:erro
echo Erro ao gerar executavel. Confira a instalacao do Python e do pip.
pause
:fim
