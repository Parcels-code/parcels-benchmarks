

import platform
import psutil
import cpuinfo
import subprocess
import json
import os
import socket

def get_cpuinfo():
    info = {}
    info["cpu"] = {}
    info["cpu"]["architecture"] = platform.processor()
    info["cpu"]["model"] = cpuinfo.get_cpu_info().get('brand_raw', 'unknown')
    info["cpu"]["count"] = psutil.cpu_count(logical=False)
    info["cpu"]["count_logical"] = psutil.cpu_count(logical=True)
    info["cpu"]["freq_MHz"] = psutil.cpu_freq().max
    return info

def get_meminfo():
    info = {}
    try:
        out = subprocess.check_output(["sudo", "lshw", "-C", "memory", "-json"], stderr=subprocess.STDOUT, text=True)
        mem = json.loads(out)
        for item in mem:
            if "bank" in item.get("id", ""):
                info["description"] = item.get("description", "")
                info["width_bits"] = item.get("width", "")
                info["clock_MHz"] = item.get("clock", 0) / 1e6
                break

                
    except Exception:
        info = {}

    return info

def read_first_matching_line(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    except Exception:
        return ""
    
def get_device_attr(dev, attr):
    # Works for SATA/SAS/NVMe with slight differences; many expose device/{model,vendor}
    p = f"/sys/block/{dev}/device/{attr}"
    return read_first_matching_line(p)

def list_block_devices():
    try:
        return sorted(d for d in os.listdir("/sys/block") if os.path.exists(f"/sys/block/{d}/device"))
    except Exception:
        return []

def is_rotational(dev):
    path = f"/sys/block/{dev}/queue/rotational"
    val = read_first_matching_line(path)
    if val is None:
        return None
    return val.strip() == "1"

def get_block_size_bytes(dev):
    # sector count * 512 (Linux logical sector default; could read /sys/block/DEV/queue/hw_sector_size if needed)
    sectors = read_first_matching_line(f"/sys/block/{dev}/size")
    if not sectors:
        return None
    try:
        return int(sectors) * 512
    except Exception:
        return None
    
def get_diskinfo():
    disks = []
    for dev in list_block_devices():
        # Skip virtual devices we don't want to attribute capacity to (loop, ram, dm- are mappers)
        if dev.startswith("loop") or dev.startswith("ram") or dev.startswith("fd") or dev.startswith("dm-"):
            continue
        size_b = get_block_size_bytes(dev)
        rot = is_rotational(dev)
        model = get_device_attr(dev, "model")
        vendor = get_device_attr(dev, "vendor")
        # NVMe sometimes uses different attributes
        if model is None and dev.startswith("nvme"):
            model = get_device_attr(dev, "model") or read_first_matching_line(f"/sys/block/{dev}/device/device/model")
            vendor = get_device_attr(dev, "vendor") or read_first_matching_line(f"/sys/block/{dev}/device/device/vendor")

        # Interface type guess (very rough)
        interface = None
        try:
            # e.g., /sys/block/sda/device/subsystem -> .../scsi/
            subsys = os.path.realpath(f"/sys/block/{dev}/device/subsystem")
            if "nvme" in subsys:
                interface = "NVMe"
            elif "scsi" in subsys:
                interface = "SCSI/SATA/SAS"
        except Exception:
            pass

        disks.append({
            "device": dev,
            "size_gb": size_b/1e9,
            "rotational": rot,  # True=HDD, False=SSD (NVMe/SATA SSD)
            "interface": interface,
            "model": model,
            "vendor": vendor,
        })

    return disks

def get_machine():

    machine = {
        "hostname": socket.gethostname(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "cpu": get_cpuinfo(),
        "memory": get_meminfo(),
        "disks": get_diskinfo(),
    }

    
    return machine
    

if __name__ == "__main__":
    info = get_machine()
    print(json.dumps(info, indent=2))