import os
import shutil
import pytest
from pathlib import Path
from core.governance.policy import GovernancePolicy, RiskLevel
from core.obsidian.vault_manager import ObsidianVaultManager
from core.obsidian.journal import JournalManager
from core.engineering.diff_engine import DiffEngine

TEST_VAULT = Path("./test_vault_tmp")

@pytest.fixture(autouse=True)
def cleanup():
    if TEST_VAULT.exists():
        shutil.rmtree(TEST_VAULT)
    yield
    if TEST_VAULT.exists():
        shutil.rmtree(TEST_VAULT)

def test_governance_destructive_commands():
    # Comandos que DEVEM acionar o travamento preventivo
    critical_cmds = [
        "rm -rf /",
        "del /f /q *",
        "rmdir /s /q project",
        "Remove-Item -Recurse -Force ./build",
        "git push origin master",
        "git push --force",
        "sudo apt update",
        "runas /user:Administrator cmd.exe"
    ]
    for cmd in critical_cmds:
        risk, reason = GovernancePolicy.evaluate_command(cmd)
        assert risk == RiskLevel.CRITICAL, f"Falha ao bloquear comando crítico: {cmd}"

def test_governance_safe_commands():
    # Comandos que devem ser permitidos de forma autônoma
    safe_cmds = [
        "git status",
        "git diff",
        "git log -n 5",
        "pytest tests/",
        "npm test",
        "python -m flake8 .",
        "cat README.md"
    ]
    for cmd in safe_cmds:
        risk, reason = GovernancePolicy.evaluate_command(cmd)
        assert risk == RiskLevel.SAFE, f"Comando seguro foi bloqueado indevidamente: {cmd}"

def test_obsidian_vault_scaffolding():
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    assert (TEST_VAULT / "Human" / "Journal").exists()
    assert (TEST_VAULT / "Human" / "Inbox").exists()
    assert (TEST_VAULT / "Human" / "Projects").exists()
    assert (TEST_VAULT / "Machine" / "SOPs").exists()
    assert (TEST_VAULT / "Machine" / "Logs").exists()

def test_obsidian_journal_creation():
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    journal = JournalManager(vault)
    daily_file = journal.get_or_create_daily_note()
    assert daily_file.exists()
    content = daily_file.read_text(encoding="utf-8")
    assert "Daily Journal" in content
    assert "Blocos de Tempo (Time-Blocking)" in content
    assert "Retrospectiva & Fechamento" in content

def test_diff_engine():
    test_file = TEST_VAULT / "sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def hello():\n    print('oi')\n", encoding="utf-8")

    new_content = "def hello():\n    print('ola mundo')\n    return True\n"
    diff = DiffEngine.generate_diff(test_file, new_content)

    assert diff["additions"] > 0
    assert "ola mundo" in diff["diff_text"]

def test_app_launcher_controls():
    from core.system.app_launcher import AppLauncher
    # Testa os métodos de controle de mídia e teclas sem levantar exceção
    assert AppLauncher.media_play_pause() is True
    assert AppLauncher.volume_up() is True
    assert AppLauncher.volume_down() is True

def test_workspace_orchestrator():
    import asyncio
    from core.system.workspace_orchestrator import WorkspaceOrchestrator
    from core.system.focus_manager import FocusManager

    focus = FocusManager()
    orchestrator = WorkspaceOrchestrator(focus_manager=focus)

    # Testa modos existentes
    res_dev = asyncio.run(orchestrator.activate_workspace("dev"))
    assert res_dev["success"] is True
    assert "desenvolvimento" in res_dev["reply"].lower()

    res_study = asyncio.run(orchestrator.activate_workspace("study"))
    assert res_study["success"] is True
    assert "estudo" in res_study["reply"].lower()

    res_deep = asyncio.run(orchestrator.activate_workspace("deep_work"))
    assert res_deep["success"] is True
    assert focus.is_deep_work is True

    res_rest = asyncio.run(orchestrator.activate_workspace("rest"))
    assert res_rest["success"] is True
    assert focus.is_deep_work is False

    # Testa modo inválido
    res_invalid = asyncio.run(orchestrator.activate_workspace("desconhecido"))
    assert res_invalid["success"] is False


# ── Clipboard Manager ────────────────────────────────────────────────────────

def test_clipboard_set_and_get():
    """Escreve e le um texto do clipboard."""
    from core.system.clipboard_manager import ClipboardManager
    test_text = "J.A.R.V.I.S clipboard test - hello world"
    ok = ClipboardManager.set_text(test_text)
    assert ok is True, "set_text deve retornar True em caso de sucesso"
    result = ClipboardManager.get_text()
    assert result is not None, "get_text nao deve retornar None apos set_text"
    assert "J.A.R.V.I.S clipboard test" in result


def test_clipboard_truncation():
    """Verifica que o clipboard e truncado ao maximo especificado."""
    from core.system.clipboard_manager import ClipboardManager
    long_text = "A" * 200
    ClipboardManager.set_text(long_text)
    result = ClipboardManager.get_text(max_length=50)
    assert result is not None
    # O resultado deve ser menor ou igual ao limite mais o sufixo de truncagem
    assert len(result) <= 50 + 60  # 50 chars + sufixo "[... truncado ...]"
    assert "truncado" in result


def test_clipboard_empty_returns_none_or_empty():
    """Apos escrever string vazia, get_text deve retornar None."""
    from core.system.clipboard_manager import ClipboardManager
    ClipboardManager.set_text("")
    result = ClipboardManager.get_text()
    # Clipboard vazio ou somente espacos deve retornar None
    assert result is None or result.strip() == ""


# ── Obsidian Inbox Voice Scratchpad ──────────────────────────────────────────

def test_obsidian_capture_to_inbox_thought():
    """Valida o registro de pensamentos/ideias na Inbox com tags e timestamp."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    res = vault.capture_to_inbox(
        content="Refatorar a arquitetura de cache do Gemini",
        entry_type="thought",
        tags=["#arquitetura", "ia"]
    )
    assert res["success"] is True
    assert "ideia registrada" in res["reply"].lower()

    inbox_file = TEST_VAULT / "Human" / "Inbox" / "Inbox.md"
    assert inbox_file.exists()
    content = inbox_file.read_text(encoding="utf-8")
    assert "Refatorar a arquitetura de cache do Gemini" in content
    assert "#arquitetura" in content
    assert "#ia" in content
    assert "**" in content  # Destaque de hora do pensamento


def test_obsidian_capture_to_inbox_task():
    """Valida o formato de checkbox de tarefa na Inbox."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    res = vault.capture_to_inbox(
        content="Atualizar dependencias do package.json",
        entry_type="task",
        tags=["#frontend"]
    )
    assert res["success"] is True
    assert "tarefa" in res["reply"].lower()

    inbox_file = TEST_VAULT / "Human" / "Inbox" / "Inbox.md"
    content = inbox_file.read_text(encoding="utf-8")
    assert "- [ ]" in content
    assert "Atualizar dependencias do package.json" in content
    assert "#frontend" in content


def test_obsidian_capture_to_inbox_reference():
    """Valida o formato de link/referência na Inbox."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    res = vault.capture_to_inbox(
        content="Documentação oficial do Google GenAI: https://ai.google.dev",
        entry_type="reference",
        tags=["docs"]
    )
    assert res["success"] is True
    assert "referência" in res["reply"].lower()

    inbox_file = TEST_VAULT / "Human" / "Inbox" / "Inbox.md"
    content = inbox_file.read_text(encoding="utf-8")
    assert "- 🔗" in content
    assert "https://ai.google.dev" in content
    assert "#docs" in content


def test_obsidian_capture_to_inbox_continuous_append():
    """Valida que multiplas capturas acumulam no mesmo arquivo continuo sem sobrescrever."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    vault.capture_to_inbox("Primeira entrada", entry_type="thought")
    vault.capture_to_inbox("Segunda entrada", entry_type="task")
    vault.capture_to_inbox("Terceira entrada", entry_type="thought")

    inbox_file = TEST_VAULT / "Human" / "Inbox" / "Inbox.md"
    content = inbox_file.read_text(encoding="utf-8")
    assert "Primeira entrada" in content
    assert "Segunda entrada" in content
    assert "Terceira entrada" in content
    assert content.count("- ") >= 3
