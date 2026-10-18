import ollama
import json
import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    file_path: str
    filename: str
    tags: List[str]


def analyze_text_node(state: AgentState):
    print(f"[Node: Analyze] Analyzing {state['filename']}...")

    try:
        with open(state['file_path'], 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(state['file_path'], 'r', encoding='cp1251', errors='ignore') as f:
            content = f.read()

    content_snippet = content[:4000]

    prompt = f"""
    Analyze the following text document. Return the answer STRICTLY in JSON format.
    Filename: {state['filename']}
    Extract 3-5 key tags summarizing the topic, content, and document type. 
    ALL TAGS MUST BE IN ENGLISH (e.g., "recipe", "notes", "article", "finance").

    TEXT CONTENT:
    {content_snippet}

    Example: {{"filename": "{state['filename']}", "tags": ["recipe", "food", "cooking"]}}
    """

    try:
        response = ollama.chat(
            model='qwen2.5vl:7b',
            messages=[{
                'role': 'user',
                'content': prompt
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


workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_text_node)
workflow.add_edge(START, "analyze")
workflow.add_edge("analyze", END)
text_agent_app = workflow.compile()


def process_text_folder(folder_path: str):
    final_result = {}
    valid_extensions = ('.txt', '.md', '.csv', '.log') 

    files = os.listdir(folder_path)

    for filename in files:
        if filename.lower().endswith(valid_extensions):
            full_path = os.path.join(folder_path, filename)

            initial_state = {
                "file_path": full_path,
                "filename": filename,
                "tags": []
            }

            final_state = text_agent_app.invoke(initial_state)
            final_result[final_state['filename']] = final_state['tags']

    json_output = json.dumps(final_result, indent=4, ensure_ascii=False)

    with open("text_results.json", "w", encoding="utf-8") as f:
        f.write(json_output)

    return json_output


if __name__ == "__main__":
    test_folder = r"C:\Projects\ai-file-sorter\test_texts"

    if not os.path.exists(test_folder):
        os.makedirs(test_folder)
        print(f"Создана пустая папка {test_folder}.")

    print("Starting text folder processing...")
    final_json = process_text_folder(test_folder)

    print("\n--- FINAL JSON FOR ORCHESTRATOR ---")
    print(final_json)
    print("\n[Success] Result saved to text_results.json!")