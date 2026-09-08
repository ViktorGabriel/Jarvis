---
name: python-async-patterns
description: >-
  Padroes asyncio Python para o core daemon do J.A.R.V.I.S: event loops, tasks concorrentes,
  WebSocket broadcast, barge-in de audio, approval gates com Future, error handling em gather,
  e integracao com APIs sincronas. Ative quando implementar novos modulos core, corrigir deadlocks,
  otimizar concorrencia do daemon ou evitar alto consumo de CPU.
---

# Padroes AsyncIO para o J.A.R.V.I.S Core Daemon

O nucleo do J.A.R.V.I.S opera inteiramente sob a arquitetura assincrona orientada a eventos (`asyncio`) do Python 3.12. Este guia estabelece os padroes e praticas de engenharia obrigatorias para manter o sistema responsivo, resiliente e livre de deadlocks.

---

## 1. Anatomia do JarvisDaemon

No arquivo `core/main.py`, o daemon orquestra multiplos subsistemas simultaneos sem bloquear a thread principal:

```python
async def start(self):
    server_coro = self.server.start()
    metrics_task = asyncio.create_task(self._system_metrics_loop())
    voice_task = asyncio.create_task(self.voice.start_listening())
    
    await asyncio.gather(
        server_coro,
        metrics_task,
        voice_task,
        return_exceptions=True
    )
```

### Regras de Ciclo de Vida:
- **Never `asyncio.run()`**: Nunca invoque `asyncio.run()` dentro de metodos do daemon ou coroutines ja ativas.
- **Task Ownership**: Guarde referencias de tasks de longa duracao em atributos de instancia para evitar coleta prematura pelo Garbage Collector.
- **Callback Cleanup**: Remova a referencia da task em seu `done_callback`:
  ```python
  task = asyncio.create_task(coro)
  self._tasks.add(task)
  task.add_done_callback(self._tasks.discard)
  ```

---

## 2. Broadcast Seguro em WebSockets

Ao emitir eventos para multiplos clientes (HUD Electron, dashboards, etc.), sockets instaveis nao podem derrubar o servidor:

```python
async def broadcast(self, event: WSEvent):
    if not self.clients:
        return
    message = event.model_dump_json()
    disconnected = set()
    
    for client in list(self.clients):
        if client.closed:
            disconnected.add(client)
            continue
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(client)
        except Exception as e:
            logger.error(f"Erro ao enviar para cliente: {e}")
            disconnected.add(client)
            
    if disconnected:
        self.clients.difference_update(disconnected)
```

---

## 3. Approval Gates com `asyncio.Future`

O subsistema de governanca (`core/governance/interceptor.py`) suspende a execucao de comandos criticos aguardando aprovacao humana no HUD:

```python
class SafetyInterceptor:
    def __init__(self, broadcast_fn):
        self._pending_tickets: dict[str, asyncio.Future] = {}
        self.broadcast_fn = broadcast_fn

    async def guard_command(self, command: str) -> bool:
        risk, reason = GovernancePolicy.evaluate_command(command)
        if risk == RiskLevel.SAFE:
            return True
            
        loop = asyncio.get_running_loop()
        ticket_id = str(uuid.uuid4())
        future = loop.create_future()
        self._pending_tickets[ticket_id] = future
        
        await self.broadcast_fn(EventType.SAFETY_APPROVAL_REQUEST, {
            "ticket_id": ticket_id,
            "command": command,
            "reason": reason
        })
        
        try:
            approved = await asyncio.wait_for(future, timeout=60.0)
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"Ticket {ticket_id} expirou por inatividade.")
            return False
        finally:
            self._pending_tickets.pop(ticket_id, None)

    def resolve_ticket(self, ticket_id: str, approved: bool):
        future = self._pending_tickets.get(ticket_id)
        if future and not future.done():
            future.set_result(approved)
```

---

## 4. Integracao de Chamadas Bloqueantes (Win32, Pyperclip, I/O)

Chamadas nativas do Windows (`ctypes`, `winsound`, `pyperclip`, subprocessos sincronos) bloqueiam o Event Loop se executadas diretamente.

### Padrao Correto: Executor ThreadPool
```python
loop = asyncio.get_running_loop()

# Exemplo 1: Leitura de Clipboard via Pyperclip
content = await loop.run_in_executor(None, ClipboardManager.get_text, 8000)

# Exemplo 2: Beep sincrono do sistema
await loop.run_in_executor(None, winsound.Beep, 1000, 150)
```

---

## 5. Orquestracao com `asyncio.gather` Resiliente

Ao executar perfis de workspace (`WorkspaceOrchestrator`), multiplos programas sao abertos paralelamente:

```python
tasks = [
    self._launch_app(app_name)
    for app_name in profile.apps
]

results = await asyncio.gather(*tasks, return_exceptions=True)

for app_name, result in zip(profile.apps, results):
    if isinstance(result, Exception):
        logger.error(f"Falha ao iniciar {app_name}: {result}")
```

---

## 6. Barge-in de Audio e Interrupcao Instantanea

O pipeline de voz (`core/brain/voice_io.py`) deve interromper a fala do assistente no momento em que o microfone detectar voz humana:

```python
def on_user_speech_detected(self):
    try:
        import sounddevice as sd
        sd.stop()
    except Exception as e:
        logger.error(f"Erro ao parar audio de saida: {e}")
        
    asyncio.run_coroutine_threadsafe(
        self.broadcast_state(AgentState.LISTENING),
        self.loop
    )
```

---

## 7. Checklist para Novos Modulos Core

1. [ ] Todas as chamadas de rede/I/O utilizam `async/await`?
2. [ ] Metodos sincronos pesados ou Win32 rodam em `run_in_executor`?
3. [ ] Nao ha nenhum `time.sleep()` (use sempre `asyncio.sleep()`)?
4. [ ] O encerramento de conexoes/recursos e tratado no bloco `finally`?
5. [ ] Exceptions em tasks concorrentes sao capturadas e logadas?
