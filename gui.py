"""Графический интерфейс pc-diag для широкой публики."""
import io
import contextlib
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

from diag.collectors import collect_all
from diag.rules import check
from diag.report import print_report
from diag import fixer

ASSETS = Path(__file__).parent / "assets"
ICON_PNG = ASSETS / "icon.png"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title("pc-diag — диагностика Windows")
        self.geometry("950x750")
        self.minsize(800, 600)

        if ICON_PNG.exists():
            try:
                self.iconphoto(True, tk.PhotoImage(file=str(ICON_PNG)))
            except Exception:
                pass

        self._report_text = ""
        self._build_ui()

    def _build_ui(self):
        # Заголовок (общий для обеих вкладок)
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
        self.status.pack(pady=(0, 8))

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
            self.bottom, text="📂 Открыть папку",
            command=self._on_open_folder, state="disabled",
        )
        self.btn_open.pack(side="left", padx=(0, 8))

    def _build_clean_tab(self):
        # Прокручиваемый фрейм для кнопок очистки
        self.clean_frame = ctk.CTkScrollableFrame(self.tab_clean, fg_color="transparent")
        self.clean_frame.pack(padx=0, pady=0, fill="both", expand=True)

        # Список действий: (ключ, название, описание)
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

        # Левая часть: название и описание
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=10, pady=5)

        ctk.CTkLabel(left, text=title, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(left, text=desc, font=ctk.CTkFont(size=12), text_color="#888", anchor="w").pack(fill="x")

        # Правая часть: статус и кнопки
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
            command=lambda: self._check_clean(key, status_label, btn_clean)
        )
        btn_check.pack(side="right", padx=5)

        # Сохраняем ссылки, чтобы кнопка "Очистить" знала, что запускать
        btn_clean.configure(command=lambda: self._apply_clean(key, status_label, btn_clean))

    def _check_clean(self, key, status_label, btn_clean):
        status_label.configure(text="Проверка...", text_color="#b0b0b0")
        self.update()

        dry_func = getattr(fixer, f"{key}_dry")
        try:
            result = dry_func()
            if result.get("error"):
                if result["error"] == "vscode_running":
                    status_label.configure(text="❌ Закройте VSCode", text_color="#ff5555")
                else:
                    status_label.configure(text="Ошибка", text_color="#ff5555")
                btn_clean.configure(state="disabled")
            else:
                size = result.get("size_bytes", 0)
                human_size = fixer._human(size)
                status_label.configure(text=f"~{human_size}", text_color="#ffb86c")
                btn_clean.configure(state="normal", fg_color="#6daa45", hover_color="#5a9438")
        except Exception as e:
            status_label.configure(text="Ошибка", text_color="#ff5555")

    def _apply_clean(self, key, status_label, btn_clean):
        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите выполнить очистку?"):
            return

        status_label.configure(text="Очистка...", text_color="#b0b0b0")
        btn_clean.configure(state="disabled", text="Ждите...")
        self.update()

        apply_func = getattr(fixer, f"{key}_apply")
        try:
            result = apply_func()
            if result.get("error"):
                status_label.configure(text="Ошибка", text_color="#ff5555")
            else:
                freed = result.get("freed_bytes", 0)
                human_size = fixer._human(freed)
                status_label.configure(text=f"✅ Очищено: {human_size}", text_color="#6daa45")
                messagebox.showinfo("Готово", f"Освобождено: {human_size}")
        except Exception as e:
            status_label.configure(text="Ошибка", text_color="#ff5555")
        finally:
            btn_clean.configure(state="disabled", text="Очистить", fg_color="#444", hover_color="#555")

    def _on_start(self):
        self.btn_start.configure(state="disabled", text="⏳ Собираю данные...")
        self.status.configure(text="Собираю данные... (30–60 секунд)")
        self.progress.start()
        self.textbox.delete("1.0", "end")
        threading.Thread(target=self._run_diagnostic, daemon=True).start()

    def _run_diagnostic(self):
        try:
            data = collect_all(skip_slow=True)
            findings = check(data)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                print_report(data, findings, llm_text=None)
            report = buf.getvalue()
            self._report_text = report
            self.after(0, self._show_report, report)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _show_report(self, report: str):
        self.progress.stop()
        self.progress.set(1)
        self.textbox.insert("1.0", report)
        self.status.configure(text="✅ Готово")
        self.btn_start.configure(state="normal", text="🔍 Начать диагностику")
        self.btn_save.configure(state="normal")
        self.btn_open.configure(state="normal")

    def _show_error(self, err: str):
        self.progress.stop()
        self.progress.set(0)
        self.status.configure(text=f"❌ Ошибка: {err}")
        self.btn_start.configure(state="normal", text="🔍 Начать диагностику")
        messagebox.showerror("Ошибка диагностики", err)

    def _on_save(self):
        if not self._report_text:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt")],
            initialfile="pc-diag-report.txt",
        )
        if path:
            Path(path).write_text(self._report_text, encoding="utf-8")
            messagebox.showinfo("Сохранено", f"Отчёт сохранён:\n{path}")

    def _on_open_folder(self):
        import subprocess
        subprocess.run(["explorer", str(Path.cwd())])


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()