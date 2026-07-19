from __future__ import annotations
import json
from pathlib import Path
from repollama.engines.cache_manager import CacheManager


def test_cache_manager_load_save(tmp_path: Path):
    cache_mgr = CacheManager(tmp_path)
    # Cache file shouldn't exist initially
    assert not cache_mgr.cache_file.exists()

    # Load cache should return empty dict
    cache = cache_mgr.load_cache()
    assert cache == {}

    # Save cache
    test_data = {"src/main.py": "hash123", "src/utils.py": "hash456"}
    cache_mgr.save_cache(test_data)
    assert cache_mgr.cache_file.exists()

    # Load cache again
    loaded = cache_mgr.load_cache()
    assert loaded == test_data


def test_cache_manager_compute_hash(tmp_path: Path):
    cache_mgr = CacheManager(tmp_path)
    file_path = tmp_path / "test.py"

    # Non-existent file should return None
    assert cache_mgr.compute_hash(str(file_path)) is None

    # Write content and compute hash
    file_path.write_text("print('hello')", encoding="utf-8")
    h1 = cache_mgr.compute_hash(str(file_path))
    assert h1 is not None
    assert len(h1) == 64  # SHA-256 is 64 characters hex

    # Modify content and compute hash again
    file_path.write_text("print('hello world')", encoding="utf-8")
    h2 = cache_mgr.compute_hash(str(file_path))
    assert h2 is not None
    assert h1 != h2

    # Deleted file should return None
    file_path.unlink()
    assert cache_mgr.compute_hash(str(file_path)) is None


def test_cache_manager_has_changed(tmp_path: Path):
    cache_mgr = CacheManager(tmp_path)
    file_path = tmp_path / "test.py"
    file_path.write_text("hello", encoding="utf-8")
    rel_path_str = "test.py"

    cache = {}
    # Case 1: File is new (not in cache)
    changed = cache_mgr.has_changed(str(file_path), cache)
    assert changed is True
    assert rel_path_str in cache
    expected_hash = cache[rel_path_str]

    # Case 2: File has not changed
    changed = cache_mgr.has_changed(str(file_path), cache)
    assert changed is False
    assert cache[rel_path_str] == expected_hash

    # Case 3: File is modified
    file_path.write_text("hello world", encoding="utf-8")
    changed = cache_mgr.has_changed(str(file_path), cache)
    assert changed is True
    assert cache[rel_path_str] != expected_hash
    new_hash = cache[rel_path_str]

    # Case 4: File is deleted
    file_path.unlink()
    changed = cache_mgr.has_changed(str(file_path), cache)
    assert changed is True
    assert rel_path_str not in cache
