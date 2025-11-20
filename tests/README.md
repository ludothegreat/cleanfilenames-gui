# Test Suite for cleanfilenames-gui

Comprehensive test suite using pytest for the cleanfilenames utility.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/test_cleanfilenames_core.py

# Run specific test
pytest tests/test_cleanfilenames_core.py::TestNormalizeName::test_removes_usa_tag

# Run with verbose output
pytest -v

# Run and show coverage report
pytest --cov --cov-report=html
```

## Test Coverage

Current coverage: **84%**

- `cleanfilenames_core.py`: 77% coverage
- `config_manager.py`: 92% coverage
- `token_manager.py`: 99% coverage

## Test Structure

- `conftest.py` - Pytest fixtures and shared test utilities
- `test_cleanfilenames_core.py` - Tests for core rename logic (28 tests)
- `test_config_manager.py` - Tests for configuration management (17 tests)
- `test_token_manager.py` - Tests for token management (25 tests)

**Total: 70 tests**

## Test Categories

### Core Logic Tests
- Name normalization
- Candidate collection
- Rename application
- Collision detection
- Auto-resolve conflicts
- Directory rename ordering
- Summary generation

### Configuration Tests
- Regex building
- Preset loading
- Config save/load
- Default creation
- Custom token handling
- Invalid JSON handling

### Token Management Tests
- Token normalization
- Duplicate detection
- Token validation
- Token tracking
- Usage counting
- Suggestion generation
- Sample collection

## Fixtures

- `temp_dir` - Temporary directory for testing
- `sample_files` - Sample files with region tags
- `sample_dirs` - Sample directories with nested structure
- `temp_config` - Temporary config file
- `collision_files` - Files that will collide after cleaning

## Notes

- Tests use temporary directories to avoid affecting the filesystem
- All file operations are isolated and cleaned up automatically
- Collision scenarios are tested with both auto-resolve on and off
- Coverage HTML report is generated in `htmlcov/` directory
