# pc-diag

> Портативная диагностика Windows за 60 секунд: SMART-здоровье дисков,
> Event Log, сеть, службы, топ процессов. Без установки, без интернета,
> **read-only** — ничего не меняет в системе.

[![Website](https://img.shields.io/badge/site-pc--diag.ru-6daa45)](https://pc-diag.ru/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Release](https://img.shields.io/github/v/release/progerman666/pc-diag)](https://github.com/progerman666/pc-diag/releases/latest)

**[Скачать](https://github.com/progerman666/pc-diag/releases/latest)** ·
**[Сайт](https://pc-diag.ru/)** ·
**[Все релизы](https://github.com/progerman666/pc-diag/releases)**

---

## Зачем это

Когда компьютер «тормозит» или «что-то не так», обычные средства Windows
показывают либо слишком мало (Диспетчер задач), либо слишком много
(Event Viewer, WMI, `smartctl` по отдельности). `pc-diag` собирает всё
в одном отчёте за 60 секунд и сразу говорит, **что не так и что делать**.

Пример: вместо «посмотрите в CrystalDiskInfo, потом в Event Viewer,
потом в Диспетчере задач» вы получаете:
🟡 [СРЕДНИЙ] SSD ADATA SU650NS38 изношен на 66%
Осталось 34% ресурса записи.
→ Сделайте бэкап важных данных. Следите за Wear раз в месяц.

text

`pc-diag` — не «ещё один cleaner». Это диагностический инструмент,
который **сначала смотрит, потом объясняет, и только потом предлагает
исправить** — с подтверждением и логом каждого действия.

---

## Что умеет

### Диагностика (read-only, ничего не меняет)

- **Система**: ОС, версия Python, физические/логические ядра CPU,
  объём RAM, uptime.
- **Нагрузка в реальном времени**: CPU, RAM, swap, топ процессов
  по CPU и по RAM (с нормализацией как в Диспетчере задач).
- **Диски**: заполнение, ФС, свободное место с визуальной шкалой.
- **SMART**: `HealthStatus`, `PredictFailure`, температура, износ SSD
  (`Wear`), наработка (`PowerOnHours`), некорректируемые ошибки
  чтения/записи. Fallback на встроенный `smartctl`, если WMI не отдаёт
  счётчики.
- **Сеть**: интерфейс, шлюз, DNS, пинг до шлюза и `8.8.8.8`
  (потери, RTT).
- **Автозагрузка**: имя, команда, локация, пользователь.
- **Службы**: авто-службы в состоянии не `Running` (с фильтром
  триггер-старт, чтобы не пугать `gpsvc`/`sppsvc`/`StiSvc`).
- **Event Log**: ошибки и `Critical` из System-лога за 24 часа,
  с русскими названиями уровней.
- **Размеры папок**: топ-20 в профиле пользователя
  (медленно, есть `--fast`).

### Анализ

- **15+ детерминированных правил**: RAM/CPU, заполнение дисков,
  износ SSD, потеря пакетов, ошибки в журнале, раздутая автозагрузка,
  крупные папки.
- **LLM-объяснение** (опционально): локальная Ollama
  (`qwen2.5:3b` / `7b`) или облачный Claude. Модель **не выполняет**
  действий — только объясняет находки человеческим языком.

---

## Пример вывода
================================================================
ДИАГНОСТИКА: DESKTOP-SFNMU9R
================================================================
ОС: Windows 10 (AMD64)
Python: 3.11.9
CPU: 4 физ / 4 лог
RAM: 15.9 ГБ, занято 47.2%
CPU load: 12.1%
Swap: 5.7%
Аптайм: 1.1 ч

── Диски ──
C:\ 89.1% [█████████████████░░░] 98.7/110.8 ГБ (NTFS)
D:\ 90.6% [██████████████████░░] 100.3/110.7 ГБ (NTFS)

── Здоровье дисков (SMART) ──
[0] ADATA SU650 🟢 Healthy (T=46°C, Wear=0%, POH=20654ч)
[1] ADATA SU650NS38 🟢 Healthy (T=39°C, Wear=66%, POH=17186ч)

── Топ по RAM ──
Code.exe 414.1 МБ (PID 9240)
steamwebhelper.exe 405.6 МБ (PID 14152)
...

── Сеть ──
Интерфейс: Ethernet
Шлюз: 192.168.0.1
DNS: 8.8.8.8, 8.8.4.4
Ping 192.168.0.1 4/4 (0.0% потерь, 0 мс)
Ping 8.8.8.8 4/4 (0.0% потерь, 71 мс)

── Найденные проблемы ──

🟡 [СРЕДНИЙ] SSD ADATA SU650NS38 изношен на 66%
Осталось 34% ресурса записи.
→ Сделайте бэкап важных данных. Следите за Wear раз в месяц.

🟡 [СРЕДНИЙ] Диск C:\ заполнен на 89.1%
98.7/110.8 ГБ.
→ Освободите место заранее.

🟢 [НИЗКИЙ] Ошибки в Event Log за 24ч: 2
Не критично, но стоит глянуть.
→ Смотрите event_errors.

text

---

## Установка

### Вариант 1: Portable (без установки, рекомендуется для выездов)

1. Скачайте `pc-diag-win64-portable.zip` из [Releases](https://github.com/progerman666/pc-diag/releases/latest).
2. Распакуйте в любую папку (например, на флешку).
3. Запустите `pc-diag.exe --no-llm --fast`.

Ничего не устанавливается в систему, не требует прав администратора.
Размер распакованной папки — ~30 МБ.

### Вариант 2: Установщик

1. Скачайте `pc-diag-setup.exe` из [Releases](https://github.com/progerman666/pc-diag/releases/latest).
2. Запустите, пройдите мастер установки (потребуются права администратора).
3. Запустите из меню «Пуск» или с рабочего стола.

Устанавливается в `C:\Program Files\pc-diag`. Создаёт ярлыки, добавляет
в «Установка и удаление программ» с деинсталлятором.

### Вариант 3: Из исходников (для разработки)

**Требования:** Windows 10/11, Python 3.11+.

```powershell
git clone https://github.com/progerman666/pc-diag.git
cd pc-diag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
Опционально: локальная LLM (Ollama)
Работает без интернета, без API-ключей, без блокировок.

Установите Ollama.

Скачайте модель:

powershell
ollama pull qwen2.5:3b     # ~2 ГБ, быстрее
# или
ollama pull qwen2.5:7b     # ~4.7 ГБ, качественнее
В .env укажите модель:

text
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen2.5:3b
Опционально: smartmontools
Если запускаете из исходников (не из готовой сборки) и WMI не отдаёт
Wear/Temperature для вашего диска — поставьте smartmontools:

powershell
winget install smartmontools.smartmontools
pc-diag автоматически использует smartctl как fallback. В готовой
сборке (portable и installer) smartctl.exe уже встроен —
устанавливать ничего не нужно.

Использование
Диагностика
powershell
pc-diag.exe --no-llm --fast     # быстро: без LLM и без сканирования папок
pc-diag.exe --no-llm            # + размеры папок (медленнее на 30-60 с)
pc-diag.exe                     # + LLM-объяснение
pc-diag.exe --json report.json  # сохранить полный отчёт в JSON
Из исходников — то же самое через python -m diag.

Fixer (только из исходников)
Каждое действие проходит цикл: dry-run → подтверждение → бэкап → лог.

powershell
python -m diag.fixer --list                       # список действий
python -m diag.fixer clean_temp                   # dry-run (ничего не удалит)
python -m diag.fixer clean_temp --apply           # применить (спросит y/N)
python -m diag.fixer clean_recycle --apply
python -m diag.fixer disable_startup --name OneDrive   # dry-run
python -m diag.fixer disable_startup --name OneDrive --apply
python -m diag.fixer --log                        # история действий
Доступные действия:

clean_temp — очистка %TEMP% и C:\Windows\Temp

clean_recycle — очистка корзины

disable_startup — отключение записи автозагрузки
(только HKCU\...\Run, с бэкапом в fixer_backups/)

docker_prune — docker system prune -a

Внимание: в готовой .exe-сборке (portable и installer)
fixer отключён — чтобы случайно не навредить системе клиента.
Доступна только диагностика. Если нужен fixer — запускайте из исходников.

Безопасность
pc-diag спроектирован так, чтобы не сломать систему:

Диагностика read-only. collect_all() ничего не меняет. Только
читает реестр, WMI, файлы, Event Log.

Готовая сборка не содержит fixer. В portable и installer
доступна только диагностика — никаких изменений в системе.

Fixer требует явного подтверждения (при запуске из исходников).
--apply без y не выполнит действие.

Бэкап перед изменением. disable_startup сохраняет оригинальную
команду в fixer_backups/ перед удалением из реестра.

Лог всех действий. fixer_log.jsonl — что запрашивали, что
применили, что освободили.

Ограниченный набор действий. Fixer не выполняет произвольные
PowerShell-команды. Только зарегистрированные в ACTIONS.

.env, fixer_log.jsonl, fixer_backups/ в .gitignore.
Личные данные не попадают в репозиторий.

Архитектура
text
pc-diag/
├── diag/
│   ├── __main__.py      # CLI: python -m diag [--no-llm] [--fast] [--json]
│   ├── collectors.py    # read-only сборщики (WMI, smartctl, psutil)
│   ├── rules.py         # детерминированные правила → findings
│   ├── report.py        # форматирование отчёта
│   ├── llm.py           # Ollama / Anthropic, только объяснения
│   └── fixer.py         # безопасные исправления (только из исходников)
├── docs/
│   ├── index.html       # лендинг для GitHub Pages
│   ├── robots.txt       # разрешение на индексацию
│   └── sitemap.xml      # карта сайта
├── installer.iss        # скрипт Inno Setup
├── run_diag.py          # точка входа для PyInstaller
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
Поток данных:

text
collectors.collect_all()
    → dict с system/load/disks/disk_health/network/services/...
rules.check(data)
    → list[dict] с severity/title/detail/suggest
report.print_report(data, findings, llm_text)
llm.explain(data, findings)   # опционально
    → str с человеческим объяснением
Сборка .exe (для разработчиков)
Требования: PyInstaller (pip install pyinstaller), smartmontools
в C:\Program Files\smartmontools\bin\.

Portable (--onedir):

powershell
pyinstaller --name pc-diag --onedir --console --paths . ^
  --add-binary "C:\Program Files\smartmontools\bin\smartctl.exe;smartctl" ^
  --hidden-import psutil --hidden-import requests ^
  --hidden-import dotenv --hidden-import anthropic ^
  run_diag.py
Результат: dist\pc-diag\ (папка ~30 МБ с pc-diag.exe и _internal\).

Установщик: Inno Setup, скрипт installer.iss в корне проекта.
Компиляция: Build → Compile, результат — pc-diag-setup.exe.

Ограничения
Только Windows x64. WMI, Event Log, Get-PhysicalDisk —
Windows-only API. Сборка для 64-битной Windows 10/11.

LLM не выполняет действий. Даже при LLM_BACKEND=ollama,
модель только генерирует текст.

SMART зависит от контроллера. Дешёвые SATA SSD (например,
ADATA SU650) иногда не отдают Wear/Temperature через WMI —
тогда используется smartctl, но и он может не увидеть диск через
USB-адаптер.

Не заменяет антивирус / мониторинг. Это диагностика, не защита.

Права администратора нужны для Get-StorageReliabilityCounter
и smartctl. Без них часть SMART-полей будет пустой.

Антивирусные ложные срабатывания. Свежесобранный PyInstaller
.exe иногда определяется как «подозрительный». Это нормально
для диагностических утилит. Добавьте в исключения или проверьте
на VirusTotal.

Roadmap
☑ Базовые сборщики (system, load, disks, processes)
☑ Сеть (шлюз, DNS, ping)
☑ SMART (WMI + smartctl fallback)
☑ Event Log с русскими уровнями
☑ Fixer: clean_temp, clean_recycle, disable_startup, docker_prune
☑ Локальная LLM через Ollama
☑ Сборка в .exe (PyInstaller, --onedir)
☑ Установщик (Inno Setup)
☑ Публичный релиз v1.0
☑ Лендинг на кастомном домене (pc-diag.ru)
□ Windows Update: последние установленные, дата
□ Драйверы с ошибками (Get-PnpDevice -Status ERROR)
□ Температуры CPU/GPU (LibreHardwareMonitor)
□ Кэши AppData (pip, VSCode, браузеры)
□ История SMART (Wear растёт со временем)
□ GitHub Actions: python -m diag --no-llm --fast на push
□ Экспорт в HTML-отчёт
Лицензия
MIT — см. LICENSE.

Дисклеймер
Инструмент предоставляется «как есть». Диагностика read-only безопасна.
Fixer (доступен только из исходников) выполняет реальные изменения —
очистку temp, удаление записей автозагрузки, docker prune. Перед
--apply читайте dry-run. Автор не несёт ответственности за потерю
данных, если вы применили действие без бэкапа.

Готовая сборка (portable и installer) не содержит fixer —
только диагностику. Это сделано специально, чтобы исключить
случайное изменение системы клиента.
