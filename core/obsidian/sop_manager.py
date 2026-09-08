import asyncio
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from core.governance.interceptor import SafetyInterceptor
from core.governance.policy import GovernancePolicy, RiskLevel
from core.obsidian.vault_manager import ObsidianVaultManager

logger = logging.getLogger("SOPManager")


@dataclass
class SOPStep:
    step_number: int
    title: str
    description: str
    commands: List[str] = field(default_factory=list)
    requires_approval: bool = False
    risk_reasons: List[str] = field(default_factory=list)
    ignore_errors: bool = False


@dataclass
class SOPDefinition:
    id: str
    title: str
    description: str
    category: str
    triggers: List[str]
    tags: List[str]
    sop_type: str  # 'SOP' ou 'Workflow'
    file_path: Path
    relative_path: str
    steps: List[SOPStep] = field(default_factory=list)
    raw_content: str = ""


class SOPParser:
    """Parser de Markdown e YAML Frontmatter para SOPs e Workflows do Obsidian."""

    @staticmethod
    def parse_yaml_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
        """Extrai o frontmatter YAML e o corpo Markdown sem dependencias externas."""
        meta: Dict[str, Any] = {}
        body = content

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not fm_match:
            return meta, body

        raw_yaml = fm_match.group(1)
        body = fm_match.group(2)

        current_key: Optional[str] = None
        for line in raw_yaml.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            # Lista multi-linha (- item)
            if line_str.startswith("- ") and current_key:
                val = line_str[2:].strip().strip("\"'")
                if isinstance(meta.get(current_key), list):
                    meta[current_key].append(val)
                else:
                    meta[current_key] = [val]
                continue

            kv_match = re.match(r"^([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line_str)
            if kv_match:
                key = kv_match.group(1).strip()
                val = kv_match.group(2).strip()
                current_key = key

                # Lista inline [a, b]
                if val.startswith("[") and val.endswith("]"):
                    items = [i.strip().strip("\"'") for i in val[1:-1].split(",") if i.strip()]
                    meta[key] = items
                elif val == "":
                    meta[key] = []
                else:
                    meta[key] = val.strip("\"'")

        return meta, body

    @classmethod
    def parse_sop(cls, file_path: Path, vault_root: Path) -> Optional[SOPDefinition]:
        """Faz o parsing completo de um arquivo Markdown de SOP ou Workflow."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Erro ao ler arquivo SOP {file_path}: {e}")
            return None

        meta, body = cls.parse_yaml_frontmatter(content)
        stem = file_path.stem
        is_workflow = "workflow" in file_path.as_posix().lower()

        title = meta.get("title") or stem.replace("-", " ").replace("_", " ").title()
        description = meta.get("description") or ""
        category = meta.get("category") or ("workflow" if is_workflow else "general")
        triggers = meta.get("triggers") or []
        if isinstance(triggers, str):
            triggers = [triggers]
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        steps = cls._parse_steps(body)
        rel_path = file_path.relative_to(vault_root).as_posix()

        return SOPDefinition(
            id=stem,
            title=title,
            description=description,
            category=category,
            triggers=triggers,
            tags=tags,
            sop_type="Workflow" if is_workflow else "SOP",
            file_path=file_path,
            relative_path=rel_path,
            steps=steps,
            raw_content=content,
        )

    @classmethod
    def _parse_steps(cls, body: str) -> List[SOPStep]:
        """Extrai passos estruturados e blocos de comandos de shell do Markdown."""
        steps: List[SOPStep] = []

        # Divide por cabeçalhos de passo (## Passo X: ..., ### Etapa X: ...)
        sections = re.split(r"\n(?=#{2,4}\s+(?:Passo|Etapa|Step|\d+\.))", "\n" + body, flags=re.IGNORECASE)

        # Se não houver seções com cabeçalho de passo, tenta dividir por cabeçalhos gerais de nível 2 ou 3
        if len(sections) <= 1:
            sections = re.split(r"\n(?=#{2,3}\s+)", "\n" + body)

        step_idx = 1
        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            lines = sec_clean.splitlines()
            header_line = lines[0] if lines else ""

            # Extrai título do passo
            title_match = re.match(r"^#{1,4}\s+(?:(?:Passo|Etapa|Step)\s*\d*[:.-]?\s*)?(.*)$", header_line, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else f"Passo {step_idx}"
            if not title:
                title = f"Passo {step_idx}"

            # Ignora seções introdutórias como Título Principal do documento
            if header_line.startswith("# ") and step_idx == 1 and len(sections) > 1:
                continue

            # Extrai blocos de código executáveis (bash, sh, powershell, cmd)
            commands = []
            code_blocks = re.findall(r"```(?:bash|sh|powershell|cmd|zsh)?\s*\n(.*?)\n```", sec_clean, re.DOTALL)
            for block in code_blocks:
                for cmd_line in block.splitlines():
                    cmd_line_strip = cmd_line.strip()
                    if cmd_line_strip and not cmd_line_strip.startswith("#"):
                        commands.append(cmd_line_strip)

            # Extrai comandos inline em crases caso não haja blocos de código
            if not commands:
                inline_cmds = re.findall(r"`([^`]+)`", sec_clean)
                for inc in inline_cmds:
                    inc_strip = inc.strip()
                    # Identifica se parece um comando executável comum
                    if re.match(r"^(?:git|docker|npm|pytest|python|curl|pip|node|pnpm)\b", inc_strip):
                        commands.append(inc_strip)

            # Remove blocos de código para extrair a descrição limpa
            desc_text = re.sub(r"```.*?```", "", sec_clean, flags=re.DOTALL)
            desc_lines = [l.strip() for l in desc_text.splitlines()[1:] if l.strip() and not l.strip().startswith("#")]
            description = " ".join(desc_lines) if desc_lines else "Sem descrição."

            # Avalia se algum comando necessita de aprovação preventiva
            requires_approval = False
            risk_reasons = []
            for cmd in commands:
                risk, reason = GovernancePolicy.evaluate_command(cmd)
                if risk == RiskLevel.CRITICAL:
                    requires_approval = True
                    risk_reasons.append(reason)

            ignore_errors = "[opcional]" in sec_clean.lower() or "ignore_errors" in sec_clean.lower()

            if commands or description:
                steps.append(SOPStep(
                    step_number=step_idx,
                    title=title,
                    description=description,
                    commands=commands,
                    requires_approval=requires_approval,
                    risk_reasons=risk_reasons,
                    ignore_errors=ignore_errors,
                ))
                step_idx += 1

        return steps


class SOPAuditLogger:
    """Gerenciador de auditoria e telemetria para execuções de SOPs em Machine/Logs/."""

    def __init__(self, vault: ObsidianVaultManager):
        self.vault = vault

    def record_run(
        self,
        sop: SOPDefinition,
        status: str,  # SUCCESS, FAILED, PARTIALLY_EXECUTED, DRY_RUN
        duration_s: float,
        step_results: List[Dict[str, Any]],
        summary_error: Optional[str] = None,
    ) -> Path:
        """Gera ou anexa o registro da execução no arquivo diário de logs do cofre."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        rel_path = f"Machine/Logs/{date_str}-sop-runs.md"
        full_path = self.vault.vault_path / rel_path

        # Cria cabeçalho diário caso o arquivo ainda não exista
        if not full_path.exists():
            header = f"""---
date: {date_str}
type: sop-audit-log
tags: [audit/sop, machine/logs]
---

# 📋 Registro de Auditoria de SOPs e Workflows: {date_str}

*(Registro cronológico de rotinas, passos executados e validações de governança)*

"""
            self.vault.write_note(rel_path, header)

        # Formata detalhes de cada passo
        steps_md = []
        for res in step_results:
            step_num = res.get("step_number", 1)
            step_title = res.get("title", f"Passo {step_num}")
            st = res.get("status", "SUCCESS")
            dur = res.get("duration_s", 0.0)
            icon = "✅" if st == "SUCCESS" else ("⚠️" if st == "SKIPPED" else "❌")

            entry = f"{step_num}. **{icon} Passo {step_num}: {step_title}** — `{st}` (`{dur:.2f}s`)"
            if res.get("commands"):
                entry += f"\n   - **Comandos**: `{'; '.join(res['commands'])}`"
            if res.get("output"):
                clean_out = res["output"].strip()[:400].replace("\n", "\n     ")
                entry += f"\n   - **Saída**: `{clean_out}`"
            if res.get("error"):
                clean_err = res["error"].strip()[:400].replace("\n", "\n     ")
                entry += f"\n   - **Erro**: `{clean_err}`"
            if res.get("approved") is not None:
                auth_str = "Autorizado pelo usuário no HUD" if res["approved"] else "Rejeitado pelo usuário"
                entry += f"\n   - **Governança**: `{auth_str}`"
            steps_md.append(entry)

        steps_str = "\n".join(steps_md) if steps_md else "- Nenhum passo registrado."
        status_icon = "🟢" if status == "SUCCESS" else ("🟡" if status == "DRY_RUN" else "🔴")

        log_block = f"""
## {status_icon} [{time_str}] Execução: {sop.title} (`{sop.id}`)
- **Tipo**: `{sop.sop_type}`
- **Categoria**: `{sop.category}`
- **Status Final**: `{status}`
- **Duração Total**: `{duration_s:.2f}s`
- **Passos Executados**: {len(step_results)} de {len(sop.steps)}
{f"- **Motivo da Falha**: `{summary_error}`" if summary_error else ""}

### 📑 Detalhes das Etapas:
{steps_str}

---
"""
        return self.vault.write_note(rel_path, log_block, append=True)


class SOPManager:
    """Orquestrador de leitura, validação e execução sequencial de SOPs e Workflows."""

    def __init__(
        self,
        vault: ObsidianVaultManager,
        interceptor: Optional[SafetyInterceptor] = None,
        workspace_root: Optional[Path] = None,
    ):
        self.vault = vault
        self.interceptor = interceptor
        self.workspace_root = workspace_root or Path.cwd()
        self.audit_logger = SOPAuditLogger(vault)

    def _get_sop_directories(self) -> List[Path]:
        """Retorna os caminhos dos diretórios de SOPs e Workflows do cofre."""
        return [
            self.vault.vault_path / "Machine" / "SOPs",
            self.vault.vault_path / "Machine" / "Workflows",
        ]

    def list_sops(self, category: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
        """Varre as pastas de SOPs e Workflows e retorna a lista de procedimentos disponíveis."""
        sops: List[SOPDefinition] = []
        for dir_path in self._get_sop_directories():
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                sop = SOPParser.parse_sop(f, self.vault.vault_path)
                if sop:
                    sops.append(sop)

        # Filtra por categoria
        if category:
            cat_clean = category.lower().strip()
            sops = [s for s in sops if cat_clean in s.category.lower()]

        # Filtra por query
        if query:
            q_clean = query.lower().strip()
            sops = [
                s for s in sops
                if q_clean in s.title.lower()
                or q_clean in s.description.lower()
                or q_clean in s.id.lower()
                or any(q_clean in t.lower() for t in s.triggers)
                or any(q_clean in tg.lower() for tg in s.tags)
            ]

        summary_list = []
        for s in sops:
            summary_list.append({
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "type": s.sop_type,
                "category": s.category,
                "steps_count": len(s.steps),
                "triggers": s.triggers,
                "file": s.relative_path,
            })

        count = len(summary_list)
        if count == 0:
            reply = "Nenhum procedimento operacional ou workflow encontrado no cofre no momento, senhor."
        else:
            names = [s["title"] for s in summary_list[:3]]
            names_str = ", ".join(names)
            more = f" e mais {count - 3}" if count > 3 else ""
            reply = f"Encontrei {count} procedimento{'s' if count != 1 else ''} disponível{'is' if count != 1 else ''}: {names_str}{more}."

        return {
            "success": True,
            "total": count,
            "sops": summary_list,
            "reply": reply,
        }

    def get_sop(self, sop_name: str) -> Optional[SOPDefinition]:
        """Localiza um SOP por nome, slug ou aproximação de título."""
        target_slug = sop_name.lower().strip().replace(".md", "").replace(" ", "-")

        for dir_path in self._get_sop_directories():
            if not dir_path.exists():
                continue

            # Tentativa 1: Arquivo direto
            direct_file = dir_path / f"{target_slug}.md"
            if direct_file.exists():
                return SOPParser.parse_sop(direct_file, self.vault.vault_path)

            # Tentativa 2: Busca por stem ou título
            for f in dir_path.glob("*.md"):
                sop = SOPParser.parse_sop(f, self.vault.vault_path)
                if not sop:
                    continue
                if sop.id == target_slug or target_slug in sop.id:
                    return sop
                if target_slug in sop.title.lower().replace(" ", "-"):
                    return sop
                if any(target_slug in t.lower().replace(" ", "-") for t in sop.triggers):
                    return sop

        return None

    def _run_cmd(self, cmd: str, timeout: int = 45) -> Tuple[int, str, str]:
        """Executa comando shell no workspace ativo com proteção de timeout e UTF-8."""
        try:
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            stdout = res.stdout if res.stdout is not None else ""
            stderr = res.stderr if res.stderr is not None else ""
            return res.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Comando excedeu o tempo limite de {timeout}s."
        except Exception as e:
            return -1, "", str(e)

    async def execute_sop(self, sop_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Executa sequencialmente os passos de um SOP respeitando a governança do HUD."""
        sop = self.get_sop(sop_name)
        if not sop:
            return {
                "success": False,
                "sop_name": sop_name,
                "error": f"Procedimento '{sop_name}' não encontrado nas pastas Machine/SOPs/ ou Machine/Workflows/.",
                "reply": f"Não encontrei o procedimento '{sop_name}' no cofre, senhor. Use 'listar sops' para ver os disponíveis.",
            }

        # 1. Modo DRY-RUN (simulação)
        if dry_run:
            simulated_steps = []
            for s in sop.steps:
                simulated_steps.append({
                    "step_number": s.step_number,
                    "title": s.title,
                    "description": s.description,
                    "commands": s.commands,
                    "requires_approval": s.requires_approval,
                    "risk_reasons": s.risk_reasons,
                })

            log_file = self.audit_logger.record_run(
                sop=sop,
                status="DRY_RUN",
                duration_s=0.0,
                step_results=[{
                    "step_number": s.step_number,
                    "title": s.title,
                    "status": "SIMULATED",
                    "duration_s": 0.0,
                    "commands": s.commands,
                } for s in sop.steps],
            )

            reply = f"Simulação do procedimento '{sop.title}': {len(sop.steps)} passos validados sem execução de comandos."
            return {
                "success": True,
                "dry_run": True,
                "sop_name": sop.title,
                "steps": simulated_steps,
                "log_file": str(log_file),
                "reply": reply,
            }

        # 2. Execução REAL passo a passo
        t_start = time.perf_counter()
        step_results = []
        overall_status = "SUCCESS"
        summary_error = None

        logger.info(f"Iniciando execução do SOP: {sop.title} ({len(sop.steps)} passos)")

        for step in sop.steps:
            t_step_start = time.perf_counter()
            step_output = []
            step_error = []
            step_success = True

            # Se o passo tiver comandos a executar
            for cmd in step.commands:
                # Checa se o comando requer aprovação no HUD pelo SafetyInterceptor
                risk, reason = GovernancePolicy.evaluate_command(cmd)
                if risk == RiskLevel.CRITICAL:
                    if self.interceptor:
                        risk_prompt = f"O passo {step.step_number} ('{step.title}') requer: {reason}. Autoriza a execução?"
                        logger.warning(f"SOP solicitando autorização para: {cmd}")
                        approved = await self.interceptor.guard_command(command=cmd, description=risk_prompt)
                        if not approved:
                            duration = time.perf_counter() - t_step_start
                            step_results.append({
                                "step_number": step.step_number,
                                "title": step.title,
                                "status": "REJECTED",
                                "approved": False,
                                "duration_s": duration,
                                "commands": [cmd],
                                "error": "Operação rejeitada pelo usuário no HUD.",
                            })
                            overall_status = "PARTIALLY_EXECUTED"
                            summary_error = f"Execução cancelada pelo usuário no passo {step.step_number}."
                            break
                    else:
                        step_results.append({
                            "step_number": step.step_number,
                            "title": step.title,
                            "status": "BLOCKED",
                            "approved": False,
                            "duration_s": 0.0,
                            "commands": [cmd],
                            "error": "SafetyInterceptor não disponível para comando crítico.",
                        })
                        overall_status = "FAILED"
                        summary_error = f"Comando crítico bloqueado no passo {step.step_number}."
                        break

                # Executa o comando
                code, out, err = self._run_cmd(cmd)
                if out:
                    step_output.append(out)
                if err:
                    step_error.append(err)

                if code != 0:
                    step_success = False
                    if not step.ignore_errors:
                        duration = time.perf_counter() - t_step_start
                        step_results.append({
                            "step_number": step.step_number,
                            "title": step.title,
                            "status": "FAILED",
                            "duration_s": duration,
                            "commands": [cmd],
                            "output": "\n".join(step_output),
                            "error": err or out or f"Código de saída {code}",
                        })
                        overall_status = "FAILED"
                        summary_error = f"Falha no comando '{cmd}' com código {code}."
                        break

            # Se foi interrompido por falha ou rejeição, encerra a sequência
            if overall_status in ["FAILED", "PARTIALLY_EXECUTED"]:
                break

            duration = time.perf_counter() - t_step_start
            step_results.append({
                "step_number": step.step_number,
                "title": step.title,
                "status": "SUCCESS" if step_success else "WARNING",
                "duration_s": duration,
                "commands": step.commands,
                "output": "\n".join(step_output),
                "error": "\n".join(step_error),
            })

        total_duration = time.perf_counter() - t_start

        # Grava auditoria completa no Obsidian
        log_file = self.audit_logger.record_run(
            sop=sop,
            status=overall_status,
            duration_s=total_duration,
            step_results=step_results,
            summary_error=summary_error,
        )

        if overall_status == "SUCCESS":
            reply = f"Procedimento '{sop.title}' concluído com sucesso. Todos os {len(step_results)} passos foram executados e o log foi salvo no Obsidian."
        elif overall_status == "PARTIALLY_EXECUTED":
            reply = f"Procedimento '{sop.title}' interrompido: autorização cancelada no HUD no passo {len(step_results)}. Registro salvo em Logs."
        else:
            reply = f"Erro na execução do procedimento '{sop.title}': {summary_error}. A execução foi interrompida para proteger o sistema."

        return {
            "success": overall_status == "SUCCESS",
            "status": overall_status,
            "sop_name": sop.title,
            "duration_s": total_duration,
            "completed_steps": len(step_results),
            "total_steps": len(sop.steps),
            "log_file": str(log_file),
            "summary_error": summary_error,
            "reply": reply,
        }
