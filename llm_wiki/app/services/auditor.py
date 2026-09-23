import frontmatter
from pathlib import Path
from typing import Union, Dict, Any, List
from app.services.parser import MarkdownParser

class WikiAuditorService:
    """
    Implements Wiki Lint & Knowledge Gap Detection (Sections 47 & 48 of specification).
    Detects broken links, orphan notes, missing frontmatter, and outputs reports to outputs/reports/knowledge-gaps.md.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.parser = MarkdownParser()
        self.outputs_dir = self.root_dir / "outputs" / "reports"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def audit_vault(self) -> Dict[str, Any]:

        all_md_files = list(self.root_dir.glob("wiki/**/*.md")) + list(self.root_dir.glob("shared/**/*.md"))
        existing_slugs = set(f.stem for f in all_md_files)

        broken_links = []
        orphan_notes = []
        missing_frontmatter = []
        contradictions = []

        link_counts: Dict[str, int] = {f.stem: 0 for f in all_md_files}

        for md_file in all_md_files:
            try:
                parsed = self.parser.parse_file(md_file)
                # Check frontmatter
                if not parsed.get("metadata"):
                    missing_frontmatter.append(str(md_file.relative_to(self.root_dir)))

                # Check links
                for link in parsed.get("wikilinks", []):
                    target_slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in link["target"]).strip().replace(" ", "-")
                    if target_slug in link_counts:
                        link_counts[target_slug] += 1
                    elif target_slug not in existing_slugs and not target_slug.startswith("wiki/") and not target_slug.startswith("mocs/"):
                        broken_links.append({
                            "source_note": str(md_file.relative_to(self.root_dir)),
                            "target_link": link["target"]
                        })

                if "contradiction" in str(md_file):
                    contradictions.append(str(md_file.relative_to(self.root_dir)))

            except Exception as e:
                missing_frontmatter.append(f"{md_file.name} (Error: {e})")

        # Determine orphans
        for slug, count in link_counts.items():
            if count == 0 and slug != "index" and slug != "log":
                orphan_notes.append(slug)

        report = {
            "total_notes": len(all_md_files),
            "broken_links": broken_links,
            "orphan_notes": orphan_notes,
            "missing_frontmatter": missing_frontmatter,
            "unresolved_contradictions": contradictions
        }

        self._write_report(report)
        return report

    def _write_report(self, report: Dict[str, Any]) -> Path:
        report_path = self.outputs_dir / "knowledge-gaps.md"
        content = (
            "# LLM Wiki Knowledge Gap & Integrity Report\n\n"
            f"- **Total Wiki Notes Analyzed**: {report['total_notes']}\n"
            f"- **Broken Links Detected**: {len(report['broken_links'])}\n"
            f"- **Orphan Notes**: {len(report['orphan_notes'])}\n"
            f"- **Missing Frontmatter**: {len(report['missing_frontmatter'])}\n\n"
            "## Broken Links\n"
        )
        for bl in report['broken_links']:
            content += f"- Note `{bl['source_note']}` links to missing target `[[{bl['target_link']}]]`\n"

        content += "\n## Orphan Notes\n"
        for orphan in report['orphan_notes']:
            content += f"- Note `[[{orphan}]]` has 0 incoming links.\n"

        report_path.write_text(content, encoding="utf-8")
        return report_path
