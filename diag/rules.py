"""Simple rules: trigger without LLM. Cheap and predictable."""


ON_DEMAND_OK = {
    "gpsvc", "sppsvc", "dosvc", "edgeupdate", "mapsbroker", "stisvc",
    "wuauserv", "wsearch", "diagtrack", "bits", "w32time", "wbengine",
    "trustedinstaller", "wersvc", "smphost",
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
            "severity": "high", "title": "RAM is almost full",
            "detail": f"Used {load.get('ram_used_gb')} of "
                      f"{sysinfo.get('ram_total_gb')} GB ({ram_pct}%).",
            "suggest": "Close unused programs. Check top_ram.",
        })
    elif ram_pct >= 80:
        findings.append({
            "severity": "medium", "title": f"RAM is {ram_pct}% full",
            "detail": "Low free memory. Apps might stutter.",
            "suggest": "Check top_ram.",
        })

    # ── CPU ──
    cpu_pct = load.get("cpu_percent", 0)
    if cpu_pct >= 90:
        findings.append({
            "severity": "high", "title": "CPU load is 90%+",
            "detail": f"Current load: {cpu_pct}%.",
            "suggest": "Check top_cpu.",
        })
    elif cpu_pct >= 70:
        findings.append({
            "severity": "medium", "title": f"CPU load is {cpu_pct}%",
            "detail": "High background load.",
            "suggest": "Check top_cpu.",
        })

    # ── Disks ──
    for d in disks:
        p = d.get("percent", 0)
        mount = d.get("mount", "?")
        if p >= 95:
            findings.append({
                "severity": "high", "title": f"Disk {mount} is almost full",
                "detail": f"{p}% ({d.get('used_gb')}/{d.get('total_gb')} GB).",
                "suggest": "Free up space: temp files, large folders, recycle bin.",
            })
        elif p >= 85:
            findings.append({
                "severity": "medium",
                "title": f"Disk {mount} is {p}% full",
                "detail": f"{d.get('used_gb')}/{d.get('total_gb')} GB.",
                "suggest": "Free up space in advance.",
            })

    # ── Disk Health ──
    disk_health = data.get("disk_health", [])
    for dh in disk_health:
        model = dh.get("model", "?")
        dev = dh.get("device_id", "?")

        if dh.get("predict_failure") is True:
            findings.append({
                "severity": "high",
                "title": f"Disk {model} predicts failure",
                "detail": "SMART PredictFailure = True. Disk may fail soon.",
                "suggest": "Back up your data immediately. Replace the disk.",
            })

        hs = str(dh.get("health_status", "")).lower()
        if hs and hs not in ("healthy", "ok", "unknown"):
            findings.append({
                "severity": "high",
                "title": f"Disk {model} is unhealthy",
                "detail": f"HealthStatus = {dh.get('health_status')}.",
                "suggest": "Back up your data. Check the disk.",
            })

        wear = dh.get("wear")
        if isinstance(wear, (int, float)) and 50 <= wear < 80:
            findings.append({
                "severity": "medium",
                "title": f"SSD {model} is {wear}% worn out",
                "detail": f"{100 - wear}% write resource left.",
                "suggest": "Back up your data. Monitor Wear monthly.",
            })
        elif isinstance(wear, (int, float)) and wear >= 80:
            findings.append({
                "severity": "high",
                "title": f"SSD {model} is {wear}% worn out",
                "detail": f"Only {100 - wear}% write resource left.",
                "suggest": "Back up your data immediately. Replace the disk.",
            })

        r_err = dh.get("read_errors_uncorrected") or 0
        w_err = dh.get("write_errors_uncorrected") or 0
        if r_err > 0 or w_err > 0:
            findings.append({
                "severity": "high",
                "title": f"Disk {model}: uncorrected errors",
                "detail": f"Read errors: {r_err}, Write errors: {w_err}.",
                "suggest": "Data may be lost. Back up immediately.",
            })

    # ── Top RAM Processes ──
    for p in procs.get("top_ram", [])[:3]:
        if p.get("ram_mb", 0) > 2000:
            findings.append({
                "severity": "medium",
                "title": f"Process {p['name']} uses a lot of RAM",
                "detail": f"PID {p['pid']}, {p['ram_mb']} MB.",
                "suggest": "Check if you need it running.",
            })

    # ── Event Log ──
    if len(events) >= 10:
        findings.append({
            "severity": "medium",
            "title": f"Many Event Log errors in 24h: {len(events)}",
            "detail": "Check event_errors.",
            "suggest": "Search for repeated IDs.",
        })
    elif len(events) >= 3:
        findings.append({
            "severity": "low",
            "title": f"Event Log errors in 24h: {len(events)}",
            "detail": "Not critical, but worth a look.",
            "suggest": "Check event_errors.",
        })

    # ── Startup ──
    if len(startup) > 15:
        findings.append({
            "severity": "low",
            "title": f"Startup is bloated: {len(startup)} items",
            "detail": "Slows down boot.",
            "suggest": "Disable unused items in Task Manager -> Startup.",
        })

    # ── Network ──
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
                "severity": "high", "title": "Gateway is unreachable",
                "detail": f"Ping to {gw_ping.get('host')} failed.",
                "suggest": "Check cable/Wi-Fi, router, VPN.",
            })
        elif gw_ping and gw_ping.get("loss_pct", 0) > 20:
            findings.append({
                "severity": "medium",
                "title": f"Packet loss to gateway: {gw_ping['loss_pct']}%",
                "detail": f"Ping to {gw_ping['host']}, avg {gw_ping.get('avg_ms')} ms.",
                "suggest": "Check Wi-Fi signal or cable.",
            })

        if inet_ping and not inet_ping.get("ok"):
            findings.append({
                "severity": "high",
                "title": "Internet is unreachable (8.8.8.8)",
                "detail": "Gateway might work, but no internet access.",
                "suggest": "Check router settings, DNS, VPN.",
            })
        elif inet_ping and inet_ping.get("loss_pct", 0) > 20:
            findings.append({
                "severity": "medium",
                "title": f"Packet loss to internet: {inet_ping['loss_pct']}%",
                "detail": f"Average ping {inet_ping.get('avg_ms')} ms.",
                "suggest": "Check provider or VPN.",
            })

    # ── Services ──
    services_real = [
        s for s in services
        if (s.get("name") or "").lower() not in ON_DEMAND_OK
    ]
    if len(services_real) >= 3:
        findings.append({
            "severity": "medium",
            "title": f"Stopped auto-services: {len(services_real)}",
            "detail": ", ".join(s.get("name", "?") for s in services_real[:5]),
            "suggest": "Check services.msc.",
        })
    elif len(services_real) >= 1:
        findings.append({
            "severity": "low",
            "title": f"Stopped auto-services: {len(services_real)}",
            "detail": ", ".join(s.get("name", "?") for s in services_real[:5]),
            "suggest": "Check services.msc.",
        })

    # ── Folders ──
    big = [f for f in folders if f.get("gb", 0) >= 5]
    if big:
        names = ", ".join(f"{f['name']} ({f['gb']} GB)" for f in big[:5])
        findings.append({
            "severity": "medium",
            "title": f"Large folders in profile: {len(big)}",
            "detail": names,
            "suggest": "Check contents (cache, installers, Docker).",
        })

    return findings