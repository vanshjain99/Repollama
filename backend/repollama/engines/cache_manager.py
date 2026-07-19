from __future__ import annotations
import hashlib
import json
from pathlib import Path


class CacheManager:
    """Manages file hashes to determine if files have changed since the last run."""

    def __init__(self, repo_path: str | Path) -> None:
        """Initialize with repository path and locate the cache file."""
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = self.repo_path / ".repollama_data"
        self.cache_file = self.cache_dir / "hash_cache.json"

    def load_cache(self) -> dict[str, str]:
        """Load the JSON dictionary mapping file paths to their SHA-256 hashes.

        Returns:
            A dictionary of file path to hash. Returns empty dict if file does not exist.
        """
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def save_cache(self, cache: dict[str, str]) -> None:
        """Save the cache dictionary back to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=4)
        except Exception:
            pass

    def compute_hash(self, file_path: str) -> str | None:
        """Read a file as bytes and return its SHA-256 hex digest.

        Returns None if the file cannot be read.
        """
        p = Path(file_path)
        if not p.is_absolute():
            p = self.repo_path / p

        if not p.is_file():
            return None

        try:
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def has_changed(self, file_path: str, current_cache: dict[str, str]) -> bool:
        """Compute the hash.

        If it differs from current_cache, updates the cache dictionary and returns True.
        If identical, returns False.
        """
        new_hash = self.compute_hash(file_path)

        key = file_path
        p = Path(file_path)
        if p.is_absolute():
            try:
                key = str(p.relative_to(self.repo_path))
            except ValueError:
                pass

        old_hash = current_cache.get(key)
        if new_hash != old_hash:
            if new_hash is None:
                current_cache.pop(key, None)
            else:
                current_cache[key] = new_hash
            return True
        return False
