"""РћРїС†РёРѕРЅР°Р»СЊРЅС‹Р№ СЃР»РѕР№: LLM РѕР±СЉСЏСЃРЅСЏРµС‚ РЅР°С…РѕРґРєРё С‡РµР»РѕРІРµС‡РµСЃРєРёРј СЏР·С‹РєРѕРј.
   РќРµ РІС‹РїРѕР»РЅСЏРµС‚ РЅРёРєР°РєРёС… РґРµР№СЃС‚РІРёР№ вЂ” С‚РѕР»СЊРєРѕ С‚РµРєСЃС‚.

   Р‘СЌРєРµРЅРґС‹:
   - Ollama (Р»РѕРєР°Р»СЊРЅРѕ, СЂР°Р±РѕС‚Р°РµС‚ РІ Р Р¤ Р±РµР· Р±Р»РѕРєРёСЂРѕРІРѕРє) вЂ” РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ
   - Anthropic (РµСЃР»Рё LLM_BACKEND=anthropic Рё РµСЃС‚СЊ ANTHROPIC_API_KEY)
"""
import json
import os


PROMPT = """РўС‹ вЂ” РѕРїС‹С‚РЅС‹Р№ СЃРёСЃС‚РµРјРЅС‹Р№ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ Windows. РўРµР±Рµ РґР°Р»Рё JSON
СЃ РґРёР°РіРЅРѕСЃС‚РёРєРѕР№ Рё СЃРїРёСЃРѕРє РЅР°Р№РґРµРЅРЅС‹С… РїСЂРѕР±Р»РµРј (findings).

РЎРўР РћР“РР• РџР РђР’РР›Рђ:

1. РџСЂРѕР№РґРё РїРѕ РљРђР–Р”РћРњРЈ finding РёР· СЃРїРёСЃРєР°. Р”Р»СЏ РєР°Р¶РґРѕРіРѕ вЂ” РѕРґРЅРѕ РєРѕСЂРѕС‚РєРѕРµ
   РїСЂРµРґР»РѕР¶РµРЅРёРµ СЃ РєРѕРЅРєСЂРµС‚РЅС‹Рј С€Р°РіРѕРј. РќРµ РѕСЃС‚Р°РЅР°РІР»РёРІР°Р№СЃСЏ РЅР° РїРµСЂРІРѕРј.
   Р•СЃР»Рё findings 5 вЂ” РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РјРёРЅРёРјСѓРј 5 РїСЂРµРґР»РѕР¶РµРЅРёР№.
2. РџРѕСЂСЏРґРѕРє: СЃРЅР°С‡Р°Р»Р° severity=high, РїРѕС‚РѕРј medium, РїРѕС‚РѕРј low.
3. Р”Р»СЏ РєР°Р¶РґРѕР№ РїСЂРѕР±Р»РµРјС‹ РЅР°Р·РѕРІРё РћР”РРќ РєРѕРЅРєСЂРµС‚РЅС‹Р№ С€Р°Рі: РєРѕРјР°РЅРґСѓ, РЅР°СЃС‚СЂРѕР№РєСѓ,
   РєСѓРґР° Р·Р°Р№С‚Рё. РќРµ В«РїСЂРѕРІРµСЂСЊС‚РµВ», Р° В«РѕС‚РєСЂРѕР№С‚Рµ РџР°СЂР°РјРµС‚СЂС‹ в†’ РЎРёСЃС‚РµРјР° в†’ РџР°РјСЏС‚СЊ
   в†’ Р’СЂРµРјРµРЅРЅС‹Рµ С„Р°Р№Р»С‹В».
4. Р•СЃР»Рё РµСЃС‚СЊ РєСЂСѓРїРЅС‹Рµ РїР°РїРєРё (folder_sizes) вЂ” РЅР°Р·РѕРІРё РєРѕРЅРєСЂРµС‚РЅСѓСЋ РїР°РїРєСѓ
   Рё РµС‘ СЂР°Р·РјРµСЂ. РќР°РїСЂРёРјРµСЂ: В«Р’ AppData 46 Р“Р‘ вЂ” РїСЂРѕРІРµСЂСЊС‚Рµ
   AppData\\Local\\Docker Рё РєСЌС€Рё Р±СЂР°СѓР·РµСЂРѕРІВ».
5. Р•СЃР»Рё РїСЂРѕР±Р»РµРјР° СЃ SSD (Wear) вЂ” СЃРєР°Р¶Рё, СЃРєРѕР»СЊРєРѕ РїСЂРѕС†РµРЅС‚РѕРІ РѕСЃС‚Р°Р»РѕСЃСЊ,
   Рё С‡С‚Рѕ РґРµР»Р°С‚СЊ (Р±СЌРєР°Рї, СЃР»РµРґРёС‚СЊ, РїР»Р°РЅРёСЂРѕРІР°С‚СЊ Р·Р°РјРµРЅСѓ).
6. РќР• РІС‹РґСѓРјС‹РІР°Р№ РїСЂРѕРіСЂР°РјРјС‹, РєРѕС‚РѕСЂС‹С… РЅРµС‚ РІ РґР°РЅРЅС‹С…. Р•СЃР»Рё РІРёРґРёС€СЊ Code.exe вЂ”
   РіРѕРІРѕСЂРё Code.exe, РЅРµ В«SteamВ» Рё РЅРµ В«ChromeВ».
7. РќРµ РїРёС€Рё C:\\\\ вЂ” РїРёС€Рё C:\\. Р­С‚Рѕ РїСѓС‚СЊ, РЅРµ escape-РїРѕСЃР»РµРґРѕРІР°С‚РµР»СЊРЅРѕСЃС‚СЊ.
8. 6вЂ“10 РїСЂРµРґР»РѕР¶РµРЅРёР№. РџРѕ-СЂСѓСЃСЃРєРё. РќР° В«РІС‹В». Р‘РµР· РІРѕРґС‹.
9. Р•СЃР»Рё РІСЃРµ findings РЅРёР·РєРѕРіРѕ РїСЂРёРѕСЂРёС‚РµС‚Р° вЂ” С‚Р°Рє Рё СЃРєР°Р¶Рё РѕРґРЅРѕР№ С„СЂР°Р·РѕР№.

Р”Р°РЅРЅС‹Рµ:
{data}

Findings:
{findings}
"""


def _slim(data: dict) -> dict:
    """РўРѕР»СЊРєРѕ С‚Рѕ, С‡С‚Рѕ СЂРµР°Р»СЊРЅРѕ РЅСѓР¶РЅРѕ LLM РґР»СЏ РѕР±СЉСЏСЃРЅРµРЅРёСЏ.
    Р’Р°Р¶РЅРѕ: РІРєР»СЋС‡Р°РµРј disk_health (Wear, temperature) Рё folder_sizes,
    РёРЅР°С‡Рµ РјРѕРґРµР»СЊ РЅРµ РІРёРґРёС‚ РёР·РЅРѕСЃ SSD Рё РєСЂСѓРїРЅС‹Рµ РїР°РїРєРё."""
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
    """Р›РѕРєР°Р»СЊРЅР°СЏ РјРѕРґРµР»СЊ С‡РµСЂРµР· Ollama. РќРёРєР°РєРёС… СЃРµС‚РµРІС‹С… Р±Р»РѕРєРёСЂРѕРІРѕРє."""
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
            f"[Ollama error: {e}. РџСЂРѕРІРµСЂСЊС‚Рµ, С‡С‚Рѕ Ollama Р·Р°РїСѓС‰РµРЅ "
            f"Рё РјРѕРґРµР»СЊ {model} СЃРєР°С‡Р°РЅР°: ollama list]"
        )


def _explain_anthropic(prompt: str) -> str | None:
    """РћР±Р»Р°С‡РЅС‹Р№ Claude. Р’ Р Р¤ РѕС‚РґР°С‘С‚ 403 вЂ” РѕСЃС‚Р°РІР»РµРЅ РґР»СЏ РґСЂСѓРіРёС… СЂРµРіРёРѕРЅРѕРІ."""
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
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ С‚РµРєСЃС‚РѕРІРѕРµ РѕР±СЉСЏСЃРЅРµРЅРёРµ РёР»Рё None."""
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    prompt = _build_prompt(data, findings)
    if backend == "anthropic":
        return _explain_anthropic(prompt)
    return _explain_ollama(prompt)
