import frontmatter
from pathlib import Path
from typing import Union, Optional
from datetime import date
from app.schemas.claim import ContradictionModel

class ContradictionService:
    """
    Implements Contradiction Tracking (Section 22 of specification).
    Preserves conflicting evidence explicitly in wiki/{domain}/contradictions/{topic}.md
    without silently resolving or overriding.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)

    def record_contradiction(self, model: ContradictionModel) -> Path:
        slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in model.topic).strip().replace(" ", "-")
        target_dir = self.root_dir / "wiki" / model.domain / "contradictions"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{slug}.md"

        fm_metadata = {
            "id": slug,
            "type": "contradiction",
            "domain": [model.domain],
            "source_domain": [model.domain],
            "topic": model.topic,
            "created": date.today().isoformat(),
            "updated": date.today().isoformat(),
            "status": "unresolved"
        }

        body = (
            f"# Contradiction Analysis: {model.topic}\n\n"
            "## Claim A\n"
            f"- **Statement**: {model.claim_a.text}\n"
            f"- **Source**: `{model.claim_a.source}`\n"
            f"- **Confidence**: {model.claim_a.confidence}\n\n"
            "## Claim B\n"
            f"- **Statement**: {model.claim_b.text}\n"
            f"- **Source**: `{model.claim_b.source}`\n"
            f"- **Confidence**: {model.claim_b.confidence}\n\n"
            "## Methodological Differences\n"
            f"{model.method_differences or 'No explicit methodological difference recorded.'}\n\n"
            "## Possible Explanation\n"
            f"{model.possible_explanation or 'Under evaluation.'}\n\n"
            "## Current Synthesis\n"
            f"{model.current_synthesis}\n\n"
            "## Remaining Uncertainty\n"
            f"{model.remaining_uncertainty}\n"
        )

        post = frontmatter.Post(body, **fm_metadata)
        with open(target_path, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        return target_path

