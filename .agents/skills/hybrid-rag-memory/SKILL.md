---
name: hybrid-rag-memory
description: >-
  Arquitetura de Recuperacao Hibrida (BM25 + Dense Semantic Search) para o Obsidian Second Brain
  do J.A.R.V.I.S: chunking semantico de Markdown, embeddings leves, caching local em SQLite
  e ranking de relev?ncia sem estourar a janela de contexto.
---

# Hybrid RAG & Semantic Memory (Obsidian Second Brain)

O J.A.R.V.I.S armazena todo o conhecimento operacional, SOPs e contexto do usu?rio no cofre local do Obsidian (`core/obsidian/`). Este guia estrutura a recupera??o de dados em duas vias: **Palavras-chave exatas (Lexical)** e **Significado conceitual (Sem?ntico)**.

---

## 1. Por que Busca H?brida?

- **Apenas Vetorial (Embeddings)**: Falha em buscar termos t?cnicos exatos, nomes de fun??es (`activate_workspace`) ou IDs de tickets.
- **Apenas L?xica (BM25 / Keyword)**: Falha quando o usu?rio usa sin?nimos ou faz perguntas indiretas ("como iniciar meu dia" vs nota `# Rotina Matinal`).
- **Abordagem H?brida (BM25 + Semantic)**: Normaliza as pontua??es e combina os melhores resultados via Reciprocal Rank Fusion (RRF).

---

## 2. Chunking Sem?ntico de Notas Markdown

Arquivos Markdown do Obsidian devem ser divididos respeitando a sem?ntica dos t?tulos:

```python
import re
from typing import List, Dict

def chunk_markdown_by_headers(content: str, filename: str) -> List[Dict[str, str]]:
    """Divide uma nota markdown em blocos baseados em cabecalhos ## ou ###."""
    sections = re.split(r'(?m)^(?=##?#? )', content)
    chunks = []
    
    for section in sections:
        clean = section.strip()
        if len(clean) > 30:  # Ignora blocos minusculos vazios
            chunks.append({
                "source": filename,
                "text": clean[:1500]  # Limite maximo por chunk para proteger o contexto
            })
    return chunks
```

---

## 3. Caching Local de Embeddings

Para economizar chamadas de API e manter o sistema ultra-r?pido:
- Guarde o hash MD5 de cada arquivo de nota modificado.
- Somente gere novos embeddings se o arquivo tiver sido alterado desde a ?ltima indexa??o.
- Use SQLite ou arquivo JSON indexado para persist?ncia simples sem necessidade de containers pesados.