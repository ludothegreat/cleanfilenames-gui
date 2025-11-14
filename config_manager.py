"""Configuration management for cleanfilenames."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

DEFAULT_PATTERN = (
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

CONFIG_PATH = Path.home() / ".config" / "cleanfilenames" / "config.json"


@dataclass
class AppConfig:
    regex: str = DEFAULT_PATTERN
    rename_directories: bool = True
    rename_root: bool = True
    stop_on_error: bool = False

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        path = path or CONFIG_PATH
        if not path.exists():
            config = cls()
            config.save(path)
            return config

        try:
            data = json.loads(path.read_text())
            return cls(
                regex=data.get("regex", DEFAULT_PATTERN),
                rename_directories=data.get("rename_directories", True),
                rename_root=data.get("rename_root", True),
                stop_on_error=data.get("stop_on_error", False),
            )
        except (json.JSONDecodeError, OSError):
            config = cls()
            config.save(path)
            return config

    def save(self, path: Optional[Path] = None) -> None:
        path = path or CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))
