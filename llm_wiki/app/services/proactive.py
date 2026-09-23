import yaml
from pathlib import Path
from typing import Union, List, Dict, Any
from datetime import datetime

class ProactiveCollectorService:
    """
    Implements Proactive Ingestion (Sections 28-30 of specification).
    Manages recurring prompt schedules in system/proactive/ for financial, health, and research updates.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.proactive_dir = self.root_dir / "system" / "proactive"
        self.proactive_dir.mkdir(parents=True, exist_ok=True)
        self._init_default_configs()

    def _init_default_configs(self) -> None:
        defaults = [
            {
                "id": "daily-personal-log",
                "domain": "personal",
                "frequency": "daily",
                "question": "How was your physical & mental state today? Any training or insights?",
                "output_type": "observation"
            },
            {
                "id": "weekly-research-synthesis",
                "domain": "research",
                "frequency": "weekly",
                "question": "What core technical concepts or papers did you explore this week?",
                "output_type": "synthesis"
            },
            {
                "id": "monthly-finance-update",
                "domain": "business",
                "frequency": "monthly",
                "question": "Please update monthly revenue, expenses, and strategic decisions.",
                "output_type": "metric_update"
            }
        ]
        for config in defaults:
            cfg_path = self.proactive_dir / f"{config['id']}.yaml"
            if not cfg_path.exists():
                with open(cfg_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f)

    def get_pending_prompts(self) -> List[Dict[str, Any]]:

        prompts = []
        for cfg_file in self.proactive_dir.glob("*.yaml"):
            with open(cfg_file, "r", encoding="utf-8") as f:
                prompts.append(yaml.safe_load(f))
        return prompts
