---
name: web-research-agent
description: >-
  Padroes de pesquisa na web e recuperacao de informacoes em tempo real para o J.A.R.V.I.S:
  consultas via APIs publicas, extracao limpa de texto com BeautifulSoup, sintese de documentacao
  tecnica e integracao de tools de busca no Gemini Brain.
---

# Web Research Agent (J.A.R.V.I.S)

Capacita o assistente a pesquisar e recuperar dados da internet sob demanda, complementando o conhecimento local do Obsidian com fatos atualizados e documenta??es de bibliotecas.

---

## 1. Arquitetura da Tool de Busca

No m?dulo `core/system/` ou `core/brain/`, disponibilize uma fun??o de consulta r?pida:

```python
import urllib.parse
import requests

def search_web_summary(query: str, max_results: int = 3) -> str:
    """Pesquisa termos tecnicos ou noticias resumidas na web sem navegadores pesados."""
    try:
        # Exemplo com DuckDuckGo HTML Lite ou API publica direta
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            for result in soup.find_all('a', class_='result__snippet', limit=max_results):
                results.append(result.get_text(strip=True))
            return "\n---\n".join(results) if results else "Nenhum resultado encontrado."
        return "Nao foi possivel conectar ao servico de busca."
    except Exception as e:
        return f"Erro na consulta web: {e}"
```

---

## 2. Boas Pr?ticas de Pesquisa
1. **Timeout Curto (m?x 5s)**: A resposta do assistente n?o pode travar a conversa de ?udio.
2. **Higieniza??o de HTML**: Nunca injete tags brutas no prompt do Gemini; extraia texto puro.
3. **Resumo Executivo**: Entregue apenas os pontos-chave ao usu?rio.