import subprocess
from pathlib import Path
from typing import Union, Optional

class GitService:
    """
    Automates Git staging and commits for wiki maintenance and ingestion events.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)

    def commit(self, message: str, files: Optional[list] = None) -> bool:
        try:
            if files:
                for f in files:
                    subprocess.run(["git", "add", str(f)], cwd=self.root_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["git", "add", "."], cwd=self.root_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            res = subprocess.run(["git", "commit", "-m", message], cwd=self.root_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return res.returncode == 0
        except Exception as e:
            print(f"[GitService Warning] Could not perform git commit: {e}")
            return False
