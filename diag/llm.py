"""Опциональный слой: LLM объясняет находки человеческим языком.
   Не выполняет никаких действий — только текст.

   Бэкенды:
   - Ollama (локально, работает в РФ без блокировок) — по умолчанию
   - Anthropic (если LLM_BACKEND=anthropic и есть ANTHROPIC_API_KEY)
"""
import json
import os


PROMPT = """Ты — опытный системный администратор Windows. Тебе дали JSON
с диагностикой и список найденных проблем (findings).

СТРОГИЕ ПРАВИЛА:

1. Пройди по КАЖДОМУ finding из списка. Для каждого — одно короткое
   предложение с конкретным шагом. Не останавливайся на первом.
   Если findings 5 — должно быть минимум 5 предложений.
2. Порядок: сначала severity=high, потом medium, потом low.
3. Для каждой проблемы назови ОДИН конкретный шаг: команду, настройку,
   куда зайти. Не «проверьте», а «откройте Параметры → Система → Память
   → Временные файлы».
4. Если есть крупные папки (folder_sizes) — назови конкретную папку
   и её размер. Например: «В AppData 46 ГБ — проверьте
   AppData\\Local\\Docker и кэши браузеров».
5. Если проблема с SSD (Wear) — скажи, сколько процентов осталось,
   и что делать (бэкап, следить, планировать замену).
6. НЕ выдумывай программы, которых нет в данных. Если видишь Code.exe —
   говори Code.exe, не «Steam» и не «Chrome».
7. Не пиши C:\\\\ — пиши C:\\. Это путь, не escape-последовательность.
8. 6–10 предложений. По-русски. На «вы». Без воды.
9. Если все findings низкого приоритета — так и скажи одной фразой.

Данные:
{data}

Findings:
{findings}
"""


def _slim(data: dict) -> dict:
    """Только то, что реально нужно LLM для объяснения.
    Важно: включаем disk_health (Wear, temperature) и folder_sizes,
    иначе модель не видит износ SSD и крупные папки."""
    return {
        "load": data.get("load", {}),
        "disks": data.get("disks", []),
        "disk_health": [
            {
                "model": d.get("model"),
                "health": d.get("health_status"),
                "wear_pct": d.get("wear"),
                "temp_c": d.get("temperature"),
                "power_on_hours": d.get("power_on_hours"),
                "predict_failure": d.get("predict_failure"),
            }
            for d in data.get("disk_health", [])
        ],
        "folder_sizes": data.get("folder_sizes", [])[:8],
        "network": {
            "gateway": data.get("network", {}).get("gateway"),
            "pings": data.get("network", {}).get("pings", []),
        },
        "event_errors_count": len(data.get("event_errors", [])),
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
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 400,
                },
            },
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip() or None
    except Exception as e:
        return (
            f"[Ollama error: {e}. Проверьте, что Ollama запущен "
            f"и модель {model} скачана: ollama list]"
        )


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