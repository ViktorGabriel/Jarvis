---
name: conventional-commits-workflow
description: >-
  Workflow de commits convencionais para o J.A.R.V.I.S: tipos, escopos do projeto, tamanho ideal
  de commit, mensagens multi-linha no PowerShell, política de push, changelogs e squash.
  Ative ao fazer commits, revisar histórico, preparar release ou ensinar boas práticas de git.
---

# Conventional Commits Workflow — J.A.R.V.I.S

> **Repositório:** https://github.com/ViktorGabriel/Jarvis | **Branch principal:** `main`
> **Shell:** PowerShell (Windows) — use `;` para encadear comandos, **nunca** `&&`

---

## 1. Tipos de Commit — Quando Usar Cada Um

A especificação Conventional Commits define o **tipo** como o prefixo que descreve a *natureza* da mudança. Use a tabela abaixo como referência rápida:

| Tipo       | Quando usar                                                                 | Gera versão? |
|------------|-----------------------------------------------------------------------------|:------------:|
| `feat`     | Nova funcionalidade perceptível pelo usuário/sistema (ex: novo skill, novo endpoint) | minor ↑ |
| `fix`      | Corrige um bug existente (comportamento errado → correto)                   | patch ↑      |
| `test`     | Adiciona ou corrige testes automatizados — sem mudar código de produção     | —            |
| `chore`    | Tarefas de manutenção: deps, configs, gitignore, scripts de CI              | —            |
| `refactor` | Mudança interna de código que **não** adiciona feature nem corrige bug      | —            |
| `docs`     | Somente alterações em documentação (README, SKILL.md, comentários)         | —            |
| `style`    | Formatação, espaços, vírgulas — zero impacto funcional                     | —            |
| `perf`     | Melhoria de desempenho mensurável (cache, query otimizada, batch)          | patch ↑      |
| `ci`       | Mudanças em pipelines de CI/CD (GitHub Actions, scripts de deploy)         | —            |

> **Regra de ouro:** Se a mudança é visível para quem **usa** o JARVIS → `feat` ou `fix`.
> Se é visível só para quem **desenvolve** → `refactor`, `chore`, `docs`, `test` ou `style`.

### Breaking Changes

Adicione `!` após o tipo ou escreva `BREAKING CHANGE:` no body quando a mudança quebra compatibilidade:

```
feat(api)!: redesign endpoint /query — parâmetro 'q' renomeado para 'prompt'
```

---

## 2. Escopos do Projeto JARVIS

O **scope** identifica *qual módulo* do projeto foi tocado. Sempre use letras minúsculas.

| Scope          | Módulo / Responsabilidade                                                     | Exemplo de path afetado              |
|----------------|-------------------------------------------------------------------------------|--------------------------------------|
| `system`       | Núcleo do JARVIS: inicialização, orquestrador principal, pipeline de runtime  | `jarvis/`, `main.py`, `core/`        |
| `brain`        | Memória, contexto, RAG, armazenamento de sessões                              | `brain/`, `memory/`                  |
| `hud`          | Interface holográfica / HUD Three.js, overlays visuais                        | `hud/`, `frontend/`, `*.glsl`        |
| `obsidian`     | Second Brain vault, notas atômicas, Daily Notes, MOCs                         | `.obsidian/`, `vault/`, `notes/`     |
| `governance`   | SafetyInterceptor, políticas de autonomia, aprovação de ações de risco        | `.agents/skills/governance-and-safety/` |
| `engineering`  | Infraestrutura de skills, subagentes, workflows, ferramentas de dev           | `.agents/`, `scripts/`, `Makefile`   |
| `api`          | Endpoints REST/WebSocket, schemas, autenticação                               | `api/`, `routes/`, `schemas/`        |
| `config`       | Configurações de ambiente, variáveis, arquivos `.env`, `pyproject.toml`       | `config/`, `.env*`, `*.toml`         |

### Escopo composto (raro)

Use apenas quando a mudança é intrinsecamente multi-módulo e não pode ser separada:

```
feat(brain,api): expose memory search via REST endpoint
```

---

## 3. Tamanho Ideal de Commit — A Regra do Commit Atômico

Um commit deve representar **uma unidade lógica indivisível de mudança**.

### O que pertence ao mesmo commit

- Um arquivo de implementação + seu arquivo de teste correspondente
- Uma função nova + a atualização do README que a documenta
- Uma correção de bug + o comentário que explica a causa raiz

### O que **não** pertence ao mesmo commit

- Duas features independentes (faça dois commits)
- Uma feature + refatoração não relacionada (separe)
- Correção de bug + atualização de dependências (separe)

### Sinais de que seu commit é grande demais

- A mensagem precisaria de "e" para conectar duas ideias
- O `git diff --staged` mostra mudanças em módulos completamente diferentes
- Você hesitou ao escolher o scope porque tocou em mais de dois

### Tamanho razoável em linhas (heurística)

| Tipo       | Linhas alteradas (+-) típicas |
|------------|-------------------------------|
| `fix`      | 1 – 30                        |
| `feat`     | 10 – 150                      |
| `refactor` | 20 – 200                      |
| `chore`    | 1 – 50                        |
| `docs`     | qualquer — é só texto         |

> Não existe limite máximo absoluto, mas se o diff supera 300 linhas em arquivos muito variados, considere dividir.

---

## 4. Sintaxe PowerShell para Commits

No PowerShell, `&&` **não existe** como operador de encadeamento (use `;`).
Para mensagens multi-linha, use aspas simples `'...'` — elas não interpolam variáveis.

### Commit de linha única

```powershell
git commit -m 'feat(brain): add short-term memory buffer for session context'
```

### Commit com subject + body (multi-linha)

```powershell
git commit -m 'feat(hud): implement reactive particle system

Add Three.js particle emitter controlled by audio input amplitude.
Particles react to microphone levels using AudioAnalyser API.

Closes #12'
```

> **Dica:** No PowerShell, aspas simples dentro de `'...'` precisam ser dobradas (`''''`).
> Use aspas duplas `"..."` apenas quando precisar de interpolação de variáveis `$var`.

### Encadeando add + commit no PowerShell

```powershell
# Correto — use ; para encadear
git add src/hud/particles.js ; git commit -m 'feat(hud): add particle emitter'

# Errado — && não funciona no PowerShell (apenas no cmd e bash)
# git add src/hud/particles.js && git commit -m 'feat(hud): ...'
```

### Commit com múltiplos arquivos seletivos

```powershell
git add brain/memory.py ; git add tests/test_memory.py ; git commit -m 'feat(brain): add episodic memory with pytest coverage'
```

### Amend sem abrir editor

```powershell
git commit --amend --no-edit
# ou para mudar somente a mensagem:
git commit --amend -m 'fix(brain): correct memory flush on session end'
```

---

## 5. Exemplos Reais do Projeto JARVIS

Dez commits exemplares que refletem o histórico e arquitetura do JARVIS:

```
1. feat(system): initialize JARVIS core orchestrator with startup pipeline

   Bootstrap main agent loop, load environment configuration and register
   all skill plugins on startup. Sets the foundation for all subsequent modules.

2. feat(governance): implement SafetyInterceptor for high-risk action gating

   Adds the SafetyInterceptor class that evaluates autonomy level before
   executing destructive or push operations. Requires explicit approval for
   actions classified as CRITICAL or IRREVERSIBLE.

3. feat(brain): add RAG pipeline with ChromaDB vector store

   Integrates ChromaDB as the long-term memory backend. Documents are chunked,
   embedded via text-embedding-004, and retrieved by cosine similarity.

4. feat(hud): scaffold Three.js HUD with holographic overlay

   Initial Three.js scene with transparent WebGL renderer, glowing grid shader,
   and HUD container anchored to viewport edges.

5. feat(api): expose /query endpoint for natural language prompt routing

   POST /query accepts { prompt, session_id } and routes through the brain
   pipeline before returning a structured JSON response.

6. feat(obsidian): create Daily Note template with JARVIS metadata block

   Adds vault/templates/Daily Note.md with YAML frontmatter (mood, energy,
   focus) and auto-populated date/time via Templater plugin.

7. fix(brain): prevent duplicate embeddings on re-ingestion

   Checks document hash before inserting into ChromaDB. Avoids vector
   duplication when the ingest pipeline is re-run on the same corpus.

8. chore(config): add .env.example and update .gitignore for secrets

   Documents all required environment variables with placeholder values.
   Excludes .env, __pycache__, and *.pyc from version control.

9. refactor(system): extract prompt builder into dedicated PromptFactory class

   Moves inline prompt construction out of the orchestrator into PromptFactory.
   Improves testability and separates concerns. No behavioral change.

10. test(api): add pytest suite for /query endpoint with mock brain

    Uses httpx.AsyncClient to test happy path, missing session_id, and
    empty prompt edge cases against a mocked BrainPipeline.
```

---

## 6. Política de Push — SafetyInterceptor

O `git push origin main` é uma ação **IRREVERSÍVEL** que afeta o repositório remoto público.
O SafetyInterceptor (governança) **bloqueia automaticamente** o push quando:

- Detecta commits com `BREAKING CHANGE`
- O push envolve mais de N commits não revisados (threshold configurável)
- A branch é `main` e não houve revisão de diff recente
- Algum arquivo sensível (`.env`, chaves, secrets) está no staged

### Fluxo de aprovação

```
1. Agente propõe: git push origin main
2. SafetyInterceptor avalia risco → classifica como CRITICAL
3. Agente apresenta ao usuário:
   - Lista de commits a serem enviados
   - Diff resumido das mudanças
   - Pergunta explícita de aprovação
4. Usuário aprova → push executado
5. SafetyInterceptor registra aprovação no log de governança
```

### Como verificar o que será enviado antes do push

```powershell
# Ver commits locais que ainda não foram para o remoto
git log origin/main..HEAD --oneline

# Ver diff completo do que será enviado
git diff origin/main..HEAD

# Conferir arquivos alterados
git diff origin/main..HEAD --name-only
```

### Situações em que o push pode ser bloqueado

| Situação                          | Ação recomendada                                           |
|-----------------------------------|------------------------------------------------------------|
| Arquivo `.env` no commit          | `git rm --cached .env` + amend + atualizar `.gitignore`   |
| Breaking change não documentada   | Adicionar `BREAKING CHANGE:` no body + re-commitar        |
| Muitos commits bagunçados         | Fazer squash interativo antes do push (ver seção 10)       |

---

## 7. git add Seletivo — Por Arquivo vs Interativo

Nunca use `git add .` sem revisar o que está sendo adicionado ao stage.

### Por arquivo (mais comum)

```powershell
# Adicionar um arquivo específico
git add brain/memory.py

# Adicionar um diretório inteiro
git add hud/

# Adicionar múltiplos arquivos explícitos
git add api/routes.py api/schemas.py
```

### git add -p — Modo interativo (patch)

Permite selecionar **hunks** (blocos de diff) dentro de um mesmo arquivo:

```powershell
git add -p brain/memory.py
```

Comandos do modo patch:

| Tecla | Ação                                              |
|-------|---------------------------------------------------|
| `y`   | Adicionar este hunk ao stage                      |
| `n`   | Pular este hunk (não adicionar)                   |
| `s`   | Dividir o hunk em partes menores                  |
| `e`   | Editar o hunk manualmente                         |
| `q`   | Sair — hunks já confirmados com `y` ficam staged  |
| `?`   | Ajuda                                             |

> **Quando usar `-p`:** Você modificou um arquivo com duas mudanças independentes e quer
> fazer dois commits separados. Adicione o primeiro bloco com `-p`, faça o commit,
> depois adicione o restante.

### Remover arquivo do stage sem descartar mudanças

```powershell
git restore --staged brain/memory.py
# ou equivalente antigo:
git reset HEAD brain/memory.py
```

---

## 8. Revisão Antes do Commit

**Nunca commite sem revisar.** Esses são os três comandos essenciais de revisão:

### git status — visão geral

```powershell
git status
```

Leia cada seção:
- **Changes to be committed** → o que vai para o commit (staged)
- **Changes not staged** → modificações que ficam de fora
- **Untracked files** → arquivos novos ainda não adicionados

### git diff --staged — o diff exato do commit

```powershell
git diff --staged
# Alias equivalente:
git diff --cached
```

Isso mostra **exatamente** o que vai entrar no commit. Leia linha a linha antes de prosseguir.
Verifique:
- Nenhum `print()`, `console.log()`, ou `debugger` esquecido
- Nenhuma chave de API ou senha no código
- As mudanças fazem sentido com a mensagem que você vai escrever

### git diff — mudanças ainda não staged

```powershell
git diff
```

Mostra o que está modificado mas **não** adicionado ao stage. Use para decidir o que
ainda merece entrar no commit atual.

### git log --oneline — contexto do histórico

```powershell
git log --oneline -10
```

Ver os últimos 10 commits para garantir que o novo commit continua o padrão da sequência.

---

## 9. Corrigir o Último Commit — git commit --amend

Use `--amend` somente para corrigir **o último commit** e **antes de fazer push**.
Após o push para `main`, o amend reescreveria a história pública — use com extremo cuidado.

### Corrigir apenas a mensagem

```powershell
git commit --amend -m 'feat(brain): add episodic memory with TTL expiration'
```

### Adicionar um arquivo esquecido sem mudar a mensagem

```powershell
git add brain/ttl_policy.py
git commit --amend --no-edit
```

### Corrigir autor do commit

```powershell
git commit --amend --author="Viktor Gabriel <viktor@example.com>" --no-edit
```

### Quando NÃO usar --amend

- Após `git push origin main` (histórico remoto já foi alterado — causaria conflito)
- Quando outros colaboradores já fizeram `git pull` (história diverge)
- Se quiser corrigir um commit mais antigo que o último (use `git rebase -i`)

---

## 10. Squash Antes de PR — git rebase -i

Use squash para consolidar múltiplos commits experimentais em um único commit limpo
antes de enviar ao repositório remoto.

### Situação típica

Você trabalhou em uma feature com 5 commits WIP:

```
abc1234 WIP: tentando fix no memory
def5678 debugando
ghi9012 mais testes
jkl3456 acho que funcionou
mno7890 limpeza
```

Esses commits não têm valor histórico. Consolide-os em um único `feat(brain): ...`.

### Procedimento

```powershell
# Rebase interativo nos últimos 5 commits
git rebase -i HEAD~5
```

No editor que abrir, mude `pick` para `squash` (ou `s`) em todos exceto o primeiro:

```
pick abc1234 WIP: tentando fix no memory
squash def5678 debugando
squash ghi9012 mais testes
squash jkl3456 acho que funcionou
squash mno7890 limpeza
```

Salve e feche o editor. O Git abrirá um segundo editor para a mensagem final:

```
feat(brain): fix memory flush race condition on concurrent sessions

Root cause: session dict was mutated during async iteration.
Fixed by copying keys before iterating and using asyncio.Lock.
```

### Alternativa rápida — reset soft + commit

```powershell
# Squash dos últimos 3 commits em um, pedindo nova mensagem
git reset --soft HEAD~3 ; git commit -m 'feat(brain): implement session memory with async safety'
```

> **Atenção:** `git reset --soft` não descarta as mudanças — apenas desfaz os commits
> mantendo tudo staged.

### Quando squash é obrigatório no JARVIS

- Antes de qualquer `git push origin main` com commits de "WIP", "debug", "teste rápido"
- Quando o log mostra mais de 3 commits para a mesma feature ainda não publicada
- Ao preparar um release: todos os commits do milestone devem estar limpos

---

## 11. Checklist do Commit Perfeito

Antes de pressionar Enter no `git commit`, verifique **todos** os 6 pontos:

```
[ ] 1. git diff --staged foi lido linha a linha — sem debug, sem segredos
[ ] 2. A mensagem segue o padrão: tipo(scope): descrição imperativa em minúsculas
[ ] 3. O scope pertence à tabela oficial:
        system | brain | hud | obsidian | governance | engineering | api | config
[ ] 4. O commit é atômico — representa uma única unidade lógica de mudança
[ ] 5. Se houver breaking change: ! no tipo OU BREAKING CHANGE: no body
[ ] 6. Nenhum arquivo .env, *.key, *.pem ou secret está no staged
```

Sequência de comandos recomendada antes de commitar:

```powershell
# Passo 1 — revisar staged
git diff --staged

# Passo 2 — verificar status geral
git status

# Passo 3 — listar arquivos staged (checar se tem segredo)
git diff --staged --name-only

# Passo 4 — commitar
git commit -m 'feat(engineering): add conventional-commits-workflow skill'
```

---

## 12. Convenção de Branches — Para Uso Futuro

Atualmente o JARVIS trabalha diretamente na `main`. Caso você adote um modelo de branches:

### Nomenclatura

| Prefixo      | Uso                                              | Exemplo                            |
|--------------|--------------------------------------------------|------------------------------------|
| `feature/`   | Nova funcionalidade em desenvolvimento           | `feature/hud-particle-shader`      |
| `fix/`       | Correção de bug isolada                          | `fix/brain-memory-flush`           |
| `chore/`     | Manutenção, deps, configs                        | `chore/update-chromadb-version`    |
| `refactor/`  | Refatoração sem feature nova                     | `refactor/extract-prompt-factory`  |
| `docs/`      | Somente documentação                             | `docs/update-obsidian-vault-guide` |
| `release/`   | Preparação de uma versão                         | `release/v1.0.0`                   |

### Criando e vinculando uma branch

```powershell
# Criar branch local e ir para ela
git checkout -b feature/hud-particle-shader

# Trabalhar, commitar...
git add hud/particles.js ; git commit -m 'feat(hud): add WebGL particle emitter'

# Publicar branch
git push origin feature/hud-particle-shader

# Após aprovação via PR, limpar a branch local
git checkout main ; git pull ; git branch -d feature/hud-particle-shader
```

### Regra de proteção da `main`

- **Nunca** force-push em `main` (`git push --force origin main`)
- Todo merge em `main` deve passar pelo SafetyInterceptor
- Mantenha `main` sempre em estado deployable (pronto para uso)

---

## Referência Rápida — Comandos Essenciais

```powershell
# Ver o que será commitado
git diff --staged

# Adicionar arquivo seletivo
git add caminho/para/arquivo.py

# Adicionar por hunks (interativo)
git add -p caminho/para/arquivo.py

# Remover do stage sem perder mudanças
git restore --staged caminho/para/arquivo.py

# Commit padrão
git commit -m 'tipo(scope): descrição imperativa'

# Commit com body multi-linha
git commit -m 'feat(brain): adicionar cache de embeddings

Descreva o motivo da mudança aqui.
Referencie issues com Closes #N.'

# Corrigir último commit (antes do push)
git commit --amend -m 'mensagem corrigida'
git commit --amend --no-edit

# Ver commits locais não enviados
git log origin/main..HEAD --oneline

# Squash dos últimos N commits
git rebase -i HEAD~N

# Squash via reset + commit (mais simples)
git reset --soft HEAD~N ; git commit -m 'tipo(scope): mensagem final'

# Push (requer aprovação da governança)
git push origin main
```

---

## Recursos e Referências

- **Especificação oficial:** https://www.conventionalcommits.org/pt-br/v1.0.0/
- **Versionamento Semântico:** https://semver.org/lang/pt-BR/
- **Governança JARVIS:** `.agents/skills/governance-and-safety/SKILL.md`
- **Histórico do repositório:** https://github.com/ViktorGabriel/Jarvis/commits/main
