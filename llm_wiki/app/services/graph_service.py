import re
from pathlib import Path
from typing import Dict, Any, List, Set, Union
import frontmatter

class VaultGraphService:
    """
    Vault Graph Service: Analyzes Markdown notes and wikilinks [[...]] across the vault
    to build an interactive network graph structure (nodes & links) suitable for Vis.js / Force-Graph.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.wikilink_pattern = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")

    def build_graph(self) -> Dict[str, Any]:
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        links: List[Dict[str, Any]] = []
        name_to_id: Dict[str, str] = {}

        # Search relevant vault directories
        scan_dirs = ["10_Projects", "20_Research", "40_Decisions", "mocs", "wiki", "shared"]
        md_files: List[Path] = []
        for d in scan_dirs:
            folder = self.root_dir / d
            if folder.exists():
                md_files.extend(list(folder.rglob("*.md")))

        # First pass: register nodes
        for f in md_files:
            rel_path = f.relative_to(self.root_dir).as_posix()
            node_id = f.stem.lower().replace(" ", "-")
            name_to_id[f.stem.lower()] = node_id

            # Determine group / domain
            parts = rel_path.split("/")
            group = parts[0]
            if group == "wiki" and len(parts) > 1:
                group = f"wiki/{parts[1]}"

            title = f.stem
            try:
                post = frontmatter.load(f)
                if post.metadata.get("title"):
                    title = str(post.metadata["title"])
                else:
                    lines = post.content.splitlines()
                    for line in lines:
                        if line.startswith("# "):
                            title = line.replace("# ", "").strip()
                            break
            except Exception:
                pass

            nodes_dict[node_id] = {
                "id": node_id,
                "label": title,
                "path": rel_path,
                "group": group,
                "degree": 0
            }

        # Second pass: scan links
        seen_links: Set[str] = set()
        for f in md_files:
            source_id = f.stem.lower().replace(" ", "-")
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                matches = self.wikilink_pattern.findall(text)
                for target_raw in matches:
                    clean_target = target_raw.strip().lower()
                    target_id = name_to_id.get(clean_target, clean_target.replace(" ", "-"))

                    # If target node doesn't exist yet, add it as ghost/external node
                    if target_id not in nodes_dict:
                        nodes_dict[target_id] = {
                            "id": target_id,
                            "label": target_raw.strip(),
                            "path": "",
                            "group": "external",
                            "degree": 0
                        }

                    link_key = f"{source_id}->{target_id}"
                    if link_key not in seen_links and source_id != target_id:
                        seen_links.add(link_key)
                        links.append({
                            "source": source_id,
                            "target": target_id
                        })
                        nodes_dict[source_id]["degree"] += 1
                        nodes_dict[target_id]["degree"] += 1
            except Exception:
                pass

        return {
            "nodes": list(nodes_dict.values()),
            "links": links,
            "total_nodes": len(nodes_dict),
            "total_links": len(links)
        }
