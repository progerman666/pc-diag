# pc-diag

> Агент-диагност Windows: read-only сбор данных, SMART-проверка дисков,
> правила, локальная LLM (Ollama) для объяснений, безопасный fixer
> с dry-run и бэкапами.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

`pc-diag` — это не «ещё один cleaner». Это диагностический инструмент,
который **сначала смотрит, потом объясняет, и только потом предлагает
исправить** — с подтверждением и логом каждого действия.

---

## Что умеет

### Диагностика (read-only, ничего не меняет)

- **Система**: ОС, версия Python, физические/логические ядра CPU, объём
  RAM, uptime.
- **Нагрузка в реальном времени**: CPU, RAM, swap, топ процессов по CPU
  и по RAM (с нормализацией как в Диспетчере задач).
- **Диски**: заполнение, ФС, свободное место с визуальной шкалой.
- **SMART**: `HealthStatus`, `PredictFailure`, температура, износ SSD
  (`Wear`), наработка (`PowerOnHours`), некорректируемые ошибки
  чтения/записи. Fallback на `smartctl` (smartmontools), если WMI
  не отдаёт счётчики.
- **Сеть**: интерфейс, шлюз, DNS, пинг до шлюза и `8.8.8.8` (потери, RTT).
- **Автозагрузка**: имя, команда, локация, пользователь.
- **Службы**: авто-службы в состоянии не `Running` (с фильтром триггер-старт,
  чтобы не пугать `gpsvc`/`sppsvc`/`storSvc`).
- **Event Log**: ошибки и `Critical` из System-лога за 24 часа, с русскими
  названиями уровней.
- **Размеры папок**: топ-20 в профиле пользователя (медленно, есть `--fast`).

### Анализ

- **15+ детерминированных правил**: RAM/CPU, заполнение дисков, износ SSD,
  потеря пакетов, ошибки в журнале, раздутая автозагрузка, крупные папки.
- **LLM-объяснение** (опционально): локальная Ollama (`qwen2.5:3b` / `7b`)
  или облачный Claude. Модель не выполняет действий — только объясняет
  находки человеческим языком.

### Безопасные исправления (`fixer`)

Каждое действие проходит цикл: **dry-run → подтверждение → бэкап → лог**.

- `clean_temp` — очистка `%TEMP%` и `C:\Windows\Temp`
- `clean_recycle` — очистка корзины
- `disable_startup` — отключение записи автозагрузки (только `HKCU\...\Run`,
  с бэкапом в `fixer_backups/`)
- `docker_prune` — `docker system prune -a` (для тех, у кого Docker съел
  десятки гигабайт)

История всех прогонов и применений — в `fixer_log.jsonl`.

---

## Пример вывода

```
================================================================
  ДИАГНОСТИКА: DESKTOP-SFNMU9R
================================================================
  ОС:        Windows 10 (AMD64)
  Python:    3.11.9
  CPU:       4 физ / 4 лог
  RAM:       15.9 ГБ, занято 46.8%
  CPU load:  63.3%
  Swap:      3.3%
  Аптайм:    2.4 ч

── Диски ──
  C:\  87.2% [█████████████████░░░]  96.6/110.8 ГБ  (NTFS)
  D:\  87.3% [█████████████████░░░]  96.7/110.7 ГБ  (NTFS)

── Здоровье дисков (SMART) ──
  [0] ADATA SU650                    🟢 Healthy  (T=45°C, Wear=0%, POH=20640ч)
  [1] ADATA SU650NS38                🟢 Healthy  (T=40°C, Wear=66%, POH=17173ч)

── Топ по RAM ──
  Code.exe                        656.9 МБ  (PID 2596)
  browser.exe                     427.3 МБ  (PID 8716)
  ...

── Сеть ──
  Интерфейс: Ethernet
  Шлюз:      192.168.0.1
  DNS:       192.168.0.1
  Ping 192.168.0.1     4/4 (0.0% потерь, 0 мс)
  Ping 8.8.8.8         4/4 (0.0% потерь, 67 мс)

── Найденные проблемы ──

  🟡 [СРЕДНИЙ] SSD ADATA SU650NS38 изношен на 66%
     Осталось 34% ресурса записи.
     → Сделайте бэкап важных данных. Следите за Wear раз в месяц.

  🟡 [СРЕДНИЙ] Диск C:\ заполнен на 87.2%
     96.6/110.8 ГБ.
     → Освободите место заранее.

  🟢 [НИЗКИЙ] Ошибки в Event Log за 24ч: 8
     Не критично, но стоит глянуть.
     → Смотрите event_errors.
```

---

## Установка

**Требования:** Windows 10/11, Python 3.11+.

```powershell
git clone https://github.com/progerman666/pc-diag.git
cd pc-diag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### Опционально: локальная LLM (Ollama)

Работает без интернета, без API-ключей, без блокировок.

1. Установите [Ollama](https://ollama.com/download/windows).
2. Скачайте модель:
   ```powershell
   ollama pull qwen2.5:3b     # ~2 ГБ, быстрее
   # или
   ollama pull qwen2.5:7b     # ~4.7 ГБ, качественнее
   ```
3. В `.env` укажите модель:
   ```
   LLM_BACKEND=ollama
   OLLAMA_MODEL=qwen2.5:3b
   ```

### Опционально: smartmontools (для SMART-деталей)

Если WMI не отдаёт `Wear`/`Temperature` для вашего диска — поставьте
[smartmontools](https://www.smartmontools.org/):

```powershell
winget install smartmontools.smartmontools
```

`pc-diag` автоматически использует `smartctl` как fallback.

---

## Использование

### Диагностика

```powershell
python -m diag --no-llm --fast     # быстро: без LLM и без сканирования папок
python -m diag --no-llm            # + размеры папок (медленнее на 30-60 с)
python -m diag                     # + LLM-объяснение
python -m diag --json report.json  # сохранить полный отчёт в JSON
```

### Fixer

```powershell
python -m diag.fixer --list                       # список действий
python -m diag.fixer clean_temp                   # dry-run (ничего не удалит)
python -m diag.fixer clean_temp --apply           # применить (спросит y/N)
python -m diag.fixer clean_recycle --apply
python -m diag.fixer disable_startup --name OneDrive   # dry-run
python -m diag.fixer disable_startup --name OneDrive --apply
python -m diag.fixer --log                        # история действий
```

---

## Безопасность

`pc-diag` спроектирован так, чтобы **не сломать систему**:

- **Диагностика read-only.** `collect_all()` ничего не меняет. Только
  читает реестр, WMI, файлы, Event Log.
- **Fixer требует явного подтверждения.** `--apply` без `y` не выполнит
  действие.
- **Бэкап перед изменением.** `disable_startup` сохраняет оригинальную
  команду в `fixer_backups/` перед удалением из реестра.
- **Лог всех действий.** `fixer_log.jsonl` — что запрашивали, что
  применили, что освободили.
- **Ограниченный набор действий.** Fixer не выполняет произвольные
  PowerShell-команды. Только зарегистрированные в `ACTIONS`.
- **`.env`, `fixer_log.jsonl`, `fixer_backups/` в `.gitignore`.**
  Личные данные не попадают в репозиторий.

---

## Архитектура

```
pc-diag/
├── diag/
│   ├── __main__.py      # CLI: python -m diag [--no-llm] [--fast] [--json]
│   ├── collectors.py    # read-only сборщики (WMI, smartctl, psutil)
│   ├── rules.py         # детерминированные правила → findings
│   ├── report.py        # форматирование отчёта
│   ├── llm.py           # Ollama / Anthropic, только объяснения
│   └── fixer.py         # безопасные исправления с dry-run и бэкапами
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Поток данных:

```
collectors.collect_all()
    → dict с system/load/disks/disk_health/network/services/...
rules.check(data)
    → list[dict] с severity/title/detail/suggest
report.print_report(data, findings, llm_text)
llm.explain(data, findings)   # опционально
    → str с человеческим объяснением
```

---

## Ограничения

- **Только Windows.** WMI, Event Log, `Get-PhysicalDisk` — Windows-only API.
- **LLM не выполняет действий.** Даже при `LLM_BACKEND=ollama`, модель
  только генерирует текст. Действия — только через `fixer` и только
  с `--apply`.
- **SMART зависит от контроллера.** Дешёвые SATA SSD (например, ADATA
  SU650) иногда не отдают `Wear`/`Temperature` через WMI — тогда
  используется `smartctl`, но и он может не увидеть диск через
  USB-адаптер.
- **Не заменяет полноценный антивирус / мониторинг.** Это диагностика,
  а не защита.
- **Права администратора** нужны для `Get-StorageReliabilityCounter`
  и `smartctl`. Без них часть SMART-полей будет пустой.

---

## Roadmap

- [x] Базовые сборщики (system, load, disks, processes)
- [x] Сеть (шлюз, DNS, ping)
- [x] SMART (WMI + smartctl fallback)
- [x] Event Log с русскими уровнями
- [x] Fixer: clean_temp, clean_recycle, disable_startup, docker_prune
- [x] Локальная LLM через Ollama
- [ ] Windows Update: последние установленные, дата
- [ ] Драйверы с ошибками (`Get-PnpDevice -Status ERROR`)
- [ ] Температуры CPU/GPU (LibreHardwareMonitor)
- [ ] Кэши `AppData` (`pip`, `VSCode`, браузеры)
- [ ] История SMART (`Wear` растёт со временем)
- [ ] GitHub Actions: `python -m diag --no-llm --fast` на push
- [ ] Экспорт в HTML-отчёт

---

## Лицензия

MIT — см. [LICENSE](LICENSE).

---

## Дисклеймер

Инструмент предоставляется «как есть». Диагностика read-only безопасна,
но **fixer выполняет реальные изменения** — очистку temp, удаление
записей автозагрузки, `docker prune`. Перед `--apply` читайте dry-run.
Автор не несёт ответственности за потерю данных, если вы применили
действие без бэкапа.
