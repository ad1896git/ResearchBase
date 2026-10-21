"""Closed manifest values; no execution binding or credential material."""

from dataclasses import asdict, dataclass

from researchbase.agent_runtime.domain.agent_version import digest_value, pinned
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    id: str
    revision: str
    content_sha256: str
    ordinal: int

    def __post_init__(self):
        for name in ("id", "revision"):
            object.__setattr__(self, name, pinned(getattr(self, name)))
        digest_value(self.content_sha256)
        if type(self.ordinal) is not int or self.ordinal < 1:
            invalid("positive ordinal required")


@dataclass(frozen=True, slots=True)
class HarnessManifest:
    schema_version: int
    researchbase_revision: str
    agent_runtime_revision: str
    model_profile_id: str
    prompt_template_version: str
    agents_md_sha256: str
    config_sha256: str
    strategy_id: str
    strategy_revision: str
    skills: tuple[ManifestEntry, ...]
    plugins: tuple[ManifestEntry, ...]
    adapters: tuple[ManifestEntry, ...]
    hooks: tuple[ManifestEntry, ...]
    mcp_capabilities: tuple[ManifestEntry, ...]
    reference_libraries: tuple[ManifestEntry, ...]

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            invalid("manifest schema version must be 1")
        for name in (
            "researchbase_revision",
            "agent_runtime_revision",
            "model_profile_id",
            "prompt_template_version",
            "strategy_id",
            "strategy_revision",
        ):
            object.__setattr__(self, name, pinned(getattr(self, name)))
        for name in ("agents_md_sha256", "config_sha256"):
            digest_value(getattr(self, name))
        for name in (
            "skills",
            "plugins",
            "adapters",
            "hooks",
            "mcp_capabilities",
            "reference_libraries",
        ):
            values = getattr(self, name)
            if type(values) is not tuple or any(type(v) is not ManifestEntry for v in values):
                invalid("closed manifest entries required")
            if len({v.id for v in values}) != len(values) or sorted(
                v.ordinal for v in values
            ) != list(range(1, len(values) + 1)):
                invalid("duplicate IDs or noncontiguous ordinals")
            object.__setattr__(self, name, tuple(sorted(values, key=lambda v: v.ordinal)))

    def digest(self):
        return str(
            sha256_canonical_json(
                {
                    k: [asdict(v) for v in value] if isinstance(value, tuple) else value
                    for k, value in ((f, getattr(self, f)) for f in self.__dataclass_fields__)
                }
            )
        )
