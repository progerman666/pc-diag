"""Печать человекочитаемого отчёта."""

SEV_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
SEV_LABEL = {"high": "ВЫСОКИЙ", "medium": "СРЕДНИЙ", "low": "НИЗКИЙ"}


def print_report(data: dict, findings: list[dict], llm_text: str | None = None):
    sysinfo = data["system"]
    load = data["load"]

    print()
    print("=" * 64)
    print(f"  ДИАГНОСТИКА: {sysinfo['hostname']}")
    print("=" * 64)
    print(f"  ОС:        {sysinfo['os']} ({sysinfo['machine']})")
    print(f"  Python:    {sysinfo['python']}")
    print(f"  CPU:       {sysinfo['cpu_cores_physical']} физ / "
          f"{sysinfo['cpu_cores_logical']} лог")
    print(f"  RAM:       {sysinfo['ram_total_gb']} ГБ, "
          f"занято {load['ram_percent']}%")
    print(f"  CPU load:  {load['cpu_percent']}%")
    print(f"  Swap:      {load['swap_percent']}%")
    print(f"  Аптайм:    {sysinfo['uptime_hours']} ч")

    # ── Диски ──
    print("\n── Диски ──")
    for d in data["disks"]:
        bar = _bar(d["percent"])
        print(f"  {d['mount']:<4} {d['percent']:>3}% {bar}  "
              f"{d['used_gb']}/{d['total_gb']} ГБ  ({d['fstype']})")
            # ── Здоровье дисков (SMART) ──
    disk_health = data.get("disk_health", [])
    if disk_health:
        print("\n── Здоровье дисков (SMART) ──")
        for dh in disk_health:
            model = dh.get("model", "?")
            dev = dh.get("device_id", "?")
            hs = dh.get("health_status", "?")
            os_ = dh.get("operational_status", "?")
            pred = dh.get("predict_failure")

            # Формируем строку статуса
            if pred is True:
                status = "🔴 PREDICTED FAILURE"
            elif hs.lower() not in ("healthy", "ok"):
                status = f"🔴 {hs}"
            elif os_.lower() not in ("ok",):
                status = f"🟡 {os_}"
            else:
                status = "🟢 Healthy"

            line = f"  [{dev}] {model:<30} {status}"

            # Дополнительные параметры
            extras = []
            if dh.get("temperature") is not None:
                extras.append(f"T={dh['temperature']}°C")
            if dh.get("wear") is not None:
                extras.append(f"Wear={dh['wear']}%")
            if dh.get("power_on_hours") is not None:
                extras.append(f"POH={dh['power_on_hours']}ч")
            if extras:
                line += "  (" + ", ".join(extras) + ")"

            print(line)

            # Ошибки, если есть
            r_err = dh.get("read_errors_uncorrected") or 0
            w_err = dh.get("write_errors_uncorrected") or 0
            if r_err > 0 or w_err > 0:
                print(f"       ⚠️ Uncorrected: R={r_err}, W={w_err}")

    # ── Топ по RAM ──
    print("\n── Топ по RAM ──")
    for p in data["processes"]["top_ram"][:5]:
        print(f"  {p['name']:<28} {p['ram_mb']:>8.1f} МБ  (PID {p['pid']})")

    # ── Топ по CPU ──
    print("\n── Топ по CPU ──")
    for p in data["processes"]["top_cpu"][:5]:
        print(f"  {p['name']:<28} {p['cpu_percent']:>6.1f}%  (PID {p['pid']})")

    # ── Сеть ──
    net = data.get("network", {})
    if net:
        print("\n── Сеть ──")
        if net.get("interface"):
            print(f"  Интерфейс: {net['interface']}")
        if net.get("gateway"):
            print(f"  Шлюз:      {net['gateway']}")
        if net.get("dns"):
            print(f"  DNS:       {net['dns']}")
        for ping in net.get("pings", []):
            if ping.get("ok"):
                avg = ping.get("avg_ms")
                avg_str = f"{avg} мс" if avg is not None else "<1 мс"
                print(f"  Ping {ping['host']:<15} "
                      f"{ping['received']}/{ping['sent']} "
                      f"({ping['loss_pct']}% потерь, {avg_str})")
            else:
                print(f"  Ping {ping['host']:<15} ❌ НЕ ОТВЕЧАЕТ")

    # ── Службы ──
    services = data.get("services", [])
    if services:
        print(f"\n── Остановленные авто-службы ({len(services)}) ──")
        for s in services[:10]:
            print(f"  {str(s.get('name')):<30} {s.get('display_name')}")
        if len(services) > 10:
            print(f"  ... и ещё {len(services) - 10}")

    # ── Папки ──
    folders = data.get("folder_sizes", [])
    if folders:
        print("\n── Крупные папки в профиле ──")
        for f in folders[:10]:
            print(f"  {str(f.get('name')):<30} {f.get('gb', 0):>7.2f} ГБ")
        if len(folders) > 10:
            print(f"  ... и ещё {len(folders) - 10}")

    # ── Event Log ──
    if data.get("event_errors"):
        print(f"\n── Ошибки Event Log (24ч, {len(data['event_errors'])}) ──")
        for e in data["event_errors"][:5]:
            print(f"  {e}")
        if len(data["event_errors"]) > 5:
            print(f"  ... и ещё {len(data['event_errors']) - 5}")

    # ── Проблемы ──
    print("\n── Найденные проблемы ──")
    if not findings:
        print("  ✅ Явных проблем не найдено.")
    else:
        for f in findings:
            emoji = SEV_EMOJI.get(f["severity"], "•")
            label = SEV_LABEL.get(f["severity"], f["severity"].upper())
            print(f"\n  {emoji} [{label}] {f['title']}")
            print(f"     {f['detail']}")
            print(f"     → {f['suggest']}")

    # ── LLM ──
    if llm_text:
        print("\n── Объяснение от LLM ──")
        for line in llm_text.splitlines():
            print(f"  {line}")

    print()


def _bar(percent: int, width: int = 20) -> str:
    filled = int(width * percent / 100)
    return "[" + "█" * filled + "░" * (width - filled) + "]"