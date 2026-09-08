import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

class TestAndLintRunner:
    @staticmethod
    async def run_command_async(cmd: str, cwd: Path) -> Dict[str, Any]:
        """Executa um comando de linter ou teste de forma não bloqueante."""
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return {
                "command": cmd,
                "exit_code": process.returncode,
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            return {
                "command": cmd,
                "exit_code": -1,
                "success": False,
                "stdout": "",
                "stderr": str(e)
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
