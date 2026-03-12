import datetime
import os

LOG_FILE = os.path.join("/tmp", "scholarflow_debug.log")

def log_debug(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"DEBUG: {message}", flush=True)
