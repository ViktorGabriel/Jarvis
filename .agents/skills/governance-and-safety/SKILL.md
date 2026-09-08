---
name: governance-and-safety
description: "Governance policies, autonomy scope boundaries, preventative lock patterns, and safety interceptor protocols for autonomous AI agents."
---

# Governance & Safety Skill

Use this skill when defining or adding new tools, file operations, terminal actions, or autonomous routines to J.A.R.V.I.S.

## 1. Safety Levels
- **Tier 1 - Autonomous (Supervision by Scope)**:
  - Read-only actions: indexing vaults, reading files, git status, git diff, checking docker status.
  - Non-destructive workspace operations: running unit tests, linters, appending thoughts to `Human/Inbox/`, writing daily journal notes.
- **Tier 2 - Critical Lock (Mandatory Confirmation)**:
  - Any operation deleting or overwriting uncommitted code outside temp buffers.
  - Executing elevated commands (`sudo`, `runas`, admin registry modifications).
  - External network publications (`git push`, production webhooks).

## 2. Interceptor Pattern
- Never execute a Tier 2 action directly.
- The action must generate a unique approval ticket.
- Emit a `SAFETY_APPROVAL_REQUEST` event to the HUD.
- Suspend the execution coroutine until explicit confirmation is received via UI click or spoken passphrase.
