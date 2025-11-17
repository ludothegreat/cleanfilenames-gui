"""Core logic for cleaning filenames and directory names by stripping region tags."""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Set

# Support both package and script imports
try:  # pragma: no cover
    from .config_manager import (  # type: ignore
        AppConfig,
        ConfigLoadError,
        DEFAULT_PATTERN,
        build_regex,
    )
    from .token_manager import TokenTracker
except ImportError:  # pragma: no cover
    from config_manager import AppConfig, ConfigLoadError, DEFAULT_PATTERN, build_regex
    from token_manager import TokenTracker

REGION_PATTERN = re.compile(DEFAULT_PATTERN)


def _is_case_insensitive_filesystem() -> bool:
    """Detect if the filesystem is case-insensitive (Windows, macOS)."""
    # Create a temp file and check if we can find it with different case
    with tempfile.NamedTemporaryFile(prefix='CasE_TeSt_', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        # Try to find it with different case
        tmp_lower = Path(str(tmp_path).lower())
        # If the lowercase version exists and has a different string representation,
        # the filesystem is case-insensitive
        result = tmp_lower.exists() and str(tmp_lower) != str(tmp_path)
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


# Cache the result since filesystem type doesn't change during execution
_CASE_INSENSITIVE = _is_case_insensitive_filesystem()


def _normalize_path_for_comparison(path: Path) -> str:
    """Normalize path for collision detection on case-insensitive systems."""
    if _CASE_INSENSITIVE:
        return str(path.resolve()).lower()
    return str(path.resolve())


@dataclass
class RenameCandidate:
    """Represents a file or directory rename that will be performed."""

    path: Path
    new_name: str
    new_path: Path
    item_type: str  # "file" or "directory"
    status: str = "pending"  # pending, done, error, skipped
    message: str = ""
    relative_path: str = ""
    original_relative_path: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.item_type,
            "old": str(self.path),
            "new": str(self.new_path),
            "status": self.status,
            "message": self.message,
        }


def normalize_name(name: str, pattern: re.Pattern[str] = REGION_PATTERN) -> str:
    """Strip region markers and tidy whitespace."""
    new = pattern.sub(" ", name)
    new = re.sub(r"\s{2,}", " ", new)
    new = re.sub(r"\s+([.\]\)])", r"\1", new)
    new = new.replace("\\", "")
    return new.strip()


def _iter_directories(root: Path) -> Iterable[Path]:
    """Yield directories under root, including root, deepest first."""
    dirs = set()
    for dirpath, dirnames, _ in os.walk(root):
        dir_path = Path(dirpath)
        dirs.add(dir_path)
        for d in dirnames:
            dirs.add(dir_path / d)
    return sorted(dirs, key=lambda p: len(p.parts), reverse=True)


def collect_candidates(
    root: Path | str,
    *,
    config: Optional[AppConfig] = None,
    token_tracker: Optional["TokenTracker"] = None,
) -> List[RenameCandidate]:
    """Scan for files and directories whose names need adjustments."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root}")

    config = config or AppConfig.load()
    pattern_text = config.regex
    if config.tokens:
        pattern_text = build_regex(config.tokens)
    pattern = re.compile(pattern_text)
    candidates: List[RenameCandidate] = []

    if token_tracker:
        token_tracker.observe(root_path.name, root_path)

    # Files first (top-down walk)
    for dirpath, dirnames, filenames in os.walk(root_path):
        dir_path = Path(dirpath)
        if token_tracker:
            for dirname in dirnames:
                token_tracker.observe(dirname, dir_path / dirname)
        for fname in filenames:
            if token_tracker:
                token_tracker.observe(fname, dir_path / fname)
            new_name = normalize_name(fname, pattern)
            if new_name != fname:
                path = dir_path / fname
                new_path = dir_path / new_name
                relative = str(path.relative_to(root_path))
                candidates.append(
                    RenameCandidate(
                        path=path,
                        new_name=new_name,
                        new_path=new_path,
                        item_type="file",
                        original_relative_path=relative,
                        relative_path=relative,
                    )
                )

    # Directories, deepest-first to avoid renaming parents before children
    if config.rename_directories:
        for directory in _iter_directories(root_path):
            new_name = normalize_name(directory.name, pattern)
            if not config.rename_root and directory == root_path:
                continue
            if new_name != directory.name:
                new_path = directory.with_name(new_name)
                relative = str(directory.relative_to(root_path))
                candidates.append(
                    RenameCandidate(
                        path=directory,
                        new_name=new_name,
                        new_path=new_path,
                        item_type="directory",
                        original_relative_path=relative,
                        relative_path=relative,
                    )
                )
    else:
        # Still consider root rename if explicitly allowed
        if config.rename_root:
            root_name = normalize_name(root_path.name, pattern)
            if root_name != root_path.name:
                parent = root_path.parent
                candidates.append(
                    RenameCandidate(
                        path=root_path,
                        new_name=root_name,
                        new_path=parent / root_name,
                        item_type="directory",
                        original_relative_path=".",
                        relative_path=".",
                    )
                )

    # Build a complete directory map for ALL directories (not just renamed ones)
    # This ensures files in non-renamed subdirectories get correct parent paths
    dir_map: dict[Path, Path] = {root_path: root_path}
    dir_candidates = [c for c in candidates if c.item_type == "directory"]

    # First pass: map directories that are being renamed
    for cand in sorted(dir_candidates, key=lambda c: len(c.path.parts)):
        parent_new = dir_map.get(cand.path.parent, cand.path.parent)
        cand.new_path = parent_new / cand.new_name
        dir_map[cand.path] = cand.new_path

    # Second pass: map ALL directories (including non-renamed ones)
    # by walking the tree and applying parent transformations
    all_dirs = set()
    for dirpath, dirnames, _ in os.walk(root_path):
        all_dirs.add(Path(dirpath))
        for dirname in dirnames:
            all_dirs.add(Path(dirpath) / dirname)

    for directory in sorted(all_dirs, key=lambda p: len(p.parts)):
        if directory not in dir_map:
            # This directory isn't being renamed, but its parent might be
            parent_new = dir_map.get(directory.parent, directory.parent)
            dir_map[directory] = parent_new / directory.name

    root_target = dir_map.get(root_path, root_path)

    for cand in candidates:
        if cand.item_type == "file":
            parent_new = dir_map.get(cand.path.parent, cand.path.parent)
            cand.new_path = parent_new / cand.new_name

        target_path = cand.new_path
        try:
            rel = target_path.relative_to(root_target)
            cand.relative_path = str(rel) if rel != Path(".") else "."
        except ValueError:
            cand.relative_path = str(target_path)

    return candidates


def apply_candidates(
    candidates: Iterable[RenameCandidate],
    *,
    dry_run: bool = False,
    stop_on_error: bool = False,
) -> None:
    """Attempt to rename every candidate in-place."""
    dirs = sorted(
        [c for c in candidates if c.item_type == "directory"],
        key=lambda cand: len(cand.path.parts),
        reverse=True,
    )
    files = [c for c in candidates if c.item_type == "file"]

    # Track occupied paths using normalized (case-insensitive on Windows/macOS) keys
    occupied: Set[str] = set()
    target_map: dict[str, Path] = {}

    # Track runtime directory renames (original -> current location)
    # This is updated as we perform each directory rename
    dir_renames: dict[Path, Path] = {}

    for cand in dirs + files:
        if cand.status != "pending":
            continue
        if cand.item_type == "file":
            # Directories are renamed first, so the file now lives beneath the
            # normalized parent path but still has its original filename.
            source_path = cand.new_path.parent / cand.path.name
            target_path = cand.new_path
        else:
            # For directories, check if the parent has been renamed
            current_parent = dir_renames.get(cand.path.parent, cand.path.parent)
            source_path = current_parent / cand.path.name
            target_path = current_parent / cand.new_name

        # Normalize paths for case-insensitive comparison
        source_norm = _normalize_path_for_comparison(source_path)
        target_norm = _normalize_path_for_comparison(target_path)
        new_path_norm = _normalize_path_for_comparison(cand.new_path)

        # Check if target already exists (case-insensitive on Windows/macOS)
        if target_path.exists() and target_norm != source_norm:
            cand.status = "error"
            cand.message = f"Target already exists on disk: {target_path}"
            cand.relative_path = str(target_path)
            continue
        if cand.new_path.exists() and new_path_norm != source_norm:
            cand.status = "error"
            cand.message = f"Target already exists on disk: {cand.new_path}"
            continue

        # Check if another pending rename will create this same target
        if new_path_norm in occupied and new_path_norm != source_norm:
            other = target_map.get(new_path_norm)
            other_desc = f": {other}" if other else ""
            cand.status = "error"
            cand.message = f"Multiple items are targeting this name{other_desc}"
            continue

        try:
            if dry_run:
                cand.status = "done (dry run)"
                occupied.add(new_path_norm)
                target_map[new_path_norm] = target_path
                # Track dry-run directory renames too for consistency
                if cand.item_type == "directory":
                    dir_renames[cand.path] = target_path
            else:
                source_path.rename(target_path)
                cand.status = "done"
                occupied.add(new_path_norm)
                target_map[new_path_norm] = target_path
                # Track where this directory actually is now
                if cand.item_type == "directory":
                    dir_renames[cand.path] = target_path
        except OSError as exc:
            cand.status = "error"
            cand.message = str(exc)
        if cand.status == "error" and stop_on_error:
            break


def summarize(candidates: Iterable[RenameCandidate]) -> dict:
    """Return simple metrics about rename results."""
    summary = {"total": 0, "files": 0, "directories": 0, "errors": 0, "completed": 0}
    type_key = {"file": "files", "directory": "directories"}
    for cand in candidates:
        summary["total"] += 1
        summary[type_key.get(cand.item_type, "files")] += 1
        if cand.status.startswith("done"):
            summary["completed"] += 1
        if cand.status == "error":
            summary["errors"] += 1
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strip region tags from filenames and directories."
    )
    parser.add_argument("path", help="Root directory to scan.")
    parser.add_argument(
        "--config",
        help="Path to config JSON (default: ~/.config/cleanfilenames/config.json)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the renames.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly skip renames even if --apply is provided.",
    )
    args = parser.parse_args()

    try:
        config = (
            AppConfig.load(Path(args.config).expanduser())
            if args.config
            else AppConfig.load()
        )
    except ConfigLoadError as exc:
        print(f"Configuration error: {exc}")
        print(
            f"Fix or remove '{exc.path}' (it's JSON) and rerun. "
            "Deleting it will recreate the default settings."
        )
        raise SystemExit(2)
    all_candidates = collect_candidates(args.path, config=config)
    if not all_candidates:
        print("No changes to be made.")
        raise SystemExit(0)

    print(f"Found {len(all_candidates)} rename candidates:")
    for cand in all_candidates:
        print(f"[{cand.item_type}] {cand.path} -> {cand.new_path}")

    if args.apply:
        apply_candidates(
            all_candidates,
            dry_run=args.dry_run,
            stop_on_error=config.stop_on_error,
        )
        summary = summarize(all_candidates)
        if args.dry_run:
            print(
                f"\nDry run complete: {summary['completed']} pending renames "
                f"({summary['errors']} would fail)."
            )
        else:
            print(
                f"\nCompleted {summary['completed']} renames "
                f"({summary['errors']} errors)."
            )
        if summary["errors"]:
            for cand in all_candidates:
                if cand.status == "error":
                    print(f" - Failed: {cand.path} -> {cand.new_path}: {cand.message}")
    else:
        print("\nPreview mode only. Use --apply to execute changes.")
