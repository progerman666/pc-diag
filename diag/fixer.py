"""Р‘РµР·РѕРїР°СЃРЅС‹Рµ РёСЃРїСЂР°РІР»РµРЅРёСЏ СЃРёСЃС‚РµРјС‹."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import winreg
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("fixer_log.jsonl")
BACKUP_DIR = Path("fixer_backups")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _human(n: int) -> str:
    for unit in ("Р‘", "РљР‘", "РњР‘", "Р“Р‘"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} РўР‘"


def _run_ps(cmd: str, timeout: int = 60) -> tuple[str, int]:
    full = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + cmd
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", full],
            capture_output=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out = None
        for enc in ("utf-8", "cp866", "cp1251"):
            try:
                out = r.stdout.decode(enc).strip()
                break
            except UnicodeDecodeError:
                continue
        if out is None:
            out = r.stdout.decode("utf-8", errors="replace").strip()
        return out, r.returncode
    except Exception as e:
        return f"[error: {e}]", 1


def _log(action: str, args: dict, result: dict, applied: bool):
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "action": action, "args": args,
        "applied": applied, "result": result,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _is_process_running(exe_name: str) -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
            capture_output=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out = r.stdout.decode("cp866", errors="replace")
        return exe_name.lower() in out.lower()
    except Exception:
        return False


def _dir_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    count, size = 0, 0
    try:
        for f in path.rglob("*"):
            try:
                if f.is_file():
                    size += f.stat().st_size
                    count += 1
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return count, size


def _dir_clean(path: Path) -> tuple[int, int, int]:
    freed, deleted, failed = 0, 0, 0
    if not path.exists():
        return 0, 0, 0
    for f in path.rglob("*"):
        try:
            if f.is_file():
                size = f.stat().st_size
                f.unlink()
                freed += size
                deleted += 1
        except (PermissionError, OSError):
            failed += 1
    return deleted, failed, freed


def _temp_dirs() -> list[Path]:
    dirs = []
    t = os.environ.get("TEMP")
    if t:
        dirs.append(Path(t))
    w = Path("C:/Windows/Temp")
    if w.exists():
        dirs.append(w)
    return dirs


def _scan_temp() -> dict:
    items = 0
    total = 0
    for d in _temp_dirs():
        c, s = _dir_stats(d)
        items += c
        total += s
    return {"files": items, "bytes": total}


def clean_temp_dry() -> dict:
    scan = _scan_temp()
    return {
        "detail": (
            f"РќР°Р№РґРµРЅРѕ {scan['files']} С„Р°Р№Р»РѕРІ РЅР° {_human(scan['bytes'])}. "
            f"Р‘СѓРґСѓС‚ СѓРґР°Р»РµРЅС‹ С„Р°Р№Р»С‹, РґРѕСЃС‚СѓРїРЅС‹Рµ РЅР° Р·Р°РїРёСЃСЊ. "
            f"Р—Р°РЅСЏС‚С‹Рµ (Р·Р°РїСѓС‰РµРЅРЅС‹Рµ РїСЂРѕРіСЂР°РјРјС‹) вЂ” РїСЂРѕРїСѓС‰РµРЅС‹.\n"
            f"РџР°РїРєРё: {', '.join(str(d) for d in _temp_dirs())}"
        ),
        "size_bytes": scan["bytes"],
    }


def clean_temp_apply() -> dict:
    freed = 0
    deleted = 0
    failed = 0
    for d in _temp_dirs():
        dl, fl, fr = _dir_clean(d)
        deleted += dl
        failed += fl
        freed += fr
    return {"deleted": deleted, "failed": failed, "freed_bytes": freed}


def clean_recycle_dry() -> dict:
    ps = (
        "$items = (New-Object -ComObject Shell.Application).NameSpace(0xA).Items(); "
        "$count = $items.Count; "
        "$sum = ($items | Measure-Object -Property Size -Sum).Sum; "
        "if ($null -eq $sum) { $sum = 0 }; "
        "[PSCustomObject]@{ Count=$count; Bytes=$sum } | ConvertTo-Json -Compress"
    )
    raw, rc = _run_ps(ps, timeout=30)
    count, size = 0, 0
    if rc == 0 and raw and not raw.startswith("[error"):
        try:
            data = json.loads(raw)
            count = data.get("Count", 0)
            size = data.get("Bytes", 0)
        except Exception:
            pass
    return {
        "detail": f"Р’ РєРѕСЂР·РёРЅРµ {count} РѕР±СЉРµРєС‚РѕРІ, РІСЃРµРіРѕ {_human(size)}.",
        "size_bytes": size,
    }


def clean_recycle_apply() -> dict:
    _run_ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", timeout=120)
    return {"done": True}


def _pip_cache_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "pip" / "cache"


def clean_pip_cache_dry() -> dict:
    path = _pip_cache_path()
    if not path.exists():
        return {"detail": f"РџР°РїРєР° РЅРµ РЅР°Р№РґРµРЅР°: {path}", "error": "not_found"}
    count, size = _dir_stats(path)
    return {
        "detail": (
            f"РќР°Р№РґРµРЅРѕ {count} С„Р°Р№Р»РѕРІ РЅР° {_human(size)} РІ {path}.\n"
            f"Р­С‚Рѕ РєСЌС€ СЃРєР°С‡Р°РЅРЅС‹С… РїР°РєРµС‚РѕРІ pip вЂ” РїСЂРё СЃР»РµРґСѓСЋС‰РµР№ СѓСЃС‚Р°РЅРѕРІРєРµ "
            f"pip СЃРєР°С‡Р°РµС‚ РёС… Р·Р°РЅРѕРІРѕ (РїСЂРё РЅР°Р»РёС‡РёРё РёРЅС‚РµСЂРЅРµС‚Р°)."
        ),
        "size_bytes": size,
    }


def clean_pip_cache_apply() -> dict:
    path = _pip_cache_path()
    deleted, failed, freed = _dir_clean(path)
    return {"deleted": deleted, "failed": failed, "freed_bytes": freed}


def _vscode_cache_paths() -> list[Path]:
    appdata = Path(os.environ.get("APPDATA", ""))
    return [
        appdata / "Code" / "Cache",
        appdata / "Code" / "CachedData",
        appdata / "Code" / "GPUCache",
        appdata / "Code" / "Code Cache",
    ]


def clean_vscode_cache_dry() -> dict:
    if _is_process_running("Code.exe"):
        return {
            "detail": "вќЊ VSCode Р·Р°РїСѓС‰РµРЅ. Р—Р°РєСЂРѕР№С‚Рµ РµРіРѕ Рё РїРѕРІС‚РѕСЂРёС‚Рµ.",
            "error": "vscode_running",
        }
    total_count = 0
    total_size = 0
    existing = []
    for p in _vscode_cache_paths():
        if p.exists():
            c, s = _dir_stats(p)
            total_count += c
            total_size += s
            existing.append(str(p))
    if not existing:
        return {"detail": "РљСЌС€ VSCode РЅРµ РЅР°Р№РґРµРЅ.", "error": "not_found"}
    return {
        "detail": (
            f"РќР°Р№РґРµРЅРѕ {total_count} С„Р°Р№Р»РѕРІ РЅР° {_human(total_size)}.\n"
            f"РџР°РїРєРё:\n  " + "\n  ".join(existing) + "\n"
            f"Р­С‚Рѕ РєСЌС€ VSCode вЂ” РїСЂРё СЃР»РµРґСѓСЋС‰РµРј Р·Р°РїСѓСЃРєРµ РѕРЅ СЃРѕР±РµСЂС‘С‚СЃСЏ Р·Р°РЅРѕРІРѕ."
        ),
        "size_bytes": total_size,
    }


def clean_vscode_cache_apply() -> dict:
    if _is_process_running("Code.exe"):
        return {"error": "vscode_running", "detail": "VSCode Р·Р°РїСѓС‰РµРЅ."}
    total_deleted = 0
    total_failed = 0
    total_freed = 0
    for p in _vscode_cache_paths():
        dl, fl, fr = _dir_clean(p)
        total_deleted += dl
        total_failed += fl
        total_freed += fr
    return {
        "deleted": total_deleted,
        "failed": total_failed,
        "freed_bytes": total_freed,
    }


def _thumbcache_dir() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft" / "Windows" / "Explorer"
    )


def clean_thumbnail_cache_dry() -> dict:
    d = _thumbcache_dir()
    if not d.exists():
        return {"detail": f"РџР°РїРєР° РЅРµ РЅР°Р№РґРµРЅР°: {d}", "error": "not_found"}
    files = list(d.glob("thumbcache_*.db"))
    if not files:
        return {"detail": "Р¤Р°Р№Р»С‹ thumbcache_*.db РЅРµ РЅР°Р№РґРµРЅС‹.", "error": "not_found"}
    size = sum(f.stat().st_size for f in files if f.exists())
    return {
        "detail": (
            f"РќР°Р№РґРµРЅРѕ {len(files)} С„Р°Р№Р»РѕРІ thumbcache РЅР° {_human(size)}.\n"
            f"Р­С‚Рѕ РєСЌС€ СЌСЃРєРёР·РѕРІ РџСЂРѕРІРѕРґРЅРёРєР° вЂ” РѕРЅ РїРµСЂРµСЃРѕР±РµСЂС‘С‚СЃСЏ РїСЂРё РїСЂРѕСЃРјРѕС‚СЂРµ РїР°РїРѕРє."
        ),
        "size_bytes": size,
    }


def clean_thumbnail_cache_apply() -> dict:
    d = _thumbcache_dir()
    deleted = 0
    failed = 0
    freed = 0
    for f in d.glob("thumbcache_*.db"):
        try:
            size = f.stat().st_size
            f.unlink()
            freed += size
            deleted += 1
        except (PermissionError, OSError):
            failed += 1
    return {"deleted": deleted, "failed": failed, "freed_bytes": freed}


def _get_startup_entries() -> list[dict]:
    ps = (
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name, Command, Location, User | "
        "ConvertTo-Json -Compress"
    )
    raw, rc = _run_ps(ps, timeout=20)
    if rc != 0 or not raw or raw == "null" or raw.startswith("[error"):
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        return []


def _find_run_entry(name: str):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                             winreg.KEY_READ)
    except FileNotFoundError:
        return None
    try:
        i = 0
        while True:
            try:
                val_name, val_data, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            if val_name.lower() == name.lower():
                winreg.CloseKey(key)
                return (val_name, val_data)
            i += 1
    finally:
        try:
            winreg.CloseKey(key)
        except Exception:
            pass
    return None


def disable_startup_dry(name: str) -> dict:
    entries = _get_startup_entries()
    matches = [e for e in entries
               if (e.get("Name") or "").lower() == name.lower()]
    if not matches:
        available = [e.get("Name") for e in entries[:15]]
        return {
            "detail": f"Р—Р°РїРёСЃСЊ '{name}' РЅРµ РЅР°Р№РґРµРЅР°. "
                      f"Р”РѕСЃС‚СѓРїРЅС‹Рµ: {available}",
            "error": "not_found",
        }
    entry = matches[0]
    hkcu = _find_run_entry(name)
    hkcu_line = (
        "Р‘СѓРґРµС‚ СѓРґР°Р»РµРЅР° РёР· HKCU\\...\\Run СЃ Р±СЌРєР°РїРѕРј РІ fixer_backups/."
        if hkcu else
        "РќР• РІ HKCU\\...\\Run вЂ” Р°РІС‚РѕРѕС‚РєР»СЋС‡РµРЅРёРµ РЅРµ РїРѕРґРґРµСЂР¶РёРІР°РµС‚СЃСЏ РґР»СЏ СЌС‚РѕР№ "
        "Р»РѕРєР°С†РёРё. РћС‚РєР»СЋС‡РёС‚Рµ РІСЂСѓС‡РЅСѓСЋ С‡РµСЂРµР· Р”РёСЃРїРµС‚С‡РµСЂ Р·Р°РґР°С‡ в†’ РђРІС‚РѕР·Р°РіСЂСѓР·РєР°."
    )
    return {
        "detail": (
            f"РРјСЏ:     {entry.get('Name')}\n"
            f"РљРѕРјР°РЅРґР°: {entry.get('Command')}\n"
            f"Р›РѕРєР°С†РёСЏ: {entry.get('Location')}\n"
            f"РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {entry.get('User')}\n\n"
            f"{hkcu_line}"
        ),
        "can_disable": hkcu is not None,
    }


def disable_startup_apply(name: str) -> dict:
    hkcu = _find_run_entry(name)
    if not hkcu:
        return {"error": "not_in_HKCU_Run",
                "detail": "Р—Р°РїРёСЃСЊ РЅРµ РІ HKCU\\...\\Run. РћС‚РєР»СЋС‡РёС‚Рµ РІСЂСѓС‡РЅСѓСЋ."}

    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"startup_{name}_{ts}.json"
    backup_file.write_text(
        json.dumps({"name": hkcu[0], "command": hkcu[1],
                    "key": f"HKCU\\{RUN_KEY}"},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                             winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, hkcu[0])
        winreg.CloseKey(key)
    except Exception as e:
        return {"error": str(e), "backup": str(backup_file)}

    return {"deleted": hkcu[0], "backup": str(backup_file)}


def _docker_available() -> bool:
    try:
        r = subprocess.run(
            ["docker", "--version"], capture_output=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return r.returncode == 0
    except Exception:
        return False


def docker_prune_dry() -> dict:
    if not _docker_available():
        return {"detail": "Docker РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ РёР»Рё РЅРµ РІ PATH.",
                "error": "no_docker"}
    try:
        r = subprocess.run(
            ["docker", "system", "df"],
            capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out = r.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return {"detail": f"РћС€РёР±РєР° docker: {e}", "error": "docker_error"}
    return {
        "detail": (
            "Р‘СѓРґСѓС‚ СѓРґР°Р»РµРЅС‹ Р’РЎР• РЅРµРёСЃРїРѕР»СЊР·СѓРµРјС‹Рµ РѕР±СЂР°Р·С‹, РєРѕРЅС‚РµР№РЅРµСЂС‹, СЃРµС‚Рё "
            "Рё build cache. Р—Р°РїСѓС‰РµРЅРЅС‹Рµ РєРѕРЅС‚РµР№РЅРµСЂС‹ Рё РёС… РѕР±СЂР°Р·С‹ РѕСЃС‚Р°РЅСѓС‚СЃСЏ.\n\n"
            f"РўРµРєСѓС‰РёР№ docker system df:\n{out}"
        ),
        "warning": "high_risk",
    }


def docker_prune_apply() -> dict:
    try:
        r = subprocess.run(
            ["docker", "system", "prune", "-a", "-f"],
            capture_output=True, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return {"output": r.stdout.decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": str(e)}


ACTIONS = {
    "clean_temp": {
        "title": "РћС‡РёСЃС‚РєР° РІСЂРµРјРµРЅРЅС‹С… С„Р°Р№Р»РѕРІ",
        "risk": "low", "needs_name": False,
        "dry": clean_temp_dry, "apply": clean_temp_apply,
    },
    "clean_recycle": {
        "title": "РћС‡РёСЃС‚РєР° РєРѕСЂР·РёРЅС‹",
        "risk": "low", "needs_name": False,
        "dry": clean_recycle_dry, "apply": clean_recycle_apply,
    },
    "clean_pip_cache": {
        "title": "РћС‡РёСЃС‚РєР° РєСЌС€Р° pip",
        "risk": "low", "needs_name": False,
        "dry": clean_pip_cache_dry, "apply": clean_pip_cache_apply,
    },
    "clean_vscode_cache": {
        "title": "РћС‡РёСЃС‚РєР° РєСЌС€Р° VSCode",
        "risk": "low", "needs_name": False,
        "dry": clean_vscode_cache_dry, "apply": clean_vscode_cache_apply,
    },
    "clean_thumbnail_cache": {
        "title": "РћС‡РёСЃС‚РєР° РєСЌС€Р° СЌСЃРєРёР·РѕРІ Windows",
        "risk": "low", "needs_name": False,
        "dry": clean_thumbnail_cache_dry, "apply": clean_thumbnail_cache_apply,
    },
    "disable_startup": {
        "title": "РћС‚РєР»СЋС‡РµРЅРёРµ Р·Р°РїРёСЃРё Р°РІС‚РѕР·Р°РіСЂСѓР·РєРё",
        "risk": "medium", "needs_name": True,
        "dry": disable_startup_dry, "apply": disable_startup_apply,
    },
    "docker_prune": {
        "title": "Docker prune (РІСЃРµ РЅРµРёСЃРїРѕР»СЊР·СѓРµРјС‹Рµ РѕР±СЂР°Р·С‹)",
        "risk": "high", "needs_name": False,
        "dry": docker_prune_dry, "apply": docker_prune_apply,
    },
}


def cmd_list():
    print("\nР”РѕСЃС‚СѓРїРЅС‹Рµ РґРµР№СЃС‚РІРёСЏ:\n")
    for key, a in ACTIONS.items():
        print(f"  {key:<22} [{a['risk'].upper():<6}]  {a['title']}")
    print(f"\nРСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ: python -m diag.fixer <action> [--apply] "
          f"[--name NAME]\n")


def cmd_log():
    if not LOG_PATH.exists():
        print("РСЃС‚РѕСЂРёСЏ РїСѓСЃС‚Р°.")
        return
    print(f"\nРСЃС‚РѕСЂРёСЏ ({LOG_PATH}):\n")
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            mark = "вњ…" if e.get("applied") else "рџ”Ќ"
            extra = ""
            if "freed_bytes" in e.get("result", {}):
                extra = f" freed={_human(e['result']['freed_bytes'])}"
            print(f"  {mark} {e['ts']}  {e['action']}{extra}")
    print()


def cmd_action(action_name: str, name: str | None, apply: bool):
    a = ACTIONS[action_name]
    print(f"\n{'=' * 60}")
    print(f"  {a['title']}  [{a['risk'].upper()}]")
    print(f"{'=' * 60}\n")

    dry_result = a["dry"](name) if a["needs_name"] else a["dry"]()
    print(dry_result.get("detail", ""))
    print()

    if dry_result.get("error"):
        _log(action_name, {"name": name} if name else {}, dry_result, False)
        return

    if dry_result.get("warning") == "high_risk":
        print("вљ пёЏ  Р’РќРРњРђРќРР•: РґРµР№СЃС‚РІРёРµ СѓРґР°Р»РёС‚ Docker-РѕР±СЂР°Р·С‹. "
              "РћС‚РєР°С‚ РЅРµРІРѕР·РјРѕР¶РµРЅ.\n")

    if not apply:
        print("Dry-run. Р§С‚РѕР±С‹ РІС‹РїРѕР»РЅРёС‚СЊ: РґРѕР±Р°РІСЊС‚Рµ --apply.\n")
        _log(action_name, {"name": name} if name else {}, dry_result, False)
        return

    answer = input("РџСЂРёРјРµРЅРёС‚СЊ? [y/N]: ").strip().lower()
    if answer not in ("y", "yes", "Рґ", "РґР°"):
        print("РћС‚РјРµРЅРµРЅРѕ.")
        return

    result = a["apply"](name) if a["needs_name"] else a["apply"]()

    print("\nР РµР·СѓР»СЊС‚Р°С‚:")
    for k, v in result.items():
        if "bytes" in k and isinstance(v, int):
            print(f"  {k}: {_human(v)}")
        else:
            print(f"  {k}: {v}")

    _log(action_name, {"name": name} if name else {}, result, True)
    print(f"\nР›РѕРі: {LOG_PATH}\n")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="diag.fixer")
    ap.add_argument("action", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--name")
    args = ap.parse_args(argv)

    if args.list or (not args.action and not args.log):
        cmd_list()
        return 0
    if args.log:
        cmd_log()
        return 0
    if args.action not in ACTIONS:
        print(f"РќРµРёР·РІРµСЃС‚РЅРѕРµ РґРµР№СЃС‚РІРёРµ: {args.action}")
        print(f"Р”РѕСЃС‚СѓРїРЅС‹Рµ: {', '.join(ACTIONS)}")
        return 1
    if ACTIONS[args.action]["needs_name"] and not args.name:
        print(f"Р”Р»СЏ {args.action} РЅСѓР¶РµРЅ --name")
        return 1
    cmd_action(args.action, args.name, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
