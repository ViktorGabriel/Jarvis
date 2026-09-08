import re
from enum import Enum
from typing import Tuple

class RiskLevel(str, Enum):
    SAFE = "safe"                   # Ação totalmente autônoma
    CRITICAL = "critical"           # Travamento preventivo: exige autorização no HUD

DESTRUCTIVE_COMMAND_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdel\b",
    r"\brmdir\b",
    r"\bformat\b",
    r"\bdrop\s+database\b",
    r"\bdrop\s+table\b",
    r"Remove-Item\b.*-Recurse",
    r"Remove-Item\b.*-Force",
    r"docker\s+compose\s+down.*-v",
    r"docker\s+system\s+prune",
    r"docker\s+volume\s+rm",
    r"docker\s+rm\s+-[a-zA-Z]*f",
]

ADMIN_COMMAND_PATTERNS = [
    r"\bsudo\b",
    r"\brunas\b",
    r"\bSet-ExecutionPolicy\b",
    r"\bnet\s+user\b",
]

class GovernancePolicy:
    @staticmethod
    def evaluate_command(command: str) -> Tuple[RiskLevel, str]:
        cmd_clean = command.strip().lower()

        # Checa git push
        if "git" in cmd_clean and "push" in cmd_clean:
            return RiskLevel.CRITICAL, "Publicação externa detectada (git push). Requer autorização preventiva."

        # Checa privilégios administrativos
        for pattern in ADMIN_COMMAND_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.CRITICAL, f"Execução com privilégios elevados detectada ({pattern}). Requer autorização."

        # Checa comandos destrutivos
        for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.CRITICAL, "Operação potencialmente destrutiva no disco. Requer aprovação explícita."

        return RiskLevel.SAFE, "Comando classificado como seguro para execução autônoma."

    @staticmethod
    def evaluate_file_write(file_path: str, is_deletion: bool = False) -> Tuple[RiskLevel, str]:
        if is_deletion:
            return RiskLevel.CRITICAL, f"Exclusão de arquivo solicitada: {file_path}"
        return RiskLevel.SAFE, "Criação/edição autorizada sob modo supervisionado por escopo."
