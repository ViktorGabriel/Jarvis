import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class JarvisConfig(BaseModel):
    # API & Network
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    gemini_live_model: str = Field(default_factory=lambda: os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-latest"))
    ws_host: str = Field(default="127.0.0.1")
    ws_port: int = Field(default=8765)

    # Obsidian Vault Configuration
    obsidian_vault_path: Path = Field(
        default_factory=lambda: Path(os.getenv("OBSIDIAN_VAULT_PATH", str(BASE_DIR / "vault")))
    )

    # Audio IO Settings
    sample_rate: int = Field(default=16000) # 16kHz for Gemini PCM
    channels: int = Field(default=1)
    chunk_size: int = Field(default=1024)

    # Governance & Safety
    require_confirmation_for_destructive: bool = True
    require_confirmation_for_git_push: bool = True
    require_confirmation_for_admin: bool = True

    @property
    def human_journal_path(self) -> Path:
        return self.obsidian_vault_path / "Human" / "Journal"

    @property
    def human_inbox_path(self) -> Path:
        return self.obsidian_vault_path / "Human" / "Inbox"

    @property
    def human_voice_notes_path(self) -> Path:
        return self.obsidian_vault_path / "Human" / "Voice Notes"

    @property
    def human_projects_path(self) -> Path:
        return self.obsidian_vault_path / "Human" / "Projects"

    @property
    def human_user_context_path(self) -> Path:
        return self.obsidian_vault_path / "Human" / "User Context"

    @property
    def machine_sops_path(self) -> Path:
        return self.obsidian_vault_path / "Machine" / "SOPs"

    @property
    def machine_workflows_path(self) -> Path:
        return self.obsidian_vault_path / "Machine" / "Workflows"

    @property
    def machine_research_path(self) -> Path:
        return self.obsidian_vault_path / "Machine" / "Research Results"

    @property
    def machine_logs_path(self) -> Path:
        return self.obsidian_vault_path / "Machine" / "Logs"

config = JarvisConfig()
