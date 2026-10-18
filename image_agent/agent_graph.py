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
        print(f"[Warning] Failed to resize image: {e}")
        return file_path


def analyze_image_node(state: AgentState):
    print(f"[Node: Analyze] Analyzing {state['filename']}...")

    prompt = f"""
    Analyze the image. Return the answer STRICTLY in JSON format.
    Filename: {state['filename']}
    Extract 3-5 key tags. ALL TAGS MUST BE IN ENGLISH.
    Example: {{"filename": "{state['filename']}", "tags": ["owl", "nature", "bird"]}}
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
            keep_alive="1h"
        )
        result_dict = json.loads(response['message']['content'])
        clean_tags = [tag.strip().lower() for tag in result_dict.get("tags", [])]
        return {"tags": clean_tags}

    except Exception as e:
        print(f"Error in node for {state['filename']}: {e}")
        return {"tags": ["error"]}

    finally:
        if temp_image_path != state['file_path'] and os.path.exists(temp_image_path):
            os.remove(temp_image_path)


workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_image_node)
workflow.add_edge(START, "analyze")
workflow.add_edge("analyze", END)
image_agent_app = workflow.compile()


def process_folder(folder_path: str):
    final_result = {}
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

            final_result[final_state['filename']] = final_state['tags']

    json_output = json.dumps(final_result, indent=4, ensure_ascii=False)

    with open("results.json", "w", encoding="utf-8") as f:
        f.write(json_output)

    return json_output


if __name__ == "__main__":
    test_folder = r"C:\Projects\ai-file-sorter\test_images"

    print("Starting folder processing via LangGraph...")
    final_json = process_folder(test_folder)

    print("\n--- FINAL JSON FOR ORCHESTRATOR ---")
    print(final_json)
    print("\n[Success] Result saved to results.json!")