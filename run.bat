@echo off
title PROCHECK - Proxy Scraper & Checker
echo ========================================================
echo               PROCHECK v2.0 LAUNCHER
echo ========================================================
echo.

if not exist venv (
    echo [!] Virtual environment not found. Creating venv...
    python -m venv venv
    call venv\Scripts\activate
    pip install --upgrade pip
    pip install aiohttp aiohttp-socks fastapi uvicorn requests
) else (
    call venv\Scripts\activate
)

echo.
echo [+] Starting Web UI Server on http://127.0.0.1:8000 ...
echo [+] Opening browser in 3 seconds...
start "" "http://127.0.0.1:8000"

python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

pause
