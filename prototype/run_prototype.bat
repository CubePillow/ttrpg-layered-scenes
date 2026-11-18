@echo off
rem Starts the layer prototype UI at http://127.0.0.1:7870 (set LAYERPROTO_PORT to change it). No model runs on this computer.
rem First time: pip install -r prototype\requirements.txt   and put your Kaggle API credentials in %USERPROFILE%\.kaggle (see docs\guides\kaggle.md).
cd /d "%~dp0.."
if exist "fastsdcpu\env\Scripts\python.exe" ( set "PY=fastsdcpu\env\Scripts\python.exe" ) else ( set "PY=python" )
"%PY%" "prototype\app.py"
pause
