
import subprocess
import os
import shlex
import re
import datetime as dt


# Regex for lines with key-value pairs
KV_RE = re.compile(r"^([^:]+):\s*(.*)$")
ELAPSED_RE = re.compile(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)")

def parse_elapsed_to_seconds(s):
    """
    Parse elapsed time string from `/usr/bin/time -v`, which can be h:mm:ss, m:ss, or s.ss.
    Returns seconds as float.
    """
    if not s:
        return 0.0
    if s.count(':') == 2:
        h, m, sec = s.split(':')
        return int(h) * 3600 + int(m) * 60 + float(sec)
    elif s.count(':') == 1:
        m, sec = s.split(':')
        return int(m) * 60 + float(sec)
    else:
        # Just seconds
        return float(s)
    
def parse_time_v_output(stderr_text):
    """
    Parse `/usr/bin/time -v` stderr into a dict with normalized keys.
    """
    metrics = {}
    for line in stderr_text.splitlines():
        m = KV_RE.match(line.strip())
        if not m:
            continue
        key, val = m.group(1).strip(), m.group(2).strip()

        # Normalize a few important fields
        if key.startswith("Elapsed (wall clock) time"):
            m = ELAPSED_RE.match(line.strip())
            if not m:
                continue
            val = m.group(1).strip()
            metrics["elapsed_s"] = parse_elapsed_to_seconds(val)
        elif key == "Maximum resident set size (kbytes)":
            # Convert to bytes
            try:
                metrics["max_rss_bytes"] = int(val) * 1024
            except:
                metrics["max_rss_bytes"] = None
        elif key == "Exit status":
            metrics["exit_status"] = int(val)
  
    return metrics


def time_v(cmd):
    """
    Run command under `/usr/bin/time -v`, capture stdout, stderr, and return code.
    """
    time_bin = "/usr/bin/time"
    if not os.path.exists(time_bin):
        raise FileNotFoundError(f"{time_bin} not found. Please install GNU time (often the 'time' package).")

    full_cmd = [time_bin, "-v"] + shlex.split(cmd)
    proc = subprocess.Popen(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()
    result = {
        "timestamp_utc": dt.datetime.utcnow().isoformat() + "Z",
        "command": cmd
    }
    result.update(parse_time_v_output(err))

    return result