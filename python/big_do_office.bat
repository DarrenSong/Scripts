@echo off
chcp 65001 > nul 2>&1  &:: 设置UTF-8编码（防止中文路径/输出乱码）
setlocal enabledelayedexpansion

:: 获取BAT文件自身名称（不含扩展名）
set "script_name=%~n0"

:: 切换到BAT文件所在目录
cd /d "%~dp0"

:: 检查同名Python文件是否存在
if exist "%script_name%.py" (
    echo 正在运行脚本: "%script_name%.py"
    python "%script_name%.py"
    
    :: 检测Python执行状态
    if errorlevel 1 (
        echo [错误] Python脚本执行失败（错误码: %errorlevel%）
        pause
        exit /b 1
    )
) else (
    echo [错误] 未找到文件: "%script_name%.py"
    pause
    exit /b 1
)
