import hashlib
from pathlib import Path
from typing import Union

class Hasher:
    """
    Computes SHA-256 hashes for raw content deduplication.
    """
    @staticmethod
    def compute_file_hash(file_path: Union[str, Path]) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def compute_text_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
