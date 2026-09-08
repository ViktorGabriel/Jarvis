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
        "runas /user:Administrator cmd.exe",
        "docker compose down -v",
        "docker system prune",
        "docker rm -f api_container",
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


# ── Git & Test Runner Tools ──────────────────────────────────────────────────

def test_git_inspect_modes():
    """Valida os modos de inspeção do GitAssistant (status, diff, recent_commits)."""
    from core.engineering.git_assistant import GitAssistant
    from core.governance.interceptor import SafetyInterceptor

    interceptor = SafetyInterceptor()
    git = GitAssistant(workspace_root=Path("."), interceptor=interceptor)

    status_res = git.inspect("status")
    assert "mode" in status_res
    assert status_res["mode"] == "status"
    assert "reply" in status_res

    diff_res = git.inspect("diff")
    assert diff_res["mode"] == "diff"
    assert "reply" in diff_res

    commits_res = git.inspect("recent_commits")
    assert commits_res["mode"] == "recent_commits"
    assert "reply" in commits_res


def test_test_runner_auto_detect():
    """Valida a detecção automática de comandos de teste."""
    from core.engineering.runner import TestAndLintRunner

    cmd = TestAndLintRunner.auto_detect_test_command(Path("."))
    assert "pytest" in cmd

    sanitized = TestAndLintRunner.sanitize_command("pytest -q \x00; echo oi\r")
    assert "\x00" not in sanitized
    assert "\r" not in sanitized


def test_test_runner_execution_summary():
    """Valida a execução de testes com extração semântica de resumo."""
    import asyncio
    from core.engineering.runner import TestAndLintRunner

    res = asyncio.run(
        TestAndLintRunner.run_tests_with_summary(
            cmd=r".\venv\Scripts\pytest -q tests/test_core.py -k test_governance_safe_commands",
            cwd=Path(".")
        )
    )
    assert res["success"] is True
    assert res["passed"] >= 1
    assert "sucesso" in res["reply"].lower()


# ── Daily Journal Lifecycle Tools ────────────────────────────────────────────

def test_setup_daily_journal_with_inheritance():
    """Valida a criação do diário matinal herdando pendências de ontem e da inbox."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    journal = JournalManager(vault)

    # 1. Simula pendência na Inbox
    vault.capture_to_inbox("Revisar PR pendente", entry_type="task")

    # 2. Executa setup_daily_journal
    res = journal.setup_daily_journal(
        priorities=["Implementar módulo de IA", "Escrever testes"],
        time_blocks=[{"time": "09:00 - 11:00", "task": "Codar IA"}]
    )
    assert res["success"] is True
    assert res["priorities_count"] == 2
    assert res["inherited_tasks_count"] >= 1
    assert "daily note criada" in res["reply"].lower()

    # Verifica arquivo
    daily_file = Path(res["file"])
    assert daily_file.exists()
    content = daily_file.read_text(encoding="utf-8")
    assert "Implementar módulo de IA" in content
    assert "Revisar PR pendente" in content
    assert "09:00 - 11:00" in content
    assert "status: in_progress" in content


def test_setup_daily_journal_non_destructive_update():
    """Valida que chamar setup em nota existente atualiza sem apagar conteúdo."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    journal = JournalManager(vault)

    # Cria diário inicial
    res1 = journal.setup_daily_journal(priorities=["Meta A"])
    daily_file = Path(res1["file"])

    # Anexa uma anotação livre
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write("\nMinha nota importante que não pode sumir!\n")

    # Atualiza com novas prioridades
    res2 = journal.setup_daily_journal(priorities=["Meta B"])
    assert res2["success"] is True

    content = daily_file.read_text(encoding="utf-8")
    assert "Minha nota importante que não pode sumir!" in content
    assert "Meta B" in content


def test_close_daily_journal():
    """Valida o fechamento noturno: contagem de tarefas e retrospectiva."""
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    journal = JournalManager(vault)

    # Prepara diário com 1 tarefa feita e 1 pendente
    res = journal.setup_daily_journal(priorities=["Tarefa 1"])
    daily_file = Path(res["file"])
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write("\n- [x] Tarefa concluída com sucesso\n- [ ] Tarefa que ficou para amanhã\n")

    # Executa fechamento
    close_res = journal.close_daily_journal(
        reflection="Dia altamente produtivo na refatoração",
        energy_rating=5
    )
    assert close_res["success"] is True
    assert close_res["completed_tasks"] >= 1
    assert close_res["pending_tasks"] >= 1
    assert "dia consolidado" in close_res["reply"].lower()

    content = daily_file.read_text(encoding="utf-8")
    assert "status: closed" in content
    assert "Dia altamente produtivo na refatoração" in content
    assert "⭐⭐⭐⭐⭐" in content


def test_docker_manager_is_running_and_inspect_daemon_down(monkeypatch):
    """Valida diagnóstico amigável quando o Docker daemon está inativo."""
    from core.engineering.docker_manager import DockerManager
    mgr = DockerManager()
    monkeypatch.setattr(mgr, "_run_cmd", lambda cmd, cwd=None, timeout=15: (1, "", "Cannot connect to the Docker daemon"))

    is_up, msg = mgr.is_docker_running()
    assert is_up is False
    assert "nao esta em execucao" in msg

    res = mgr.inspect_services()
    assert res["success"] is False
    assert res["is_docker_running"] is False
    assert "desligado" in res["reply"].lower()


def test_docker_manager_inspect_services_mock(monkeypatch):
    """Valida o parsing consolidado de containers a partir da saída do Docker CLI."""
    from core.engineering.docker_manager import DockerManager
    mgr = DockerManager()
    monkeypatch.setattr(mgr, "is_docker_running", lambda: (True, "OK"))

    sample_json = (
        '{"ID":"1a2b3c","Names":"my_postgres","Image":"postgres:15","Status":"Up 2 hours","State":"running","Ports":"0.0.0.0:5432->5432/tcp"}\n'
        '{"ID":"4d5e6f","Names":"my_redis","Image":"redis:alpine","Status":"Up 2 hours","State":"running","Ports":"0.0.0.0:6379->6379/tcp"}'
    )
    monkeypatch.setattr(mgr, "_run_cmd", lambda cmd, cwd=None, timeout=15: (0, sample_json, ""))

    res = mgr.inspect_services()
    assert res["success"] is True
    assert res["containers_count"] == 2
    assert res["containers"][0]["name"] == "my_postgres"
    assert res["containers"][1]["name"] == "my_redis"
    assert "2 containers encontrados" in res["reply"]


def test_docker_manager_manage_service_start_stop(monkeypatch):
    """Valida início e parada de serviços específicos via Docker CLI."""
    from core.engineering.docker_manager import DockerManager
    mgr = DockerManager()
    monkeypatch.setattr(mgr, "is_docker_running", lambda: (True, "OK"))

    executed_cmds = []
    def fake_run(cmd, cwd=None, timeout=30):
        executed_cmds.append(cmd)
        return 0, "Container executed", ""
    monkeypatch.setattr(mgr, "_run_cmd", fake_run)

    start_res = mgr.manage_service(action="start", target="postgres")
    assert start_res["success"] is True
    assert "inicializados" in start_res["reply"]
    assert executed_cmds[-1] == ["docker", "start", "postgres"]

    stop_res = mgr.manage_service(action="stop", target="postgres")
    assert stop_res["success"] is True
    assert "finalizados" in stop_res["reply"]
    assert executed_cmds[-1] == ["docker", "stop", "postgres"]


def test_check_service_health_tcp_and_http(monkeypatch):
    """Valida medição de latência e detecção de socket TCP e endpoint HTTP."""
    import socket
    import threading
    from core.engineering.docker_manager import DockerManager

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    assigned_port = server_sock.getsockname()[1]

    def accept_once():
        try:
            conn, _ = server_sock.accept()
            conn.close()
        except Exception:
            pass
        finally:
            server_sock.close()

    t = threading.Thread(target=accept_once, daemon=True)
    t.start()

    mgr = DockerManager()
    # Porta ativa
    res_up = mgr.check_health(target="custom", port=assigned_port)
    assert res_up["success"] is True
    assert res_up["reachable"] is True
    assert res_up["status"] == "healthy"
    assert res_up["latency_ms"] >= 0

    # Porta inativa
    res_down = mgr.check_health(target="custom", port=59998)
    assert res_down["success"] is True
    assert res_down["reachable"] is False
    assert res_down["status"] in ["closed", "timeout"]

    # Endpoint HTTP
    monkeypatch.setattr(mgr, "_check_http_health", lambda url, target_name: {
        "success": True, "target": target_name, "type": "http", "url": url,
        "status_code": 200, "healthy": True, "latency_ms": 1.5,
        "reply": f"API {target_name} esta ativo (200) com latencia de 1.5ms."
    })
    res_http = mgr.check_health(target="api", endpoint="/health")
    assert res_http["healthy"] is True
    assert res_http["status_code"] == 200


def test_docker_destructive_operation_governance_block(monkeypatch):
    """Valida que operações destrutivas exigem aprovação preventiva no HUD e bloqueiam se rejeitadas."""
    import asyncio
    from core.engineering.docker_manager import DockerManager
    from core.governance.interceptor import SafetyInterceptor

    interceptor = SafetyInterceptor()
    mgr = DockerManager(interceptor=interceptor)

    # Caso 1: Usuário rejeita a operação no HUD
    async def run_rejected():
        async def auto_reject():
            while not interceptor.pending_tickets:
                await asyncio.sleep(0.01)
            ticket_id = list(interceptor.pending_tickets.keys())[0]
            interceptor.resolve_ticket(ticket_id, approved=False)

        task = asyncio.create_task(auto_reject())
        res = await mgr.destructive_operation(action="down_volumes")
        await task
        return res

    rej_res = asyncio.run(run_rejected())
    assert rej_res["success"] is False
    assert rej_res["approved"] is False
    assert "cancelada pelo usuario" in rej_res["reply"]

    # Caso 2: Usuário autoriza a operação no HUD
    monkeypatch.setattr(mgr, "_run_cmd", lambda cmd, cwd=None, timeout=30: (0, "Pruned", ""))
    async def run_approved():
        async def auto_approve():
            while not interceptor.pending_tickets:
                await asyncio.sleep(0.01)
            ticket_id = list(interceptor.pending_tickets.keys())[0]
            interceptor.resolve_ticket(ticket_id, approved=True)

        task = asyncio.create_task(auto_approve())
        res = await mgr.destructive_operation(action="prune_system")
        await task
        return res

    app_res = asyncio.run(run_approved())
    assert app_res["success"] is True
    assert app_res["approved"] is True
    assert "concluida com sucesso" in app_res["reply"]


def test_sop_parser_frontmatter_and_steps():
    """Valida o parser de frontmatter YAML e extração de etapas com blocos de código."""
    from core.obsidian.sop_manager import SOPParser

    sop_file = TEST_VAULT / "Machine" / "SOPs" / "deploy-homolog.md"
    sop_file.parent.mkdir(parents=True, exist_ok=True)
    sop_content = """---
title: Deploy em Homologação
description: Atualiza os containers de teste e executa migrações
category: devops
triggers: ["fazer deploy", "deploy homolog"]
tags: [sop/devops, deploy]
---

# Deploy em Homologação

## Passo 1: Atualizar Repositório
Puxa as alterações mais recentes da branch main.
```bash
git pull origin main
```

## Passo 2: Rodar Migrações do Banco
Aplica os schemas pendentes.
```bash
python manage.py migrate
```
"""
    sop_file.write_text(sop_content, encoding="utf-8")

    sop = SOPParser.parse_sop(sop_file, TEST_VAULT)
    assert sop is not None
    assert sop.id == "deploy-homolog"
    assert sop.title == "Deploy em Homologação"
    assert sop.category == "devops"
    assert "fazer deploy" in sop.triggers
    assert len(sop.steps) == 2
    assert sop.steps[0].title == "Atualizar Repositório"
    assert "git pull origin main" in sop.steps[0].commands
    assert sop.steps[1].title == "Rodar Migrações do Banco"
    assert "python manage.py migrate" in sop.steps[1].commands


def test_sop_list_available():
    """Valida listagem e filtros de SOPs e Workflows no cofre."""
    from core.obsidian.sop_manager import SOPManager

    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    mgr = SOPManager(vault=vault)

    # Cria 1 SOP e 1 Workflow
    f1 = TEST_VAULT / "Machine" / "SOPs" / "sop-backup.md"
    f1.parent.mkdir(parents=True, exist_ok=True)
    f1.write_text("---\ntitle: Backup Geral\ncategory: infra\n---\n## Passo 1\n`git status`\n", encoding="utf-8")

    f2 = TEST_VAULT / "Machine" / "Workflows" / "wf-onboarding.md"
    f2.parent.mkdir(parents=True, exist_ok=True)
    f2.write_text("---\ntitle: Onboarding de Dev\ncategory: hr\n---\n## Passo 1\n`python --version`\n", encoding="utf-8")

    res = mgr.list_sops()
    assert res["success"] is True
    assert res["total"] >= 2

    # Filtro por categoria
    cat_res = mgr.list_sops(category="infra")
    assert cat_res["total"] == 1
    assert cat_res["sops"][0]["id"] == "sop-backup"

    # Filtro por query
    q_res = mgr.list_sops(query="onboarding")
    assert q_res["total"] == 1
    assert q_res["sops"][0]["id"] == "wf-onboarding"


def test_sop_execute_dry_run():
    """Valida simulação dry-run sem disparo de comandos reais."""
    import asyncio
    from core.obsidian.sop_manager import SOPManager

    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    mgr = SOPManager(vault=vault)

    f = TEST_VAULT / "Machine" / "SOPs" / "sop-test.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("---\ntitle: Teste Simulado\ncategory: test\n---\n## Passo 1\n```bash\necho 'nao deve rodar'\n```\n", encoding="utf-8")

    res = asyncio.run(mgr.execute_sop("sop-test", dry_run=True))
    assert res["success"] is True
    assert res["dry_run"] is True
    assert "Simulação" in res["reply"]
    assert Path(res["log_file"]).exists()


def test_sop_execute_sequential_and_audit_logging(monkeypatch):
    """Valida execução sequencial com êxito e registro de auditoria em Machine/Logs."""
    import asyncio
    from core.obsidian.sop_manager import SOPManager

    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    mgr = SOPManager(vault=vault)

    f = TEST_VAULT / "Machine" / "SOPs" / "pipeline-completo.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("""---
title: Pipeline Completo
category: ci
---
## Passo 1: Checagem
```bash
echo passo1
```
## Passo 2: Build
```bash
echo passo2
```
""", encoding="utf-8")

    executed = []
    def fake_cmd(cmd, timeout=45):
        executed.append(cmd)
        return 0, f"Output of {cmd}", ""

    monkeypatch.setattr(mgr, "_run_cmd", fake_cmd)

    res = asyncio.run(mgr.execute_sop("pipeline-completo", dry_run=False))
    assert res["success"] is True
    assert res["status"] == "SUCCESS"
    assert res["completed_steps"] == 2
    assert len(executed) == 2

    # Valida auditoria em Machine/Logs
    log_path = Path(res["log_file"])
    assert log_path.exists()
    log_content = log_path.read_text(encoding="utf-8")
    assert "Pipeline Completo" in log_content
    assert "SUCCESS" in log_content
    assert "Passo 1" in log_content
    assert "Passo 2" in log_content


def test_sop_execute_governance_rejection():
    """Valida que passo destrutivo pausa para aprovação e encerra se rejeitado."""
    import asyncio
    from core.obsidian.sop_manager import SOPManager
    from core.governance.interceptor import SafetyInterceptor

    interceptor = SafetyInterceptor()
    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    mgr = SOPManager(vault=vault, interceptor=interceptor)

    f = TEST_VAULT / "Machine" / "SOPs" / "limpeza-critica.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("""---
title: Limpeza Crítica
category: cleanup
---
## Passo 1: Remover Volumes
```bash
docker compose down -v
```
## Passo 2: Pós-limpeza
```bash
echo nunca_chegara_aqui
```
""", encoding="utf-8")

    async def run_sop_with_rejection():
        async def auto_reject():
            while not interceptor.pending_tickets:
                await asyncio.sleep(0.01)
            ticket_id = list(interceptor.pending_tickets.keys())[0]
            interceptor.resolve_ticket(ticket_id, approved=False)

        task = asyncio.create_task(auto_reject())
        res = await mgr.execute_sop("limpeza-critica")
        await task
        return res

    res = asyncio.run(run_sop_with_rejection())
    assert res["success"] is False
    assert res["status"] == "PARTIALLY_EXECUTED"
    assert "cancelada no HUD" in res["reply"]

    # Verifica que o log registrou a rejeição
    log_content = Path(res["log_file"]).read_text(encoding="utf-8")
    assert "REJECTED" in log_content


def test_sop_execute_failure_halt(monkeypatch):
    """Valida que erro em passo interrompe imediatamente os passos posteriores."""
    import asyncio
    from core.obsidian.sop_manager import SOPManager

    vault = ObsidianVaultManager(vault_path=TEST_VAULT)
    mgr = SOPManager(vault=vault)

    f = TEST_VAULT / "Machine" / "SOPs" / "falha-proposital.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("""---
title: Falha Proposital
category: test
---
## Passo 1: Quebra
```bash
comando_que_falha
```
## Passo 2: Nunca Executado
```bash
echo 'passo2'
```
""", encoding="utf-8")

    executed = []
    def fake_cmd(cmd, timeout=45):
        executed.append(cmd)
        if "comando_que_falha" in cmd:
            return 1, "", "Erro fatal no comando"
        return 0, "Sucesso", ""

    monkeypatch.setattr(mgr, "_run_cmd", fake_cmd)

    res = asyncio.run(mgr.execute_sop("falha-proposital"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert res["completed_steps"] == 1
    assert len(executed) == 1  # Passo 2 nunca foi chamado!
    assert "Erro na execução" in res["reply"]


def test_telemetry_get_system_metrics_summary():
    """Valida coleta consolidada de métricas de sistema (CPU, RAM, Disco e Voz)."""
    from core.system.telemetry_service import TelemetryService
    telemetry = TelemetryService()
    metrics = telemetry.get_system_metrics("summary")

    assert metrics["success"] is True
    assert metrics["metric"] == "summary"
    assert "cpu_percent" in metrics
    assert isinstance(metrics["cpu_count"], int)
    assert metrics["ram_total_gb"] > 0
    assert metrics["ram_percent"] >= 0
    assert "disk_total_gb" in metrics
    assert "reply" in metrics
    assert len(metrics["reply"]) > 0


def test_telemetry_metrics_by_type():
    """Valida consultas direcionadas de métricas por tipo específico."""
    from core.system.telemetry_service import TelemetryService
    telemetry = TelemetryService()

    # CPU
    cpu_res = telemetry.get_system_metrics("cpu")
    assert cpu_res["success"] is True
    assert cpu_res["metric"] == "cpu"
    assert "CPU" in cpu_res["reply"] or "Carga" in cpu_res["reply"]

    # Memória
    mem_res = telemetry.get_system_metrics("memory")
    assert mem_res["success"] is True
    assert mem_res["metric"] == "memory"
    assert "ram_total_gb" in mem_res
    assert "Memória RAM" in mem_res["reply"]

    # Disco
    disk_res = telemetry.get_system_metrics("disk")
    assert disk_res["success"] is True
    assert disk_res["metric"] == "disk"
    assert "disk_free_gb" in disk_res
    assert "Disco" in disk_res["reply"]


def test_telemetry_top_processes_extraction(monkeypatch):
    """Valida extração e ordenação dos processos que mais consom recursos."""
    from core.system.telemetry_service import TelemetryService
    import psutil

    telemetry = TelemetryService()

    class FakeProc:
        def __init__(self, pid, name, rss, cpu_p):
            self.info = {
                "pid": pid,
                "name": name,
                "memory_info": type("obj", (object,), {"rss": rss})(),
                "cpu_percent": cpu_p,
                "memory_percent": 2.5,
            }

    fake_procs = [
        FakeProc(101, "node.exe", 800 * 1024 * 1024, 5.0),
        FakeProc(102, "chrome.exe", 1500 * 1024 * 1024, 8.0),
        FakeProc(103, "python.exe", 200 * 1024 * 1024, 1.2),
        FakeProc(104, "System Idle Process", 0, 0.0),
    ]

    monkeypatch.setattr(psutil, "process_iter", lambda attrs: fake_procs)

    procs = telemetry.get_top_processes(limit=2)
    assert len(procs) == 2
    # chrome.exe tem maior consumo de RAM (1500 MB)
    assert procs[0]["name"] == "chrome.exe"
    assert procs[0]["memory_mb"] == 1500.0
    assert procs[1]["name"] == "node.exe"


def test_telemetry_threshold_alert_and_cooldown():
    """Valida disparo de alertas proativos para limites de RAM/CPU/Disco e controle de cooldown."""
    from core.system.telemetry_service import TelemetryService
    telemetry = TelemetryService()

    fake_procs = [{"name": "heavy_process.exe", "memory_mb": 4096.0}]

    # 1. Alerta de RAM > 88%
    alert = telemetry._check_alerts(cpu_p=30.0, ram_p=92.0, disk_free=50.0, top_procs=fake_procs)
    assert alert is not None
    assert alert["type"] == "memory"
    assert alert["level"] == "warning"
    assert alert["should_notify"] is True
    assert "heavy_process.exe" in alert["message"]

    # 2. Cooldown ativo impede notificação imediata duplicada
    second_alert = telemetry._check_alerts(cpu_p=30.0, ram_p=93.0, disk_free=50.0, top_procs=fake_procs)
    assert second_alert is not None
    assert second_alert["should_notify"] is False

    # 3. Alerta de CPU > 90%
    telemetry.last_alert_time = 0.0  # Reseta cooldown
    cpu_alert = telemetry._check_alerts(cpu_p=95.0, ram_p=40.0, disk_free=50.0, top_procs=fake_procs)
    assert cpu_alert is not None
    assert cpu_alert["type"] == "cpu"
    assert cpu_alert["level"] == "critical"
    assert cpu_alert["should_notify"] is True

    # 4. Alerta de Disco < 10GB
    telemetry.last_alert_time = 0.0
    disk_alert = telemetry._check_alerts(cpu_p=20.0, ram_p=50.0, disk_free=4.5, top_procs=[])
    assert disk_alert is not None
    assert disk_alert["type"] == "disk"
    assert disk_alert["should_notify"] is True
    assert "4.5 GB" in disk_alert["message"]


def test_gemini_telemetry_deterministic_trigger():
    """Valida atalhos diretos determinísticos de telemetria no GeminiBrain (0 tokens de API)."""
    import asyncio
    from unittest.mock import MagicMock
    from core.brain.live_client import GeminiBrain
    from core.system.telemetry_service import TelemetryService

    mock_telemetry = MagicMock(spec=TelemetryService)
    mock_telemetry.get_system_metrics.return_value = {
        "success": True,
        "reply": "Memória RAM em 62%, CPU operando em 15%. Sistema perfeitamente estável."
    }

    brain = GeminiBrain(
        vault=MagicMock(),
        journal=MagicMock(),
        rag=MagicMock(),
        git=MagicMock(),
        focus=MagicMock(),
        interceptor=MagicMock(),
        telemetry=mock_telemetry,
    )

    # Executa comando de status da máquina
    res = asyncio.run(brain.process_user_intent("como está a máquina?"))
    assert "Memória RAM em 62%" in res["reply"]
    mock_telemetry.get_system_metrics.assert_called_with("summary")

    # Executa comando de uso de RAM
    mock_telemetry.get_system_metrics.return_value = {
        "success": True,
        "reply": "Memória RAM em 62%, com 9.8 GB utilizados de 16.0 GB."
    }
    res_ram = asyncio.run(brain.process_user_intent("uso de ram"))
    assert "Memória RAM em 62%" in res_ram["reply"]
    mock_telemetry.get_system_metrics.assert_called_with("memory")


