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
            try:
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

                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                    )
                )

                reply_text = response.text or "Comando recebido, senhor."
                return {"reply": reply_text}
            except Exception as e:
                logger.error(f"Erro na chamada do modelo Gemini: {e}")
                return {"reply": f"Perdão, senhor. Ocorreu uma oscilação na conexão com a API do Gemini: {e}"}

        # Resposta de fallback quando aguardando inserção da API Key
        return {
            "reply": f"J.A.R.V.I.S online e operacional. Chave do Gemini aguardando configuração no arquivo .env."
        }
