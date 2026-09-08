---
name: windows-automation-pro
description: >-
  Automacao nativa e de baixo nivel para Windows 10 e Windows 11: manipulacao de janelas via ctypes (user32),
  controle granular de audio por aplicativo com pycaw, gestao de processos com psutil,
  execucao silenciosa de PowerShell sem janela de terminal e compatibilidade estrita Win10/Win11.
---

# Windows Automation Pro (Windows 10 & Windows 11)

Este guia define os padroes de engenharia para automacao nativa do sistema operacional no J.A.R.V.I.S, garantindo **compatibilidade universal com Windows 10 (Build 19041+) e Windows 11**.

---

## 1. Matriz de Compatibilidade Windows 10 vs Windows 11

| Recurso | Windows 10 | Windows 11 | Implementacao Segura |
| :--- | :---: | :---: | :--- |
| `user32.dll` (Janelas, Teclas, Foco) | 100% | 100% | Padrao universal Win32 C types |
| `pycaw` (Audio Master & Sessao por App) | 100% | 100% | Windows Core Audio API |
| PowerShell 5.1 (Built-in nativo) | 100% | 100% | Usar flags `-NoProfile -NonInteractive` |
| `psutil` (Metricas, Processos, CPU, RAM) | 100% | 100% | Python standard wrapper |
| DWM Cantos Arredondados / Mica | Nao suportado | Suportado | Envolver chamada em try/except silencioso |

---

## 2. Manipulacao de Janelas (user32.dll via ctypes)

Permite ao assistente focar, minimizar ou restaurar qualquer janela de aplicativo (VS Code, Chrome, Spotify, Obsidian).

```python
import ctypes
from ctypes import wintypes
from typing import Optional

user32 = ctypes.windll.user32

SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_RESTORE = 9

def focus_window_by_title(partial_title: str) -> bool:
    """Localiza e traz para primeiro plano uma janela que contenha o texto no titulo."""
    target_hwnd = None
    
    def enum_windows_callback(hwnd, extra):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if partial_title.lower() in buff.value.lower():
                    target_hwnd = hwnd
                    return False  # Para a enumeracao
        return True

    CMPFUNC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(CMPFUNC(enum_windows_callback), 0)
    
    if target_hwnd:
        # Se a janela estiver minimizada, restaura primeiro
        user32.ShowWindowAsync(target_hwnd, SW_RESTORE)
        user32.SetForegroundWindow(target_hwnd)
        return True
    return False
```

---

## 3. Controle de Audio Granular por App (`pycaw`)

O J.A.R.V.I.S ja possui `pycaw` no `requirements.txt`. Ele funciona identicamente no Windows 10 e Windows 11 para mutar ou ajustar volume de um aplicativo especifico (ex: mutar Discord durante reunioes ou Deep Work).

```python
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

def set_app_volume(app_process_name: str, volume: float) -> bool:
    """Ajusta volume (0.0 a 1.0) para um processo especifico (ex: 'spotify.exe', 'discord.exe')."""
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)
        if session.Process and session.Process.name().lower() == app_process_name.lower():
            volume_control.SetMasterVolume(max(0.0, min(1.0, volume)), None)
            return True
    return False
```

---

## 4. Execucao Silenciosa de Comandos PowerShell

Ao executar scripts ou comandos via PowerShell no Windows 10 ou 11:
- **Nunca** use `&&` para encadear (use `;`).
- Use flags de supressao de janela para execucao silenciosa em background.

```python
import subprocess
import asyncio

async def run_powershell_silent(command: str) -> str:
    """Executa comando PowerShell em background sem criar janela de terminal."""
    loop = asyncio.get_running_loop()
    
    def _execute():
        # STARTUPINFO com wShowWindow=0 oculta completamente qualquer prompt no Win10/Win11
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return proc.stdout.strip()

    return await loop.run_in_executor(None, _execute)
```

---

## 5. Regras de Boas Praticas no Windows
1. **Sempre use `run_in_executor`** para chamadas ctypes ou subprocessos que possam demorar mais de 10ms.
2. **Nao dependa de caminhos absolutos com letras de disco fixas** para pastas de usuario (use `os.path.expandvars('%APPDATA%')` ou `Path.home()`).
3. **Evite travar em prompts interativos**: Sempre passe `-NonInteractive` em chamadas de CLI.