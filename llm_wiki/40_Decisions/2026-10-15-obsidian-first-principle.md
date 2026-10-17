---
confidence: high
created: '2026-10-15'
domain:
- llm_wiki
- architecture
id: 2026-10-15-obsidian-first-principle
status: active
type: decision
topic: Canonical Memory Storage
title: Store Canonical Knowledge in Obsidian Markdown
---

# Decision: Store Canonical Knowledge in Obsidian Markdown

**Project / Domain**: llm_wiki / Architecture

## Decision
All synthesized knowledge, daily logs, project memories, and decisions are stored as pure Markdown files with YAML frontmatter inside local Obsidian vaults, rather than inside a proprietary black-box database.

## Rationale & Reason
Ensures 100% human-readable provenance, perpetual data ownership, seamless Git versioning, and allows Moshe to browse and edit everything natively in Obsidian.

## Alternatives Considered
- **Pure Vector DB (Chroma/Qdrant only)**: Fast semantic search, but impossible for a human to audit, inspect, or manually edit notes.
- **Relational SQL Database**: Rigid schema, lacks native Markdown rendering and Obsidian backlinking.

## Tradeoffs
Requires maintaining custom indexing and sync pipelines between files and RAG models, but preserves the fundamental rule: *"Raw owns truth, Wiki owns synthesis, Human owns judgment."*

## Resolved By
Moshe (System Architect)
