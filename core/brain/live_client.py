import asyncio
import logging
import re
from typing import Optional, Callable, Dict, Any
from google import genai
from google.genai import types
from core.config import config
from core.brain.prompts import JARVIS_SYSTEM_INSTRUCTION
from core.obsidian.vault_manager import ObsidianVaultManager
from core.obsidian.journal import JournalManager
from core.obsidian.rag import VaultRAG
from core.engineering.git_assistant import GitAssistant
from core.engineering.diff_engine import DiffEngine
from core.engineering.runner import TestAndLintRunner
from core.engineering.docker_manager import DockerManager
from core.obsidian.sop_manager import SOPManager
from core.governance.interceptor import SafetyInterceptor
from core.system.focus_manager import FocusManager
from core.system.audio_controller import AudioFeedback
from core.system.app_launcher import AppLauncher
from core.system.workspace_orchestrator import WorkspaceOrchestrator
from core.system.clipboard_manager import ClipboardManager

logger = logging.getLogger("GeminiBrain")

class GeminiBrain:
    def __init__(
        self,
        vault: ObsidianVaultManager,
        journal: JournalManager,
        rag: VaultRAG,
        git: GitAssistant,
        focus: FocusManager,
        interceptor: SafetyInterceptor,
        broadcast_fn: Optional[Callable[[Any, dict], Any]] = None,
        orchestrator: Optional[WorkspaceOrchestrator] = None,
        docker: Optional[DockerManager] = None,
        sop_manager: Optional[SOPManager] = None,
    ):
        self.vault = vault
        self.journal = journal
        self.rag = rag
        self.git = git
        self.focus = focus
        self.interceptor = interceptor
        self.broadcast_fn = broadcast_fn
        self.orchestrator = orchestrator or WorkspaceOrchestrator(
            focus_manager=self.focus,
            journal_manager=self.journal
        )
        self.docker = docker or DockerManager(interceptor=self.interceptor)
        self.sop_manager = sop_manager or SOPManager(
            vault=self.vault,
            interceptor=self.interceptor,
            workspace_root=self.git.workspace_root
        )

        self.client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self):
        key = config.gemini_api_key
        if key:
            try:
                self.client = genai.Client(api_key=key)
                logger.info("Cliente Google GenAI inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente GenAI: {e}")
        else:
            logger.warning("Nenhuma chave GEMINI_API_KEY configurada no .env ainda.")

    async def process_user_intent(self, text: str) -> Dict[str, Any]:
        """Processa comando de texto ou fala transcrita, executando as ferramentas apropriadas."""
        text_lower = text.lower().strip()

        # 1. Orquestração de Workspaces e Modos de Foco (dev, study, deep_work, rest)
        workspace_triggers = {
            "dev": ["hora de codar", "modo dev", "modo programação", "vamos programar", "iniciar dev", "workspace dev"],
            "study": ["modo estudo", "hora de estudar", "modo pesquisa", "workspace study", "workspace estudo"],
            "deep_work": ["modo deep work", "foco total", "foco profundo", "modo foco total"],
            "rest": ["hora de descansar", "modo descanso", "modo rest", "encerrar expediente", "modo pausa", "hora de relaxar"],
        }
        for target_mode, triggers in workspace_triggers.items():
            if any(trig in text_lower for trig in triggers):
                res = await self.orchestrator.activate_workspace(target_mode)
                return {"reply": res.get("reply", "Ambiente configurado com sucesso, senhor.")}

        # Regex flexível para comandos como "ativar modo dev", "definir workspace study", etc.
        ws_match = re.search(r"(?:ativar|iniciar|definir|set|mudar para|entrar no)\s+(?:o\s+)?(?:workspace|modo)\s+([a-zA-Z_]+)", text_lower)
        if ws_match:
            res = await self.orchestrator.activate_workspace(ws_match.group(1))
            return {"reply": res.get("reply", "Ambiente configurado, senhor.")}

        # 2. Checa comandos rápidos de Deep Work
        if "deep work" in text_lower or "modo foco" in text_lower:
            if "iniciar" in text_lower or "começar" in text_lower:
                res = self.focus.start_deep_work(60, "Foco do Usuário")
                AudioFeedback.play_activation()
                return {"reply": "Modo Deep Work ativado por 60 minutos, senhor. Notificações silenciadas e cronômetro iniciado no HUD."}
            elif "parar" in text_lower or "encerrar" in text_lower:
                res = self.focus.stop_deep_work()
                self.journal.append_deep_work_session(res.get("elapsed_minutes", 0), res.get("project", "Geral"))
                return {"reply": f"Sessão de Deep Work finalizada. Registrei {res.get('elapsed_minutes', 0)} minutos na sua Daily Note do Obsidian."}

        # 3. Checa comandos de Daily Note / Rotina
        if "daily note" in text_lower or "diário" in text_lower or "agenda do dia" in text_lower:
            note_path = self.journal.get_or_create_daily_note()
            return {"reply": f"Sua Daily Note foi gerada e atualizada no Obsidian: {note_path.name}"}

        # 3.01 Fechamento Noturno do Diário (Atalho Rápido)
        if any(trig in text_lower for trig in ["fechar o dia", "encerrar o dia", "fechar diário", "fechar diario", "retrospectiva do dia"]):
            close_res = self.journal.close_daily_journal()
            return {"reply": close_res.get("reply", "Dia consolidado com sucesso, senhor.")}

        # 3.1 Atalho direto para captura na Inbox (economia de tokens)
        inbox_match = re.search(r"(?:anote|anota|salve|salva|adicionar?)\s+(?:na\s+|a\s+|no\s+)?(?:inbox|caixa de entrada)[:\s]+(.+)", text_lower)
        if inbox_match:
            raw_content = inbox_match.group(1).strip()
            entry_type = "task" if any(raw_content.startswith(w) for w in ["tarefa", "fazer", "comprar", "corrigir", "implementar"]) else "thought"
            res = self.vault.capture_to_inbox(content=raw_content, entry_type=entry_type)
            return {"reply": res.get("reply", "Anotado na sua Inbox, senhor.")}

        # 3.2 Atalhos rápidos para Docker e Infraestrutura (economia de tokens)
        if any(trig in text_lower for trig in [
            "como estão os containers", "como estao os containers", "status dos containers",
            "o docker tá rodando", "o docker ta rodando", "status do docker", "verificar containers"
        ]):
            d_res = self.docker.inspect_services()
            return {"reply": d_res.get("reply", "Status dos containers verificado, senhor.")}

        if any(trig in text_lower for trig in ["status do postgres", "status do banco de dados", "status do banco"]):
            h_res = self.docker.check_health("postgres")
            return {"reply": h_res.get("reply", "Verificação do banco de dados concluída, senhor.")}

        if "status do redis" in text_lower:
            h_res = self.docker.check_health("redis")
            return {"reply": h_res.get("reply", "Verificação do Redis concluída, senhor.")}

        # 3.3 Atalhos rápidos para SOPs e Workflows (economia de tokens)
        if any(trig in text_lower for trig in [
            "quais procedimentos você conhece", "quais procedimentos voce conhece",
            "quais sops", "listar sops", "o que você pode automatizar", "o que voce pode automatizar",
            "quais workflows", "listar workflows"
        ]):
            sop_res = self.sop_manager.list_sops()
            return {"reply": sop_res.get("reply", "Procedimentos listados com sucesso, senhor.")}

        sop_exec_match = re.search(r"(?:executar|rodar|iniciar|rodar o|executar o)\s+(?:procedimento|sop|workflow)\s+([a-zA-Z0-9_-]+)", text_lower)
        if sop_exec_match:
            sop_target = sop_exec_match.group(1)
            dry_run = "simular" in text_lower or "dry run" in text_lower
            res = await self.sop_manager.execute_sop(sop_target, dry_run=dry_run)
            return {"reply": res.get("reply", "Execução de procedimento finalizada, senhor.")}

        # 4. Comandos de Abertura de Aplicativos e Mídia (Spotify, VS Code, Obsidian, etc.)
        if "spotify" in text_lower or ("abrir" in text_lower and "música" in text_lower):
            AppLauncher.launch_spotify()
            AudioFeedback.play_activation()
            return {"reply": "Spotify inicializado com sucesso, senhor."}

        if "pausar música" in text_lower or "pausar spotify" in text_lower or text_lower == "pausar":
            AppLauncher.media_play_pause()
            return {"reply": "Música pausada, senhor."}

        if "despausar" in text_lower or "tocar música" in text_lower or "play música" in text_lower:
            AppLauncher.media_play_pause()
            return {"reply": "Retomando reprodução musical, senhor."}

        if "próxima música" in text_lower or "pular música" in text_lower or "passar música" in text_lower:
            AppLauncher.media_next()
            return {"reply": "Avançando para a próxima faixa, senhor."}

        if "música anterior" in text_lower or "voltar música" in text_lower:
            AppLauncher.media_previous()
            return {"reply": "Voltando para a faixa anterior."}

        if "abrir obsidian" in text_lower:
            AppLauncher.launch_obsidian(str(config.obsidian_vault_path))
            AudioFeedback.play_activation()
            return {"reply": "Cofre do Obsidian aberto com sucesso, senhor."}

        if "abrir vs code" in text_lower or "abrir vscode" in text_lower or "abrir código" in text_lower:
            AppLauncher.launch_vscode()
            AudioFeedback.play_activation()
            return {"reply": "VS Code aberto no seu workspace, senhor."}

        if "abrir navegador" in text_lower or "abrir chrome" in text_lower or "abrir edge" in text_lower or "abrir google" in text_lower:
            AppLauncher.launch_browser()
            AudioFeedback.play_activation()
            return {"reply": "Navegador de internet aberto, senhor."}

        if "aumentar volume" in text_lower or "mais alto" in text_lower:
            for _ in range(4):
                AppLauncher.volume_up()
            return {"reply": "Volume do sistema aumentado, senhor."}

        if "abaixar volume" in text_lower or "diminuir volume" in text_lower or "mais baixo" in text_lower:
            for _ in range(4):
                AppLauncher.volume_down()
            return {"reply": "Volume do sistema reduzido, senhor."}

        # 5. Comandos de Clipboard — leitura direta (sem roundtrip ao Gemini)
        clipboard_read_triggers = [
            "analisa esse erro", "analisa isso", "o que quebrou", "o que e isso",
            "converte o que copiei", "da uma olhada nisso", "analisa o que copiei",
            "veja o que copiei", "veja isso", "debug isso",
        ]
        if any(trig in text_lower for trig in clipboard_read_triggers):
            clip = ClipboardManager.get_text()
            if not clip:
                return {"reply": "A area de transferencia esta vazia ou nao possui conteudo de texto, senhor."}
            # Injeta o clipboard no prompt enviado ao Gemini (continua para o bloco abaixo)
            text = f"{text}\n\n[CONTEUDO DO CLIPBOARD DO USUARIO]:\n{clip}"
            text_lower = text.lower()

        # 6. Comandos de Clipboard — escrita (copiar resultado gerado)
        clipboard_write_triggers = [
            "copia o resultado", "copia o codigo", "cole o resultado",
            "coloca no clipboard", "copia isso para o clipboard",
        ]
        if any(trig in text_lower for trig in clipboard_write_triggers):
            # Será tratado pela tool function no bloco Gemini abaixo
            pass

        # 6.1 Comandos de Git e Testes — atalhos diretos determinísticos (0 Tokens)
        if text_lower in ["git status", "status do git", "verificar git", "o que foi alterado", "quais arquivos foram modificados"]:
            res = self.git.inspect("status")
            return {"reply": res.get("reply", "Status verificado, senhor.")}

        if text_lower in ["rodar testes", "executar testes", "rodar os testes", "execute os testes", "rodar pytest", "executar pytest"]:
            test_res = await TestAndLintRunner.run_tests_with_summary(cwd=self.git.workspace_root)
            return {"reply": test_res.get("reply", "Suíte de testes concluída.")}

        # 7. Se temos o cliente Gemini configurado, consultamos com o contexto vivo do Obsidian
        if self.client:
            # Monta contexto do RAG
            rag_context = self.rag.build_system_context()
            search_results = self.rag.search_context(text, limit=3)
            rag_snippets = "\n".join(f"- {r['title']}: {r['snippet']}" for r in search_results)

            system_prompt = f"""{JARVIS_SYSTEM_INSTRUCTION}

### Contexto Atual do Obsidian (RAG):
{rag_context}

Notas Relevantes Encontradas:
{rag_snippets}
"""

            def activate_workspace(mode: str) -> str:
                """Ativa e orquestra um ambiente de trabalho completo com multiplos aplicativos e configuracoes de foco.

                Args:
                    mode: O modo desejado: 'dev' (programacao), 'study' (estudo/Obsidian), 'deep_work' (foco total), ou 'rest' (descanso).
                """
                return f"Workspace '{mode}' ativado."

            def get_clipboard_content(max_length: int = 8000) -> str:
                """Le o conteudo de texto atual da area de transferencia do sistema operacional para analise ou conversao.

                Use quando o usuario disser: 'analisa esse erro', 'o que quebrou aqui?',
                'converte o que copiei', 'da uma olhada nisso', 'debug isso', 'analisa o clipboard'.

                Args:
                    max_length: Numero maximo de caracteres a retornar (padrao 8000).

                Returns:
                    O conteudo textual do clipboard, ou mensagem de erro se vazio.
                """
                content = ClipboardManager.get_text(max_length=max_length)
                if content is None:
                    return "CLIPBOARD_VAZIO: A area de transferencia esta vazia ou nao possui conteudo textual."
                return content

            def set_clipboard_content(text: str) -> str:
                """Escreve texto na area de transferencia do sistema operacional.

                Use quando gerar codigo formatado, converter dados (JSON para TypeScript, SQL, etc.)
                ou quando o usuario pedir 'copia o resultado', 'cole no clipboard', 'copia o codigo'.

                Args:
                    text: Conteudo a ser copiado para o clipboard.

                Returns:
                    Confirmacao de sucesso ou mensagem de erro.
                """
                success = ClipboardManager.set_text(text)
                if success:
                    return f"CLIPBOARD_ATUALIZADO: {len(text)} caracteres copiados para a area de transferencia."
                return "CLIPBOARD_ERRO: Falha ao escrever na area de transferencia."

            def capture_to_inbox(content: str, type: str = "thought", tags: Optional[list] = None) -> str:
                """Registra notas rapidas, tarefas ou ideias diretamente em Human/Inbox/Inbox.md no Obsidian.

                Chame esta ferramenta quando o usuario disser:
                'Jarvis, anote na inbox...', 'lembrete rapido...', 'registre a ideia...',
                'anota isso...', 'salve na minha inbox...', 'crie uma tarefa para...', 'anotar na inbox'.

                Args:
                    content: O conteudo principal da nota, ideia ou tarefa capturada.
                    type: O tipo da entrada: 'task' (afazeres/acoes), 'thought' (ideias/reflexoes) ou 'reference' (links/consultas).
                    tags: Lista de tags semanticas inferidas (ex: ['#backend', '#ideia', '#tarefa']).

                Returns:
                    Confirmacao de sucesso ou status do registro.
                """
                res = self.vault.capture_to_inbox(content=content, entry_type=type, tags=tags)
                return res.get("reply", "Anotado na sua Inbox, senhor.")

            def git_inspect(mode: str = "status") -> str:
                """Inspeciona o estado do repositorio Git no workspace ativo.

                Use quando o usuario perguntar: 'o que foi alterado?', 'verifique o git',
                'quais arquivos foram modificados?', 'mostre o diff', 'ultimos commits'.

                Args:
                    mode: O modo de inspecao: 'status' (arquivos alterados/staged),
                          'diff' (modificacoes no codigo), ou 'recent_commits' (ultimos commits).

                Returns:
                    Saida formatada da inspecao Git.
                """
                res = self.git.inspect(mode)
                return res.get("reply", res.get("output", "Inspecao Git concluida."))

            def git_smart_commit(message: Optional[str] = None, stage_all: bool = True) -> str:
                """Prepara e executa um commit semantico no padrao Conventional Commits.

                Requer aprovacao previa no HUD pelo SafetyInterceptor antes de efetivar.

                Args:
                    message: Mensagem inferida no formato Conventional Commits (ex: 'feat(auth): add jwt middleware'). Se omitida, gerada automaticamente do diff.
                    stage_all: Se True, executa git add -A antes do commit.

                Returns:
                    Status do commit ou aviso de cancelamento.
                """
                return f"PROPOSAL_COMMIT: message='{message}', stage_all={stage_all}"

            def git_push_safe(remote: str = "origin", branch: Optional[str] = None) -> str:
                """Envia os commits para o repositorio remoto com trava de seguranca critica e confirmacao no HUD.

                Args:
                    remote: Nome do remoto (padrao 'origin').
                    branch: Nome da branch alvo (opcional).

                Returns:
                    Resultado do envio ou aviso de cancelamento.
                """
                return f"PROPOSAL_PUSH: remote='{remote}', branch='{branch}'"

            def run_workspace_tests(command: Optional[str] = None) -> str:
                """Executa a suite de testes locais do workspace ativo (pytest, npm test, etc.).

                Args:
                    command: Comando customizado de teste (opcional). Se omitido, autodetectado.

                Returns:
                    Resumo executivo dos testes indicando passed/failed.
                """
                return f"PROPOSAL_TEST: command='{command}'"

            def setup_daily_journal(priorities: list[str], time_blocks: Optional[list] = None) -> str:
                """Estrutura ou atualiza a Daily Note do dia (Human/Journal/YYYY-MM-DD.md).

                Importa tarefas pendentes de ontem e da Inbox, define prioridades e blocos de tempo.
                Use quando o usuario disser: 'planejar meu dia', 'iniciar diario', 'preparar daily note',
                'definir metas de hoje', 'rotina matinal'.

                Args:
                    priorities: 1 a 3 metas/focos principais para o dia (obrigatorio).
                    time_blocks: Lista opcional de blocos [{ "time": "09:00 - 11:00", "task": "..." }].

                Returns:
                    Confirmacao da criacao ou atualizacao da Daily Note.
                """
                res = self.journal.setup_daily_journal(priorities=priorities, time_blocks=time_blocks)
                return res.get("reply", "Daily Note estruturada com sucesso, senhor.")

            def close_daily_journal(reflection: Optional[str] = None, energy_rating: Optional[int] = None) -> str:
                """Consolida o encerramento do dia na Daily Note atual (retrospectiva noturna).

                Calcula tarefas concluidas vs pendentes, commits realizados e registra reflexoes.
                Use quando o usuario disser: 'fechar o dia', 'encerrar o dia', 'retrospectiva noturna',
                'finalizar diario', 'como foi meu dia hoje?'.

                Args:
                    reflection: Reflexao rapida ou resumo do dia ditado pelo usuario.
                    energy_rating: Avaliacao de foco/energia/produtividade de 1 a 5.

                Returns:
                    Sintese executiva do dia e status de fechamento.
                """
                res = self.journal.close_daily_journal(reflection=reflection, energy_rating=energy_rating)
                return res.get("reply", "Dia consolidado com sucesso, senhor.")

            def docker_inspect_services(all: bool = False) -> str:
                """Inspeciona containers Docker em execucao ou todos os containers do sistema.

                Use quando o usuario perguntar: 'como estao os containers?', 'status do banco de dados',
                'o docker ta rodando?', 'quais containers estao ativos?'.

                Args:
                    all: Se True, lista todos os containers incluindo parados/inativos. Padrao False.

                Returns:
                    Relatorio consolidado dos containers com nomes, status, portas e uptime.
                """
                res = self.docker.inspect_services(all_containers=all)
                return res.get("reply", "Inspecao de containers concluida, senhor.")

            def docker_manage_service(action: str, target: Optional[str] = None, compose_file: Optional[str] = None) -> str:
                """Inicia, para ou reinicia servicos de infraestrutura e containers Docker.

                Args:
                    action: Acao a executar ('start', 'stop', 'restart').
                    target: Nome do container ou servico compose (ou 'all').
                    compose_file: Caminho relativo para o docker-compose.yml (opcional).

                Returns:
                    Resultado da acao nos servicos.
                """
                res = self.docker.manage_service(action=action, target=target, compose_file=compose_file)
                return res.get("reply", "Comando de gerenciamento Docker processado, senhor.")

            def docker_destructive_operation(action: str, target: Optional[str] = None) -> str:
                """Executa operacoes destrutivas no Docker com perda de estado (down com volumes, prune, rm).

                Trava de seguranca critica obrigatoria: exige autorizacao previa do usuario no HUD.

                Args:
                    action: 'down_volumes' (apaga volumes locais), 'prune_system' (limpeza geral) ou 'remove_container' (exclui container).
                    target: Nome do container para remocao (obrigatorio se action for 'remove_container').

                Returns:
                    Resultado da operacao autorizada ou aviso de cancelamento.
                """
                return f"PROPOSAL_DOCKER_DESTRUCTIVE: action='{action}', target='{target}'"

            def check_service_health(target: str = "postgres", port: Optional[int] = None, endpoint: Optional[str] = None) -> str:
                """Verifica a integridade e conectividade de servicos locais (PostgreSQL, Redis, APIs) via TCP ou HTTP.

                Args:
                    target: Servico a verificar ('postgres', 'redis', 'api' ou 'custom').
                    port: Porta TCP customizada (opcional).
                    endpoint: URL ou rota HTTP para teste GET (ex: 'http://localhost:3000/health').

                Returns:
                    Status de saude, latencia em ms e diagnostico de conectividade.
                """
                res = self.docker.check_health(target=target, port=port, endpoint=endpoint)
                return res.get("reply", "Verificacao de integridade concluida, senhor.")

            def list_available_sops(category: Optional[str] = None, query: Optional[str] = None) -> str:
                """Lista os Procedimentos Operacionais Padrao (SOPs) e Workflows disponiveis no cofre do Obsidian.

                Use quando o usuario perguntar: 'quais procedimentos voce conhece?',
                'o que voce pode automatizar?', 'listar sops', ou antes de sugerir automacoes.

                Args:
                    category: Filtrar por categoria (opcional, ex: 'maintenance', 'engineering').
                    query: Termo de busca no titulo, descricao ou tags (opcional).

                Returns:
                    Catalogo consolidado de procedimentos disponiveis.
                """
                res = self.sop_manager.list_sops(category=category, query=query)
                return res.get("reply", "Consulta de SOPs concluida, senhor.")

            def execute_sop(sop_name: str, dry_run: bool = False) -> str:
                """Interpreta e executa sequencialmente os passos de um SOP ou Workflow da pasta Machine/.

                Respeita a governanca: comandos de alto risco pausam para confirmacao no HUD.
                Registra auditoria detalhada em Machine/Logs/YYYY-MM-DD-sop-runs.md.

                Args:
                    sop_name: Nome do arquivo ou identificador do SOP (ex: 'limpeza-ambiente', 'setup-novo-projeto').
                    dry_run: Se True, apenas simula os passos sem executar comandos reais. Padrao False.

                Returns:
                    Status da execucao, passos validados e caminho do log gerado.
                """
                return f"PROPOSAL_EXECUTE_SOP: sop_name='{sop_name}', dry_run={dry_run}"

            # Cascata de modelos para contingencia contra picos de demanda (503 UNAVAILABLE)
            candidate_models = [config.gemini_model, "gemini-2.5-flash", "gemini-2.5-pro", "gemini-pro-latest"]
            candidate_models = list(dict.fromkeys(candidate_models))

            available_tools = [
                activate_workspace,
                get_clipboard_content,
                set_clipboard_content,
                capture_to_inbox,
                git_inspect,
                git_smart_commit,
                git_push_safe,
                run_workspace_tests,
                setup_daily_journal,
                close_daily_journal,
                docker_inspect_services,
                docker_manage_service,
                docker_destructive_operation,
                check_service_health,
                list_available_sops,
                execute_sop,
            ]

            last_error = None
            for model_name in candidate_models:
                for attempt in range(2): # Tenta ate 2 vezes cada modelo
                    try:
                        logger.info(f"Enviando prompt ao Gemini com modelo '{model_name}' (tentativa {attempt + 1})...")
                        response = self.client.models.generate_content(
                            model=model_name,
                            contents=text,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                temperature=0.7,
                                tools=available_tools,
                            )
                        )
                        # Despacha function calls
                        if response.function_calls:
                            for call in response.function_calls:
                                if call.name == "activate_workspace":
                                    target_mode = call.args.get("mode", "dev")
                                    ws_res = await self.orchestrator.activate_workspace(target_mode)
                                    return {"reply": ws_res.get("reply", "Ambiente configurado, senhor.")}

                                elif call.name == "get_clipboard_content":
                                    max_len = int(call.args.get("max_length", 8000))
                                    clip_result = get_clipboard_content(max_len)
                                    follow_up = self.client.models.generate_content(
                                        model=model_name,
                                        contents=f"{text}\n\n[CLIPBOARD]:\n{clip_result}",
                                        config=types.GenerateContentConfig(
                                            system_instruction=system_prompt,
                                            temperature=0.7,
                                            tools=[set_clipboard_content],
                                        )
                                    )
                                    if follow_up.function_calls:
                                        for f_call in follow_up.function_calls:
                                            if f_call.name == "set_clipboard_content":
                                                text_copied = f_call.args.get("text", "")
                                                set_clipboard_content(text_copied)
                                                return {
                                                    "reply": follow_up.text or "Conteudo convertido e copiado para sua area de transferencia, senhor."
                                                }
                                    return {"reply": follow_up.text or "Analise concluida, senhor."}

                                elif call.name == "set_clipboard_content":
                                    content_to_copy = call.args.get("text", "")
                                    copy_result = set_clipboard_content(content_to_copy)
                                    logger.info(copy_result)
                                    return {
                                        "reply": "Conteudo gerado e copiado para a sua area de transferencia, senhor. Pode colar onde desejar."
                                    }

                                elif call.name == "capture_to_inbox":
                                    c_content = call.args.get("content", "")
                                    c_type = call.args.get("type", "thought")
                                    c_tags = call.args.get("tags", [])
                                    inbox_res = self.vault.capture_to_inbox(
                                        content=c_content,
                                        entry_type=c_type,
                                        tags=c_tags
                                    )
                                    return {"reply": inbox_res.get("reply", "Anotado na sua Inbox, senhor.")}

                                elif call.name == "git_inspect":
                                    insp_mode = call.args.get("mode", "status")
                                    git_res = self.git.inspect(insp_mode)
                                    return {"reply": git_res.get("reply", git_res.get("output", "Inspecao Git concluida."))}

                                elif call.name == "git_smart_commit":
                                    msg = call.args.get("message")
                                    stage = bool(call.args.get("stage_all", True))
                                    commit_res = await self.git.commit(message=msg, stage_all=stage, require_approval=True)
                                    return {"reply": commit_res.get("reply", commit_res.get("output", "Commit processado."))}

                                elif call.name == "git_push_safe":
                                    rem = call.args.get("remote", "origin")
                                    br = call.args.get("branch")
                                    push_res = await self.git.push(remote=rem, branch=br)
                                    return {"reply": push_res.get("reply", push_res.get("output", "Push processado."))}

                                elif call.name == "run_workspace_tests":
                                    cmd_override = call.args.get("command")
                                    test_res = await TestAndLintRunner.run_tests_with_summary(
                                        cmd=cmd_override,
                                        cwd=self.git.workspace_root
                                    )
                                    return {"reply": test_res.get("reply", "Execucao de testes finalizada.")}

                                elif call.name == "setup_daily_journal":
                                    prio = call.args.get("priorities", ["Foco geral"])
                                    t_blocks = call.args.get("time_blocks")
                                    journal_res = self.journal.setup_daily_journal(priorities=prio, time_blocks=t_blocks)
                                    return {"reply": journal_res.get("reply", "Daily Note configurada, senhor.")}

                                elif call.name == "close_daily_journal":
                                    refl = call.args.get("reflection")
                                    rating = call.args.get("energy_rating")
                                    if rating is not None:
                                        try:
                                            rating = int(rating)
                                        except Exception:
                                            rating = None
                                    close_res = self.journal.close_daily_journal(reflection=refl, energy_rating=rating)
                                    return {"reply": close_res.get("reply", "Dia consolidado, senhor.")}

                                elif call.name == "docker_inspect_services":
                                    all_c = bool(call.args.get("all", False))
                                    d_res = self.docker.inspect_services(all_containers=all_c)
                                    return {"reply": d_res.get("reply", "Inspecao de containers concluida, senhor.")}

                                elif call.name == "docker_manage_service":
                                    act = call.args.get("action", "start")
                                    tgt = call.args.get("target")
                                    c_file = call.args.get("compose_file")
                                    m_res = self.docker.manage_service(action=act, target=tgt, compose_file=c_file)
                                    return {"reply": m_res.get("reply", "Comando de gerenciamento processado, senhor.")}

                                elif call.name == "docker_destructive_operation":
                                    act = call.args.get("action", "")
                                    tgt = call.args.get("target")
                                    dest_res = await self.docker.destructive_operation(action=act, target=tgt)
                                    return {"reply": dest_res.get("reply", "Operacao destrutiva processada.")}

                                elif call.name == "check_service_health":
                                    tgt = call.args.get("target", "postgres")
                                    p = call.args.get("port")
                                    if p is not None:
                                        try:
                                            p = int(p)
                                        except Exception:
                                            p = None
                                    ep = call.args.get("endpoint")
                                    h_res = self.docker.check_health(target=tgt, port=p, endpoint=ep)
                                    return {"reply": h_res.get("reply", "Verificacao de integridade concluida, senhor.")}

                                elif call.name == "list_available_sops":
                                    cat = call.args.get("category")
                                    q = call.args.get("query")
                                    sop_list_res = self.sop_manager.list_sops(category=cat, query=q)
                                    return {"reply": sop_list_res.get("reply", "Procedimentos listados com sucesso, senhor.")}

                                elif call.name == "execute_sop":
                                    s_name = call.args.get("sop_name", "")
                                    d_run = bool(call.args.get("dry_run", False))
                                    sop_run_res = await self.sop_manager.execute_sop(sop_name=s_name, dry_run=d_run)
                                    return {"reply": sop_run_res.get("reply", "Execução do procedimento concluída, senhor.")}

                        reply_text = response.text or "Comando recebido, senhor."
                        return {"reply": reply_text}
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        logger.warning(f"Oscilacao no modelo '{model_name}' (tentativa {attempt + 1}): {err_str[:120]}")
                        if "503" in err_str or "demand" in err_str.lower() or "429" in err_str:
                            await asyncio.sleep(1.0)
                        else:
                            break

            logger.error(f"Todos os modelos da cascata falharam. Ultimo erro: {last_error}")
            return {
                "reply": "Perdao, senhor. Os servidores do Gemini estao enfrentando um pico atipico de alta demanda no momento. Recomendo aguardar alguns instantes e repetir a instrucao."
            }

        # Resposta de fallback quando aguardando insercao da API Key
        return {
            "reply": f"J.A.R.V.I.S online e operacional. Chave do Gemini aguardando configuracao no arquivo .env."
        }
