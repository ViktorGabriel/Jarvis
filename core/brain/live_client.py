import asyncio
import logging
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
        broadcast_fn: Optional[Callable[[Any, dict], Any]] = None
    ):
        self.vault = vault
        self.journal = journal
        self.rag = rag
        self.git = git
        self.focus = focus
        self.interceptor = interceptor
        self.broadcast_fn = broadcast_fn

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

        # 1. Checa comandos rápidos de Deep Work
        if "deep work" in text_lower or "modo foco" in text_lower:
            if "iniciar" in text_lower or "começar" in text_lower:
                res = self.focus.start_deep_work(60, "Foco do Usuário")
                AudioFeedback.play_activation()
                return {"reply": "Modo Deep Work ativado por 60 minutos, senhor. Notificações silenciadas e cronômetro iniciado no HUD."}
            elif "parar" in text_lower or "encerrar" in text_lower:
                res = self.focus.stop_deep_work()
                self.journal.append_deep_work_session(res.get("elapsed_minutes", 0), res.get("project", "Geral"))
                return {"reply": f"Sessão de Deep Work finalizada. Registrei {res.get('elapsed_minutes', 0)} minutos na sua Daily Note do Obsidian."}

        # 2. Checa comandos de Daily Note / Rotina
        if "daily note" in text_lower or "diário" in text_lower or "agenda do dia" in text_lower:
            note_path = self.journal.get_or_create_daily_note()
            return {"reply": f"Sua Daily Note foi gerada e atualizada no Obsidian: {note_path.name}"}

        # 3. Se temos o cliente Gemini configurado, consultamos com o contexto vivo do Obsidian
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

            # Cascata de modelos para contingência contra picos de demanda (503 UNAVAILABLE)
            candidate_models = [config.gemini_model, "gemini-2.5-flash", "gemini-2.5-pro", "gemini-pro-latest"]
            candidate_models = list(dict.fromkeys(candidate_models))

            last_error = None
            for model_name in candidate_models:
                for attempt in range(2): # Tenta até 2 vezes cada modelo
                    try:
                        logger.info(f"Enviando prompt ao Gemini com modelo '{model_name}' (tentativa {attempt + 1})...")
                        response = self.client.models.generate_content(
                            model=model_name,
                            contents=text,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                temperature=0.7,
                            )
                        )
                        reply_text = response.text or "Comando recebido, senhor."
                        return {"reply": reply_text}
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        logger.warning(f"Oscilação no modelo '{model_name}' (tentativa {attempt + 1}): {err_str[:120]}")
                        if "503" in err_str or "demand" in err_str.lower() or "429" in err_str:
                            await asyncio.sleep(1.0)
                        else:
                            break

            logger.error(f"Todos os modelos da cascata falharam. Último erro: {last_error}")
            return {
                "reply": "Perdão, senhor. Os servidores do Gemini estão enfrentando um pico atípico de alta demanda no momento. Recomendo aguardar alguns instantes e repetir a instrução."
            }

        # Resposta de fallback quando aguardando inserção da API Key
        return {
            "reply": f"J.A.R.V.I.S online e operacional. Chave do Gemini aguardando configuração no arquivo .env."
        }
