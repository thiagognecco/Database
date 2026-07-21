#!/usr/bin/env python3
"""
Monitor de GPU NVIDIA + RAM durante processamento
Mostra em tempo real enquanto o Mistral roda
"""

import os
import time
import subprocess
import psutil
from datetime import datetime

def get_nvidia_info():
    """Pega info da GPU NVIDIA"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total",
             "--format=csv,nounits,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            data = result.stdout.strip().split(',')
            return {
                'gpu_util': float(data[0]),
                'mem_util': float(data[1]),
                'mem_used_mb': float(data[2]),
                'mem_total_mb': float(data[3])
            }
    except:
        pass
    return None

def get_cpu_info():
    """Pega info de CPU/RAM"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    return {
        'cpu_percent': cpu_percent,
        'ram_percent': mem.percent,
        'ram_used_gb': mem.used / (1024**3),
        'ram_total_gb': mem.total / (1024**3)
    }

def monitor_loop():
    """Loop de monitoramento"""
    print("\n" + "="*100)
    print("🖥️  MONITOR DE SISTEMA - OLLAMA + GPU NVIDIA")
    print("="*100)
    print("(Pressione CTRL+C para parar)\n")

    try:
        while True:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} ", end='')

            # GPU
            gpu_info = get_nvidia_info()
            if gpu_info:
                print(f"| 🎮 GPU: {gpu_info['gpu_util']:.0f}% | ", end='')
                print(f"GPU-RAM: {gpu_info['mem_used_mb']:.0f}MB/{gpu_info['mem_total_mb']:.0f}MB ({gpu_info['mem_util']:.0f}%) | ", end='')
            else:
                print(f"| ⚠️  GPU não detectada | ", end='')

            # CPU/RAM
            cpu_info = get_cpu_info()
            print(f"CPU: {cpu_info['cpu_percent']:.0f}% | ", end='')
            print(f"RAM: {cpu_info['ram_used_gb']:.1f}GB/{cpu_info['ram_total_gb']:.1f}GB ({cpu_info['ram_percent']:.0f}%)", end='')

            # Status OLLAMA
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    print(" | ✅ OLLAMA: OK", end='')
                else:
                    print(" | ❌ OLLAMA: Error", end='')
            except:
                print(" | ❌ OLLAMA: Offline", end='')

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n✋ Monitor parado")
        print("="*100 + "\n")

if __name__ == "__main__":
    monitor_loop()
