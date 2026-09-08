import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from core.config import config
from core.obsidian.vault_manager import ObsidianVaultManager

class JournalManager:
    def __init__(self, vault: ObsidianVaultManager):
        self.vault = vault

    def _get_yesterday_pending_tasks(self, current_date: datetime) -> List[str]:
        """Procura na Daily Note anterior por tarefas incompletas `- [ ]`."""
        tasks = []
        for days_back in range(1, 5): # Olha até 4 dias atrás para fins de semana
            prev_date = (current_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
            prev_file = self.vault.vault_path / "Human" / "Journal" / f"{prev_date}.md"
            if prev_file.exists():
                try:
                    with open(prev_file, "r", encoding="utf-8") as f:
                        for line in f:
                            match = re.match(r"^\s*-\s*\[\s*\]\s*(.+)$", line)
                            if match:
                                task_text = match.group(1).strip()
                                if task_text not in tasks:
                                    tasks.append(task_text)
                    break # Encontrou o dia mais recente com nota
                except Exception:
                    pass
        return tasks

    def get_or_create_daily_note(self) -> Path:
        """Obtém ou gera a Daily Note do dia no Human/Journal/YYYY-MM-DD.md"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        rel_path = f"Human/Journal/{date_str}.md"
        full_path = self.vault.vault_path / rel_path

        if full_path.exists():
            return full_path

        pending_tasks = self._get_yesterday_pending_tasks(now)
        pending_str = "\n".join(f"- [ ] {t} *(importada)*" for t in pending_tasks) if pending_tasks else "- [ ] (Nenhuma pendência anterior)"

        template = f"""---
date: {date_str}
type: daily-journal
status: active
deep_work_minutes: 0
---

# 📅 Daily Journal: {date_str}

## 🎯 Prioridades do Dia
{pending_str}
- [ ] 

## ⏱️ Blocos de Tempo (Time-Blocking)
- **09:00 - 10:30**: 
- **10:45 - 12:30**: 
- **14:00 - 16:30**: 
- **16:45 - 18:00**: 

## ⚡ Sessões de Foco & Deep Work
*(Registradas automaticamente pelo J.A.R.V.I.S durante as sessões)*

## 🌙 Retrospectiva & Fechamento
### O que foi concluído?
- 

### Resumo Reflexivo & Lições Aprendidas:
*(Será sintetizado no fechamento noturno)*
"""
        return self.vault.write_note(rel_path, template)

    def append_deep_work_session(self, duration_minutes: int, project_name: str = "Geral"):
        """Registra uma sessão concluída de Deep Work na Daily Note de hoje."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H:%M")
        rel_path = f"Human/Journal/{date_str}.md"
        entry = f"\n- [x] **[{timestamp}]** Foco contínuo: `{duration_minutes} min` em `{project_name}`"
        self.vault.write_note(rel_path, entry, append=True)
