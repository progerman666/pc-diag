"""python -m diag [--no-llm] [--slow] [--json out.json]

РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ вЂ” Р±С‹СЃС‚СЂС‹Р№ СЂРµР¶РёРј (Р±РµР· СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ РїР°РїРѕРє, 30-60 СЃРµРє).
--slow РІРєР»СЋС‡Р°РµС‚ СЃРєР°РЅРёСЂРѕРІР°РЅРёРµ СЂР°Р·РјРµСЂРѕРІ РїР°РїРѕРє (РјРѕР¶РµС‚ Р·Р°РЅСЏС‚СЊ 1-3 РјРёРЅ).
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .collectors import collect_all
from .rules import check
from .report import print_report
from . import llm


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(
        prog="diag",
        description="Р”РёР°РіРЅРѕСЃС‚РёРєР° Windows: read-only СЃР±РѕСЂ РґР°РЅРЅС‹С… + РїСЂР°РІРёР»Р° "
                    "+ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ) LLM-РѕР±СЉСЏСЃРЅРµРЅРёРµ.",
    )
    ap.add_argument(
        "--no-llm", action="store_true",
        help="РќРµ РѕР±СЂР°С‰Р°С‚СЊСЃСЏ Рє LLM, С‚РѕР»СЊРєРѕ РїСЂР°РІРёР»Р° Рё РґР°РЅРЅС‹Рµ",
    )
    ap.add_argument(
        "--slow", action="store_true",
        help="Р’РєР»СЋС‡РёС‚СЊ СЃРєР°РЅРёСЂРѕРІР°РЅРёРµ СЂР°Р·РјРµСЂРѕРІ РїР°РїРѕРє (РјРµРґР»РµРЅРЅРѕ, 1-3 РјРёРЅ)",
    )
    ap.add_argument(
        "--json", type=str, default=None, metavar="FILE",
        help="РЎРѕС…СЂР°РЅРёС‚СЊ РїРѕР»РЅС‹Р№ РѕС‚С‡С‘С‚ (data + findings + llm) РІ JSON",
    )
    args = ap.parse_args()

    print("РЎРѕР±РёСЂР°СЋ РґР°РЅРЅС‹Рµ (СЌС‚Рѕ Р·Р°РЅРёРјР°РµС‚ РЅРµСЃРєРѕР»СЊРєРѕ СЃРµРєСѓРЅРґ)...")
    if args.slow:
        print("  РЎРєР°РЅРёСЂСѓСЋ СЂР°Р·РјРµСЂС‹ РїР°РїРѕРє вЂ” РјРѕР¶РµС‚ Р·Р°РЅСЏС‚СЊ РґРѕ РјРёРЅСѓС‚С‹...")
    data = collect_all(skip_slow=not args.slow)
    findings = check(data)

    llm_text = None
    if not args.no_llm:
        llm_text = llm.explain(data, findings)

    print_report(data, findings, llm_text)

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {"data": data, "findings": findings, "llm": llm_text},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"JSON СЃРѕС…СЂР°РЅС‘РЅ: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
