"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from config_manager import AppConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir: Path) -> Path:
    """Create sample files with region tags for testing."""
    # Files with region tags
    (temp_dir / "Game (USA).zip").touch()
    (temp_dir / "Game (EU).zip").touch()
    (temp_dir / "Game (JP).zip").touch()
    (temp_dir / "Game (En,Fr,De,Es,It).zip").touch()
    (temp_dir / "Game  (USA)  .zip").touch()  # Extra whitespace
    (temp_dir / "Normal File.txt").touch()  # No tags

    return temp_dir


@pytest.fixture
def sample_dirs(temp_dir: Path) -> Path:
    """Create sample directories with region tags for testing."""
    (temp_dir / "Folder (USA)").mkdir()
    (temp_dir / "Folder (USA)" / "Game (JP).zip").touch()
    (temp_dir / "Nested" / "Deep (EU)" / "Game (USA).zip").mkdir(parents=True, exist_ok=True)
    (temp_dir / "Nested" / "Deep (EU)" / "Game (USA).zip").touch()

    return temp_dir


@pytest.fixture
def temp_config(temp_dir: Path) -> Generator[AppConfig, None, None]:
    """Create a temporary config for testing."""
    config_path = temp_dir / "test_config.json"
    config = AppConfig()
    config.save(config_path)
    yield config
    if config_path.exists():
        config_path.unlink()


@pytest.fixture
def collision_files(temp_dir: Path) -> Path:
    """Create files that will collide after cleaning."""
    (temp_dir / "Game (USA).zip").touch()
    (temp_dir / "Game (EU).zip").touch()
    (temp_dir / "Game (JP).zip").touch()
    # These all clean to "Game.zip"

    return temp_dir
