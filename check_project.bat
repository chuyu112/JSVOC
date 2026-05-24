@echo off
chcp 65001 >nul
title 检查 D:\JPASP 项目文件

set ROOT=D:\JPASP
set REPORT=%ROOT%\project_check_report.txt

echo =======================================
echo 正在检查项目目录：%ROOT%
echo =======================================
echo.

if not exist "%ROOT%" (
    echo [错误] 目录不存在：%ROOT%
    pause
    exit /b
)

echo AI短视频项目文件检查报告 > "%REPORT%"
echo 检查目录：%ROOT% >> "%REPORT%"
echo 检查时间：%date% %time% >> "%REPORT%"
echo. >> "%REPORT%"

echo.
echo ========== 检查基础目录 ==========
echo ========== 检查基础目录 ========== >> "%REPORT%"

call :check_dir "%ROOT%\docs"
call :check_dir "%ROOT%\frontend"
call :check_dir "%ROOT%\backend"

echo.
echo ========== 检查根目录文件 ==========
echo ========== 检查根目录文件 ========== >> "%REPORT%"

call :check_file "%ROOT%\AGENTS.md"
call :check_file "%ROOT%\README.md"
call :check_file "%ROOT%\.env.example"
call :check_file "%ROOT%\docker-compose.yml"

echo.
echo ========== 检查 docs 文档 ==========
echo ========== 检查 docs 文档 ========== >> "%REPORT%"

call :check_file "%ROOT%\docs\PRD.md"
call :check_file "%ROOT%\docs\ARCHITECTURE.md"
call :check_file "%ROOT%\docs\API_SPEC.md"
call :check_file "%ROOT%\docs\DB_SCHEMA.md"
call :check_file "%ROOT%\docs\TASKS.md"
call :check_file "%ROOT%\docs\ACCEPTANCE.md"

echo.
echo ========== 检查前端 Vue 项目 ==========
echo ========== 检查前端 Vue 项目 ========== >> "%REPORT%"

call :check_file "%ROOT%\frontend\package.json"
call :check_file "%ROOT%\frontend\index.html"
call :check_file "%ROOT%\frontend\vite.config.ts"
call :check_dir "%ROOT%\frontend\src"
call :check_file "%ROOT%\frontend\src\main.ts"
call :check_file "%ROOT%\frontend\src\App.vue"

echo.
echo ========== 检查后端 FastAPI 项目 ==========
echo ========== 检查后端 FastAPI 项目 ========== >> "%REPORT%"

call :check_file "%ROOT%\backend\requirements.txt"
call :check_file "%ROOT%\backend\Dockerfile"
call :check_dir "%ROOT%\backend\app"
call :check_file "%ROOT%\backend\app\main.py"

echo.
echo ========== 检查 Git ==========
echo ========== 检查 Git ========== >> "%REPORT%"

call :check_dir "%ROOT%\.git"

echo.
echo =======================================
echo 检查完成
echo 报告文件：%REPORT%
echo =======================================
echo.

notepad "%REPORT%"

pause
exit /b


:check_file
if exist %1 (
    echo [OK] 文件存在：%~1
    echo [OK] 文件存在：%~1 >> "%REPORT%"
) else (
    echo [缺失] 文件不存在：%~1
    echo [缺失] 文件不存在：%~1 >> "%REPORT%"
)
exit /b


:check_dir
if exist %1 (
    echo [OK] 目录存在：%~1
    echo [OK] 目录存在：%~1 >> "%REPORT%"
) else (
    echo [缺失] 目录不存在：%~1
    echo [缺失] 目录不存在：%~1 >> "%REPORT%"
)
exit /b