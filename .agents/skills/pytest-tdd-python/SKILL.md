---
name: pytest-tdd-python
description: >-
  Guia TDD com pytest para o core Python do J.A.R.V.I.S: estrutura de testes, fixtures,
  mock de syscalls Win32/clipboard/asyncio, testes de integracao de orquestrador,
  coverage e resolucao rapida de bugs. Ative ao criar testes, debugar falhas de teste
  ou validar novos modulos antes do commit.
---

# Test-Driven Development (TDD) para o Core J.A.R.V.I.S

A estabilidade do J.A.R.V.I.S repousa em testes automatizados rapidos e deterministicos executados pelo `pytest`.

---

## 1. Execucao de Testes

Execute sempre a partir da raiz do projeto usando o ambiente virtual:
```powershell
.\venv\Scripts\pytest tests\ -v
```

Configuracao `pytest.ini`:
```ini
[pytest]
pythonpath = .
```

---

## 2. Isolamento com Fixtures Autouse

Para testes que interagem com o sistema de arquivos (Obsidian Vault, Logs), garanta que nenhum resquicio persista:

```python
TEST_VAULT = Path("./test_vault_tmp")

@pytest.fixture(autouse=True)
def cleanup_test_vault():
    if TEST_VAULT.exists():
        shutil.rmtree(TEST_VAULT)
    yield
    if TEST_VAULT.exists():
        shutil.rmtree(TEST_VAULT)
```

---

## 3. Mockando Chamadas Nativas do Windows

Nao dispare processos reais ou altere estados criticos do sistema durante a execucao dos testes unitarios:

```python
from unittest.mock import patch

def test_app_launcher_mocked():
    with patch("os.system") as mock_sys:
        from core.system.app_launcher import AppLauncher
        AppLauncher.launch_spotify()
        mock_sys.assert_called_once_with("start spotify:")

def test_clipboard_fallback_power_shell():
    with patch("core.system.clipboard_manager.ClipboardManager._ps_get", return_value="erro simulado"):
        from core.system.clipboard_manager import ClipboardManager
        text = ClipboardManager.get_text()
        assert text == "erro simulado"
```

---

## 4. Testando Logica Assincrona

Para modulos que envolvem `asyncio`:

```python
import asyncio

def test_workspace_orchestrator():
    from core.system.workspace_orchestrator import WorkspaceOrchestrator
    orchestrator = WorkspaceOrchestrator()
    
    result = asyncio.run(orchestrator.activate_workspace("dev"))
    assert result["success"] is True
```

---

## 5. Checklist de Cobertura para Novos Recursos

1. [ ] Teste de caminho feliz (execucao bem-sucedida).
2. [ ] Teste de valores limites (clipboard vazio, comando inexistente).
3. [ ] Teste de bloqueio de governanca (comandos perigosos sao barrados).
4. [ ] Nenhuma dependencia externa ativa (APIs reais do Gemini usam mocks ou fallbacks).
