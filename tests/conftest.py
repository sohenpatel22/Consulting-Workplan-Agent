import pytest

import workplan_agent.config as config_module


@pytest.fixture(autouse=True)
def unlimited_revisions_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep API tests independent of local .env revision limits."""
    monkeypatch.setenv("MAX_REVISIONS", "0")
    config_module._settings = None
    yield
    config_module._settings = None
