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
                encoding="utf-8",
                errors="replace",
                check=False
            )
            stdout = res.stdout if res.stdout is not None else ""
            stderr = res.stderr if res.stderr is not None else ""
            return res.returncode, stdout, stderr
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

    def get_diff(self, staged: bool = False, max_length: int = 4000) -> str:
        args = ["diff", "--staged"] if staged else ["diff"]
        _, out, _ = self._run_git(*args)
        out = out or ""
        if len(out) > max_length:
            return out[:max_length] + f"\n\n[... diff truncado em {max_length} caracteres para proteger contexto ...]"
        return out

    def get_recent_commits(self, limit: int = 5) -> str:
        """Retorna os últimos commits no formato resumido oneline."""
        code, out, _ = self._run_git("log", f"-n {max(1, min(20, limit))}", "--oneline")
        return out.strip() if code == 0 else "Não foi possível recuperar o histórico de commits."

    def inspect(self, mode: str = "status") -> Dict[str, Any]:
        """Inspeciona o estado do Git com base no modo ('status', 'diff', 'recent_commits')."""
        mode_clean = (mode or "status").lower().strip()

        if mode_clean == "diff":
            diff_text = self.get_diff()
            if not diff_text.strip():
                return {"mode": "diff", "output": "Nenhuma alteração detectada no momento.", "reply": "Nenhuma modificação não comitada no momento, senhor."}
            return {
                "mode": "diff",
                "output": diff_text,
                "reply": "Aqui está o diff das alterações recentes no workspace, senhor."
            }

        elif mode_clean == "recent_commits":
            log_text = self.get_recent_commits(5)
            return {
                "mode": "recent_commits",
                "output": log_text,
                "reply": f"Últimos commits no repositório:\n{log_text}"
            }

        else:  # status
            status_data = self.get_status()
            if not status_data.get("is_git_repo"):
                return {"mode": "status", "output": "O diretório atual não é um repositório Git.", "reply": "O workspace atual não é um repositório Git, senhor."}

            changes = status_data.get("raw_status", [])
            count = len(changes)
            if count == 0:
                return {"mode": "status", "output": "Working tree limpa.", "reply": "Nenhuma alteração pendente no repositório. Working tree limpa."}

            summary_files = ", ".join(line.split()[-1] for line in changes[:4])
            if count > 4:
                summary_files += f" e mais {count - 4} arquivos"

            reply = f"{count} arquivo{'s' if count > 1 else ''} alterado{'s' if count > 1 else ''}: {summary_files}. Deseja que eu prepare o commit?"
            return {
                "mode": "status",
                "changes_count": count,
                "files": changes,
                "output": "\n".join(changes),
                "reply": reply
            }

    def generate_conventional_commit_message(self, diff_text: str) -> str:
        """Gera mensagem padronizada no formato Conventional Commits com base no diff."""
        if not diff_text.strip():
            return "chore(workspace): synchronize workspace files"

        diff_lower = diff_text.lower()
        if "test" in diff_lower:
            return "test(core): update and add unit tests"
        elif "fix" in diff_lower or "bug" in diff_lower or "error" in diff_lower:
            return "fix(core): correct identified bug and stabilize behavior"
        elif "doc" in diff_lower or "readme" in diff_lower:
            return "docs(readme): update project documentation"
        elif "refactor" in diff_lower:
            return "refactor(system): streamline code structure"
        else:
            return "feat(workspace): implement new capabilities and improvements"

    async def commit(self, message: Optional[str] = None, stage_all: bool = True, require_approval: bool = True) -> Dict[str, Any]:
        """Executa git commit semântico com aprovação prévia opcional no HUD."""
        diff_text = self.get_diff()
        final_message = message or self.generate_conventional_commit_message(diff_text)

        # Se requer aprovação, passa pelo SafetyInterceptor antes de efetivar
        if require_approval:
            cmd_preview = f"git commit -m \"{final_message}\""
            allowed = await self.interceptor.guard_command(
                cmd_preview,
                description=f"Commit semântico: '{final_message}' ({'stage all' if stage_all else 'staged only'})"
            )
            if not allowed:
                return {
                    "success": False,
                    "error": "Commit cancelado pelo usuário no HUD.",
                    "reply": "Operação de commit cancelada pelo usuário, senhor."
                }

        if stage_all:
            self._run_git("add", "-A")

        code, out, err = self._run_git("commit", "-m", final_message)
        if code == 0:
            return {
                "success": True,
                "message": final_message,
                "output": out,
                "reply": f"Commit realizado com sucesso: '{final_message}'."
            }
        else:
            return {
                "success": False,
                "error": err or out,
                "reply": f"Não foi possível concluir o commit: {err or out}"
            }

    async def push(self, remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
        cmd_str = f"git push {remote} {branch or ''}".strip()
        # TRAVAMENTO PREVENTIVO: Requer aprovação explícita no HUD!
        allowed = await self.interceptor.guard_command(
            cmd_str,
            description="Publicação de código no repositório remoto (git push)"
        )
        if not allowed:
            return {
                "success": False,
                "error": "Operação de git push cancelada pelo usuário.",
                "reply": "Envio remoto cancelado por ordem do senhor."
            }

        args = ["push", remote]
        if branch:
            args.append(branch)

        code, out, err = self._run_git(*args)
        if code == 0:
            return {
                "success": True,
                "output": out,
                "reply": f"Código enviado com sucesso para {remote}{'/' + branch if branch else ''}, senhor."
            }
        else:
            return {
                "success": False,
                "error": err or out,
                "reply": f"Falha ao enviar código para o repositório remoto: {err or out}"
            }
