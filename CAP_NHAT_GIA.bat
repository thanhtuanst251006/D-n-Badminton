@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
echo Dang lay danh muc tu ShopVNB, FBShop va HVShop...
python -m racket_rec.live_catalog --pages 10 --details 30
if errorlevel 1 goto :failed
echo Da cap nhat. Tai lai trang Streamlit de xem du lieu moi.
pause
exit /b 0
:failed
echo Khong the hoan tat. Hay xem thong bao loi o tren.
pause
exit /b 1
