import json
import re
import uuid
import frontmatter
from pathlib import Path
from typing import Union, Optional, List
from datetime import date
from app.schemas.claim import ContradictionModel, ClaimModel
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider

class ContradictionService:
    """
    Implements Contradiction Tracking (Section 22 of specification).
    Preserves conflicting evidence explicitly in wiki/{domain}/contradictions/{topic}.md
    without silently resolving or overriding.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.llm = llm_provider or OllamaProvider()

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

    def detect_contradictions(self, new_claims: List[str], domain: str, source_identifier: str) -> List[Path]:
        """
        Scans existing notes in the domain to detect any substantive contradictions
        against newly extracted claims. If found, records contradiction notes.
        """
        recorded_paths = []
        if not new_claims:
            return recorded_paths

        domain_dir = self.root_dir / "wiki" / domain
        if not domain_dir.exists():
            return recorded_paths

        # Scan existing notes for keyword matches
        existing_notes = list(domain_dir.glob("**/*.md"))
        for claim in new_claims:
            tokens = [w.lower() for w in re.findall(r'[\u0590-\u05FFa-zA-Z0-9_-]{4,}', claim)]
            if not tokens:
                continue

            for note_path in existing_notes:
                if "contradictions" in note_path.parts:
                    continue
                try:
                    post = frontmatter.load(note_path)
                    content = post.content
                    # Fast keyword pre-filter: at least 2 tokens must match
                    matching_tokens = [tok for tok in tokens if tok in content.lower()]
                    if len(matching_tokens) < 2:
                        continue

                    # Evaluate contradiction via local Ollama
                    prompt = (
                        f"Existing Vault Note Statement ({note_path.name}):\n\"{content[:500]}\"\n\n"
                        f"New Claim from {source_identifier}:\n\"{claim}\"\n\n"
                        "Do these statements DIRECTLY contradict each other on facts, methods, or conclusions? "
                        "Respond STRICTLY in JSON format with keys:\n"
                        "- is_contradiction (boolean: true/false)\n"
                        "- topic (string: 2-5 words topic of dispute)\n"
                        "- explanation (string: why they contradict)\n"
                        "- synthesis (string: balanced synthesis)\n"
                        "- uncertainty (string: remaining unknown)\n"
                    )
                    raw_res = self.llm.generate(prompt, system_prompt="You are a contradiction detection evaluator for scientific knowledge.")
                    
                    # Parse JSON safely
                    m = re.search(r'\{.*\}', raw_res, re.DOTALL)
                    if m:
                        data = json.loads(m.group(0))
                        if data.get("is_contradiction"):
                            model = ContradictionModel(
                                topic=data.get("topic") or "Contradictory Findings",
                                domain=domain,
                                claim_a=ClaimModel(
                                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                                    text=content[:250],
                                    claim_type="claim",
                                    domain=domain,
                                    source=str(note_path.relative_to(self.root_dir))
                                ),
                                claim_b=ClaimModel(
                                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                                    text=claim,
                                    claim_type="claim",
                                    domain=domain,
                                    source=source_identifier
                                ),
                                method_differences=data.get("explanation"),
                                possible_explanation="Differing experimental setups or population samples.",
                                current_synthesis=data.get("synthesis") or "Both claims are preserved pending further replication.",
                                remaining_uncertainty=data.get("uncertainty") or "Mechanisms require further validation."
                            )
                            c_path = self.record_contradiction(model)
                            recorded_paths.append(c_path)
                except Exception:
                    continue

        return recorded_paths

