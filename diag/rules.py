"""Простые правила: срабатывают без LLM. Дешево и предсказуемо."""


# Службы Windows с триггер-стартом: нормально быть остановленными,
# запускаются по событию. Их не считаем проблемой.
ON_DEMAND_OK = {
    "gpsvc", "sppsvc", "dosvc", "edgeupdate", "mapsbroker", "stisvc",
    "wuauserv", "wsearch", "diagtrack", "bits", "w32time", "wbengine",
    "trustedinstaller", "wersvc", "smphost", "sppsvc",
}


def check(data: dict) -> list[dict]:
    findings: list[dict] = []
    load = data.get("load", {})
    sysinfo = data.get("system", {})
    disks = data.get("disks", [])
    procs = data.get("processes", {})
    events = data.get("event_errors", [])
    startup = data.get("startup", [])
    network = data.get("network", {})
    services = data.get("services", [])
    folders = data.get("folder_sizes", [])

    # ── RAM ──
    ram_pct = load.get("ram_percent", 0)
    if ram_pct >= 90:
        findings.append({
            "severity": "high", "title": "RAM почти заполнена",
            "detail": f"Занято {load.get('ram_used_gb')} из "
                      f"{sysinfo.get('ram_total_gb')} ГБ ({ram_pct}%).",
            "suggest": "Закройте лишние программы. Смотрите top_ram.",
        })
    elif ram_pct >= 80:
        findings.append({
            "severity": "medium", "title": f"RAM загружена на {ram_pct}%",
            "detail": "Запас небольшой, приложения могут подтормаживать.",
            "suggest": "Проверьте top_ram.",
        })

    # ── CPU ──
    cpu_pct = load.get("cpu_percent", 0)
    if cpu_pct >= 90:
        findings.append({
            "severity": "high", "title": "CPU загружен на 90%+",
            "detail": f"Текущая загрузка {cpu_pct}%.",
            "suggest": "Смотрите top_cpu.",
        })
    elif cpu_pct >= 70:
        findings.append({
            "severity": "medium", "title": f"CPU загружен на {cpu_pct}%",
            "detail": "Высокая фоновая нагрузка.",
            "suggest": "Смотрите top_cpu.",
        })

    # ── Диски ──
        # ── Здоровье дисков (SMART) ──
    disk_health = data.get("disk_health", [])
    for dh in disk_health:
        model = dh.get("model", "?")
        dev = dh.get("device_id", "?")

        # 1. Предсказание отказа (PredictFailure = True) — критично
        if dh.get("predict_failure") is True:
            findings.append({
                "severity": "high",
                "title": f"Диск {model} (ID {dev}) предсказывает отказ",
                "detail": "SMART-статус PredictFailure = True. Диск может выйти "
                          "из строя в ближайшее время (часы/дни/недели).",
                "suggest": "Немедленно сделайте резервную копию данных. "
                           "Замените диск.",
            })

        # 2. HealthStatus не Healthy
        hs = str(dh.get("health_status", "")).lower()
        if hs and hs not in ("healthy", "ok", "unknown"):
            findings.append({
                "severity": "high",
                "title": f"Диск {model} (ID {dev}) нездоров",
                "detail": f"HealthStatus = {dh.get('health_status')}, "
                          f"OperationalStatus = {dh.get('operational_status')}.",
                "suggest": "Проверьте диск утилитой производителя. "
                           "Сделайте бэкап.",
            })

        # 3. Wear (износ SSD) >= 80%
        wear = dh.get("wear")
                # 3a. Wear 50-80% — предупреждение
        if isinstance(wear, (int, float)) and 50 <= wear < 80:
            findings.append({
                "severity": "medium",
                "title": f"SSD {model} изношен на {wear}%",
                "detail": f"Осталось {100 - wear}% ресурса записи. "
                          f"При активной работе диск может потребовать "
                          f"замены в течение года-двух.",
                "suggest": "Сделайте бэкап важных данных. Следите за Wear "
                           "раз в месяц. Рассмотрите плановую замену.",
            })
        if isinstance(wear, (int, float)) and wear >= 80:
            findings.append({
                "severity": "medium",
                "title": f"SSD {model} изношен на {wear}%",
                "detail": f"Осталось {100 - wear}% ресурса записи.",
                "suggest": "Планируйте замену SSD. Сделайте бэкап.",
            })

        # 4. Некорректируемые ошибки чтения/записи > 0
        r_err = dh.get("read_errors_uncorrected") or 0
        w_err = dh.get("write_errors_uncorrected") or 0
        if r_err > 0 or w_err > 0:
            findings.append({
                "severity": "high",
                "title": f"Диск {model}: некорректируемые ошибки",
                "detail": f"Read errors: {r_err}, Write errors: {w_err}.",
                "suggest": "Данные могут теряться. Срочно сделайте бэкап.",
            })

        # 5. Температура >= 60°C
        temp = dh.get("temperature")
        if isinstance(temp, (int, float)) and temp >= 60:
            findings.append({
                "severity": "medium",
                "title": f"Диск {model} перегревается: {temp}°C",
                "detail": "Высокая температура сокращает срок службы.",
                "suggest": "Проверьте охлаждение корпуса и поток воздуха.",
            })

        # 6. PowerOnHours > 30000 (примерно 3.5 года непрерывной работы)
        poh = dh.get("power_on_hours")
        if isinstance(poh, (int, float)) and poh > 30000:
            findings.append({
                "severity": "low",
                "title": f"Диск {model} наработал {poh:,} ч",
                "detail": "Возраст диска превышает 3.5 года непрерывной работы.",
                "suggest": "Следите за SMART. Рассмотрите плановую замену.",
            })
    for d in disks:
        p = d.get("percent", 0)
        mount = d.get("mount", "?")
        if p >= 95:
            findings.append({
                "severity": "high", "title": f"Диск {mount} почти заполнен",
                "detail": f"{p}% ({d.get('used_gb')}/{d.get('total_gb')} ГБ).",
                "suggest": "Освободите место: временные, крупные папки, корзина.",
            })
        elif p >= 85:
            findings.append({
                "severity": "medium",
                "title": f"Диск {mount} заполнен на {p}%",
                "detail": f"{d.get('used_gb')}/{d.get('total_gb')} ГБ.",
                "suggest": "Освободите место заранее.",
            })

    # ── Процессы-обжоры ──
    for p in procs.get("top_ram", [])[:3]:
        if p.get("ram_mb", 0) > 2000:
            findings.append({
                "severity": "medium",
                "title": f"Процесс {p['name']} ест много RAM",
                "detail": f"PID {p['pid']}, {p['ram_mb']} МБ.",
                "suggest": "Проверьте, нужен ли он сейчас.",
            })

    # ── Event Log ──
    if len(events) >= 10:
        findings.append({
            "severity": "medium",
            "title": f"Много ошибок в Event Log за 24ч: {len(events)}",
            "detail": "Смотрите event_errors.",
            "suggest": "Если ID повторяется — ищите его в поиске.",
        })
    elif len(events) >= 3:
        findings.append({
            "severity": "low",
            "title": f"Ошибки в Event Log за 24ч: {len(events)}",
            "detail": "Не критично, но стоит глянуть.",
            "suggest": "Смотрите event_errors.",
        })

    # ── Автозагрузка ──
    if len(startup) > 15:
        findings.append({
            "severity": "low",
            "title": f"Автозагрузка раздута: {len(startup)} записей",
            "detail": "Замедляет старт системы.",
            "suggest": "Отключите ненужное: Диспетчер задач → Автозагрузка.",
        })

    # ── Сеть ──
    if network.get("pings"):
        pings = network["pings"]
        gw_ping = next(
            (p for p in pings if p.get("host") == network.get("gateway")),
            None,
        )
        inet_ping = next(
            (p for p in pings if p.get("host") == "8.8.8.8"),
            None,
        )

        if gw_ping and not gw_ping.get("ok"):
            findings.append({
                "severity": "high", "title": "Шлюз недоступен",
                "detail": f"Пинг до {gw_ping.get('host')} не проходит. "
                          f"Локальная сеть/Wi-Fi может быть сломана.",
                "suggest": "Проверьте кабель/Wi-Fi, роутер, отключите VPN.",
            })
        elif gw_ping and gw_ping.get("loss_pct", 0) > 20:
            findings.append({
                "severity": "medium",
                "title": f"Потери пакетов до шлюза: {gw_ping['loss_pct']}%",
                "detail": f"Пинг до {gw_ping['host']}, "
                          f"среднее {gw_ping.get('avg_ms')} мс.",
                "suggest": "Проверьте Wi-Fi сигнал или кабель.",
            })

        if inet_ping and not inet_ping.get("ok"):
            findings.append({
                "severity": "high",
                "title": "Интернет недоступен (8.8.8.8)",
                "detail": "Шлюз может быть доступен, а внешний интернет — нет.",
                "suggest": "Проверьте настройки роутера, DNS, VPN/Windscribe.",
            })
        elif inet_ping and inet_ping.get("loss_pct", 0) > 20:
            findings.append({
                "severity": "medium",
                "title": f"Потери пакетов в интернет: {inet_ping['loss_pct']}%",
                "detail": f"Средний пинг {inet_ping.get('avg_ms')} мс до 8.8.8.8.",
                "suggest": "Возможно, провайдер или VPN. Проверьте без VPN.",
            })

    # ── Службы ──
    services_real = [
        s for s in services
        if (s.get("name") or "").lower() not in ON_DEMAND_OK
    ]
    if len(services_real) >= 3:
        findings.append({
            "severity": "medium",
            "title": f"Остановлены {len(services_real)} авто-служб",
            "detail": ", ".join(s.get("name", "?") for s in services_real[:5]),
            "suggest": "Проверьте в services.msc — возможно, драйвер не работает.",
        })
    elif len(services_real) >= 1:
        findings.append({
            "severity": "low",
            "title": f"Остановлены авто-службы: {len(services_real)}",
            "detail": ", ".join(s.get("name", "?") for s in services_real[:5]),
            "suggest": "Если проблема с устройством — проверьте в services.msc.",
        })

    # ── Папки ──
    big = [f for f in folders if f.get("gb", 0) >= 5]
    if big:
        names = ", ".join(f"{f['name']} ({f['gb']} ГБ)" for f in big[:5])
        findings.append({
            "severity": "medium",
            "title": f"Крупные папки в профиле: {len(big)}",
            "detail": names,
            "suggest": "Проверьте содержимое — там может быть кэш, "
                       "старые установщики, Docker.",
        })

    return findings