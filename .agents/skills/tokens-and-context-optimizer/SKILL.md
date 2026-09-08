---
name: tokens-and-context-optimizer
description: >-
  Estrategias avancadas de reducao de consumo de tokens e otimizacao de contexto no J.A.R.V.I.S:
  filtragem de boilerplate, compressao de stack traces, prompt caching no Gemini 2.5,
  respostas telegraficas estruturadas para voz e limites de contexto preventivos.
---

# Tokens & Context Optimizer (J.A.R.V.I.S)

Esta skill define as tecnicas de engenharia para manter o consumo de tokens da API do Gemini no menor patamar possivel, garantindo velocidade instantanea e custos minimos.

---

## 1. A Regra dos Tr?s N?veis de Resolu??o

Antes de qualquer chamada a API externa, avalie o n?vel da solicita??o:

1. **N?vel 1 (Local / Determin?stico - 0 Tokens)**: Comandos de m?dia, abrir apps, mudar workspaces, consultar hora, volume. Resolvidos com regex e m?todos nativos de `core/system/`.
2. **N?vel 2 (RAG Local Compactado - Baixo Custo)**: Busca por notas espec?ficas no Obsidian. Enviar apenas o cabe?alho e o snippet relevante (limite m?ximo de 300 palavras por nota).
3. **N?vel 3 (Gemini com Contexto Higienizado)**: An?lises de c?digo, perguntas abertas ou depura??o de erros complexos.

---

## 2. Higieniza??o e Compacta??o de Stack Traces

Ao ler logs ou erros da ?rea de transfer?ncia com `get_clipboard_content()`, remova ru?dos antes de enviar ao prompt:

```python
import re

def compact_stacktrace(raw_text: str, max_lines: int = 40) -> str:
    """Remove caminhos absolutos redundantes e mantem apenas o frame do erro."""
    lines = raw_text.splitlines()
    if len(lines) <= max_lines:
        return raw_text
        
    # Mant?m o cabe?alho do erro e as ?ltimas 30 linhas onde reside o erro real
    compressed = lines[:5] + ["\n... [frames intermediarios omitidos para economizar tokens] ...\n"] + lines[-35:]
    return "\n".join(compressed)
```

---

## 3. Diretrizes de Respostas Telegr?ficas para ?udio (VoiceIO)

Para comandos de voz, a LLM deve gerar sa?das curtas e concisas. Tokens de output s?o mais lentos e mais caros que tokens de input.

### Configura??o no System Prompt:
```text
Responda de forma telegrafica, executiva e concisa (maximo 2 a 3 frases para audio).
Nunca faca preambulos como 'Claro, com certeza, estou analisando...'. Va direto ao ponto.
```

---

## 4. Prompt Caching do Google GenAI

No Gemini 2.5, o `system_instruction` longo e as notas de contexto frequentes podem se beneficiar de Context Caching quando o tamanho do contexto for relevante:
- Mantenha a ordem dos componentes do prompt est?vel (System Instruction -> Contexto Obsidian -> Input do Usu?rio).
- N?o injete timestamps mut?veis (segundos/minutos) dentro da instru??o de sistema est?tica, pois isso invalida o cache de prefixo da API.