@echo off
cd /d "%~dp0"
echo Starting QueueLess at http://127.0.0.1:8000/
.venv\Scripts\python.exe -m flask --app run.py db upgrade
.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:8000 run:app
