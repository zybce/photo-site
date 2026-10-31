@echo off
rem 本地预览：生成页面并起服务，浏览器打开 http://127.0.0.1:8000
rem 关闭本窗口即停止预览。注意：预览开着时不要运行 deploy.bat
cd /d %~dp0
C:\ProgramData\miniconda3\envs\image\python.exe build.py --serve
pause
