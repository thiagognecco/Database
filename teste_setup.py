#!/usr/bin/env python3
"""
Teste rápido de setup:
- GPU NVIDIA disponível?
- OLLAMA rodando?
- Mistral carregado?
- RAM suficiente?
"""

import subprocess
import requests
import time
import psutil
from datetime import datetime

print("="*100)
print("🔍 VERIFICAÇÃO DE SETUP - OLLAMA + GPU")
print("="*100 + "\n")

# 1. NVIDIA GPU
print("1️⃣  Verificando GPU NVIDIA...")
try:
    result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        gpu_info = result.stdout.strip().split('\n')[0]
        print(f"   ✅ GPU encontrada: {gpu_info}")
    else:
        print("   ❌ GPU não detectada")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. OLLAMA rodando
print("\n2️⃣  Verificando OLLAMA...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"   ✅ OLLAMA rodando")
        print(f"   Modelos disponíveis: {len(models)}")

        # Procurar Mistral
        mistral_found = False
        for model in models:
            name = model.get('name', '')
            if 'mistral' in name.lower():
                print(f"   ✅ Mistral encontrado: {name}")
                mistral_found = True
                break

        if not mistral_found:
            print(f"   ⚠️  Mistral NÃO encontrado. Modelos: {[m.get('name') for m in models[:3]]}")
    else:
        print(f"   ❌ OLLAMA respondeu com erro: {response.status_code}")
except requests.ConnectionError:
    print("   ❌ OLLAMA não está rodando em localhost:11434")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 3. RAM disponível
print("\n3️⃣  Verificando RAM...")
mem = psutil.virtual_memory()
print(f"   RAM total: {mem.total / (1024**3):.1f}GB")
print(f"   RAM em uso: {mem.used / (1024**3):.1f}GB ({mem.percent}%)")
print(f"   RAM disponível: {mem.available / (1024**3):.1f}GB")

if mem.available > 8:
    print(f"   ✅ RAM suficiente para processar")
else:
    print(f"   ⚠️  RAM baixa (recomendado >8GB disponível)")

# 4. CPU
print("\n4️⃣  Verificando CPU...")
cpu_count = psutil.cpu_count()
print(f"   Cores: {cpu_count}")
print(f"   CPU em uso: {psutil.cpu_percent(interval=1)}%")

# 5. Teste rápido com Mistral
print("\n5️⃣  Teste rápido com Mistral...")
try:
    print("   Enviando request test...")
    start = time.time()

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": "What is 2+2? Answer with ONLY the number.",
            "stream": False,
            "temperature": 0.1
        },
        timeout=120
    )

    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()['response'].strip()
        print(f"   ✅ Mistral respondeu em {elapsed:.1f}s: '{result}'")
    else:
        print(f"   ❌ Mistral erro: {response.status_code}")

except requests.Timeout:
    print(f"   ❌ Timeout (modelo muito grande ou muito lento)")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "="*100)
print("✨ SETUP CHECK COMPLETO")
print("="*100)
print("\n📝 Próximos passos:")
print("   1. Se tudo ✅, execute: python processar_otimizado_gpu.py")
print("   2. Em outro terminal, rode: python monitor_gpu.py")
print("   3. Acompanhe o progresso\n")
