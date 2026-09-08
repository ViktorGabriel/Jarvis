import os
import subprocess
import ctypes
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("AppLauncher")

# Códigos de teclas virtuais de controle de mídia no Windows
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

class AppLauncher:
    @staticmethod
    def _send_key(vk_code: int):
        """Dispara evento de tecla virtual no Windows."""
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0) # Key up
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar tecla virtual: {e}")
            return False

    @classmethod
    def media_play_pause(cls) -> bool:
        return cls._send_key(VK_MEDIA_PLAY_PAUSE)

    @classmethod
    def media_next(cls) -> bool:
        return cls._send_key(VK_MEDIA_NEXT_TRACK)

    @classmethod
    def media_previous(cls) -> bool:
        return cls._send_key(VK_MEDIA_PREV_TRACK)

    @classmethod
    def volume_up(cls) -> bool:
        return cls._send_key(VK_VOLUME_UP)

    @classmethod
    def volume_down(cls) -> bool:
        return cls._send_key(VK_VOLUME_DOWN)

    @classmethod
    def launch_spotify(cls) -> Dict[str, Any]:
        """Abre o aplicativo do Spotify via URI protocol do Windows ou executável."""
        try:
            # Tenta via protocolo URI oficial do Windows (funciona para Microsoft Store e instalador clássico)
            os.system("start spotify:")
            return {"success": True, "app": "Spotify", "message": "Spotify aberto com sucesso, senhor."}
        except Exception as e:
            # Fallback para caminho clássico em AppData
            appdata_path = Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe"
            if appdata_path.exists():
                subprocess.Popen([str(appdata_path)])
                return {"success": True, "app": "Spotify", "message": "Spotify iniciado a partir do executável local."}
            return {"success": False, "app": "Spotify", "error": str(e)}

    @classmethod
    def launch_obsidian(cls, vault_path: Optional[str] = None) -> Dict[str, Any]:
        """Abre o Obsidian apontando para o cofre configurado."""
        try:
            if vault_path:
                os.system(f'start obsidian://open?path="{vault_path}"')
            else:
                os.system("start obsidian:")
            return {"success": True, "app": "Obsidian", "message": "Obsidian aberto, senhor."}
        except Exception as e:
            return {"success": False, "app": "Obsidian", "error": str(e)}

    @classmethod
    def launch_vscode(cls, path_to_open: Optional[str] = None) -> Dict[str, Any]:
        """Abre o VS Code no diretório do projeto ou vazio."""
        try:
            target = path_to_open or "."
            subprocess.Popen(["code", target], shell=True)
            return {"success": True, "app": "VS Code", "message": "VS Code iniciado no workspace do projeto."}
        except Exception as e:
            return {"success": False, "app": "VS Code", "error": str(e)}

    @classmethod
    def launch_browser(cls, url: Optional[str] = None) -> Dict[str, Any]:
        """Abre o navegador padrão em uma URL ou aba em branco."""
        try:
            target = url or "https://google.com"
            os.system(f'start {target}')
            return {"success": True, "app": "Navegador", "message": f"Navegador aberto em {target}."}
        except Exception as e:
            return {"success": False, "app": "Navegador", "error": str(e)}

    @classmethod
    def launch_terminal(cls) -> Dict[str, Any]:
        """Abre o terminal do Windows / PowerShell."""
        try:
            subprocess.Popen(["wt.exe"], shell=True)
            return {"success": True, "app": "Terminal", "message": "Terminal do Windows aberto."}
        except Exception:
            subprocess.Popen(["powershell.exe"])
            return {"success": True, "app": "PowerShell", "message": "PowerShell aberto."}
