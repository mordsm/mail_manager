import re
import zipfile
import shutil
from pathlib import Path
from typing import Union, Dict, Any, Optional
from app.services.inbox_service import InboxIngestionService
from app.services.parser import MarkdownParser
from app.services.atomic_note import AtomicNoteService
from app.services.moc_service import MOCService
from app.services.git_service import GitService
from app.services.contradiction import ContradictionService
from app.llm.base import LLMProvider
from app.llm import get_llm_provider

class LLMWikiPipeline:
    """
    End-to-End Orchestrator for LLM Wiki Ingestion, Synthesis, MOC Maintenance, and Versioning.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.inbox_service = InboxIngestionService(root_dir=self.root_dir)
        self.parser = MarkdownParser()
        self.atomic_service = AtomicNoteService(root_dir=self.root_dir)
        self.moc_service = MOCService(root_dir=self.root_dir)
        self.git_service = GitService(root_dir=self.root_dir)
        self.llm = llm_provider or get_llm_provider()
        self.contradiction_service = ContradictionService(root_dir=self.root_dir, llm_provider=self.llm)

    def process_file(self, source_path: Union[str, Path], domain: str = "unclassified") -> Dict[str, Any]:
        # 1. Receive & Save Raw Immutable Copy
        job = self.inbox_service.ingest_file(source_path, domain=domain)
        if job.status == "DUPLICATE":
            return {"status": "DUPLICATE", "job": job.model_dump()}

        raw_path = Path(job.target_raw_path)

        # 2. Parse Source Content
        parsed_data = {}
        if raw_path.suffix.lower() in [".md", ".txt", ".docx", ".pdf"]:
            parsed_data = self.parser.parse_file(raw_path)
            content = parsed_data.get("content", "")
        else:
            content = f"Source binary asset preserved at {raw_path.name}"

        target_domain = domain if domain != "unclassified" else "research"

        # 2b. Check if content represents a multi-chapter book or manual
        chapter_matches = list(re.finditer(r"(?m)^(?:##\s+)?(פרק\s+\d+|שער\s+[א-ת]|נספח\s+[א-ת]|Chapter\s+\d+[:\s—\-].*)", content))
        if len(chapter_matches) >= 3 or (raw_path.suffix.lower() in [".docx", ".pdf"] and len(content) > 15000 and "פרק" in content):
            return self._process_book(raw_path, content, target_domain, job.job_id)

        # 3. AI Extraction
        extraction = self.llm.extract_entities_and_claims(content, domain=target_domain)

        # 3b. Automated Contradiction Detection against existing knowledge
        contradictions = self.contradiction_service.detect_contradictions(
            extraction.get("claims", []),
            target_domain,
            raw_path.name
        )

        # 4. Synthesize Atomic Note
        title = raw_path.stem.replace("_", " ").replace("-", " ").title()
        summary = extraction.get("summary", content[:500])
        concepts = extraction.get("concepts", [])
        for cp in contradictions:
            concepts.append(f"contradiction-{cp.stem}")

        note_path = self.atomic_service.create_or_update_note(
            title=title,
            domain=target_domain,
            note_type="source_summary",
            content=summary,
            sources=[str(raw_path.relative_to(self.root_dir))],
            related=[f"[[{c}]]" for c in concepts],
            tags=[target_domain]
        )

        # 5. Update MOC and Domain Log
        target_domain = domain if domain != "unclassified" else "research"
        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{note_path.stem}")
        self.moc_service.append_domain_log(target_domain, f"Ingested raw source: {raw_path.name}")

        # 6. Git Commit
        commit_msg = f"ingest({target_domain}): process {raw_path.name}"
        self.git_service.commit(commit_msg)

        return {
            "status": "COMPLETED",
            "job_id": job.job_id,
            "raw_path": str(raw_path),
            "note_path": str(note_path)
        }

    def process_text(self, content: str, title: str = "Untitled Note", domain: str = "research") -> Dict[str, Any]:
        target_domain = domain if domain and domain != "unclassified" else "research"

        # 1. Save Raw Immutable Copy
        job = self.inbox_service.ingest_text(content, title=title, domain=target_domain)
        if job.status == "DUPLICATE":
            return {"status": "DUPLICATE", "job": job.model_dump()}

        raw_path = Path(job.target_raw_path)

        # 2. AI Extraction
        extraction = self.llm.extract_entities_and_claims(content, domain=target_domain)

        # 3. Synthesize Atomic Note
        summary = extraction.get("summary", content[:500])
        concepts = extraction.get("concepts", [])

        note_path = self.atomic_service.create_or_update_note(
            title=title,
            domain=target_domain,
            note_type="concept",
            content=content if len(content) <= 1000 else f"{summary}\n\n## Content\n{content}",
            sources=[str(raw_path.relative_to(self.root_dir))] if raw_path.exists() else [],
            related=[f"[[{c}]]" for c in concepts],
            tags=[target_domain]
        )

        # 4. Update MOC and Domain Log
        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{note_path.stem}")
        self.moc_service.append_domain_log(target_domain, f"Ingested text note: {title}")

        # 5. Git Commit
        commit_msg = f"ingest({target_domain}): process note '{title}'"
        self.git_service.commit(commit_msg)

        return {
            "status": "COMPLETED",
            "job_id": job.job_id,
            "raw_path": str(raw_path),
            "note_path": str(note_path)
        }

    def smart_ingest(
        self,
        content: str,
        title: Optional[str] = None,
        domain: Optional[str] = None,
        direct: bool = True,
        append: bool = False
    ) -> Dict[str, Any]:
        """
        Zero-Cognitive-Load Ingestion:
        1. Auto-classifies domain if not explicitly provided.
        2. Auto-extracts title / topic if not explicitly provided.
        3. Auto-searches existing vault for matching notes.
        4. Appends to matching note or creates a clean atomic note directly.
        """
        extraction = self.llm.extract_entities_and_claims(content, domain=domain or "research")

        target_domain = domain if (domain and domain != "unclassified") else extraction.get("domain", "research")
        if target_domain not in ["personal", "research", "business", "competitive", "development"]:
            target_domain = "research"

        if not title or title == "Untitled Note":
            concepts = extraction.get("concepts", [])
            if concepts:
                target_title = concepts[0]
            else:
                words = content.strip().split()
                target_title = " ".join(words[:5]).title() if words else "Quick Note"
        else:
            target_title = title

        existing_note = self.atomic_service.find_matching_note(target_title, domain=target_domain)

        if existing_note and (append or existing_note.exists()):
            note_path = self.atomic_service.append_to_note(existing_note, content)
            action = "APPENDED"
        else:
            concepts = extraction.get("concepts", [])
            note_path = self.atomic_service.create_or_update_note(
                title=target_title,
                domain=target_domain,
                note_type="concept",
                content=content,
                sources=[],
                related=[f"[[{c}]]" for c in concepts],
                tags=[target_domain]
            )
            action = "CREATED"

        raw_path = None
        if not direct:
            job = self.inbox_service.ingest_text(content, title=target_title, domain=target_domain)
            raw_path = job.target_raw_path

        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{note_path.stem}")
        self.moc_service.append_domain_log(target_domain, f"Smart ingest [{action}]: {target_title}")
        self.git_service.commit(f"ingest({target_domain}): smart {action.lower()} '{target_title}'")

        return {
            "status": "COMPLETED",
            "action": action,
            "domain": target_domain,
            "title": target_title,
            "note_path": str(note_path),
            "raw_path": str(raw_path) if raw_path else "Skipped (Direct Mode)"
        }

    def _process_book(self, raw_path: Path, content: str, target_domain: str, job_id: str) -> Dict[str, Any]:
        """
        Processes a multi-chapter book or extensive manual:
        1. Cleans title and sets safe slug.
        2. Extracts embedded images (from docx) into wiki/assets/{slug}/.
        3. Saves full master book in wiki/{target_domain}/{slug}/.
        4. Segments book into atomic chapter notes.
        5. Generates dedicated Book MOC in mocs/{slug}_moc.md.
        6. Updates domain MOC and creates Git commit.
        """
        clean_title = raw_path.stem.replace("_", " ").replace("-", " ").strip()
        slug = re.sub(r'[^\w\-]+', '_', raw_path.stem).strip('_')
        if not slug or slug.lower().startswith("tmp"):
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            for line in lines[:5]:
                candidate = re.sub(r"^#+\s*", "", line).strip()
                if len(candidate) > 2 and len(candidate) < 60:
                    clean_title = candidate
                    slug = re.sub(r'[^\w\-]+', '_', clean_title).strip('_')
                    break
        if not slug:
            slug = f"book_{job_id[:8]}"

        # 1. Extract embedded images if docx
        assets_dir = self.root_dir / f"wiki/assets/{slug}"
        assets_dir.mkdir(parents=True, exist_ok=True)
        image_count = 0
        if raw_path.suffix.lower() == ".docx":
            try:
                with zipfile.ZipFile(raw_path) as z:
                    for name in z.namelist():
                        if name.startswith("word/media/"):
                            img_name = Path(name).name
                            target_img = assets_dir / img_name
                            with open(target_img, "wb") as f_out, z.open(name) as f_in:
                                shutil.copyfileobj(f_in, f_out)
                            image_count += 1
            except Exception:
                pass

        # 2. Directory structure
        book_dir = self.root_dir / "wiki" / target_domain / slug
        book_dir.mkdir(parents=True, exist_ok=True)

        # 3. Master Full Book Note
        full_book_filename = f"{slug}_ספר_שלם.md"
        full_book_path = book_dir / full_book_filename
        full_book_content = (
            f"---\n"
            f"title: \"{clean_title}\"\n"
            f"type: book\n"
            f"domain: {target_domain}\n"
            f"tags: [book, {target_domain}, {slug}]\n"
            f"source_raw: \"{raw_path.name}\"\n"
            f"status: active\n"
            f"---\n\n"
            f"# {clean_title}\n\n"
            f"{content}\n"
        )
        full_book_path.write_text(full_book_content, encoding="utf-8")

        # 4. Segment into chapters
        split_pattern = r"(?m)^(?=(?:##\s+)?(?:פרק\s+\d+|שער\s+[א-ת]|נספח\s+[א-ת]|תוכן\s*עניינים|Chapter\s+\d+|Appendix\s+[A-Z]))"
        raw_chunks = re.split(split_pattern, content)
        chunks = [c.strip() for c in raw_chunks if c.strip()]

        chapter_notes = []
        chapter_links = []

        if len(chunks) > 1:
            for idx, chunk in enumerate(chunks):
                chunk_lines = [l for l in chunk.splitlines() if l.strip()]
                first_line = chunk_lines[0] if chunk_lines else f"חלק {idx}"
                ch_title = re.sub(r"^#+\s*", "", first_line).strip()
                if not ch_title:
                    ch_title = f"{clean_title} — חלק {idx}"

                safe_ch_stem = re.sub(r'[\\/*?:"<>|]', "", ch_title)[:50].strip().replace(" ", "_")
                ch_filename = f"{slug}_{idx:02d}_{safe_ch_stem}.md"
                ch_path = book_dir / ch_filename

                ch_note_content = (
                    f"---\n"
                    f"title: \"{ch_title}\"\n"
                    f"book: \"{clean_title}\"\n"
                    f"domain: {target_domain}\n"
                    f"type: book_chapter\n"
                    f"tags: [book, chapter, {target_domain}]\n"
                    f"---\n\n"
                    f"# {ch_title}\n\n"
                    f"**ספר מקור:** [[{full_book_filename.replace('.md', '')}|{clean_title}]]\n\n"
                    f"{chunk}\n"
                )
                ch_path.write_text(ch_note_content, encoding="utf-8")
                chapter_notes.append(ch_path)
                chapter_links.append(f"- [[{ch_path.stem}|{ch_title}]]")
        else:
            chapter_notes.append(full_book_path)
            chapter_links.append(f"- [[{full_book_path.stem}|{clean_title}]]")

        # 5. Dedicated Book MOC
        mocs_dir = self.root_dir / "mocs"
        mocs_dir.mkdir(parents=True, exist_ok=True)
        book_moc_path = mocs_dir / f"{slug}_moc.md"
        moc_content = (
            f"---\n"
            f"title: \"{clean_title} — תוכן ומפת פרקים (MOC)\"\n"
            f"type: moc\n"
            f"domain: {target_domain}\n"
            f"tags: [moc, book, {target_domain}]\n"
            f"---\n\n"
            f"# {clean_title} — מפת נושאים ופרקים\n\n"
            f"- **ספר שלם:** [[{full_book_filename.replace('.md', '')}]]\n"
            f"- **פורמט מקור:** `{raw_path.name}`\n"
            f"- **תחום:** `{target_domain}`\n"
            f"- **פרקים שחולצו:** {len(chapter_notes)}\n"
            f"- **תמונות שחולצו:** {image_count}\n\n"
            f"## תוכן עניינים ופרקים\n\n"
            + "\n".join(chapter_links)
            + "\n"
        )
        book_moc_path.write_text(moc_content, encoding="utf-8")

        # 6. Update Domain MOC & Log
        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{slug}_moc")
        self.moc_service.append_domain_log(target_domain, f"Ingested book: {clean_title} ({len(chapter_notes)} chapters, {image_count} images)")

        # 7. Git commit
        commit_msg = f"ingest({target_domain}): process book '{clean_title}' ({len(chapter_notes)} chapters)"
        self.git_service.commit(commit_msg)

        return {
            "status": "COMPLETED",
            "job_id": job_id,
            "type": "book",
            "title": clean_title,
            "raw_path": str(raw_path),
            "book_path": str(full_book_path),
            "chapters_count": len(chapter_notes),
            "chapters": [str(c) for c in chapter_notes],
            "moc_path": str(book_moc_path),
            "images_extracted": image_count
        }



