"""Вывод в консоль Windows: UTF-8 без падений на псевдографике и эмодзи.

На русской Windows консоль по умолчанию cp866/cp1251, и print() отчёта
падает с UnicodeEncodeError на символах █ и 🟢. Здесь мы переключаем и
кодовую страницу консоли, и сами потоки на UTF-8.
"""
import os
import sys


def init_console() -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass

    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
