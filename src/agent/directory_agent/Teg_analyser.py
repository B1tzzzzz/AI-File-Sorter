import re
import json
import time
from pathlib import Path
from collections import Counter, defaultdict
from ollama import Client

BATCH_SIZE = 15
TREE_FILE_BATCH = 8
MAX_FIX_ROUNDS = 2
MAX_TREE_ROUNDS = 3
ENABLE_TREE_REBUILD = False
CLIENT_TIMEOUT = 300.0
JSON_ARRAY_SCHEMA = {"type": "array", "items": {"type": "string"}}
JSON_OBJECT_SCHEMA = {"type": "object"}
DUP_PREFIX_LEN = 4

MAX_PARTS = 6            # 5 папок + файл (было 5)
SPLIT_THRESHOLD = 5      # разбиваем папки с >5 файлов

NUM_PREDICT_SORTER = 2500
NUM_PREDICT_STRUCT = 1000
NUM_PREDICT_FILES = 500
NUM_PREDICT_REBUILD = 3500
NUM_CTX = 4096


# ════════════════════════════════════════════════════════════════
#  ДЕТЕРМИНИРОВАННЫЙ КЛАССИФИКАТОР — fallback для Other/Unsorted
# ════════════════════════════════════════════════════════════════
TAG_RULES = [
    (r"kitten|\bcat\b|cats|feline", "Animals/Cats"),
    (r"primate|chimpanzee|monkey|ape", "Animals/Primates"),
    (r"owl|bird|eagle|parrot", "Animals/Birds"),
    (r"wildlife|\banimal\b|\blion\b|\btiger\b|leopard|squirrel|wolf|wolves|fox",
     "Animals/Wildlife"),
    (r"hamburger|cheeseburger|burger|fast food", "Food/FastFood"),
    (r"dessert|cake|sweet|snack", "Food/Desserts"),
    (r"blueberr|fruit|apple|banana|berry", "Food/Fruit"),
    (r"nutrition|healthy food|dietary|bowl", "Food/Nutrition"),
    (r"\bcar\b|sports car|classic car|vehicle|truck|suv", "Vehicles/Cars"),
    (r"error|bios|blue screen|hardware|\bcpu\b|\bgpu\b|motherboard",
     "Technology/Hardware"),
    (r"cursor|mouse pointer|\bui\b|\bux\b|interface|button", "Technology/UI"),
    (r"security|vulnerab|threat|malware", "Technology/Security"),
    (r"network|routing|traffic|\btcp\b|\bip\b|protocol", "Technology/Networks"),
    (r"\bphp\b|wordpress|html|\bcss\b", "Technology/Web"),
    (r"troubleshoot|technical|windows|diagnos", "Technology/Troubleshooting"),
    (r"queue|buffer|stack|waiting", "Technology/Computing"),
    (r"document|layout|\btext\b|word|pdf", "Documents"),
    (r"literature|novel|\bplay\b|poem|story|fiction|description|setting",
     "Literature"),
    (r"dictionary|definition|language", "Language"),
    (r"islam|religion", "History/Religion"),
    (r"biography|soviet history|political figure", "History/Biography"),
    (r"politics|diplomacy|policy|government|international relation", "Politics"),
    (r"history|historical|medieval", "History"),
    (r"geology|volcanic|lava|rock", "Nature/Geology"),
    (r"night sky|moonlight|moon|stars|sunset", "Nature/NightSky"),
    (r"autumn|fall foliage|season", "Nature/Autumn"),
    (r"landscape|mountain|forest|lake|river|reflection|sky|snow",
     "Nature/Landscape"),
    (r"nature|serenity|spring|flowers", "Nature"),
    (r"city geography|waterway|urban infrastructure|street", "Urban/Streets"),
    (r"urban|citect|tourism|population|administration", "Urban"),
    (r"cartoon|character|avatar|red hair|t-shirt|pointing", "Art/Cartoons"),
    (r"video game|gaming|esports", "Games/Esports"),
    (r"meeting|agenda|action items|report", "Work/Meetings"),
    (r"travel|vacation|sightseeing|trip|cruise", "Travel"),
    (r"construction|materials|concrete", "Construction/Materials"),
]


# ════════════════════════════════════════════════════════════════
#  ПРАВИЛА СПЛИТА — двух-уровневая структура
#  Порядок КРИТИЧЕН: специфичные выше общих
# ════════════════════════════════════════════════════════════════
SPLIT_RULES = [
    # NLP — выше ML, потому что у orkestrator есть и "graph theory"
    (r"natural language processing|\bnlp\b|langchain|chatbot|\bllm\b|"
     r"chatgpt|openai",
     "MachineLearning/NLP"),
    # ML/Regression — специфичнее общего ML
    (r"linear.?regression|logistic regression|regression analysis",
     "MachineLearning/Regression"),
    # ML/NeuralNetworks
    (r"neural network|\bneural\b|\bcnn\b|\brnn\b|\btransformer\b|deep learning",
     "MachineLearning/NeuralNetworks"),
    # ML/DataAnalysis — специфичные библиотеки
    (r"data analysis|data cleaning|data visualization|correlation|heatmap|"
     r"numpy|pandas|matplotlib|seaborn|dataframe",
     "MachineLearning/DataAnalysis"),
    # ML — общий
    (r"machine learning|supervised learning|unsupervised", "MachineLearning"),

    # DataStructures/Trees
    (r"avl tree|segment tree|binary search tree|red.black tree|"
     r"tree algorithm|binary tree", "DataStructures/Trees"),
    # DataStructures/UnionFind
    (r"\bdsu\b|union.find|disjoint set", "DataStructures/UnionFind"),

    # Algorithms/Graphs — ВЫШЕ DataStructures/Sets
    (r"graph theory|\bdfs\b|\bbfs\b|undirected graph|directed graph|"
     r"connected components|topological|dijkstra|bfs|dfs|shortest path",
     "Algorithms/Graphs"),
    # Algorithms/DynamicProgramming
    (r"dynamic programming|\bdp\b|memoization", "Algorithms/DynamicProgramming"),
    # Algorithms/Sorting
    (r"sorting algorithm|merge sort|quick sort|bubble sort|insertion sort|"
     r"heap sort|counting sort|radix sort|pseudo sorting", "Algorithms/Sorting"),
    # Algorithms/BinarySearch
    (r"binary search|quick select|lower bound|upper bound", "Algorithms/BinarySearch"),
    # Algorithms/Strings
    (r"string algorithm|hash function|\bkmp\b|\btrie\b|suffix array|"
     r"string matching", "Algorithms/Strings"),
    # Algorithms/Greedy
    (r"greedy", "Algorithms/Greedy"),
    # Algorithms/Math
    (r"number theory|modular arithmetic|prime number|binary.?exponentiation|"
     r"quadratic equation|floating point comparison|numerical stability|"
     r"integer division|\bmath\b|\barithmetic\b|\bstatistics\b",
     "Algorithms/Math"),

    # DataStructures/Sets — ниже Graphs
    (r"ordered set|unordered set|hash set|std::set|std::unordered_set|\bset\b",
     "DataStructures/Sets"),
    # DataStructures/Arrays
    (r"linked list|priority queue|\barraylist\b|\bstack\b|\bdeque\b",
     "DataStructures/Arrays"),
    # DataStructures — общий
    (r"data structure", "DataStructures"),

    # Algorithms — общий
    (r"\balgorithm\b", "Algorithms"),

    # Testing
    (r"testing|checker|comparison|numba|subprocess", "Testing"),
    # MemoryManagement
    (r"memory management|memory allocation|universal swap|shift operation",
     "MemoryManagement"),
    # Web
    (r"web development|\bhtml\b|\bcss\b|javascript|\bphp\b|wordpress", "Web"),
]

LANGUAGE_MAP = {
    ".c": "C", ".h": "C",
    ".cpp": "Cpp", ".cc": "Cpp", ".cxx": "Cpp", ".hpp": "Cpp",
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript", ".ts": "TypeScript",
    ".rs": "Rust", ".go": "Go", ".rb": "Ruby",
    ".cs": "CSharp", ".php": "PHP",
    ".html": "HTML", ".css": "CSS",
}

CODE_EXTENSIONS = set(LANGUAGE_MAP.keys()) | {".sql", ".sh", ".bat", ".ps1"}


def classify_by_tags(tags):
    if not tags:
        return None
    text = " ".join(tags).lower()
    for pattern, category in TAG_RULES:
        if re.search(pattern, text):
            return category
    return None


def classify_by_split_rules(tags):
    """Возвращает подкатегорию (например, 'Algorithms/Sorting') или None."""
    if not tags:
        return None
    text = " ".join(tags).lower()
    for pattern, subfolder in SPLIT_RULES:
        if re.search(pattern, text):
            return subfolder
    return None


def language_subfolder(fname):
    return LANGUAGE_MAP.get(Path(fname).suffix.lower())


def _is_code_file(fname):
    return Path(fname).suffix.lower() in CODE_EXTENSIONS


# ════════════════════════════════════════════════════════════════
#  Утилиты
# ════════════════════════════════════════════════════════════════
def _normalize_for_match(s):
    return "".join(c for c in s.lower() if c.isalnum() or c == ".")


def collapse_duplicate_folders(folders, prefix_len=DUP_PREFIX_LEN):
    out = []
    for f in folders:
        if out:
            prev, cur = out[-1].lower(), f.lower()
            if (len(prev) >= prefix_len and len(cur) >= prefix_len
                    and prev[:prefix_len] == cur[:prefix_len]):
                continue
        out.append(f)
    return out or ["Other"]


def validate_paths(paths, expected_files, tegs=None):
    if not isinstance(paths, list):
        return False, f"Not a list: {type(paths).__name__}"
    if len(paths) != len(expected_files):
        return False, f"Expected {len(expected_files)}, got {len(paths)}"
    seen = set()
    for p in paths:
        if not isinstance(p, str):
            return False, f"Non-string: {p!r}"
        if p.startswith(("/", "./", "../", "~")):
            return False, f"Absolute: {p!r}"
        parts = p.split("/")
        if len(parts) < 2:
            return False, f"No folder: {p!r}"
        if len(parts) > MAX_PARTS:
            return False, f"Too deep: {p!r}"
        for folder in parts[:-1]:
            if " " in folder:
                return False, f"Space in folder: {folder!r}"
            if not re.fullmatch(r"[A-Za-z0-9_]+", folder):
                return False, f"Bad folder: {folder!r}"
        fn = parts[-1]
        if fn not in expected_files:
            return False, f"Unknown file: {fn!r}"
        if fn in seen:
            return False, f"Duplicate: {fn!r}"
        seen.add(fn)
        if parts[0] == "Unsorted" and tegs and tegs.get(fn):
            return False, f"Unsorted for tagged file: {fn!r}"
    missing = expected_files - seen
    if missing:
        return False, f"Missing: {sorted(missing)}"
    return True, ""


def _repair_batch(paths, expected_files):
    expected_list = list(expected_files)
    exact = {f: f for f in expected_list}
    fuzzy = {_normalize_for_match(f): f for f in expected_list}
    result = {}
    for p in paths or []:
        if not isinstance(p, str):
            continue
        p = p.strip().rstrip("/")
        if "/" not in p:
            continue
        parts = p.split("/")
        last = parts[-1]
        matched = exact.get(last) or fuzzy.get(_normalize_for_match(last))
        if matched is None or matched in result:
            continue
        folders = [re.sub(r"\s+", "", f) for f in parts[:-1] if f.strip()]
        folders = [re.sub(r'[\\/:*?"<>|]', "", f) or "Other" for f in folders]
        folders = collapse_duplicate_folders(folders)
        result[matched] = "/".join(folders + [matched])
    for f in expected_list:
        if f not in result:
            result[f] = f"Other/{f}"
    return result


def _safe_dump(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _timed_print(start, suffix=""):
    elapsed = time.time() - start
    print(f" {elapsed:.1f}s{suffix}")


# ════════════════════════════════════════════════════════════════
#  ПОСТПРОЦЕССИНГ: принудительная правильная структура для кода
#  Работает НАД результатом модели — перекладывает ВСЕ файлы кода
# ════════════════════════════════════════════════════════════════
def _refine_programming_paths(all_paths_map, tegs):
    """
    Проходит по ВСЕМ файлам кода. Применяет SPLIT_RULES к тегам.
    Если правило даёт путь — ставит его. Иначе — по языку.
    Гарантирует, что модель не оставит код в "Technology/UI/" или
    "Technology/Programming/Sorting/" без Algorithms.
    """
    moved = 0
    for fname in list(all_paths_map.keys()):
        if not _is_code_file(fname):
            continue

        tags = tegs.get(fname, [])
        target = classify_by_split_rules(tags)
        if not target:
            lang = language_subfolder(fname)
            target = f"Other/{lang}" if lang else "Other"
        else:
            target = target  # например "Algorithms/Sorting"

        expected = f"Technology/Programming/{target}/{fname}"

        # Проверка глубины
        if len(expected.split("/")) > MAX_PARTS:
            # Слишком глубоко — упростим: только первый уровень target
            first = target.split("/")[0]
            expected = f"Technology/Programming/{first}/{fname}"

        current = all_paths_map[fname]
        if current == expected:
            continue
        # Уже в правильной подкатегории (или глубже) — не трогаем
        if current.startswith(f"Technology/Programming/{target}/"):
            continue

        old = current
        all_paths_map[fname] = expected
        moved += 1
        if moved <= 15:
            print(f"    refine {old} → {expected}")

    print(f"  [refine] переложено файлов кода: {moved}")
    return moved


def _split_oversized_folders(all_paths_map, tegs, threshold=SPLIT_THRESHOLD):
    """Добивает случаи, когда папка большая, а refine не сработал (не код)."""
    by_folder = defaultdict(list)
    for fname, path in all_paths_map.items():
        parts = path.split("/")
        if len(parts) >= 2:
            by_folder["/".join(parts[:-1])].append(fname)

    total = 0
    for folder, files in by_folder.items():
        if len(files) <= threshold:
            continue
        if len(folder.split("/")) >= MAX_PARTS - 1:
            continue
        moves = {}
        for fname in files:
            tags = tegs.get(fname, [])
            sub = classify_by_split_rules(tags)
            if sub:
                moves[fname] = f"{folder}/{sub}/{fname}"
            else:
                lang = language_subfolder(fname)
                if lang:
                    moves[fname] = f"{folder}/{lang}/{fname}"
        if not moves:
            continue
        sub_count = Counter("/".join(p.split("/")[:-1]) for p in moves.values())
        if len(sub_count) < 2:
            continue
        for fname, new_path in moves.items():
            all_paths_map[fname] = new_path
            total += 1
        print(f"  [split] {folder}: {len(files)} → {len(sub_count)} подпапок")
    return total


# ════════════════════════════════════════════════════════════════
#  АГЕНТ 1: СОРТИРОВЩИК
# ════════════════════════════════════════════════════════════════
def _ask_sorter(client, model, system_prompt, chunk):
    expected = set(chunk.keys())
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(chunk, ensure_ascii=False)},
    ]
    for attempt in range(1, 4):
        try:
            print(f"    [sorter] попытка {attempt}", end="", flush=True)
            t0 = time.time()
            chunks = []
            for part in client.chat(
                model=model, messages=messages, format=JSON_ARRAY_SCHEMA,
                options={
                    "temperature": 0.1 if attempt == 1 else 0.5,
                    "num_predict": NUM_PREDICT_SORTER,
                    "num_ctx": NUM_CTX,
                    "repeat_penalty": 1.1,
                },
                keep_alive="10m", stream=True,
            ):
                chunks.append(part["message"]["content"])
                print(".", end="", flush=True)
            content = "".join(chunks)
            _timed_print(t0)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f" ERROR: {e}")
            continue
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "Не валидный JSON. Верни JSON-массив строк."},
            ]
            continue
        if not isinstance(parsed, list):
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "Нужен МАССИВ строк."},
            ]
            continue
        repaired = _repair_batch(parsed, expected)
        ok, err = validate_paths(list(repaired.values()), expected, chunk)
        if ok:
            return list(repaired.values())
        print(f"    [sorter] debug: {err}")
        messages += [
            {"role": "assistant", "content": content},
            {"role": "user", "content": f"Не прошло: {err}. Верни массив строк."},
        ]
    return [f"Other/{f}" for f in expected]


def _ask_sorter_fix(client, model, system_prompt, all_tags, problems):
    files = [p["file"] for p in problems if p["file"] in all_tags]
    if not files:
        return {}
    fix_payload = {
        "fix": [
            {"file": p["file"], "current": p.get("current", ""),
             "reason": p.get("reason", ""), "suggest": p.get("suggest", "")}
            for p in problems if p["file"] in all_tags
        ],
        "tags": {f: all_tags[f] for f in files},
    }
    expected = set(files)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(fix_payload, ensure_ascii=False)},
    ]
    print(f"    [sorter-fix] {len(files)} файлов", end="", flush=True)
    try:
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_ARRAY_SCHEMA,
            options={
                "temperature": 0.2,
                "num_predict": NUM_PREDICT_SORTER,
                "num_ctx": NUM_CTX,
            },
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f" ERROR: {e}")
        return {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, list):
        return {}
    repaired = _repair_batch(parsed, expected)
    ok, err = validate_paths(list(repaired.values()), expected, all_tags)
    if not ok:
        return {}
    return repaired


# ════════════════════════════════════════════════════════════════
#  АГЕНТ 2
# ════════════════════════════════════════════════════════════════
def _ask_validator(client, model, validator_prompt, tags, paths):
    payload = {"tags": tags, "paths": paths}
    messages = [
        {"role": "system", "content": validator_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    try:
        print(f"    [validator] {len(paths)} путей", end="", flush=True)
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_OBJECT_SCHEMA,
            options={
                "temperature": 0.1,
                "num_predict": 1200,
                "num_ctx": NUM_CTX,
            },
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"    ERROR: {e}")
        return []
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, dict) or parsed.get("ok") is True:
        return []
    problems = parsed.get("problems", [])
    if not isinstance(problems, list):
        return []
    clean = []
    for p in problems:
        if not isinstance(p, dict):
            continue
        f = p.get("file")
        if f in tags and f in paths:
            clean.append({
                "file": f,
                "current": p.get("current", paths[f]),
                "reason": p.get("reason", ""),
                "suggest": p.get("suggest", ""),
            })
    return clean


def _sort_with_validation(client, model, sorter_prompt, validator_prompt, chunk):
    expected = set(chunk.keys())
    paths = _ask_sorter(client, model, sorter_prompt, chunk)
    paths_map = {p.split("/")[-1]: p for p in paths if p.split("/")[-1] in expected}

    for round_no in range(1, MAX_FIX_ROUNDS + 1):
        print(f"  ── validation round {round_no}/{MAX_FIX_ROUNDS} ──")
        problems = _ask_validator(client, model, validator_prompt, chunk, paths_map)
        if not problems:
            print(f"    ✓ смысл в порядке")
            break
        print(f"    ✗ проблем: {len(problems)}")
        for p in problems[:5]:
            print(f"      · {p['file']}: {p['reason']} → {p['suggest'] or '?'}")
        fixes = _ask_sorter_fix(client, model, sorter_prompt, chunk, problems)
        if not fixes:
            print(f"    [warn] не удалось исправить")
            break
        for fname, new_path in fixes.items():
            paths_map[fname] = new_path
        print(f"    исправлено: {len(fixes)}")

    return paths_map


# ════════════════════════════════════════════════════════════════
#  АГЕНТ 3, этап 1
# ════════════════════════════════════════════════════════════════
def _ask_tree_structure(client, model, prompt, folders_counts, top_categories):
    payload = {"folders": folders_counts, "top_categories": top_categories}
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    print(f"    [tree stage 1] {len(folders_counts)} папок", end="", flush=True)
    try:
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_OBJECT_SCHEMA,
            options={
                "temperature": 0.1,
                "num_predict": NUM_PREDICT_STRUCT,
                "num_ctx": NUM_CTX,
            },
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f" ERROR: {e}")
        return {"ok": True, "issues": []}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"ok": True, "issues": []}
    if not isinstance(parsed, dict):
        return {"ok": True, "issues": []}
    raw = parsed.get("issues", [])
    if not isinstance(raw, list):
        raw = []
    allowed = {"merge", "rename_folder", "too_specific", "split_oversized"}
    clean = [i for i in raw if isinstance(i, dict) and i.get("type") in allowed]
    for iss in clean:
        if iss.get("type") == "too_specific" and not iss.get("files"):
            iss["files"] = []
    return {"ok": parsed.get("ok", not clean), "issues": clean}


# ════════════════════════════════════════════════════════════════
#  АГЕНТ 3, этап 2
# ════════════════════════════════════════════════════════════════
def _ask_tree_files(client, model, prompt, batch_paths, tegs):
    payload = {
        "files": {
            fname: {"path": path, "tags": tegs.get(fname, [])}
            for fname, path in batch_paths.items()
        }
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    print(f"      batch ({len(batch_paths)})", end="", flush=True)
    try:
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_OBJECT_SCHEMA,
            options={
                "temperature": 0.1,
                "num_predict": NUM_PREDICT_FILES,
                "num_ctx": NUM_CTX,
                "repeat_penalty": 1.15,
            },
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f" ERROR: {e}")
        return []
    content = content.strip()
    if not content.startswith("{"):
        return []
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("issues", [])
    if not isinstance(raw, list):
        return []
    allowed = {"misplaced_file", "inconsistent"}
    clean = []
    for iss in raw:
        if not isinstance(iss, dict) or iss.get("type") not in allowed:
            continue
        if iss["type"] == "misplaced_file":
            if iss.get("file") not in batch_paths:
                continue
        clean.append(iss)
    return clean


# ════════════════════════════════════════════════════════════════
#  Применение правок
# ════════════════════════════════════════════════════════════════
def _apply_tree_fixes(all_paths_map, issues, tegs):
    fixed = dict(all_paths_map)
    applied, skipped = [], []

    def _valid_folder(folder):
        if not folder or " " in folder:
            return False
        return all(re.fullmatch(r"[A-Za-z0-9_]+", p)
                   for p in folder.split("/") if p)

    def _rename_prefix(src, dst):
        src_p, dst_p = src + "/", dst + "/"
        n = 0
        for fname, path in fixed.items():
            if path.startswith(src_p):
                fixed[fname] = dst_p + path[len(src_p):]
                n += 1
        return n

    for iss in issues:
        t = iss.get("type")

        if t in ("merge", "rename_folder"):
            src = (iss.get("from") or "").strip("/")
            dst = (iss.get("to") or "").strip("/")
            if not src or not dst or not _valid_folder(dst) or src == dst:
                skipped.append({"issue": iss, "why": "bad from/to"})
                continue
            n = _rename_prefix(src, dst)
            if n:
                applied.append(f"{t} {src}/ → {dst}/ ({n})")
            else:
                skipped.append({"issue": iss, "why": "нет файлов"})

        elif t == "move_files":
            src_f = (iss.get("from_folder") or "").strip("/")
            dst_f = (iss.get("to_folder") or "").strip("/")
            files = iss.get("files") or []
            if not src_f or not dst_f or not _valid_folder(dst_f):
                skipped.append({"issue": iss, "why": "bad folders"})
                continue
            src_p, dst_p = src_f + "/", dst_f + "/"
            moved = 0
            for fname in files:
                if fname in fixed and fixed[fname].startswith(src_p):
                    tail = fixed[fname][len(src_p):]
                    fixed[fname] = dst_p + tail
                    applied.append(f"move {src_f}/{tail} → {dst_f}/{tail}")
                    moved += 1
            if not moved:
                skipped.append({"issue": iss, "why": "нет файлов"})

        elif t == "too_specific":
            target = (iss.get("suggest") or "").strip("/")
            files = iss.get("files") or []
            if not target or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad target"})
                continue
            for fname in files:
                if fname in fixed:
                    new_path = f"{target}/{fname}"
                    applied.append(f"move {fixed[fname]} → {new_path}")
                    fixed[fname] = new_path

        elif t == "split_oversized":
            folder = (iss.get("folder") or "").strip("/")
            if not folder or not _valid_folder(folder):
                skipped.append({"issue": iss, "why": "bad folder"})
                continue
            n = _split_one_folder(fixed, tegs, folder)
            if n:
                applied.append(f"split {folder}/ ({n})")
            else:
                skipped.append({"issue": iss, "why": "нет кандидатов"})

        elif t == "misplaced_file":
            fname = iss.get("file")
            target = (iss.get("suggest") or "").strip("/")
            if fname not in fixed or not target or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad file/target"})
                continue
            new_path = f"{target}/{fname}"
            if new_path != fixed[fname]:
                applied.append(f"move {fixed[fname]} → {new_path}")
                fixed[fname] = new_path

        elif t == "inconsistent":
            target = (iss.get("suggest") or "").strip("/")
            folders = iss.get("folders") or []
            if not target or not folders or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad target/folders"})
                continue
            for src in folders:
                src = src.strip("/")
                if src == target:
                    continue
                n = _rename_prefix(src, target)
                if n:
                    applied.append(f"inconsistent {src}/ → {target}/ ({n})")

    ok, err = validate_paths(list(fixed.values()), set(tegs.keys()), tegs)
    if not ok:
        print(f"    [tree-fix] сломали формат ({err}) — откат")
        return dict(all_paths_map), [], [{"why": f"rollback: {err}"}]

    return fixed, applied, skipped


def _split_one_folder(all_paths_map, tegs, folder):
    files = [f for f, p in all_paths_map.items()
             if "/".join(p.split("/")[:-1]) == folder]
    if len(files) <= SPLIT_THRESHOLD:
        return 0
    if len(folder.split("/")) >= MAX_PARTS - 1:
        return 0
    moves = {}
    for fname in files:
        tags = tegs.get(fname, [])
        sub = classify_by_split_rules(tags)
        if sub:
            moves[fname] = f"{folder}/{sub}/{fname}"
        else:
            lang = language_subfolder(fname)
            if lang:
                moves[fname] = f"{folder}/{lang}/{fname}"
    if not moves:
        return 0
    sub_count = Counter("/".join(p.split("/")[:-1]) for p in moves.values())
    if len(sub_count) < 2:
        return 0
    for fname, new_path in moves.items():
        all_paths_map[fname] = new_path
    return len(moves)


# ════════════════════════════════════════════════════════════════
#  Двух-этапная проверка дерева
# ════════════════════════════════════════════════════════════════
def _tree_validation_staged(client, model, structure_prompt, files_prompt,
                             all_paths_map, tegs):
    total_issues = 0

    folder_counts = Counter(
        "/".join(p.split("/")[:-1]) for p in all_paths_map.values()
    )
    folders_dict = {f: n for f, n in folder_counts.items() if f}
    top_cats = sorted({p.split("/")[0] for p in all_paths_map.values()})

    print(f"\n  [этап 1/2] структура")
    struct = _ask_tree_structure(client, model, structure_prompt,
                                  folders_dict, top_cats)
    struct_issues = struct.get("issues", [])
    if struct_issues:
        print(f"    ✗ проблем: {len(struct_issues)}")
        for iss in struct_issues[:10]:
            print(f"      · {iss.get('type')}: {iss.get('reason', '')}")
        for iss in struct_issues:
            if iss.get("type") == "too_specific" and not iss.get("files"):
                folder = (iss.get("folder") or "").strip("/") + "/"
                iss["files"] = [fname for fname, path in all_paths_map.items()
                                if path.startswith(folder)]
        fixed_map, applied, skipped = _apply_tree_fixes(
            all_paths_map, struct_issues, tegs
        )
        if applied:
            print(f"    ✓ применено: {len(applied)}")
            for line in applied[:10]:
                print(f"      {line}")
            all_paths_map = fixed_map
        total_issues += len(struct_issues)
    else:
        print(f"    ✓ структура в порядке")

    print(f"\n  [этап 2/2] смысл файлов")
    items = list(all_paths_map.items())
    batches = [items[i:i + TREE_FILE_BATCH]
               for i in range(0, len(items), TREE_FILE_BATCH)]
    print(f"    батчей: {len(batches)}")

    all_file_issues = []
    skipped_batches = 0
    for idx, batch in enumerate(batches, 1):
        print(f"    [{idx}/{len(batches)}]", end="")
        try:
            batch_paths = dict(batch)
            issues = _ask_tree_files(client, model, files_prompt,
                                      batch_paths, tegs)
            all_file_issues.extend(issues)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"      [skip] {e}")
            skipped_batches += 1
            continue

    if skipped_batches:
        print(f"    [warn] пропущено батчей: {skipped_batches}")

    if all_file_issues:
        print(f"    ✗ проблем: {len(all_file_issues)}")
        for iss in all_file_issues[:10]:
            print(f"      · {iss.get('type')}: {iss.get('reason', '')}")
        fixed_map, applied, skipped = _apply_tree_fixes(
            all_paths_map, all_file_issues, tegs
        )
        if applied:
            print(f"    ✓ применено: {len(applied)}")
            for line in applied[:10]:
                print(f"      {line}")
            all_paths_map = fixed_map
        total_issues += len(all_file_issues)
    else:
        print(f"    ✓ смысл в порядке")

    return all_paths_map, total_issues


# ════════════════════════════════════════════════════════════════
#  Детерминированный fallback
# ════════════════════════════════════════════════════════════════
def apply_deterministic_fallback(all_paths, tegs):
    fixed = []
    fixed_count = 0
    for path in all_paths:
        parts = path.split("/")
        name, top = parts[-1], parts[0]
        if tegs.get(name) and top in ("Other", "Unsorted"):
            category = classify_by_tags(tegs[name])
            if category:
                new_path = f"{category}/{name}"
                print(f"  [fallback] {path} → {new_path}")
                fixed.append(new_path)
                fixed_count += 1
                continue
        fixed.append(path)
    print(f"[fallback] восстановлено: {fixed_count}")
    return fixed


# ════════════════════════════════════════════════════════════════
#  Оркестратор
# ════════════════════════════════════════════════════════════════
def Teg_analyse(programm_path):
    base = Path(programm_path)
    sorter_prompt = (base / "teg_analyse_prompt.txt").read_text(encoding="utf-8")
    validator_prompt = (base / "validate_paths_prompt.txt").read_text(encoding="utf-8")
    structure_prompt = (base / "validate_tree_structure_prompt.txt").read_text(encoding="utf-8")
    files_prompt = (base / "validate_tree_files_prompt.txt").read_text(encoding="utf-8")

    with open(base / "tegs.json", "r", encoding="utf-8") as f:
        tegs = json.load(f)

    if not tegs:
        _safe_dump(base / "new_paths.json", [])
        print("[]")
        return []

    client = Client(timeout=CLIENT_TIMEOUT)
    items = list(tegs.items())
    batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    print(f"Всего файлов: {len(items)}, батчей: {len(batches)} (размер {BATCH_SIZE})")

    all_paths_map = {}
    start_total = time.time()

    # ─── Основной цикл ───
    try:
        for idx, batch in enumerate(batches, 1):
            chunk = dict(batch)
            print(f"\n═══ Батч {idx}/{len(batches)} — {len(chunk)} файлов ═══")
            result = _sort_with_validation(
                client, "qwen2.5:7b", sorter_prompt, validator_prompt, chunk
            )
            all_paths_map.update(result)
            _safe_dump(base / "new_paths.json",
                       [all_paths_map[f] for f in tegs if f in all_paths_map])
    except KeyboardInterrupt:
        print("\n\n[!] Прервано. Сохраняю готовое.")
        _safe_dump(base / "new_paths.json",
                   [all_paths_map[f] for f in tegs if f in all_paths_map])
        return list(all_paths_map.values())

    for f in tegs:
        if f not in all_paths_map:
            all_paths_map[f] = f"Other/{f}"

    # ─── Fallback для Other/Unsorted ───
    print("\n[deterministic fallback]")
    ordered = [all_paths_map[f] for f in tegs]
    ordered = apply_deterministic_fallback(ordered, tegs)
    for f, p in zip(tegs, ordered):
        all_paths_map[f] = p

    # ═══ ПОСТПРОЦЕССИНГ: принудительная правильная структура ═══
    print("\n[refine programming paths]")
    t_ref = time.time()
    n = _refine_programming_paths(all_paths_map, tegs)
    _timed_print(t_ref, f", переложено {n}")
    _safe_dump(base / "new_paths.json",
               [all_paths_map[f] for f in tegs])

    # ─── Сплит больших неклассифицированных папок ───
    print("\n[split oversized folders]")
    t_split = time.time()
    moved = _split_oversized_folders(all_paths_map, tegs, SPLIT_THRESHOLD)
    _timed_print(t_split, f", перемещено {moved}")
    _safe_dump(base / "new_paths.json",
               [all_paths_map[f] for f in tegs])

    # ─── АГЕНТ 3 ───
    print("\n═══ Tree validation (staged) ═══")
    for round_no in range(1, MAX_TREE_ROUNDS + 1):
        print(f"\n[tree round {round_no}/{MAX_TREE_ROUNDS}]")
        t0 = time.time()
        all_paths_map, issues_count = _tree_validation_staged(
            client, "qwen2.5:7b",
            structure_prompt, files_prompt,
            all_paths_map, tegs,
        )
        _safe_dump(base / "new_paths.json",
                   [all_paths_map[f] for f in tegs])
        _timed_print(t0, " round time")
        if issues_count == 0:
            print(f"  ✓ дерево логично")
            break
        print(f"  → issues: {issues_count}")

    # ─── Финальный refine (на случай, если агент 3 что-то сломал) ───
    print("\n[final refine]")
    _refine_programming_paths(all_paths_map, tegs)
    _safe_dump(base / "new_paths.json",
               [all_paths_map[f] for f in tegs])

    # ─── Финальная валидация ───
    final = [all_paths_map[f] for f in tegs]
    ok, err = validate_paths(final, set(tegs.keys()), tegs)
    if not ok:
        print(f"[!] Финальная валидация: {err}")
    _safe_dump(base / "new_paths.json", final)

    others = sum(1 for p in final if p.split("/")[0] == "Other")
    unsorted = sum(1 for p in final if p.split("/")[0] == "Unsorted")
    total_time = time.time() - start_total
    print(f"\nГотово: {len(final)}, Other/: {others}, Unsorted/: {unsorted}")
    print(f"Время: {total_time:.0f}с")
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return final


if __name__ == "__main__":
    Teg_analyse(
        r"C:\Users\MSI\Documents\GitHub\AI-File-Sorter\src\agent\directory_agent"
    )