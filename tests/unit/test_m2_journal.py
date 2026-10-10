import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from researchbase.adapters.metadata_journal import MetadataDispatchJournal
from researchbase.foundation.errors import ResearchBaseError


class Provider:
    provider_id = "test"
    provider_version = "1"
    adapter_version = "1"
    endpoint = "https://example.org"

    def __init__(self):
        self.calls = 0

    def observe(self, doi: str | None, title: str, timeout: int = 15):
        self.calls += 1
        return {"outcome": "MATCH"}


def test_completed_concurrent_replay_does_not_redispatch(tmp_path):
    provider = Provider()
    journal = MetadataDispatchJournal(tmp_path, provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(
            pool.map(lambda _: journal.obtain("key", "fingerprint", None, "title", 10), range(2))
        )
    assert values == [{"outcome": "MATCH"}] * 2 and provider.calls == 1
    with pytest.raises(ResearchBaseError):
        journal.obtain("key", "changed", None, "title", 10)


def test_uncertain_intent_is_not_reissued_or_fabricated(tmp_path):
    provider = Provider()
    (tmp_path / "key.json").write_text(json.dumps({"fingerprint": "same"}))
    with pytest.raises(ResearchBaseError):
        MetadataDispatchJournal(tmp_path, provider).obtain("key", "same", None, "title", 10)
    assert provider.calls == 0
