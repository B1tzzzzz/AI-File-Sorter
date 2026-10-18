import os
import sys
import json
import re
import ollama

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MODEL_NAME = "qwen2.5:7b"
INDEX_FILE_NAME = "code_index.json"

SUPPORTED_EXTENSIONS = {
    '.py': 'Python',
    '.c': 'C',
    '.cpp': 'C++',
    '.cc': 'C++',
    '.cxx': 'C++',
    '.h': 'C/C++ Header',
    '.hpp': 'C++ Header',
}

SYSTEM_PROMPT = (
    "You are an expert in competitive programming and algorithm analysis. "
    "Your task is to analyze the source code and return ONLY a comma-separated list of specific technical tags in English (lowercase). "
    "Follow these rules strictly:\n"
    "1. LANGUAGE: Always include the language (e.g., c++, python, c).\n"
    "2. ALGORITHMS & DATA STRUCTURES: Identify specific named algorithms or structures (e.g., fenwick tree, 3d fenwick, aho–corasick, dijkstra, trie, segment tree, binary search, dynamic programming).\n"
    "3. DOMAIN: Include the problem domain (e.g., string algorithm, array algorithm, graph theory, math, geometry, sport programming).\n"
    "4. SPECIFICITY: Be as specific as possible. Instead of just 'data structure', use 'fenwick tree'. Instead of 'math', use 'number theory' if applicable.\n"
    "5. FORMAT: Return only the tags, separated by commas. No explanations, no quotes, no extra text.\n"
    "\n"
    "Examples:\n"
    "- For a C++ file with Aho-Corasick: c++, aho–corasick algorithm, string algorithm, trie, sport programming\n"
    "- For a C++ file with 3D prefix sums/Fenwick: c++, 3d fenwick, fenwick tree, array algorithm, data structures, sport programming\n"
    "- For a Python sorting script: python, sorting algorithm, array algorithm, sort"
)

def detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return SUPPORTED_EXTENSIONS.get(ext, None)

def read_code_file(file_path: str) -> str:
    try:
        for encoding in ['utf-8', 'cp1251', 'ascii', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        return "ERROR: Could not read file in any supported encoding."
    except FileNotFoundError:
        return f"ERROR: File not found at '{file_path}'."
    except Exception as e:
        return f"ERROR reading file: {e}"

def analyze_code(file_content: str, language: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Analyze the following {language} source code and return specific technical tags:\n\n"
            f"```\n{file_content}\n```"
        )}
    ]    
    try:
        response = ollama.chat(model=MODEL_NAME, messages=messages, stream=False)
        raw_answer = response['message']['content']
        
        tags = raw_answer.strip().lower()
        tags = re.sub(r'[^a-z0-9,\s\-–]', '', tags)
        tags = re.sub(r'\s*,\s*', ', ', tags)
        tags = re.sub(r'\s+', ' ', tags).strip()
        tags = tags.strip(', ')
        
        return tags
    except Exception as e:
        return f"Error: {e}"

def load_index(directory: str) -> dict:
    index_path = os.path.join(directory, INDEX_FILE_NAME)
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_index(directory: str, index_data: dict):
    index_path = os.path.join(directory, INDEX_FILE_NAME)
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"\n Failed to save index: {e}")

def main():
    file_path = input("Enter path to code file (.py, .c, .cpp, .h, etc.): ").strip().strip('"').strip("'")
    
    if not os.path.exists(file_path):
        print("\n File not found. Check the path.")
        input("Press Enter to exit")
        sys.exit(1)
    
    directory = os.path.dirname(os.path.abspath(file_path))
    file_name = os.path.basename(file_path)
    
    language = detect_language(file_path)
    if language is None:
        ext = os.path.splittext(file_path)[1].lower()
        print(f"\n Unsupported file extension: '{ext}'")
        print(f"    Supported: {', '.join(SUPPORTED_EXTENSIONS.keys())}")
        input("Press Enter to exit")
        sys.exit(1)
    
    print(f"\n Language: {language}")
    print("Reading file")
    code_content = read_code_file(file_path).strip()
    
    if code_content.startswith("ERROR"):
        print(f"\n {code_content}")
        input("Press Enter to exit")
        sys.exit(1)
    
    if len(code_content) < 50:
        print("\n File too short for quality analysis (< 50 characters)")
        input("Press Enter to exit")
        sys.exit(1)

    lines = code_content.split('\n')
    loc = len([l for l in lines if l.strip()])

    if len(code_content) > 40000:
        print(f"\n File is very large ({loc} lines)")
    else:
        print(f" File read: {loc} lines of code, {len(code_content)} characters")
    
    print("[*] AI is identifying specific algorithms and structures")
    tags = analyze_code(code_content, language)
    
    if tags.startswith("Error"):
        print(f"\n[!] {tags}")
        input("Press Enter to exit")
        sys.exit(1)

    print(f"\n Tags: {tags}")
    
    index_data = load_index(directory)
    index_data[file_name] = tags
    save_index(directory, index_data)
    
    print(f"\n Result added to index: {os.path.join(directory, INDEX_FILE_NAME)}")
    input("\n Press Enter to exit")

if __name__ == "__main__":
    try:
        ollama.list()
    except Exception:
        print("ERROR: Could not connect to Ollama")
        input("Press Enter to exit")
        sys.exit(1)
        
    main()
