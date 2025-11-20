"""Tests for token_manager module."""

from pathlib import Path

import pytest

from token_manager import (
    TokenSuggestion,
    TokenTracker,
    find_duplicate_tokens,
    normalize_token,
    validate_tokens,
)


class TestNormalizeToken:
    """Tests for normalize_token function."""

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize_token("  USA  ") == "USA"

    def test_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""
        assert normalize_token("Virtual Console") == "Virtual Console"

    def test_empty_string(self):
        """Test empty string normalization."""
        assert normalize_token("") == ""

    def test_whitespace_only(self):
        """Test whitespace-only string."""
        assert normalize_token("   ") == ""


class TestFindDuplicateTokens:
    """Tests for find_duplicate_tokens function."""

    def test_no_duplicates(self):
        """Test with no duplicate tokens."""
        tokens = ["USA", "EU", "JP"]
        duplicates = find_duplicate_tokens(tokens)
        assert duplicates == {}

    def test_with_duplicates(self):
        """Test with duplicate tokens."""
        tokens = ["USA", "EU", "USA", "JP", "EU", "EU"]
        duplicates = find_duplicate_tokens(tokens)
        assert duplicates == {"USA": 2, "EU": 3}

    def test_case_sensitive(self):
        """Test that duplicates are case-sensitive."""
        tokens = ["USA", "usa", "UsA"]
        duplicates = find_duplicate_tokens(tokens)
        assert duplicates == {}

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized when finding duplicates."""
        tokens = ["USA", " USA ", "  USA  "]
        duplicates = find_duplicate_tokens(tokens)
        assert duplicates == {"USA": 3}

    def test_empty_tokens_ignored(self):
        """Test that empty tokens are ignored."""
        tokens = ["USA", "", "  ", "USA"]
        duplicates = find_duplicate_tokens(tokens)
        assert duplicates == {"USA": 2}


class TestValidateTokens:
    """Tests for validate_tokens function."""

    def test_valid_tokens(self):
        """Test that valid tokens pass validation."""
        tokens = ["USA", "EU", "JP", "En,Fr,De"]
        errors = validate_tokens(tokens)
        assert errors == []

    def test_pipe_character_rejected(self):
        """Test that pipe character is rejected."""
        tokens = ["USA|EU"]
        errors = validate_tokens(tokens)
        assert len(errors) == 2  # Pipe generates two errors (special check + invalid char)
        assert any("|" in error for error in errors)

    def test_invalid_filename_chars_rejected(self):
        """Test that invalid filename characters are rejected."""
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '?', '*']
        for char in invalid_chars:
            tokens = [f"Test{char}Token"]
            errors = validate_tokens(tokens)
            assert len(errors) > 0, f"Should reject '{char}'"

    def test_multiple_errors(self):
        """Test that multiple errors are reported."""
        tokens = ["USA|EU", "Test<Token", "Valid"]
        errors = validate_tokens(tokens)
        assert len(errors) == 3  # USA|EU generates 2 errors, Test<Token generates 1

    def test_line_numbers_in_errors(self):
        """Test that error messages include line numbers."""
        tokens = ["Valid", "USA|EU", "Test<Token"]
        errors = validate_tokens(tokens)
        # Line 2 errors come first (2 errors for USA|EU), then Line 3 error
        assert any("Line 2" in error for error in errors)
        assert any("Line 3" in error for error in errors)


class TestTokenTracker:
    """Tests for TokenTracker class."""

    def test_initialization_with_tokens(self):
        """Test initialization with known tokens."""
        known = ["USA", "EU", "JP"]
        tracker = TokenTracker(known)
        assert tracker.known_tokens == known

    def test_initialization_empty(self):
        """Test initialization without tokens."""
        tracker = TokenTracker()
        assert tracker.known_tokens == []

    def test_observe_known_token(self):
        """Test observing a known token."""
        tracker = TokenTracker(["USA"])
        tracker.observe("Game (USA).zip", Path("/test/Game (USA).zip"))

        usage = tracker.usage()
        usa_usage = next((u for u in usage if u.token == "USA"), None)
        assert usa_usage is not None
        assert usa_usage.count == 1

    def test_observe_unknown_token(self):
        """Test observing an unknown token."""
        tracker = TokenTracker(["USA"])
        tracker.observe("Game (EU).zip", Path("/test/Game (EU).zip"))

        suggestions = tracker.suggestions()
        assert len(suggestions) == 1
        assert suggestions[0].token == "EU"
        assert suggestions[0].count == 1

    def test_suggestions_sorted_by_count(self):
        """Test that suggestions are sorted by count."""
        tracker = TokenTracker(["USA"])
        tracker.observe("Game1 (EU).zip", Path("/test/Game1 (EU).zip"))
        tracker.observe("Game2 (EU).zip", Path("/test/Game2 (EU).zip"))
        tracker.observe("Game3 (JP).zip", Path("/test/Game3 (JP).zip"))

        suggestions = tracker.suggestions()
        assert suggestions[0].token == "EU"
        assert suggestions[0].count == 2
        assert suggestions[1].token == "JP"
        assert suggestions[1].count == 1

    def test_suggestion_samples(self):
        """Test that suggestion samples are collected."""
        tracker = TokenTracker(["USA"])
        path1 = Path("/test/Game1 (EU).zip")
        path2 = Path("/test/Game2 (EU).zip")

        tracker.observe("Game1 (EU).zip", path1)
        tracker.observe("Game2 (EU).zip", path2)

        suggestions = tracker.suggestions()
        assert len(suggestions[0].samples) == 2
        assert str(path1) in suggestions[0].samples
        assert str(path2) in suggestions[0].samples

    def test_suggestion_samples_limited(self):
        """Test that suggestion samples are limited to MAX_SAMPLES."""
        from token_manager import MAX_SAMPLES

        tracker = TokenTracker(["USA"])
        for i in range(MAX_SAMPLES + 5):
            tracker.observe(f"Game{i} (EU).zip", Path(f"/test/Game{i} (EU).zip"))

        suggestions = tracker.suggestions()
        assert len(suggestions[0].samples) == MAX_SAMPLES

    def test_multiple_tags_in_filename(self):
        """Test observing multiple tags in one filename."""
        tracker = TokenTracker(["USA"])
        tracker.observe("Game (EU) (v1.0).zip", Path("/test/Game (EU) (v1.0).zip"))

        suggestions = tracker.suggestions()
        tokens = [s.token for s in suggestions]
        assert "EU" in tokens
        assert "v1.0" in tokens

    def test_duplicate_tokens_detected(self):
        """Test that duplicate tokens in known list are detected."""
        tracker = TokenTracker(["USA", "EU", "USA"])
        duplicates = tracker.duplicate_tokens()
        assert "USA" in duplicates
        assert duplicates["USA"] == 2

    def test_empty_filename_ignored(self):
        """Test that empty filenames are ignored."""
        tracker = TokenTracker(["USA"])
        tracker.observe("", Path("/test/"))

        usage = tracker.usage()
        suggestions = tracker.suggestions()
        assert all(u.count == 0 for u in usage)
        assert len(suggestions) == 0

    def test_no_tags_in_filename(self):
        """Test filename without parentheses."""
        tracker = TokenTracker(["USA"])
        tracker.observe("Normal File.txt", Path("/test/Normal File.txt"))

        usage = tracker.usage()
        suggestions = tracker.suggestions()
        assert all(u.count == 0 for u in usage)
        assert len(suggestions) == 0
