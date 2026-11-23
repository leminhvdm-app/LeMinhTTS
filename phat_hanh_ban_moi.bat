@echo off
chcp 65001 >nul
title Phát Hành Bản Cập Nhật Mới — LeMinhTTS
cls

echo ================================================================
echo        LEMINHTTS — CÔNG CỤ TỰ ĐỘNG PHÁT HÀNH BẢN MỚI
echo ================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LỖI] Không tìm thấy môi trường ảo .venv\Scripts\python.exe!
    pause
    exit /b 1
)

.venv\Scripts\python.exe scripts\publish_release.py %*

echo.
echo ================================================================
echo Đã hoàn tất quy trình phát hành!
echo ================================================================
pause
