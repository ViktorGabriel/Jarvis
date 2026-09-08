import asyncio
import json
import logging
import re
import socket
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from core.governance.interceptor import SafetyInterceptor

logger = logging.getLogger("DockerManager")


class DockerManager:
    """Gerenciador de infraestrutura local, containers Docker e health checks de servicos."""

    DEFAULT_PORTS = {
        "postgres": 5432,
        "postgresql": 5432,
        "redis": 6379,
        "api": 3000,
        "backend": 3000,
        "custom": 8080,
    }

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        interceptor: Optional[SafetyInterceptor] = None,
    ):
        self.workspace_root = workspace_root or Path.cwd()
        self.interceptor = interceptor

    def _run_cmd(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 15,
    ) -> Tuple[int, str, str]:
        """Executa comando de terminal de forma segura e com suporte a UTF-8 no Windows."""
        run_cwd = cwd or self.workspace_root
        try:
            res = subprocess.run(
                cmd,
                cwd=str(run_cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            stdout = res.stdout if res.stdout is not None else ""
            stderr = res.stderr if res.stderr is not None else ""
            return res.returncode, stdout, stderr
        except FileNotFoundError:
            return -1, "", f"Comando '{cmd[0]}' nao encontrado no PATH do sistema operacional."
        except subprocess.TimeoutExpired:
            return -1, "", f"Comando '{' '.join(cmd)}' excedeu o tempo limite de {timeout}s."
        except Exception as e:
            return -1, "", str(e)

    def is_docker_running(self) -> Tuple[bool, str]:
        """Verifica preliminarmente se o daemon do Docker esta ativo."""
        code, out, err = self._run_cmd(["docker", "info"], timeout=5)
        if code == 0:
            return True, "Docker daemon esta ativo e respondendo."

        err_lower = (err + out).lower()
        if "not found" in err_lower or "nao encontrado" in err_lower:
            return False, "O Docker CLI nao esta instalado ou nao foi encontrado nas variaveis de ambiente."
        return False, "O Docker Desktop/daemon nao esta em execucao no sistema."

    def inspect_services(self, all_containers: bool = False) -> Dict[str, Any]:
        """Inspeciona containers ativos ou todos os containers do sistema."""
        is_running, status_msg = self.is_docker_running()
        if not is_running:
            return {
                "success": False,
                "is_docker_running": False,
                "containers": [],
                "containers_count": 0,
                "reply": f"O Docker esta desligado no momento, senhor. {status_msg}",
            }

        cmd = ["docker", "ps", "--format", "{{json .}}"]
        if all_containers:
            cmd.append("-a")

        code, out, err = self._run_cmd(cmd, timeout=10)
        if code != 0:
            return {
                "success": False,
                "is_docker_running": True,
                "containers": [],
                "containers_count": 0,
                "error": err,
                "reply": f"Nao foi possivel inspecionar os containers: {err.strip()[:100]}",
            }

        containers = []
        for line in out.strip().splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                containers.append({
                    "id": data.get("ID", ""),
                    "name": data.get("Names", ""),
                    "image": data.get("Image", ""),
                    "status": data.get("Status", ""),
                    "state": data.get("State", ""),
                    "ports": data.get("Ports", ""),
                })
            except Exception:
                containers.append({"raw": line_str})

        count = len(containers)
        if count == 0:
            mode_desc = "no sistema" if all_containers else "em execucao"
            reply = f"Nenhum container encontrado {mode_desc}, senhor."
        else:
            names = [c.get("name", "container") for c in containers[:3]]
            names_summary = ", ".join(names)
            more = f" e mais {count - 3}" if count > 3 else ""
            reply = f"{count} container{'s' if count != 1 else ''} encontrado{'s' if count != 1 else ''} ({names_summary}{more}), senhor."

        return {
            "success": True,
            "is_docker_running": True,
            "containers": containers,
            "containers_count": count,
            "reply": reply,
        }

    def manage_service(
        self,
        action: str,
        target: Optional[str] = None,
        compose_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inicia, para ou reinicia containers Docker ou servicos do docker-compose."""
        act_clean = (action or "start").lower().strip()
        if act_clean not in ["start", "stop", "restart"]:
            return {
                "success": False,
                "error": f"Acao '{action}' invalida. Use start, stop ou restart.",
                "reply": f"Acao '{action}' nao suportada. Posso iniciar, parar ou reiniciar servicos.",
            }

        is_running, status_msg = self.is_docker_running()
        if not is_running:
            return {
                "success": False,
                "is_docker_running": False,
                "reply": f"Nao foi possivel executar '{act_clean}'. {status_msg}",
            }

        target_clean = (target or "").strip()
        cmd = []

        if compose_file:
            comp_path = Path(compose_file)
            if not comp_path.is_absolute():
                comp_path = self.workspace_root / comp_path

            if not comp_path.exists():
                return {
                    "success": False,
                    "error": f"Arquivo compose '{compose_file}' nao encontrado.",
                    "reply": f"Arquivo docker-compose '{compose_file}' nao foi localizado no workspace, senhor.",
                }

            if act_clean == "start":
                cmd = ["docker", "compose", "-f", str(comp_path), "up", "-d"]
            else:
                cmd = ["docker", "compose", "-f", str(comp_path), act_clean]

            if target_clean and target_clean.lower() != "all":
                cmd.append(target_clean)

        elif target_clean and target_clean.lower() != "all":
            cmd = ["docker", act_clean, target_clean]

        else:
            default_compose = self._find_default_compose_file()
            if default_compose:
                if act_clean == "start":
                    cmd = ["docker", "compose", "-f", str(default_compose), "up", "-d"]
                else:
                    cmd = ["docker", "compose", "-f", str(default_compose), act_clean]
            elif target_clean.lower() == "all" and act_clean in ["stop", "restart"]:
                code, out, _ = self._run_cmd(["docker", "ps", "-q"])
                ids = [i.strip() for i in out.splitlines() if i.strip()]
                if not ids:
                    return {
                        "success": True,
                        "reply": "Nenhum container em execucao para parar, senhor.",
                    }
                cmd = ["docker", act_clean, *ids]
            else:
                return {
                    "success": False,
                    "error": "Nenhum container alvo informado e nenhum docker-compose.yml encontrado no workspace.",
                    "reply": "Por favor, especifique o container ou compose para gerenciar, senhor.",
                }

        logger.info(f"Executando comando Docker: {' '.join(cmd)}")
        code, out, err = self._run_cmd(cmd, timeout=30)
        if code == 0:
            target_desc = f"'{target_clean}'" if target_clean and target_clean.lower() != "all" else "do projeto"
            action_pt = {"start": "inicializados", "stop": "finalizados", "restart": "reiniciados"}.get(act_clean, act_clean)
            reply = f"Servicos {target_desc} {action_pt} com sucesso, senhor."
            return {
                "success": True,
                "action": act_clean,
                "target": target_clean,
                "command": " ".join(cmd),
                "output": out,
                "reply": reply,
            }
        else:
            err_msg = err or out
            if "port is already allocated" in err_msg.lower() or "address already in use" in err_msg.lower():
                port_match = re.search(r"bind:.*?(\d+)", err_msg)
                port_info = f" na porta {port_match.group(1)}" if port_match else ""
                reply = f"Erro ao iniciar servico: conflito de porta{port_info}. Ja existe outro processo em uso."
            else:
                reply = f"Falha ao executar '{act_clean}': {err_msg.strip()[:120]}"

            return {
                "success": False,
                "action": act_clean,
                "target": target_clean,
                "command": " ".join(cmd),
                "error": err_msg,
                "reply": reply,
            }

    async def destructive_operation(
        self,
        action: str,
        target: Optional[str] = None,
        compose_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executa operacoes com perda de estado (down com volumes, prune, rm) sob trava de seguranca."""
        act_clean = (action or "").lower().strip()

        if act_clean == "down_volumes":
            comp_path = Path(compose_file) if compose_file else self._find_default_compose_file()
            if comp_path and comp_path.exists():
                cmd = ["docker", "compose", "-f", str(comp_path), "down", "-v"]
            else:
                cmd = ["docker", "compose", "down", "-v"]
            risk_desc = (
                "Atencao: isto encerrara os containers e apagara todos os volumes de dados locais do projeto."
            )

        elif act_clean == "prune_system":
            cmd = ["docker", "system", "prune", "-f"]
            risk_desc = (
                "Atencao: isto removera todos os containers inativos, redes nao utilizadas e dados temporarios do Docker."
            )

        elif act_clean == "remove_container":
            if not target or not target.strip():
                return {
                    "success": False,
                    "error": "Nome do container alvo e obrigatorio para remocao.",
                    "reply": "Por favor, especifique o container que deseja remover, senhor.",
                }
            cmd = ["docker", "rm", "-f", target.strip()]
            risk_desc = (
                f"Atencao: isto forcara a exclusao definitiva do container '{target.strip()}'. Confirmar operacao?"
            )

        else:
            return {
                "success": False,
                "error": f"Acao destrutiva '{action}' desconhecida. Use down_volumes, prune_system ou remove_container.",
                "reply": f"Acao destrutiva '{action}' invalida, senhor.",
            }

        cmd_str = " ".join(cmd)

        if self.interceptor:
            logger.warning(f"Operacao destrutiva solicitada: {cmd_str}. Solicitando aprovacao preventiva no HUD...")
            approved = await self.interceptor.guard_command(
                command=cmd_str,
                description=risk_desc,
            )
            if not approved:
                return {
                    "success": False,
                    "approved": False,
                    "command": cmd_str,
                    "reply": "Operacao cancelada pelo usuario no HUD, senhor. Nenhum container ou volume foi alterado.",
                }
        else:
            logger.error("Tentativa de operacao destrutiva sem SafetyInterceptor configurado!")
            return {
                "success": False,
                "approved": False,
                "error": "SafetyInterceptor nao configurado. Operacao destrutiva abortada por seguranca.",
                "reply": "Operacao abortada: modulo de governanca e aprovacao indisponivel, senhor.",
            }

        logger.info(f"Operacao autorizada pelo usuario. Executando: {cmd_str}")
        code, out, err = self._run_cmd(cmd, timeout=30)
        if code == 0:
            return {
                "success": True,
                "approved": True,
                "action": act_clean,
                "command": cmd_str,
                "output": out,
                "reply": "Operacao de infraestrutura concluida com sucesso apos sua autorizacao, senhor.",
            }
        else:
            return {
                "success": False,
                "approved": True,
                "action": act_clean,
                "command": cmd_str,
                "error": err,
                "reply": f"Erro durante a execucao da limpeza autorizada: {err.strip()[:100]}",
            }

    def check_health(
        self,
        target: str = "postgres",
        port: Optional[int] = None,
        endpoint: Optional[str] = None,
        host: str = "localhost",
    ) -> Dict[str, Any]:
        """Realiza verificacao de integridade (health check) via socket TCP ou requisicao HTTP."""
        target_clean = (target or "postgres").lower().strip()
        actual_port = port or self.DEFAULT_PORTS.get(target_clean, 8080)

        if endpoint:
            url = endpoint if endpoint.startswith("http") else f"http://{host}:{actual_port}{endpoint}"
            return self._check_http_health(url, target_name=target_clean)

        return self._check_tcp_port(host, actual_port, target_name=target_clean)

    def _check_tcp_port(self, host: str, port: int, target_name: str) -> Dict[str, Any]:
        """Verifica se a porta TCP esta aberta e medindo a latencia de conexao."""
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=2.0):
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                reply = f"Servico '{target_name}' esta ativo na porta {port} (latencia: {latency_ms}ms)."
                return {
                    "success": True,
                    "target": target_name,
                    "type": "tcp",
                    "host": host,
                    "port": port,
                    "reachable": True,
                    "latency_ms": latency_ms,
                    "status": "healthy",
                    "reply": reply,
                }
        except ConnectionRefusedError:
            return {
                "success": True,
                "target": target_name,
                "type": "tcp",
                "host": host,
                "port": port,
                "reachable": False,
                "status": "closed",
                "reply": f"Nenhum servico respondendo na porta {port} ({target_name}). O container pode estar inativo.",
            }
        except socket.timeout:
            return {
                "success": True,
                "target": target_name,
                "type": "tcp",
                "host": host,
                "port": port,
                "reachable": False,
                "status": "timeout",
                "reply": f"Tempo esgotado ao tentar conectar a porta {port} ({target_name}).",
            }
        except Exception as e:
            return {
                "success": False,
                "target": target_name,
                "type": "tcp",
                "host": host,
                "port": port,
                "reachable": False,
                "error": str(e),
                "reply": f"Erro de conectividade ao testar {target_name} na porta {port}: {e}",
            }

    def _check_http_health(self, url: str, target_name: str) -> Dict[str, Any]:
        """Executa ping HTTP GET em endpoint de health check."""
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "JARVIS-HealthCheck/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                code = resp.status
                is_ok = 200 <= code < 400
                status_word = "ativo" if is_ok else "com falha"
                reply = f"API {target_name} esta {status_word} ({code}) com latencia de {latency_ms}ms."
                return {
                    "success": True,
                    "target": target_name,
                    "type": "http",
                    "url": url,
                    "status_code": code,
                    "healthy": is_ok,
                    "latency_ms": latency_ms,
                    "reply": reply,
                }
        except urllib.error.HTTPError as he:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "success": True,
                "target": target_name,
                "type": "http",
                "url": url,
                "status_code": he.code,
                "healthy": False,
                "latency_ms": latency_ms,
                "reply": f"Endpoint {target_name} retornou status HTTP {he.code}.",
            }
        except Exception as e:
            return {
                "success": False,
                "target": target_name,
                "type": "http",
                "url": url,
                "healthy": False,
                "error": str(e),
                "reply": f"Nao foi possivel alcancar o endpoint HTTP {url}: {e}",
            }

    def _find_default_compose_file(self) -> Optional[Path]:
        """Procura por arquivo docker-compose padrao no workspace."""
        candidates = [
            self.workspace_root / "docker-compose.yml",
            self.workspace_root / "docker-compose.yaml",
            self.workspace_root / "compose.yml",
            self.workspace_root / "compose.yaml",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None
