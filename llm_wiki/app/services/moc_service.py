from pathlib import Path
from typing import Union, List
from datetime import date
import threading
import time

_MOC_LOCK = threading.Lock()

def _safe_write_text(file_path: Path, content: str, max_retries: int = 5) -> None:
    """
    Safely writes text to a file, handling Windows NTFS file locks, anti-virus delays,
    and concurrent write attempts with retry and atomic temporary rename.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_name(f"{file_path.stem}.tmp_{int(time.time()*1000)}{file_path.suffix}")
    for attempt in range(max_retries):
        try:
            temp_file.write_text(content, encoding="utf-8")
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass
            temp_file.replace(file_path)
            return
        except OSError:
            if attempt == max_retries - 1:
                # Direct fallback write
                with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content)
                return
            time.sleep(0.08 * (attempt + 1))
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

class MOCService:
    """
    Maintains curated Maps of Content (MOCs) in mocs/ and appends updates to domain index.md files.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        (self.root_dir / "mocs").mkdir(parents=True, exist_ok=True)

    def update_moc(self, moc_title: str, section: str, note_link: str) -> Path:
        slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in moc_title).strip().replace(" ", "-")
        moc_path = self.root_dir / "mocs" / f"{slug}.md"


        link_entry = f"- [[{note_link}]]"

        if not moc_path.exists():
            content = f"# {moc_title}\n\n## {section}\n\n{link_entry}\n"
            _safe_write_text(moc_path, content)
            return moc_path

        existing_text = moc_path.read_text(encoding="utf-8")
        if link_entry in existing_text:
            return moc_path  # Already linked

        section_header = f"## {section}"
        if section_header in existing_text:
            new_text = existing_text.replace(
                section_header,
                f"{section_header}\n\n{link_entry}"
            )
        else:
            new_text = existing_text + f"\n\n## {section}\n\n{link_entry}\n"

        _safe_write_text(moc_path, new_text)
        return moc_path

    def append_domain_log(self, domain: str, log_message: str) -> Path:
        log_path = self.root_dir / "wiki" / domain / "log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        entry = f"- **{today}**: {log_message}\n"

        if not log_path.exists():
            _safe_write_text(log_path, f"# {domain.capitalize()} Domain Log\n\n{entry}")
        else:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        return log_path

    def rebuild_domain_mocs(self) -> dict:
        """
        Scans vault domains and projects to build comprehensive, curated MOCs (Maps of Content).
        Adheres to verbatim rule: 'MOCs own navigation. Wiki owns synthesis.'
        Thread-safe and protected against Windows file-lock collisions.
        """
        with _MOC_LOCK:
            domains = ["personal", "research", "business", "competitive", "development"]
            mocs_dir = self.root_dir / "mocs"
            mocs_dir.mkdir(parents=True, exist_ok=True)
            stats = {}

            master_links = []

            for d in domains:
                domain_dir = self.root_dir / "wiki" / d
                if not domain_dir.exists():
                    continue

                categories = {}
                for md_file in sorted(domain_dir.glob("**/*.md")):
                    if md_file.name in ["index.md", "log.md"]:
                        continue
                    cat = md_file.parent.name if md_file.parent != domain_dir else "general"
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(md_file.stem)

                # Build Domain MOC
                moc_title = f"{d.capitalize()} Map of Content (MOC)"
                lines = [
                    f"# {moc_title}\n",
                    f"**Domain**: `{d}` | **Last Synthesized**: {date.today().isoformat()}\n",
                    f"> Navigation map generated per AGENTS.md MOC specification.\n"
                ]

                total_domain_notes = 0
                for cat, notes in categories.items():
                    lines.append(f"## {cat.capitalize()} ({len(notes)})")
                    for n in notes:
                        lines.append(f"- [[{n}]]")
                    lines.append("")
                    total_domain_notes += len(notes)

                moc_file = mocs_dir / f"{d}_moc.md"
                _safe_write_text(moc_file, "\n".join(lines))
                stats[d] = total_domain_notes
                master_links.append(f"- [[{d}_moc]] — {total_domain_notes} active notes")

                # Update wiki/{domain}/index.md
                index_file = domain_dir / "index.md"
                index_content = (
                    f"# {d.capitalize()} Domain Index\n\n"
                    f"**Navigation MOC**: [[{d}_moc]]\n\n"
                    f"**Domain Log**: [[log]]\n\n"
                    f"## Overview\n"
                    f"Total curated knowledge units: {total_domain_notes}\n"
                )
                _safe_write_text(index_file, index_content)

            # 2. Add Projects & Research Sessions to Master MOC
            projects_dir = self.root_dir / "10_Projects"
            proj_notes = [p.name for p in projects_dir.iterdir() if p.is_dir()] if projects_dir.exists() else []

            research_dir = self.root_dir / "20_Research"
            res_notes = [r.name for r in research_dir.iterdir() if r.is_dir()] if research_dir.exists() else []

            proj_entries = [f"- [[{p}]]" for p in proj_notes] if proj_notes else ["- No active project directories"]
            res_entries = [f"- [[{r}]]" for r in res_notes[:15]] if res_notes else ["- No research sessions recorded"]

            master_lines = [
                "# Master Vault Map of Content (MOC)\n",
                f"**Generated**: {date.today().isoformat()}\n",
                "## Domain Maps of Content",
                *master_links,
                "\n## Active Projects (10_Projects)",
                *proj_entries,
                "\n## Deep Research Sessions (20_Research)",
                *res_entries,
                ""
            ]
            master_file = mocs_dir / "master_vault_moc.md"
            _safe_write_text(master_file, "\n".join(master_lines))

            stats["total_domains_indexed"] = len(stats)
            stats["master_moc"] = str(master_file.relative_to(self.root_dir))
            return stats
