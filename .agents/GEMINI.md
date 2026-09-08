# J.A.R.V.I.S — Regras do Agente (sempre ativas)

## Identidade e Tom
- Voce e o agente de desenvolvimento do projeto J.A.R.V.I.S (Just A Rather Very Intelligent System).
- Responda sempre em **portugues brasileiro** a menos que o usuario mude o idioma.
- Seja tecnicamente preciso e conciso. Evite frases de enchimento.

## Stack do Projeto
- **Core Python**: Python 3.12, asyncio, websockets, google-genai, psutil, pyperclip, sounddevice
- **HUD**: Electron 33 + React 18 + Vite 5 + TypeScript + Tailwind CSS + Three.js
- **Banco**: Sem banco relacional — estado persiste em arquivos Markdown no Obsidian vault
- **OS alvo**: Windows 11 (PowerShell, Win32 API via ctypes, pyperclip, winsound)
- **AI**: Gemini 2.5 Flash (primario), cascata para 2.5 Pro em caso de 503/429
- **Testes**: pytest 9.1, pytest-anyio, unittest.mock

## Regras de Codigo

### Python (core/)
- Todos os modulos novos em `core/system/`, `core/brain/`, etc. devem ser **stateless** (class methods) OU instanciados e injetados no `JarvisDaemon` via `__init__`.
- Nunca usar `asyncio.run()` dentro de uma coroutine ja em execucao.
- Toda chamada bloqueante (subprocess, ctypes, pyperclip) deve ser envolvida em `loop.run_in_executor(None, ...)` quando chamada de dentro de uma coroutine critica.
- Importar `config` de `core.config` — nunca hardcode paths ou chaves de API.
- Tratar excecoes especificas (nao `except Exception` puro) sempre que possivel.

### TypeScript/React (hud/)
- Componentes novos em `hud/src/components/`.
- Todo estado derivado do WebSocket vem do hook `useJarvisSocket` — nao criar novos sockets.
- Three.js: sempre fazer `dispose()` de geometrias e materiais no cleanup do `useEffect`.
- Nao usar `<React.StrictMode>` — causa dupla montagem do WebSocket hook em dev.
- IPC Electron: sempre usar `contextBridge` no preload — nunca expor `ipcRenderer` diretamente.

### Electron (hud/electron/)
- Arquivos Electron usam extensao `.cjs` por causa do `"type": "module"` no package.json.
- Handlers IPC: sempre `ipcMain.handle()` (async) + `ipcRenderer.invoke()` no renderer.

## Regras de Commits (SEMPRE seguir)
- Commits PONTUAIS e CONVENCIONAIS: `tipo(escopo): descricao em ingles ou portugues`
- Tipos: `feat`, `fix`, `test`, `chore`, `refactor`, `docs`, `style`, `perf`
- Escopos validos: `system`, `brain`, `hud`, `obsidian`, `governance`, `engineering`, `api`, `config`
- **Nunca** commitar `.env`, `venv/`, `node_modules/`, `dist/`, `__pycache__/`
- No PowerShell: usar `;` para encadear comandos (nao `&&`)

## Regras de Governanca
- Comandos `git push`, `rm -rf`, `del /f`, `runas`, operacoes de admin: **requerem aprovacao**
- Operacoes de leitura (git status, git diff, pytest, cat): **autonomas**
- Nunca executar codigo que modifique arquivos fora do repositorio sem confirmacao

## Estrutura de Arquivos
```
Jarvis/
  core/           # Daemon Python
    api/          # WebSocket server + protocol
    brain/        # GeminiBrain, VoiceIO, prompts
    engineering/  # DiffEngine, GitAssistant, Runner
    governance/   # Policy, Interceptor
    obsidian/     # VaultManager, Journal, RAG, Watcher
    system/       # AppLauncher, AudioController, FocusManager,
                  # WorkspaceOrchestrator, ClipboardManager
  hud/            # Electron + React HUD
    electron/     # main.cjs, preload.cjs
    src/
      components/ # ArcReactor, ApprovalModal, SystemMetrics...
      hooks/      # useJarvisSocket.ts
      config/     # workspaces.ts
      types/      # index.ts
  tests/          # pytest suite
  .agents/        # Skills e regras do agente
```

## Testes (obrigatorio)
- Todo novo modulo core DEVE ter pelo menos 1 teste em `tests/test_core.py`
- Rodar antes de commitar: `.\venv\Scripts\pytest tests\ -v`
- Coverage minimo esperado por modulo: 80%

## Economizar Tokens
- Antes de implementar, verificar se a feature ja existe em algum modulo do projeto
- Usar triggers deterministicos (if/elif) para comandos frequentes — evitar roundtrip ao Gemini desnecessariamente
- Ativar skills especificas quando o contexto exigir (nao carregar todas de uma vez)
