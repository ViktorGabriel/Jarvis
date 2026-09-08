import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class TestAndLintRunner:
    @staticmethod
    def auto_detect_test_command(cwd: Path) -> str:
        """Detecta automaticamente o comando de teste apropriado inspecionando o workspace."""
        # 1. Verifica Node.js / package.json
        pkg_json = cwd / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                if "scripts" in data and "test" in data["scripts"]:
                    return "npm test"
            except Exception:
                pass

        # 2. Verifica Python / pytest
        venv_pytest = cwd / "venv" / "Scripts" / "pytest.exe"
        if venv_pytest.exists():
            return r".\venv\Scripts\pytest -q"
        if (cwd / "pytest.ini").exists() or (cwd / "tests").exists():
            return "pytest -q"

        return "pytest -q"

    @staticmethod
    def sanitize_command(cmd: str) -> str:
        """Sanitiza o comando para evitar injeções maliciosas básicas."""
        clean = cmd.strip()
        # Remove caracteres nulos e sequências perigosas
        clean = clean.replace("\x00", "").replace("\r", "")
        return clean

    @staticmethod
    async def run_command_async(cmd: str, cwd: Path, timeout: int = 30) -> Dict[str, Any]:
        """Executa um comando no terminal com timeout e sanitização direcionado ao cwd do workspace."""
        clean_cmd = TestAndLintRunner.sanitize_command(cmd)
        try:
            process = await asyncio.create_subprocess_shell(
                clean_cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Timeout configurável (padrão 30s)
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=float(timeout))
            return {
                "command": clean_cmd,
                "exit_code": process.returncode,
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except asyncio.TimeoutError:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
                else:
                    process.kill()
            except Exception:
                pass
            return {
                "command": clean_cmd,
                "exit_code": -1,
                "success": False,
                "stdout": "",
                "stderr": f"Comando excedeu o tempo limite de {timeout} segundos."
            }
        except Exception as e:
            return {
                "command": clean_cmd,
                "exit_code": -1,
                "success": False,
                "stdout": "",
                "stderr": str(e)
            }

    @staticmethod
    async def run_tests_with_summary(cmd: Optional[str] = None, cwd: Optional[Path] = None, timeout: int = 30) -> Dict[str, Any]:
        """Executa a suite de testes e gera um resumo executivo em 1-2 frases para voz."""
        active_cwd = cwd or Path.cwd()
        actual_cmd = cmd or TestAndLintRunner.auto_detect_test_command(active_cwd)

        res = await TestAndLintRunner.run_command_async(actual_cmd, cwd=active_cwd, timeout=timeout)
        output = (res["stdout"] + "\n" + res["stderr"]).strip()

        # Extração semântica de resultados (pytest / jest / vitest / mocha)
        passed_count = 0
        failed_count = 0

        # Padrão pytest (ex: "14 passed in 3.12s", "1 failed, 13 passed")
        pass_match = re.search(r"(\d+)\s+passed", output, re.IGNORECASE)
        fail_match = re.search(r"(\d+)\s+failed", output, re.IGNORECASE)

        if pass_match:
            passed_count = int(pass_match.group(1))
        if fail_match:
            failed_count = int(fail_match.group(1))

        if res["success"]:
            if passed_count > 0:
                reply = f"Suíte de testes executada com sucesso. {passed_count} teste{'s' if passed_count > 1 else ''} passaram."
            else:
                reply = "Suíte de testes executada com sucesso. Todos os testes passaram, senhor."
        else:
            if failed_count > 0:
                reply = f"Atenção, senhor: {failed_count} teste{'s' if failed_count > 1 else ''} falharam na suíte."
            elif "timeout" in res["stderr"].lower():
                reply = f"A execução dos testes foi interrompida após exceder o limite de {timeout} segundos."
            else:
                first_err = res["stderr"].strip().splitlines()[-1] if res["stderr"].strip() else "Verifique o log de saída no terminal."
                reply = f"Falha na execução dos testes: {first_err[:120]}"

        return {
            "success": res["success"],
            "command": actual_cmd,
            "passed": passed_count,
            "failed": failed_count,
            "output": output[:3000],  # Trunca para proteger tokens
            "reply": reply
        }

    @staticmethod
    async def check_docker_status() -> Dict[str, Any]:
        """Verifica o status dos containers Docker locais."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "docker ps --format \"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\"",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {
                    "running": True,
                    "containers": stdout.decode("utf-8", errors="replace").strip()
                }
            return {"running": False, "error": stderr.decode("utf-8", errors="replace").strip()}
        except Exception as e:
            return {"running": False, "error": str(e)}
