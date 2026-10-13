import sqlite3
import json
import math
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import httpx

class VectorIndexService:
    """
    Vector Index Service:
    Manages semantic vector representations of Obsidian micro-blocks and notes.
    Supports Ollama embeddings (e.g. nomic-embed-text) with automatic fallback
    to subword/n-gram vector cosine similarity for 100% offline robustness.
    """
    def __init__(
        self,
        root_dir: Union[str, Path] = ".",
        db_path: Union[str, Path] = "system/db/vector_embeddings.db",
        ollama_url: str = "http://localhost:11434",
        embed_model: str = "nomic-embed-text"
    ):
        self.root_dir = Path(root_dir)
        self.db_path = self.root_dir / db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ollama_url = ollama_url.rstrip("/")
        self.embed_model = embed_model
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS block_vectors (
                block_id TEXT PRIMARY KEY,
                note_path TEXT,
                note_title TEXT,
                domain TEXT,
                content TEXT,
                vector_json TEXT,
                vector_type TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _get_ollama_embedding(self, text: str) -> Optional[List[float]]:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text[:2000]}
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("embedding")
        except Exception:
            pass
        return None

    def _get_fallback_vector(self, text: str, dim: int = 128) -> List[float]:
        """
        Pure-Python semantic subword hash vector for 100% offline, zero-dependency embedding.
        Works across Hebrew, English, and technical terminology.
        """
        vec = [0.0] * dim
        words = re.findall(r"[\u0590-\u05FF\w]+", text.lower())
        if not words:
            return vec

        for word in words:
            # Word level hash
            h_word = abs(hash(word)) % dim
            vec[h_word] += 2.0
            # 3-gram character hashes for morphological & fuzzy semantics
            for i in range(len(word) - 2):
                tri = word[i:i+3]
                h_tri = abs(hash(tri)) % dim
                vec[h_tri] += 1.0

        # L2 Normalize vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_text(self, text: str) -> (List[float], str):
        ollama_vec = self._get_ollama_embedding(text)
        if ollama_vec:
            return ollama_vec, "ollama"
        return self._get_fallback_vector(text), "fallback"

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    def index_block(self, block_id: str, content: str, note_path: str, note_title: str, domain: str):
        vec, v_type = self.embed_text(f"{note_title}\n{content}")
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO block_vectors 
            (block_id, note_path, note_title, domain, content, vector_json, vector_type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (block_id, note_path, note_title, domain, content, json.dumps(vec), v_type))
        conn.commit()
        conn.close()

    def search_similar(self, query: str, top_k: int = 6, domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if domain_filter and domain_filter not in ["all", "global"]:
            cursor.execute("SELECT block_id, note_path, note_title, domain, content, vector_json, vector_type FROM block_vectors WHERE domain = ?", (domain_filter,))
        else:
            cursor.execute("SELECT block_id, note_path, note_title, domain, content, vector_json, vector_type FROM block_vectors")
        
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        # Use same vector space as the indexed records
        first_type = rows[0][6]
        if first_type == "ollama":
            q_vec = self._get_ollama_embedding(query) or self._get_fallback_vector(query)
        else:
            q_vec = self._get_fallback_vector(query)

        scored = []
        for b_id, n_path, n_title, d, content, v_json, v_type in rows:
            try:
                b_vec = json.loads(v_json)
                sim = self.cosine_similarity(q_vec, b_vec)
                if sim > 0.15:
                    scored.append({
                        "block_id": b_id,
                        "note_path": n_path,
                        "note_title": n_title,
                        "domain": d,
                        "content": content,
                        "semantic_score": sim
                    })
            except Exception:
                continue

        scored.sort(key=lambda x: x["semantic_score"], reverse=True)
        return scored[:top_k]

    def index_vault(self, folders: Optional[List[str]] = None, max_blocks: int = 200) -> int:
        """
        Indexes micro-blocks from vault folders into the vector database.
        """
        target_folders = folders or ["wiki", "10_Projects", "20_Research", "40_Decisions"]
        count = 0
        
        # Check existing indexed block IDs to avoid re-embedding
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT block_id FROM block_vectors")
        existing_ids = set(row[0] for row in cursor.fetchall())
        conn.close()

        for folder_name in target_folders:
            folder_dir = self.root_dir / folder_name
            if not folder_dir.exists():
                continue
            for md_file in folder_dir.glob("**/*.md"):
                if count >= max_blocks:
                    break
                try:
                    rel_path = md_file.relative_to(self.root_dir)
                    text = md_file.read_text(encoding="utf-8", errors="replace")
                    if not text.strip():
                        continue
                    
                    domain = "research" if "20_Research" in str(rel_path) or "research" in str(rel_path) else (
                        "development" if "10_Projects" in str(rel_path) else (
                            "decisions" if "40_Decisions" in str(rel_path) else "wiki"
                        )
                    )
                    title = md_file.stem.replace("_", " ").title()

                    # Extract block anchors (^block-xxx)
                    lines = text.split("\n")
                    curr_lines = []
                    found_any = False
                    for line in lines:
                        curr_lines.append(line)
                        m = re.search(r"\^([a-zA-Z0-9_\-]+)", line)
                        if m:
                            b_id = m.group(1)
                            b_text = "\n".join(curr_lines).strip()
                            if b_id not in existing_ids:
                                self.index_block(b_id, b_text, str(rel_path), title, domain)
                                existing_ids.add(b_id)
                                count += 1
                            curr_lines = []
                            found_any = True
                    
                    # If no block anchors, index the note head as a document block
                    if not found_any and md_file.stem not in existing_ids:
                        self.index_block(md_file.stem, text[:1500].strip(), str(rel_path), title, domain)
                        existing_ids.add(md_file.stem)
                        count += 1
                except Exception:
                    continue
        return count

    def get_stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), vector_type FROM block_vectors GROUP BY vector_type")
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM block_vectors")
        total = cursor.fetchone()[0]
        conn.close()
        breakdown = {r[1]: r[0] for r in rows}
        return {"total_vectors": total, "breakdown": breakdown, "model": self.embed_model}
