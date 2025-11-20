"""Tests for cleanfilenames_core module."""

import re
from pathlib import Path

import pytest

from cleanfilenames_core import (
    RenameCandidate,
    apply_candidates,
    collect_candidates,
    normalize_name,
    summarize,
)
from config_manager import AppConfig


class TestNormalizeName:
    """Tests for normalize_name function."""

    def test_removes_usa_tag(self):
        """Test removal of USA region tag."""
        assert normalize_name("Game (USA).zip") == "Game.zip"

    def test_removes_eu_tag(self):
        """Test removal of EU region tag."""
        assert normalize_name("Game (EU).zip") == "Game.zip"

    def test_removes_jp_tag(self):
        """Test removal of JP region tag."""
        assert normalize_name("Game (JP).zip") == "Game.zip"

    def test_removes_multi_language_tag(self):
        """Test removal of multi-language region tag."""
        assert normalize_name("Game (En,Fr,De,Es,It).zip") == "Game.zip"

    def test_trims_extra_whitespace(self):
        """Test that extra whitespace is normalized."""
        assert normalize_name("Game  (USA)  .zip") == "Game.zip"

    def test_no_space_before_extension(self):
        """Test that spaces before extensions are removed."""
        assert normalize_name("Game (USA) .zip") == "Game.zip"

    def test_preserves_non_tagged_names(self):
        """Test that files without tags are unchanged."""
        assert normalize_name("Normal File.txt") == "Normal File.txt"

    def test_removes_backslashes(self):
        """Test that backslashes are removed."""
        assert normalize_name("Game\\Test (USA).zip") == "GameTest.zip"

    def test_multiple_tags(self):
        """Test removal of multiple tags."""
        assert normalize_name("Game (USA) (v1.0).zip") == "Game.zip"

    def test_custom_pattern(self):
        """Test with custom regex pattern."""
        pattern = re.compile(r"\s*\(v\d+\.\d+\)\s*")
        assert normalize_name("Game (v1.0).zip", pattern) == "Game.zip"


class TestCollectCandidates:
    """Tests for collect_candidates function."""

    def test_finds_files_with_tags(self, sample_files):
        """Test that files with region tags are detected."""
        candidates = collect_candidates(sample_files)
        assert len(candidates) > 0
        assert all(isinstance(c, RenameCandidate) for c in candidates)

    def test_skips_files_without_tags(self, sample_files):
        """Test that files without tags are not included."""
        candidates = collect_candidates(sample_files)
        original_names = [c.path.name for c in candidates]
        assert "Normal File.txt" not in original_names

    def test_finds_directories_with_tags(self, sample_dirs):
        """Test that directories with tags are detected."""
        config = AppConfig()
        config.rename_directories = True
        candidates = collect_candidates(sample_dirs, config=config)
        dir_candidates = [c for c in candidates if c.item_type == "directory"]
        assert len(dir_candidates) > 0

    def test_respects_rename_directories_false(self, sample_dirs):
        """Test that directories are skipped when rename_directories=False."""
        config = AppConfig()
        config.rename_directories = False
        candidates = collect_candidates(sample_dirs, config=config)
        dir_candidates = [c for c in candidates if c.item_type == "directory"]
        assert len(dir_candidates) == 0

    def test_respects_rename_root_false(self, temp_dir):
        """Test that root directory is not renamed when rename_root=False."""
        root = temp_dir / "Root (USA)"
        root.mkdir()
        (root / "file.txt").touch()

        config = AppConfig()
        config.rename_root = False
        candidates = collect_candidates(root, config=config)

        root_candidates = [c for c in candidates if c.path == root]
        assert len(root_candidates) == 0

    def test_nonexistent_path_raises_error(self):
        """Test that nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            collect_candidates("/nonexistent/path")

    def test_nested_directory_order(self, sample_dirs):
        """Test that directories are ordered deepest-first."""
        config = AppConfig()
        config.rename_directories = True
        candidates = collect_candidates(sample_dirs, config=config)
        dir_candidates = [c for c in candidates if c.item_type == "directory"]

        # Verify deepest directories come first
        if len(dir_candidates) > 1:
            depths = [len(c.path.parts) for c in dir_candidates]
            assert depths == sorted(depths, reverse=True)


class TestApplyCandidates:
    """Tests for apply_candidates function."""

    def test_dry_run_no_changes(self, sample_files):
        """Test that dry run doesn't modify filesystem."""
        config = AppConfig()
        candidates = collect_candidates(sample_files, config=config)
        original_files = set(sample_files.glob("*"))

        apply_candidates(candidates, config=config, dry_run=True)

        current_files = set(sample_files.glob("*"))
        assert original_files == current_files

    def test_dry_run_status_updated(self, sample_files):
        """Test that dry run updates candidate status."""
        config = AppConfig()
        config.auto_resolve_conflicts = True  # Enable auto-resolve to avoid collisions
        candidates = collect_candidates(sample_files, config=config)

        apply_candidates(candidates, config=config, dry_run=True)

        assert all(c.status == "done (dry run)" for c in candidates)

    def test_actual_rename(self, temp_dir):
        """Test that files are actually renamed."""
        test_file = temp_dir / "Game (USA).zip"
        test_file.touch()

        config = AppConfig()
        candidates = collect_candidates(temp_dir, config=config)
        apply_candidates(candidates, config=config, dry_run=False)

        assert not test_file.exists()
        assert (temp_dir / "Game.zip").exists()

    def test_collision_detection(self, collision_files):
        """Test that collisions are detected."""
        config = AppConfig()
        config.auto_resolve_conflicts = False
        candidates = collect_candidates(collision_files, config=config)
        apply_candidates(candidates, config=config, dry_run=False)

        errors = [c for c in candidates if c.status == "error"]
        assert len(errors) > 0

    def test_auto_resolve_conflicts(self, collision_files):
        """Test that auto-resolve adds numeric suffixes."""
        config = AppConfig()
        config.auto_resolve_conflicts = True
        candidates = collect_candidates(collision_files, config=config)
        apply_candidates(candidates, config=config, dry_run=False)

        # Should have Game.zip, Game (1).zip, Game (2).zip
        assert (collision_files / "Game.zip").exists()
        assert (collision_files / "Game (1).zip").exists() or (collision_files / "Game (2).zip").exists()

    def test_stop_on_error(self, collision_files):
        """Test that stop_on_error halts processing."""
        config = AppConfig()
        config.auto_resolve_conflicts = False
        config.stop_on_error = True

        candidates = collect_candidates(collision_files, config=config)
        apply_candidates(candidates, config=config, dry_run=False)

        # Some candidates should still be pending
        pending = [c for c in candidates if c.status == "pending"]
        assert len(pending) > 0

    def test_directory_rename_before_files(self, sample_dirs):
        """Test that directories are renamed before their files."""
        config = AppConfig()
        config.rename_directories = True
        candidates = collect_candidates(sample_dirs, config=config)
        apply_candidates(candidates, config=config, dry_run=False)

        # All operations should succeed
        errors = [c for c in candidates if c.status == "error"]
        assert len(errors) == 0


class TestSummarize:
    """Tests for summarize function."""

    def test_counts_total(self, sample_files):
        """Test that total count is correct."""
        config = AppConfig()
        candidates = collect_candidates(sample_files, config=config)
        summary = summarize(candidates)
        assert summary["total"] == len(candidates)

    def test_counts_files_and_directories(self, sample_dirs):
        """Test that files and directories are counted separately."""
        config = AppConfig()
        config.rename_directories = True
        candidates = collect_candidates(sample_dirs, config=config)
        summary = summarize(candidates)

        assert summary["files"] > 0
        assert summary["directories"] > 0
        assert summary["total"] == summary["files"] + summary["directories"]

    def test_counts_completed(self, sample_files):
        """Test that completed renames are counted."""
        config = AppConfig()
        config.auto_resolve_conflicts = True  # Enable auto-resolve to avoid collisions
        candidates = collect_candidates(sample_files, config=config)
        apply_candidates(candidates, config=config, dry_run=True)
        summary = summarize(candidates)

        assert summary["completed"] == len(candidates)

    def test_counts_errors(self, collision_files):
        """Test that errors are counted."""
        config = AppConfig()
        config.auto_resolve_conflicts = False
        candidates = collect_candidates(collision_files, config=config)
        apply_candidates(candidates, config=config, dry_run=False)
        summary = summarize(candidates)

        assert summary["errors"] > 0
