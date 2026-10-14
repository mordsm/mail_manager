import yaml
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from datetime import datetime

class ProactiveCollectorService:
    """
    Implements Proactive Ingestion (Sections 28-30 of specification).
    Manages recurring prompt schedules in system/proactive/ for financial, health, and research updates.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.proactive_dir = self.root_dir / "system" / "proactive"
        self.proactive_dir.mkdir(parents=True, exist_ok=True)
        self._init_default_configs()

    def _init_default_configs(self) -> None:
        defaults = [
            {
                "id": "daily-personal-log",
                "domain": "personal",
                "frequency": "daily",
                "question": "How was your physical & mental state today? Any training or insights?",
                "output_type": "observation"
            },
            {
                "id": "weekly-research-synthesis",
                "domain": "research",
                "frequency": "weekly",
                "question": "What core technical concepts or papers did you explore this week?",
                "output_type": "synthesis"
            },
            {
                "id": "monthly-finance-update",
                "domain": "business",
                "frequency": "monthly",
                "question": "Please update monthly revenue, expenses, and strategic decisions.",
                "output_type": "metric_update"
            }
        ]
        for config in defaults:
            cfg_path = self.proactive_dir / f"{config['id']}.yaml"
            if not cfg_path.exists():
                with open(cfg_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f)

    def get_pending_prompts(self) -> List[Dict[str, Any]]:

        prompts = []
        for cfg_file in self.proactive_dir.glob("*.yaml"):
            with open(cfg_file, "r", encoding="utf-8") as f:
                prompts.append(yaml.safe_load(f))
        return prompts

import re
import frontmatter
from app.services.auditor import WikiAuditorService
from app.services.hybrid_rag import HybridRAGService
from app.services.moc_service import MOCService
from app.services.vector_service import VectorIndexService

class ProactiveGapFillerService:
    """
    Proactive Knowledge Gap Filler (Sections 28-30 & Section 37 of AGENTS.md):
    Autonomously scans the Obsidian Vault for broken reference targets, isolated orphan notes,
    and unresolved empirical uncertainties, and generates targeted research passes to bridge the gaps.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.auditor = WikiAuditorService(root_dir=self.root_dir)
        self.rag = HybridRAGService(root_dir=self.root_dir)
        self.moc_service = MOCService(root_dir=self.root_dir)
        self.vector_service = VectorIndexService(root_dir=self.root_dir)

    def scan_knowledge_gaps(self) -> List[Dict[str, Any]]:
        audit_report = self.auditor.audit_vault()
        gaps = []

        # 1. Broken Links (Missing expected concepts/entities)
        for bl in audit_report.get("broken_links", []):
            target = bl["target_link"].strip()
            if not target or target.startswith("^"):
                continue
            slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in target).strip().replace(" ", "-")
            gap_id = f"gap_link_{slug}"
            gaps.append({
                "gap_id": gap_id,
                "type": "broken_link",
                "title": target,
                "source": bl["source_note"],
                "domain": "research" if "research" in bl["source_note"].lower() else "personal",
                "priority": "HIGH",
                "description": f"Missing concept note [[{target}]] referenced in {bl['source_note']}",
                "suggested_query": f"Synthesize core scientific concepts, definitions, and mechanisms for: {target}"
            })

        # 2. Orphan Notes (Isolated islands lacking MOC integration)
        for orphan in audit_report.get("orphan_notes", [])[:10]:
            orphan_clean = orphan.replace("[[", "").replace("]]", "").strip()
            slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in orphan_clean).strip().replace(" ", "-")
            gaps.append({
                "gap_id": f"gap_orphan_{slug}",
                "type": "orphan_note",
                "title": orphan_clean,
                "source": "isolated_vault_node",
                "domain": "research" if "research" in orphan_clean.lower() else "wiki",
                "priority": "MEDIUM",
                "description": f"Orphan note with 0 backlinks. Needs semantic linking into domain MOC and parent concepts.",
                "suggested_query": f"Identify semantic parent concepts and cross-domain links for: {orphan_clean}"
            })

        # 3. Unresolved Contradictions
        for c in audit_report.get("unresolved_contradictions", []):
            slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in c).strip().replace(" ", "-")
            gaps.append({
                "gap_id": f"gap_contra_{slug}",
                "type": "unresolved_contradiction",
                "title": c,
                "source": "wiki/contradictions",
                "domain": "research",
                "priority": "HIGH",
                "description": f"Unresolved empirical contradiction in evidence vault: {c}",
                "suggested_query": f"Evaluate reconciling mechanisms, dose dependencies, or cohort differences for: {c}"
            })

        priority_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        gaps.sort(key=lambda x: priority_weights.get(x["priority"], 0), reverse=True)
        return gaps

    def fill_gap(self, gap_id: str, custom_query: Optional[str] = None) -> Dict[str, Any]:
        gaps = self.scan_knowledge_gaps()
        target_gap = next((g for g in gaps if g["gap_id"] == gap_id), None)
        if not target_gap:
            return {"status": "ERROR", "message": f"Gap {gap_id} not found."}

        query = custom_query or target_gap["suggested_query"]
        domain = target_gap.get("domain", "research")
        title = target_gap["title"]

        if target_gap["type"] == "broken_link":
            # 1. Synthesize target note via Hybrid RAG
            rag_res = self.rag.query(question=query, domain=domain, allow_web_fallback=True)
            answer = rag_res.get("answer", "")
            citations = rag_res.get("citations", [])

            # 2. Save note to wiki/{domain}/concepts/{slug}.md
            slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in title).strip().replace(" ", "-")
            target_dir = self.root_dir / "wiki" / domain / "concepts"
            target_dir.mkdir(parents=True, exist_ok=True)
            note_path = target_dir / f"{slug}.md"

            post_meta = {
                "title": title,
                "type": "concept",
                "domain": [domain],
                "created": datetime.now().strftime("%Y-%m-%d"),
                "status": "proactively_synthesized",
                "origin_gap": gap_id,
                "referenced_by": [target_gap["source"]]
            }
            body = (
                f"# {title}\n\n"
                f"> Proactively synthesized knowledge unit to bridge vault gap referenced in `{target_gap['source']}`.\n\n"
                f"## Synthesis & Definition\n{answer}\n\n"
                f"## Citations & Evidence Base\n"
            )
            for c in citations:
                if isinstance(c, dict):
                    body += f"- **[{c.get('block_id', 'ref')}]**: {c.get('title', 'Ref')} (`{c.get('note_path', '')}`)\n"
                else:
                    body += f"- {c}\n"

            post = frontmatter.Post(body, **post_meta)
            with open(note_path, "w", encoding="utf-8") as f:
                frontmatter.dump(post, f)

            # 3. Index into vector embeddings
            try:
                self.vector_service.index_block(
                    block_id=slug,
                    content=answer[:1200],
                    note_path=str(note_path.relative_to(self.root_dir)),
                    note_title=title,
                    domain=domain
                )
            except Exception:
                pass

            # 4. Update MOC
            try:
                self.moc_service.update_moc(f"{domain.capitalize()} MOC", "Concepts", title)
            except Exception:
                pass

            return {
                "status": "GAP_FILLED",
                "gap_id": gap_id,
                "gap_type": target_gap["type"],
                "note_title": title,
                "note_path": str(note_path.relative_to(self.root_dir)),
                "synthesis": answer[:300] + "..."
            }

        elif target_gap["type"] == "orphan_note":
            self.moc_service.update_moc(f"{domain.capitalize()} MOC", "General Synthesis", title)
            similar_notes = self.vector_service.search_similar(title, top_k=3)
            return {
                "status": "GAP_FILLED",
                "gap_id": gap_id,
                "gap_type": target_gap["type"],
                "note_title": title,
                "action": "Linked into MOC and discovered semantic neighbors",
                "related_notes": [s["note_title"] for s in similar_notes]
            }

        else:
            return {
                "status": "REQUIRES_HUMAN_INTERVENTION",
                "gap_id": gap_id,
                "message": "Contradictions must be resolved by human supervisor per AGENTS.md rule."
            }
