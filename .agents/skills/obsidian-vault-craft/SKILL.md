---
name: obsidian-vault-craft
description: "Expert guidelines and workflows for structuring and maintaining the J.A.R.V.I.S Obsidian Second Brain vault, atomic notes, bi-directional links, daily journals, and SOP manuals."
---

# Obsidian Vault Craft Skill

Use this skill whenever creating, organizing, or refactoring notes inside the Obsidian vault (`Human/` and `Machine/`).

## 1. Vault Taxonomy Standards
- **`Human/Journal/`**: Daily notes named strictly `YYYY-MM-DD.md`.
  - Must include YAML frontmatter (`date`, `type: daily-journal`, `status`).
  - Mandatory sections: Prioridades do Dia, Blocos de Tempo (Time-Blocking), Sessões de Foco & Deep Work, Retrospectiva & Fechamento.
- **`Human/Inbox/`**: Raw capture files `Inbox-YYYY-MM-DD.md`. Rapid dumps before atomic processing.
- **`Human/Projects/`**: Atomic notes named by concise topic/concept.
  - Formatted with frontmatter (`title`, `created`, `tags`, `type: atomic-note`).
  - Must link to related notes via `[[Nome da Nota]]`.
- **`Human/User Context/`**: Persistent profile, guidelines, preferences, and long-term architectural decisions.
- **`Machine/SOPs/`**: Standard Operating Procedures. Operational recipes that the agent can read and execute dynamically.
- **`Machine/Workflows/`**: Step-by-step logic and triggers for automated background tasks.
- **`Machine/Logs/`**: Execution audits, tool results, and command logs in JSONL or Markdown.

## 2. Linking & Bi-directional Navigation
- Always favor dense, meaningful bi-links: `[[Nome da Outra Nota]]`.
- Never create orphaned notes in `Human/Projects/`; connect each new atomic note to at least one hub or parent project note.
- Use clean tags: `#projeto`, `#arquitetura`, `#backend`, `#produtividade`.
