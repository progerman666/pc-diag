"""python -m diag [--no-llm] [--slow] [--json out.json]

По умолчанию — быстрый режим (без сканирования папок, 30-60 сек).
--slow включает сканирование размеров папок (может занять 1-3 мин).
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .collectors import collect_all
from .console import init_console
from .rules import check
from .report import print_report
from . import llm


def main() -> int:
    init_console()
    load_dotenv()
    ap = argparse.ArgumentParser(
        prog="diag",
        description="Диагностика Windows: read-only сбор данных + правила "
                    "+ (опционально) LLM-объяснение.",
    )
    ap.add_argument(
        "--no-llm", action="store_true",
        help="Не обращаться к LLM, только правила и данные",
    )
    ap.add_argument(
        "--slow", action="store_true",
        help="Включить сканирование размеров папок (медленно, 1-3 мин)",
    )
    ap.add_argument(
        "--json", type=str, default=None, metavar="FILE",
        help="Сохранить полный отчёт (data + findings + llm) в JSON",
    )
    args = ap.parse_args()

    print("Собираю данные (это занимает несколько секунд)...")
    if args.slow:
        print("  Сканирую размеры папок — может занять до минуты...")
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
        print(f"JSON сохранён: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
