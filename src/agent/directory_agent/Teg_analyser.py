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
CLIENT_TIMEOUT = 300.0
JSON_ARRAY_SCHEMA = {"type": "array", "items": {"type": "string"}}
JSON_OBJECT_SCHEMA = {"type": "object"}
DUP_PREFIX_LEN = 4
MAX_PARTS = 6
FOLDER_TOP_TAGS_N = 5

NUM_PREDICT_SORTER = 2500
NUM_PREDICT_STRUCT = 1500
NUM_PREDICT_FILES = 500
NUM_CTX = 4096


WHITELIST_ROOTS = {
    "Animals", "Art", "Business", "Construction", "Culture", "Documents",
    "Education", "Entertainment", "Food", "Games", "Geography", "Health",
    "History", "Language", "Literature", "Media", "Nature", "People",
    "Politics", "Science", "Technology", "Travel", "Urban", "Vehicles",
    "Work", "Other", "Unsorted",
}

BAD_ROOTS = {
    "sciencefiction": "Literature/ScienceFiction",
    "play": "Literature/Plays", "plays": "Literature/Plays",
    "novel": "Literature/Novels", "novels": "Literature/Novels",
    "ui": "Technology/UI", "ux": "Technology/UI",
    "web": "Technology/Web",
    "programming": "Technology/Programming",
    "cars": "Vehicles/Cars", "car": "Vehicles/Cars",
    "primates": "Animals/Primates",
    "birds": "Animals/Birds",
    "cats": "Animals/Cats",
    "wildlife": "Animals/Wildlife",
    "geology": "Nature/Geology",
    "nightsky": "Nature/NightSky",
    "landscape": "Nature/Landscape",
    "autumn": "Nature/Autumn",
    "cities": "Urban", "city": "Urban",
    "dictionary": "Language/Dictionary",
    "islam": "History/Islam",
    "fastfood": "Food/FastFood",
    "characters": "Art/Cartoons",
}

# Минимальная сеть синонимов — только для защиты от грубых ошибок перетаскивания.
# Если файл с тегом "owl" перетаскивают в "Animals/Birds", проверка должна пройти.
SYNONYMS = {
    "bird": {"owl", "eagle", "parrot", "sparrow", "duck", "swan", "penguin", "hawk", "falcon"},
    "cat": {"kitten", "feline"},
    "dog": {"puppy", "canine"},
    "primate": {"chimpanzee", "chimp", "monkey", "ape", "gorilla", "orangutan"},
    "wildlife": {"tiger", "lion", "leopard", "wolf", "wolves", "fox", "bear",
                 "deer", "squirrel", "elephant", "zebra", "giraffe"},
    "plant": {"flower", "tree", "grass", "leaf", "bloom"},
    "insect": {"bee", "ant", "butterfly", "fly", "mosquito"},
}


LANGUAGE_MAP = {
    ".c": "C", ".h": "C",
    ".cpp": "Cpp", ".cc": "Cpp", ".cxx": "Cpp", ".hpp": "Cpp",
    ".py": "Python", ".java": "Java",
    ".js": "JavaScript", ".ts": "TypeScript",
    ".rs": "Rust", ".go": "Go", ".rb": "Ruby",
    ".cs": "CSharp", ".php": "PHP",
    ".html": "HTML", ".css": "CSS",
}
CODE_EXTENSIONS = set(LANGUAGE_MAP.keys()) | {".sql", ".sh", ".bat", ".ps1"}


def _is_code_file(fname):
    return Path(fname).suffix.lower() in CODE_EXTENSIONS


def language_subfolder(fname):
    return LANGUAGE_MAP.get(Path(fname).suffix.lower())


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
    if parts[0] not in WHITELIST_ROOTS:
        return ""
    return s


def _expand_tags(tags_lower):
    expanded = set(tags_lower)
    for tag in tags_lower:
        for canon, syns in SYNONYMS.items():
            if tag in syns:
                expanded.add(canon)
            if tag == canon:
                expanded.update(syns)
    return expanded


def _path_matches_tags(fname, target_folder, tegs):
    """Для не-кода: хотя бы одно слово из пути должно быть в тегах."""
    if _is_code_file(fname):
        return True
    tags = tegs.get(fname, [])
    if not tags:
        return True
    expanded = _expand_tags(set(t.lower() for t in tags))
    folder_words = re.findall(r'[A-Za-z]+', target_folder)
    for fw in folder_words:
        fw_lower = fw.lower()
        if fw_lower in expanded:
            return True
        for tag in expanded:
            if tag in fw_lower or fw_lower in tag:
                return True
    return False


def _dest_matches_top(fname, dest_folder):
    """Базовая проверка top-level: whitelist, код→Programming, не-код∉Programming."""
    if not dest_folder:
        return False
    top = dest_folder.split("/")[0]
    if top not in WHITELIST_ROOTS:
        return False
    is_code = _is_code_file(fname)
    in_prog = dest_folder.startswith("Technology/Programming")
    if is_code and not in_prog:
        return False
    if not is_code and in_prog:
        return False
    return True


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
    print(f" {time.time() - start:.1f}s{suffix}")


def _build_folder_stats(all_paths_map, tegs, top_n=FOLDER_TOP_TAGS_N):
    by_folder = defaultdict(list)
    for fname, path in all_paths_map.items():
        by_folder["/".join(path.split("/")[:-1])].append(fname)
    result = {}
    for folder, files in by_folder.items():
        if not folder:
            continue
        tag_counter = Counter()
        for f in files:
            for tag in tegs.get(f, []):
                tag_counter[tag.lower()] += 1
        result[folder] = {
            "count": len(files),
            "top_tags": [t for t, _ in tag_counter.most_common(top_n)],
        }
    return result


def _refine_programming_paths(all_paths_map, silent=False):
    moved = 0
    for fname, current in list(all_paths_map.items()):
        if not _is_code_file(fname):
            continue
        if current.startswith("Technology/Programming/"):
            continue
        lang = language_subfolder(fname) or "Other"
        new_path = f"Technology/Programming/{lang}/{fname}"
        all_paths_map[fname] = new_path
        moved += 1
        if not silent and moved <= 15:
            print(f"    refine {current} → {new_path}")
    if not silent:
        print(f"  [refine] переложено: {moved}")
    return moved


# ════════════════════════════════════════════════════════════════
#  Агент 1
# ════════════════════════════════════════════════════════════════
def _ask_sorter(client, model, system_prompt, chunk):
    expected = set(chunk.keys())
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(chunk, ensure_ascii=False)},
    ]
    for attempt in range(1, 4):
        try:
            print(f"    [sorter] {attempt}", end="", flush=True)
            t0 = time.time()
            chunks = []
            for part in client.chat(
                model=model, messages=messages, format=JSON_ARRAY_SCHEMA,
                options={"temperature": 0.1 if attempt == 1 else 0.5,
                         "num_predict": NUM_PREDICT_SORTER,
                         "num_ctx": NUM_CTX, "repeat_penalty": 1.1},
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
                {"role": "user", "content": "Не валидный JSON. Верни JSON-массив строк."}]
            continue
        if not isinstance(parsed, list):
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "Нужен МАССИВ строк."}]
            continue
        repaired = _repair_batch(parsed, expected)
        ok, err = validate_paths(list(repaired.values()), expected, chunk)
        if ok:
            return list(repaired.values())
        messages += [
            {"role": "assistant", "content": content},
            {"role": "user", "content": f"Не прошло: {err}. Верни массив строк."}]
    return [f"Other/{f}" for f in expected]


def _ask_sorter_fix(client, model, system_prompt, all_tags, problems):
    files = [p["file"] for p in problems if p["file"] in all_tags]
    if not files:
        return {}
    fix_payload = {
        "fix": [{"file": p["file"], "current": p.get("current", ""),
                 "reason": p.get("reason", ""), "suggest": p.get("suggest", "")}
                for p in problems if p["file"] in all_tags],
        "tags": {f: all_tags[f] for f in files},
    }
    expected = set(files)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(fix_payload, ensure_ascii=False)},
    ]
    print(f"    [sorter-fix] {len(files)}", end="", flush=True)
    try:
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_ARRAY_SCHEMA,
            options={"temperature": 0.2, "num_predict": NUM_PREDICT_SORTER,
                     "num_ctx": NUM_CTX},
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception:
        return {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, list):
        return {}
    repaired = _repair_batch(parsed, expected)
    ok, _ = validate_paths(list(repaired.values()), expected, all_tags)
    return repaired if ok else {}


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
        print(f"    [validator] {len(paths)}", end="", flush=True)
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_OBJECT_SCHEMA,
            options={"temperature": 0.1, "num_predict": 1200, "num_ctx": NUM_CTX},
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception:
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
            clean.append({"file": f, "current": p.get("current", paths[f]),
                          "reason": p.get("reason", ""),
                          "suggest": _sanitize_suggest(p.get("suggest", ""))})
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
            break
        paths_map.update(fixes)
        print(f"    исправлено: {len(fixes)}")
    return paths_map


# ════════════════════════════════════════════════════════════════
#  Агент 3
# ════════════════════════════════════════════════════════════════
def _ask_tree_structure(client, model, prompt, folder_stats, top_categories):
    payload = {"folders": folder_stats, "top_categories": top_categories}
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    print(f"    [tree stage 1] {len(folder_stats)}", end="", flush=True)
    try:
        t0 = time.time()
        chunks = []
        for part in client.chat(
            model=model, messages=messages, format=JSON_OBJECT_SCHEMA,
            options={"temperature": 0.1, "num_predict": NUM_PREDICT_STRUCT,
                     "num_ctx": NUM_CTX},
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception:
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
    allowed = {"merge", "rename_folder", "too_specific"}
    clean = [i for i in raw if isinstance(i, dict) and i.get("type") in allowed]
    for iss in clean:
        if iss.get("type") == "too_specific" and not iss.get("files"):
            iss["files"] = []
        if iss.get("to"):
            iss["to"] = _sanitize_suggest(iss["to"])
        if iss.get("suggest"):
            iss["suggest"] = _sanitize_suggest(iss["suggest"])
    return {"ok": parsed.get("ok", not clean), "issues": clean}


def _ask_tree_files(client, model, prompt, batch_paths, tegs):
    payload = {
        "files": {fname: {"path": path, "tags": tegs.get(fname, [])}
                  for fname, path in batch_paths.items()}
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
            options={"temperature": 0.1, "num_predict": NUM_PREDICT_FILES,
                     "num_ctx": NUM_CTX, "repeat_penalty": 1.15},
            keep_alive="10m", stream=True,
        ):
            chunks.append(part["message"]["content"])
            print(".", end="", flush=True)
        content = "".join(chunks)
        _timed_print(t0)
    except KeyboardInterrupt:
        raise
    except Exception:
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
        if iss["type"] == "misplaced_file" and iss.get("file") not in batch_paths:
            continue
        if iss.get("suggest"):
            iss["suggest"] = _sanitize_suggest(iss["suggest"])
        clean.append(iss)
    return clean


# ════════════════════════════════════════════════════════════════
#  Применение правок с проверкой тегов
# ════════════════════════════════════════════════════════════════
def _apply_tree_fixes(all_paths_map, issues, tegs):
    fixed = dict(all_paths_map)
    applied, skipped = [], []

    def _valid_folder(folder):
        if not folder or " " in folder:
            return False
        parts = [p for p in folder.split("/") if p]
        return 0 < len(parts) < MAX_PARTS and all(
            re.fullmatch(r"[A-Za-z0-9_]+", p) for p in parts)

    def _same_top(a, b):
        return bool(a and b and a.split("/")[0] == b.split("/")[0])

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

        # ── merge / rename_folder ──
        if t in ("merge", "rename_folder"):
            src = (iss.get("from") or "").strip("/")
            dst = _sanitize_suggest(iss.get("to") or "").strip("/")
            if not src or not dst or not _valid_folder(dst) or src == dst:
                skipped.append({"issue": iss, "why": "bad from/to"})
                continue
            if not _same_top(src, dst):
                skipped.append({"issue": iss, "why": "cross top-level"})
                continue
            if dst.startswith(src + "/"):
                skipped.append({"issue": iss, "why": "dst inside src"})
                continue
            n = _rename_prefix(src, dst)
            if n:
                applied.append(f"{t} {src}/ → {dst}/ ({n})")
            else:
                skipped.append({"issue": iss, "why": "нет файлов"})

        # ── too_specific ──
        elif t == "too_specific":
            target = _sanitize_suggest(iss.get("suggest") or "").strip("/")
            files = iss.get("files") or []
            if not target or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad target"})
                continue
            for fname in files:
                if fname not in fixed:
                    continue
                if not _dest_matches_top(fname, target):
                    skipped.append({"issue": iss, "why": f"bad top {fname}"})
                    continue
                current = fixed[fname]
                # Поднятие из узкой папки в родителя — разрешаем без тегов
                is_promotion = current.startswith(target + "/")
                if not is_promotion and not _path_matches_tags(fname, target, tegs):
                    skipped.append({"issue": iss, "why": f"no tag match {fname}"})
                    continue
                new_path = f"{target}/{fname}"
                if len(new_path.split("/")) > MAX_PARTS:
                    skipped.append({"issue": iss, "why": "too deep"})
                    continue
                applied.append(f"move {current} → {new_path}")
                fixed[fname] = new_path

        # ── misplaced_file ──
        elif t == "misplaced_file":
            fname = iss.get("file")
            target = _sanitize_suggest(iss.get("suggest") or "").strip("/")
            if fname not in fixed or not target or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad file/target"})
                continue
            if not _dest_matches_top(fname, target):
                skipped.append({"issue": iss, "why": "bad top"})
                continue
            # Проверка тегов для не-кода
            if not _is_code_file(fname) and not _path_matches_tags(fname, target, tegs):
                skipped.append({"issue": iss, "why": "no tag match"})
                continue
            new_path = f"{target}/{fname}"
            if len(new_path.split("/")) > MAX_PARTS:
                skipped.append({"issue": iss, "why": "too deep"})
                continue
            if new_path != fixed[fname]:
                applied.append(f"move {fixed[fname]} → {new_path}")
                fixed[fname] = new_path

        # ── inconsistent ──
        elif t == "inconsistent":
            target = _sanitize_suggest(iss.get("suggest") or "").strip("/")
            folders = iss.get("folders") or []
            if not target or not folders or not _valid_folder(target):
                skipped.append({"issue": iss, "why": "bad target"})
                continue
            target_top = target.split("/")[0]
            # Все src должны быть в одном top с target
            if not all(f.strip("/").split("/")[0] == target_top
                       for f in folders if f.strip("/")):
                skipped.append({"issue": iss, "why": "cross top-level"})
                continue
            affected = [f for f, p in fixed.items()
                        if any(p.startswith(fd.strip("/") + "/") for fd in folders)]
            # Проверка тегов
            if not all(_path_matches_tags(f, target, tegs) for f in affected):
                skipped.append({"issue": iss, "why": "no tag match"})
                continue
            for src in folders:
                src = src.strip("/")
                if src != target and _rename_prefix(src, target):
                    applied.append(f"inconsistent {src}/ → {target}/")

    ok, err = validate_paths(list(fixed.values()), set(tegs.keys()), tegs)
    if not ok:
        print(f"    [tree-fix] сломали формат ({err}) — откат")
        return dict(all_paths_map), [], [{"why": f"rollback: {err}"}]

    if applied:
        refined = _refine_programming_paths(fixed, silent=True)
        if refined:
            applied.append(f"refine: {refined}")
            ok2, err2 = validate_paths(list(fixed.values()), set(tegs.keys()), tegs)
            if not ok2:
                return dict(all_paths_map), [], [{"why": f"rollback: {err2}"}]

    return fixed, applied, skipped


def _tree_validation_staged(client, model, structure_prompt, files_prompt,
                             all_paths_map, tegs):
    total_issues = 0
    folder_stats = _build_folder_stats(all_paths_map, tegs)
    top_cats = sorted({p.split("/")[0] for p in all_paths_map.values()})

    print(f"\n  [этап 1/2] структура")
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
                iss["files"] = [f for f, p in all_paths_map.items()
                                if p.startswith(folder)]
        fixed_map, applied, _ = _apply_tree_fixes(all_paths_map, struct_issues, tegs)
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
    for idx, batch in enumerate(batches, 1):
        print(f"    [{idx}/{len(batches)}]", end="")
        try:
            all_file_issues.extend(
                _ask_tree_files(client, model, files_prompt, dict(batch), tegs))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"      [skip] {e}")

    if all_file_issues:
        print(f"    ✗ проблем: {len(all_file_issues)}")
        for iss in all_file_issues[:10]:
            print(f"      · {iss.get('type')}: {iss.get('reason', '')}")
        fixed_map, applied, _ = _apply_tree_fixes(all_paths_map, all_file_issues, tegs)
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
#  Retry: файлы с плохим путём → переспросить у агента 1
# ════════════════════════════════════════════════════════════════
def _needs_retry(fname, path, tegs):
    if not tegs.get(fname):
        return False
    top = path.split("/")[0]
    if top in ("Other", "Unsorted") or top not in WHITELIST_ROOTS:
        return True
    if _is_code_file(fname):
        return not path.startswith("Technology/Programming/")
    return not _path_matches_tags(fname, "/".join(path.split("/")[:-1]), tegs)


def _retry_unresolved(client, model, base_prompt, all_paths_map, tegs):
    candidates = {f: tegs[f] for f, p in all_paths_map.items()
                  if _needs_retry(f, p, tegs)}
    if not candidates:
        return 0

    hint_prompt = base_prompt + (
        "\n\n━━━ ВАЖНО ━━━\n"
        "У всех файлов ниже ЕСТЬ теги. НЕ ИСПОЛЬЗУЙ Other и НЕ ИСПОЛЬЗУЙ Unsorted.\n"
        "Выбери подходящую категорию из whitelist. Для кода — Technology/Programming/<тема>/file.\n"
        "Категория должна ОТРАЖАТЬ теги: если в тегах 'landscape' — должно быть Landscape в пути."
    )

    items = list(candidates.items())
    batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    print(f"[retry unresolved] файлов: {len(candidates)}, батчей: {len(batches)}")

    fixed = 0
    for idx, batch in enumerate(batches, 1):
        chunk = dict(batch)
        expected = set(chunk.keys())
        print(f"  [{idx}/{len(batches)}]", end="")
        try:
            paths = _ask_sorter(client, model, hint_prompt, chunk)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"  [skip] {e}")
            continue
        for p in paths:
            fname = p.split("/")[-1]
            if fname not in expected:
                continue
            top = p.split("/")[0]
            if top not in ("Other", "Unsorted") and top in WHITELIST_ROOTS:
                all_paths_map[fname] = p
                fixed += 1
    print(f"\n[retry unresolved] исправлено: {fixed}/{len(candidates)}")
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
    print(f"Всего файлов: {len(items)}, батчей: {len(batches)}")

    all_paths_map = {}
    start_total = time.time()

    try:
        for idx, batch in enumerate(batches, 1):
            chunk = dict(batch)
            print(f"\n═══ Батч {idx}/{len(batches)} — {len(chunk)} ═══")
            result = _sort_with_validation(
                client, "qwen2.5:7b", sorter_prompt, validator_prompt, chunk)
            all_paths_map.update(result)
            _safe_dump(base / "new_paths.json",
                       [all_paths_map[f] for f in tegs if f in all_paths_map])
    except KeyboardInterrupt:
        print("\n[!] Прервано.")
        _safe_dump(base / "new_paths.json",
                   [all_paths_map[f] for f in tegs if f in all_paths_map])
        return list(all_paths_map.values())

    for f in tegs:
        if f not in all_paths_map:
            all_paths_map[f] = f"Other/{f}"

    print("\n[retry unresolved]")
    _retry_unresolved(client, "qwen2.5:7b", sorter_prompt, all_paths_map, tegs)
    _safe_dump(base / "new_paths.json", [all_paths_map[f] for f in tegs])

    print("\n[refine programming paths]")
    t = time.time()
    n = _refine_programming_paths(all_paths_map)
    _timed_print(t, f", {n}")
    _safe_dump(base / "new_paths.json", [all_paths_map[f] for f in tegs])

    print("\n═══ Tree validation ═══")
    for round_no in range(1, MAX_TREE_ROUNDS + 1):
        print(f"\n[tree round {round_no}/{MAX_TREE_ROUNDS}]")
        t = time.time()
        all_paths_map, issues_count = _tree_validation_staged(
            client, "qwen2.5:7b", structure_prompt, files_prompt,
            all_paths_map, tegs)
        _safe_dump(base / "new_paths.json", [all_paths_map[f] for f in tegs])
        _timed_print(t, " round")
        if issues_count == 0:
            print(f"  ✓ логично")
            break
        print(f"  → issues: {issues_count}")

    print("\n[final retry unresolved]")
    _retry_unresolved(client, "qwen2.5:7b", sorter_prompt, all_paths_map, tegs)

    print("\n[final refine]")
    _refine_programming_paths(all_paths_map)
    _safe_dump(base / "new_paths.json", [all_paths_map[f] for f in tegs])

    final = [all_paths_map[f] for f in tegs]
    ok, err = validate_paths(final, set(tegs.keys()), tegs)
    if not ok:
        print(f"[!] Финальная валидация: {err}")
    _safe_dump(base / "new_paths.json", final)

    others = sum(1 for p in final if p.split("/")[0] == "Other")
    unsorted = sum(1 for p in final if p.split("/")[0] == "Unsorted")
    print(f"\nГотово: {len(final)}, Other/: {others}, Unsorted/: {unsorted}")
    print(f"Время: {time.time() - start_total:.0f}с")
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return final


if __name__ == "__main__":
    Teg_analyse(
        r"C:\Users\MSI\Documents\GitHub\AI-File-Sorter\src\agent\directory_agent"
    )