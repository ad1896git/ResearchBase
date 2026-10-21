#!/usr/bin/env python3
"""Read-only HG1 distinct-UID host check; run after interactive sudo -v."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from datetime import UTC, datetime

ROOT = pathlib.Path("/Users/onephone/ResearchBaseData")
WORKTREE = pathlib.Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "migration-evidence" / "HG1-HOST"
PYTHON = pathlib.Path(
    "/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/"
    "m1-identity-onboarding/.venv/bin/python"
)
PG_DUMP = "/opt/homebrew/opt/postgresql@18/bin/pg_dump"
PSQL = "/opt/homebrew/opt/postgresql@18/bin/psql"
TAGS = ("final", "live", "live2", "live3")
CHILD = r"""
import json, os, socket, struct, sys
path, expected = sys.argv[1:]
print(json.dumps({"kind":"identity","uid":os.getuid(),"euid":os.geteuid(),
                  "expected_uid":int(expected),"match":os.geteuid()==int(expected)}), flush=True)
cases = [
    ("whoami", {"v":1,"op":"whoami"}),
    ("owner_actor_claim", {"v":1,"op":"whoami","actor_id":"forged"}),
    ("owner_role_claim", {"v":1,"op":"whoami","role":"OWNER"}),
    (
        "project_read",
        {"v": 1, "op": "project.get", "project_id": "0ecdbd9a-b426-4814-b245-7c382dfae708"},
    ),
    ("reviewer_claim", {"v":2,"op":"enrollment.challenge","principal":"REVIEWER"}),
    (
        "review_write",
        {
            "v": 2,
            "op": "evidence.review",
            "project_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
            "evidence_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
            "basis": "host-denial-only",
            "request_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
        },
    ),
    (
        "support_write",
        {
            "v": 2,
            "op": "support.create",
            "project_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
            "target_type": "ClaimVersion",
            "target_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
            "evidence_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
            "qualification": "host-denial-only",
            "request_id": "0ecdbd9a-b426-4814-b245-7c382dfae708",
        },
    ),
]
for name, value in cases:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(path)
            body=json.dumps(value,separators=(",",":")).encode()
            conn.sendall(struct.pack("!I",len(body))+body)
            head=conn.recv(4)
            if len(head)!=4: raise RuntimeError("missing response length")
            length=struct.unpack("!I",head)[0]
            if not 1<=length<=4096: raise RuntimeError("invalid response length")
            data=b""
            while len(data)<length:
                part=conn.recv(length-len(data))
                if not part: raise RuntimeError("short response")
                data+=part
            print(json.dumps({"kind":"runner","case":name,"transport":"connected",
                              "response":json.loads(data)}),flush=True)
    except OSError as exc:
        print(json.dumps({"kind":"runner","case":name,"transport":"socket_error",
                          "errno":exc.errno,"error":str(exc)}),flush=True)
    except Exception as exc:
        print(json.dumps({"kind":"runner","case":name,"transport":"protocol_error",
                          "error":str(exc)}),flush=True)
"""


def now() -> str:
    return datetime.now(UTC).isoformat()


class Transcript:
    def __init__(self) -> None:
        if EVIDENCE.is_symlink():
            raise RuntimeError("evidence directory is a symlink")
        EVIDENCE.mkdir(mode=0o700, exist_ok=True)
        if EVIDENCE.stat().st_uid != os.geteuid() or EVIDENCE.stat().st_mode & 0o077:
            raise RuntimeError("evidence directory is not private and owner-controlled")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.path = EVIDENCE / f"hg1-host-{stamp}-{os.getpid()}.jsonl"
        self.file = open(self.path, "x", encoding="utf-8", opener=lambda p, f: os.open(p, f, 0o600))

    def record(self, event: str, **fields: object) -> None:
        line = json.dumps({"at": now(), "event": event, **fields}, sort_keys=True)
        self.file.write(line + "\n")
        self.file.flush()
        print(line, flush=True)

    def close(self) -> str:
        self.file.close()
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        digest_path = pathlib.Path(str(self.path) + ".sha256")
        with open(
            digest_path, "x", encoding="ascii", opener=lambda p, f: os.open(p, f, 0o600)
        ) as out:
            out.write(f"{digest}  {self.path.name}\n")
        print(f"TRANSCRIPT={self.path}\nSHA256={digest}\nDIGEST_FILE={digest_path}", flush=True)
        return digest


def run(
    log: Transcript, label: str, argv: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=30)
    log.record(
        "command",
        label=label,
        argv=argv,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    return result


def dump_hash(log: Transcript, tag: str, stage: str) -> str:
    env = {
        **os.environ,
        "PGHOST": "/private/tmp",
        "PGPORT": "55440",
        "PGUSER": "onephone",
        "PGCONNECT_TIMEOUT": "5",
        "PGPASSWORD": "",
    }
    argv = [PG_DUMP, "--data-only", "--no-owner", "--no-privileges", f"researchbase_m2_{tag}"]
    result = subprocess.run(argv, capture_output=True, env=env, timeout=30)
    # PostgreSQL 18 emits a random psql \restrict token in every dump. Exclude
    # only those two transport-control lines from the content comparison.
    canonical = b"".join(
        line
        for line in result.stdout.splitlines(keepends=True)
        if not line.startswith((b"\\restrict ", b"\\unrestrict "))
    )
    digest = hashlib.sha256(canonical).hexdigest()
    log.record(
        "db_snapshot",
        stage=stage,
        database=f"researchbase_m2_{tag}",
        command=argv,
        exit_code=result.returncode,
        sha256=digest,
        byte_count=len(result.stdout),
        canonical_byte_count=len(canonical),
        stderr=result.stderr.decode(errors="replace"),
    )
    if result.returncode:
        raise RuntimeError(f"database snapshot failed: {tag} {stage}")
    return digest


def main() -> int:
    log = Transcript()
    server: subprocess.Popen[str] | None = None
    failures: list[str] = []
    try:
        runner_digest = hashlib.sha256(
            (WORKTREE / "src/researchbase/runner.py").read_bytes()
        ).hexdigest()
        log.record(
            "baseline",
            implementation_sha="c097dacf2826f18e5ba9e9736500d1f8121058e4",
            evidence_head="3ddacd3f372b898f8b776949fba39fc87dd619fa",
            worktree=str(WORKTREE),
            host_uid=os.geteuid(),
            platform=sys.platform,
            runner_sha256=runner_digest,
        )
        if runner_digest != "ae0a3a03ae07e683f8770001cb5311580a5311d94ba0582ebed546d05c7e52df":
            raise RuntimeError("Runner implementation digest differs from accepted HG1-02 evidence")
        if sys.platform != "darwin" or os.geteuid() != 502:
            raise RuntimeError("requires macOS trusted onephone UID 502")
        git = run(log, "git_head", ["git", "-C", str(WORKTREE), "rev-parse", "HEAD"])
        if git.returncode:
            raise RuntimeError("integrated HEAD unavailable")
        ancestor = run(
            log,
            "accepted_evidence_ancestor",
            [
                "git",
                "-C",
                str(WORKTREE),
                "merge-base",
                "--is-ancestor",
                "3ddacd3f372b898f8b776949fba39fc87dd619fa",
                git.stdout.strip(),
            ],
        )
        if ancestor.returncode:
            raise RuntimeError("accepted HG1-02 evidence is not in tested HEAD")
        identity = run(log, "nobody_uid", ["/usr/bin/id", "-u", "nobody"])
        if identity.returncode or not identity.stdout.strip().isdigit():
            raise RuntimeError("nobody identity unavailable")
        nobody_uid = int(identity.stdout.strip())
        if nobody_uid in (0, os.geteuid()):
            raise RuntimeError("nobody is not distinct from trusted owner")
        sudo = run(
            log,
            "sudo_nobody_precheck",
            ["/usr/bin/sudo", "-n", "-u", "nobody", "/usr/bin/id", "-un"],
        )
        if sudo.returncode or sudo.stdout.strip() != "nobody":
            raise RuntimeError(
                "interactive sudo authorization required: run sudo -v in host Terminal"
            )
        baseline = {tag: dump_hash(log, tag, "before") for tag in TAGS}
        readback = json.loads(
            (ROOT / "migration-evidence/postcutover-cli-verification.json").read_text()
        )
        tag = "final"
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(WORKTREE / "src"),
            "DATABASE_URL": "postgresql+psycopg://onephone@/researchbase_m2_final?host=%2Fprivate%2Ftmp&port=55440",
            "RESEARCHBASE_LOCAL_ROOT": str(ROOT / "rb-m2-final-installation"),
            "ARTIFACT_STORE_ROOT": str(ROOT / "rb-m2-final-artifacts"),
            "PGOPTIONS": "-c TimeZone=UTC",
        }
        server = subprocess.Popen(
            [
                str(PYTHON),
                "-m",
                "researchbase.runner",
                "--max-requests",
                "4",
                "--lifetime-seconds",
                "60",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert server.stdout is not None
        path = pathlib.Path(server.stdout.readline().strip())
        if (
            not path.is_socket()
            or path.parent.stat().st_mode & 0o777 != 0o711
            or path.stat().st_mode & 0o777 != 0o666
        ):
            raise RuntimeError("Runner socket path or modes unexpected")
        log.record(
            "runner_started",
            pid=server.pid,
            socket=str(path),
            parent_mode=oct(path.parent.stat().st_mode & 0o777),
            socket_mode=oct(path.stat().st_mode & 0o777),
        )
        sys.path.insert(0, str(WORKTREE / "src"))
        from researchbase.runner import request

        owner_cases = [
            ("whoami", {"v": 1, "op": "whoami"}),
            (
                "project.get",
                {"v": 1, "op": "project.get", "project_id": readback[tag]["projects_read"][0]},
            ),
        ]
        for label, value in owner_cases:
            response = request(path, value)
            log.record("owner_request", label=label, response=response)
            if response.get("ok") is not True:
                failures.append(f"trusted owner {label} failed")
        nobody = run(
            log,
            "nobody_runner_cases",
            [
                "/usr/bin/sudo",
                "-n",
                "-u",
                "nobody",
                "/usr/bin/python3",
                "-c",
                CHILD,
                str(path),
                str(nobody_uid),
            ],
        )
        if nobody.returncode:
            failures.append("nobody client did not execute")
        else:
            rows = [json.loads(line) for line in nobody.stdout.splitlines()]
            if len(rows) != 8 or rows[0].get("kind") != "identity" or not rows[0].get("match"):
                failures.append("genuine nobody UID evidence missing")
            for row in rows[1:]:
                if row.get("transport") != "connected" or row.get("response") != {
                    "v": 1,
                    "ok": False,
                    "error": "DENIED",
                }:
                    failures.append(f"Runner denial unverified: {row.get('case')}: {row}")
        dirs = [ROOT / "rb-m2-pg", ROOT / "migration-evidence"]
        files = [ROOT / "migration-evidence/historical-proof-manifest.json"]
        for suffix in TAGS:
            dirs.extend((ROOT / f"rb-m2-{suffix}-installation", ROOT / f"rb-m2-{suffix}-artifacts"))
            files.append(ROOT / f"rb-m2-{suffix}-installation/audit.key")
        for item in dirs:
            result = run(
                log,
                f"nobody_write_denial:{item}",
                ["/usr/bin/sudo", "-n", "-u", "nobody", "/bin/test", "-w", str(item)],
            )
            if not item.is_dir() or result.returncode != 1 or result.stderr:
                failures.append(f"protected directory access unverified: {item}")
        for item in files:
            result = run(
                log,
                f"nobody_read_denial:{item}",
                ["/usr/bin/sudo", "-n", "-u", "nobody", "/bin/test", "-r", str(item)],
            )
            if not item.is_file() or result.returncode != 1 or result.stderr:
                failures.append(f"protected audit access unverified: {item}")
        for host in ("/private/tmp", "127.0.0.1"):
            pg_env = {
                "PGHOST": host,
                "PGPORT": "55440",
                "PGUSER": "onephone",
                "PGDATABASE": "postgres",
                "PGCONNECT_TIMEOUT": "3",
            }
            result = run(
                log,
                f"nobody_pg_denial:{host}",
                [
                    "/usr/bin/sudo",
                    "-n",
                    "-u",
                    "nobody",
                    "/usr/bin/env",
                    "-i",
                    *(f"{k}={v}" for k, v in pg_env.items()),
                    PSQL,
                    "-w",
                    "-XAt",
                    "-c",
                    "SELECT 1",
                ],
            )
            if result.returncode == 0 or not any(
                x in result.stderr
                for x in (
                    "Peer authentication failed",
                    "pg_hba.conf rejects connection",
                    "no pg_hba.conf entry",
                )
            ):
                failures.append(f"direct PostgreSQL denial unverified: {host}")
    except Exception as exc:
        failures.append(f"execution blocked: {type(exc).__name__}: {exc}")
    finally:
        if server is not None:
            if server.poll() is None:
                server.terminate()
            try:
                out, err = server.communicate(timeout=5)
                log.record("runner_exit", exit_code=server.returncode, stdout=out, stderr=err)
            except subprocess.TimeoutExpired:
                server.kill()
                out, err = server.communicate()
                log.record("runner_killed", exit_code=server.returncode, stdout=out, stderr=err)
                failures.append("Runner failed to stop")
        if "baseline" in locals():
            try:
                after = {tag: dump_hash(log, tag, "after") for tag in TAGS}
                for tag in TAGS:
                    if baseline[tag] != after[tag]:
                        failures.append(f"M2 database changed during host test: {tag}")
            except Exception as exc:
                failures.append(f"post-test database comparison failed: {exc}")
        log.record(
            "final",
            verdict="PASS" if not failures else "BLOCKED",
            failures=failures,
            original_test_exit_code=0 if not failures else 1,
        )
        log.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
