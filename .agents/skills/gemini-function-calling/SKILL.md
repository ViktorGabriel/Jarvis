---
name: gemini-function-calling
description: >-
  Guia de integracao Gemini Function Calling com google-genai SDK no J.A.R.V.I.S:
  definir tools via Python callables, dispatch de function_calls, follow-up calls,
  cascade de modelos 503/429, economia de tokens via triggers deterministicos e docstrings otimizadas.
  Ative ao registrar novas tools, debugar chamadas de funcoes ou otimizar custos de API.
---

# Gemini Function Calling & Otimizacao de Tokens no J.A.R.V.I.S

O J.A.R.V.I.S integra o Google GenAI SDK (`google-genai`) para conceder autonomia de execucao a IA. Este guia detalha a criacao de ferramentas, mitigacao de erros 503/429 e tecnicas de reducao drastica de consumo de tokens.

---

## 1. Economia de Tokens: Triggers Deterministicos First

**Regra de Ouro**: Nunca envie ao Gemini intencoes que podem ser resolvidas com regex ou combinacao de strings locais.

```python
# Em core/brain/live_client.py:
# 1. Triggers deterministicos evitam roundtrip e custo de API
if "aumentar volume" in text_lower:
    AppLauncher.volume_up()
    return {"reply": "Volume do sistema aumentado, senhor."}

if "abrir spotify" in text_lower:
    AppLauncher.launch_spotify()
    return {"reply": "Spotify inicializado, senhor."}

# 2. Apenas intencoes complexas ou analiticas chegam ao Gemini
```

---

## 2. Padrao de Registro de Tools

No `google-genai` SDK, tools sao funcoes Python regulares com anotacoes de tipo e docstrings completas:

```python
def activate_workspace(mode: str) -> str:
    """Ativa e orquestra um ambiente de trabalho completo com multiplos aplicativos e foco.

    Args:
        mode: O modo desejado: 'dev' (programacao), 'study' (estudo/Obsidian), 'deep_work' (foco total), ou 'rest' (descanso).
    """
    return f"Workspace '{mode}' ativado."

def get_clipboard_content(max_length: int = 8000) -> str:
    """Le o conteudo de texto atual da area de transferencia do SO para analise ou conversao.

    Use quando o usuario disser: 'analisa esse erro', 'o que quebrou aqui?',
    'converte o que copiei', 'da uma olhada nisso', 'debug isso'.
    """
    content = ClipboardManager.get_text(max_length=max_length)
    return content or "CLIPBOARD_VAZIO"
```

---

## 3. Despacho e Follow-Up Calls

Quando uma tool necessita de conclusao analitica (ex: inspecionar o erro copiado):

```python
response = self.client.models.generate_content(
    model=model_name,
    contents=text,
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.7,
        tools=[activate_workspace, get_clipboard_content, set_clipboard_content],
    )
)

if response.function_calls:
    for call in response.function_calls:
        if call.name == "get_clipboard_content":
            data = get_clipboard_content()
            # Follow-up call fornecendo o dado para a resposta final
            follow_up = self.client.models.generate_content(
                model=model_name,
                contents=f"{text}\n\n[CLIPBOARD]:\n{data}"
            )
            return {"reply": follow_up.text}
```

---

## 4. Cascata de Contingencia contra 503 e 429

Para contornar oscilacoes de demanda dos modelos da Google:

```python
candidate_models = [
    config.gemini_model,
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-pro-latest"
]

for model_name in candidate_models:
    for attempt in range(2):
        try:
            response = self.client.models.generate_content(...)
            return {"reply": response.text}
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                await asyncio.sleep(1.0)
                continue
            break
```
