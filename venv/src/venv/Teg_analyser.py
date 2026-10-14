from ollama import chat
import json


def Teg_analyse(programm_path):
    f = open("teg_analyse_prompt.txt", encoding="utf-8")
    with open(programm_path + "/tegs.json", "r") as json_data:
            data = json.load(json_data)
    response = chat(
        model='qwen2.5:7b',
        messages=[
            {'role': 'system', 'content': f.read()},
            {"role": "user", "content": json.dumps(data, ensure_ascii=False)}
        ],
        format="json",
        options={
            "temperature": 0.5,
        }
    )
    roots = response["message"]["content"]
    with open(programm_path + "/new_paths.json", "w") as json_data:
            json.dump(roots, json_data)
    print(roots)
    f.close()
    
Teg_analyse("C:/Users/MSI/Documents/GitHub/AI-File-Sorter/venv/src/venv")