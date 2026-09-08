import logging
import os
import time
from typing import Dict, List, Optional, Any
import psutil

logger = logging.getLogger("TelemetryService")


class TelemetryService:
    """Servico de coleta de telemetria de hardware e monitoramento proativo de sobrecarga."""

    RAM_THRESHOLD_PERCENT = 88.0
    CPU_THRESHOLD_PERCENT = 90.0
    DISK_FREE_THRESHOLD_GB = 10.0
    ALERT_COOLDOWN_SECONDS = 60.0

    def __init__(self):
        self.last_alert_time: float = 0.0
        self.last_alert_msg: str = ""
        # Inicializa medidor de CPU sem bloquear
        psutil.cpu_percent(interval=None)

    def get_top_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Identifica os processos que mais consom memoria RAM e processamento."""
        processes = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "memory_percent"]):
            try:
                info = p.info
                name = info.get("name") or "Desconhecido"
                if name.lower() in ["system idle process", "system", "registry"]:
                    continue

                mem_info = info.get("memory_info")
                rss_bytes = mem_info.rss if mem_info else 0
                mem_mb = round(rss_bytes / (1024 * 1024), 1)
                cpu_p = round(info.get("cpu_percent") or 0.0, 1)

                processes.append({
                    "pid": info.get("pid"),
                    "name": name,
                    "cpu_percent": cpu_p,
                    "memory_mb": mem_mb,
                    "memory_percent": round(info.get("memory_percent") or 0.0, 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Ordena prioritariamente por consumo de RAM (MB)
        processes.sort(key=lambda x: x["memory_mb"], reverse=True)
        return processes[:limit]

    def get_system_metrics(self, metric_type: str = "summary") -> Dict[str, Any]:
        """Coleta metricas de sistema detalhadas de acordo com o tipo solicitado."""
        m_type = (metric_type or "summary").lower().strip()

        # 1. CPU
        cpu_p = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True) or 1
        cpu_physical = psutil.cpu_count(logical=False) or cpu_count

        # 2. RAM
        mem = psutil.virtual_memory()
        ram_total = round(mem.total / (1024**3), 2)
        ram_used = round(mem.used / (1024**3), 2)
        ram_free = round(mem.available / (1024**3), 2)
        ram_p = mem.percent

        # 3. Armazenamento (Disco do sistema)
        drive_path = os.path.splitdrive(os.path.abspath("."))[0] or "/"
        if not drive_path.endswith("\\") and not drive_path.endswith("/"):
            drive_path += "\\"
        try:
            disk = psutil.disk_usage(drive_path)
            disk_total = round(disk.total / (1024**3), 2)
            disk_used = round(disk.used / (1024**3), 2)
            disk_free = round(disk.free / (1024**3), 2)
            disk_p = disk.percent
        except Exception:
            disk_total = 0.0
            disk_used = 0.0
            disk_free = 0.0
            disk_p = 0.0

        # 4. Top processos
        top_procs = self.get_top_processes(limit=5) if m_type in ["summary", "top_processes"] else []

        # 5. Deteccao de alertas de sobrecarga
        alert_info = self._check_alerts(cpu_p, ram_p, disk_free, top_procs)

        # 6. Sintese para voz
        reply = self._build_voice_reply(m_type, cpu_p, ram_p, disk_free, top_procs, alert_info)

        base_data = {
            "success": True,
            "metric": m_type,
            "cpu_percent": cpu_p,
            "cpu_count": cpu_count,
            "cpu_physical_count": cpu_physical,
            "ram_used_gb": ram_used,
            "ram_total_gb": ram_total,
            "ram_free_gb": ram_free,
            "ram_percent": ram_p,
            "disk_used_gb": disk_used,
            "disk_total_gb": disk_total,
            "disk_free_gb": disk_free,
            "disk_percent": disk_p,
            "top_processes": top_procs,
            "alert": alert_info,
            "reply": reply,
        }

        if m_type == "cpu":
            return {
                "success": True,
                "metric": "cpu",
                "cpu_percent": cpu_p,
                "cpu_count": cpu_count,
                "alert": alert_info if alert_info and alert_info.get("type") == "cpu" else None,
                "reply": f"Carga geral de CPU em {cpu_p}% distribuída em {cpu_count} núcleos lógicos, senhor.",
            }
        elif m_type == "memory":
            return {
                "success": True,
                "metric": "memory",
                "ram_used_gb": ram_used,
                "ram_total_gb": ram_total,
                "ram_percent": ram_p,
                "alert": alert_info if alert_info and alert_info.get("type") == "memory" else None,
                "reply": f"Memória RAM em {ram_p}%, com {ram_used} GB utilizados de {ram_total} GB.",
            }
        elif m_type == "disk":
            return {
                "success": True,
                "metric": "disk",
                "disk_free_gb": disk_free,
                "disk_total_gb": disk_total,
                "disk_percent": disk_p,
                "alert": alert_info if alert_info and alert_info.get("type") == "disk" else None,
                "reply": f"Disco com {disk_p}% de ocupação. Há {disk_free} GB de espaço livre disponível.",
            }
        elif m_type == "top_processes":
            top_names = [f"{p['name']} ({p['memory_mb']}MB)" for p in top_procs[:3]]
            reply_procs = f"Principais processos em memória: {', '.join(top_names)}." if top_names else "Nenhum processo pesado identificado."
            return {
                "success": True,
                "metric": "top_processes",
                "top_processes": top_procs,
                "reply": reply_procs,
            }

        return base_data

    def _check_alerts(
        self,
        cpu_p: float,
        ram_p: float,
        disk_free: float,
        top_procs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Avalia se os limiares criticos de hardware foram atingidos."""
        now = time.time()
        is_cooldown_expired = (now - self.last_alert_time) > self.ALERT_COOLDOWN_SECONDS

        alert = None

        if ram_p >= self.RAM_THRESHOLD_PERCENT:
            top_proc = top_procs[0]["name"] if top_procs else "Processos do sistema"
            alert = {
                "type": "memory",
                "level": "critical" if ram_p > 95 else "warning",
                "percent": ram_p,
                "message": f"Consumo de memória atingiu {ram_p}%. Processo mais pesado: {top_proc}.",
                "should_notify": is_cooldown_expired,
            }
        elif cpu_p >= self.CPU_THRESHOLD_PERCENT:
            top_proc = top_procs[0]["name"] if top_procs else "Processos ativos"
            alert = {
                "type": "cpu",
                "level": "critical",
                "percent": cpu_p,
                "message": f"Carga de CPU elevada em {cpu_p}%. Atividade intensa detectada.",
                "should_notify": is_cooldown_expired,
            }
        elif disk_free > 0 and disk_free <= self.DISK_FREE_THRESHOLD_GB:
            alert = {
                "type": "disk",
                "level": "warning",
                "free_gb": disk_free,
                "message": f"Espaço em disco reduzido: apenas {disk_free} GB disponíveis.",
                "should_notify": is_cooldown_expired,
            }

        if alert and alert.get("should_notify"):
            self.last_alert_time = now
            self.last_alert_msg = alert["message"]

        return alert

    def _build_voice_reply(
        self,
        m_type: str,
        cpu_p: float,
        ram_p: float,
        disk_free: float,
        top_procs: List[Dict[str, Any]],
        alert: Optional[Dict[str, Any]],
    ) -> str:
        """Gera sintese falada concisa e de alta precisao para voz."""
        if alert:
            return f"Atenção, senhor: {alert['message']}"

        status_text = "Sistema estável" if (ram_p < 80 and cpu_p < 80) else "Carga moderada"
        heavy_proc = f" Principal carga: {top_procs[0]['name']}." if (top_procs and ram_p > 75) else ""
        return f"Memória RAM em {ram_p}%, CPU operando em {cpu_p}%. {status_text}.{heavy_proc}"
