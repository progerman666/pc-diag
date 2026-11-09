"""Графический интерфейс pc-diag для широкой публики."""
import contextlib
import io
import os
import sys
import threading
import time
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

# ЖЕСТКАЯ НАСТРОЙКА UTF-8 ДЛЯ WINDOWS
# Это предотвращает кракозябры в консоли и при сборке в EXE
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr is not None:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import customtkinter as ctk

from diag.collectors import collect_all
from diag.rules import check
from diag.report import print_report
from diag import fixer
from diag.version import __version__

ASSETS = Path(__file__).parent / "assets"
ICON_PNG = ASSETS / "icon.png"
ICON_ICO = ASSETS / "icon.ico"

# Лог ошибок: чтобы у пользователя было что прислать, если что-то упало.
LOG_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "pc-diag"
LOG_PATH = LOG_DIR / "pc-diag.log"


def app_dir() -> Path:
    """Папка с exe (в собранной версии) или с исходниками."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()


def log_error(where: str, exc: BaseException) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] {where}\n")
            f.write("".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ))
    except Exception:
        pass


def is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin() -> bool:
    """Перезапускает приложение с запросом UAC. False — если отменили."""
    try:
        import ctypes
        exe = sys.executable
        params = "" if getattr(sys, "frozen", False) else f'"{Path(sys.argv[0]).resolve()}"'
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return rc > 32
    except Exception as exc:
        log_error("restart_as_admin", exc)
        return False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title(f"pc-diag {__version__} — диагностика Windows")
        self.geometry("980x760")
        self.minsize(820, 620)

        self._report_text = ""
        self._admin = is_admin()
        self._started_at: float | None = None
        self._set_window_icon()

        self._build_ui()

        # Диагностика стартует сама: пользователь открыл и сразу видит результат.
        self.after(500, self._on_start)

    # ── служебное ────────────────────────────────────────────────
    def _set_window_icon(self) -> None:
        """Иконка окна и панели задач: сначала .ico, потом .png."""
        if ICON_ICO.exists():
            try:
                self.iconbitmap(default=str(ICON_ICO))
                return
            except Exception as exc:
                log_error("icon:ico", exc)
        if ICON_PNG.exists():
            try:
                self.iconphoto(True, tk.PhotoImage(file=str(ICON_PNG)))
            except Exception as exc:
                log_error("icon:png", exc)

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def _ui(self, func, *args) -> None:
        """Обновление интерфейса из фонового потока."""
        try:
            self.after(0, func, *args)
        except Exception:
            pass

    def _show_error_dialog(self, title: str, exc: BaseException) -> None:
        text = f"{exc}"
        if len(text) > 500:
            text = text[:500] + "…"
        messagebox.showerror(title, f"{text}\n\nПодробности записаны в:\n{LOG_PATH}")

    def _build_ui(self):
        # Заголовок
        self.header = ctk.CTkLabel(
            self, text="pc-diag",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        self.header.pack(pady=(10, 4))

        self.subtitle = ctk.CTkLabel(
            self, text="Диагностика и безопасная очистка Windows",
            font=ctk.CTkFont(size=14), text_color="#b0b0b0",
        )
        self.subtitle.pack(pady=(0, 10))

        # Вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=0, fill="both", expand=True)

        self.tab_diag = self.tabview.add("Диагностика")
        self.tab_clean = self.tabview.add("Очистка")

        self._build_diag_tab()
        self._build_clean_tab()

    def _build_diag_tab(self):
        self.btn_start = ctk.CTkButton(
            self.tab_diag, text="🔍 Начать диагностику",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=48, command=self._on_start,
        )
        self.btn_start.pack(pady=(10, 8), padx=20, fill="x")

        self.status = ctk.CTkLabel(
            self.tab_diag, text="Готов к работе",
            font=ctk.CTkFont(size=12), text_color="#888",
        )
        self.status.pack(pady=(0, 4))

        self.summary = ctk.CTkLabel(
            self.tab_diag, text="",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#e0e0e0",
        )
        self.summary.pack(pady=(0, 6))

        if not self._admin:
            admin_row = ctk.CTkFrame(self.tab_diag, fg_color="transparent")
            admin_row.pack(pady=(0, 6), padx=20, fill="x")
            ctk.CTkLabel(
                admin_row,
                text="Без прав администратора часть SMART-данных "
                     "(износ, температура) недоступна.",
                font=ctk.CTkFont(size=11), text_color="#ffb86c", anchor="w",
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                admin_row, text="🛡 Запустить как администратор",
                width=230, height=28, command=self._on_elevate,
                fg_color="#3a3a3a", hover_color="#4a4a4a",
                font=ctk.CTkFont(size=12),
            ).pack(side="right")

        self.progress = ctk.CTkProgressBar(self.tab_diag, mode="indeterminate")
        self.progress.pack(pady=(0, 12), padx=20, fill="x")
        self.progress.set(0)

        self.textbox = ctk.CTkTextbox(
            self.tab_diag, font=ctk.CTkFont(family="Consolas", size=13),
            wrap="word",
        )
        self.textbox.pack(padx=20, pady=(0, 12), fill="both", expand=True)

        self.bottom = ctk.CTkFrame(self.tab_diag, fg_color="transparent")
        self.bottom.pack(padx=20, pady=(0, 10), fill="x")

        self.btn_save = ctk.CTkButton(
            self.bottom, text="💾 Сохранить отчёт",
            command=self._on_save, state="disabled",
        )
        self.btn_save.pack(side="left", padx=(0, 8))

        self.btn_open = ctk.CTkButton(
            self.bottom, text="📂 Папка программы",
            command=self._on_open_folder,
        )
        self.btn_open.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            self.bottom, text=f"v{__version__}",
            font=ctk.CTkFont(size=11), text_color="#666",
        ).pack(side="right")

    def _build_clean_tab(self):
        self.clean_frame = ctk.CTkScrollableFrame(self.tab_clean, fg_color="transparent")
        self.clean_frame.pack(padx=0, pady=0, fill="both", expand=True)

        actions = [
            ("clean_temp", "Временные файлы (TEMP)", "Безопасно. Удаляет мусор из временных папок."),
            ("clean_recycle", "Корзина", "Удаляет файлы из корзины. Откат невозможен."),
            ("clean_pip_cache", "Кэш pip", "Кэш Python-пакетов. При следующей установке скачается заново."),
            ("clean_thumbnail_cache", "Эскизы Windows", "Кэш картинок Проводника. Пересоберётся сам."),
            ("clean_vscode_cache", "Кэш VSCode", "Требует закрыть VSCode. Ускоряет работу редактора."),
        ]

        for key, title, desc in actions:
            self._create_clean_row(key, title, desc)

    def _create_clean_row(self, key, title, desc):
        row = ctk.CTkFrame(self.clean_frame)
        row.pack(fill="x", pady=6, padx=10)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=10, pady=5)

        ctk.CTkLabel(left, text=title, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(left, text=desc, font=ctk.CTkFont(size=12), text_color="#888", anchor="w").pack(fill="x")

        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=10)

        status_label = ctk.CTkLabel(right, text="", text_color="#b0b0b0", font=ctk.CTkFont(size=12))
        status_label.pack(side="left", padx=10)

        btn_clean = ctk.CTkButton(
            right, text="Очистить", width=100, state="disabled",
            fg_color="#444", hover_color="#555",
        )
        btn_clean.pack(side="right")

        btn_check = ctk.CTkButton(
            right, text="Проверить", width=100,
        )
        btn_check.pack(side="right", padx=5)

        state = {"check": btn_check, "clean": btn_clean}
        btn_check.configure(command=lambda: self._check_clean(key, status_label, state))
        btn_clean.configure(command=lambda: self._apply_clean(key, title, status_label, state))

    def _check_clean(self, key, status_label, state):
        check_btn, clean_btn = state["check"], state["clean"]
        check_btn.configure(state="disabled", text="Проверка...")
        clean_btn.configure(state="disabled", fg_color="#444", hover_color="#555")
        status_label.configure(text="Проверка...", text_color="#b0b0b0")

        def worker():
            try:
                result = getattr(fixer, f"{key}_dry")()
            except Exception as exc:
                log_error(f"check:{key}", exc)
                self._ui(self._on_check_done, key, status_label, state, None, exc)
            else:
                self._ui(self._on_check_done, key, status_label, state, result, None)

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_done(self, key, status_label, state, result, error):
        if not self._alive():
            return
        check_btn, clean_btn = state["check"], state["clean"]
        check_btn.configure(state="normal", text="Проверить")

        if error is not None:
            status_label.configure(text="Ошибка — см. лог", text_color="#ff5555")
            self._show_error_dialog("Проверка не удалась", error)
            return

        if result.get("error"):
            kind = result["error"]
            if kind == "vscode_running":
                status_label.configure(text="❌ Закройте VSCode", text_color="#ff5555")
            elif kind == "not_found":
                status_label.configure(text="не найдено", text_color="#888")
            else:
                status_label.configure(text="Ошибка", text_color="#ff5555")
            clean_btn.configure(state="disabled", fg_color="#444", hover_color="#555")
            return

        size = result.get("size_bytes", 0)
        status_label.configure(
            text=f"~{fixer._human(size)}", text_color="#ffb86c",
        )
        clean_btn.configure(
            state="normal", fg_color="#6daa45", hover_color="#5a9438",
        )

    def _apply_clean(self, key, title, status_label, state):
        if not messagebox.askyesno(
            "Подтверждение очистки",
            f"{title}\n\nОсвободить место? Отменить действие будет нельзя.",
        ):
            return

        check_btn, clean_btn = state["check"], state["clean"]
        check_btn.configure(state="disabled")
        clean_btn.configure(state="disabled", text="Ждите...")
        status_label.configure(text="Очистка...", text_color="#b0b0b0")

        def worker():
            try:
                result = getattr(fixer, f"{key}_apply")()
            except Exception as exc:
                log_error(f"clean:{key}", exc)
                self._ui(self._on_clean_done, key, status_label, state, None, exc)
            else:
                self._ui(self._on_clean_done, key, status_label, state, result, None)

        threading.Thread(target=worker, daemon=True).start()

    def _on_clean_done(self, key, status_label, state, result, error):
        if not self._alive():
            return
        check_btn, clean_btn = state["check"], state["clean"]
        check_btn.configure(state="normal")
        clean_btn.configure(
            state="disabled", text="Очистить", fg_color="#444", hover_color="#555",
        )

        if error is not None:
            status_label.configure(text="Ошибка — см. лог", text_color="#ff5555")
            self._show_error_dialog("Очистка не удалась", error)
            return

        if result.get("error"):
            if result["error"] == "vscode_running":
                status_label.configure(text="❌ Закройте VSCode", text_color="#ff5555")
            else:
                status_label.configure(text="Ошибка", text_color="#ff5555")
            return

        freed = int(result.get("freed_bytes", 0) or 0)
        human_size = fixer._human(freed)
        status_label.configure(
            text=f"✅ Освобождено: {human_size}", text_color="#6daa45",
        )

        lines = [f"Освобождено: {human_size}"]
        deleted = result.get("deleted")
        failed = result.get("failed")
        if isinstance(deleted, int):
            lines.append(f"Удалено файлов: {deleted}")
        if isinstance(failed, int) and failed:
            lines.append(f"Пропущено (заняты или нет прав): {failed}")
        messagebox.showinfo("Готово", "\n".join(lines))

    def _on_start(self):
        self.btn_start.configure(state="disabled", text="⏳ Собираю данные...")
        self.status.configure(text="Собираю данные... (30–60 секунд)")
        self.summary.configure(text="")
        self.progress.start()
        self.textbox.delete("1.0", "end")
        self._started_at = time.monotonic()
        threading.Thread(target=self._run_diagnostic, daemon=True).start()

    def _run_diagnostic(self):
        try:
            data = collect_all(skip_slow=True)
            findings = check(data)

            # Отчёт печатается в строку: так же, как в консольном режиме.
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                print_report(data, findings, llm_text=None)

            report = buf.getvalue()
            self._report_text = report
            self._ui(self._show_report, report, findings)
        except Exception as exc:
            log_error("diagnostic", exc)
            self._ui(self._show_error, exc)

    def _show_report(self, report: str, findings: list):
        if not self._alive():
            return
        self.progress.stop()
        self.progress.set(1)
        self.textbox.insert("1.0", report)
        self._update_summary(findings)

        elapsed = ""
        if self._started_at is not None:
            elapsed = f" за {time.monotonic() - self._started_at:.0f} с"
        self.status.configure(text=f"✅ Готово{elapsed}")
        self.btn_start.configure(state="normal", text="🔍 Проверить ещё раз")
        self.btn_save.configure(state="normal")

    def _update_summary(self, findings: list):
        if not self._alive():
            return
        if not findings:
            self.summary.configure(
                text="✅ Проблем не найдено", text_color="#6daa45",
            )
            return

        counts = {"high": 0, "medium": 0, "low": 0}
        for item in findings:
            sev = str(item.get("severity", "")).lower()
            if sev in counts:
                counts[sev] += 1

        parts = []
        if counts["high"]:
            parts.append(f"🔴 критичных: {counts['high']}")
        if counts["medium"]:
            parts.append(f"🟡 средних: {counts['medium']}")
        if counts["low"]:
            parts.append(f"🟢 мелочей: {counts['low']}")
        self.summary.configure(
            text="     ".join(parts) or f"найдок: {len(findings)}",
            text_color="#e0e0e0",
        )

    def _show_error(self, exc: BaseException):
        if not self._alive():
            return
        self.progress.stop()
        self.progress.set(0)
        self.status.configure(text="❌ Не удалось собрать данные")
        self.btn_start.configure(state="normal", text="🔍 Повторить")
        self._show_error_dialog("Ошибка диагностики", exc)

    def _on_elevate(self):
        if not messagebox.askyesno(
            "Права администратора",
            "Программа перезапустится с повышением прав — Windows покажет "
            "запрос. Текущее окно закроется.\n\nПродолжить?",
        ):
            return
        if restart_as_admin():
            self.destroy()
        else:
            messagebox.showwarning(
                "Не удалось",
                "Запрос прав отклонён или отменён.\n"
                "Можно закрыть программу и запустить её через "
                "«Запуск от имени администратора».",
            )

    def _on_save(self):
        if not self._report_text:
            return
        docs = Path.home() / "Documents"
        initial_dir = docs if docs.exists() else Path.home()
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Куда сохранить отчёт",
            initialdir=str(initial_dir),
            initialfile=f"pc-diag-report_{stamp}.txt",
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self._report_text, encoding="utf-8")
        except Exception as exc:
            log_error("save_report", exc)
            self._show_error_dialog("Не удалось сохранить отчёт", exc)
            return
        messagebox.showinfo("Сохранено", f"Отчёт сохранён:\n{path}")

    def _on_open_folder(self):
        try:
            os.startfile(str(app_dir()))
        except Exception as exc:
            log_error("open_folder", exc)
            self._show_error_dialog("Не удалось открыть папку", exc)


def main() -> int:
    try:
        app = App()
        app.mainloop()
    except Exception as exc:
        log_error("main", exc)
        try:
            messagebox.showerror(
                "pc-diag",
                f"Программа не смогла запуститься:\n{exc}\n\nПодробности:\n{LOG_PATH}",
            )
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    main()