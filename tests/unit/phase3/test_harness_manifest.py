from dataclasses import asdict, replace

import pytest

from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest, ManifestEntry
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes


def manifest():
    return HarnessManifest(
        1,
        "rb@1",
        "runtime@1",
        "model@1",
        "prompt@1",
        "a" * 64,
        "b" * 64,
        "strategy@1",
        "rev@1",
        (),
        (),
        (),
        (),
        (),
        (),
    )


@pytest.mark.parametrize(
    "collection",
    ["skills", "plugins", "adapters", "hooks", "mcp_capabilities", "reference_libraries"],
)
def test_order_and_material(collection):
    base = manifest()
    a = ManifestEntry("alpha", "rev@1", "a" * 64, 1)
    b = ManifestEntry("beta", "rev@2", "b" * 64, 2)
    view = replace(base, **{collection: (b, a)})
    assert getattr(view, collection) == (a, b)
    assert view.digest() != base.digest()
    swapped = replace(view, **{collection: (replace(a, ordinal=2), replace(b, ordinal=1))})
    assert swapped.digest() != view.digest()
    for invalid in ((a, a), (replace(a, ordinal=2),)):
        with pytest.raises(ResearchBaseError):
            replace(base, **{collection: invalid})


@pytest.mark.parametrize(
    "field",
    [
        "researchbase_revision",
        "agent_runtime_revision",
        "model_profile_id",
        "prompt_template_version",
        "strategy_id",
        "strategy_revision",
        "agents_md_sha256",
        "config_sha256",
    ],
)
def test_each_scalar_material(field):
    base = manifest()
    value = "c" * 64 if field.endswith("sha256") else "different@2"
    assert replace(base, **{field: value}).digest() != base.digest()


def test_closed_and_byte_hash_distinction():
    base = manifest()
    assert len(asdict(base)) == 15
    with pytest.raises(TypeError):
        HarnessManifest(**{**asdict(base), "secret": "never serialize"})
    assert (
        str(
            sha256_bytes(
                b" "
                + canonical_json_bytes(
                    {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(base).items()}
                )
            )
        )
        != base.digest()
    )
    for alias in ("latest", "main", "https://test/repo/master"):
        with pytest.raises(ResearchBaseError):
            replace(base, researchbase_revision=alias)
