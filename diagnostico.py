#!/usr/bin/env python3
"""Diagnóstico rápido do OLLAMA"""

import subprocess
import requests
import time

print("="*80)
print("🔍 DIAGNÓSTICO OLLAMA")
print("="*80 + "\n")

# 1. Verificar se OLLAMA está rodando
print("1. Tentando conectar ao OLLAMA...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    print("   ✅ OLLAMA respondendo")

    models = response.json().get('models', [])
    print(f"   Modelos disponíveis: {len(models)}")
    for model in models:
        name = model.get('name', '')
        size = model.get('size', 0) / (1024**3)
        print(f"      - {name} ({size:.1f}GB)")
except:
    print("   ❌ OLLAMA não está respondendo!")
    print("   Inicie com: ollama serve\n")
    exit(1)

# 2. Verificar GPU
print("\n2. Verificando GPU NVIDIA...")
try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
         "--format=csv,nounits,noheader"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        data = result.stdout.strip().split(',')
        print(f"   ✅ GPU: {data[0].strip()}")
        print(f"      Uso: {float(data[1]):.0f}%")
        print(f"      VRAM: {float(data[2]):.0f}MB / {float(data[3]):.0f}MB")
    else:
        print("   ❌ nvidia-smi não funcionou")
except:
    print("   ❌ NVIDIA drivers não instalados")

# 3. Testar Mistral com timeout maior
print("\n3. Testando Mistral (pode demorar...)...")
try:
    print("   Aguardando resposta (120 segundos max)...")
    start = time.time()

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": "2+2=",
            "stream": False,
            "temperature": 0.1
        },
        timeout=120
    )

    elapsed = time.time() - start

    if response.status_code == 200:
        result = response.json()['response'].strip()
        print(f"   ✅ Mistral respondeu em {elapsed:.1f}s")
        print(f"      Resposta: {result[:50]}")
    else:
        print(f"   ❌ Erro HTTP: {response.status_code}")

except requests.Timeout:
    print(f"   ❌ Timeout após 120s - modelo muito lento/pesado")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "="*80)
print("💡 SOLUÇÕES:")
print("="*80)
print("""
Se Mistral está lento:

Opção 1: Usar modelo menor (neural-chat)
  $ ollama pull neural-chat
  (Edite: processar_otimizado_gpu.py, linha 14: MODEL = "neural-chat")

Opção 2: Aumentar timeout no script
  (Edite: processar_otimizado_gpu.py, linha 56: timeout=120)

Opção 3: Verificar se GPU está ativa
  $ nvidia-smi
  (Se GPU Util = 0%, OLLAMA está usando CPU - muito lento!)
  Solução: ollama serve com CUDA_VISIBLE_DEVICES=0

Opção 4: Reiniciar OLLAMA
  Feche o terminal do OLLAMA e inicie novamente:
  $ ollama serve
""")
