# J.A.R.V.I.S. (Just A Rather Very Intelligent System) 🤖⚡

> Segundo cérebro autônomo, copiloto de engenharia e assistente tático com interface holográfica futurista inspirada nas indústrias Stark e inteligência em tempo real via **Gemini 2.0 Live API**.

---

## 🌌 Visão Geral

O **J.A.R.V.I.S.** foi projetado para rodar 24/7 de forma leve, fluida e com máxima segurança operacional:

1. **Interface HUD Holográfica (Desktop)**:
   - Desenvolvida em **React 18 + Tailwind CSS + Three.js + Electron**.
   - Janela translúcida (*acrylic blur*) e frameless sem bordas no Windows.
   - **Reator Arc 3D** com anéis concêntricos que reagem em tempo real à amplitude do áudio do microfone e da voz do assistente.
   - **Atalho Global de Ativação**: Pressione `Ctrl + Shift + J` em qualquer lugar do Windows para abrir ou recolher o HUD.
   - Painel de controle de janelas com fixação no topo (*Always on Top*), minimizar e ocultar.

2. **Segundo Cérebro Integrado ao Obsidian**:
   - Organização automática do cofre nas camadas **`Human/`** e **`Machine/`**.
   - **Daily Notes Inteligentes**: Geração automática com blocos de tempo (*time-blocking*), importação de pendências e retrospectiva noturna.
   - **Notas Atômicas**: Criação automática de notas conceituais em `Human/Projects/` com conexões bidirecionais (`[[bi-links]]`) e tags.
   - **Captura Rápida (`Human/Inbox/`)**: Registro instantâneo de pensamentos e ideias.
   - **Sincronização em Tempo Real (`watchdog`)**: Qualquer alteração manual feita no Obsidian é indexada imediatamente pelo J.A.R.V.I.S.
   - **RAG Local**: Busca semântica e contextual no cofre para responder com precisão sobre decisões e históricos anteriores.

3. **Governança e Travamento Preventivo (Safety Interceptor)**:
   - **Modo Supervisionado por Escopo**: Leitura de notas, execução de testes unitários e linters ocorrem de forma 100% autônoma.
   - **Aprovação Crítica Obrigatória**: Operações destrutivas (`rm`, `del`), privilégios de Administrador (`runas`, `sudo`) e publicação remota (`git push`) disparam um travamento preventivo com modal neon sonoro no HUD, exigindo autorização visual ou por voz.

4. **Copiloto de Engenharia & Pair Programming**:
   - **Diff Engine**: Qualquer proposta de alteração de código é apresentada no HUD com realce de sintaxe antes de tocar no disco.
   - **Git Semântico**: Geração automática de mensagens de commit seguindo a especificação **Conventional Commits** (`feat:`, `fix:`, `refactor:`).
   - **Modo Deep Work**: Disparo de sessões de foco contínuo com cronômetro no HUD e registro das horas na Daily Note do Obsidian.

---

## 🏗️ Arquitetura do Projeto

```
Jarvis/
├── core/                                # Camada de Inteligência e Controle (Python Daemon)
│   ├── api/                             # Servidor WebSocket local e protocolo IPC
│   ├── brain/                           # Orquestrador Gemini, System Prompt e Áudio IO
│   ├── governance/                      # Motor de Governança e Travamento Preventivo
│   ├── obsidian/                        # Gerenciador do Cofre (CRUD, Journaling, Watchdog, RAG)
│   ├── engineering/                     # Diff Engine, Git Assistant, Runner assíncrono
│   ├── system/                          # Gerenciador de Deep Work, Métricas e Efeitos Sonoros
│   ├── main.py                          # Ponto de entrada do Daemon
│   └── requirements.txt                 # Dependências Python
│
├── hud/                                 # Camada Visual Holográfica (React + Three.js + Electron)
│   ├── electron/                        # Janela translúcida e atalhos globais
│   ├── src/                             # Componentes React (ArcReactor, ApprovalModal, DiffViewer)
│   └── package.json
│
├── .agents/skills/                      # Skills operacionais do J.A.R.V.I.S
│   ├── obsidian-vault-craft/
│   ├── jarvis-live-audio/
│   ├── futuristic-hud-design/
│   └── governance-and-safety/
│
├── tests/                               # Suíte de testes unitários (pytest)
├── .env.example                         # Modelo de configuração de chaves
└── start.bat                            # Inicializador de comando único
```

---

## 🚀 Como Executar

### 1. Configurar Credenciais
No arquivo `.env` na raiz do projeto:
```env
# Insira a chave da sua conta Gemini Plus / Google AI Studio:
GEMINI_API_KEY=sua_chave_aqui

# (Opcional) Caminho do seu cofre do Obsidian. 
# Se deixado vazio, uma pasta local ./vault será criada e gerenciada automaticamente:
OBSIDIAN_VAULT_PATH=C:/Users/Viktor/Documents/Meu-Vault
```

### 2. Iniciar Sistema Completo
Dê um duplo clique no arquivo `start.bat` ou execute no terminal:
```bash
./start.bat
```

Ou inicie separadamente:
```bash
# Terminal 1 - Backend Daemon:
.\venv\Scripts\python core\main.py

# Terminal 2 - HUD Desktop:
cd hud
npm run start
```

---

## ⌨️ Atalhos e Comandos

- `Ctrl + Shift + J`: Alterna a visibilidade do HUD flutuante sobre qualquer aplicação.
- `"J.A.R.V.I.S, iniciar Deep Work por 60 minutos"`: Inicia a contagem de foco no HUD.
- `"J.A.R.V.I.S, gere minha Daily Note"`: Cria/atualiza o diário do dia no Obsidian.
