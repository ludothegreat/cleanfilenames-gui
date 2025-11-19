"""Configuration management for cleanfilenames."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional

PRESETS_DIR = Path(__file__).parent / "presets"


def load_preset_tokens(preset_name: str) -> List[str]:
    """Load a list of tokens from a preset file."""
    preset_file = PRESETS_DIR / f"{preset_name}.txt"
    if not preset_file.exists():
        return []
    return [
        line.strip() for line in preset_file.read_text().splitlines() if line.strip()
    ]


def build_regex(tokens: List[str]) -> str:
    """Build the regex pattern from a list of tokens."""
    inner = "|".join(filter(None, tokens))
    return rf"\s*\((?:{inner})\)\s*"


DEFAULT_TOKENS = load_preset_tokens("default")
DEFAULT_PATTERN = build_regex(DEFAULT_TOKENS)

CONFIG_PATH = Path.home() / ".config" / "cleanfilenames" / "config.json"


class ConfigLoadError(RuntimeError):
    """Raised when the application config cannot be loaded."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = Path(path)
        super().__init__(message)


@dataclass
class AppConfig:
    regex: str = DEFAULT_PATTERN
    rename_directories: bool = True
    rename_root: bool = True
    stop_on_error: bool = False
    auto_resolve_conflicts: bool = False
    tokens: Optional[List[str]] = field(
        default_factory=lambda: DEFAULT_TOKENS.copy()
    )

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        print(f"Loading config from: {path}")
        is_default_path = path is None
        path = path or CONFIG_PATH

        if not path.exists():
            print(f"Path does not exist: {path}")
            if is_default_path:
                # If using the default path, create it on first run
                print("Using default path, creating config.")
                config = cls()
                config.save(path)
                return config
            else:
                # If a specific path was provided and it doesn't exist, raise an error
                print("Raising FileNotFoundError")
                raise FileNotFoundError(f"Config file not found at specified path: {path}")

        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:  # pragma: no cover - depends on user input
            raise ConfigLoadError(path, f"Failed to parse config: {exc}") from exc
        except OSError as exc:  # pragma: no cover - depends on filesystem issues
            raise ConfigLoadError(path, f"Unable to read config: {exc}") from exc

        tokens_field = data.get("tokens", DEFAULT_TOKENS)
        if tokens_field is None:
            tokens: Optional[List[str]] = None
        elif isinstance(tokens_field, list):
            tokens = list(tokens_field)
        else:
            tokens = DEFAULT_TOKENS.copy()

        config = cls(
            regex=data.get("regex", DEFAULT_PATTERN),
            rename_directories=data.get("rename_directories", True),
            rename_root=data.get("rename_root", True),
            stop_on_error=data.get("stop_on_error", False),
            auto_resolve_conflicts=data.get("auto_resolve_conflicts", False),
            tokens=tokens,
        )
        if config.tokens:
            rebuilt = build_regex(config.tokens)
            config.regex = rebuilt
        return config

    def save(self, path: Optional[Path] = None) -> None:
        path = path or CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))


__all__ = [
    "AppConfig",
    "DEFAULT_PATTERN",
    "DEFAULT_TOKENS",
    "build_regex",
    "CONFIG_PATH",
    "ConfigLoadError",
]
