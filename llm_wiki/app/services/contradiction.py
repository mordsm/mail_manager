import json
import re
import uuid
import frontmatter
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
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

    def list_contradictions(self) -> List[Dict[str, Any]]:
        """
        Scans vault for contradiction notes and returns structured list.
        """
        contradictions = []
        for path in self.root_dir.glob("wiki/**/contradictions/*.md"):
            try:
                post = frontmatter.load(path)
                content = post.content
                
                # Extract claims from markdown body
                claim_a_match = re.search(r"## Claim A\s*\n- \*\*Statement\*\*:\s*(.*?)\n- \*\*Source\*\*:\s*`(.*?)`", content, re.DOTALL)
                claim_b_match = re.search(r"## Claim B\s*\n- \*\*Statement\*\*:\s*(.*?)\n- \*\*Source\*\*:\s*`(.*?)`", content, re.DOTALL)
                
                synthesis_match = re.search(r"## Current Synthesis\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
                uncertainty_match = re.search(r"## Remaining Uncertainty\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)

                domain = post.get("domain", ["research"])
                if isinstance(domain, list):
                    domain_val = domain[0] if domain else "research"
                else:
                    domain_val = str(domain)

                contradictions.append({
                    "id": post.get("id") or path.stem,
                    "topic": post.get("topic") or path.stem.replace("-", " ").title(),
                    "domain": domain_val,
                    "status": post.get("status", "unresolved"),
                    "created": str(post.get("created", "")),
                    "updated": str(post.get("updated", "")),
                    "claim_a": {
                        "text": claim_a_match.group(1).strip() if claim_a_match else "Claim A details recorded in file.",
                        "source": claim_a_match.group(2).strip() if claim_a_match else ""
                    },
                    "claim_b": {
                        "text": claim_b_match.group(1).strip() if claim_b_match else "Claim B details recorded in file.",
                        "source": claim_b_match.group(2).strip() if claim_b_match else ""
                    },
                    "current_synthesis": synthesis_match.group(1).strip() if synthesis_match else "",
                    "remaining_uncertainty": uncertainty_match.group(1).strip() if uncertainty_match else "",
                    "resolution": post.get("resolution"),
                    "rationale": post.get("rationale"),
                    "resolved_by": post.get("resolved_by"),
                    "path": str(path.relative_to(self.root_dir))
                })
            except Exception:
                continue

        return contradictions

    def resolve_contradiction(
        self,
        contradiction_id: str,
        resolution: str,
        rationale: str,
        resolved_by: str = "human"
    ) -> Dict[str, Any]:
        """
        Resolves a contradiction explicitly per AGENTS.md rule:
        'Never silently resolve contradictory evidence. Human owns judgment.'
        """
        target_path = None
        for path in self.root_dir.glob("wiki/**/contradictions/*.md"):
            if path.stem == contradiction_id or f"{contradiction_id}.md" == path.name:
                target_path = path
                break

        if not target_path or not target_path.exists():
            return {"status": "ERROR", "message": f"Contradiction {contradiction_id} not found."}

        post = frontmatter.load(target_path)
        post["status"] = "resolved"
        post["resolution"] = resolution
        post["rationale"] = rationale
        post["resolved_by"] = resolved_by
        post["updated"] = date.today().isoformat()

        resolution_block = (
            f"\n\n## Resolution Decision\n"
            f"- **Status**: Resolved\n"
            f"- **Resolution**: {resolution}\n"
            f"- **Rationale**: {rationale}\n"
            f"- **Resolved By**: `{resolved_by}`\n"
            f"- **Resolved Date**: {date.today().isoformat()}\n"
        )
        post.content += resolution_block

        with open(target_path, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        return {
            "status": "RESOLVED",
            "id": contradiction_id,
            "path": str(target_path.relative_to(self.root_dir)),
            "resolution": resolution,
            "rationale": rationale
        }

