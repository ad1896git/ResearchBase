from researchbase.adapters.crossref import CrossrefVerifier
from researchbase.adapters.literature_http import HttpObservation


def verifier(message, status=200):
    return CrossrefVerifier(get=lambda *args: HttpObservation(status, {}, {"message": message}))


def test_match_normalizes_doi_and_title_and_retains_only_bibliography():
    value = verifier(
        {
            "DOI": "10.1234/ABC",
            "title": ["CRISPR–Cas9"],
            "author": [{"given": "A", "family": "Smith"}],
            "abstract": "must not retain",
        }
    ).observe("https://doi.org/10.1234/abc", "CRISPR Cas9")
    assert value["outcome"] == "MATCH"
    assert value["metadata"]["doi"] == "10.1234/abc"
    assert "abstract" not in value["evidence"]["response"]
    assert value["metadata"]["authors"][0]["name"] == "A Smith"


def test_conflicting_title_is_not_overwritten():
    value = verifier({"DOI": "10.1234/abc", "title": ["Unrelated study"]}).observe(
        "10.1234/abc", "CRISPR Cas9"
    )
    assert value["outcome"] == "CONFLICT"
    assert value["evidence"]["response"]["title"] == ["Unrelated study"]


def test_missing_title_is_ambiguous():
    assert (
        verifier({"DOI": "10.1234/abc"}).observe("10.1234/abc", "Title")["outcome"] == "AMBIGUOUS"
    )


def test_missing_doi_is_unresolved_without_network():
    def no_call(*args):
        raise AssertionError("missing DOI dispatched")

    value = CrossrefVerifier(get=no_call).observe(None, "Title")
    assert value["outcome"] == "UNRESOLVED" and value["evidence"] is not None


def test_timeout_is_responseless_unavailable():
    def timeout(*args):
        raise TimeoutError

    value = CrossrefVerifier(get=timeout).observe("10.1234/abc", "Title")
    assert value["outcome"] == "UNAVAILABLE"
    assert value["evidence"] is None and value["http_status"] is None
    assert value["failure_code"] == "TRANSPORT_TIMEOUT"


def test_received_404_is_retained_not_responseless():
    value = verifier({}, 404).observe("10.1234/abc", "Title")
    assert value["outcome"] == "UNRESOLVED" and value["evidence"] is not None
    assert value["http_status"] == 404


def test_malformed_response_is_ambiguous_with_evidence():
    value = CrossrefVerifier(get=lambda *args: HttpObservation(200, {}, [])).observe(
        "10.1234/abc", "Title"
    )
    assert value["outcome"] == "AMBIGUOUS" and value["evidence"] is not None


def test_partial_http_timeout_retains_received_response(monkeypatch):
    from researchbase.adapters import literature_http

    class Response:
        code = 200
        headers = {}
        count = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            self.count += 1
            if self.count == 1:
                return b'{"message":'
            raise TimeoutError

    class Opener:
        def open(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(literature_http, "build_opener", lambda *args: Opener())
    value = CrossrefVerifier().observe("10.1234/abc", "Title")
    assert value["outcome"] == "AMBIGUOUS"
    assert value["http_status"] == 200 and value["evidence"] is not None
    assert value["evidence"]["response_failure"] == "INCOMPLETE_BODY"
    assert value["evidence"]["response_sha256"] is not None
