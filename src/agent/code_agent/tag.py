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
        tags = re.sub(r'[^a-z0-9,\s\-–+]', '', tags)
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

def collect_code_files(directory: str) -> list:
    files = []
    for entry in os.scandir(directory):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(entry.path)
    return sorted(files)

def process_single_file(file_path: str, index_data: dict, skip_existing: bool = True) -> bool:
    file_name = os.path.basename(file_path)
    
    if skip_existing and file_name in index_data:
        print(f"  [skip] {file_name} (already in index)")
        return False
    
    language = detect_language(file_path)
    if language is None:
        print(f"  [skip] {file_name} (unsupported extension)")
        return False
    
    code_content = read_code_file(file_path).strip()
    
    if code_content.startswith("ERROR"):
        print(f"  [error] {file_name}: {code_content}")
        return False
    
    if len(code_content) < 50:
        print(f"  [skip] {file_name} (too short)")
        return False
    
    lines = code_content.split('\n')
    loc = len([l for l in lines if l.strip()])
    
    print(f"  [analyze] {file_name} ({language}, {loc} lines)...", end=" ", flush=True)
    
    tags = analyze_code(code_content, language)
    
    if tags.startswith("Error"):
        print(f"ERROR: {tags}")
        return False
    
    print(f"OK")
    print(f"Tags: {tags}")
    
    index_data[file_name] = tags
    return True

def main():
    directory = input("Enter path to directory with code files: ").strip().strip('"').strip("'")
    
    if not os.path.exists(directory):
        print("\n Directory not found")
        input("Press Enter to exit")
        sys.exit(1)
    
    if not os.path.isdir(directory):
        print("\n Specified path is not a directory")
        input("Press Enter to exit")
        sys.exit(1)
    
    files = collect_code_files(directory)
    
    if not files:
        print(f"\n No supported files found in '{directory}'")
        print(f"    Supported extensions: {', '.join(SUPPORTED_EXTENSIONS.keys())}")
        input("Press Enter to exit")
        sys.exit(1)
    
    print(f"\n Found {len(files)} file(s) with supported extensions")
    
    index_data = load_index(directory)
    if index_data:
        print(f" Existing index loaded: {len(index_data)} file(s) already processed")
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, file_path in enumerate(files, 1):
        file_name = os.path.basename(file_path)
        print(f"\n[{i}/{len(files)}] Processing: {file_name}")
        
        if file_name in index_data:
            print(f"  [skip] Already in index")
            skipped_count += 1
            continue
        
        language = detect_language(file_path)
        code_content = read_code_file(file_path).strip()
        
        if code_content.startswith("ERROR"):
            print(f"  [error] {code_content}")
            error_count += 1
            continue
        
        if len(code_content) < 50:
            print(f"  [skip] File too short (< 50 characters)")
            skipped_count += 1
            continue
        
        lines = code_content.split('\n')
        loc = len([l for l in lines if l.strip()])
        
        print(f"  Language: {language} | Lines: {loc} | Size: {len(code_content)} chars")
        print(f"  Analyzing...", end=" ", flush=True)
        
        tags = analyze_code(code_content, language)
        
        if tags.startswith("Error"):
            print(f"ERROR: {tags}")
            error_count += 1
            continue
        
        print(f"  Tags: {tags}")
        
        index_data[file_name] = tags
        processed_count += 1
        save_index(directory, index_data)
    
    print("\n" + "="*60)
    print(f"  Total files found : {len(files)}")
    print(f"  Processed         : {processed_count}")
    print(f"  Skipped           : {skipped_count}")
    print(f"  Errors            : {error_count}")
    print(f"  Total in index    : {len(index_data)}")
    print(f"  Index saved to    : {os.path.join(directory, INDEX_FILE_NAME)}")
    print("="*60)
    
    input("\n Press Enter to exit")

if __name__ == "__main__":
    try:
        ollama.list()
    except Exception:
        print("ERROR: Could not connect to Ollama")
        input("Press Enter to exit")
        sys.exit(1)
        
    main()
