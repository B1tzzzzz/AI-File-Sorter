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

MAX_PARTS = 6
SPLIT_THRESHOLD = 5
FOLDER_TOP_TAGS_N = 5

NUM_PREDICT_SORTER = 2500
NUM_PREDICT_STRUCT = 1500
NUM_PREDICT_FILES = 500
NUM_PREDICT_REBUILD = 3500
NUM_CTX = 4096


# ════════════════════════════════════════════════════════════════
#  Проверка suggest по whitelist
# ════════════════════════════════════════════════════════════════
BAD_ROOTS = {
    "sciencefiction": "Literature/ScienceFiction",
    "play": "Literature/Plays", "plays": "Literature/Plays",
    "novel": "Literature/Novels", "novels": "Literature/Novels",
    "poem": "Literature/Poems", "poems": "Literature/Poems",
    "story": "Literature/ShortStories", "stories": "Literature/ShortStories",
    "ui": "Technology/UI", "ux": "Technology/UI",
    "web": "Technology/Web",
    "programming": "Technology/Programming",
    "algorithm": "Technology/Programming/Algorithms",
    "algorithms": "Technology/Programming/Algorithms",
    "sorting": "Technology/Programming/Algorithms/Sorting",
    "graphs": "Technology/Programming/Algorithms/Graphs",
    "dynamicprogramming": "Technology/Programming/Algorithms/DynamicProgramming",
    "computing": "Technology/Computing",
    "networks": "Technology/Networks",
    "hardware": "Technology/Hardware",
    "troubleshooting": "Technology/Troubleshooting",
    "cars": "Vehicles/Cars",
    "primates": "Animals/Primates",
    "birds": "Animals/Birds",
    "cats": "Animals/Cats",
    "wildlife": "Animals/Wildlife",
    "geology": "Nature/Geology",
    "nightsky": "Nature/NightSky",
    "landscape": "Nature/Landscape",
    "autumn": "Nature/Autumn",
    "cities": "Urban", "city": "Urban",
    "machinelearning": "Technology/Programming/MachineLearning",
    "datastructures": "Technology/Programming/DataStructures",
    "testing": "Technology/Programming/Testing",
    "memorymanagement": "Technology/Programming/MemoryManagement",
    "dictionary": "Language/Dictionary",
    "islam": "History/Islam",
}


def _sanitize_suggest(suggest):
    if not suggest:
        return suggest
    s = suggest.strip("/")
    if not s:
        return suggest
    parts = s.split("/")
    first_lower = parts[0].lower()
    if first_lower in BAD_ROOTS:
        replacement = BAD_ROOTS[first_lower]
        rest = "/".join(parts[1:])
        return f"{replacement}/{rest}" if rest else replacement
    return s


# ════════════════════════════════════════════════════════════════
#  Детерминированный классификатор — fallback для Other/Unsorted
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
#  ПРАВИЛА СПЛИТА — порядок КРИТИЧЕН
#  Testing / Memory / Web — ВЫШЕ generic \balgorithm\b
#  \s* везде — матчит слитные теги (segmenttree, sortingalgorithm)
# ════════════════════════════════════════════════════════════════
SPLIT_RULES = [
    # NLP — выше ML
    (r"natural\s*language\s*processing|\bnlp\b|langchain|chatbot|\bllm\b",
     "MachineLearning/NLP"),
    (r"linear\s*regression|logistic\s*regression|regression\s*analysis",
     "MachineLearning/Regression"),
    (r"neural\s*network|deep\s*learning|\bcnn\b|\brnn\b|\btransformer\b",
     "MachineLearning/NeuralNetworks"),
    (r"data\s*analysis|data\s*cleaning|data\s*visualization|correlation|heatmap|"
     r"numpy|pandas|matplotlib|seaborn|dataframe",
     "MachineLearning/DataAnalysis"),
    (r"machine\s*learning|supervised\s*learning|unsupervised", "MachineLearning"),

    # ─── Testing / Memory / Web ВЫШЕ generic algorithm ───
    (r"testing|checker|comparison|numba|subprocess", "Testing"),
    (r"memory\s*management|memory\s*allocation|universal\s*swap|shift\s*operation",
     "MemoryManagement"),
    (r"web\s*development|\bhtml\b|\bcss\b|javascript|\bphp\b|wordpress", "Web"),

    # ─── DataStructures конкретные ───
    (r"avl\s*tree|segment\s*tree|binary\s*search\s*tree|red.black\s*tree|"
     r"tree\s*algorithm|binary\s*tree", "DataStructures/Trees"),
    (r"\bdsu\b|union.find|disjoint\s*set", "DataStructures/UnionFind"),

    # ─── Algorithms конкретные ───
    (r"graph\s*theory|\bdfs\b|\bbfs\b|undirected\s*graph|directed\s*graph|"
     r"connected\s*components|topological|dijkstra|shortest\s*path",
     "Algorithms/Graphs"),
    (r"dynamic\s*programming|\bdp\b|memoization", "Algorithms/DynamicProgramming"),
    (r"sorting\s*algorithm|merge\s*sort|quick\s*sort|bubble\s*sort|"
     r"insertion\s*sort|heap\s*sort|counting\s*sort|radix\s*sort|"
     r"pseudo\s*sorting", "Algorithms/Sorting"),
    (r"binary\s*search|quick\s*select|lower\s*bound|upper\s*bound|"
     r"searching\s*algorithm", "Algorithms/BinarySearch"),
    (r"string\s*algorithm|hash\s*function|\bkmp\b|\btrie\b|suffix\s*array|"
     r"string\s*matching|hash\s*string", "Algorithms/Strings"),
    (r"greedy", "Algorithms/Greedy"),
    (r"number\s*theory|modular\s*arithmetic|prime\s*number|"
     r"binary\s*exponentiation|quadratic\s*equation|floating\s*point\s*comparison|"
     r"numerical\s*stability|integer\s*division|\bmath\b|\barithmetic\b|"
     r"\bstatistics\b", "Algorithms/Math"),

    # ─── DataStructures менее специфичные ───
    (r"ordered\s*set|unordered\s*set|hash\s*set|\bset\b", "DataStructures/Sets"),
    (r"linked\s*list|priority\s*queue|\barraylist\b|\bstack\b|\bdeque\b",
     "DataStructures/Arrays"),
    (r"data\s*structure", "DataStructures"),

    # ─── Generic — последний ───
    (r"\balgorithm\b|\w*algorithm\b", "Algorithms"),
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
#  Агрегация тегов по папкам
# ════════════════════════════════════════════════════════════════
def _build_folder_stats(all_paths_map, tegs, top_n=FOLDER_TOP_TAGS_N):
    by_folder = defaultdict(list)
    for fname, path in all_paths_map.items():
        folder = "/".join(path.split("/")[:-1])
        by_folder[folder].append(fname)

    result = {}
    for folder, files in by_folder.items():
        if not folder:
            continue
        tag_counter = Counter()
        for f in files:
            for tag in tegs.get(f, []):
                tag_counter[tag.lower()] += 1
        top_tags = [t for t, _ in tag_counter.most_common(top_n)]
        result[folder] = {"count": len(files), "top_tags": top_tags}
    return result


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
#  Принудительная классификация для кода
# ════════════════════════════════════════════════════════════════
def _refine_programming_paths(all_paths_map, tegs, silent=False):
    moved = 0
    for fname in list(all_paths_map.keys()):
        if not _is_code_file(fname):
            continue

        tags = tegs.get(fname, [])
        target = classify_by_split_rules(tags)
        if not target:
            lang = language_subfolder(fname)
            if not lang:
                continue
            target = f"Other/{lang}"

        expected = f"Technology/Programming/{target}/{fname}"
        if len(expected.split("/")) > MAX_PARTS:
            first = target.split("/")[0]
            expected = f"Technology/Programming/{first}/{fname}"

        current = all_paths_map[fname]
        if current == expected:
            continue
        if current.startswith(f"Technology/Programming/{target}/"):
            continue

        old = current
        all_paths_map[fname] = expected
        moved += 1
        if not silent and moved <= 15:
            print(f"    refine {old} → {expected}")

    if not silent:
        print(f"  [refine] переложено файлов кода: {moved}")
    return moved


def _split_oversized_folders(all_paths_map, tegs, threshold=SPLIT_THRESHOLD):
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
#  Агент 1: сортировщик
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
#  Агент 2
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
            suggest = _sanitize_suggest(p.get("suggest", ""))
            clean.append({
                "file": f,
                "current": p.get("current", paths[f]),
                "reason": p.get("reason", ""),
                "suggest": suggest,
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
#  Агент 3, этап 1 — структура с тегами
# ════════════════════════════════════════════════════════════════
def _ask_tree_structure(client, model, prompt, folder_stats, top_categories):
    payload = {"folders": folder_stats, "top_categories": top_categories}
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    print(f"    [tree stage 1] {len(folder_stats)} папок (с тегами)",
          end="", flush=True)
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
        if iss.get("to"):
            iss["to"] = _sanitize_suggest(iss["to"])
        if iss.get("suggest"):
            iss["suggest"] = _sanitize_suggest(iss["suggest"])
    return {"ok": parsed.get("ok", not clean), "issues": clean}


# ════════════════════════════════════════════════════════════════
#  Агент 3, этап 2 — смысл файлов
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
            iss["suggest"] = _sanitize_suggest(iss.get("suggest", ""))
        if iss.get("suggest"):
            iss["suggest"] = _sanitize_suggest(iss["suggest"])
        clean.append(iss)
    return clean


# ════════════════════════════════════════════════════════════════
#  Применение правок с защитой глубины и авто-refine
# ════════════════════════════════════════════════════════════════
def _apply_tree_fixes(all_paths_map, issues, tegs):
    fixed = dict(all_paths_map)
    applied, skipped = [], []

    def _valid_folder(folder):
        if not folder or " " in folder:
            return False
        parts = [p for p in folder.split("/") if p]
        if not parts:
            return False
        # MAX_PARTS=6 → папок может быть ≤ 5 (5 папок + файл = 6)
        if len(parts) >= MAX_PARTS:
            return False
        return all(re.fullmatch(r"[A-Za-z0-9_]+", p) for p in parts)

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
            dst = _sanitize_suggest(iss.get("to") or "").strip("/")
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
            dst_f = _sanitize_suggest(iss.get("to_folder") or "").strip("/")
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
            target = _sanitize_suggest(iss.get("suggest") or "").strip("/")
            files = iss.get("files") or []
            if not target or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad target"})
                continue
            for fname in files:
                if fname in fixed:
                    new_path = f"{target}/{fname}"
                    if len(new_path.split("/")) > MAX_PARTS:
                        skipped.append({"issue": iss, "why": "too deep"})
                        continue
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
            target = _sanitize_suggest(iss.get("suggest") or "").strip("/")
            if fname not in fixed or not target or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad file/target"})
                continue
            new_path = f"{target}/{fname}"
            if len(new_path.split("/")) > MAX_PARTS:
                skipped.append({"issue": iss, "why": "too deep"})
                continue
            if new_path != fixed[fname]:
                applied.append(f"move {fixed[fname]} → {new_path}")
                fixed[fname] = new_path

        elif t == "inconsistent":
            target = _sanitize_suggest(iss.get("suggest") or "").strip("/")
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

    # ═══ Валидация: при ошибке откат ═══
    ok, err = validate_paths(list(fixed.values()), set(tegs.keys()), tegs)
    if not ok:
        print(f"    [tree-fix] сломали формат ({err}) — откат")
        return dict(all_paths_map), [], [{"why": f"rollback: {err}"}]

    # ═══ Защита: детерминированные правила для кода всегда побеждают ═══
    if applied:
        refined = _refine_programming_paths(fixed, tegs, silent=True)
        if refined:
            applied.append(f"refine после правок: {refined}")
            ok2, err2 = validate_paths(list(fixed.values()), set(tegs.keys()), tegs)
            if not ok2:
                print(f"    [tree-fix] refine сломал ({err2}) — откат")
                return dict(all_paths_map), [], [{"why": f"rollback after refine: {err2}"}]

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

    folder_stats = _build_folder_stats(all_paths_map, tegs)
    top_cats = sorted({p.split("/")[0] for p in all_paths_map.values()})

    print(f"\n  [этап 1/2] структура (с тегами)")
    struct = _ask_tree_structure(client, model, structure_prompt,
                                  folder_stats, top_cats)
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

    print(f"\n  [этап 2/2] смысл файлов (с тегами)")
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

    print("\n[deterministic fallback]")
    ordered = [all_paths_map[f] for f in tegs]
    ordered = apply_deterministic_fallback(ordered, tegs)
    for f, p in zip(tegs, ordered):
        all_paths_map[f] = p

    print("\n[refine programming paths]")
    t_ref = time.time()
    n = _refine_programming_paths(all_paths_map, tegs)
    _timed_print(t_ref, f", переложено {n}")
    _safe_dump(base / "new_paths.json",
               [all_paths_map[f] for f in tegs])

    print("\n[split oversized folders]")
    t_split = time.time()
    moved = _split_oversized_folders(all_paths_map, tegs, SPLIT_THRESHOLD)
    _timed_print(t_split, f", перемещено {moved}")
    _safe_dump(base / "new_paths.json",
               [all_paths_map[f] for f in tegs])

    print("\n═══ Tree validation (staged, all agents see tags) ═══")
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

    print("\n[final refine]")
    _refine_programming_paths(all_paths_map, tegs)
    _safe_dump(base / "new_paths.json",
               [all_paths_map[f] for f in tegs])

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