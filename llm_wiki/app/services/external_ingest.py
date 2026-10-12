import re
import uuid
from pathlib import Path
from typing import Union, Dict, Any, Optional, List
import httpx

from app.services.pipeline import LLMWikiPipeline
from app.services.parser import MarkdownParser


class ExternalIngestService:
    """
    Multi-Source External Ingestion Pipeline for OCKA.
    Ingests web articles, scientific research, and YouTube content/summaries,
    applies granular block anchors (^block-ext-xxxx), and links evidence into
    the Obsidian Central Knowledge Spine.
    """

    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.pipeline = LLMWikiPipeline(root_dir=root_dir)
        self.parser = MarkdownParser()

    def fetch_url_content(self, url: str) -> Dict[str, str]:
        """
        Fetches web page content cleanly using HTTP request.
        """
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OCKA External Ingest"}
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    text = res.text
                    # Extract page title
                    title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
                    title = title_match.group(1).strip() if title_match else "External Resource"
                    
                    # Clean simple HTML to text
                    body_text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                    body_text = re.sub(r"<style.*?>.*?</style>", "", body_text, flags=re.DOTALL | re.IGNORECASE)
                    clean_body = re.sub(r"<[^>]+>", " ", body_text)
                    clean_body = re.sub(r"\s+", " ", clean_body).strip()[:3000]

                    return {"title": title, "content": clean_body, "url": url}
        except Exception as e:
            return {"title": "External Ingestion Failure", "content": f"Failed to fetch content from {url}: {str(e)}", "url": url}

        return {"title": "External Ingestion", "content": f"No content retrieved from {url}", "url": url}

    def ingest_external_source(
        self,
        source_type: str,  # 'web', 'youtube', 'paper'
        url_or_identifier: str,
        title: Optional[str] = None,
        raw_text: Optional[str] = None,
        domain: str = "research",
        target_concept_links: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ingests external source into wiki/research/external/<title>.md with micro-block anchors.
        """
        if raw_text:
            content = raw_text
            note_title = title or "External Note"
        else:
            fetched = self.fetch_url_content(url_or_identifier)
            content = fetched["content"]
            note_title = title or fetched["title"]

        # Break content into paragraphs and attach ^block-ext-xxxx anchors
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [content]

        anchored_paragraphs = []
        for idx, p in enumerate(paragraphs):
            b_id = f"block-ext-{uuid.uuid4().hex[:6]}"
            anchored_paragraphs.append(f"{p} ^{b_id}")

        anchored_body = "\n\n".join(anchored_paragraphs)

        # Build Wikilinks Footer
        links_str = ""
        if target_concept_links:
            links_str = "\n\n## 🔗 Linked Knowledge Network Nodes\n" + "\n".join(f"- [[{c}]]" for c in target_concept_links)

        md_content = (
            f"# {note_title}\n\n"
            f"**Source Type:** {source_type.upper()}\n"
            f"**URL / Identifier:** {url_or_identifier}\n"
            f"**Ingestion Domain:** `{domain}`\n\n"
            f"## 📝 Extracted Content & Micro-Block Anchors\n\n"
            f"{anchored_body}\n"
            f"{links_str}"
        )

        # Ingest note into vault via pipeline
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", note_title)[:50]
        ext_dir = self.root_dir / "wiki" / domain / "external"
        ext_dir.mkdir(parents=True, exist_ok=True)
        note_path = ext_dir / f"{sanitized_title}.md"
        note_path.write_text(md_content, encoding="utf-8")

        return {
            "status": "INGESTED",
            "source_type": source_type,
            "title": note_title,
            "note_path": str(note_path.relative_to(self.root_dir)),
            "blocks_created": len(anchored_paragraphs)
        }
