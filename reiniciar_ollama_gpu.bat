@echo off
echo Parando OLLAMA e Python...
taskkill /IM ollama.exe /F 2>nul
taskkill /IM python.exe /F 2>nul

echo Aguardando 3 segundos...
timeout /t 3 /nobreak

echo.
echo Procurando OLLAMA...

if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_PATH=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    echo Encontrado em AppData
    goto :found
)

if exist "C:\Program Files\Ollama\ollama.exe" (
    set "OLLAMA_PATH=C:\Program Files\Ollama\ollama.exe"
    echo Encontrado em Program Files
    goto :found
)

echo OLLAMA nao encontrado!
echo Instale em: https://ollama.ai
pause
exit /b 1

:found
echo.
echo Iniciando OLLAMA com GPU CUDA...
echo.

set CUDA_VISIBLE_DEVICES=0
set OLLAMA_NUM_GPU=1
set OLLAMA_KEEP_ALIVE=24h

"%OLLAMA_PATH%" serve

pause
