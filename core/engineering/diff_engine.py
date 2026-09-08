import difflib
from pathlib import Path
from typing import Dict, Any, Optional

class DiffEngine:
    @staticmethod
    def generate_diff(file_path: Path, new_content: str) -> Dict[str, Any]:
        """Gera o diff unificado entre o arquivo existente e o novo conteúdo proposto."""
        old_content = ""
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    old_content = f.read()
            except Exception:
                old_content = ""

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            lineterm=""
        ))

        additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "diff_text": "\n".join(diff),
            "additions": additions,
            "deletions": deletions,
            "is_new_file": not file_path.exists(),
        }

    @staticmethod
    def apply_diff(file_path: Path, new_content: str) -> bool:
        """Aplica o conteúdo validado diretamente no disco."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        except Exception as e:
            return False
