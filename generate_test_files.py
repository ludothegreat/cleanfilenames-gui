#!/usr/bin/env python3
"""Generate test files for CleanFilenames - Run this first to create sample files!"""

import argparse
import random
import shutil
import sys
from pathlib import Path
from typing import List

# Test directory - will be created next to this script
TEST_DIR_NAME = "CleanFilenames_TestFiles"

# Region tags from cleanfilenames config (subset of most common ones)
REGION_TAGS = [
    "USA", "EU", "JP", "UK", "CA", "PAL", "NTSC",
    "En,Fr,De,Es,It", "En,Ja", "En,Fr,De", "En,Es",
    "En,Fr,De,Es,It,Pt", "USA,Europe", "USA,EU,JP",
    "World", "Virtual Console", "Japan", "Europe",
    "En,Ja,Fr,De,Es,It", "1999-10-29", "v1.0", "v2.02",
    "Rev A", "Rev 1", "Beta", "Proto", "Demo",
]

# Tokens intentionally missing from the default config to exercise auto-detect
UNKNOWN_REGION_TAGS = [
    "Asia Rev B",
    "FanFix",
    "Spain,Portugal",
    "En,Pl,Cz",
    "Prototype-Alt",
    "Korea",
    "Scandinavia",
    "Arcade Only",
    "Rest of World",
]

# Junk tags commonly found in ROM collections
JUNK_TAGS = [
    "[!]", "[b]", "[h]", "[o]", "[t]", "[T+]",
    "(b)", "(h)", "(o)", "(t)",
]

# Game name components for realistic ROM names
GAME_PREFIXES = [
    "Super", "The Legend of", "Final", "Street", "Sonic the",
    "Mega", "Donkey Kong", "Mario", "Zelda", "Metroid",
    "Castlevania", "Contra", "Double Dragon", "Golden",
    "Chrono", "Secret of", "Tales of", "Dragon", "Advance",
    "Pocket", "Dr.", "Bust-A-Move", "Puzzle",
]

GAME_NAMES = [
    "Fighter", "Warriors", "Quest", "Adventure", "Racer",
    "Championship", "Deluxe", "Turbo", "Championship Edition",
    "Advance", "Returns", "Odyssey", "Galaxy", "World",
    "Land", "Island", "Strikers", "Tennis", "Golf",
    "Party", "Kart", "Smash", "Stadium", "Tournament",
    "Chronicles", "Legends", "Heroes", "Battle", "Arena",
    "Trigger", "Cross", "Saga", "Fantasy", "Impact",
]

GAME_SUFFIXES = [
    "II", "III", "64", "Advance", "DX", "Special Edition",
    "Remastered", "HD", "Remix", "Plus", "Turbo",
    "Championship", "Directors Cut", "Gold Edition", "2", "3",
    "Revenge", "Attack", "Tournament",
]

# Console categories for organizing
CONSOLES = [
    "NES", "SNES", "N64", "GameCube", "Wii", "WiiU",
    "Genesis", "Dreamcast", "PlayStation", "PS2", "PS3",
    "GameBoy", "GBA", "DS", "3DS", "Arcade", "PC Engine",
    "Neo Geo", "Saturn",
]

# File extensions for ROM files
ROM_EXTENSIONS = [
    ".zip", ".7z", ".rar", ".nes", ".smc", ".sfc", ".z64", ".n64",
    ".iso", ".gcm", ".wbfs", ".gba", ".nds", ".3ds", ".gen", ".md",
    ".bin", ".cue", ".pce", ".ngc",
]

# Add some other common file types to the mix
OTHER_EXTENSIONS = [".txt", ".nfo", ".doc", ".jpg", ".png", ".sfv"]

RUNTIME_UNKNOWN_TAGS = []


def _build_runtime_unknown_tags(count: int = 8) -> List[str]:
    tokens = []
    for _ in range(count):
        letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=5))
        tokens.append(f"Custom-{letters}")
    return tokens


def _all_unknown_tokens() -> List[str]:
    return UNKNOWN_REGION_TAGS + RUNTIME_UNKNOWN_TAGS


def generate_game_name() -> str:
    """Generate a random game title."""
    parts = []

    # 40% chance of prefix
    if random.random() < 0.4:
        parts.append(random.choice(GAME_PREFIXES))

    # Always have a main name, with a 10% chance of a second name part
    parts.append(random.choice(GAME_NAMES))
    if random.random() < 0.1:
        parts.append(random.choice(GAME_NAMES))

    # 30% chance of suffix
    if random.random() < 0.3:
        parts.append(random.choice(GAME_SUFFIXES))

    # 15% chance of adding a year or version number
    if random.random() < 0.15:
        if random.random() < 0.5:
            parts.append(str(random.randint(1990, 2010)))
        else:
            parts.append(f"v{random.randint(1, 3)}.{random.randint(0, 9)}")

    return " ".join(parts)


def generate_filename(include_region: bool = True, collision_target: str = None) -> str:
    """Generate a ROM-like filename.

    Args:
        include_region: Whether to include region tags
        collision_target: If provided, create a name that would collide with this
    """
    if collision_target:
        # Create a collision scenario
        return collision_target

    name = generate_game_name()

    if include_region and random.random() < 0.9:  # 90% have region tags
        # Add 1-4 region tags, mixing in unknown ones for auto-detect coverage
        num_tags = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
        tags = []
        for _ in range(num_tags):
            pool = REGION_TAGS
            if random.random() < 0.25:
                pool = UNKNOWN_REGION_TAGS
            tags.append(random.choice(pool))

        # 15% chance to add a junk tag
        if random.random() < 0.15:
            tags.append(random.choice(JUNK_TAGS))
            random.shuffle(tags)

        for tag in tags:
            # Random spacing variations but enforce parentheses so the parser catches them
            spacing = random.choice(["", " ", "  ", "_", "."])
            name += f"{spacing}({tag}){spacing}"

    # Randomly vary capitalization
    if random.random() < 0.1:
        name = name.upper()
    elif random.random() < 0.1:
        name = name.lower()

    # Add extension (with a chance for non-ROM extensions)
    if random.random() < 0.05:
        ext = random.choice(OTHER_EXTENSIONS)
    else:
        ext = random.choice(ROM_EXTENSIONS)

    return name.replace("  ", " ").strip() + ext


def create_collision_pair(base_name: str, ext: str) -> tuple[str, str]:
    """Create a pair of filenames that would collide after cleaning.

    Returns:
        (file_with_tag, file_without_tag)
    """
    tag = random.choice(REGION_TAGS + _all_unknown_tokens())
    opening, closing = "(", ")"
    separator = random.choice([" ", " _ "])

    file_with_tag = f"{base_name}{separator}{opening}{tag}{closing}{ext}"
    file_without_tag = f"{base_name}{ext}"
    return file_with_tag, file_without_tag


def create_case_collision_pair(base_name: str, ext: str) -> tuple[str, str]:
    """Create files that collide only on case-insensitive filesystems.

    Returns:
        (file_with_tag, existing_lowercase_file)
    """
    tag = random.choice(REGION_TAGS + _all_unknown_tokens())
    opening, closing = "(", ")"
    separator = random.choice([" ", " _ "])

    file_with_tag = f"{base_name}{separator}{opening}{tag}{closing}{ext}"
    # After cleaning, would become base_name + ext
    # We create a lowercase version that already exists
    file_lowercase = f"{base_name.lower()}{ext}"
    return file_with_tag, file_lowercase


def generate_test_data(size: str, output_dir: Path) -> None:
    """Generate test data of specified size.

    Args:
        size: 'small' (150), 'medium' (500), or 'large' (1500)
        output_dir: Directory to create test files in
    """
    # Clean up existing test directory
    if output_dir.exists():
        print(f"\nRemoving existing test directory: {output_dir}")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True)
    print(f"Created test directory: {output_dir}\n")

    # Determine file counts (smaller than original for quick testing)
    size_config = {
        "small": {
            "total_files": 150,
            "num_consoles": 3,
            "num_categories": 2,
            "collisions": 5,
            "case_collisions": 3,
            "random_dirs": 1,
        },
        "medium": {
            "total_files": 500,
            "num_consoles": 5,
            "num_categories": 3,
            "collisions": 10,
            "case_collisions": 5,
            "random_dirs": 2,
        },
        "large": {
            "total_files": 1500,
            "num_consoles": 8,
            "num_categories": 4,
            "collisions": 30,
            "case_collisions": 15,
            "random_dirs": 5,
        },
    }

    config = size_config[size]
    total_files = config["total_files"]
    num_consoles = config["num_consoles"]
    num_categories = config["num_categories"]
    num_collisions = config["collisions"]
    num_case_collisions = config["case_collisions"]
    num_random_dirs = config["random_dirs"]

    global RUNTIME_UNKNOWN_TAGS
    RUNTIME_UNKNOWN_TAGS = _build_runtime_unknown_tags(max(5, num_consoles // 2))

    # Reserve files for collisions
    regular_files = total_files - (num_collisions * 2) - (num_case_collisions * 2)

    consoles = random.sample(CONSOLES, num_consoles)
    categories = ["Action", "RPG", "Sports", "Puzzle", "Platformer", "Racing"][:num_categories]

    files_created = 0
    dirs_created = 0

    # Create directory structure
    for console in consoles:
        console_dir = output_dir / console

        # Some consoles have categorized subdirs, some don't
        if random.random() < 0.6:  # 60% have categories
            for category in categories:
                # Add region tag to some directory names
                if random.random() < 0.3:  # 30% of dirs have region tags
                    tag_pool = REGION_TAGS + _all_unknown_tokens()
                    tag = random.choice(tag_pool)
                    category_name = f"{category} ({tag})"
                else:
                    category_name = category

                cat_dir = console_dir / category_name
                cat_dir.mkdir(parents=True, exist_ok=True)
                dirs_created += 1
        else:
            console_dir.mkdir(parents=True, exist_ok=True)
            dirs_created += 1

    # Create some completely random directory names
    for _ in range(num_random_dirs):
        random_name = "".join(random.choices("abcdefghijklmnopqrstuvwxyz1234567890", k=12))
        random_dir = output_dir / f"RANDOM_{random_name}"
        random_dir.mkdir(parents=True, exist_ok=True)
        dirs_created += 1

    # Get all leaf directories
    all_dirs = [d for d in output_dir.rglob("*") if d.is_dir()]
    if not all_dirs:
        all_dirs = [output_dir]

    print(f"Generating {total_files} files across {dirs_created} directories...")

    # Create regular files
    files_per_dir = regular_files // len(all_dirs) if all_dirs else 0
    remainder = regular_files % len(all_dirs) if all_dirs else 0

    for i, directory in enumerate(all_dirs):
        num_files = files_per_dir + (1 if i < remainder else 0)

        for _ in range(num_files):
            # 10% of files have no region tags (already clean)
            has_region = random.random() > 0.1
            filename = generate_filename(include_region=has_region)
            filepath = directory / filename
            filepath.touch()
            files_created += 1

    # Create collision scenarios (exact collisions)
    print(f"Creating {num_collisions} collision scenarios...")
    for _ in range(num_collisions):
        directory = random.choice(all_dirs)
        base_name = generate_game_name()
        ext = random.choice(ROM_EXTENSIONS)

        file_with_tag, file_without_tag = create_collision_pair(base_name, ext)

        (directory / file_with_tag).touch()
        (directory / file_without_tag).touch()
        files_created += 2

    # Create case-insensitive collision scenarios
    print(f"Creating {num_case_collisions} case-insensitive collision scenarios...")
    for _ in range(num_case_collisions):
        directory = random.choice(all_dirs)
        base_name = generate_game_name()
        ext = random.choice(ROM_EXTENSIONS)

        file_with_tag, file_lowercase = create_case_collision_pair(base_name, ext)

        (directory / file_with_tag).touch()
        (directory / file_lowercase).touch()
        files_created += 2

    # Guarantee each unknown token appears at least once for auto-detect testing
    unknown_dir = output_dir / "UnknownTokens"
    unknown_dir.mkdir(parents=True, exist_ok=True)
    for token in _all_unknown_tokens():
        sample_file = unknown_dir / f"Sample Game ({token}).zip"
        sample_file.touch()
        files_created += 1

    # Add some deeply nested extras
    extras_dir = output_dir / "Extras (USA)" / "Music (En,Fr,De)" / "Soundtrack"
    extras_dir.mkdir(parents=True, exist_ok=True)
    dirs_created += 3

    for i in range(min(20, total_files // 50)):
        filename = f"Track {i+1:02d} (USA).mp3"
        (extras_dir / filename).touch()
        files_created += 1

    print(f"\n" + "="*60)
    print("TEST FILES CREATED SUCCESSFULLY!")
    print("="*60)
    print(f"Location: {output_dir}")
    print(f"Files created: {files_created}")
    print(f"Directories created: {dirs_created}")
    print(f"Collision scenarios: {num_collisions} exact + {num_case_collisions} case-insensitive")
    print(f"\nNext step: Open CleanFilenames.exe and select this folder")
    print(f"           to preview and clean the test files!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate test files for CleanFilenames - try before using on real files!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Generate small test set (default, ~150 files)
  %(prog)s --small      # Generate small test set (~150 files)
  %(prog)s --medium     # Generate medium test set (~500 files)
  %(prog)s --large      # Generate large test set (~1500 files)

The test data includes:
  - ROM-like filenames with various region tags like (USA), (EU), (JP)
  - Nested directory structures (console/category)
  - Directory names with region tags
  - Collision scenarios (files that would conflict after cleaning)
  - Case-insensitive collision scenarios (for Windows)
  - Some files without region tags (already clean)

After generating, use CleanFilenames.exe to preview and clean!
        """
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s", "--small",
        action="store_const",
        const="small",
        dest="size",
        help="Generate small test set (~150 files)"
    )
    group.add_argument(
        "-m", "--medium",
        action="store_const",
        const="medium",
        dest="size",
        help="Generate medium test set (~500 files)"
    )
    group.add_argument(
        "-l", "--large",
        action="store_const",
        const="large",
        dest="size",
        help="Generate large test set (~1500 files)"
    )

    args = parser.parse_args()

    # Default to small if no size specified
    size = args.size or "small"

    # Determine output directory (next to the script/exe)
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        script_dir = Path(sys.executable).parent
    else:
        # Running as Python script
        script_dir = Path(__file__).parent

    test_dir = script_dir / TEST_DIR_NAME

    print("="*60)
    print("CLEANFILENAMES TEST FILE GENERATOR")
    print("="*60)
    print(f"Generating {size} test dataset...\n")

    generate_test_data(size, test_dir)


if __name__ == "__main__":
    main()
