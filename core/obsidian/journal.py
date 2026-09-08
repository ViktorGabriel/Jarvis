import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from core.config import config
from core.obsidian.vault_manager import ObsidianVaultManager

class JournalManager:
    def __init__(self, vault: ObsidianVaultManager, git_workspace_path: Optional[Path] = None):
        self.vault = vault
        self.git_workspace_path = git_workspace_path

    def set_git_workspace(self, path: Path):
        self.git_workspace_path = path

    def _get_yesterday_pending_tasks(self, current_date: datetime) -> List[str]:
        """Procura na Daily Note anterior por tarefas incompletas `- [ ]`."""
        tasks = []
        for days_back in range(1, 6):  # Busca até 5 dias atrás (fins de semana/feriados)
            prev_date = (current_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
            prev_file = self.vault.vault_path / "Human" / "Journal" / f"{prev_date}.md"
            if prev_file.exists():
                try:
                    with open(prev_file, "r", encoding="utf-8") as f:
                        for line in f:
                            match = re.match(r"^\s*-\s*\[\s*\]\s*(.+)$", line)
                            if match:
                                task_text = match.group(1).strip()
                                # Remove anotações antigas de herança para não acumular tags redundantes
                                task_text = re.sub(r"\*\(.*?\)\*", "", task_text).strip()
                                if task_text and task_text not in tasks:
                                    tasks.append(task_text)
                    break  # Encontrou a data mais recente com nota
                except Exception:
                    pass
        return tasks

    def _get_inbox_pending_tasks(self) -> List[str]:
        """Coleta tarefas pendentes `- [ ]` registradas na Human/Inbox/Inbox.md."""
        tasks = []
        inbox_file = self.vault.vault_path / "Human" / "Inbox" / "Inbox.md"
        if inbox_file.exists():
            try:
                with open(inbox_file, "r", encoding="utf-8") as f:
                    for line in f:
                        match = re.match(r"^\s*-\s*\[\s*\]\s*(.+)$", line)
                        if match:
                            task_text = match.group(1).strip()
                            if task_text and task_text not in tasks:
                                tasks.append(task_text)
            except Exception:
                pass
        return tasks

    def _get_today_commits_count(self) -> int:
        """Obtém a contagem de commits realizados no workspace ativo durante o dia."""
        ws = self.git_workspace_path or Path.cwd()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d 00:00:00")
            res = subprocess.run(
                ["git", "log", f"--since={today_str}", "--oneline"],
                cwd=str(ws),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5
            )
            if res.returncode == 0 and res.stdout:
                lines = [l for l in res.stdout.strip().splitlines() if l.strip()]
                return len(lines)
        except Exception:
            pass
        return 0

    def get_or_create_daily_note(self) -> Path:
        """Obtém ou gera a Daily Note básica do dia."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        rel_path = f"Human/Journal/{date_str}.md"
        full_path = self.vault.vault_path / rel_path

        if full_path.exists():
            return full_path

        res = self.setup_daily_journal(
            priorities=["Definir prioridades do dia"],
            time_blocks=None
        )
        return Path(res["file"])

    def setup_daily_journal(
        self,
        priorities: List[str],
        time_blocks: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Cria ou atualiza a Daily Note matinal com metas, time-blocking e herança de pendências.

        Args:
            priorities: 1 a 3 focos principais para o dia.
            time_blocks: Lista de blocos `{ "time": "09:00 - 11:00", "task": "..." }`.

        Returns:
            Dict com arquivo, tarefas migradas e resposta falada.
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        rel_path = f"Human/Journal/{date_str}.md"
        full_path = self.vault.vault_path / rel_path

        # 1. Herança de pendências (Ontem + Inbox)
        yesterday_tasks = self._get_yesterday_pending_tasks(now)
        inbox_tasks = self._get_inbox_pending_tasks()
        all_inherited = []
        for t in yesterday_tasks:
            all_inherited.append(f"- [ ] {t} *(ontem)*")
        for t in inbox_tasks:
            all_inherited.append(f"- [ ] {t} *(inbox)*")

        inherited_count = len(all_inherited)

        # 2. Formata prioridades
        clean_priorities = [p.strip() for p in priorities if p.strip()]
        priorities_str = "\n".join(f"- [ ] 🎯 **{p}**" for p in clean_priorities) if clean_priorities else "- [ ] Foco geral"

        # 3. Formata blocos de tempo
        default_blocks = [
            {"time": "09:00 - 10:30", "task": "Deep Work / Engenharia"},
            {"time": "10:45 - 12:30", "task": "Desenvolvimento & Implementações"},
            {"time": "14:00 - 16:30", "task": "Arquitetura & Testes"},
            {"time": "16:45 - 18:00", "task": "Revisões & Planejamento"},
        ]
        blocks_to_use = time_blocks or default_blocks
        time_blocks_str = "\n".join(f"- **{b.get('time', '')}**: {b.get('task', '')}" for b in blocks_to_use)

        # 4. Formata tarefas herdadas
        tasks_section_str = "\n".join(all_inherited) if all_inherited else "- [ ] (Nenhuma pendência anterior)"

        # 5. Se já existe, atualiza sem sobrescrever anotações ou sessões existentes
        if full_path.exists():
            existing_content = full_path.read_text(encoding="utf-8")
            # Adiciona novas prioridades se não estiverem presentes
            for p in clean_priorities:
                if p not in existing_content:
                    existing_content = existing_content.replace("## 🎯 Foco do Dia", f"## 🎯 Foco do Dia\n- [ ] 🎯 **{p}**")
            full_path.write_text(existing_content, encoding="utf-8")
            reply = f"Daily Note de hoje atualizada, senhor. {len(clean_priorities)} metas registradas."
            return {
                "success": True,
                "file": str(full_path),
                "inherited_tasks_count": inherited_count,
                "reply": reply
            }

        # 6. Criação da nova nota estruturada
        template = f"""---
date: {date_str}
type: daily-journal
tags: [journal/daily]
status: in_progress
deep_work_minutes: 0
---

# 📅 Daily Journal: {date_str}

## 🎯 Foco do Dia
{priorities_str}

## ⏱️ Cronograma & Blocos de Tempo (Time-Blocking)
{time_blocks_str}

## ✅ Tarefas Herdadas & Pendências
{tasks_section_str}

## 📝 Anotações & Registro Contínuo
*(Anotações, pensamentos e insights registrados ao longo do dia)*

## ⚡ Sessões de Foco & Deep Work
*(Registradas automaticamente pelo J.A.R.V.I.S durante as sessões de foco)*

## 🌙 Retrospectiva Noturna (Retrospectiva & Fechamento)
*(Aguardando consolidação do encerramento do dia)*
"""
        self.vault.write_note(rel_path, template)
        reply = f"Daily note criada, senhor. Suas {len(clean_priorities)} prioridades estão definidas e {inherited_count} pendência{'s' if inherited_count != 1 else ''} foram migradas."
        return {
            "success": True,
            "file": str(full_path),
            "inherited_tasks_count": inherited_count,
            "priorities_count": len(clean_priorities),
            "reply": reply
        }

    def close_daily_journal(
        self,
        reflection: Optional[str] = None,
        energy_rating: Optional[int] = None
    ) -> Dict[str, Any]:
        """Consolida o dia: analisa checkboxes concluídos vs pendentes e sintetiza a retrospectiva noturna.

        Args:
            reflection: Resumo reflexivo ou lições aprendidas ditadas pelo usuário.
            energy_rating: Avaliação de energia/produtividade de 1 a 5.

        Returns:
            Dict com estatísticas do dia e resposta falada para voz.
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        rel_path = f"Human/Journal/{date_str}.md"
        full_path = self.vault.vault_path / rel_path

        if not full_path.exists():
            return {
                "success": False,
                "error": f"Daily note de hoje ({date_str}.md) não encontrada para encerramento.",
                "reply": "Não encontrei a Daily Note de hoje para realizar o fechamento, senhor."
            }

        content = full_path.read_text(encoding="utf-8")

        # Identifica possíveis variações do cabeçalho de retrospectiva existente
        retro_headers = [
            "## 🌙 Retrospectiva Noturna (Retrospectiva & Fechamento)",
            "## 🌙 Retrospectiva Noturna & Fechamento",
            "## 🌙 Retrospectiva Noturna",
            "## 🌙 Retrospectiva & Fechamento"
        ]
        found_header = None
        for h in retro_headers:
            if h in content:
                found_header = h
                break

        before_retro = content
        after_retro = ""
        if found_header:
            parts = content.split(found_header, 1)
            before_retro = parts[0]
            after_retro = parts[1]

        # Preserva linhas de anotações ou tarefas que o usuário tenha adicionado após o bloco de retro
        extra_user_lines = []
        for line in after_retro.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if "*(Aguardando consolidação" in stripped:
                continue
            if (
                stripped.startswith("- **Produtividade**:")
                or stripped.startswith("- **Energia / Foco**:")
                or stripped.startswith("- **Commits no Workspace**:")
                or stripped.startswith("- **Reflexão do Usuário**:")
                or "Pendências para Remanejar" in stripped
            ):
                continue
            if stripped.startswith("- [ ]") and "*(ontem)*" in stripped:
                continue
            extra_user_lines.append(line)

        if extra_user_lines:
            before_retro = before_retro.rstrip() + "\n\n" + "\n".join(extra_user_lines) + "\n"

        # 1. Contagem de tarefas concluídas vs pendentes
        completed_tasks = []
        pending_tasks = []

        for line in before_retro.splitlines():
            if re.match(r"^\s*-\s*\[x\]", line, re.IGNORECASE):
                completed_tasks.append(line.strip())
            elif re.match(r"^\s*-\s*\[\s*\]", line):
                pending_tasks.append(line.strip())

        total_tasks = len(completed_tasks) + len(pending_tasks)
        pct = int((len(completed_tasks) / total_tasks * 100)) if total_tasks > 0 else 100

        # 2. Extração de commits do dia
        commits_today = self._get_today_commits_count()

        # 3. Formatação da energia (estrelas)
        stars = ""
        if energy_rating:
            safe_rating = max(1, min(5, energy_rating))
            stars = f"{'⭐' * safe_rating} ({safe_rating}/5)"
        else:
            stars = "Não avaliado"

        # 4. Formata pendências a remanejar
        if pending_tasks:
            pending_str = "\n".join(f"  {p}" for p in pending_tasks)
        else:
            pending_str = "  - *(Nenhuma pendência! Todas as tarefas concluídas)*"

        # 5. Monta bloco de retrospectiva
        retro_block = f"""## 🌙 Retrospectiva Noturna (Retrospectiva & Fechamento)
- **Produtividade**: `{len(completed_tasks)} de {total_tasks} tarefas concluídas` ({pct}%)
- **Energia / Foco**: {stars}
- **Commits no Workspace**: `{commits_today} commit(s) hoje`
- **Reflexão do Usuário**: {reflection or "Nenhuma reflexão informada."}

### 📌 Pendências para Remanejar Amanhã:
{pending_str}
"""

        # 6. Atualiza o conteúdo substituindo o bloco de retrospectiva
        new_content = before_retro.rstrip() + "\n\n" + retro_block

        # Atualiza o status do frontmatter para closed
        new_content = re.sub(r"status:\s*[a-zA-Z_-]+", "status: closed", new_content)

        full_path.write_text(new_content, encoding="utf-8")

        reply = f"Dia consolidado, senhor. Você concluiu {len(completed_tasks)} de {total_tasks} tarefas hoje. Bom descanso."
        return {
            "success": True,
            "file": str(full_path),
            "completed_tasks": len(completed_tasks),
            "pending_tasks": len(pending_tasks),
            "total_tasks": total_tasks,
            "completion_rate": pct,
            "commits_today": commits_today,
            "reply": reply
        }

    def append_deep_work_session(self, duration_minutes: int, project_name: str = "Geral"):
        """Registra uma sessão concluída de Deep Work na Daily Note de hoje."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H:%M")
        rel_path = f"Human/Journal/{date_str}.md"
        entry = f"\n- [x] **[{timestamp}]** Foco contínuo: `{duration_minutes} min` em `{project_name}`"
        self.vault.write_note(rel_path, entry, append=True)
