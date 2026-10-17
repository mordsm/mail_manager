---
confidence: high
created: '2026-10-14'
domain:
- llm_wiki
- search
id: 2026-10-14-rag-fusion-architecture
status: active
type: decision
topic: Hybrid Search Strategy
title: Hybrid Search with Reciprocal Rank Fusion
---

# Decision: Hybrid Search with Reciprocal Rank Fusion

**Project / Domain**: llm_wiki / Search

## Decision
Combine BM25 keyword matching with dense vector embeddings using Reciprocal Rank Fusion (RRF) for all knowledge retrieval and conversational querying.

## Rationale & Reason
Pure vector search frequently missed exact medical acronyms, specific genes, and technical file paths (e.g. SCFA, Tight Junctions, FastApi). Pure keyword search missed semantic paraphrasing in Hebrew and English. Hybrid RAG gives the best of both worlds.

## Alternatives Considered
- **Vector Search Only**: Failed on exact technical tokens and terminology.
- **BM25 Only**: Failed on conceptual queries and cross-lingual understanding (Hebrew-English query expansion).

## Tradeoffs
Slightly higher index build time and dual scoring overhead, mitigated by local caching and sub-second execution.

## Resolved By
Moshe (System Architect)
