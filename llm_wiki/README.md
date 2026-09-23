# LLM Wiki

A local-first, AI-maintained knowledge system based on Obsidian, Markdown, YAML Frontmatter, Git, Python, FastAPI, Typer CLI, Watchdog, and LLM Provider Abstraction.

## Quick Start CLI

```bash
# Add file to a domain inbox
wiki add research /path/to/paper.pdf

# Run natural language query over research domain
wiki ask research "What do we know about multi-agent planning?"

# Run vault integrity check
wiki lint
```

## Directory Structure Overview

- `inbox/`: Universal entry point for new files and notes.
- `raw/`: Immutable raw source store.
- `wiki/`: Synthesized knowledge domains (`personal`, `research`, `business`, `competitive`).
- `shared/`: Reusable cross-domain knowledge promoted via `promote()`.
- `mocs/`: Maps of Content for topic navigation.
- `system/`: State, logs, operational SQLite database.

