"""Formatting the diagnostic report to text (English version)."""


def print_report(data: dict, findings: list[dict], llm_text: str | None = None):
    sysinfo = data["system"]
    load = data["load"]

    print()
    print("=" * 64)
    print(f"  DIAGNOSTICS: {sysinfo['hostname']}")
    print("=" * 64)
    print(f"  OS:        {sysinfo['os']} ({sysinfo['machine']})")
    print(f"  Python:    {sysinfo['python']}")
    print(f"  CPU:       {sysinfo['cpu_cores_physical']} phys / "
          f"{sysinfo['cpu_cores_logical']} log")
    print(f"  RAM:       {sysinfo['ram_total_gb']} GB, "
          f"used {load['ram_percent']}%")
    print(f"  CPU load:  {load['cpu_percent']}%")
    print(f"  Swap:      {load['swap_percent']}%")
    print(f"  Uptime:    {sysinfo['uptime_hours']} h")

    # ── Disks ──
    print("\n-- Disks --")
    for d in data["disks"]:
        bar = _bar(d["percent"])
        print(f"  {d['mount']:<4} {d['percent']:>3}% {bar}  "
              f"{d['used_gb']}/{d['total_gb']} GB  ({d['fstype']})")

    # ── Disk Health (SMART) ──
    disk_health = data.get("disk_health", [])
    if disk_health:
        print("\n-- Disk Health (SMART) --")
        for dh in disk_health:
            model = dh.get("model", "?")
            dev = dh.get("device_id", "?")
            hs = dh.get("health_status", "?")
            os_ = dh.get("operational_status", "?")
            pred = dh.get("predict_failure")

            if pred is True:
                status = "🔴 PREDICTED FAILURE"
            elif hs.lower() not in ("healthy", "ok"):
                status = f"🔴 {hs}"
            elif os_.lower() not in ("ok",):
                status = f"🟡 {os_}"
            else:
                status = "🟢 Healthy"

            line = f"  [{dev}] {model:<30} {status}"

            extras = []
            if dh.get("temperature") is not None:
                extras.append(f"T={dh['temperature']}C")
            if dh.get("wear") is not None:
                extras.append(f"Wear={dh['wear']}%")
            if dh.get("power_on_hours") is not None:
                extras.append(f"POH={dh['power_on_hours']}h")
            if extras:
                line += "  (" + ", ".join(extras) + ")"

            print(line)

            r_err = dh.get("read_errors_uncorrected") or 0
            w_err = dh.get("write_errors_uncorrected") or 0
            if r_err > 0 or w_err > 0:
                print(f"       ⚠️ Uncorrected: R={r_err}, W={w_err}")

    # ── Top RAM ──
    print("\n-- Top RAM --")
    for p in data["processes"]["top_ram"][:5]:
        print(f"  {p['name']:<28} {p['ram_mb']:>8.1f} MB  (PID {p['pid']})")

    # ── Top CPU ──
    print("\n-- Top CPU --")
    for p in data["processes"]["top_cpu"][:5]:
        print(f"  {p['name']:<28} {p['cpu_percent']:>6.1f}%  (PID {p['pid']})")

    # ── Network ──
    net = data.get("network", {})
    if net:
        print("\n-- Network --")
        if net.get("interface"):
            print(f"  Interface: {net['interface']}")
        if net.get("gateway"):
            print(f"  Gateway:   {net['gateway']}")
        if net.get("dns"):
            print(f"  DNS:       {net['dns']}")
        for ping in net.get("pings", []):
            if ping.get("ok"):
                avg = ping.get("avg_ms")
                avg_str = f"{avg} ms" if avg is not None else "<1 ms"
                print(f"  Ping {ping['host']:<15} "
                      f"{ping['received']}/{ping['sent']} "
                      f"({ping['loss_pct']}% loss, {avg_str})")
            else:
                print(f"  Ping {ping['host']:<15} ❌ NO RESPONSE")

    # ── Services ──
    services = data.get("services", [])
    if services:
        print(f"\n-- Stopped Auto-Services ({len(services)}) --")
        for s in services[:10]:
            print(f"  {str(s.get('name')):<30} {s.get('display_name')}")
        if len(services) > 10:
            print(f"  ... and {len(services) - 10} more")

    # ── Folders ──
    folders = data.get("folder_sizes", [])
    if folders:
        print("\n-- Large Folders --")
        for f in folders[:10]:
            print(f"  {str(f.get('name')):<30} {f.get('gb', 0):>7.2f} GB")
        if len(folders) > 10:
            print(f"  ... and {len(folders) - 10} more")

    # ── Event Log ──
    if data.get("event_errors"):
        print(f"\n-- Event Log Errors (24h, {len(data['event_errors'])}) --")
        for e in data["event_errors"][:5]:
            print(f"  {e}")
        if len(data["event_errors"]) > 5:
            print(f"  ... and {len(data['event_errors']) - 5} more")

    # ── Found Problems ──
    print("\n-- Found Problems --")
    if not findings:
        print("  ✅ No obvious problems found.")
    else:
        for f in findings:
            emoji = _sev_emoji(f["severity"])
            label = f["severity"].upper()
            print(f"\n  {emoji} [{label}] {f['title']}")
            print(f"     {f['detail']}")
            print(f"     -> {f['suggest']}")

    if llm_text:
        print("\n-- LLM Explanation --")
        for line in llm_text.splitlines():
            print(f"  {line}")

    print()


def _bar(percent: int, width: int = 20) -> str:
    filled = int(width * percent / 100)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _sev_emoji(sev: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "•")