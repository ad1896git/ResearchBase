"""Literal JSON vectors independent of the production material constructor."""

import hashlib
import json
from uuid import UUID

import pytest

from researchbase.domain.novelty import HashRef, PriorArtKind, prior_art_material
from researchbase.foundation.canonical_json import canonical_json_bytes

# This authored fixture is intentionally independent of builder/key assembly.
V1 = '{"assessed_by":{"id":"00000000-0000-0000-0000-000000000005","type":"ActorIdentity"},"claim_version":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000001","type":"ClaimVersion"},"literature_evidence":[{"content_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","id":"00000000-0000-0000-0000-000000000003","type":"LiteratureEvidence"},{"content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","id":"00000000-0000-0000-0000-000000000004","type":"LiteratureEvidence"}],"material_version":1,"rationale":"é","relation":"RELATED","source_version":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000002","type":"SourceVersion"},"type":"PriorArtRelation"}'  # noqa: E501
V2 = '{"assessed_by":{"id":"00000000-0000-0000-0000-000000000005","type":"ActorIdentity"},"claim_version":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000001","type":"ClaimVersion"},"literature_evidence":[{"content_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","id":"00000000-0000-0000-0000-000000000003","type":"LiteratureEvidence"},{"content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","id":"00000000-0000-0000-0000-000000000004","type":"LiteratureEvidence"}],"material_version":2,"rationale":"é","relation":"RELATED","source_version":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000002","type":"SourceVersion"},"supersedes_prior_art_relation":{"content_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","id":"00000000-0000-0000-0000-000000000006","type":"PriorArtRelation"},"type":"PriorArtRelation"}'  # noqa: E501


def material(version=1, *, predecessor=None, actor=None, rationale="e\u0301", reverse=False):
    evidence = (
        HashRef("LiteratureEvidence", UUID(int=3), "c" * 64),
        HashRef("LiteratureEvidence", UUID(int=4), "d" * 64),
    )
    return prior_art_material(
        HashRef("ClaimVersion", UUID(int=1), "a" * 64),
        HashRef("SourceVersion", UUID(int=2), "b" * 64),
        PriorArtKind.RELATED,
        rationale,
        evidence[::-1] if reverse else evidence,
        UUID(int=5) if actor is None else actor,
        predecessor,
        material_version=version,
    )


@pytest.mark.parametrize("version,literal", [(1, V1), (2, V2)])
def test_literal_vectors(version, literal):
    previous = HashRef("PriorArtRelation", UUID(int=6), "e" * 64) if version == 2 else None
    expected = literal.encode("utf8")
    assert canonical_json_bytes(material(version, predecessor=previous)) == expected
    assert canonical_json_bytes(material(version, predecessor=previous, reverse=True)) == expected
    assert hashlib.sha256(expected).hexdigest() == DIGESTS[version]
    assert json.loads(literal)["material_version"] == version


@pytest.mark.parametrize("version", [0, 3, True, "2", None])
def test_unknown_version(version):
    with pytest.raises(ValueError):
        material(version)


def test_correction_binding():
    previous = HashRef("PriorArtRelation", UUID(int=6), "e" * 64)
    base = material(2, predecessor=previous)
    for changed in [
        material(2, predecessor=HashRef("PriorArtRelation", UUID(int=7), "e" * 64)),
        material(2, predecessor=HashRef("PriorArtRelation", UUID(int=6), "f" * 64)),
        material(2, predecessor=previous, actor=UUID(int=9)),
        material(2, predecessor=previous, rationale="changed"),
    ]:
        assert changed != base
    with pytest.raises(ValueError):
        material(1, predecessor=previous)
    with pytest.raises(ValueError):
        material(2)


DIGESTS = {
    1: "b2f77007fd09564c11123ac6280459b6a06df26a966595ee68deb249f2890349",
    2: "39fa96d616af25dbeeeab8d77ff141a0ac15befe96202b8610916a6cfe9e8369",
}
