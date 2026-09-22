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
