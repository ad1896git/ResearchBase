"""Real CLI/provider demonstration against an explicitly configured disposable DB.

Set DATABASE_URL, RESEARCHBASE_LOCAL_ROOT and ARTIFACT_STORE_ROOT to a fresh
migrated disposable installation. No fixture provider is used by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume-project")
    parser.add_argument("--resume-execution")
    args = parser.parse_args()
    for name in ("DATABASE_URL", "RESEARCHBASE_LOCAL_ROOT", "ARTIFACT_STORE_ROOT"):
        if not os.environ.get(name):
            raise SystemExit(f"{name} is required")
    commands = []

    def cli(*words):
        command = [sys.executable, "-m", "researchbase.cli.main", *words]
        run = subprocess.run(command, capture_output=True, text=True, timeout=120)
        commands.append(["researchbase", *words])
        if run.returncode:
            raise RuntimeError(run.stderr)
        return json.loads(run.stdout.splitlines()[-1])

    def write(*words):
        return cli("--request-id", str(uuid4()), *words, "--json")

    started = datetime.now(UTC).isoformat()
    if args.resume_project and args.resume_execution:
        project = args.resume_project
        principal = cli("local", "whoami", "--json")
        execution = {"execution_id": args.resume_execution}
        provenance = cli(
            "literature-search-execution",
            "provenance",
            "--project-id",
            project,
            "--execution-id",
            args.resume_execution,
            "--json",
        )
        plan = provenance["plan"]
        executed = provenance["execution"]
        assert executed["status"] == "SUCCEEDED", executed
    else:
        cli("local", "init", "--json")
        first = cli(
            "local",
            "bootstrap",
            "--display-name",
            "M2 live researcher",
            "--project-name",
            "M2 bibliographic demonstration",
            "--json",
        )
        project = first["project_id"]
        principal = cli("local", "whoami", "--json")
        question = cli(
            "local",
            "question-create",
            "--project-id",
            project,
            "--question-text",
            "What structural mechanisms underlie CRISPR Cas9?",
            "--json",
        )
        frozen = cli(
            "local",
            "question-freeze",
            "--question-id",
            question["id"],
            "--version-id",
            question["current_version_id"],
            "--json",
        )
        material = {
            "objective": "Retrieve two bibliographic candidates about CRISPR Cas9 structure",
            "source_scope": "BIBLIOGRAPHIC",
            "search_strategy": "KEYWORD",
            "planned_providers": ["openalex"],
            "language_scope": [],
            "research_question_refs": [
                {
                    "research_question_id": question["id"],
                    "version_id": frozen["id"],
                    "content_hash": frozen["content_hash"],
                }
            ],
        }
        plan = write(
            "literature",
            "search-plan",
            "create",
            "--project-id",
            project,
            "--material-json",
            json.dumps(material),
        )
        write(
            "literature",
            "search-plan",
            "freeze",
            "--project-id",
            project,
            "--plan-id",
            plan["plan_id"],
            "--version-id",
            plan["version_id"],
        )
        execution = write(
            "literature-search-execution",
            "create",
            "--project-id",
            project,
            "--plan-version-id",
            plan["version_id"],
            "--provider-id",
            "openalex",
            "--provider-version",
            "works-v1",
            "--queries-json",
            json.dumps([{"query_text": "CRISPR Cas9 Structures and Mechanisms"}]),
            "--max-results",
            "2",
            "--timeout-seconds",
            "15",
            "--max-provider-attempts",
            "2",
            "--execution-budget-seconds",
            "60",
        )
        executed = write(
            "literature-search-execution",
            "execute",
            "--project-id",
            project,
            "--execution-id",
            execution["execution_id"],
        )
        provenance = cli(
            "literature-search-execution",
            "provenance",
            "--project-id",
            project,
            "--execution-id",
            execution["execution_id"],
            "--json",
        )
        assert provenance["execution"]["status"] == "SUCCEEDED", provenance["execution"]
        executed = provenance["execution"]
    observations = []
    for result in provenance["results"]:
        observation = write(
            "literature-metadata", "observe", "--project-id", project, "--result-id", result["id"]
        )
        readback = cli(
            "literature-metadata",
            "get",
            "--project-id",
            project,
            "--observation-id",
            observation["id"],
            "--json",
        )
        assert readback == observation
        resolution = cli(
            "literature-metadata",
            "resolve",
            "--project-id",
            project,
            "--observation-id",
            observation["id"],
            "--json",
        )
        source = None
        version = None
        if resolution["resolution"]:
            source = cli(
                "literature",
                "source",
                "show",
                "--project-id",
                project,
                "--source-id",
                resolution["resolution"]["source_id"],
                "--json",
            )
            version = cli(
                "literature",
                "version",
                "show",
                "--project-id",
                project,
                "--source-version-id",
                resolution["resolution"]["source_version_id"],
                "--json",
            )
        observations.append(
            {
                "observation": observation,
                "resolution": resolution,
                "source": source,
                "version": version,
            }
        )
    assert any(item["resolution"]["resolution"] for item in observations), observations
    assert (
        cli(
            "literature-search-execution",
            "provenance",
            "--project-id",
            project,
            "--execution-id",
            execution["execution_id"],
            "--json",
        )
        == provenance
    )
    evidence = {
        "verdict": "PASS",
        "real_uid": os.getuid(),
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "actor_id": principal["actor_id"],
        "project_id": project,
        "plan": plan,
        "execution": executed,
        "provenance": provenance,
        "observations": observations,
        "commands": commands,
        "readback": "exact equality across separate authenticated CLI subprocesses",
    }
    Path(args.output).write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            {
                "verdict": "PASS",
                "project_id": project,
                "execution_id": execution["execution_id"],
                "results": len(provenance["results"]),
                "outcomes": [item["observation"]["outcome"] for item in observations],
                "output": args.output,
            }
        )
    )


if __name__ == "__main__":
    main()
