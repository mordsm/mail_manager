from pathlib import Path
from typing import Union, List
from datetime import date

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
            moc_path.write_text(content, encoding="utf-8")
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

        moc_path.write_text(new_text, encoding="utf-8")
        return moc_path

    def append_domain_log(self, domain: str, log_message: str) -> Path:
        log_path = self.root_dir / "wiki" / domain / "log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        entry = f"- **{today}**: {log_message}\n"

        if not log_path.exists():
            log_path.write_text(f"# {domain.capitalize()} Domain Log\n\n{entry}", encoding="utf-8")
        else:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        return log_path
