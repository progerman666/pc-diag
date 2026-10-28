"""Опциональный слой: LLM объясняет находки человеческим языком.
   Не выполняет никаких действий — только текст.

   Поддерживает два бэкенда:
   - Ollama (локально, работает в РФ без блокировок) — по умолчанию
   - Anthropic (если LLM_BACKEND=anthropic и есть ANTHROPIC_API_KEY)
"""
import json
import os


PROMPT = """Ты — опытный системный администратор Windows. Тебе дали
результаты диагностики компьютера в виде JSON и список найденных проблем.

Задача — короткий разбор (5–8 предложений) на русском:

1. Начни с САМОЙ важной проблемы (severity=high важнее medium).
2. Для каждой проблемы из списка назови ОДИН конкретный шаг —
   команду, настройку или куда зайти. Без «стоит проверить» —
   конкретика: «Откройте Параметры → Система → Память → Временные файлы».
3. Если проблема — диск, назови текущий процент и что удалить
   в первую очередь (Docker, Steam, cleanmgr, Windows.old).
4. Если проблема — Event Log, упомяни конкретные ID (7000, 10010, 1801)
   и что они обычно означают.
5. Не выдумывай проблем, которых нет в findings.
6. Не предлагай команд, которые меняют реестр или файлы — только
   диагностика и безопасные шаги.
7. Обращайся на «вы». Без воды и без общих фраз.

Данные диагностики:
{data}

Найденные проблемы:
{findings}
"""


def _slim(data: dict) -> dict:
    return {
        "system": data.get("system", {}),
        "load": data.get("load", {}),
        "disks": data.get("disks", []),
        "top_ram": data.get("processes", {}).get("top_ram", [])[:5],
        "top_cpu": data.get("processes", {}).get("top_cpu", [])[:5],
        "event_errors": data.get("event_errors", [])[:10],
        "startup_count": len(data.get("startup", [])),
    }


def _build_prompt(data: dict, findings: list[dict]) -> str:
    return PROMPT.format(
        data=json.dumps(_slim(data), ensure_ascii=False, indent=2),
        findings=json.dumps(findings, ensure_ascii=False, indent=2),
    )


def _explain_ollama(prompt: str) -> str | None:
    """Локальная модель через Ollama. Никаких сетевых блокировок."""
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        import requests
        resp = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip() or None
    except Exception as e:
        return f"[Ollama error: {e}. Проверьте, что Ollama запущен и модель {model} скачана: ollama list]"


def _explain_anthropic(prompt: str) -> str | None:
    """Облачный Claude. В РФ отдаёт 403 — оставлен для других регионов."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None
    client = Anthropic(api_key=key)
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"[LLM error: {e}]"


def explain(data: dict, findings: list[dict]) -> str | None:
    """Возвращает текстовое объяснение или None."""
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    prompt = _build_prompt(data, findings)
    if backend == "anthropic":
        return _explain_anthropic(prompt)
    return _explain_ollama(prompt)