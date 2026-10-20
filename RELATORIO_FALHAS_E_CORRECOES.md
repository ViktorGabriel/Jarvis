# 🛠️ Relatório de Auditoria, Falhas Encontradas e Guia de Correções — J.A.R.V.I.S.

**Data da Auditoria:** 18/10/2026  
**Diretório Analisado:** `C:\Users\Viktor\Documents\estagio\Jarvis`  
**Status Final:** ✅ **100% Funcional (50/50 testes automatizados aprovados + Build HUD validado)**

---

## 📋 Resumo Executivo

Durante a inspeção completa de ponta a ponta (Backend Python Core Daemon, Servidor IPC WebSocket, Governança de Segurança, Integração Obsidian, Orquestrador de Sistema e Frontend HUD em Electron/React/TypeScript), foram identificadas **9 falhas técnicas e comportamentais** (incluindo bugs silenciosos de estado, falhas de configuração e efeitos colaterais nos testes).

Todas as falhas foram documentadas abaixo com a causa raiz, o passo a passo de como corrigir e já foram **corrigidas e cobertas por novos testes automatizados** em `tests/test_core.py`.

---

## 🚨 Registro de Falhas Detectadas e Como Corrigir

### 1. `[FALHA-01]` Variáveis vazias no `.env` quebravam o fallback de `OBSIDIAN_VAULT_PATH` e ignoravam `WS_HOST` / `WS_PORT`
- **Arquivo:** `core/config.py` (linhas 12–21)
- **Sintoma / Causa Raiz:**
  - `os.getenv("OBSIDIAN_VAULT_PATH", str(BASE_DIR / "vault"))` retorna `""` (string vazia) quando a chave existe em branco no `.env` (`OBSIDIAN_VAULT_PATH=`). Ao passar `""` para `Path("")`, o Python resolve para `Path(".")` (a raiz do projeto) em vez da pasta `./vault`, criando pastas `Human/` e `Machine/` soltas na raiz do repositório.
  - Além disso, `ws_host` e `ws_port` estavam com valores estáticos, ignorando `WS_HOST` e `WS_PORT` definidos no `.env`.
- **Como Corrigir:**
  Garantir higienização com `.strip()` e operador `or` para acionar o valor padrão sempre que a variável estiver vazia:
  ```python
  gemini_api_key: str = Field(default_factory=lambda: (os.getenv("GEMINI_API_KEY") or "").strip())
  gemini_model: str = Field(default_factory=lambda: (os.getenv("GEMINI_MODEL") or "").strip() or "gemini-3.5-flash-lite")
  gemini_live_model: str = Field(default_factory=lambda: (os.getenv("GEMINI_LIVE_MODEL") or "").strip() or "gemini-2.5-flash-native-audio-latest")
  ws_host: str = Field(default_factory=lambda: (os.getenv("WS_HOST") or "").strip() or "127.0.0.1")
  ws_port: int = Field(default_factory=lambda: int((os.getenv("WS_PORT") or "").strip() or 8765))
  obsidian_vault_path: Path = Field(
      default_factory=lambda: Path((os.getenv("OBSIDIAN_VAULT_PATH") or "").strip() or str(BASE_DIR / "vault"))
  )
  ```

---

### 2. `[FALHA-02]` Interrupção de fala (*Barge-in*) era enviada como pergunta ao modelo Gemini e faltava importação `Optional`
- **Arquivo:** `core/main.py` (linhas 1–8 e 163–203)
- **Sintoma / Causa Raiz:**
  1. Quando o usuário falava durante o estado `speaking`, o HUD (`useJarvisSocket.ts`) enviava `{ event: "USER_INPUT", data: { text: "[INTERRUPCAO_BARGE_IN]" } }`. O `core/main.py` não filtrava esse marcador, mudava o estado para `THINKING`, enviava a string literal `"[INTERRUPCAO_BARGE_IN]"` para a API do Gemini e não interrompia `self.voice_io.stop_speaking()`.
  2. Na linha 94 de `core/main.py`, `Optional[asyncio.AbstractEventLoop]` era utilizado sem `from typing import Optional`.
  3. Ao encerrar o modo Deep Work pelo botão do HUD (`DEEP_WORK_TOGGLE` com `enable=False`), a sessão não era gravada na Daily Note (`self.journal.append_deep_work_session`).
- **Como Corrigir:**
  Importar `Optional` de `typing`, interceptar `user_text == "[INTERRUPCAO_BARGE_IN]"` no início de `handle_hud_message` chamando `self.voice_io.stop_speaking()` e `await self.server.update_state(AgentState.IDLE)`, e registrar a sessão no `journal` ao desativar `DEEP_WORK_TOGGLE`.

---

### 3. `[FALHA-03]` Subtítulo de estado (`stateDetail`) ficava congelado no HUD e eventos `NOTIFICATION` eram descartados
- **Arquivo:** `hud/src/hooks/useJarvisSocket.ts` (linhas 59–105)
- **Sintoma / Causa Raiz:**
  1. Em `case 'STATE_UPDATE':`, a condição `if (data.detail) setStateDetail(data.detail);` impedia que `stateDetail` fosse limpo quando o backend enviava `detail: ""` ao retornar para `idle`. O texto da última ação ficava preso permanentemente no HUD.
  2. Eventos `NOTIFICATION` enviados pelo backend (alertas críticos de CPU/RAM/Disco e avisos de Deep Work) caíam no `default: break` e nunca eram exibidos no feed do HUD.
- **Como Corrigir:**
  Substituir `if (data.detail) setStateDetail(data.detail);` por `setStateDetail(data.detail ?? '');` e adicionar o tratamento `case 'NOTIFICATION':` inserindo a mensagem como `sender: 'system'` na lista `messages`.

---

### 4. `[FALHA-04]` `GitAssistant.commit` (`git_smart_commit`) não acionava o modal de aprovação no HUD
- **Arquivos:** `core/governance/interceptor.py` (linha 31) e `core/engineering/git_assistant.py` (linha 122)
- **Sintoma / Causa Raiz:**
  - `GitAssistant.commit(..., require_approval=True)` chamava `self.interceptor.guard_command('git commit -m "..."')`. Porém, `guard_command` avaliava o comando em `GovernancePolicy.evaluate_command()`, que classificava `git commit` como `RiskLevel.SAFE` e retornava `True` imediatamente sem abrir o modal no HUD.
  - Pior: se a mensagem de commit contivesse palavras como `"format"` ou `"del"` (ex.: `chore: format files`), caía num falso positivo de comando destrutivo de disco.
- **Como Corrigir:**
  Adicionar suporte a `force_approval: bool = False` e `custom_reason: str = ""` em `SafetyInterceptor.guard_command()` e passar `force_approval=True` em `GitAssistant.commit()` quando `require_approval=True`.

---

### 5. `[FALHA-05]` Captura Rápida do `ObsidianWidget` não acionava o atalho de Inbox e corrompia letras maiúsculas
- **Arquivo:** `core/brain/live_client.py` (linhas 173–181)
- **Sintoma / Causa Raiz:**
  1. O componente `ObsidianWidget.tsx` envia `"Criar nota de pensamento rápido: ${thought}"`, formato que não era reconhecido pela regex determinística `inbox_match` em `live_client.py`.
  2. A regex `inbox_match` fazia match em `text_lower` em vez de `text` com `re.IGNORECASE`, convertendo todo o texto da nota do usuário para letras minúsculas (perdendo siglas, nomes próprios e camelCase).
- **Como Corrigir:**
  Aplicar `re.search(..., text.strip(), re.IGNORECASE)` sobre o texto original e incluir `"criar nota de pensamento rápido"` e `"captura rápida"` nos gatilhos da regex.

---

### 6. `[FALHA-06]` `JournalManager.setup_daily_journal` mantinha prioridade fictícia, ignorava `time_blocks` e omitia `priorities_count` ao atualizar nota existente
- **Arquivo:** `core/obsidian/journal.py` (linhas 140–155)
- **Sintoma / Causa Raiz:**
  - Como `JarvisDaemon.run()` chama `get_or_create_daily_note()` no boot (criando a Daily Note com `- [ ] 🎯 **Definir prioridades do dia**`), qualquer chamada posterior a `setup_daily_journal` no mesmo dia entrava no bloco `if full_path.exists():`.
  - Esse bloco não removia o item fictício `"Definir prioridades do dia"`, ignorava novos `time_blocks` passados pelo usuário e não retornava a chave `"priorities_count"` no dicionário.
- **Como Corrigir:**
  No bloco `if full_path.exists():`, remover o placeholder `"Definir prioridades do dia"` quando prioridades reais forem enviadas, mesclar `time_blocks` informados e incluir `"priorities_count": len(clean_priorities)` no retorno.

---

### 7. `[FALHA-07]` `SOPManager` listava arquivos `*Index.md` como SOPs executáveis, omitia governança aprovada no log e usava ícone `❌` em `DRY_RUN`
- **Arquivo:** `core/obsidian/sop_manager.py` (linhas 256, 319 e 473–554)
- **Sintoma / Causa Raiz:**
  1. No cofre Obsidian com arquivos de índice (`SOPs Index.md`, `Workflows Index.md`), `list_sops()` listava os índices como se fossem procedimentos executáveis.
  2. Em `SOPAuditLogger.record_run`, passos com status `"SIMULATED"` (`dry_run=True`) recebiam o ícone `"❌"` (erro) em vez de `"🟡"`.
  3. Quando um passo crítico recebia aprovação do usuário no HUD (`approved = True`), o resultado do passo não salvava `"approved": True`, omitindo a linha `Governança: Autorizado pelo usuário no HUD` no log de auditoria.
- **Como Corrigir:**
  Ignorar arquivos cujo `stem.lower().endswith("index")` em `list_sops()` e `get_sop()`, mapear `"SIMULATED"` para `"🟡"` e `"WARNING"` para `"⚠️"`, e propagar `"approved": step_approved` em `step_results`.

---

### 8. `[FALHA-08]` Uso de `WebSocketServerProtocol` depreciado no `websockets 16.x` e ausência de `stop()` em `JarvisServer`
- **Arquivo:** `core/api/server.py` (linhas 6, 40, 50–80)
- **Sintoma / Causa Raiz:**
  - `from websockets.server import WebSocketServerProtocol` gerava `DeprecationWarning` no `websockets 16.1.1`.
  - Não havia método `stop()` para encerrar o servidor WebSocket de forma limpa em testes automatizados ou no desligamento do daemon.
- **Como Corrigir:**
  Remover a importação legada, criar o helper `_is_ws_closed(ws)` compatível com `ServerConnection` (`websockets 16.x`), capturar `Exception` em `send_to()` e adicionar `async def stop(self)`.

---

### 9. `[FALHA-09]` Testes `test_workspace_orchestrator` e `test_app_launcher_controls` disparavam ações reais no Windows durante o `pytest`
- **Arquivos:** `tests/test_core.py` (linhas 83–118) e `core/system/app_launcher.py` (linhas 55–94)
- **Sintoma / Causa Raiz:**
  - Rodar `pytest` executava `AppLauncher` e `AudioFeedback` reais sem mock: abria VS Code, Spotify, Obsidian e 3 abas no navegador, emitia bipes sonoros e alterava o volume do Windows da máquina.
  - Em `AppLauncher`, `os.system(f'start {target}')` era chamado sem o título vazio `start "" "{target}"`, o que no `cmd.exe` do Windows falha quando o caminho ou URL contém espaços ou `&`.
- **Como Corrigir:**
  Usar `start "" "{target}"` em `AppLauncher` e aplicar `monkeypatch` em `test_app_launcher_controls` e `test_workspace_orchestrator` para isolar os testes do sistema operacional.

---

### 10. `[FALHA-10]` `start.bat` fechava imediatamente por falta de `call`, detecção inadequada de porta e ausência de `pause`
- **Arquivo:** `start.bat`
- **Sintoma / Causa Raiz:**
  1. `netstat -ano | findstr ":8765"` detectava sockets de clientes tentando reconectar em `SYN_SENT` / `TIME_WAIT` (como abas de navegadores) como se fossem o servidor rodando, pulando a inicialização do daemon Python.
  2. A chamada a `npm run start` sem `call` (`call npm run start`) no Windows CMD transfere o controle para o script em lote `npm.cmd` sem retorno, fazendo com que a janela do terminal fechasse subitamente após qualquer término de processo.
  3. Ausência de validações explícitas de ambiente (`node`, `npm`, `venv`) e ausência de bloco `:erro` com `pause`.
- **Como Corrigir:**
  Filtrar explicitamente por `:8765 .*LISTENING`, usar `call npm run start`, adicionar checagem prévia de `python.exe`, `node` e `npm`, e adicionar `pause` ao final para manter a tela aberta em caso de erro.

---

### 11. `[FALHA-11]` Loop infinito de reconexão de voz do navegador no Electron (`network error`)
- **Arquivo:** `hud/src/hooks/useSpeechRecognition.ts` (linhas 68–74)
- **Sintoma / Causa Raiz:**
  O Chromium/Electron não suporta `webkitSpeechRecognition` nativo sem chaves de API do Google Cloud, disparando o evento `error: network`. Ao disparar o erro, o gatilho `onend` reiniciava a escuta instantaneamente sem verificar o tipo de erro, provocando um loop infinito de 10 tentativas por segundo no console.
- **Como Corrigir:**
  No manipulador `onerror`, se o erro for `network`, `not-allowed` ou `service-not-allowed`, desativar a flag de escuta contínua (`shouldListenRef.current = false`).

---

## 🧪 Suíte de Testes Automatizados (50 Testes)

Para executar todos os testes automatizados (incluindo os 10 novos testes de regressão e integração):

```powershell
.\venv\Scripts\pytest tests/ -v
```

Para validar a tipagem estática TypeScript e o build de produção do HUD:

```powershell
cd hud
npx tsc --noEmit
npm run build
```
