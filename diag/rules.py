"""РџСЂРѕСЃС‚С‹Рµ РїСЂР°РІРёР»Р°: СЃСЂР°Р±Р°С‚С‹РІР°СЋС‚ Р±РµР· LLM. Р”РµС€РµРІРѕ Рё РїСЂРµРґСЃРєР°Р·СѓРµРјРѕ."""


# РЎР»СѓР¶Р±С‹ Windows СЃ С‚СЂРёРіРіРµСЂ-СЃС‚Р°СЂС‚РѕРј: РЅРѕСЂРјР°Р»СЊРЅРѕ Р±С‹С‚СЊ РѕСЃС‚Р°РЅРѕРІР»РµРЅРЅС‹РјРё,
# Р·Р°РїСѓСЃРєР°СЋС‚СЃСЏ РїРѕ СЃРѕР±С‹С‚РёСЋ. РС… РЅРµ СЃС‡РёС‚Р°РµРј РїСЂРѕР±Р»РµРјРѕР№.
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

    # в”Ђв”Ђ RAM в”Ђв”Ђ
    ram_pct = load.get("ram_percent", 0)
    if ram_pct >= 90:
        findings.append({
            "severity": "high", "title": "RAM РїРѕС‡С‚Рё Р·Р°РїРѕР»РЅРµРЅР°",
            "detail": f"Р—Р°РЅСЏС‚Рѕ {load.get('ram_used_gb')} РёР· "
                      f"{sysinfo.get('ram_total_gb')} Р“Р‘ ({ram_pct}%).",
            "suggest": "Р—Р°РєСЂРѕР№С‚Рµ Р»РёС€РЅРёРµ РїСЂРѕРіСЂР°РјРјС‹. РЎРјРѕС‚СЂРёС‚Рµ top_ram.",
        })
    elif ram_pct >= 80:
        findings.append({
            "severity": "medium", "title": f"RAM Р·Р°РіСЂСѓР¶РµРЅР° РЅР° {ram_pct}%",
            "detail": "Р—Р°РїР°СЃ РЅРµР±РѕР»СЊС€РѕР№, РїСЂРёР»РѕР¶РµРЅРёСЏ РјРѕРіСѓС‚ РїРѕРґС‚РѕСЂРјР°Р¶РёРІР°С‚СЊ.",
            "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ top_ram.",
        })

    # в”Ђв”Ђ CPU в”Ђв”Ђ
    cpu_pct = load.get("cpu_percent", 0)
    if cpu_pct >= 90:
        findings.append({
            "severity": "high", "title": "CPU Р·Р°РіСЂСѓР¶РµРЅ РЅР° 90%+",
            "detail": f"РўРµРєСѓС‰Р°СЏ Р·Р°РіСЂСѓР·РєР° {cpu_pct}%.",
            "suggest": "РЎРјРѕС‚СЂРёС‚Рµ top_cpu.",
        })
    elif cpu_pct >= 70:
        findings.append({
            "severity": "medium", "title": f"CPU Р·Р°РіСЂСѓР¶РµРЅ РЅР° {cpu_pct}%",
            "detail": "Р’С‹СЃРѕРєР°СЏ С„РѕРЅРѕРІР°СЏ РЅР°РіСЂСѓР·РєР°.",
            "suggest": "РЎРјРѕС‚СЂРёС‚Рµ top_cpu.",
        })

    # в”Ђв”Ђ Р”РёСЃРєРё в”Ђв”Ђ
        # в”Ђв”Ђ Р—РґРѕСЂРѕРІСЊРµ РґРёСЃРєРѕРІ (SMART) в”Ђв”Ђ
    disk_health = data.get("disk_health", [])
    for dh in disk_health:
        model = dh.get("model", "?")
        dev = dh.get("device_id", "?")

        # 1. РџСЂРµРґСЃРєР°Р·Р°РЅРёРµ РѕС‚РєР°Р·Р° (PredictFailure = True) вЂ” РєСЂРёС‚РёС‡РЅРѕ
        if dh.get("predict_failure") is True:
            findings.append({
                "severity": "high",
                "title": f"Р”РёСЃРє {model} (ID {dev}) РїСЂРµРґСЃРєР°Р·С‹РІР°РµС‚ РѕС‚РєР°Р·",
                "detail": "SMART-СЃС‚Р°С‚СѓСЃ PredictFailure = True. Р”РёСЃРє РјРѕР¶РµС‚ РІС‹Р№С‚Рё "
                          "РёР· СЃС‚СЂРѕСЏ РІ Р±Р»РёР¶Р°Р№С€РµРµ РІСЂРµРјСЏ (С‡Р°СЃС‹/РґРЅРё/РЅРµРґРµР»Рё).",
                "suggest": "РќРµРјРµРґР»РµРЅРЅРѕ СЃРґРµР»Р°Р№С‚Рµ СЂРµР·РµСЂРІРЅСѓСЋ РєРѕРїРёСЋ РґР°РЅРЅС‹С…. "
                           "Р—Р°РјРµРЅРёС‚Рµ РґРёСЃРє.",
            })

        # 2. HealthStatus РЅРµ Healthy
        hs = str(dh.get("health_status", "")).lower()
        if hs and hs not in ("healthy", "ok", "unknown"):
            findings.append({
                "severity": "high",
                "title": f"Р”РёСЃРє {model} (ID {dev}) РЅРµР·РґРѕСЂРѕРІ",
                "detail": f"HealthStatus = {dh.get('health_status')}, "
                          f"OperationalStatus = {dh.get('operational_status')}.",
                "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ РґРёСЃРє СѓС‚РёР»РёС‚РѕР№ РїСЂРѕРёР·РІРѕРґРёС‚РµР»СЏ. "
                           "РЎРґРµР»Р°Р№С‚Рµ Р±СЌРєР°Рї.",
            })

        # 3. Wear (РёР·РЅРѕСЃ SSD) >= 80%
        wear = dh.get("wear")
                # 3a. Wear 50-80% вЂ” РїСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµ
        if isinstance(wear, (int, float)) and 50 <= wear < 80:
            findings.append({
                "severity": "medium",
                "title": f"SSD {model} РёР·РЅРѕС€РµРЅ РЅР° {wear}%",
                "detail": f"РћСЃС‚Р°Р»РѕСЃСЊ {100 - wear}% СЂРµСЃСѓСЂСЃР° Р·Р°РїРёСЃРё. "
                          f"РџСЂРё Р°РєС‚РёРІРЅРѕР№ СЂР°Р±РѕС‚Рµ РґРёСЃРє РјРѕР¶РµС‚ РїРѕС‚СЂРµР±РѕРІР°С‚СЊ "
                          f"Р·Р°РјРµРЅС‹ РІ С‚РµС‡РµРЅРёРµ РіРѕРґР°-РґРІСѓС….",
                "suggest": "РЎРґРµР»Р°Р№С‚Рµ Р±СЌРєР°Рї РІР°Р¶РЅС‹С… РґР°РЅРЅС‹С…. РЎР»РµРґРёС‚Рµ Р·Р° Wear "
                           "СЂР°Р· РІ РјРµСЃСЏС†. Р Р°СЃСЃРјРѕС‚СЂРёС‚Рµ РїР»Р°РЅРѕРІСѓСЋ Р·Р°РјРµРЅСѓ.",
            })
        if isinstance(wear, (int, float)) and wear >= 80:
            findings.append({
                "severity": "medium",
                "title": f"SSD {model} РёР·РЅРѕС€РµРЅ РЅР° {wear}%",
                "detail": f"РћСЃС‚Р°Р»РѕСЃСЊ {100 - wear}% СЂРµСЃСѓСЂСЃР° Р·Р°РїРёСЃРё.",
                "suggest": "РџР»Р°РЅРёСЂСѓР№С‚Рµ Р·Р°РјРµРЅСѓ SSD. РЎРґРµР»Р°Р№С‚Рµ Р±СЌРєР°Рї.",
            })

        # 4. РќРµРєРѕСЂСЂРµРєС‚РёСЂСѓРµРјС‹Рµ РѕС€РёР±РєРё С‡С‚РµРЅРёСЏ/Р·Р°РїРёСЃРё > 0
        r_err = dh.get("read_errors_uncorrected") or 0
        w_err = dh.get("write_errors_uncorrected") or 0
        if r_err > 0 or w_err > 0:
            findings.append({
                "severity": "high",
                "title": f"Р”РёСЃРє {model}: РЅРµРєРѕСЂСЂРµРєС‚РёСЂСѓРµРјС‹Рµ РѕС€РёР±РєРё",
                "detail": f"Read errors: {r_err}, Write errors: {w_err}.",
                "suggest": "Р”Р°РЅРЅС‹Рµ РјРѕРіСѓС‚ С‚РµСЂСЏС‚СЊСЃСЏ. РЎСЂРѕС‡РЅРѕ СЃРґРµР»Р°Р№С‚Рµ Р±СЌРєР°Рї.",
            })

        # 5. РўРµРјРїРµСЂР°С‚СѓСЂР° >= 60В°C
        temp = dh.get("temperature")
        if isinstance(temp, (int, float)) and temp >= 60:
            findings.append({
                "severity": "medium",
                "title": f"Р”РёСЃРє {model} РїРµСЂРµРіСЂРµРІР°РµС‚СЃСЏ: {temp}В°C",
                "detail": "Р’С‹СЃРѕРєР°СЏ С‚РµРјРїРµСЂР°С‚СѓСЂР° СЃРѕРєСЂР°С‰Р°РµС‚ СЃСЂРѕРє СЃР»СѓР¶Р±С‹.",
                "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ РѕС…Р»Р°Р¶РґРµРЅРёРµ РєРѕСЂРїСѓСЃР° Рё РїРѕС‚РѕРє РІРѕР·РґСѓС…Р°.",
            })

        # 6. PowerOnHours > 30000 (РїСЂРёРјРµСЂРЅРѕ 3.5 РіРѕРґР° РЅРµРїСЂРµСЂС‹РІРЅРѕР№ СЂР°Р±РѕС‚С‹)
        poh = dh.get("power_on_hours")
        if isinstance(poh, (int, float)) and poh > 30000:
            findings.append({
                "severity": "low",
                "title": f"Р”РёСЃРє {model} РЅР°СЂР°Р±РѕС‚Р°Р» {poh:,} С‡",
                "detail": "Р’РѕР·СЂР°СЃС‚ РґРёСЃРєР° РїСЂРµРІС‹С€Р°РµС‚ 3.5 РіРѕРґР° РЅРµРїСЂРµСЂС‹РІРЅРѕР№ СЂР°Р±РѕС‚С‹.",
                "suggest": "РЎР»РµРґРёС‚Рµ Р·Р° SMART. Р Р°СЃСЃРјРѕС‚СЂРёС‚Рµ РїР»Р°РЅРѕРІСѓСЋ Р·Р°РјРµРЅСѓ.",
            })
    for d in disks:
        p = d.get("percent", 0)
        mount = d.get("mount", "?")
        if p >= 95:
            findings.append({
                "severity": "high", "title": f"Р”РёСЃРє {mount} РїРѕС‡С‚Рё Р·Р°РїРѕР»РЅРµРЅ",
                "detail": f"{p}% ({d.get('used_gb')}/{d.get('total_gb')} Р“Р‘).",
                "suggest": "РћСЃРІРѕР±РѕРґРёС‚Рµ РјРµСЃС‚Рѕ: РІСЂРµРјРµРЅРЅС‹Рµ, РєСЂСѓРїРЅС‹Рµ РїР°РїРєРё, РєРѕСЂР·РёРЅР°.",
            })
        elif p >= 85:
            findings.append({
                "severity": "medium",
                "title": f"Р”РёСЃРє {mount} Р·Р°РїРѕР»РЅРµРЅ РЅР° {p}%",
                "detail": f"{d.get('used_gb')}/{d.get('total_gb')} Р“Р‘.",
                "suggest": "РћСЃРІРѕР±РѕРґРёС‚Рµ РјРµСЃС‚Рѕ Р·Р°СЂР°РЅРµРµ.",
            })

    # в”Ђв”Ђ РџСЂРѕС†РµСЃСЃС‹-РѕР±Р¶РѕСЂС‹ в”Ђв”Ђ
    for p in procs.get("top_ram", [])[:3]:
        if p.get("ram_mb", 0) > 2000:
            findings.append({
                "severity": "medium",
                "title": f"РџСЂРѕС†РµСЃСЃ {p['name']} РµСЃС‚ РјРЅРѕРіРѕ RAM",
                "detail": f"PID {p['pid']}, {p['ram_mb']} РњР‘.",
                "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ, РЅСѓР¶РµРЅ Р»Рё РѕРЅ СЃРµР№С‡Р°СЃ.",
            })

    # в”Ђв”Ђ Event Log в”Ђв”Ђ
    if len(events) >= 10:
        findings.append({
            "severity": "medium",
            "title": f"РњРЅРѕРіРѕ РѕС€РёР±РѕРє РІ Event Log Р·Р° 24С‡: {len(events)}",
            "detail": "РЎРјРѕС‚СЂРёС‚Рµ event_errors.",
            "suggest": "Р•СЃР»Рё ID РїРѕРІС‚РѕСЂСЏРµС‚СЃСЏ вЂ” РёС‰РёС‚Рµ РµРіРѕ РІ РїРѕРёСЃРєРµ.",
        })
    elif len(events) >= 3:
        findings.append({
            "severity": "low",
            "title": f"РћС€РёР±РєРё РІ Event Log Р·Р° 24С‡: {len(events)}",
            "detail": "РќРµ РєСЂРёС‚РёС‡РЅРѕ, РЅРѕ СЃС‚РѕРёС‚ РіР»СЏРЅСѓС‚СЊ.",
            "suggest": "РЎРјРѕС‚СЂРёС‚Рµ event_errors.",
        })

    # в”Ђв”Ђ РђРІС‚РѕР·Р°РіСЂСѓР·РєР° в”Ђв”Ђ
    if len(startup) > 15:
        findings.append({
            "severity": "low",
            "title": f"РђРІС‚РѕР·Р°РіСЂСѓР·РєР° СЂР°Р·РґСѓС‚Р°: {len(startup)} Р·Р°РїРёСЃРµР№",
            "detail": "Р—Р°РјРµРґР»СЏРµС‚ СЃС‚Р°СЂС‚ СЃРёСЃС‚РµРјС‹.",
            "suggest": "РћС‚РєР»СЋС‡РёС‚Рµ РЅРµРЅСѓР¶РЅРѕРµ: Р”РёСЃРїРµС‚С‡РµСЂ Р·Р°РґР°С‡ в†’ РђРІС‚РѕР·Р°РіСЂСѓР·РєР°.",
        })

    # в”Ђв”Ђ РЎРµС‚СЊ в”Ђв”Ђ
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
                "severity": "high", "title": "РЁР»СЋР· РЅРµРґРѕСЃС‚СѓРїРµРЅ",
                "detail": f"РџРёРЅРі РґРѕ {gw_ping.get('host')} РЅРµ РїСЂРѕС…РѕРґРёС‚. "
                          f"Р›РѕРєР°Р»СЊРЅР°СЏ СЃРµС‚СЊ/Wi-Fi РјРѕР¶РµС‚ Р±С‹С‚СЊ СЃР»РѕРјР°РЅР°.",
                "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ РєР°Р±РµР»СЊ/Wi-Fi, СЂРѕСѓС‚РµСЂ, РѕС‚РєР»СЋС‡РёС‚Рµ VPN.",
            })
        elif gw_ping and gw_ping.get("loss_pct", 0) > 20:
            findings.append({
                "severity": "medium",
                "title": f"РџРѕС‚РµСЂРё РїР°РєРµС‚РѕРІ РґРѕ С€Р»СЋР·Р°: {gw_ping['loss_pct']}%",
                "detail": f"РџРёРЅРі РґРѕ {gw_ping['host']}, "
                          f"СЃСЂРµРґРЅРµРµ {gw_ping.get('avg_ms')} РјСЃ.",
                "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ Wi-Fi СЃРёРіРЅР°Р» РёР»Рё РєР°Р±РµР»СЊ.",
            })

        if inet_ping and not inet_ping.get("ok"):
            findings.append({
                "severity": "high",
                "title": "РРЅС‚РµСЂРЅРµС‚ РЅРµРґРѕСЃС‚СѓРїРµРЅ (8.8.8.8)",
                "detail": "РЁР»СЋР· РјРѕР¶РµС‚ Р±С‹С‚СЊ РґРѕСЃС‚СѓРїРµРЅ, Р° РІРЅРµС€РЅРёР№ РёРЅС‚РµСЂРЅРµС‚ вЂ” РЅРµС‚.",
                "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°СЃС‚СЂРѕР№РєРё СЂРѕСѓС‚РµСЂР°, DNS, VPN/Windscribe.",
            })
        elif inet_ping and inet_ping.get("loss_pct", 0) > 20:
            findings.append({
                "severity": "medium",
                "title": f"РџРѕС‚РµСЂРё РїР°РєРµС‚РѕРІ РІ РёРЅС‚РµСЂРЅРµС‚: {inet_ping['loss_pct']}%",
                "detail": f"РЎСЂРµРґРЅРёР№ РїРёРЅРі {inet_ping.get('avg_ms')} РјСЃ РґРѕ 8.8.8.8.",
                "suggest": "Р’РѕР·РјРѕР¶РЅРѕ, РїСЂРѕРІР°Р№РґРµСЂ РёР»Рё VPN. РџСЂРѕРІРµСЂСЊС‚Рµ Р±РµР· VPN.",
            })

    # в”Ђв”Ђ РЎР»СѓР¶Р±С‹ в”Ђв”Ђ
    services_real = [
        s for s in services
        if (s.get("name") or "").lower() not in ON_DEMAND_OK
    ]
    if len(services_real) >= 3:
        findings.append({
            "severity": "medium",
            "title": f"РћСЃС‚Р°РЅРѕРІР»РµРЅС‹ {len(services_real)} Р°РІС‚Рѕ-СЃР»СѓР¶Р±",
            "detail": ", ".join(s.get("name", "?") for s in services_real[:5]),
            "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ РІ services.msc вЂ” РІРѕР·РјРѕР¶РЅРѕ, РґСЂР°Р№РІРµСЂ РЅРµ СЂР°Р±РѕС‚Р°РµС‚.",
        })
    elif len(services_real) >= 1:
        findings.append({
            "severity": "low",
            "title": f"РћСЃС‚Р°РЅРѕРІР»РµРЅС‹ Р°РІС‚Рѕ-СЃР»СѓР¶Р±С‹: {len(services_real)}",
            "detail": ", ".join(s.get("name", "?") for s in services_real[:5]),
            "suggest": "Р•СЃР»Рё РїСЂРѕР±Р»РµРјР° СЃ СѓСЃС‚СЂРѕР№СЃС‚РІРѕРј вЂ” РїСЂРѕРІРµСЂСЊС‚Рµ РІ services.msc.",
        })

    # в”Ђв”Ђ РџР°РїРєРё в”Ђв”Ђ
    big = [f for f in folders if f.get("gb", 0) >= 5]
    if big:
        names = ", ".join(f"{f['name']} ({f['gb']} Р“Р‘)" for f in big[:5])
        findings.append({
            "severity": "medium",
            "title": f"РљСЂСѓРїРЅС‹Рµ РїР°РїРєРё РІ РїСЂРѕС„РёР»Рµ: {len(big)}",
            "detail": names,
            "suggest": "РџСЂРѕРІРµСЂСЊС‚Рµ СЃРѕРґРµСЂР¶РёРјРѕРµ вЂ” С‚Р°Рј РјРѕР¶РµС‚ Р±С‹С‚СЊ РєСЌС€, "
                       "СЃС‚Р°СЂС‹Рµ СѓСЃС‚Р°РЅРѕРІС‰РёРєРё, Docker.",
        })

    return findings
