"""Test to verify CI environment is properly configured."""

import os

import pytest


class TestCIEnvironment:
    """Test that CI environment has necessary dependencies."""

    @staticmethod
    def test_rmapi_available():
        """Test that rmapi is available in PATH or as env variable."""
        rmapi_path = os.environ.get("RMAPI_PATH", "rmapi")
        # Don't fail in CI if rmapi not available, just skip
        if not os.path.exists(rmapi_path) and os.system(f"which {rmapi_path}") != 0:
            pytest.skip("rmapi not available in CI environment")

    @staticmethod
    def test_api_keys_configured():
        """Test that required API keys are configured."""
        # These tests should skip if keys not available, not fail
        if not os.environ.get("LIMITLESS_API_KEY"):
            pytest.skip("LIMITLESS_API_KEY not configured")

        if not os.environ.get("MYSCRIPT_APP_KEY"):
            pytest.skip("MYSCRIPT_APP_KEY not configured")

        if not os.environ.get("MYSCRIPT_API_KEY"):
            pytest.skip("MYSCRIPT_API_KEY not configured")

    @staticmethod
    def test_neo4j_available():
        """Test that Neo4j is available if needed."""
        neo4j_url = os.environ.get("NEO4J_URL", "bolt://localhost:7687")
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(neo4j_url)
            driver.close()
        except Exception:
            pytest.skip("Neo4j not available in CI environment")
