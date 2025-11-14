"""Core logic for cleaning filenames and directory names by stripping region tags."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Set

# Support both package and script imports
try:  # pragma: no cover
    from .config_manager import AppConfig, DEFAULT_PATTERN  # type: ignore
except ImportError:  # pragma: no cover
    from config_manager import AppConfig, DEFAULT_PATTERN

REGION_PATTERN = re.compile(DEFAULT_PATTERN)


@dataclass
class RenameCandidate:
    """Represents a file or directory rename that will be performed."""

    path: Path
    new_name: str
    new_path: Path
    item_type: str  # "file" or "directory"
    status: str = "pending"  # pending, done, error, skipped
    message: str = ""

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
    root: Path | str, *, config: Optional[AppConfig] = None
) -> List[RenameCandidate]:
    """Scan for files and directories whose names need adjustments."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root}")

    config = config or AppConfig.load()
    pattern = re.compile(config.regex)
    candidates: List[RenameCandidate] = []

    # Files first (top-down walk)
    for dirpath, _, filenames in os.walk(root_path):
        dir_path = Path(dirpath)
        for fname in filenames:
            new_name = normalize_name(fname, pattern)
            if new_name != fname:
                new_path = dir_path / new_name
                candidates.append(
                    RenameCandidate(
                        path=dir_path / fname,
                        new_name=new_name,
                        new_path=new_path,
                        item_type="file",
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
                candidates.append(
                    RenameCandidate(
                        path=directory,
                        new_name=new_name,
                        new_path=new_path,
                        item_type="directory",
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
                    )
                )

    return candidates


def apply_candidates(
    candidates: Iterable[RenameCandidate],
    *,
    dry_run: bool = False,
    stop_on_error: bool = False,
) -> None:
    """Attempt to rename every candidate in-place."""
    # Process files first, then directories
    files = [c for c in candidates if c.item_type == "file"]
    dirs = [c for c in candidates if c.item_type == "directory"]

    occupied: Set[Path] = set()

    for cand in files + dirs:
        if cand.status != "pending":
            continue
        if cand.new_path.exists() and cand.new_path != cand.path:
            cand.status = "error"
            cand.message = "Target already exists"
            continue
        if cand.new_path in occupied and cand.new_path != cand.path:
            cand.status = "error"
            cand.message = "Another item already targets this name"
            continue
        try:
            if dry_run:
                cand.status = "done (dry run)"
                occupied.add(cand.new_path)
            else:
                cand.path.rename(cand.new_path)
                cand.status = "done"
                occupied.add(cand.new_path)
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

    config = (
        AppConfig.load(Path(args.config).expanduser())
        if args.config
        else AppConfig.load()
    )
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
