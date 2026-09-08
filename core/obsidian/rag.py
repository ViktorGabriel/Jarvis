import re
from pathlib import Path
from typing import List, Dict
from core.obsidian.vault_manager import ObsidianVaultManager

class VaultRAG:
    def __init__(self, vault: ObsidianVaultManager):
        self.vault = vault

    def search_context(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Busca contextual rápida no cofre por correspondência semântica e palavras-chave."""
        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        all_notes = self.vault.list_notes()
        results = []

        for note in all_notes:
            content = self.vault.read_note(note["path"])
            if not content:
                continue

            score = 0
            content_lower = content.lower()
            title_lower = note["title"].lower()

            # Pontuação por termos encontrados no título e corpo
            for term in query_terms:
                if term in title_lower:
                    score += 5
                matches = content_lower.count(term)
                score += min(matches, 10)

            if score > 0:
                # Extrai um trecho representativo
                snippet = content[:350].strip().replace("\n", " ")
                results.append({
                    "title": note["title"],
                    "path": note["path"],
                    "snippet": snippet,
                    "score": score
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def build_system_context(self) -> str:
        """Coleta o contexto vivo essencial (User Context, SOPs e Daily Note) para alimentar o Gemini."""
        parts = []

        # 1. User Context
        user_ctx_notes = self.vault.list_notes("Human/User Context")
        for n in user_ctx_notes[:2]:
            content = self.vault.read_note(n["path"])
            if content:
                parts.append(f"### [Contexto do Usuário - {n['title']}]\n{content[:600]}")

        # 2. SOPs ativas do Machine/
        sop_notes = self.vault.list_notes("Machine/SOPs")
        for n in sop_notes[:3]:
            content = self.vault.read_note(n["path"])
            if content:
                parts.append(f"### [SOP Operacional - {n['title']}]\n{content[:500]}")

        return "\n\n".join(parts) if parts else "Nenhum contexto histórico registrado ainda."
