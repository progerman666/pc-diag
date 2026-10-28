"""Read-only сборщики данных о системе. Ничего не меняют."""
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timezone

import psutil


LEVEL_RU = {
    "Critical": "Критический", "Error": "Ошибка",
    "Warning": "Предупреждение", "Information": "Информация",
    "Verbose": "Подробно", "Критический": "Критический",
    "Ошибка": "Ошибка", "Предупреждение": "Предупреждение",
    "Информация": "Информация",
}

SMARTCTL = r"C:\Program Files\smartmontools\bin\smartctl.exe"


def _run(cmd: list[str], timeout: int = 10) -> str:
    if cmd and "powershell" in cmd[0].lower():
        for i, part in enumerate(cmd):
            if part == "-Command" and i + 1 < len(cmd):
                cmd = list(cmd)
                cmd[i + 1] = (
                    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                    + cmd[i + 1]
                )
                break
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout)
        for enc in ("utf-8", "cp866", "cp1251"):
            try:
                return out.stdout.decode(enc).strip()
            except UnicodeDecodeError:
                continue
        return out.stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"[error: {e}]"


def get_system_info() -> dict:
    uname = platform.uname()
    boot = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
    uptime_h = (datetime.now(timezone.utc) - boot).total_seconds() / 3600
    return {
        "os": f"{uname.system} {uname.release}",
        "machine": uname.machine,
        "hostname": uname.node,
        "python": platform.python_version(),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "ram_total_gb": round(psutil.virtual_memory().total / 1024**3, 1),
        "uptime_hours": round(uptime_h, 1),
    }


def get_cpu_ram() -> dict:
    vm = psutil.virtual_memory()
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / 1024**3, 1),
        "ram_available_gb": round(vm.available / 1024**3, 1),
        "swap_percent": psutil.swap_memory().percent,
    }


def get_top_processes(n: int = 10) -> dict:
    cores = psutil.cpu_count(logical=True) or 1
    for p in psutil.process_iter():
        try:
            p.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    SKIP_PIDS = {0, 4}
    SKIP_NAMES = {"Registry", "Memory Compression", "?"}
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            if info["pid"] in SKIP_PIDS:
                continue
            name = info["name"] or "?"
            if name in SKIP_NAMES:
                continue
            rss = info["memory_info"].rss / 1024**2 if info["memory_info"] else 0
            cpu = (info["cpu_percent"] or 0) / cores
            procs.append({
                "pid": info["pid"], "name": name,
                "cpu_percent": round(cpu, 1), "ram_mb": round(rss, 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    top_cpu = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:n]
    top_ram = sorted(procs, key=lambda x: x["ram_mb"], reverse=True)[:n]
    return {"top_cpu": top_cpu, "top_ram": top_ram}


def get_disks() -> list[dict]:
    out = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            out.append({
                "mount": part.mountpoint, "fstype": part.fstype,
                "total_gb": round(usage.total / 1024**3, 1),
                "used_gb": round(usage.used / 1024**3, 1),
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            continue
    return out


def _smartctl_scan() -> dict:
    """Возвращает {device_id: '/dev/sda' или '/dev/pd0'}.
    Использует smartctl --scan для маппинга индексов на устройства."""
    if not os.path.exists(SMARTCTL):
        return {}
    try:
        r = subprocess.run(
            [SMARTCTL, "--scan"],
            capture_output=True, timeout=15,
        )
        text = r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return {}

    mapping = {}
    idx = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Пример: /dev/sda -d ata # /dev/sda, ATA device
        dev = line.split()[0]
        mapping[str(idx)] = dev
        idx += 1
    return mapping


def _smartctl_query(device: str) -> dict:
    """Запрашивает smartctl -a -j <device>, парсит ключевые поля."""
    if not os.path.exists(SMARTCTL) or not device:
        return {}
    try:
        r = subprocess.run(
            [SMARTCTL, "-a", "-j", device],
            capture_output=True, timeout=30,
        )
        # Коды возврата smartctl: 0 = ok, 1 = SMART warning, 4 = prefail
        if r.returncode not in (0, 1, 2, 4, 8):
            return {}
        raw = r.stdout.decode("utf-8", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
    except Exception:
        return {}

    out = {}

    # Температура
    temp = data.get("temperature", {}).get("current")
    if temp is not None:
        out["temperature"] = int(temp)

    # Наработка (ATA/SCSI)
    poh = data.get("power_on_time", {}).get("hours")
    if poh is not None:
        out["power_on_hours"] = int(poh)

    # NVMe-специфичные поля
    nvme = data.get("nvme_smart_health_information_log", {})
    if nvme:
        pu = nvme.get("percentage_used")
        if pu is not None:
            out["wear"] = int(pu)
        nvme_temp = nvme.get("temperature")
        if nvme_temp is not None and "temperature" not in out:
            out["temperature"] = int(nvme_temp)
        nvme_poh = nvme.get("power_on_hours")
        if nvme_poh is not None and "power_on_hours" not in out:
            out["power_on_hours"] = int(nvme_poh)

    # ATA-атрибуты (SATA SSD/HDD)
    ata = data.get("ata_smart_attributes", {}).get("table", [])
    for attr in ata:
        name = (attr.get("name") or "").lower()
        raw_val = attr.get("raw", {}).get("value")
        if raw_val is None:
            continue
        try:
            rv = int(raw_val)
        except (ValueError, TypeError):
            continue

        if "ssd_life_left" in name and "wear" not in out:
            # остаток ресурса → износ = 100 - остаток
            out["wear"] = max(0, min(100, 100 - rv))
        elif "wear_leveling" in name and "wear" not in out:
            # raw = среднее число циклов стирания, не проценты —
            # но поле полезно для оценки
            out["wear_leveling_count"] = rv
        elif name == "reallocated_sector_ct":
            out["reallocated_sectors"] = rv
        elif name == "power_on_hours" and "power_on_hours" not in out:
            out["power_on_hours"] = rv
        elif name == "temperature_celsius" and "temperature" not in out:
            # raw обычно "35 (Min/Max ...)" — первое число
            m = re.match(r"(\d+)", str(raw_val))
            if m:
                out["temperature"] = int(m.group(1))
        elif "media_wearout_indicator" in name and "wear" not in out:
            out["wear"] = max(0, min(100, 100 - rv))

    # Общий статус SMART
    passed = data.get("smart_status", {}).get("passed")
    if passed is not None:
        out["health_passed"] = bool(passed)

    return out


def get_disk_health() -> list[dict]:
    """SMART-статус физических дисков.

    Источники (по приоритету):
      1. Get-PhysicalDisk + Get-StorageReliabilityCounter (WMI)
      2. MSStorageDriver_FailurePredictStatus (WMI)
      3. smartctl (smartmontools) — если WMI не дал ключевые поля
    """
    # 1. Базовый статус
    ps_base = (
        "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, "
        "HealthStatus, OperationalStatus, DeviceId | ConvertTo-Json -Compress"
    )
    raw_base = _run(["powershell", "-NoProfile", "-Command", ps_base], timeout=20)
    base_list = []
    if raw_base and not raw_base.startswith("[error") and raw_base != "null":
        try:
            data = json.loads(raw_base)
            if isinstance(data, dict):
                data = [data]
            base_list = data
        except Exception:
            pass

    # 2. Детальные счётчики WMI
    ps_rel = (
        "Get-PhysicalDisk | Get-StorageReliabilityCounter | "
        "Select-Object DeviceId, Temperature, Wear, PowerOnHours, "
        "ReadErrorsTotal, ReadErrorsUncorrected, WriteErrorsTotal, "
        "WriteErrorsUncorrected | ConvertTo-Json -Compress"
    )
    raw_rel = _run(["powershell", "-NoProfile", "-Command", ps_rel], timeout=20)
    rel_map = {}
    if raw_rel and not raw_rel.startswith("[error") and raw_rel != "null":
        try:
            data = json.loads(raw_rel)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                dev_id = item.get("DeviceId")
                if dev_id is not None:
                    rel_map[str(dev_id)] = item
        except Exception:
            pass

    # 3. PredictFailure
    ps_fail = (
        "Get-CimInstance -Namespace root\\wmi "
        "-ClassName MSStorageDriver_FailurePredictStatus "
        "-ErrorAction SilentlyContinue | "
        "Select-Object InstanceName, PredictFailure, Reason | "
        "ConvertTo-Json -Compress"
    )
    raw_fail = _run(["powershell", "-NoProfile", "-Command", ps_fail], timeout=20)
    fail_map = {}
    if raw_fail and not raw_fail.startswith("[error") and raw_fail != "null":
        try:
            data = json.loads(raw_fail)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                inst = item.get("InstanceName", "")
                for b in base_list:
                    if str(b.get("DeviceId")) in inst:
                        fail_map[str(b.get("DeviceId"))] = item
                        break
        except Exception:
            pass

    # 4. Маппинг device_id → /dev/sdX для smartctl (сканируем один раз)
    smart_map = _smartctl_scan()

    # Сборка результата
    result = []
    for b in base_list:
        dev_id = b.get("DeviceId")
        rel = rel_map.get(str(dev_id), {})
        fail = fail_map.get(str(dev_id), {})

        entry = {
            "device_id": dev_id,
            "model": b.get("FriendlyName") or "?",
            "media_type": str(b.get("MediaType") or "?"),
            "health_status": str(b.get("HealthStatus") or "?"),
            "operational_status": str(b.get("OperationalStatus") or "?"),
            "predict_failure": fail.get("PredictFailure") if fail else None,
            "fail_reason": fail.get("Reason") if fail else None,
            "temperature": rel.get("Temperature"),
            "wear": rel.get("Wear"),
            "power_on_hours": rel.get("PowerOnHours"),
            "read_errors_uncorrected": rel.get("ReadErrorsUncorrected"),
            "write_errors_uncorrected": rel.get("WriteErrorsUncorrected"),
            "read_errors_total": rel.get("ReadErrorsTotal"),
            "write_errors_total": rel.get("WriteErrorsTotal"),
            "source": "wmi",
        }

        # Нулевые значения WMI = "нет данных", а не "0 градусов"
        for k in ("temperature", "wear", "power_on_hours"):
            if entry[k] == 0:
                entry[k] = None

        # Fallback на smartctl, если ключевые поля пустые
        if (entry["temperature"] is None
                or entry["wear"] is None
                or entry["power_on_hours"] is None):
            dev_path = smart_map.get(str(dev_id))
            if dev_path:
                fb = _smartctl_query(dev_path)
                if fb:
                    entry["source"] = "smartctl"
                    for k in ("temperature", "wear", "power_on_hours"):
                        if entry[k] is None and fb.get(k) is not None:
                            entry[k] = fb[k]
                    if fb.get("reallocated_sectors") is not None:
                        entry["reallocated_sectors"] = fb["reallocated_sectors"]
                    if fb.get("health_passed") is not None:
                        entry["smartctl_passed"] = fb["health_passed"]

        result.append(entry)

    return result


def get_startup_details() -> list[dict]:
    """Автозагрузка: имя, команда, путь, пользователь."""
    ps = (
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name, Command, Location, User | "
        "ConvertTo-Json -Compress"
    )
    raw = _run(["powershell", "-NoProfile", "-Command", ps], timeout=20)
    if not raw or raw.startswith("[error") or raw == "null":
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [
            {
                "name": d.get("Name") or "?",
                "command": d.get("Command") or "",
                "location": d.get("Location") or "",
                "user": d.get("User") or "",
            }
            for d in data
        ]
    except Exception:
        return []


def get_event_errors(last_hours: int = 24, limit: int = 20) -> list[str]:
    ps = (
        f"Get-WinEvent -FilterHashtable @{{LogName='System';Level=1,2;"
        f"StartTime=(Get-Date).AddHours(-{last_hours})}} -MaxEvents {limit} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object @{n='T';e={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')}}, "
        "ProviderName, Id, LevelDisplayName | "
        "ConvertTo-Json -Compress"
    )
    raw = _run(["powershell", "-NoProfile", "-Command", ps], timeout=30)
    if not raw or raw.startswith("[error") or raw == "null":
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [
            f"{d.get('T')} | {d.get('ProviderName')} | "
            f"ID={d.get('Id')} | "
            f"{LEVEL_RU.get(d.get('LevelDisplayName'), d.get('LevelDisplayName'))}"
            for d in data
        ]
    except Exception:
        return []


def _ping(host: str, count: int = 4) -> dict:
    """Пинг через системный ping. Возвращает потери и средний RTT."""
    try:
        result = subprocess.run(
            ["ping", "-n", str(count), "-w", "1000", host],
            capture_output=True, timeout=30,
        )
        output = None
        for enc in ("cp866", "cp1251", "utf-8"):
            try:
                output = result.stdout.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if output is None:
            output = result.stdout.decode("utf-8", errors="replace")

        received = output.count("TTL=") + output.count("ttl=")
        m = re.search(r"(?:Average|Среднее)\s*=\s*(\d+)", output)
        avg_ms = int(m.group(1)) if m else None
        return {
            "host": host, "sent": count, "received": received,
            "loss_pct": round((count - received) / count * 100, 1),
            "avg_ms": avg_ms, "ok": received > 0,
        }
    except Exception as e:
        return {"host": host, "ok": False, "error": str(e)}


def get_network() -> dict:
    """Шлюз, DNS и пинг до шлюза и 8.8.8.8."""
    ps = (
        "$cfg = Get-NetIPConfiguration | "
        "Where-Object {$_.IPv4DefaultGateway -ne $null} | Select-Object -First 1; "
        "$dns = Get-DnsClientServerAddress -AddressFamily IPv4 | "
        "Where-Object {$_.ServerAddresses.Count -gt 0} | Select-Object -First 1; "
        "[PSCustomObject]@{ "
        "Interface = $cfg.InterfaceAlias; "
        "Gateway = $cfg.IPv4DefaultGateway.NextHop; "
        "DNS = ($dns.ServerAddresses -join ', ') "
        "} | ConvertTo-Json -Compress"
    )
    raw = _run(["powershell", "-NoProfile", "-Command", ps], timeout=15)
    gateway = None
    dns = None
    iface = None
    if raw and not raw.startswith("[error") and raw != "null":
        try:
            info = json.loads(raw)
            gateway = info.get("Gateway")
            dns = info.get("DNS")
            iface = info.get("Interface")
        except Exception:
            pass

    pings = []
    if gateway:
        pings.append(_ping(gateway))
    pings.append(_ping("8.8.8.8"))

    return {
        "interface": iface, "gateway": gateway, "dns": dns,
        "pings": pings,
    }


def get_folder_sizes(top_n: int = 20) -> list[dict]:
    """Топ папок в домашней директории по размеру.
    Может занять 30-60 сек на большом профиле."""
    ps = (
        "$dirs = Get-ChildItem $env:USERPROFILE -Directory -Force "
        "-ErrorAction SilentlyContinue; "
        "$result = foreach ($d in $dirs) { "
        "$size = (Get-ChildItem $d.FullName -Recurse -File -Force "
        "-ErrorAction SilentlyContinue | "
        "Measure-Object -Property Length -Sum).Sum; "
        "if ($size -gt 0) { "
        "[PSCustomObject]@{ Name=$d.Name; Bytes=$size } } }; "
        f"$result | Sort-Object Bytes -Descending | Select-Object -First {top_n} | "
        "ConvertTo-Json -Compress"
    )
    raw = _run(["powershell", "-NoProfile", "-Command", ps], timeout=180)
    if not raw or raw.startswith("[error") or raw == "null":
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [
            {"name": d.get("Name"), "gb": round((d.get("Bytes") or 0) / 1024**3, 2)}
            for d in data
        ]
    except Exception:
        return []


def get_services_errors() -> list[dict]:
    """Службы с типом запуска Automatic, которые не Running."""
    ps = (
        "Get-Service | Where-Object { $_.StartType -eq 'Automatic' "
        "-and $_.Status -ne 'Running' } | "
        "Select-Object Name, DisplayName, Status | "
        "ConvertTo-Json -Compress"
    )
    raw = _run(["powershell", "-NoProfile", "-Command", ps], timeout=20)
    if not raw or raw.startswith("[error") or raw == "null":
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [
            {
                "name": d.get("Name"),
                "display_name": d.get("DisplayName"),
                "status": str(d.get("Status")),
            }
            for d in data
        ]
    except Exception:
        return []


def collect_all(skip_slow: bool = False) -> dict:
    """skip_slow=True пропускает get_folder_sizes (медленный, 30-60 сек)."""
    data = {
        "system": get_system_info(),
        "load": get_cpu_ram(),
        "processes": get_top_processes(),
        "disks": get_disks(),
        "disk_health": get_disk_health(),
        "startup": get_startup_details(),
        "event_errors": get_event_errors(),
        "network": get_network(),
        "services": get_services_errors(),
    }
    if not skip_slow:
        data["folder_sizes"] = get_folder_sizes()
    else:
        data["folder_sizes"] = []
    return data