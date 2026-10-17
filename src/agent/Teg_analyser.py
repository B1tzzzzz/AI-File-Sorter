from ollama import chat
import json
from pathlib import Path


def Teg_analyse(programm_path):
    base = Path(programm_path)

    with open(base / "teg_analyse_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    with open(base / "tegs.json", "r", encoding="utf-8") as json_data:
        data = json.load(json_data)

    response = chat(
        model='qwen2.5:7b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {"role": "user", "content": json.dumps(data, ensure_ascii=False)}
        ],
        format="json",
        options={
            "temperature": 0.2,
        }
    )

    content = response["message"]["content"]

    try:
        roots = json.loads(content)
    except json.JSONDecodeError:
        roots = content

    with open(base / "new_paths.json", "w", encoding="utf-8") as json_data:
        json.dump(roots, json_data, ensure_ascii=False, indent=2)

    print(json.dumps(roots, ensure_ascii=False, indent=2))


Teg_analyse("C:/Users/MSI/Documents/GitHub/AI-File-Sorter/venv/src/venv")