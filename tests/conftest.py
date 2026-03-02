"""
Pytest configuration and shared fixtures.
"""

import os
import sys
from pathlib import Path

import pytest

# Set dummy API key for tests that don't make API calls
# Must be set before any tool module imports (base.py reads at import time)
if not os.environ.get("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = "test-dummy-key"

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _has_real_api_key():
    """Check if a real (non-dummy) API key is available."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    return key and key != "test-dummy-key"


# Shared skip marker for tests that make real API calls
requires_api_key = pytest.mark.skipif(
    not _has_real_api_key(),
    reason="OPENROUTER_API_KEY not set (or dummy key)",
)


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture(scope="session")
def project_root():
    """Return project root path."""
    return Path(__file__).parent.parent
