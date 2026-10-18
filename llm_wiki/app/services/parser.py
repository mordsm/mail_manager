import re
import frontmatter
from pathlib import Path
from typing import Dict, Any, List, Tuple, Union

class MarkdownParser:
    """
    Parses Markdown files, extracting YAML frontmatter, [[Wikilinks]], #tags, and structural headings.
    """
    WIKILINK_PATTERN = re.compile(r'\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]')
    TAG_PATTERN = re.compile(r'(?<!\w)#([a-zA-Z0-9_\-\/]+)')

    def parse_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".docx":
            return self.parse_docx(path)

        post = frontmatter.load(path)
        content = post.content

        wikilinks = self.extract_wikilinks(content)
        tags = self.extract_tags(content)
        
        # Merge frontmatter tags if present
        fm_tags = post.metadata.get("tags", [])
        if isinstance(fm_tags, list):
            tags = list(set(tags + fm_tags))

        return {
            "path": str(path),
            "filename": path.name,
            "title": post.metadata.get("title", path.stem),
            "metadata": post.metadata,
            "content": content,
            "wikilinks": wikilinks,
            "tags": tags,
        }

    def parse_docx(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        import zipfile
        import xml.etree.ElementTree as ET

        path = Path(file_path)
        paragraphs = []
        try:
            with zipfile.ZipFile(path) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                    pStyle = p.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
                    style_val = pStyle.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "") if pStyle is not None else ""
                    p_text = "".join([node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]).strip()
                    if p_text:
                        if "Heading1" in style_val or style_val == "1":
                            paragraphs.append(f"\n## {p_text}\n")
                        elif "Heading2" in style_val or style_val == "2":
                            paragraphs.append(f"\n### {p_text}\n")
                        elif "Heading3" in style_val or style_val == "3":
                            paragraphs.append(f"\n#### {p_text}\n")
                        else:
                            paragraphs.append(p_text)
        except Exception as e:
            paragraphs = [f"Error extracting docx: {e}"]

        content = "\n\n".join(paragraphs)
        return {
            "path": str(path),
            "filename": path.name,
            "title": path.stem.replace("_", " ").title(),
            "metadata": {"source_type": "docx", "paragraphs_count": len(paragraphs)},
            "content": content,
            "wikilinks": self.extract_wikilinks(content),
            "tags": ["document", "docx"],
        }

    def extract_wikilinks(self, text: str) -> List[Dict[str, str]]:
        """
        Extracts [[Wikilinks]] returning target and display label.
        """
        links = []
        for match in self.WIKILINK_PATTERN.finditer(text):
            target = match.group(1).strip()
            label = match.group(2).strip() if match.group(2) else target
            links.append({"target": target, "label": label})
        return links

    def extract_tags(self, text: str) -> List[str]:
        """
        Extracts #tags from text.
        """
        return list(set(match.group(1) for match in self.TAG_PATTERN.finditer(text)))

