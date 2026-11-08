"""РџРµС‡Р°С‚СЊ С‡РµР»РѕРІРµРєРѕС‡РёС‚Р°РµРјРѕРіРѕ РѕС‚С‡С‘С‚Р°."""

SEV_EMOJI = {"high": "рџ”ґ", "medium": "рџџЎ", "low": "рџџў"}
SEV_LABEL = {"high": "Р’Р«РЎРћРљРР™", "medium": "РЎР Р•Р”РќРР™", "low": "РќРР—РљРР™"}


def print_report(data: dict, findings: list[dict], llm_text: str | None = None):
    sysinfo = data["system"]
    load = data["load"]

    print()
    print("=" * 64)
    print(f"  Р”РРђР“РќРћРЎРўРРљРђ: {sysinfo['hostname']}")
    print("=" * 64)
    print(f"  РћРЎ:        {sysinfo['os']} ({sysinfo['machine']})")
    print(f"  Python:    {sysinfo['python']}")
    print(f"  CPU:       {sysinfo['cpu_cores_physical']} С„РёР· / "
          f"{sysinfo['cpu_cores_logical']} Р»РѕРі")
    print(f"  RAM:       {sysinfo['ram_total_gb']} Р“Р‘, "
          f"Р·Р°РЅСЏС‚Рѕ {load['ram_percent']}%")
    print(f"  CPU load:  {load['cpu_percent']}%")
    print(f"  Swap:      {load['swap_percent']}%")
    print(f"  РђРїС‚Р°Р№Рј:    {sysinfo['uptime_hours']} С‡")

    # в”Ђв”Ђ Р”РёСЃРєРё в”Ђв”Ђ
    print("\nв”Ђв”Ђ Р”РёСЃРєРё в”Ђв”Ђ")
    for d in data["disks"]:
        bar = _bar(d["percent"])
        print(f"  {d['mount']:<4} {d['percent']:>3}% {bar}  "
              f"{d['used_gb']}/{d['total_gb']} Р“Р‘  ({d['fstype']})")
            # в”Ђв”Ђ Р—РґРѕСЂРѕРІСЊРµ РґРёСЃРєРѕРІ (SMART) в”Ђв”Ђ
    disk_health = data.get("disk_health", [])
    if disk_health:
        print("\nв”Ђв”Ђ Р—РґРѕСЂРѕРІСЊРµ РґРёСЃРєРѕРІ (SMART) в”Ђв”Ђ")
        for dh in disk_health:
            model = dh.get("model", "?")
            dev = dh.get("device_id", "?")
            hs = dh.get("health_status", "?")
            os_ = dh.get("operational_status", "?")
            pred = dh.get("predict_failure")

            # Р¤РѕСЂРјРёСЂСѓРµРј СЃС‚СЂРѕРєСѓ СЃС‚Р°С‚СѓСЃР°
            if pred is True:
                status = "рџ”ґ PREDICTED FAILURE"
            elif hs.lower() not in ("healthy", "ok"):
                status = f"рџ”ґ {hs}"
            elif os_.lower() not in ("ok",):
                status = f"рџџЎ {os_}"
            else:
                status = "рџџў Healthy"

            line = f"  [{dev}] {model:<30} {status}"

            # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РїР°СЂР°РјРµС‚СЂС‹
            extras = []
            if dh.get("temperature") is not None:
                extras.append(f"T={dh['temperature']}В°C")
            if dh.get("wear") is not None:
                extras.append(f"Wear={dh['wear']}%")
            if dh.get("power_on_hours") is not None:
                extras.append(f"POH={dh['power_on_hours']}С‡")
            if extras:
                line += "  (" + ", ".join(extras) + ")"

            print(line)

            # РћС€РёР±РєРё, РµСЃР»Рё РµСЃС‚СЊ
            r_err = dh.get("read_errors_uncorrected") or 0
            w_err = dh.get("write_errors_uncorrected") or 0
            if r_err > 0 or w_err > 0:
                print(f"       вљ пёЏ Uncorrected: R={r_err}, W={w_err}")

    # в”Ђв”Ђ РўРѕРї РїРѕ RAM в”Ђв”Ђ
    print("\nв”Ђв”Ђ РўРѕРї РїРѕ RAM в”Ђв”Ђ")
    for p in data["processes"]["top_ram"][:5]:
        print(f"  {p['name']:<28} {p['ram_mb']:>8.1f} РњР‘  (PID {p['pid']})")

    # в”Ђв”Ђ РўРѕРї РїРѕ CPU в”Ђв”Ђ
    print("\nв”Ђв”Ђ РўРѕРї РїРѕ CPU в”Ђв”Ђ")
    for p in data["processes"]["top_cpu"][:5]:
        print(f"  {p['name']:<28} {p['cpu_percent']:>6.1f}%  (PID {p['pid']})")

    # в”Ђв”Ђ РЎРµС‚СЊ в”Ђв”Ђ
    net = data.get("network", {})
    if net:
        print("\nв”Ђв”Ђ РЎРµС‚СЊ в”Ђв”Ђ")
        if net.get("interface"):
            print(f"  РРЅС‚РµСЂС„РµР№СЃ: {net['interface']}")
        if net.get("gateway"):
            print(f"  РЁР»СЋР·:      {net['gateway']}")
        if net.get("dns"):
            print(f"  DNS:       {net['dns']}")
        for ping in net.get("pings", []):
            if ping.get("ok"):
                avg = ping.get("avg_ms")
                avg_str = f"{avg} РјСЃ" if avg is not None else "<1 РјСЃ"
                print(f"  Ping {ping['host']:<15} "
                      f"{ping['received']}/{ping['sent']} "
                      f"({ping['loss_pct']}% РїРѕС‚РµСЂСЊ, {avg_str})")
            else:
                print(f"  Ping {ping['host']:<15} вќЊ РќР• РћРўР’Р•Р§РђР•Рў")

    # в”Ђв”Ђ РЎР»СѓР¶Р±С‹ в”Ђв”Ђ
    services = data.get("services", [])
    if services:
        print(f"\nв”Ђв”Ђ РћСЃС‚Р°РЅРѕРІР»РµРЅРЅС‹Рµ Р°РІС‚Рѕ-СЃР»СѓР¶Р±С‹ ({len(services)}) в”Ђв”Ђ")
        for s in services[:10]:
            print(f"  {str(s.get('name')):<30} {s.get('display_name')}")
        if len(services) > 10:
            print(f"  ... Рё РµС‰С‘ {len(services) - 10}")

    # в”Ђв”Ђ РџР°РїРєРё в”Ђв”Ђ
    folders = data.get("folder_sizes", [])
    if folders:
        print("\nв”Ђв”Ђ РљСЂСѓРїРЅС‹Рµ РїР°РїРєРё РІ РїСЂРѕС„РёР»Рµ в”Ђв”Ђ")
        for f in folders[:10]:
            print(f"  {str(f.get('name')):<30} {f.get('gb', 0):>7.2f} Р“Р‘")
        if len(folders) > 10:
            print(f"  ... Рё РµС‰С‘ {len(folders) - 10}")

    # в”Ђв”Ђ Event Log в”Ђв”Ђ
    if data.get("event_errors"):
        print(f"\nв”Ђв”Ђ РћС€РёР±РєРё Event Log (24С‡, {len(data['event_errors'])}) в”Ђв”Ђ")
        for e in data["event_errors"][:5]:
            print(f"  {e}")
        if len(data["event_errors"]) > 5:
            print(f"  ... Рё РµС‰С‘ {len(data['event_errors']) - 5}")

    # в”Ђв”Ђ РџСЂРѕР±Р»РµРјС‹ в”Ђв”Ђ
    print("\nв”Ђв”Ђ РќР°Р№РґРµРЅРЅС‹Рµ РїСЂРѕР±Р»РµРјС‹ в”Ђв”Ђ")
    if not findings:
        print("  вњ… РЇРІРЅС‹С… РїСЂРѕР±Р»РµРј РЅРµ РЅР°Р№РґРµРЅРѕ.")
    else:
        for f in findings:
            emoji = SEV_EMOJI.get(f["severity"], "вЂў")
            label = SEV_LABEL.get(f["severity"], f["severity"].upper())
            print(f"\n  {emoji} [{label}] {f['title']}")
            print(f"     {f['detail']}")
            print(f"     в†’ {f['suggest']}")

    # в”Ђв”Ђ LLM в”Ђв”Ђ
    if llm_text:
        print("\nв”Ђв”Ђ РћР±СЉСЏСЃРЅРµРЅРёРµ РѕС‚ LLM в”Ђв”Ђ")
        for line in llm_text.splitlines():
            print(f"  {line}")

    print()


def _bar(percent: int, width: int = 20) -> str:
    filled = int(width * percent / 100)
    return "[" + "в–€" * filled + "в–‘" * (width - filled) + "]"
