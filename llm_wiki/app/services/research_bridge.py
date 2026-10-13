import json
import sqlite3
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from app.services.atomic_note import AtomicNoteService
from app.services.moc_service import MOCService
from app.services.git_service import GitService
from app.services.contradiction import ContradictionService
from app.schemas.claim import ContradictionModel

class ResearchBridgeService:
    """
    Research Bridge Service: Ingests structured multi-agent scientific/medical research states
    from the Research Manager (LangGraph / AGENTS.md engine) into LLM Wiki Obsidian vault layers
    (20_Research/, wiki/research/topics/, 40_Decisions/, and 10_Projects/research_manager).
    """
    def __init__(
        self,
        root_dir: Union[str, Path] = ".",
        research_db_path: Union[str, Path] = "C:/workspace/research_manager/data/research_manager.db"
    ):
        self.root_dir = Path(root_dir)
        self.research_db_path = Path(research_db_path)
        self.atomic_service = AtomicNoteService(root_dir=self.root_dir)
        self.moc_service = MOCService(root_dir=self.root_dir)
        self.git_service = GitService(root_dir=self.root_dir)
        self.contradiction_service = ContradictionService(root_dir=self.root_dir)

    def is_db_available(self) -> bool:
        return self.research_db_path.exists()

    def sync_all_research(self) -> Dict[str, Any]:
        if not self.is_db_available():
            return {
                "status": "SKIPPED",
                "message": f"Research Manager database not found at {self.research_db_path}",
                "synced_count": 0
            }

        conn = sqlite3.connect(str(self.research_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT research_id, state_json, updated_at FROM research_states")
        rows = cursor.fetchall()
        conn.close()

        synced_records = []
        for r_id, raw_json, updated_at in rows:
            try:
                state_data = json.loads(raw_json)
                final_report = state_data.get("final_report")
                primary_q = state_data.get("primary_question") or "Research Investigation"

                if not final_report:
                    continue

                topic_slug = re.sub(r'[\W_]+', '_', primary_q.strip()).lower().strip('_')[:50] or r_id
                res_dir = self.root_dir / "20_Research" / topic_slug
                res_dir.mkdir(parents=True, exist_ok=True)
                overview_file = res_dir / "overview.md"

                # Extract claims, evidence, and contradictions
                claims = state_data.get("claims", [])
                contradictions = state_data.get("contradictions", [])
                studies = state_data.get("included_studies", [])
                hypotheses = state_data.get("active_hypotheses", [])

                claims_md = []
                for c in claims:
                    claims_md.append(f"- **{c.get('text')}** (Type: `{c.get('claim_type')}`, Strength: `{c.get('evidence_strength')}`)")

                studies_md = []
                for s in studies[:10]:
                    studies_md.append(f"- [[{s.get('citation') or s.get('study_id')}]] - {s.get('study_type', 'Study')} ({s.get('year', 'N/A')})")

                report_text = final_report.get("executive_summary", "") if isinstance(final_report, dict) else str(final_report)

                body = (
                    f"# Research Synthesis: {primary_q}\n\n"
                    f"**Research ID**: `{r_id}` | **Updated**: {updated_at}\n"
                    f"**Stopping Reason**: {state_data.get('stopping_reason', 'COMPLETED')}\n\n"
                    f"## Executive Summary\n{report_text}\n\n"
                    f"## Evidence-Based Claims ({len(claims)})\n"
                    f"{chr(10).join(claims_md) if claims_md else 'No formal claims generated.'}\n\n"
                    f"## Material Included Studies ({len(studies)})\n"
                    f"{chr(10).join(studies_md) if studies_md else 'None recorded.'}\n\n"
                    f"## Hypotheses Explored\n"
                )
                for h in hypotheses:
                    body += f"- **{h.get('statement')}** (Status: `{h.get('status')}`)\n"

                overview_file.write_text(body, encoding="utf-8")

                # Ingest into atomic synthesis note
                self.atomic_service.create_or_update_note(
                    title=f"Research: {primary_q[:60]}",
                    domain="research",
                    note_type="synthesis",
                    content=report_text,
                    sources=[f"research_manager/{r_id}"],
                    tags=["research_manager", "evidence_synthesis"]
                )

                # Process contradictions if any
                from app.schemas.claim import ClaimModel
                for cd in contradictions:
                    try:
                        ca = ClaimModel(
                            claim_id=f"claim_{r_id[:6]}_a",
                            text=cd.get("claim_a", "Primary observation"),
                            claim_type="claim",
                            domain="research",
                            source=r_id
                        )
                        cb = ClaimModel(
                            claim_id=f"claim_{r_id[:6]}_b",
                            text=cd.get("claim_b", "Counter observation"),
                            claim_type="claim",
                            domain="research",
                            source=r_id
                        )
                        contra_model = ContradictionModel(
                            topic=cd.get("topic") or primary_q[:40],
                            domain="research",
                            claim_a=ca,
                            claim_b=cb,
                            current_synthesis="Contradiction flagged during critic review in Research Manager.",
                            remaining_uncertainty="Requires further experimental verification."
                        )
                        self.contradiction_service.record_contradiction(contra_model)
                    except Exception:
                        pass

                synced_records.append({
                    "research_id": r_id,
                    "question": primary_q,
                    "overview_file": str(overview_file.relative_to(self.root_dir))
                })
            except Exception:
                continue

        # Append to domain log & commit to git
        if synced_records:
            self.moc_service.append_domain_log("research", f"Synced {len(synced_records)} research syntheses from Research Manager")
            self.git_service.commit(f"research(sync): import {len(synced_records)} research syntheses from research_manager")

        return {
            "status": "COMPLETED",
            "synced_count": len(synced_records),
            "records": synced_records
        }
