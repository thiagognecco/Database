# Script para iniciar OLLAMA com GPU

Write-Host "Procurando OLLAMA..." -ForegroundColor Cyan

# Procurar em locais comuns
$paths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "C:\Program Files\Ollama\ollama.exe",
    "C:\Program Files (x86)\Ollama\ollama.exe"
)

$ollama_path = $null

foreach ($path in $paths) {
    if (Test-Path $path) {
        $ollama_path = $path
        Write-Host "Encontrado: $path" -ForegroundColor Green
        break
    }
}

if (-not $ollama_path) {
    Write-Host "OLLAMA nao encontrado!" -ForegroundColor Red
    Write-Host "Instale de: https://ollama.ai" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Parando OLLAMA anterior..." -ForegroundColor Yellow
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Iniciando OLLAMA com GPU..." -ForegroundColor Cyan
Write-Host ""

$env:CUDA_VISIBLE_DEVICES = "0"
$env:OLLAMA_NUM_GPU = "1"
$env:OLLAMA_KEEP_ALIVE = "24h"

& $ollama_path serve
