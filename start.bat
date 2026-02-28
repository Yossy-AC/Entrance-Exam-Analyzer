@echo off
chcp 65001 > nul
echo 合格実績分析ダッシュボード を起動中...
echo.
echo ブラウザで http://localhost:8000 を開いてください
echo 停止するには Ctrl+C を押してください
echo.
set PATH=%USERPROFILE%\.local\bin;%PATH%
cd /d %~dp0
uv run uvicorn src.goukaku_analytics.main:app --host 127.0.0.1 --port 8000 --reload
