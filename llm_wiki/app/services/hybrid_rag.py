import re
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import httpx

from app.services.parser import MarkdownParser
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm import get_llm_provider
from app.services.vector_service import VectorIndexService
from app.services.taxonomy_service import SubjectTaxonomyService


class MicroBlock:
    """
    Represents a granular micro-block within an Obsidian note.
    """
    def __init__(self, block_id: str, content: str, note_path: Path, note_title: str, domain: str):
        self.block_id = block_id
        self.content = content
        self.note_path = note_path
        self.note_title = note_title
        self.domain = domain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "content": self.content,
            "note_path": str(self.note_path),
            "note_title": self.note_title,
            "domain": self.domain,
        }


class HybridRAGService:
    """
    Hybrid RAG Engine for OCKA (Obsidian Central Knowledge Agent).
    Workflow:
    1. Search local Obsidian micro-blocks (^block-xxxx) across requested domains and sub-subjects.
    2. Evaluate evidence relevance score with sub-subject boosts.
    3. If local evidence is partial or missing, fetch supplementary web context.
    4. Synthesize unified response with granular block citations.
    """

    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.parser = MarkdownParser()
        self.llm = llm_provider or get_llm_provider()
        self.vector_service = VectorIndexService(root_dir=self.root_dir)
        self.taxonomy = SubjectTaxonomyService(root_dir=self.root_dir)

    def extract_blocks(self, note_path: Path, domain: str) -> List[MicroBlock]:
        """
        Extracts micro-blocks with block IDs (^block-xxxx) from a Markdown file.
        """
        blocks = []
        if not note_path.exists():
            return blocks

        try:
            parsed = self.parser.parse_file(note_path)
            content = parsed.get("content", "")
            title = parsed.get("title", note_path.stem)
            rel_path = note_path.relative_to(self.root_dir)

            lines = content.split("\n")
            current_chunk = []
            
            for line in lines:
                current_chunk.append(line)
                match = re.search(r"\^([a-zA-Z0-9_\-]+)", line)
                if match:
                    block_id = match.group(1)
                    block_text = "\n".join(current_chunk).strip()
                    blocks.append(MicroBlock(
                        block_id=block_id,
                        content=block_text,
                        note_path=rel_path,
                        note_title=title,
                        domain=domain
                    ))
                    current_chunk = []

            # If no block anchors found, treat full note as single unit
            if not blocks and content.strip():
                blocks.append(MicroBlock(
                    block_id=note_path.stem,
                    content=content[:1000].strip(),
                    note_path=rel_path,
                    note_title=title,
                    domain=domain
                ))
        except Exception:
            pass

        return blocks

    def is_vault_overview_query(self, query: str) -> bool:
        """
        Detects if user is asking for an overview or inventory of the vault / knowledge base.
        e.g. 'מה הדברים שרשומים אצלך כרגע בידע', 'מה יש בכספת', 'איזה נושאים קיימים'
        """
        q = query.lower().strip()
        patterns = [
            r"מה.*(רשום|כתוב|נמצא|קיים|שמור|ידוע|בידע|בכספת|שלך)",
            r"(איזה|אילו|מהם|מה).*?(נושאים|תחומים|דברים|פרויקטים|מחקרים|הערכים|המידע)",
            r"תסכם.*(ידע|כספת|נושאים|תכולה)",
            r"מה אתה יודע",
            r"סקיר(ת|ה).*(כספת|ידע|מפות)",
            r"מה יש (לך|אצלך|בכספת)",
            r"מה.*(בידע|במאגר|במערכת)",
            r"what (is in|exists in|topics|knowledge|notes exist)",
            r"overview of",
            r"list (topics|notes|projects)"
        ]
        return any(re.search(pat, q) for pat in patterns)

    def get_vault_overview_blocks(self) -> List[MicroBlock]:
        """
        Gathers high-level Maps of Content (MOCs) to provide complete knowledge overview.
        """
        blocks = []
        master_moc = self.root_dir / "mocs" / "master_vault_moc.md"
        if master_moc.exists():
            txt = master_moc.read_text(encoding="utf-8", errors="ignore")
            blocks.append(MicroBlock(
                block_id="master-vault-moc",
                content=txt[:2500],
                note_path=master_moc.relative_to(self.root_dir),
                note_title="Master Vault Map of Content (MOC)",
                domain="mocs"
            ))

        moc_dir = self.root_dir / "mocs"
        if moc_dir.exists():
            for m in moc_dir.glob("*_moc.md"):
                if m.name != "master_vault_moc.md":
                    txt = m.read_text(encoding="utf-8", errors="ignore")
                    domain_name = m.stem.replace("_moc", "")
                    blocks.append(MicroBlock(
                        block_id=f"{domain_name}-overview",
                        content=txt[:1500],
                        note_path=m.relative_to(self.root_dir),
                        note_title=f"Domain MOC: {domain_name.capitalize()}",
                        domain=domain_name
                    ))
        return blocks

    def search_local_vault(self, query: str, domain: str = "all", subsubject: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Searches all micro-blocks in the vault matching query keywords across all domains and vault folders,
        fusing lexical keyword scoring with dense semantic vector embedding similarity and sub-subject taxonomy rules.
        """
        fused_map: Dict[tuple, Dict[str, Any]] = {}

        # 0. Check for Vault Overview Query (Fast MOC path)
        if self.is_vault_overview_query(query):
            overview_blocks = self.get_vault_overview_blocks()
            return [{"block": b, "score": 100.0} for b in overview_blocks]

        target_domains = ["personal", "research", "business", "competitive", "development"] if domain.lower() in ["all", "global"] else [domain]
        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]

        # Sub-subject taxonomy rules
        sub_keywords: List[str] = []
        sub_folders: List[str] = []
        if subsubject and subsubject.lower() != "all":
            sub_keywords, sub_folders = self.taxonomy.get_filter_rules(domain, subsubject)

        # 1. Search wiki domains
        for d in target_domains:
            domain_dir = self.root_dir / "wiki" / d
            if domain_dir.exists():
                for md_file in domain_dir.glob("**/*.md"):
                    blocks = self.extract_blocks(md_file, domain=d)
                    for b in blocks:
                        score = 0
                        text_lower = b.content.lower()
                        title_lower = b.note_title.lower()
                        path_posix = b.note_path.as_posix().lower()

                        for term in query_terms:
                            if term in text_lower:
                                score += 2
                            if term in title_lower:
                                score += 5

                        # Sub-subject boost
                        if sub_folders and any(sf.lower() in path_posix for sf in sub_folders):
                            score += 12
                        if sub_keywords:
                            for sk in sub_keywords:
                                sk_lower = sk.lower()
                                if sk_lower in text_lower:
                                    score += 4
                                if sk_lower in title_lower:
                                    score += 8

                        if score > 0:
                            key = (str(b.note_path), b.block_id)
                            fused_map[key] = {
                                "block": b,
                                "score": float(score)
                            }

        # 2. If global/all, also search projects, research sessions, decisions, and MOCs
        if domain.lower() in ["all", "global"]:
            extra_folders = [
                ("10_Projects", "development"),
                ("20_Research", "research"),
                ("40_Decisions", "decisions"),
                ("mocs", "mocs")
            ]
            for folder_name, cat in extra_folders:
                folder_dir = self.root_dir / folder_name
                if folder_dir.exists():
                    for md_file in folder_dir.glob("**/*.md"):
                        blocks = self.extract_blocks(md_file, domain=cat)
                        for b in blocks:
                            score = 0
                            text_lower = b.content.lower()
                            title_lower = b.note_title.lower()

                            for term in query_terms:
                                if term in text_lower:
                                    score += 2
                                if term in title_lower:
                                    score += 5

                            if score > 0:
                                key = (str(b.note_path), b.block_id)
                                fused_map[key] = {
                                    "block": b,
                                    "score": float(score)
                                }

        # 3. Dense Semantic Vector Search Fusion
        try:
            semantic_matches = self.vector_service.search_similar(
                query=query,
                top_k=8,
                domain_filter=domain if domain.lower() not in ["all", "global"] else None
            )
            for sm in semantic_matches:
                key = (sm["note_path"], sm["block_id"])
                sem_boost = sm.get("semantic_score", 0.0) * 10.0
                path_lower = sm["note_path"].lower()

                # Sub-subject boost for vector results
                if sub_folders and any(sf.lower() in path_lower for sf in sub_folders):
                    sem_boost += 12.0
                if sub_keywords:
                    for sk in sub_keywords:
                        sk_lower = sk.lower()
                        if sk_lower in sm.get("content", "").lower():
                            sem_boost += 4.0

                if key in fused_map:
                    fused_map[key]["score"] += sem_boost
                else:
                    nb = MicroBlock(
                        block_id=sm["block_id"],
                        content=sm["content"],
                        note_path=Path(sm["note_path"]),
                        note_title=sm["note_title"],
                        domain=sm["domain"]
                    )
                    fused_map[key] = {
                        "block": nb,
                        "score": sem_boost
                    }
        except Exception:
            pass

        # Sort by relevance score descending
        ranked_blocks = list(fused_map.values())
        ranked_blocks.sort(key=lambda x: x["score"], reverse=True)
        return ranked_blocks[:8]

    def search_web_fallback(self, query: str) -> Optional[str]:
        """
        Fetches web search snippets if local vault coverage is partial or missing.
        Uses DuckDuckGo search fallback with fast timeout.
        """
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            with httpx.Client(timeout=2.5) as client:
                res = client.get(url, params={"q": query}, headers=headers)
                if res.status_code == 200:
                    text = res.text
                    # Extract snippets
                    snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', text, re.DOTALL)
                    clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]]
                    if clean_snippets:
                        return "\n".join(f"- {s}" for s in clean_snippets)
        except Exception:
            pass
        return None

    def query(self, question: str, domain: str = "all", subsubject: Optional[str] = None, allow_web_fallback: bool = True, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the full Hybrid RAG Workflow.
        Allows specifying external sub-model provider (e.g. 'gemini', 'openai', 'ollama')
        and filtering by main domain and sub-subject taxonomy.
        """
        active_llm = get_llm_provider(provider) if provider else self.llm
        local_results = self.search_local_vault(question, domain=domain, subsubject=subsubject)
        has_sufficient_local = len(local_results) > 0

        web_context = None
        if not has_sufficient_local and allow_web_fallback:
            web_context = self.search_web_fallback(question)

        # Construct Context
        context_str = "### 📚 Local Obsidian Micro-Blocks (Direct Evidence):\n"
        citations = []
        if local_results:
            for item in local_results:
                b: MicroBlock = item["block"]
                citation_tag = f"[{b.note_title} ^{b.block_id}] (`{b.note_path}`)"
                citations.append(citation_tag)
                context_str += f"- **Citation**: {citation_tag}\n  **Content**:\n  {b.content}\n\n"
        else:
            context_str += "No matching micro-blocks found in local vault.\n\n"

        if web_context:
            context_str += f"### 🌐 Web Context (External Fallback):\n{web_context}\n\n"

        # Synthesize prompt
        subsubject_hint = f"Focus Subject: {domain} | Sub-Subject: {subsubject}\n" if subsubject and subsubject != "all" else ""
        system_prompt = (
            "You are the Obsidian Central Knowledge Agent (OCKA). "
            "Your task is to answer user queries accurately using local Obsidian vault micro-blocks as primary direct evidence. "
            "Always include precise block citations in the format [Title ^block-id] when referencing local context. "
            "If web content was used, clearly label it as external web fallback."
        )

        user_prompt = (
            f"{subsubject_hint}"
            f"Question: {question}\n\n"
            f"Retrieved Context:\n{context_str}\n"
            "Please provide a clear, comprehensive answer in Hebrew."
        )

        try:
            llm_response = active_llm.generate(user_prompt, system_prompt=system_prompt)
            if not llm_response or "Fallback" in llm_response:
                llm_response = self._synthesize_fallback(question, local_results, web_context)
        except Exception:
            llm_response = self._synthesize_fallback(question, local_results, web_context)

        return {
            "question": question,
            "domain": domain,
            "subsubject": subsubject,
            "answer": llm_response,
            "citations": citations,
            "local_blocks_found": len(local_results),
            "web_fallback_used": web_context is not None,
            "provider_used": active_llm.__class__.__name__
        }

    def _synthesize_fallback(self, question: str, local_results: List[Dict[str, Any]], web_context: Optional[str]) -> str:
        out = f"### 🔍 תוצאות מענה היברידי מתוך הכספת (OCKA Hybrid RAG)\n\n"
        out += f"**שאלה:** {question}\n\n"

        if local_results:
            out += "#### 📌 ראיות ישירות מתוך עוגני הבלוקים בכספת:\n\n"
            for item in local_results:
                b: MicroBlock = item["block"]
                clean_text = re.sub(r"\^([a-zA-Z0-9_\-]+)", "", b.content).strip()
                out += f"* **[{b.note_title} ^{b.block_id}]** (`{b.note_path}`):\n"
                out += f"  > {clean_text}\n\n"
        else:
            out += "לא נמצאו בלוקים ישירים בכספת המתאימים לשאלה.\n\n"

        if web_context:
            out += f"#### 🌐 השלמת מידע מן הרשת (Web Fallback):\n{web_context}\n"

        return out
