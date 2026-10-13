import re
from pathlib import Path
from typing import Union, Optional, List
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


class DocxExporterService:
    """
    Exports Obsidian Vault books/notes into clean DOCX documents.
    Strips granular block anchors (^block-xxxx) for reader-facing documents
    while preserving heading hierarchy, tables, callouts, and formatting.
    """

    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)

    def clean_markdown_for_docx(self, text: str) -> str:
        """
        Removes block anchor tags ^block-xxxx and double bracket wikilinks [[Concept]].
        """
        # Remove ^block-xxxx anchors
        text = re.sub(r"\^([a-zA-Z0-9_\-]+)", "", text)
        # Convert [[Concept]] to plain text Concept
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        return text

    def export_book_to_docx(
        self,
        book_dir: Union[str, Path],
        output_docx_path: Union[str, Path],
        title: str = "שער פנימי — המעי, האנרגיה והבריאות",
        author: str = "משה"
    ) -> Path:
        """
        Combines all chapter files in book_dir into a clean, formatted DOCX file.
        """
        book_path = Path(book_dir)
        output_path = Path(output_docx_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()

        # Document Title Page / Header
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        title_run = title_p.add_run(title)
        title_run.font.size = Pt(26)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(14, 116, 144)

        author_p = doc.add_paragraph()
        author_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        author_run = author_p.add_run(f"מאת: {author}\n")
        author_run.font.size = Pt(14)
        author_run.font.italic = True
        author_run.font.color.rgb = RGBColor(71, 85, 105)

        doc.add_page_break()

        # Find all chapter files sorted
        chapter_files = sorted(list(book_path.glob("chapter_*.md")))
        if not chapter_files:
            chapter_files = sorted(list(book_path.glob("*.md")))

        for md_file in chapter_files:
            content = md_file.read_text(encoding="utf-8")
            clean_content = self.clean_markdown_for_docx(content)
            self._add_markdown_to_docx(doc, clean_content)
            doc.add_page_break()

        doc.save(str(output_path))
        return output_path

    def export_note_to_docx(
        self,
        note_path: Union[str, Path],
        output_docx_path: Union[str, Path],
        title: Optional[str] = None,
        author: str = "משה"
    ) -> Path:
        """
        Exports a single Markdown note file into a clean, formatted DOCX file.
        """
        np = Path(note_path)
        output_path = Path(output_docx_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()
        doc_title = title or np.stem.replace("_", " ").title()

        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        title_run = title_p.add_run(doc_title)
        title_run.font.size = Pt(22)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(14, 116, 144)

        author_p = doc.add_paragraph()
        author_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        author_run = author_p.add_run(f"מאת: {author}\n")
        author_run.font.size = Pt(12)
        author_run.font.italic = True
        author_run.font.color.rgb = RGBColor(71, 85, 105)

        doc.add_paragraph("________________________________________").alignment = WD_ALIGN_PARAGRAPH.CENTER

        content = np.read_text(encoding="utf-8")
        clean_content = self.clean_markdown_for_docx(content)
        self._add_markdown_to_docx(doc, clean_content)

        doc.save(str(output_path))
        return output_path

    def _add_markdown_to_docx(self, doc: Document, md_text: str):
        lines = md_text.split("\n")
        in_table = False
        table_rows = []

        for line in lines:
            line_str = line.strip()

            if line_str.startswith("|"):
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append(line_str)
                continue
            elif in_table:
                in_table = False
                self._render_docx_table(doc, table_rows)
                table_rows = []

            if not line_str:
                continue

            if line_str.startswith("# "):
                p = doc.add_heading(line_str[2:], level=1)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif line_str.startswith("## "):
                p = doc.add_heading(line_str[3:], level=2)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif line_str.startswith("### "):
                p = doc.add_heading(line_str[4:], level=3)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif line_str.startswith("---"):
                p = doc.add_paragraph("________________________________________")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.line_spacing = 1.2
                run = p.add_run(line_str)
                run.font.name = "Arial"
                run.font.size = Pt(11)

        if in_table:
            self._render_docx_table(doc, table_rows)

    def _render_docx_table(self, doc: Document, table_rows: List[str]):
        if len(table_rows) < 2:
            return

        headers = [c.strip() for c in table_rows[0].split("|") if c.strip()]
        data_rows = []
        for r in table_rows[2:]:
            cells = [c.strip() for c in r.split("|") if c.strip()]
            if cells:
                data_rows.append(cells)

        if not headers:
            return

        table = doc.add_table(rows=1 + len(data_rows), cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header Row
        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(headers):
            if i < len(hdr_cells):
                hdr_cells[i].text = header_text
                for p in hdr_cells[i].paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in p.runs:
                        run.font.bold = True
                        run.font.size = Pt(10)

        # Data Rows
        for r_idx, row_data in enumerate(data_rows):
            row_cells = table.rows[r_idx + 1].cells
            for c_idx, cell_value in enumerate(row_data):
                if c_idx < len(row_cells):
                    row_cells[c_idx].text = cell_value
                    for p in row_cells[c_idx].paragraphs:
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        for run in p.runs:
                            run.font.size = Pt(10)
