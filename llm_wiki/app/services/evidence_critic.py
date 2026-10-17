import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import frontmatter

from app.llm.base import LLMProvider
from app.llm import get_llm_provider
from app.services.contradiction import ContradictionService
from app.schemas.claim import ContradictionModel, ClaimModel

class EvidenceCriticService:
    """
    Evidence Critic Service (Section 11 & Section 23 of AGENTS.md):
    Attacks prevailing research conclusions, detects causal overreach from observational data,
    evaluates publication/funding bias, sample size adequacy, and mechanistic-to-clinical conflation.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.llm = llm_provider or get_llm_provider()
        self.contradiction_service = ContradictionService(root_dir=self.root_dir)

    def critique_research_topic(self, topic_path: Union[str, Path]) -> Dict[str, Any]:
        target = Path(topic_path)
        if not target.is_absolute():
            target = self.root_dir / topic_path

        if target.is_dir():
            target = target / "overview.md"

        if not target.exists():
            return {"status": "ERROR", "message": f"Target not found: {topic_path}"}

        content = target.read_text(encoding="utf-8")
        title = target.parent.name.replace("_", " ").title()

        # Heuristic Risk Detection (Rule-based checks)
        heuristic_risks = []
        lower_content = content.lower()

        # 1. Causal Language Check
        causal_words = ["proves", "causes", "cures", "prevents", "eradicates", "מוכיח", "מרפא", "גורם באופן מוחלט"]
        for w in causal_words:
            if w in lower_content:
                heuristic_risks.append(f"Potential Causal Overreach: Found strong causal term '{w}' in evidence text.")

        # 2. Mechanistic / Animal to Clinical Generalization Check
        if ("animal" in lower_content or "mouse" in lower_content or "in-vitro" in lower_content or "עכבר" in lower_content) and ("clinical" in lower_content or "treatment" in lower_content):
            heuristic_risks.append("Preclinical to Clinical Leap: Animal or in-vitro models mentioned alongside clinical treatment claims.")

        # 3. Single Source Reliance
        study_links = re.findall(r"\[\[([^\]]+)\]\]", content)
        if len(study_links) <= 2:
            heuristic_risks.append(f"Small Evidence Base: Conclusion supported by only {len(study_links)} cited study/entity reference(s).")

        # 4. Deep Adversarial Critique using Local LLM
        prompt = (
            f"Topic: {title}\n"
            f"Research Evidence Text:\n{content[:2500]}\n\n"
            "As an adversarial Research Critic following strict scientific methodology:\n"
            "1. Identify critical methodological issues or potential confounders.\n"
            "2. Are there alternative explanations or missing negative studies?\n"
            "3. Identify bias risks (publication bias, small sample sizes, industry bias).\n"
            "4. Provide a concrete falsification test or recommended follow-up study."
        )

        try:
            critique_text = self.llm.generate(
                prompt,
                system_prompt="You are an uncompromising Scientific Research Critic. Actively challenge claims and look for reasons the conclusion might be invalid or incomplete."
            )
        except Exception as e:
            critique_text = f"LLM critique skipped ({e}). Heuristic audit completed."

        # Save critique note in wiki/research/critiques/
        critique_dir = self.root_dir / "wiki" / "research" / "critiques"
        critique_dir.mkdir(parents=True, exist_ok=True)
        critique_file = critique_dir / f"critic_{target.parent.name}.md"

        critique_body = (
            f"# Adversarial Research Critique: {title}\n\n"
            f"**Target Note**: `{target.relative_to(self.root_dir)}`\n"
            f"**Critique Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"## Heuristic Bias & Validity Risks ({len(heuristic_risks)})\n"
        )
        for r in heuristic_risks:
            critique_body += f"- ⚠️ **{r}**\n"
        if not heuristic_risks:
            critique_body += "- No glaring heuristic violations detected in direct text.\n"

        critique_body += f"\n## In-Depth Methodological Critique\n{critique_text}\n"

        critique_file.write_text(critique_body, encoding="utf-8")

        return {
            "status": "COMPLETED",
            "topic": title,
            "critique_file": str(critique_file.relative_to(self.root_dir)),
            "heuristic_risks_count": len(heuristic_risks),
            "heuristic_risks": heuristic_risks,
            "critique_summary": critique_text[:400]
        }

    def audit_all_research_topics(self) -> List[Dict[str, Any]]:
        research_dir = self.root_dir / "20_Research"
        results = []
        if not research_dir.exists():
            return results

        for topic_dir in research_dir.iterdir():
            if topic_dir.is_dir() and (topic_dir / "overview.md").exists():
                res = self.critique_research_topic(topic_dir)
                results.append(res)

        return results

