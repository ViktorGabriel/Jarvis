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

        # 3.1 Atalho direto para captura na Inbox (economia de tokens)
        inbox_match = re.search(r"(?:anote|anota|salve|salva|adicionar?)\s+(?:na\s+|a\s+|no\s+)?(?:inbox|caixa de entrada)[:\s]+(.+)", text_lower)
        if inbox_match:
            raw_content = inbox_match.group(1).strip()
            entry_type = "task" if any(raw_content.startswith(w) for w in ["tarefa", "fazer", "comprar", "corrigir", "implementar"]) else "thought"
            res = self.vault.capture_to_inbox(content=raw_content, entry_type=entry_type)
            return {"reply": res.get("reply", "Anotado na sua Inbox, senhor.")}

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

            # Cascata de modelos para contingencia contra picos de demanda (503 UNAVAILABLE)
            candidate_models = [config.gemini_model, "gemini-2.5-flash", "gemini-2.5-pro", "gemini-pro-latest"]
            candidate_models = list(dict.fromkeys(candidate_models))

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
                                tools=[activate_workspace, get_clipboard_content, set_clipboard_content, capture_to_inbox],
                            )
                        )
                        # Despacha function calls (activate_workspace, get_clipboard_content, set_clipboard_content, capture_to_inbox)
                        if response.function_calls:
                            for call in response.function_calls:
                                if call.name == "activate_workspace":
                                    target_mode = call.args.get("mode", "dev")
                                    ws_res = await self.orchestrator.activate_workspace(target_mode)
                                    return {"reply": ws_res.get("reply", "Ambiente configurado, senhor.")}

                                elif call.name == "get_clipboard_content":
                                    max_len = int(call.args.get("max_length", 8000))
                                    clip_result = get_clipboard_content(max_len)
                                    # Reenvia ao Gemini com o conteudo do clipboard para analise ou conversao
                                    follow_up = self.client.models.generate_content(
                                        model=model_name,
                                        contents=f"{text}\n\n[CLIPBOARD]:\n{clip_result}",
                                        config=types.GenerateContentConfig(
                                            system_instruction=system_prompt,
                                            temperature=0.7,
                                            tools=[set_clipboard_content],
                                        )
                                    )
                                    # Se a resposta do follow-up pediu para copiar dados convertidos
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
