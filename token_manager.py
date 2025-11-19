"""Utilities for managing region tokens."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

TOKEN_FINDER = re.compile(r"\(([^()]+)\)")
MAX_SAMPLES = 3

# See: https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
INVALID_FILENAME_CHARS: Set[str] = {'<', '>', ':', '"', '/', '\\', '|', '?', '*'}


def validate_tokens(tokens: List[str]) -> List[str]:
    """Check a list of tokens for invalid characters or formatting."""
    errors: List[str] = []
    for i, token in enumerate(tokens, 1):
        # The '|' character is of special concern as it's used as the regex delimiter.
        # While it's technically a valid regex character, allowing it in a token
        # is almost always a mistake unless the user is an expert.
        # We will forbid it to prevent users from shooting themselves in the foot
        # by creating a file with `token1|token2` on a single line.
        if '|' in token:
            errors.append(f"Line {i}: Token contains a '|' character. Each token should be on its own line.")

        # Check for other invalid filename characters.
        # This is not a perfect regex character validator, but it prevents mistakes.
        invalid_chars_found = INVALID_FILENAME_CHARS.intersection(token)
        if invalid_chars_found:
            # Format the found characters for a readable error message.
            char_list = ", ".join(f"'{c}'" for c in sorted(list(invalid_chars_found)))
            errors.append(f"Line {i}: Token contains invalid filename characters: {char_list}")
            
    return errors


TOKEN_FINDER = re.compile(r"\(([^()]+)\)")
MAX_SAMPLES = 3


def normalize_token(token: str) -> str:
    """Trim whitespace from tokens for consistent comparisons."""
    return token.strip()


def find_duplicate_tokens(tokens: Iterable[str]) -> Dict[str, int]:
    """Return a mapping of duplicate tokens to their occurrence count."""
    counts: Dict[str, int] = {}
    for token in tokens:
        normalized = normalize_token(token)
        if not normalized:
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
    return {token: count for token, count in counts.items() if count > 1}


@dataclass
class TokenSuggestion:
    token: str
    count: int = 0
    samples: List[str] = field(default_factory=list)


@dataclass
class TokenUsage:
    token: str
    count: int = 0


class TokenTracker:
    """Inspect filenames and directories to track token usage and suggestions."""

    def __init__(self, known_tokens: Optional[Iterable[str]] = None) -> None:
        known_list = [
            normalize_token(token)
            for token in (known_tokens or [])
            if normalize_token(token)
        ]
        self.known_tokens: List[str] = known_list
        self._known_set = set(known_list)
        self._known_usage: Dict[str, int] = {}
        self._suggestions: Dict[str, TokenSuggestion] = {}
        self._duplicate_map = find_duplicate_tokens(known_list)

    def observe(self, name: str, path: Path) -> None:
        """Record tokens spotted in a file or directory name."""
        if not name:
            return
        for match in TOKEN_FINDER.finditer(name):
            token = normalize_token(match.group(1))
            if not token:
                continue
            if token in self._known_set:
                self._known_usage[token] = self._known_usage.get(token, 0) + 1
            else:
                suggestion = self._suggestions.setdefault(token, TokenSuggestion(token))
                suggestion.count += 1
                sample = str(path)
                if sample not in suggestion.samples and len(suggestion.samples) < MAX_SAMPLES:
                    suggestion.samples.append(sample)

    def usage(self) -> List[TokenUsage]:
        """Return usage counts for the known tokens."""
        usages: List[TokenUsage] = []
        for token in self.known_tokens:
            usages.append(TokenUsage(token=token, count=self._known_usage.get(token, 0)))
        return usages

    def suggestions(self) -> List[TokenSuggestion]:
        """Return discovered tokens that are not part of the known list."""
        return sorted(
            self._suggestions.values(),
            key=lambda suggestion: suggestion.count,
            reverse=True,
        )

    def duplicate_tokens(self) -> Dict[str, int]:
        """Return duplicates that were detected in the known token list."""
        return dict(self._duplicate_map)


__all__ = [
    "TokenSuggestion",
    "TokenTracker",
    "TokenUsage",
    "find_duplicate_tokens",
    "normalize_token",
    "validate_tokens",
]
