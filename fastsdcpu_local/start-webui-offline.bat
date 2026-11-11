@echo off
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set GRADIO_ANALYTICS_ENABLED=False
set PATH=%PATH%;%~dp0env\Lib\site-packages\openvino\libs
call "%~dp0env\Scripts\activate.bat" && python "%~dp0src\app.py" -w
