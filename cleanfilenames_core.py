"""Core logic for cleaning filenames and directory names by stripping region tags."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List


REGION_PATTERN = re.compile(
    r"\s*\((?:USA|EU|En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar|En,Fr,De,Es,It,Sv|En,De,Es,Nl,Sv|"
    r"1999-10-29|1999-05-25|2000-10-26|1999-02-25|En,Fr,De,Es,Sv|1995-10-25|"
    r"En,Fr,De,Es,It,Nl,Sv,No,Da,Fi|En,Fr,De,Es,It,Nl|En,Fr,Es,Pt|USA, Europe|"
    r"Virtual Console|En,Fr,De,Es,It,Ni,Sv|En,Es,Fi|En,Fr,De,Nl,Sv,No,Da|U|!|"
    r"1996-09-24|USA,Brazil|1997-08-11||1998-08-10|UnI|En,Fr,Es,Pt|Unl|Unl|"
    r"En,Fr,De,Es,It,Fi|En,Fr,De,Es,Nl,Sv|En,De,Es,It|En,Fr,De,Sv|2000-07-24|"
    r"En,Fr,De,Es,It,Sv|En,Ja,Fr,De|1996-11-21|JP|UK|En,Fr,De,Es,It,Pt|CA|"
    r"En,Fr,De,Es,It|Unl|En,Fr,De,Es,Nl,Sv,Da|En,Fr,De,It|En,Fr,De,Es,It,Nl,Sv,Da|"
    r"En,Fr,De,Es|En,Ja,Fr,De,Es|En,Ja||En,Fr|En,Fr,Es,It,Ja|USA,Asia|USA|En,Fr,De|"
    r"USA,Korea|En,Ja,Fr,De,Es,It,Pt,Pl,Ru|En,Ja|En,Es,It|En,Fr,De,Es,It,Ru|En,Ja,Es|"
    r"USA, Canada|En,Fr,Es|v\d+\.\d+|En,Ja,Fr,De,Es,It,Ko|En,Es|USA,Canada|En,Zh|"
    r"En,Fr,De,Es,It,Pt,Ru|En,Ja,Fr,De,Es,It,Ko|En,Fr,Es,Pt|En,Ja,Fr,De,Es,It|v2.02|"
    r"En,Ja,Fr,Es|En,De|Japan|PAL|NTSC|Europe|World)\)\s*"
)


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


def normalize_name(name: str) -> str:
    """Strip region markers and tidy whitespace."""
    new = REGION_PATTERN.sub(" ", name)
    new = re.sub(r"\s{2,}", " ", new)
    new = re.sub(r"\s+([.\]\)])", r"\1", new)
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


def collect_candidates(root: Path | str) -> List[RenameCandidate]:
    """Scan for files and directories whose names need adjustments."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root}")

    candidates: List[RenameCandidate] = []

    # Files first (top-down walk)
    for dirpath, _, filenames in os.walk(root_path):
        dir_path = Path(dirpath)
        for fname in filenames:
            new_name = normalize_name(fname)
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
    for directory in _iter_directories(root_path):
        new_name = normalize_name(directory.name)
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

    return candidates


def apply_candidates(candidates: Iterable[RenameCandidate]) -> None:
    """Attempt to rename every candidate in-place."""
    # Process files first, then directories
    files = [c for c in candidates if c.item_type == "file"]
    dirs = [c for c in candidates if c.item_type == "directory"]

    for cand in files + dirs:
        if cand.status != "pending":
            continue
        if cand.new_path.exists() and cand.new_path != cand.path:
            cand.status = "error"
            cand.message = "Target already exists"
            continue
        try:
            cand.path.rename(cand.new_path)
            cand.status = "done"
        except OSError as exc:
            cand.status = "error"
            cand.message = str(exc)


def summarize(candidates: Iterable[RenameCandidate]) -> dict:
    """Return simple metrics about rename results."""
    summary = {"total": 0, "files": 0, "directories": 0, "errors": 0, "completed": 0}
    for cand in candidates:
        summary["total"] += 1
        summary[cand.item_type + "s"] += 1
        if cand.status == "done":
            summary["completed"] += 1
        if cand.status == "error":
            summary["errors"] += 1
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Strip region tags from filenames and directories."
    )
    parser.add_argument("path", help="Root directory to scan.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the renames (default: preview only).",
    )
    args = parser.parse_args()

    all_candidates = collect_candidates(args.path)
    if not all_candidates:
        print("No changes to be made.")
        raise SystemExit(0)

    print(f"Found {len(all_candidates)} rename candidates:")
    for cand in all_candidates:
        print(f"[{cand.item_type}] {cand.path} -> {cand.new_path}")

    if args.apply:
        apply_candidates(all_candidates)
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
        print("\nPreview mode only. Use --apply to execute the changes.")
