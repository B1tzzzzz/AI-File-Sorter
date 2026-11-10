import os
import json
import shutil
from pathlib import Path


# ════════════════════════════════════════════════════════════════
#  Windows long paths (>260 символов)
# ════════════════════════════════════════════════════════════════
def _long(path: str) -> str:
    """Добавляет \\\\?\\ для Windows, если путь длинный."""
    if os.name != "nt":
        return path
    p = os.path.abspath(path)
    if len(p) < 240:
        return p
    if p.startswith("\\\\?\\"):
        return p
    return "\\\\?\\" + p


def _exists(path: str) -> bool:
    try:
        return os.path.exists(_long(path))
    except OSError:
        return False


# ════════════════════════════════════════════════════════════════
#  Базовые операции
# ════════════════════════════════════════════════════════════════
def directory_search(path, saved=None):
    if saved is None:
        saved = []
    try:
        entries = os.listdir(_long(path))
    except OSError:
        return saved
    for name in entries:
        full = os.path.join(path, name)
        if os.path.isdir(_long(full)):
            directory_search(full, saved)
        else:
            saved.append(full)
    return saved


def is_within(child, parent):
    try:
        return os.path.commonpath([
            os.path.realpath(child), os.path.realpath(parent)
        ]) == os.path.realpath(parent)
    except ValueError:
        return False


def push_new_file(old_path, new_path):
    """Возвращает финальный путь (может отличаться при коллизии)."""
    parent = os.path.dirname(new_path)
    if parent:
        os.makedirs(_long(parent), exist_ok=True)
    shutil.move(_long(old_path), _long(new_path))
    return new_path


def move_files_into_root(main_root, path, conflicts=None):
    if conflicts is None:
        conflicts = {}
    for name in os.listdir(_long(path)):
        full = os.path.join(path, name)
        if os.path.isdir(_long(full)):
            move_files_into_root(main_root, full, conflicts)
        else:
            dst = os.path.join(main_root, name)
            if _exists(dst):
                parent_name = os.path.basename(os.path.dirname(full)) or "dup"
                alt_dir = os.path.join(main_root, "_conflicts", parent_name)
                os.makedirs(_long(alt_dir), exist_ok=True)
                alt = os.path.join(alt_dir, name)
                n = 1
                base, ext = os.path.splitext(alt)
                while _exists(alt):
                    alt = f"{base}_{n}{ext}"
                    n += 1
                shutil.move(_long(full), _long(alt))
                conflicts[full] = alt
            else:
                shutil.move(_long(full), _long(dst))
    return conflicts


def clear(path, keep_root=True):
    try:
        entries = os.listdir(_long(path))
    except OSError:
        return
    for name in entries:
        full = os.path.join(path, name)
        if os.path.isdir(_long(full)):
            clear(full, keep_root=False)
            try:
                if not os.listdir(_long(full)):
                    os.rmdir(_long(full))
            except OSError:
                pass
    if not keep_root:
        try:
            if not os.listdir(_long(path)):
                os.rmdir(_long(path))
        except OSError:
            pass


# ════════════════════════════════════════════════════════════════
#  Менеджер с dry-run
# ════════════════════════════════════════════════════════════════
def directory_tree_maker_manager(main_root, new_paths, programm_path,
                                 dry_run=False):
    """
    main_root:    корень
    new_paths:    [[old_abs, new_abs], ...]
    programm_path: куда писать saved_paths.json
    dry_run:      True — только отчёт, без перемещения
    """
    if not dry_run:
        saved = directory_search(main_root, [])
        os.makedirs(_long(programm_path), exist_ok=True)
        with open(os.path.join(programm_path, "saved_paths.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"saved_file_paths": saved}, f, ensure_ascii=False, indent=2)

    stats = {"moved": 0, "missing": 0, "outside": 0, "failed": 0,
             "would_move": 0, "conflicts": []}

    for old_path, new_path in new_paths:
        if not _exists(old_path):
            stats["missing"] += 1
            print(f"[missing] {old_path}")
            continue
        if not is_within(new_path, main_root):
            stats["outside"] += 1
            print(f"[outside] {new_path}")
            continue
        if os.path.abspath(old_path) == os.path.abspath(new_path):
            continue

        if dry_run:
            if _exists(new_path):
                stats["conflicts"].append((old_path, new_path))
                print(f"[dry] conflict {old_path} → {new_path}")
            else:
                print(f"[dry] {old_path} → {new_path}")
            stats["would_move"] += 1
            continue

        try:
            push_new_file(old_path, new_path)
            stats["moved"] += 1
        except Exception as e:
            stats["failed"] += 1
            print(f"[fail] {old_path} → {new_path}: {e}")

    if not dry_run:
        clear(main_root, keep_root=True)

    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}{stats}")
    return stats


# ════════════════════════════════════════════════════════════════
#  Мост анализатор → менеджер
# ════════════════════════════════════════════════════════════════
def apply_analyzer_output(main_root, new_paths_json, programm_path,
                          dry_run=False):
    with open(new_paths_json, "r", encoding="utf-8") as f:
        relative = json.load(f)

    if not isinstance(relative, list):
        raise ValueError(f"Ожидался массив, получено: {type(relative).__name__}")

    files = directory_search(main_root, [])
    by_name = {}
    for f in files:
        by_name.setdefault(os.path.basename(f), []).append(f)

    dup = {n: ps for n, ps in by_name.items() if len(ps) > 1}
    if dup:
        raise ValueError(f"Дубли имён: {list(dup.keys())[:5]}")

    pairs, unmatched, seen = [], [], set()
    for rel in relative:
        if not isinstance(rel, str):
            unmatched.append(repr(rel))
            continue
        rel = rel.replace("\\", "/").strip().lstrip("/")
        parts = [p for p in rel.split("/") if p and p not in (".", "..")]
        if len(parts) < 2:
            unmatched.append(rel)
            continue
        name = parts[-1]
        if name in seen or name not in by_name:
            unmatched.append(name)
            continue
        seen.add(name)
        pairs.append([by_name[name][0], os.path.join(main_root, *parts)])

    if unmatched:
        print(f"[bridge] не сопоставлено {len(unmatched)}: {unmatched[:5]}")

    return directory_tree_maker_manager(main_root, pairs, programm_path,
                                        dry_run=dry_run)


# ════════════════════════════════════════════════════════════════
#  Пример
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    MAIN = r"C:\Users\MSI\Downloads\gg2"
    PROG = r"C:\Users\MSI\Downloads\project_shlak"

    # 1. Сначала dry-run — посмотреть, что будет
    apply_analyzer_output(MAIN, os.path.join(PROG, "new_paths.json"), PROG,
                          dry_run=True)

    # 2. Убедились — раскомментируйте реальный запуск
    # apply_analyzer_output(MAIN, os.path.join(PROG, "new_paths.json"), PROG)