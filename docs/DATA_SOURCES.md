# Data Sources

## Recommended Corpus

The prototype deliberately uses a small, high-authority corpus.

### 1. Regulation (EU) 2024/1689 - consolidated text as of 27 July 2026

**Role:** primary RAG source.

**Official source:** EUR-Lex  
**PDF:** https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A02024R1689-20260727  
**ELI page:** https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng

This version is preferred over the original 2024 text for the prototype because it includes the 2026 amendment in a single readable document. The PDF itself states that a consolidated text is a documentation tool and that authentic legal acts are the versions published in the Official Journal.

### 2. Commission Guidelines on prohibited artificial intelligence practices

**Role:** practical examples and Commission interpretation for Article 5 topics.

**Official landing page:** https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-prohibited-artificial-intelligence-ai-practices-defined-ai-act  
**English PDF:** https://ai-act-service-desk.ec.europa.eu/sites/default/files/2025-08/guidelines_on_prohibited_artificial_intelligence_practices_established_by_regulation_eu_20241689_ai_act_english_ied3r5nwo50xggpcfmwckm3nuc_112367-1.PDF

The guidelines are useful but non-binding, so they are secondary to the Regulation.

### 3. Commission Guidelines on the definition of an artificial intelligence system

**Role:** practical scope/definition guidance.

**Official landing page:** https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-ai-system-definition-facilitate-first-ai-acts-rules-application  
**English PDF:** https://ai-act-service-desk.ec.europa.eu/sites/default/files/2025-08/commission_guidelines_on_the_definition_of_an_artificial_intelligence_system_established_by_regulation_eu_20241689_ai_actenglish_nf2skcqfrtjdfggjavcodopcwz4_112455.PDF

The guidelines are useful but non-binding, so they are secondary to the Regulation.

## Why Only These Documents?

The assignment emphasizes processing quality and scalable integration rather than document quantity. Three official sources are enough to demonstrate:

- legal-text ingestion;
- multi-document retrieval;
- source metadata and citations;
- source authority differences;
- scope, risk, prohibition and obligation questions.

GPAI-specific codes, standards, national implementation documents and general web search are intentionally outside the prototype scope.

## Source Versioning

`data/sources.yaml` pins:

- official URL;
- local filename;
- SHA256 hash;
- source type;
- authority.

If an upstream PDF changes, `scripts/download_sources.py` fails the hash check instead of silently changing the evaluation corpus. Update the URL/hash only after reviewing the new official source.

## Processing

1. PyMuPDF extracts text per page.
2. Common page-header noise and line-break hyphenation are normalized.
3. Article/Annex/Chapter headings are tracked when present.
4. Text is chunked to roughly 2,200 characters with a small overlap.
5. Each chunk receives source, page, section and URL metadata.
6. `embeddinggemma:latest` produces 768-dimensional embeddings through Ollama.
7. Qdrant local mode stores vectors and payloads under `data/qdrant/`.
