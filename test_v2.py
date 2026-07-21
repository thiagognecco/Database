#!/usr/bin/env python3
import json, requests, time

print("Testando Mistral com prompt otimizado...\n")

for i in range(2):
    titulo = "Python" if i == 0 else "Medium Blog"
    url = "python.org" if i == 0 else "medium.com"

    prompt = f"""[INSTRUCTION]
You MUST respond with ONLY valid JSON, nothing else.
Do not explain, do not add text before or after.
Return exactly this format:
{{"cat":"VALUE","tags":["tag1","tag2"],"res":"SUMMARY"}}

[DATA]
Title: {titulo}
URL: {url}

[CATEGORIES]
cat must be ONE of: Tec|IA|Edu|Mark|Neg|Sau|Fin|Jur|Auto|Rec|SAP|Tut|Vid|Art|Fer

Now respond with ONLY the JSON object:"""

    print(f"[{i+1}] Processando: {titulo}...")

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False, "temperature": 0.1},
        timeout=300
    )

    response_text = response.json()['response'].strip()
    print(f"    Resposta bruta: {response_text[:100]}...")

    if "{" in response_text and "}" in response_text:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        json_str = response_text[start:end]

        try:
            resultado = json.loads(json_str)
            print(f"    JSON OK: cat={resultado.get('cat')}, tags={resultado.get('tags')}")
        except:
            print(f"    ERRO parseando JSON")
    else:
        print(f"    ERRO: JSON nao encontrado")

    print()
