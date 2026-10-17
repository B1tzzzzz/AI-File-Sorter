import ollama
import json
import os
from pydantic import BaseModel, Field
from typing import List


class ImageTags(BaseModel):
    filename: str = Field(description="Имя файла")
    tags: List[str] = Field(description="Список тегов на русском языке")


def analyze_image(file_path: str) -> list:
    filename = os.path.basename(file_path)
    prompt = f"""
    Проанализируй изображение. Верни ответ СТРОГО в формате JSON.
    Имя файла: {filename}
    Выдели 3-5 ключевых тегов на русском языке.
    Пример ответа: {{"filename": "{filename}", "tags": ["сова", "природа", "животное"]}}
    """
    try:
        response = ollama.chat(
            model='qwen2.5vl:7b',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [file_path]
            }],
            format='json'
        )
        result_dict = json.loads(response['message']['content'])
        clean_tags = [tag.strip() for tag in result_dict["tags"]]
        return [filename, clean_tags]
    except Exception as e:
        print(f"Ошибка при обработке {filename}: {e}")
        return [filename, ["ошибка"]]


def process_folder(folder_path: str) -> list:
    final_result = []
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

    files = os.listdir(folder_path)

    for filename in files:
        if filename.lower().endswith(valid_extensions):
            full_path = os.path.join(folder_path, filename)
            print(f"Анализирую {filename}...")
            result = analyze_image(full_path)
            final_result.append(result)

    return final_result


if __name__ == "__main__":
    test_folder = r"C:\Projects\ai-file-sorter\test_images"

    result = process_folder(test_folder)
    print("\n--- ИТОГОВЫЙ РЕЗУЛЬТАТ ДЛЯ СОРТИРОВЩИКА ---")
    print(result)