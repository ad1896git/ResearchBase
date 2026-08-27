import pytest

from researchbase.foundation.hashing import ContentHash, sha256_bytes, sha256_canonical_json


def test_known_sha256_vector() -> None:
    assert (
        sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_same_bytes_have_same_hash_and_different_bytes_differ() -> None:
    assert sha256_bytes(b"same") == sha256_bytes(b"same")
    assert sha256_bytes(b"same") != sha256_bytes(b"different")


def test_canonical_json_key_order_has_same_hash() -> None:
    assert sha256_canonical_json({"a": 1, "b": 2}) == sha256_canonical_json({"b": 2, "a": 1})


def test_content_hash_validates_and_normalizes_hex() -> None:
    value = ContentHash("AB" * 32)

    assert value == "ab" * 32


@pytest.mark.parametrize(
    "value",
    ["", "a" * 63, "a" * 65, "g" * 64, " " * 64, "a" * 63 + "!"],
)
def test_content_hash_rejects_malformed_digest_text(value: str) -> None:
    with pytest.raises(ValueError, match="64-character SHA-256"):
        ContentHash(value)


def test_content_hash_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="must be text"):
        ContentHash(123)  # type: ignore[arg-type]
