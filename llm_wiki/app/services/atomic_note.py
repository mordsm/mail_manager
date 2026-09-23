import frontmatter
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import date
from app.schemas.frontmatter import WikiFrontmatter, DomainType, PageType

class AtomicNoteService:
    """
    Manages creation and updates of Atomic Notes in wiki/{domain}/.
    Enforces frontmatter schema, source provenance links, and [[Wikilinks]].
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)

    def create_or_update_note(
        self,
        title: str,
        domain: DomainType,
        note_type: PageType,
        content: str,
        sources: List[str],
        related: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        confidence: str = "medium"
    ) -> Path:
        slug = self._slugify(title)
        subfolder = self._map_type_to_subfolder(note_type)
        target_dir = self.root_dir / "wiki" / domain / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{slug}.md"

        related = related or []
        tags = tags or []

        # Check existing note to preserve created date and metadata
        created_date = date.today().isoformat()
        existing_sources = []
        existing_related = []

        if target_path.exists():
            post = frontmatter.load(target_path)
            created_date = post.metadata.get("created", created_date)
            existing_sources = post.metadata.get("sources", [])
            existing_related = post.metadata.get("related", [])

            # Check if user marked ai_edit: false
            if post.metadata.get("ai_edit") is False:
                print(f"Skipping AI update for user-protected note: {target_path}")
                return target_path

        combined_sources = list(set(existing_sources + sources))
        combined_related = list(set(existing_related + related))

        fm = WikiFrontmatter(
            id=slug,
            type=note_type,
            domain=[domain],
            source_domain=[domain],
            created=created_date,
            updated=date.today().isoformat(),
            confidence=confidence,
            sources=combined_sources,
            related=combined_related,
            tags=tags,
            ai_edit=True
        )

        body = (
            f"# {title}\n\n"
            f"{content.strip()}\n\n"
            "## Provenance & Sources\n"
        )
        for src in combined_sources:
            body += f"- `{src}`\n"

        if combined_related:
            body += "\n## Related Notes\n"
            for rel in combined_related:
                body += f"- {rel}\n"

        post = frontmatter.Post(body, **fm.model_dump())
        with open(target_path, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        return target_path

    def _slugify(self, text: str) -> str:
        clean = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in text)
        return clean.strip().replace(" ", "-")

    def _map_type_to_subfolder(self, note_type: str) -> str:
        mapping = {
            "concept": "concepts",
            "entity": "entities",
            "person": "entities",
            "company": "entities",
            "technology": "technologies",
            "project": "projects",
            "claim": "claims",
            "evidence": "evidence",
            "hypothesis": "hypotheses",
            "question": "questions",
            "decision": "decisions",
            "signal": "signals",
            "experiment": "experiments",
            "comparison": "comparisons",
            "synthesis": "synthesis",
            "source_summary": "topics"
        }
        return mapping.get(note_type, "topics")

    def find_matching_note(self, query: str, domain: Optional[str] = None) -> Optional[Path]:
        query_slug = self._slugify(query)
        if not query_slug:
            return None
        search_dirs = []
        if domain and domain != "unclassified":
            search_dirs.append(self.root_dir / "wiki" / domain)
        else:
            wiki_dir = self.root_dir / "wiki"
            if wiki_dir.exists():
                search_dirs = [d for d in wiki_dir.iterdir() if d.is_dir()]

        for d in search_dirs:
            for md_file in d.glob("**/*.md"):
                if md_file.name == "log.md":
                    continue
                file_slug = md_file.stem.lower()
                if query_slug == file_slug or (len(query_slug) > 3 and (query_slug in file_slug or file_slug in query_slug)):
                    return md_file
        return None

    def append_to_note(self, target_path: Path, content: str) -> Path:
        if not target_path.exists():
            return target_path

        post = frontmatter.load(target_path)

        if post.metadata.get("ai_edit") is False:
            print(f"Skipping AI update for user-protected note: {target_path}")
            return target_path

        post.metadata["updated"] = date.today().isoformat()
        today_str = date.today().isoformat()
        append_block = f"\n\n### Observation ({today_str})\n{content.strip()}\n"

        body = post.content
        if "## Provenance & Sources" in body:
            parts = body.split("## Provenance & Sources", 1)
            new_body = parts[0].rstrip() + append_block + "\n## Provenance & Sources" + parts[1]
        elif "## Related Notes" in body:
            parts = body.split("## Related Notes", 1)
            new_body = parts[0].rstrip() + append_block + "\n## Related Notes" + parts[1]
        else:
            new_body = body.rstrip() + append_block

        post.content = new_body

        with open(target_path, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        return target_path

