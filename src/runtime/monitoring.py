from __future__ import annotations

import os
import platform
import shutil
from datetime import datetime
from typing import Any, Dict, Optional


def collect_metrics() -> Dict[str, Any]:
    metrics = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 0,
    }
    metrics.update(_disk_metrics())
    metrics.update(_memory_metrics())
    metrics.update(_cpu_metrics())
    return metrics


def _disk_metrics() -> Dict[str, Any]:
    try:
        total, used, free = shutil.disk_usage(os.getcwd())
        return {
            "disk_total": total,
            "disk_used": used,
            "disk_free": free,
        }
    except Exception:
        return {"disk_total": None, "disk_used": None, "disk_free": None}


def _memory_metrics() -> Dict[str, Any]:
    data = _try_psutil()
    if not data:
        return {"mem_total": None, "mem_used": None, "mem_free": None}
    return {
        "mem_total": data.get("total"),
        "mem_used": data.get("used"),
        "mem_free": data.get("available"),
    }


def _cpu_metrics() -> Dict[str, Any]:
    data = _try_psutil()
    if not data:
        return {"cpu_percent": None}
    return {"cpu_percent": data.get("cpu_percent")}


def _try_psutil() -> Optional[Dict[str, Any]]:
    try:
        import psutil
    except Exception:
        return None
    try:
        vm = psutil.virtual_memory()
        return {
            "total": vm.total,
            "used": vm.used,
            "available": vm.available,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
        }
    except Exception:
        return None
