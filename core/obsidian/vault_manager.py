import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from core.config import config

class ObsidianVaultManager:
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or config.obsidian_vault_path
        self._ensure_structure()

    def _ensure_structure(self):
        """Garante a taxonomia oficial do J.A.R.V.I.S no cofre."""
        subdirs = [
            config.human_journal_path,
            config.human_inbox_path,
            config.human_voice_notes_path,
            config.human_projects_path,
            config.human_user_context_path,
            config.machine_sops_path,
            config.machine_workflows_path,
            config.machine_research_path,
            config.machine_logs_path,
        ]
        for s in subdirs:
            s.mkdir(parents=True, exist_ok=True)

    def write_note(self, relative_path: str, content: str, append: bool = False) -> Path:
        """Cria ou atualiza uma nota no cofre."""
        target = self.vault_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            f.write(content)
        return target

    def read_note(self, relative_path: str) -> Optional[str]:
        """Lê o conteúdo de uma nota do cofre."""
        target = self.vault_path / relative_path
        if target.exists() and target.is_file():
            with open(target, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def list_notes(self, subfolder: Optional[str] = None) -> List[Dict[str, str]]:
        """Lista todas as notas markdown na pasta especificada ou em todo o cofre."""
        base = self.vault_path / subfolder if subfolder else self.vault_path
        notes = []
        if not base.exists():
            return notes
        for p in base.rglob("*.md"):
            rel = p.relative_to(self.vault_path).as_posix()
            notes.append({
                "title": p.stem,
                "path": rel,
                "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
            })
        return notes

    def create_atomic_project_note(self, title: str, summary: str, tags: List[str], related_notes: List[str] = None) -> Path:
        """Cria uma nota atômica no Human/Projects conectada via bi-links."""
        clean_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        filename = f"{clean_title}.md"
        rel_path = f"Human/Projects/{filename}"

        tag_str = " ".join(f"#{t.replace('#', '')}" for t in tags)
        links_str = "\n".join(f"- [[{ref}]]" for ref in (related_notes or []))

        content = f"""---
title: "{clean_title}"
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags: [{', '.join(tags)}]
type: atomic-note
---

# {clean_title}

{tag_str}

## Resumo
{summary}

## Conexões e Referências
{links_str if links_str else "- (Sem conexões diretas)"}
"""
        return self.write_note(rel_path, content)

    def append_inbox_thought(self, text: str, source: str = "quick_capture") -> Path:
        """Adiciona pensamento rápido ao Human/Inbox."""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"Inbox-{today}.md"
        rel_path = f"Human/Inbox/{filename}"
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n- **[{timestamp}]** ({source}): {text}"
        return self.write_note(rel_path, entry, append=True)
