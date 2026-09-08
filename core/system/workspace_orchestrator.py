import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
from core.config import config
from core.system.app_launcher import AppLauncher
from core.system.focus_manager import FocusManager
from core.system.audio_controller import AudioFeedback
from core.obsidian.journal import JournalManager

logger = logging.getLogger("WorkspaceOrchestrator")

class WorkspaceMode(str, Enum):
    DEV = "dev"
    STUDY = "study"
    DEEP_WORK = "deep_work"
    REST = "rest"

CONFIG_FILE = Path(__file__).resolve().parent / "workspaces.json"

class WorkspaceOrchestrator:
    def __init__(self, focus_manager: FocusManager, journal_manager: Optional[JournalManager] = None):
        self.focus_manager = focus_manager
        self.journal_manager = journal_manager
        self.profiles = self._load_profiles()

    def _load_profiles(self) -> Dict[str, Any]:
        """Carrega perfis de workspaces.json com fallback seguro."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar workspaces.json: {e}")
        
        # Fallback padrão
        return {
            "dev": {
                "name": "Desenvolvimento",
                "apps": ["vscode", "browser", "spotify"],
                "urls": ["http://localhost:5173"],
                "speech_reply": "Protocolo de desenvolvimento ativado. Ambiente de engenharia pronto, senhor."
            },
            "study": {
                "name": "Estudo",
                "apps": ["obsidian", "browser"],
                "speech_reply": "Modo de estudo iniciado. Cofre do Obsidian pronto, senhor."
            },
            "deep_work": {
                "name": "Deep Work",
                "apps": ["vscode", "obsidian"],
                "deep_work": True,
                "deep_work_minutes": 60,
                "speech_reply": "Modo Deep Work iniciado. Foco tático ativado por 60 minutos."
            },
            "rest": {
                "name": "Descanso",
                "apps": ["spotify"],
                "stop_deep_work": True,
                "speech_reply": "Ambiente de trabalho recolhido. Tenha um bom descanso, senhor."
            }
        }

    async def _launch_app_task(self, app_name: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a inicialização de um app de forma assíncrona e resiliente."""
        try:
            name = app_name.lower().strip()
            if name == "vscode":
                return AppLauncher.launch_vscode()
            elif name == "obsidian":
                return AppLauncher.launch_obsidian(str(config.obsidian_vault_path))
            elif name == "spotify":
                res = AppLauncher.launch_spotify()
                if profile.get("spotify_action") == "play":
                    await asyncio.sleep(1.0)
                    AppLauncher.media_play_pause()
                elif profile.get("spotify_action") == "pause":
                    AppLauncher.media_play_pause()
                return res
            elif name == "browser":
                urls = profile.get("urls", ["https://google.com"])
                for url in urls:
                    AppLauncher.launch_browser(url)
                    await asyncio.sleep(0.3)
                return {"success": True, "app": "Browser", "urls": urls}
            elif name == "terminal":
                return AppLauncher.launch_terminal()
            else:
                return {"success": False, "app": app_name, "error": "App desconhecido"}
        except Exception as e:
            logger.warning(f"Exceção ao disparar app '{app_name}': {e}")
            return {"success": False, "app": app_name, "error": str(e)}

    async def activate_workspace(self, mode: str) -> Dict[str, Any]:
        """Orquestra o ambiente completo do sistema operacional concorrentemente."""
        mode_key = mode.lower().strip()
        
        # Mapeamento de sinônimos naturais
        aliases = {
            "programar": "dev",
            "codar": "dev",
            "codigo": "dev",
            "código": "dev",
            "estudar": "study",
            "estudos": "study",
            "foco": "deep_work",
            "foco total": "deep_work",
            "descansar": "rest",
            "pausa": "rest",
            "limpar": "rest"
        }
        mode_key = aliases.get(mode_key, mode_key)

        if mode_key not in self.profiles:
            valid_modes = ", ".join(self.profiles.keys())
            return {
                "success": False,
                "reply": f"Modo '{mode}' não reconhecido, senhor. Modos disponíveis: {valid_modes}."
            }

        profile = self.profiles[mode_key]
        apps = profile.get("apps", [])

        # Efeito sonoro de ativação
        AudioFeedback.play_activation()

        # 1. Disparo concorrente de aplicativos (Promise.allSettled equivalente em Python)
        tasks = [self._launch_app_task(app, profile) for app in apps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Gerenciamento de Foco e Deep Work
        if profile.get("deep_work"):
            duration = profile.get("deep_work_minutes", 60)
            self.focus_manager.start_deep_work(duration, profile.get("name", "Deep Work"))
            if self.journal_manager:
                self.journal_manager.append_deep_work_session(duration, profile.get("name", "Deep Work"))
        elif profile.get("stop_deep_work"):
            self.focus_manager.stop_deep_work()

        # 3. Ajuste de volume se especificado
        vol = profile.get("volume_level")
        if vol is not None:
            # Envia ajuste de volume moderado
            for _ in range(2):
                AppLauncher.volume_down()

        reply = profile.get("speech_reply", f"Workspace {profile.get('name')} ativado.")
        logger.info(f"Workspace '{mode_key}' orquestrado com sucesso. Resultados: {results}")

        return {
            "success": True,
            "mode": mode_key,
            "name": profile.get("name"),
            "reply": reply,
            "results": [r for r in results if isinstance(r, dict)]
        }
