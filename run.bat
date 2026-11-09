@echo off
chcp 65001 >nul
title pc-diag
cd /d "%~dp0"

rem Двойной клик по run.bat открывает графический интерфейс.
if exist "pc-diag.exe" (
  start "" "pc-diag.exe"
  exit /b 0
)

rem Если GUI нет, а консольная сборка есть — работаем как CLI.
if exist "pc-diag-cli.exe" (
  "pc-diag-cli.exe" %*
  pause
  exit /b %errorlevel%
)

rem Запуск из исходников (нужен Python и зависимости из requirements.txt).
if exist "run_gui.py" (
  python run_gui.py
  exit /b %errorlevel%
)

echo Не найден pc-diag.exe рядом с этим файлом.
echo Скачайте portable-сборку целиком и распакуйте в одну папку.
pause
exit /b 1
