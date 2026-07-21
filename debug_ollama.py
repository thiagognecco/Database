#!/usr/bin/env python3
"""Debug - ver resposta bruta do Ollama"""

import requests
import json

prompt = "Titulo: Python\nURL: python.org\n\nJSON: {\"cat\":\"Tec\",\"tags\":[\"prog\"],\"res\":\"linguagem\"}"

print("Enviando prompt para Ollama...")
print(f"Prompt:\n{prompt}\n")

response = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "mistral", "prompt": prompt, "stream": False, "temperature": 0.2},
    timeout=300
)

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Content (primeiros 500 chars):\n{response.text[:500]}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"\nJSON parseado:\n{json.dumps(data, indent=2)[:500]}")
    except Exception as e:
        print(f"Erro ao parsear JSON: {e}")
