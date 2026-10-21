@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] Cai dat thu vien theo requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [2/3] Chay kiem thu...
python -m pytest tests/ -q
if errorlevel 1 goto :failed

echo [3/3] Khoi dong Racket Pro...
python -m streamlit run app/streamlit_app.py
if errorlevel 1 goto :failed
exit /b 0

:failed
echo Khong the hoan tat. Hay xem thong bao loi o tren.
pause
exit /b 1
