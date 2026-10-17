from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml
import os

class SubjectTaxonomyService:
    """
    Manages knowledge taxonomy: main subjects and sub-subjects configured externally.
    Default configuration file: config/subjects.yaml
    """
    def __init__(self, root_dir: Path | str = ".", config_path: str = "config/subjects.yaml"):
        self.root_dir = Path(root_dir)
        self.config_path = self.root_dir / config_path
        self._cached_mtime = 0.0
        self._cached_data: Dict[str, Any] = {}

    def get_taxonomy(self) -> Dict[str, Any]:
        """
        Loads and returns the taxonomy dictionary from config/subjects.yaml.
        Reloads dynamically if the file was edited externally.
        """
        if not self.config_path.exists():
            return self._default_fallback_taxonomy()

        try:
            mtime = self.config_path.stat().st_mtime
            if mtime != self._cached_mtime or not self._cached_data:
                raw_text = self.config_path.read_text(encoding="utf-8")
                loaded = yaml.safe_load(raw_text) or {}
                self._cached_data = loaded.get("subjects", {})
                self._cached_mtime = mtime
            return self._cached_data
        except Exception as e:
            if self._cached_data:
                return self._cached_data
            return self._default_fallback_taxonomy()

    def get_subsubjects(self, subject_key: str) -> Dict[str, Any]:
        """
        Returns all sub-subjects defined for a given main subject.
        """
        tax = self.get_taxonomy()
        clean_key = (subject_key or "").lower().strip()
        subject_info = tax.get(clean_key, {})
        return subject_info.get("subsubjects", {})

    def get_filter_rules(self, subject_key: str, subsubject_key: Optional[str] = None) -> Tuple[List[str], List[str]]:
        """
        Returns (keywords_boost, target_folder_prefixes) for a subject and optional sub-subject.
        """
        tax = self.get_taxonomy()
        clean_subj = (subject_key or "").lower().strip()
        clean_sub = (subsubject_key or "all").lower().strip()

        if clean_subj in ["all", "global", ""]:
            return [], []

        subject_info = tax.get(clean_subj, {})
        base_folder = subject_info.get("folder", f"wiki/{clean_subj}")
        folders = [base_folder]
        keywords: List[str] = []

        sub_map = subject_info.get("subsubjects", {})
        if clean_sub and clean_sub != "all" and clean_sub in sub_map:
            sub_info = sub_map[clean_sub]
            if "folder" in sub_info:
                folders = [sub_info["folder"]]
            if "keywords" in sub_info:
                keywords.extend(sub_info["keywords"])

        return keywords, folders

    def save_taxonomy(self, subjects_dict: Dict[str, Any]) -> bool:
        """
        Saves updated taxonomy back to config/subjects.yaml.
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            content = {
                "subjects": subjects_dict
            }
            raw = yaml.dump(content, allow_unicode=True, sort_keys=False, default_flow_style=False)
            self.config_path.write_text(raw, encoding="utf-8")
            self._cached_data = subjects_dict
            self._cached_mtime = self.config_path.stat().st_mtime
            return True
        except Exception:
            return False

    def _default_fallback_taxonomy(self) -> Dict[str, Any]:
        return {
            "research": {
                "title": "Research & Technology",
                "title_he": "מחקר וטכנולוגיה",
                "folder": "wiki/research",
                "subsubjects": {
                    "all": {"title": "All Research", "title_he": "כל תחומי המחקר"}
                }
            },
            "personal": {
                "title": "Personal",
                "title_he": "אישי ובריאות",
                "folder": "wiki/personal",
                "subsubjects": {
                    "all": {"title": "All Personal", "title_he": "כל האישי"}
                }
            },
            "development": {
                "title": "Development",
                "title_he": "פיתוח והנדסה",
                "folder": "wiki/development",
                "subsubjects": {
                    "all": {"title": "All Development", "title_he": "כל הפיתוח"}
                }
            }
        }
