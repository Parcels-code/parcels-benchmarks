

import platform
from numpy import rint
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
        info['memory'] = json.loads(out)
                
    except Exception:
        info = {}

    return info

def get_diskinfo():
    info = {}
    try:
        out = subprocess.check_output(["sudo", "lshw", "-C", "disk", "-json"], stderr=subprocess.STDOUT, text=True)
        info['disk'] = json.loads(out)
                
    except Exception:
        info['disk'] = {}

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