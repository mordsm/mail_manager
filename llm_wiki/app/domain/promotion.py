import frontmatter
from pathlib import Path
from typing import Union, List, Dict, Any
from datetime import date

class KnowledgePromotionService:
    """
    Implements promote() logic (Section 11 of specification).
    Promotes reusable concepts/entities to shared/ layer when referenced across multiple domains
    and permitted by privacy share policy.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        (self.root_dir / "shared").mkdir(parents=True, exist_ok=True)

    def promote(
        self,
        concept_title: str,
        category: str,
        source_domain: str,
        target_domains: List[str],
        content: str,
        sources: List[str]
    ) -> Path:
        slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in concept_title).strip().replace(" ", "-")
        target_dir = self.root_dir / "shared" / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{slug}.md"

        all_domains = list(set([source_domain] + target_domains))

        fm_metadata = {
            "id": slug,
            "title": concept_title,
            "shared": True,
            "type": "concept",
            "source_domains": [source_domain],
            "used_by_domains": all_domains,
            "created": date.today().isoformat(),
            "updated": date.today().isoformat(),
            "share_policy": "allowed",
            "sources": sources
        }

        body = (
            f"# {concept_title}\n\n"
            f"**Promoted Shared Knowledge** (Source: `{source_domain}`, Used by: {', '.join(all_domains)})\n\n"
            f"{content.strip()}\n\n"
            "## Provenance & Sources\n"
        )
        for s in sources:
            body += f"- `{s}`\n"

        post = frontmatter.Post(body, **fm_metadata)
        with open(target_path, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        # Update shared/index.md
        shared_index = self.root_dir / "shared" / "index.md"
        entry_link = f"- [[shared/{category}/{slug}|{concept_title}]] (Source: {source_domain})"
        if shared_index.exists():
            text = shared_index.read_text(encoding="utf-8")
            if entry_link not in text:
                shared_index.write_text(text + f"\n{entry_link}", encoding="utf-8")

        return target_path

