from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from app.services.parser import MarkdownParser
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider

class QueryPlannerService:
    """
    Implements the Query Planner (Sections 33 & 34 of specification).
    Retrieves evidence from atomic notes, MOCs, and YAML frontmatter across requested domains
    and constructs context-aware answers with provenance citations.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.parser = MarkdownParser()
        self.llm = llm_provider or OllamaProvider()

    def query(self, domain: str, question: str) -> Dict[str, Any]:
        # Collect relevant notes
        target_domains = ["personal", "research", "business", "competitive"] if domain.lower() in ["all", "global"] else [domain]
        
        notes_context = []
        for d in target_domains:
            domain_dir = self.root_dir / "wiki" / d
            if domain_dir.exists():
                for md_path in domain_dir.glob("**/*.md"):
                    try:
                        parsed = self.parser.parse_file(md_path)
                        rel_path = md_path.relative_to(self.root_dir)
                        title = parsed.get("title", md_path.stem)
                        content = parsed.get("content", "")[:600]
                        notes_context.append({
                            "path": str(rel_path),
                            "title": title,
                            "domain": d,
                            "content": content,
                            "tags": parsed.get("tags", [])
                        })
                    except Exception:
                        pass

        # Also check MOCs
        mocs_dir = self.root_dir / "mocs"
        if mocs_dir.exists():
            for moc_path in mocs_dir.glob("*.md"):
                rel_path = moc_path.relative_to(self.root_dir)
                notes_context.append({
                    "path": str(rel_path),
                    "title": f"MOC: {moc_path.stem}",
                    "domain": "moc",
                    "content": moc_path.read_text(encoding="utf-8")[:400],
                    "tags": ["moc"]
                })

        # Build context summary
        context_str = "Obsidian Vault Knowledge Base Notes:\n\n"
        for idx, item in enumerate(notes_context, 1):
            context_str += f"[{idx}] Note Path: `{item['path']}` | Title: {item['title']}\nSummary:\n{item['content']}\n\n"

        prompt = (
            f"Question: {question}\n\n"
            f"Retrieved Vault Context:\n{context_str}\n\n"
            "Answer the question accurately based on the retrieved context above. "
            "List all relevant subjects/notes found and include citation paths."
        )

        try:
            answer = self.llm.generate(prompt, system_prompt="You are a Knowledge Assistant for Obsidian LLM Wiki.")
            if "Fallback" in answer or not answer:
                answer = self._format_structured_context_answer(question, notes_context)
        except Exception:
            answer = self._format_structured_context_answer(question, notes_context)

        return {
            "domain": domain,
            "question": question,
            "answer": answer,
            "retrieved_notes_count": len(notes_context)
        }

    def _format_structured_context_answer(self, question: str, notes: List[Dict[str, Any]]) -> str:
        res = f"### Obsidian Vault Subjects & Notes Summary\n\n"
        res += f"Found **{len(notes)} notes** in your vault:\n\n"
        for item in notes:
            res += f"- **{item['title']}** (`{item['path']}`)\n"
            if item['content']:
                snippet = item['content'].strip().replace("\n", " ")[:150]
                res += f"  > {snippet}...\n"
        return res

