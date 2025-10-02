

import platform
import psutil
import cpuinfo
import subprocess
import json

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
                info["memory"]["description"] = item.get("description", "")
                info["memory"]["width_bits"] = item.get("width", "")
                info["memory"]["clock_MHz"] = item.get("clock", 0) / 1e6
                break

                
    except Exception:
        info ["memory"] = {}

    return info

def get_diskinfo():
    info = {}
    info["disks"] = []
    try:
        out = subprocess.check_output(["sudo", "lshw", "-C", "disk", "-json"], stderr=subprocess.STDOUT, text=True)
        disks = json.loads(out)
        for item in disks:
            if "configuration" in item.keys():
                disk_info = {}
                disk_info["description"] = item.get("description", "")
                disk_info["logical_name"] = item.get("logicalname", "")
                disk_info["size_GB"] = item.get("size", 0) / 1e9
                info["disks"].append(disk_info)

    except Exception:
        info = {}

    return info

def get_machine():

    machine = {}

    # OS Information
    machine["system"] = platform.system()
    machine["release"] = platform.release()
    machine["name"] = platform.node()
    # CPU information
    machine.update(get_cpuinfo())
    # Memory information
    machine.update(get_meminfo())
    # Disk information
    machine.update(get_diskinfo())
    
    return machine
    

if __name__ == "__main__":
    info = get_machine()
    print(json.dumps(info, indent=2))