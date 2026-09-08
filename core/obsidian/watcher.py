import os
import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

logger = logging.getLogger("VaultWatcher")

class VaultChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, str], None]):
        super().__init__()
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self.callback("modified", event.src_path)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self.callback("created", event.src_path)

class ObsidianWatcher:
    def __init__(self, vault_path: Path, on_change: Optional[Callable[[str, str], None]] = None):
        self.vault_path = vault_path
        self.on_change = on_change
        self.observer: Optional[Observer] = None

    def start(self):
        if not self.vault_path.exists():
            self.vault_path.mkdir(parents=True, exist_ok=True)

        handler = VaultChangeHandler(self._handle_change)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.vault_path), recursive=True)
        self.observer.daemon = True
        self.observer.start()
        logger.info(f"Monitoramento do cofre Obsidian ativo em: {self.vault_path}")

    def _handle_change(self, change_type: str, file_path: str):
        rel_path = os.path.relpath(file_path, str(self.vault_path))
        logger.info(f"Edição detectada no Obsidian ({change_type}): {rel_path}")
        if self.on_change:
            self.on_change(change_type, rel_path)

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
