import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime

class FocusManager:
    def __init__(self):
        self.is_deep_work: bool = False
        self.session_start_time: Optional[float] = None
        self.target_duration_seconds: int = 0
        self.project_name: str = "Geral"

    def start_deep_work(self, minutes: int = 60, project: str = "Geral") -> Dict[str, Any]:
        self.is_deep_work = True
        self.session_start_time = time.time()
        self.target_duration_seconds = minutes * 60
        self.project_name = project

        return {
            "status": "active",
            "project": project,
            "duration_minutes": minutes,
            "start_time": datetime.now().strftime("%H:%M:%S")
        }

    def stop_deep_work(self) -> Dict[str, Any]:
        if not self.is_deep_work or not self.session_start_time:
            return {"status": "inactive", "elapsed_minutes": 0}

        elapsed_sec = time.time() - self.session_start_time
        elapsed_min = int(elapsed_sec // 60)
        self.is_deep_work = False
        self.session_start_time = None

        return {
            "status": "stopped",
            "project": self.project_name,
            "elapsed_minutes": elapsed_min
        }

    def get_deep_work_status(self) -> Dict[str, Any]:
        if not self.is_deep_work or not self.session_start_time:
            return {"is_active": False, "elapsed_seconds": 0, "remaining_seconds": 0}

        elapsed = int(time.time() - self.session_start_time)
        remaining = max(0, self.target_duration_seconds - elapsed)
        return {
            "is_active": True,
            "project": self.project_name,
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "target_seconds": self.target_duration_seconds
        }

    @staticmethod
    def get_hardware_metrics() -> Dict[str, Any]:
        """Lê uso de CPU e memória RAM em tempo real."""
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": cpu_percent,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent
        }
