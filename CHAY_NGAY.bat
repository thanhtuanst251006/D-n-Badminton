@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo   1. DANG CAI DAT THU VIEN TUONG THICH PYTHON...
echo ===================================================
python -m pip install --only-binary=:all: pandas numpy scikit-learn streamlit plotly requests beautifulsoup4 pytest ruff

echo.
echo ===================================================
echo   2. CHAY KIEM THU UNIT TEST (PYTEST)...
echo ===================================================
python -m pytest tests/

echo.
echo ===================================================
echo   3. KHOI DONG GIAO DIEN WEB STREAMLIT...
echo ===================================================
python -m streamlit run app/streamlit_app.py
pause
