"""Trusted local deployment adapter; no canonical persistence or network listener."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from researchbase.application.phase2_identity import BootstrapAuthority, VerifiedSubject
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def _denied() -> ResearchBaseError:
    return ResearchBaseError(
        ErrorCode.AUTHENTICATION_REQUIRED, "trusted local identity unavailable"
    )


def process_uid() -> int:
    uid = os.getuid()
    if uid == 0 or uid != os.geteuid() or os.getgid() != os.getegid():
        raise _denied()
    return uid


def machine_identity() -> str:
    if platform.system() == "Darwin":
        output = subprocess.check_output(
            ["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], timeout=5
        ).decode("utf-8")
        match = re.search(r'"IOPlatformUUID" = "([0-9A-Fa-f-]+)"', output)
        if match is None:
            raise _denied()
        raw = str(UUID(match.group(1)))
    elif platform.system() == "Linux":
        path = Path("/etc/machine-id")
        info = path.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise _denied()
        raw = path.read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{32}", raw):
            raise _denied()
    else:
        raise _denied()
    return hashlib.sha256(raw.encode()).hexdigest()


def _bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class LocalIdentityAdapter:
    def __init__(self, root: Path) -> None:
        self.root = root.absolute()

    @classmethod
    def initialize(cls, root: Path) -> LocalIdentityAdapter:
        adapter = cls(root)
        uid = process_uid()
        if any((parent / ".git").exists() for parent in adapter.root.parents):
            raise _denied()
        # A dedicated new directory prevents accidental credential replacement.
        try:
            adapter.root.mkdir(mode=0o700, parents=False)
        except OSError as exc:
            raise _denied() from exc
        machine = machine_identity()
        installation = str(uuid4())
        secret = secrets.token_bytes(32)
        adapter._write("bootstrap.secret", secret)
        adapter._write("audit.key", secrets.token_bytes(32))
        adapter._write(
            "installation.json",
            _bytes(
                {
                    "version": 1,
                    "uid": uid,
                    "machine": machine,
                    "installation": installation,
                    "root": str(adapter.root),
                    "deployment_id": f"local-{machine}-{installation}",
                    "credential_id": f"os-{uuid4()}",
                    "enabled": True,
                    "not_before": datetime.now(UTC).isoformat(),
                    "not_after": None,
                    "bootstrap_digest": hashlib.sha256(secret).hexdigest(),
                }
            ),
        )
        return adapter

    def _directory(self) -> None:
        uid = process_uid()
        info = self.root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077:
            raise _denied()
        # Refuse symlinks in the selected path, including its parents.
        if self.root.resolve() != self.root:
            raise _denied()

    def _read(self, name: str) -> bytes:
        self._directory()
        fd = os.open(self.root / name, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != process_uid()
                or info.st_mode & 0o077
                or info.st_nlink != 1
            ):
                raise _denied()
            with os.fdopen(fd, "rb", closefd=False) as stream:
                value = stream.read(65537)
                if len(value) > 65536:
                    raise _denied()
                return value
        finally:
            os.close(fd)

    def _write(self, name: str, content: bytes) -> None:
        self._directory()
        fd = os.open(self.root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

    def _policy(self) -> dict:
        try:
            policy = json.loads(self._read("installation.json"))
            machine = machine_identity()
            installation = str(UUID(policy["installation"]))
            if (
                policy["version"] != 1
                or policy["uid"] != process_uid()
                or isinstance(policy["uid"], bool)
                or policy["machine"] != machine
                or policy["root"] != str(self.root)
                or policy["deployment_id"] != f"local-{machine}-{installation}"
                or policy["enabled"] is not True
            ):
                raise _denied()
            return policy
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            raise _denied() from exc

    def subject(self) -> VerifiedSubject:
        policy = self._policy()
        subject = VerifiedSubject(
            policy["deployment_id"], "OS_UID", str(process_uid()), policy["credential_id"]
        )
        if not self.is_valid(subject, datetime.now(UTC)):
            raise _denied()
        return subject

    def is_valid(self, principal: VerifiedPrincipal | VerifiedSubject, at: datetime) -> bool:
        try:
            policy = self._policy()
            start = datetime.fromisoformat(policy["not_before"])
            end = datetime.fromisoformat(policy["not_after"]) if policy["not_after"] else None
            return (
                principal.deployment_id == policy["deployment_id"]
                and principal.subject_kind == "OS_UID"
                and principal.subject_value == str(process_uid())
                and principal.credential_id == policy["credential_id"]
                and start <= at
                and (end is None or at < end)
                and (not isinstance(principal, VerifiedPrincipal) or principal.verified_at <= at)
            )
        except Exception:
            return False

    def is_allowlisted(self, principal: VerifiedPrincipal) -> bool:
        return self.is_valid(principal, datetime.now(UTC))

    def bootstrap_authority(self) -> BootstrapAuthority:
        subject = self.subject()
        policy = self._policy()
        secret = self._read("bootstrap.secret")
        if not hmac.compare_digest(hashlib.sha256(secret).hexdigest(), policy["bootstrap_digest"]):
            raise _denied()
        principal = VerifiedPrincipal(
            uuid4(),
            subject.deployment_id,
            subject.subject_kind,
            subject.subject_value,
            subject.credential_id,
            datetime.now(UTC),
        )
        material = {
            "type": "LOCAL_BOOTSTRAP_PROOF",
            "deployment_id": subject.deployment_id,
            "uid": process_uid(),
            "credential_id": subject.credential_id,
            "operator_id": str(principal.actor_id),
            "verified_at": principal.verified_at.isoformat(),
            "nonce": secrets.token_hex(32),
        }
        signature = hmac.new(self._read("audit.key"), _bytes(material), hashlib.sha256).hexdigest()
        record = _bytes({"material": material, "hmac_sha256": signature})
        digest = hashlib.sha256(record).hexdigest()
        self._write(f"proof-{digest}.json", record)
        return BootstrapAuthority(
            subject.deployment_id,
            principal,
            process_uid(),
            subject.credential_id,
            policy["bootstrap_digest"],
            digest,
            str(self.root / f"proof-{digest}.json"),
        )

    def verify(self, authority: BootstrapAuthority) -> bool:
        try:
            policy = self._policy()
            raw = self._read(f"proof-{authority.proof_sha256}.json")
            record = json.loads(raw)
            material = record["material"]
            expected = hmac.new(
                self._read("audit.key"), _bytes(material), hashlib.sha256
            ).hexdigest()
            return (
                hmac.compare_digest(record["hmac_sha256"], expected)
                and hashlib.sha256(raw).hexdigest() == authority.proof_sha256
                and authority.proof_record_ref
                == str(self.root / f"proof-{authority.proof_sha256}.json")
                and material["operator_id"] == str(authority.operator.actor_id)
                and material["verified_at"] == authority.operator.verified_at.isoformat()
                and material["deployment_id"] == authority.deployment_id
                and material["uid"] == authority.verified_os_uid == process_uid()
                and material["credential_id"]
                == authority.subject_credential_id
                == authority.operator.credential_id
                and authority.secret_digest_id == policy["bootstrap_digest"]
                and hmac.compare_digest(
                    hashlib.sha256(self._read("bootstrap.secret")).hexdigest(),
                    policy["bootstrap_digest"],
                )
                and self.is_valid(authority.operator, datetime.now(UTC))
            )
        except Exception:
            return False

    def invalidate(self, authority: BootstrapAuthority) -> None:
        # DB bootstrap is permanently closed even if a crash leaves this file behind.
        (self.root / "bootstrap.secret").unlink(missing_ok=True)

    def issue(self) -> bytes:
        return secrets.token_bytes(32)
