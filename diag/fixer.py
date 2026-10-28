"""Безопасные исправления системы.

Каждое действие:
1. Сначала dry-run — показывает, что будет сделано.
2. Требует явного --apply и подтверждения y/N.
3. Логируется в fixer_log.jsonl.
4. Для disable_startup — бэкап в fixer_backups/.

Использование:
    python -m diag.fixer --list
    python -m diag.fixer clean_temp              # dry-run
    python -m diag.fixer clean_temp --apply      # применить
    python -m diag.fixer disable_startup --name OneDrive --apply
    python -m diag.fixer --log
"""
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


# ─── Утилиты ──────────────────────────────────────────────────────────

def _human(n: int) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ТБ"


def _run_ps(cmd: str, timeout: int = 60) -> tuple[str, int]:
    full = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + cmd
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", full],
            capture_output=True, timeout=timeout,
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


# ─── clean_temp ───────────────────────────────────────────────────────

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
        if not d.exists():
            continue
        for f in d.rglob("*"):
            try:
                if f.is_file():
                    total += f.stat().st_size
                    items += 1
            except (PermissionError, OSError):
                continue
    return {"files": items, "bytes": total}


def clean_temp_dry() -> dict:
    scan = _scan_temp()
    return {
        "detail": (
            f"Найдено {scan['files']} файлов на {_human(scan['bytes'])}. "
            f"Будут удалены файлы, доступные на запись. "
            f"Занятые (запущенные программы) — пропущены.\n"
            f"Папки: {', '.join(str(d) for d in _temp_dirs())}"
        ),
        "size_bytes": scan["bytes"],
    }


def clean_temp_apply() -> dict:
    freed = 0
    deleted = 0
    failed = 0
    for d in _temp_dirs():
        if not d.exists():
            continue
        for f in d.rglob("*"):
            try:
                if not f.is_file():
                    continue
                size = f.stat().st_size
                f.unlink()
                freed += size
                deleted += 1
            except (PermissionError, OSError):
                failed += 1
    return {"deleted": deleted, "failed": failed, "freed_bytes": freed}


# ─── clean_recycle ────────────────────────────────────────────────────

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
        "detail": f"В корзине {count} объектов, всего {_human(size)}.",
        "size_bytes": size,
    }


def clean_recycle_apply() -> dict:
    _run_ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", timeout=120)
    return {"done": True}


# ─── disable_startup ──────────────────────────────────────────────────

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
    """Ищет запись в HKCU\\...\\Run. Возвращает (name, command) или None."""
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
            "detail": f"Запись '{name}' не найдена. "
                      f"Доступные: {available}",
            "error": "not_found",
        }
    entry = matches[0]
    hkcu = _find_run_entry(name)
    hkcu_line = (
        "Будет удалена из HKCU\\...\\Run с бэкапом в fixer_backups/."
        if hkcu else
        "НЕ в HKCU\\...\\Run — автоотключение не поддерживается для этой "
        "локации. Отключите вручную через Диспетчер задач → Автозагрузка."
    )
    return {
        "detail": (
            f"Имя:     {entry.get('Name')}\n"
            f"Команда: {entry.get('Command')}\n"
            f"Локация: {entry.get('Location')}\n"
            f"Пользователь: {entry.get('User')}\n\n"
            f"{hkcu_line}"
        ),
        "can_disable": hkcu is not None,
    }


def disable_startup_apply(name: str) -> dict:
    hkcu = _find_run_entry(name)
    if not hkcu:
        return {"error": "not_in_HKCU_Run",
                "detail": "Запись не в HKCU\\...\\Run. Отключите вручную."}

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


# ─── docker_prune ─────────────────────────────────────────────────────

def _docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "--version"], capture_output=True,
                           timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def docker_prune_dry() -> dict:
    if not _docker_available():
        return {"detail": "Docker не установлен или не в PATH.",
                "error": "no_docker"}
    try:
        r = subprocess.run(["docker", "system", "df"],
                           capture_output=True, timeout=30)
        out = r.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return {"detail": f"Ошибка docker: {e}", "error": "docker_error"}
    return {
        "detail": (
            "Будут удалены ВСЕ неиспользуемые образы, контейнеры, сети "
            "и build cache. Запущенные контейнеры и их образы останутся.\n\n"
            f"Текущий docker system df:\n{out}"
        ),
        "warning": "high_risk",
    }


def docker_prune_apply() -> dict:
    try:
        r = subprocess.run(["docker", "system", "prune", "-a", "-f"],
                           capture_output=True, timeout=300)
        return {"output": r.stdout.decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": str(e)}


# ─── Реестр действий ──────────────────────────────────────────────────

ACTIONS = {
    "clean_temp": {
        "title": "Очистка временных файлов",
        "risk": "low", "needs_name": False,
        "dry": clean_temp_dry, "apply": clean_temp_apply,
    },
    "clean_recycle": {
        "title": "Очистка корзины",
        "risk": "low", "needs_name": False,
        "dry": clean_recycle_dry, "apply": clean_recycle_apply,
    },
    "disable_startup": {
        "title": "Отключение записи автозагрузки",
        "risk": "medium", "needs_name": True,
        "dry": disable_startup_dry, "apply": disable_startup_apply,
    },
    "docker_prune": {
        "title": "Docker prune (все неиспользуемые образы)",
        "risk": "high", "needs_name": False,
        "dry": docker_prune_dry, "apply": docker_prune_apply,
    },
}


# ─── CLI ──────────────────────────────────────────────────────────────

def cmd_list():
    print("\nДоступные действия:\n")
    for key, a in ACTIONS.items():
        print(f"  {key:<18} [{a['risk'].upper():<6}]  {a['title']}")
    print(f"\nИспользование: python -m diag.fixer <action> [--apply] "
          f"[--name NAME]\n")


def cmd_log():
    if not LOG_PATH.exists():
        print("История пуста.")
        return
    print(f"\nИстория ({LOG_PATH}):\n")
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            mark = "✅" if e.get("applied") else "🔍"
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
        print("⚠️  ВНИМАНИЕ: действие удалит Docker-образы. "
              "Откат невозможен.\n")

    if not apply:
        print("Dry-run. Чтобы выполнить: добавьте --apply.\n")
        _log(action_name, {"name": name} if name else {}, dry_result, False)
        return

    answer = input("Применить? [y/N]: ").strip().lower()
    if answer not in ("y", "yes", "д", "да"):
        print("Отменено.")
        return

    result = a["apply"](name) if a["needs_name"] else a["apply"]()

    print("\nРезультат:")
    for k, v in result.items():
        if "bytes" in k and isinstance(v, int):
            print(f"  {k}: {_human(v)}")
        else:
            print(f"  {k}: {v}")

    _log(action_name, {"name": name} if name else {}, result, True)
    print(f"\nЛог: {LOG_PATH}\n")


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
        print(f"Неизвестное действие: {args.action}")
        print(f"Доступные: {', '.join(ACTIONS)}")
        return 1
    if ACTIONS[args.action]["needs_name"] and not args.name:
        print(f"Для {args.action} нужен --name")
        return 1
    cmd_action(args.action, args.name, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())