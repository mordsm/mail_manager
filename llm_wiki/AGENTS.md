# AGENTS.md — LLM Wiki Specification & Verbatim Rules

## Mission & Core Principles

This project implements a local-first, AI-maintained knowledge system based on Obsidian, Markdown, YAML frontmatter, Git, Python, FastAPI, Typer CLI, and LLM abstraction.

---

## Verbatim Architectural Rules

```text
Raw owns truth.

Domains own evidence.

Shared owns reusable knowledge.

Wiki owns synthesis.

Atomic notes own individual knowledge units.

MOCs own navigation.

LLM owns maintenance.

Human owns judgment.
```

```text
Never destroy provenance.

Never silently convert inference into fact.

Never silently resolve contradictory evidence.

Never duplicate knowledge when links are sufficient.

Never promote private information without policy approval.

Never let Shared become a dumping ground.

Never modify raw sources.

Never make a database the canonical wiki.
```

---

## Domain Boundaries & Knowledge Flow

1. **Personal**: Health, psychology, training, nutrition, cognition, habits, goals, projects, reflections.
2. **Research & Technology**: Topics, concepts, technologies, architectures, software, papers, evidence, hypotheses, claims, contradictions.
3. **Business & Operations**: Strategy, projects, products, customers, finance, administration, operations, decisions, risks, opportunities.
4. **Competitive Analysis**: Companies, products, technologies, pricing, features, positioning, markets, signals, comparisons.
5. **Shared Knowledge**: Reusable cross-domain concepts, entities, methods, people, companies promoted via `promote()`.

---

## Ingestion Pipeline Stages

```text
RECEIVE ──► VALIDATE ──► HASH (SHA-256) ──► DEDUPLICATE ──► CLASSIFY ──► SAVE RAW ──► PARSE ──► EXTRACT ──► COMPARE ──► UPDATE WIKI ──► CREATE LINKS ──► CHECK SHARED PROMOTION ──► UPDATE MOCS ──► UPDATE INDEX ──► UPDATE LOG ──► GIT COMMIT
```

