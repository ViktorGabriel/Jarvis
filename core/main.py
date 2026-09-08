import asyncio
import logging
import signal
import sys
import uuid
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import config
from core.api.server import JarvisServer
from core.api.protocol import EventType, AgentState
from core.governance.interceptor import SafetyInterceptor
from core.obsidian.vault_manager import ObsidianVaultManager
from core.obsidian.journal import JournalManager
from core.obsidian.watcher import ObsidianWatcher
from core.obsidian.rag import VaultRAG
from core.engineering.git_assistant import GitAssistant
from core.system.focus_manager import FocusManager
from core.system.audio_controller import AudioFeedback
from core.system.workspace_orchestrator import WorkspaceOrchestrator
from core.brain.voice_io import VoiceIO
from core.brain.live_client import GeminiBrain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("JarvisCore")

class JarvisDaemon:
    def __init__(self):
        logger.info("Inicializando subsistemas do J.A.R.V.I.S...")

        # 1. Servidor IPC WebSocket
        self.server = JarvisServer(host=config.ws_host, port=config.ws_port)

        # 2. Governança e Segurança
        self.interceptor = SafetyInterceptor(broadcast_fn=self.server.broadcast)

        # 3. Obsidian & Segundo Cérebro
        self.vault = ObsidianVaultManager()
        self.journal = JournalManager(self.vault)
        self.rag = VaultRAG(self.vault)
        self.watcher = ObsidianWatcher(
            vault_path=config.obsidian_vault_path,
            on_change=self._on_obsidian_change
        )

        # 4. Engenharia & Git
        self.git = GitAssistant(workspace_root=ROOT_DIR, interceptor=self.interceptor)

        # 5. Sistema Operacional, Foco & Orquestrador de Workspaces
        self.focus = FocusManager()
        self.orchestrator = WorkspaceOrchestrator(
            focus_manager=self.focus,
            journal_manager=self.journal
        )

        # 6. Cérebro de IA
        self.brain = GeminiBrain(
            vault=self.vault,
            journal=self.journal,
            rag=self.rag,
            git=self.git,
            focus=self.focus,
            interceptor=self.interceptor,
            broadcast_fn=self.server.broadcast,
            orchestrator=self.orchestrator
        )

        # 7. Áudio & Voz
        self.voice_io = VoiceIO()
        self.voice_io.set_volume_listener(self._on_audio_volume)

        # Registra callback de mensagens do HUD
        self.server.on_message_callback = self.handle_hud_message

    def _on_obsidian_change(self, change_type: str, rel_path: str):
        asyncio.create_task(self.server.broadcast(EventType.OBSIDIAN_UPDATE, {
            "type": change_type,
            "path": rel_path
        }))

    def _on_audio_volume(self, volume_level: float):
        """Envia métrica de decibéis para animação do HUD a cada chunk relevante."""
        if volume_level > 2.0:
            asyncio.create_task(self.server.broadcast(EventType.AUDIO_METRICS, {
                "volume": round(volume_level, 2)
            }))

    async def handle_hud_message(self, message: dict):
        event = message.get("event")
        data = message.get("data", {})

        if event == EventType.USER_INPUT.value:
            user_text = data.get("text", "")
            logger.info(f"Comando recebido do HUD: {user_text}")
            await self.server.update_state(AgentState.THINKING, "Processando solicitação...")
            response = await self.brain.process_user_intent(user_text)
            reply = response.get("reply", "")

            await self.server.update_state(AgentState.SPEAKING, reply[:80])
            await self.server.broadcast(EventType.TRANSCRIPT, {
                "id": f"jarvis_{uuid.uuid4().hex[:10]}",
                "sender": "jarvis",
                "text": reply
            })
            await asyncio.sleep(1.0)
            await self.server.update_state(AgentState.IDLE)

        elif event == EventType.SAFETY_DECISION.value:
            ticket_id = data.get("ticket_id")
            approved = data.get("approved", False)
            logger.info(f"Decisão de governança recebida para [{ticket_id}]: {approved}")
            self.interceptor.resolve_ticket(ticket_id, approved)

        elif event == EventType.DEEP_WORK_TOGGLE.value:
            enable = data.get("enable", True)
            duration = data.get("duration", 60)
            if enable:
                res = self.focus.start_deep_work(duration)
                AudioFeedback.play_activation()
            else:
                res = self.focus.stop_deep_work()
                AudioFeedback.play_success()
            await self.server.broadcast(EventType.NOTIFICATION, {
                "message": f"Deep Work {'iniciado' if enable else 'encerrado'}"
            })

    async def _system_metrics_loop(self):
        """Loop contínuo transmitindo métricas de hardware e foco ao HUD."""
        while True:
            metrics = FocusManager.get_hardware_metrics()
            deep_work = self.focus.get_deep_work_status()
            await self.server.broadcast(EventType.SYSTEM_METRICS, {
                "hardware": metrics,
                "deep_work": deep_work
            })
            await asyncio.sleep(2.0)

    async def run(self):
        # Inicia o servidor WebSocket
        await self.server.start()

        # Inicia o monitor de arquivos do Obsidian
        self.watcher.start()

        # Inicia a escuta do microfone
        self.voice_io.start_listening()

        # Inicia a Daily Note matinal do dia de forma não intrusiva
        daily_note = self.journal.get_or_create_daily_note()
        logger.info(f"Daily Note do dia pronta no Obsidian: {daily_note.name}")

        AudioFeedback.play_activation()
        logger.info("J.A.R.V.I.S Core Daemon operacional e pronto para atender.")

        # Executa o loop de métricas do sistema
        await self._system_metrics_loop()

async def main():
    daemon = JarvisDaemon()
    await daemon.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Encerrando J.A.R.V.I.S...")
