"""Actual non-root OS principal and real CC-BY source; human verification NOT RUN."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

SOURCE = Path("tests/fixtures/m3/PMC3812051.xml")
QUOTE = "The standard solution to track evolution of code is to use a version control system"


def test_real_source_cli_restart_and_no_self_approval(phase2_database_url, tmp_path, monkeypatch):
    assert os.getuid() != 0
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    monkeypatch.setenv("RESEARCHBASE_LOCAL_ROOT", str(tmp_path / "installation"))
    monkeypatch.setenv("ARTIFACT_STORE_ROOT", str(tmp_path / "cas"))
    transcript = []

    def cli(*args, ok=True):
        process = subprocess.run(
            [sys.executable, "-m", "researchbase.cli.main", *args],
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=40,
        )
        output = process.stdout if process.returncode == 0 else process.stderr
        lines = [line for line in output.splitlines() if line.startswith("{")]
        assert lines, (process.stdout, process.stderr)
        value = json.loads(lines[-1])
        transcript.append({"command": list(args), "exit": process.returncode, "output": value})
        assert (process.returncode == 0) == ok, (process.stdout, process.stderr)
        return value

    cli("local", "init", "--json")
    boot = cli(
        "local",
        "bootstrap",
        "--display-name",
        "M3 local demonstrator",
        "--project-name",
        "M3 real source demonstration",
        "--json",
    )
    project = boot["project_id"]
    actor = cli("local", "whoami", "--json")
    source = cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "source",
        "create",
        "--project-id",
        project,
        "--kind",
        "PAPER",
        "--title",
        "Ten Simple Rules for Reproducible Computational Research",
        "--initial-identifier-type",
        "DOI",
        "--initial-identifier-value",
        "10.1371/journal.pcbi.1003285",
        "--json",
    )
    document = cli(
        "--request-id",
        str(uuid4()),
        "literature-evidence",
        "import-document",
        "--project-id",
        project,
        "--path",
        str(SOURCE.absolute()),
        "--media-type",
        "application/jats+xml",
        "--rights-basis",
        (
            "CC BY 4.0; Sandve et al. 2013; doi:10.1371/journal.pcbi.1003285; "
            "original Europe PMC JATS; local project retention"
        ),
        "--json",
    )
    assert document["content_hash"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    material = {
        "version_kind": "PUBLISHED",
        "title": "Ten Simple Rules for Reproducible Computational Research",
        "authors": [],
        "fulltext_artifact": {
            "id": document["artifact_version_id"],
            "content_hash": document["content_hash"],
        },
    }
    version = cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "version",
        "create",
        "--project-id",
        project,
        "--source-id",
        source["source_id"],
        "--material-json",
        json.dumps(material),
        "--json",
    )
    source_version = version["source_version_id"]
    cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "version",
        "freeze",
        "--project-id",
        project,
        "--source-version-id",
        source_version,
        "--json",
    )
    inspected = cli(
        "literature-evidence",
        "inspect",
        "--project-id",
        project,
        "--source-version-id",
        source_version,
        "--paragraph",
        "16",
        "--json",
    )
    assert inspected["text"].startswith(QUOTE)
    evidence = cli(
        "--request-id",
        str(uuid4()),
        "literature-evidence",
        "create",
        "--project-id",
        project,
        "--source-version-id",
        source_version,
        "--artifact-version-id",
        document["artifact_version_id"],
        "--quotation",
        QUOTE,
        "--paragraph",
        "16",
        "--start",
        "0",
        "--end",
        str(len(QUOTE)),
        "--json",
    )
    hypothesis = cli(
        "local",
        "hypothesis-create",
        "--project-id",
        project,
        "--statement",
        "Computational results may depend on the exact version of code used.",
        "--rationale",
        "Demonstration hypothesis only; methodological context is not verified support.",
        "--json",
    )
    frozen = cli(
        "local",
        "hypothesis-freeze",
        "--hypothesis-id",
        hypothesis["id"],
        "--version-id",
        hypothesis["current_version_id"],
        "--json",
    )
    edge = {
        "evidence_id": evidence["id"],
        "relation_type": "CONTEXTUALIZES",
        "qualification": (
            "Methodological context only; no scientific SUPPORTS assertion "
            "or independent-human acceptance."
        ),
    }
    snapshot = cli(
        "--request-id",
        str(uuid4()),
        "literature-evidence",
        "support-create",
        "--project-id",
        project,
        "--target-type",
        "HypothesisVersion",
        "--target-version-id",
        frozen["id"],
        "--inputs-json",
        json.dumps([edge]),
        "--json",
    )
    assert snapshot["relations"][0]["relation_type"] == "CONTEXTUALIZES"
    assert (
        cli(
            "literature-evidence",
            "get",
            "--project-id",
            project,
            "--evidence-id",
            evidence["id"],
            "--json",
        )
        == evidence
    )
    assert (
        cli(
            "literature-evidence",
            "support-get",
            "--project-id",
            project,
            "--snapshot-id",
            snapshot["id"],
            "--json",
        )
        == snapshot
    )
    cli(
        "--request-id",
        str(uuid4()),
        "literature-evidence",
        "review",
        "--project-id",
        project,
        "--evidence-id",
        evidence["id"],
        "--status",
        "VERIFIED",
        "--basis",
        "Self verification must be rejected",
        "--json",
        ok=False,
    )
    cli(
        "--request-id",
        str(uuid4()),
        "literature-evidence",
        "support-create",
        "--project-id",
        project,
        "--target-type",
        "HypothesisVersion",
        "--target-version-id",
        frozen["id"],
        "--inputs-json",
        json.dumps([{**edge, "relation_type": "SUPPORTS"}]),
        "--json",
        ok=False,
    )
    cli(
        "--actor-id",
        str(uuid4()),
        "literature-evidence",
        "get",
        "--project-id",
        project,
        "--evidence-id",
        evidence["id"],
        "--json",
        ok=False,
    )
    cli(
        "literature-evidence",
        "get",
        "--project-id",
        str(uuid4()),
        "--evidence-id",
        evidence["id"],
        "--json",
        ok=False,
    )
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        db_version = connection.execute(text("SELECT version()")).scalar_one()
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_evidence_review_events")
            ).scalar_one()
            == 0
        )
    engine.dispose()
    output = {
        "os_uid": os.getuid(),
        "postgresql": db_version,
        "migration": head,
        "principal": actor,
        "project": project,
        "source": source,
        "document": document,
        "source_version": source_version,
        "evidence": evidence,
        "hypothesis": frozen,
        "snapshot": snapshot,
        "real_independent_human_verification": (
            "NOT RUN: no designated independent authenticated "
            "human reviewer; existing profile is single-user"
        ),
        "cli_process_restart_readback": "PASS",
        "transcript": transcript,
    }
    Path("/private/tmp/rb-m3-real-cli.json").write_text(json.dumps(output, indent=2))
