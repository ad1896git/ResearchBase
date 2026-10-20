"""Shared fixtures for the Phase 2 unit transport tests."""

# B20 and B22 reuse the PR2-18 transport fixture. A conftest import (instead of
# pytest_plugins naming a test module) keeps it visible whatever the collection
# order; with pytest_plugins, collecting test_pr2_18_transports.py first made it
# "fixture not found" in the later modules.
from tests.unit.phase2.test_pr2_18_transports import novelty_transports

__all__ = ["novelty_transports"]
