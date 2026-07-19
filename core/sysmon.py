"""core/sysmon.py — Theo dõi CPU / RAM / GPU thời gian thực (nhẹ, chạy nền).

Dùng cho thanh trạng thái ở footer: người dùng thấy máy đang tải bao nhiêu,
biết vì sao render chậm, và tự giảm số worker trong Cài đặt nếu cần.

- CPU/RAM: psutil nếu có, không thì gọi API Windows (không thêm phụ thuộc).
- GPU: nvidia-smi (chỉ NVIDIA). Không có GPU → trả None, UI ẩn phần GPU.
Mỗi chỉ số đo trong thread nền, cache lại; UI chỉ đọc cache nên không bị khựng.
"""
import os, shutil, logging, subprocess, threading; logger = logging.getLogger("TubeCraft.SysMon"); _CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0; POLL_SECONDS = 2.0; _state = {"cpu": 0.0, "ram": 0.0, "ram_used_gb": 0.0, "ram_total_gb": 0.0, "gpu": None, "gpu_mem_used_gb": 0.0, "gpu_mem_total_gb": 0.0, "gpu_name": ""}; _lock = threading.Lock(); _thread = None; _stop = threading.Event()
def _read_cpu_ram():
    try:
        import psutil
        vm = psutil.virtual_memory()
        return (psutil.cpu_percent(interval=None), vm.percent,
            (vm.used) / 1_073_741_824, (vm.total) / 1_073_741_824)
    except Exception:
        pass
    if os.name == "nt":
        try:
            import ctypes
            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = _MS()
            ms.dwLength = ctypes.sizeof(_MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            total = (ms.ullTotalPhys) / 1_073_741_824
            used = ((ms.ullTotalPhys) - (ms.ullAvailPhys)) / 1_073_741_824
            return (_cpu_percent_windows(), float(ms.dwMemoryLoad), used, total)
        except Exception:
            return (0.0, 0.0, 0.0, 0.0)
    return (0.0, 0.0, 0.0, 0.0)

_last_kernel = _last_user = (_last_idle := None)

def _cpu_percent_windows() -> float:
    global _last_idle
    global _last_kernel
    global _last_user
    try:
        import ctypes
        from ctypes import wintypes
        user = wintypes.FILETIME()
        kern = wintypes.FILETIME()
        idle = wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
            return 0.0
        def _v(ft):
            return (ft.dwHighDateTime) << 32 | ft.dwLowDateTime
        u = _v(user)
        k = _v(kern)
        i = _v(idle)
        if _last_idle is None:
            _last_idle = i
            _last_kernel = k
            _last_user = u
            return 0.0
        du = u - _last_user
        dk = k - _last_kernel
        di = i - _last_idle
        _last_idle = i
        _last_kernel = k
        _last_user = u
        total = dk + du
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, (total - di) * 100.0 / total))
    except Exception:
        return 0.0

_nvidia_smi = None; _gpu_available = None
def _read_gpu():
    global _nvidia_smi
    global _gpu_available
    if _gpu_available is False:
        return None
    elif _nvidia_smi is None:
        _nvidia_smi = shutil.which("nvidia-smi") or ""
        if not _nvidia_smi:
            _gpu_available = False
            return None
    try:
        r = subprocess.run([_nvidia_smi, "--query-gpu=utilization.gpu,memory.used,memory.total,name", "--format=csv,noheader,nounits"], capture_output=True, timeout=5, creationflags=_CREATE_NO_WINDOW)
        if r.returncode != 0:
            _gpu_available = False
            return None
        line = r.stdout.decode("utf-8", "replace").strip().splitlines()[0]
        util, used, total, name = [p.strip() for p in line.split(",", 3)]
        _gpu_available = True
        return (float(util), float(used) / 1024, float(total) / 1024, name)
    except Exception:
        _gpu_available = False
        return None

def _loop():
    while not _stop.is_set():
        cpu, ram, ru, rt = _read_cpu_ram()
        gpu = _read_gpu()
        with _lock:
            _state["cpu"] = cpu
            _state["ram"] = ram
            _state["ram_used_gb"] = ru
            _state["ram_total_gb"] = rt
            if gpu:
                _state["gpu"], _state["gpu_mem_used_gb"], _state["gpu_mem_total_gb"], _state["gpu_name"] = gpu
            else:
                _state["gpu"] = None
        _stop.wait(POLL_SECONDS)

def start():
    global _thread
    if _thread and _thread.is_alive():
        return None
    _stop.clear(); _thread = threading.Thread(target=_loop, daemon=True, name="TubeCraft-SysMon"); _thread.start()

def stop():
    _stop.set()

def snapshot() -> dict:
    with _lock:
        return dict(_state)

def is_busy(cpu_limit: float=85.0, ram_limit: float=90.0) -> bool:
    s = snapshot()
    return s["cpu"] >= cpu_limit or s["ram"] >= ram_limit
