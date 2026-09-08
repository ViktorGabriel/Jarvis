"""
clipboard_manager.py
Gerenciador de area de transferencia do sistema operacional.
Utiliza pyperclip (cross-platform) com fallback para PowerShell no Windows.
"""
import logging
import subprocess
from typing import Optional

logger = logging.getLogger("ClipboardManager")

DEFAULT_MAX_LENGTH = 8_000


class ClipboardManager:
    """Leitura e escrita na area de transferencia do SO. Todos os metodos sao de classe (stateless)."""

    @classmethod
    def get_text(cls, max_length: int = DEFAULT_MAX_LENGTH) -> Optional[str]:
        """
        Le o conteudo de texto atual da area de transferencia.

        Args:
            max_length: Numero maximo de caracteres retornados (padrao 8 000).

        Returns:
            String com o conteudo do clipboard, ou None se vazio / nao-textual.
        """
        content: Optional[str] = None

        try:
            import pyperclip  # type: ignore
            content = pyperclip.paste()
        except ImportError:
            logger.debug("pyperclip nao instalado - tentando fallback PowerShell.")
        except Exception as e:
            logger.warning(f"pyperclip.paste() falhou: {e} - tentando fallback PowerShell.")

        if content is None:
            content = cls._ps_get()

        if not content or not content.strip():
            return None

        if len(content) > max_length:
            logger.info(f"Clipboard truncado de {len(content)} para {max_length} caracteres.")
            content = content[:max_length] + f"\n\n[... truncado em {max_length} chars]"

        return content

    @classmethod
    def set_text(cls, text: str) -> bool:
        """
        Escreve texto na area de transferencia do SO.

        Args:
            text: Conteudo a copiar.

        Returns:
            True se bem-sucedido, False caso contrario.
        """
        if not isinstance(text, str):
            logger.error("set_text recebeu valor nao-string.")
            return False

        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
            logger.info(f"Clipboard atualizado via pyperclip ({len(text)} chars).")
            return True
        except ImportError:
            logger.debug("pyperclip nao instalado - tentando fallback PowerShell.")
        except Exception as e:
            logger.warning(f"pyperclip.copy() falhou: {e} - tentando fallback PowerShell.")

        return cls._ps_set(text)

    @classmethod
    def _ps_get(cls) -> Optional[str]:
        """Le clipboard via PowerShell Get-Clipboard."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            logger.error(f"Fallback PowerShell Get-Clipboard falhou: {e}")
            return None

    @classmethod
    def _ps_set(cls, text: str) -> bool:
        """Escreve no clipboard via PowerShell Set-Clipboard."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
                input=text,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"Clipboard atualizado via PowerShell ({len(text)} chars).")
                return True
            logger.error(f"PowerShell Set-Clipboard retornou codigo {result.returncode}: {result.stderr}")
            return False
        except Exception as e:
            logger.error(f"Fallback PowerShell Set-Clipboard falhou: {e}")
            return False
