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

