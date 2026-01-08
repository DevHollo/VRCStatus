from pythonosc.udp_client import SimpleUDPClient
from messages import Messages
from vars import *
import psutil
import pynvml
import random
import ctypes
import yaml
import time
import sys
import os

messages = Messages()

if os.name != "nt":
    messages.error("Please use a Windows 10+ machine!")

client = SimpleUDPClient(OSC_HOST, OSC_PORT)

gpu_available = True
try:
    pynvml.nvmlInit()
    GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
except Exception:
    gpu_available = False

with open(STATUS_FILE, "r", encoding="utf-8") as f:
    STATUS_LIST = yaml.safe_load(f)["statuses"]

class StatusPicker:
    def __init__(self, statuses):
        self.statuses = statuses
        self.last = None

    def random(self):
        if len(self.statuses) <= 1:
            return self.statuses[0]

        choice = random.choice(self.statuses)
        while choice == self.last:
            choice = random.choice(self.statuses)

        self.last = choice
        return choice

status_picker = StatusPicker(STATUS_LIST)

def is_vrchat_running():
    for proc in psutil.process_iter(attrs=["name"]):
        try:
            if proc.info["name"] == PROCESS_NAME:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def get_system_stats():
    cpu = psutil.cpu_percent(interval=None)

    mem = psutil.virtual_memory()
    ram_used = mem.used / (1024 ** 3)
    ram_total = mem.total / (1024 ** 3)

    gpu = "N/A"
    if gpu_available:
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(GPU_HANDLE)
            gpu = f"{util.gpu}%"
        except Exception:
            pass

    return cpu, gpu, ram_used, ram_total

def idle_seconds():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000

def is_vrchat_focused():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return False

    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    try:
        return psutil.Process(pid.value).name().lower() == PROCESS_NAME.lower()
    except psutil.NoSuchProcess:
        return False

def get_afk_state():
    return idle_seconds() >= (AFK_TIMEOUT * 60) or not is_vrchat_focused()

def format_afk_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s" if m > 0 else f"{s}s"

_afk_start_time = None

def get_status_line(is_afk):
    global _afk_start_time

    if is_afk:
        if _afk_start_time is None:
            _afk_start_time = time.time()
        return f"💤 AFK for {format_afk_time(time.time() - _afk_start_time)}"

    _afk_start_time = None
    return f"💬 {status_picker.last or status_picker.random()}"

def get_current_time(no_timezone: bool = False):
    now = time.localtime()

    if no_timezone:
        return time.strftime("%H:%M:%S", now)

    tz_name = time.tzname[now.tm_isdst]
    offset = -time.altzone if now.tm_isdst else -time.timezone
    utc_hours = offset // 3600

    return f"{time.strftime('%H:%M:%S', now)} {tz_name} (UTC{utc_hours:+})"

os.system("cls")

print(f"\033[38;5;208mWelcome to VRCStatus v{VERSION}\033[0m")
print("\033[38;5;208m+----------------------------------------------+\033[0m\n")

messages.info(f"OSC target: {OSC_HOST}:{OSC_PORT}")
messages.info(f"AFK timeout: {AFK_TIMEOUT} minutes")
messages.info(f"Update interval: {UPDATE_INTERVAL}s")

if gpu_available:
    messages.success("GPU monitoring enabled")
else:
    messages.warning("GPU monitoring unavailable")

temp_check = False

try:
    while True:
        if not is_vrchat_running():
            messages.error("VRChat not running, Exiting.")
            time.sleep(1.2)
            break

        if not temp_check:
            messages.success("VRChat OSC Connected!")
            temp_check = True

        cpu, gpu, ram_used, ram_total = get_system_stats()
        is_afk = get_afk_state()

        status_line = get_status_line(is_afk)

        current_time = get_current_time()

        message = (
            f"{status_line}\n"
            f"CPU: {cpu:.0f}% | GPU: {gpu} | "
            f"RAM: {(ram_used / ram_total) * 100:.0f}%\n"
            f"My Time: {current_time}"
        )

        client.send_message(OSC_PATH, [message, True])
        time.sleep(UPDATE_INTERVAL)
except KeyboardInterrupt:
    messages.warning("Disconnecting from VRChat OSC...")
    time.sleep(0.3)
    client.send_message(OSC_PATH, ["", True])
    time.sleep(1.2)