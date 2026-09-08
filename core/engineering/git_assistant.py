import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from core.governance.interceptor import SafetyInterceptor

class GitAssistant:
    def __init__(self, workspace_root: Path, interceptor: SafetyInterceptor):
        self.workspace_root = workspace_root
        self.interceptor = interceptor

    def _run_git(self, *args: str) -> Tuple[int, str, str]:
        try:
            res = subprocess.run(
                ["git", *args],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                check=False
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            return -1, "", str(e)

    def get_status(self) -> Dict[str, Any]:
        code, out, _ = self._run_git("status", "--porcelain")
        if code != 0:
            return {"is_git_repo": False, "changes": []}

        changes = [line.strip() for line in out.splitlines() if line.strip()]
        return {
            "is_git_repo": True,
            "has_changes": len(changes) > 0,
            "changes_count": len(changes),
            "raw_status": changes
        }

    def get_diff(self, staged: bool = False) -> str:
        args = ["diff", "--staged"] if staged else ["diff"]
        _, out, _ = self._run_git(*args)
        return out

    def generate_conventional_commit_message(self, diff_text: str) -> str:
        """Gera mensagem padronizada no formato Conventional Commits com base no diff."""
        if not diff_text.strip():
            return "chore: update files"

        diff_lower = diff_text.lower()
        if "test" in diff_lower:
            prefix = "test"
        elif "fix" in diff_lower or "bug" in diff_lower or "error" in diff_lower:
            prefix = "fix"
        elif "doc" in diff_lower or "readme" in diff_lower:
            prefix = "docs"
        elif "refactor" in diff_lower:
            prefix = "refactor"
        else:
            prefix = "feat"

        return f"{prefix}: synchronize modifications and workspace improvements"

    async def commit(self, message: str, stage_all: bool = True) -> Dict[str, Any]:
        if stage_all:
            self._run_git("add", "-A")

        code, out, err = self._run_git("commit", "-m", message)
        return {
            "success": code == 0,
            "output": out if code == 0 else err,
            "message": message
        }

    async def push(self, remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
        cmd_str = f"git push {remote} {branch or ''}".strip()
        # TRAVAMENTO PREVENTIVO: Requer aprovação explícita no HUD!
        allowed = await self.interceptor.guard_command(
            cmd_str,
            description="Publicação de código no repositório remoto (git push)"
        )
        if not allowed:
            return {"success": False, "error": "Operação de git push cancelada pelo usuário."}

        args = ["push", remote]
        if branch:
            args.append(branch)

        code, out, err = self._run_git(*args)
        return {
            "success": code == 0,
            "output": out if code == 0 else err
        }
