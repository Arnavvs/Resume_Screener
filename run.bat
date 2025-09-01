@echo off
REM This script starts the resume screener application.

ECHO Starting Flask Backend Server...
REM The "/B" flag starts the application in the background in a new window.
start "Backend" /B cmd /c ".\venv\Scripts\activate && python app.py"

ECHO Starting Streamlit Frontend Dashboard...
REM This starts the frontend and will open your web browser.
start "Frontend" cmd /c ".\venv\Scripts\activate && streamlit run streamlit_dashboard.py"

ECHO Both servers have been launched.