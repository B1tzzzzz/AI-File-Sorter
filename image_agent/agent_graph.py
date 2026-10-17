import ollama
import json
import os
import tempfile
from PIL import Image
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    file_path: str
    filename: str
    tags: List[str]


def prepare_image_for_vlm(file_path: str, max_size: tuple = (1024, 1024)) -> str:
    try:
        with Image.open(file_path) as img:
            img_format = img.format.lower() if img.format else 'jpeg'
            if img_format not in ['jpeg', 'png', 'webp']:
                img_format = 'jpeg'

            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P') and img_format == 'jpeg':
                img = img.convert('RGB')

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{img_format}")
            img.save(temp_file.name, format=img_format.upper() if img_format != 'jpg' else 'JPEG')
            return temp_file.name
    except Exception as e:
        print(f"[Предупреждение] Не удалось уменьшить изображение: {e}")
        return file_path


def analyze_image_node(state: AgentState):
    print(f"[Node: Analyze] Анализирую {state['filename']}...")

    prompt = f"""
    Проанализируй изображение. Верни ответ СТРОГО в формате JSON.
    Имя файла: {state['filename']}
    Выдели 3-5 ключевых тегов на русском языке.
    Пример ответа: {{"filename": "{state['filename']}", "tags": ["сова", "природа"]}}
    """

    temp_image_path = prepare_image_for_vlm(state['file_path'])

    try:
        response = ollama.chat(
            model='qwen2.5vl:7b',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [temp_image_path]
            }],
            format='json',
            options={
                "num_ctx": 8192
            }
        )
        result_dict = json.loads(response['message']['content'])
        clean_tags = [tag.strip() for tag in result_dict.get("tags", [])]
        return {"tags": clean_tags}

    except Exception as e:
        print(f"Ошибка в узле для {state['filename']}: {e}")
        return {"tags": ["ошибка"]}

    finally:
        if temp_image_path != state['file_path'] and os.path.exists(temp_image_path):
            os.remove(temp_image_path)


workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_image_node)
workflow.add_edge(START, "analyze")
workflow.add_edge("analyze", END)
image_agent_app = workflow.compile()


def process_folder(folder_path: str):
    final_result = []
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

    files = os.listdir(folder_path)

    for filename in files:
        if filename.lower().endswith(valid_extensions):
            full_path = os.path.join(folder_path, filename)

            initial_state = {
                "file_path": full_path,
                "filename": filename,
                "tags": []
            }

            final_state = image_agent_app.invoke(initial_state)

            final_result.append([final_state['filename'], final_state['tags']])

    return final_result


if __name__ == "__main__":
    test_folder = r"C:\Projects\ai-file-sorter\test_images"

    print("Запускаю обработку папки через LangGraph...")
    final_result = process_folder(test_folder)

    print("\n--- ИТОГОВЫЙ РЕЗУЛЬТАТ ДЛЯ СОРТИРОВЩИКА ---")
    print(final_result)