#!/usr/bin/env bash
set -uo pipefail

readonly EXPECTED_REPO="/private/tmp/ResearchBase-phase2-recovered"
readonly EXPECTED_BRANCH="phase2/entry-gate"
readonly DESIGN_SUBJECT="8c4355b7b8f25450a97436c1989e254c023ad34e"
readonly IMPLEMENTATION_SHA="3de5e897cc72de3e4c4f7b86d83ed8ae2b13fc93"
readonly EVIDENCE_SHA="a8fd1fef2475b12c50e6f18a4aaa6d9b0e663d02"
readonly PHASE1_BASELINE="d2400fbeca835c89bd802a4e9d647bda01cfd115"
PG_BIN=""
POSTGRES_VERSION_TEXT=""
POSTGRES_VERSION=""
readonly PYTHON_ENV_ROOT="/Users/onephone/Documents/Codex/ResearchBase"
readonly PYTHON_BIN="/Users/onephone/Documents/Codex/ResearchBase/.venv/bin/python"
readonly PYTHON_SCRIPTS="$PYTHON_ENV_ROOT/.venv/bin"
readonly EXPECTED_HEAD_REVISION="0022_source_version_and_merge_lineage"
readonly BASELINE_REVISION="0018_current_pointer_same_parent_integrity"

MODE=""
DRY_RUN=0
RUN_ID=""
RUN_TMP=""
PGDATA=""
PGLOG=""
PORT=""
DATABASE_URL=""
RUN_OUTPUT_DIR=""
MANIFEST=""
SERVER_STARTED=0
CLEANUP_STATUS="NOT_STARTED"
PR2_00_TEMPORAL_STATUS="NOT_RUN"
POSTGRES_VERSION_TEXT=""
PREFLIGHT_STATUS="NOT_RUN"
MIGRATION_HEAD="UNKNOWN"

usage() {
  cat <<'EOF'
Usage: bash scripts/researchbase_host_review.sh --pr2-02-closure [--dry-run]
       bash scripts/researchbase_host_review.sh --pr2-03-verification

Runs PR2-02 PostgreSQL 18 closure verification on the normal macOS host using
an isolated temporary cluster. --dry-run validates inputs and prints the
planned lifecycle without starting PostgreSQL.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

discover_postgres18() {
  local candidate version_text version_number binary
  if [ -x "/opt/homebrew/opt/postgresql@18/bin/postgres" ]; then
    candidate="/opt/homebrew/opt/postgresql@18/bin"
  elif command -v brew >/dev/null 2>&1; then
    local prefix
    prefix="$(brew --prefix postgresql@18 2>/dev/null || true)"
    if [ -n "$prefix" ] && [ -x "$prefix/bin/postgres" ]; then
      candidate="$prefix/bin"
    else
      printf 'PostgreSQL 18 Homebrew binaries were not found.\n' >&2
      return 1
    fi
  else
    printf 'PostgreSQL 18 binaries and Homebrew are unavailable.\n' >&2
    return 1
  fi

  for binary in postgres initdb pg_ctl psql pg_isready createdb; do
    if [ ! -x "$candidate/$binary" ]; then
      printf 'Required PostgreSQL binary is missing: %s/%s\n' "$candidate" "$binary" >&2
      return 1
    fi
  done
  version_text="$("$candidate/postgres" --version 2>&1)" || return 1
  case "$version_text" in
    *"PostgreSQL) 18."*|*"PostgreSQL 18."*) ;;
    *) printf 'Expected PostgreSQL 18.x, found: %s\n' "$version_text" >&2; return 1 ;;
  esac
  version_number="$(printf '%s\n' "$version_text" | sed -E 's/.*PostgreSQL\)? ([0-9]+\.[0-9]+).*/\1/')"
  [ "$version_number" != "$version_text" ] || return 1
  PG_BIN="$candidate"
  POSTGRES_VERSION_TEXT="$version_text"
  POSTGRES_VERSION="$version_number"
  export PG_BIN POSTGRES_VERSION_TEXT POSTGRES_VERSION
  return 0
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --pr2-02-closure)
      [ -z "$MODE" ] || fail "select exactly one mode"
      MODE="pr2-02-closure"
      ;;
    --pr2-03-verification)
      [ -z "$MODE" ] || fail "select exactly one mode"
      MODE="pr2-03-verification"
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unsupported argument: $1"
      ;;
  esac
  shift
done

[ -n "$MODE" ] || { usage >&2; exit 2; }

if [ "$MODE" = "pr2-03-verification" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  if ! discover_postgres18; then
    printf 'CHECK postgres18_binary FAIL\nHOST_POSTGRESQL_18_UNAVAILABLE\n' >&2
    exit 2
  fi
  printf 'POSTGRESQL_VERSION=%s\nPG_BIN=%s\n' "$POSTGRES_VERSION" "$PG_BIN"
  if [ "$DRY_RUN" -eq 1 ]; then
    exec bash "$SCRIPT_DIR/researchbase_host_pr2_03_verification.sh" --dry-run
  fi
  exec bash "$SCRIPT_DIR/researchbase_host_pr2_03_verification.sh"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
[ "$REPO_ROOT" = "$EXPECTED_REPO" ] || fail "runner must be used from $EXPECTED_REPO"
cd "$REPO_ROOT" || fail "could not enter repository root"
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

record_check() {
  check_id="$1"
  check_rc="$2"
  check_command="$3"
  check_log="$4"
  printf '%s\t%s\t%s\t%s\n' "$check_id" "$check_rc" "$check_command" "$check_log" >> "$MANIFEST"
  if [ "$check_rc" -eq 0 ]; then
    printf 'CHECK %s PASS\n' "$check_id"
  else
    printf 'CHECK %s FAIL (exit %s); log: %s\n' "$check_id" "$check_rc" "$check_log"
  fi
}

run_step() {
  step_id="$1"
  command_text="$2"
  shift 2
  step_log="$RUN_OUTPUT_DIR/logs/$step_id.log"
  "$@" > "$step_log" 2>&1
  step_rc=$?
  record_check "$step_id" "$step_rc" "$command_text" "$step_log"
  return 0
}

verify_pg18_binaries() {
  discover_postgres18
}

verify_static_inputs() {
  git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 1
  [ "$(git -C "$REPO_ROOT" branch --show-current)" = "$EXPECTED_BRANCH" ] || {
    printf 'Unexpected branch; expected %s.\n' "$EXPECTED_BRANCH" >&2
    return 1
  }
  current_head="$(git -C "$REPO_ROOT" rev-parse HEAD)" || return 1
  git -C "$REPO_ROOT" merge-base --is-ancestor "$DESIGN_SUBJECT" "$current_head" || {
    printf 'Current HEAD does not descend from frozen PR2-03 subject %s.\n' "$DESIGN_SUBJECT" >&2
    return 1
  }
  for subject in "$IMPLEMENTATION_SHA" "$EVIDENCE_SHA" "$PHASE1_BASELINE" "$DESIGN_SUBJECT"; do
    git -C "$REPO_ROOT" cat-file -e "$subject^{commit}" 2>/dev/null || {
      printf 'Required subject commit is absent: %s\n' "$subject" >&2
      return 1
    }
  done
  git -C "$REPO_ROOT" merge-base --is-ancestor "$IMPLEMENTATION_SHA" "$EVIDENCE_SHA" || {
    printf 'PR2-02 evidence is not a descendant of the implementation subject.\n' >&2
    return 1
  }
  git -C "$REPO_ROOT" grep -F "$IMPLEMENTATION_SHA" "$EVIDENCE_SHA" -- artifacts/pr_evidence/PR2-02 >/dev/null 2>&1 || {
    printf 'PR2-02 evidence does not bind the implementation SHA.\n' >&2
    return 1
  }
  tag_commit="$(git -C "$REPO_ROOT" rev-parse 'phase1-final-v4^{commit}' 2>/dev/null)" || return 1
  [ "$tag_commit" = "$PHASE1_BASELINE" ] || {
    printf 'phase1-final-v4 resolves to %s, expected %s.\n' "$tag_commit" "$PHASE1_BASELINE" >&2
    return 1
  }
  git -C "$REPO_ROOT" diff --quiet "$IMPLEMENTATION_SHA" -- src migrations pyproject.toml uv.lock || {
    printf 'PR2-02 production/configuration inputs differ from the reviewed implementation subject.\n' >&2
    return 1
  }
  git -C "$REPO_ROOT" diff --quiet "$IMPLEMENTATION_SHA" -- tests \
    ':(exclude)tests/integration/test_p1_fcr4_boundary_corruption.py' \
    ':(exclude)tests/integration/test_p1_fcr4_postgres_digest_invariance.py' || {
    printf 'Tests differ from the reviewed subject outside the two authorized PG 18.6 assertions.\n' >&2
    return 1
  }
  grep -F 'int(connection.scalar(text("SHOW server_version_num"))) == 180006' \
    "$REPO_ROOT/tests/integration/test_p1_fcr4_boundary_corruption.py" >/dev/null || {
    printf 'Authorized boundary test must assert PostgreSQL 18.6 via server_version_num.\n' >&2
    return 1
  }
  grep -F 'int(connection.execute(text("SHOW server_version_num")).scalar_one()) == 180006' \
    "$REPO_ROOT/tests/integration/test_p1_fcr4_postgres_digest_invariance.py" >/dev/null || {
    printf 'Authorized digest test must assert PostgreSQL 18.6 via server_version_num.\n' >&2
    return 1
  }
  git -C "$REPO_ROOT" diff --quiet "$DESIGN_SUBJECT" -- execution/phase2/PR2-03_Literature_Search_Plan_Execution_Pack_v1.0.md || {
    printf 'The frozen PR2-03 pack differs from its design subject.\n' >&2
    return 1
  }
  [ -x "$PYTHON_BIN" ] || {
    printf 'Required Python is missing: %s\n' "$PYTHON_BIN" >&2
    return 1
  }
  "$PYTHON_BIN" -c 'import researchbase, alembic, fastapi, idna, psycopg, pydantic, pytest, sqlalchemy, typer' >/dev/null 2>&1 || {
    printf 'ResearchBase source or required project Python dependency is unavailable.\n' >&2
    return 1
  }
  for tool in alembic pytest ruff pyright; do
    [ -x "$PYTHON_SCRIPTS/$tool" ] || {
      printf 'Required host tool is missing: %s\n' "$tool" >&2
      return 1
    }
  done
  return 0
}

choose_port() {
  "$PYTHON_BIN" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

write_result() {
  exit_code="$1"
  [ -n "$RUN_OUTPUT_DIR" ] || return 0
  "$PYTHON_BIN" - "$RUN_OUTPUT_DIR" "$MANIFEST" "$RUN_ID" "$exit_code" <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

out_dir = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
run_id = sys.argv[3]
process_exit = int(sys.argv[4])
checks = []
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    if not line:
        continue
    check_id, raw_rc, command, log_path = line.split("\t", 3)
    checks.append(
        {
            "id": check_id,
            "exit_code": int(raw_rc),
            "status": "PASS" if raw_rc == "0" else "FAIL",
            "command": command,
            "log": log_path,
        }
    )

def pytest_counts(xml_path: Path) -> dict[str, int] | None:
    if not xml_path.is_file():
        return None
    root = ET.parse(xml_path).getroot()
    cases = list(root.iter("testcase"))
    counts = {"collected": len(cases), "passed": 0, "skipped": 0, "xfailed": 0, "failed": 0, "errors": 0}
    for case in cases:
        if case.find("error") is not None:
            counts["errors"] += 1
        elif case.find("failure") is not None:
            counts["failed"] += 1
        elif (skipped := case.find("skipped")) is not None:
            if "xfail" in skipped.get("type", "").lower():
                counts["xfailed"] += 1
            else:
                counts["skipped"] += 1
        else:
            counts["passed"] += 1
    return counts

def check_by_id(check_id: str) -> dict | None:
    return next((check for check in checks if check["id"] == check_id), None)

temporal_check = check_by_id("pr2_00_temporal_expiry")

def add_warning_count(counts: dict[str, int] | None, log_name: str) -> dict[str, int] | None:
    if counts is None:
        return None
    log_path = out_dir / "logs" / log_name
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    matches = re.findall(r"\b(\d+) warnings?\b", log_text)
    counts["warnings"] = int(matches[-1]) if matches else 0
    return counts

full_counts = add_warning_count(pytest_counts(out_dir / "logs" / "full_suite.xml"), "full_suite.log")
focused_counts = add_warning_count(pytest_counts(out_dir / "logs" / "focused_pr2_02.xml"), "focused_pr2_02.log")
formatter = {}
formatter_path = out_dir / "formatter_baseline_delta.json"
if formatter_path.is_file():
    formatter = json.loads(formatter_path.read_text(encoding="utf-8"))

temporal_status = os.environ.get("RB_TEMPORAL_STATUS", "NOT_RUN")
db_probe_path = out_dir / "logs" / "python_db_probe.log"
db_probe = db_probe_path.read_text(encoding="utf-8", errors="replace") if db_probe_path.exists() else ""
version_match = re.search(r"^SERVER_VERSION=(.*)$", db_probe, re.MULTILINE)
db_match = re.search(r"^DATABASE=(.*)$", db_probe, re.MULTILINE)
user_match = re.search(r"^USER=(.*)$", db_probe, re.MULTILINE)
timezone_match = re.search(r"^TIMEZONE=(.*)$", db_probe, re.MULTILINE)
temporal_proof_path = out_dir / "temporal_proof.json"
temporal_proof = (
    json.loads(temporal_proof_path.read_text(encoding="utf-8"))
    if temporal_proof_path.is_file()
    else None
)

failed_required = [
    check["id"]
    for check in checks
    if check["exit_code"] != 0 and check["id"] != "ruff_format_raw"
]
formatter_delta_pass = formatter.get("new_format_failures") == []
verification_gate = "PASS" if not failed_required and formatter_delta_pass and process_exit == 0 else "FAIL"
if temporal_status != "NO_RESIDUAL_REPRODUCED":
    verification_gate = "FAIL"

result = {
    "run_id": run_id,
    "mode": "pr2-02-closure",
    "review_scope": "verification evidence only; no independent reviewer verdict",
    "reviewed_implementation_sha": "3de5e897cc72de3e4c4f7b86d83ed8ae2b13fc93",
    "reviewed_evidence_sha": "a8fd1fef2475b12c50e6f18a4aaa6d9b0e663d02",
    "phase1_baseline_sha": "d2400fbeca835c89bd802a4e9d647bda01cfd115",
    "postgres": {
        "version": os.environ.get("RB_POSTGRES_VERSION", "unavailable"),
        "host": "127.0.0.1",
        "port": os.environ.get("RB_POSTGRES_PORT"),
        "database": "researchbase_review",
        "phase1_database": "researchbase_phase1_review",
        "phase1_migration": "0018_current_pointer_same_parent_integrity",
        "phase2_database": "researchbase_review",
        "phase2_migration": "0022_source_version_and_merge_lineage",
        "timezone": "UTC",
        "user": "researchbase",
        "database_url": "postgresql+psycopg://researchbase@127.0.0.1:<temporary-port>/researchbase_review",
        "temporary_cluster_cleaned": os.environ.get("RB_CLEANUP_STATUS", "NOT_STARTED"),
    },
    "migration": {
        "expected_unique_head": "0022_source_version_and_merge_lineage",
        "observed_head": os.environ.get("RB_MIGRATION_HEAD", "UNKNOWN"),
        "lineage": [
            "0018_current_pointer_same_parent_integrity",
            "0019_phase2_bootstrap_membership",
            "0020_literature_source_identity",
            "0021_source_merge_governance_bridge",
            "0021a_source_merge_gov_guards",
            "0022_source_version_and_merge_lineage",
        ],
    },
    "focused_pytest": focused_counts,
    "full_suite": full_counts,
    "ruff": check_by_id("ruff_check"),
    "pyright": check_by_id("pyright"),
    "formatter": {
        "raw_result": "PASS" if (check_by_id("ruff_format_raw") or {}).get("exit_code") == 0 else "FAIL",
        "raw_exit_code": (check_by_id("ruff_format_raw") or {}).get("exit_code"),
        "baseline_delta_gate": "PASS" if formatter_delta_pass else "FAIL",
        **formatter,
    },
    "git_diff_check": check_by_id("git_diff_check"),
    "phase1_migration_drift": os.environ.get("RB_PHASE1_MIGRATION_DRIFT", "UNKNOWN"),
    "phase1_semantic_drift": "NOT_INDEPENDENTLY_REVIEWED; baseline tag, historical migrations, and regression results are recorded",
    "pr2_00_temporal": {
        "status": temporal_status,
        "test": "tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait",
        "exit_code": temporal_check["exit_code"] if temporal_check else None,
        "residual_reopened": temporal_status == "RESIDUAL_REOPENED",
        "trace": temporal_proof,
    },
    "database_identity": {
        "server_version": version_match.group(1).strip() if version_match else None,
        "database": db_match.group(1).strip() if db_match else None,
        "user": user_match.group(1).strip() if user_match else None,
        "timezone": timezone_match.group(1).strip() if timezone_match else None,
    },
    "checks": checks,
    "failed_required_checks": failed_required,
    "verification_gate": verification_gate,
    "P0": None,
    "P1": None,
    "P2": None,
    "verdict": "NOT_ISSUED_INDEPENDENT_REVIEW_REQUIRED",
    "runner_exit_code": process_exit,
}

json_path = out_dir / "host_review_result.json"
json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "# PR2-02 Host Review Verification",
    "",
    f"- Run: `{run_id}`",
    "- Result type: verification evidence only; an independent reviewer must issue the verdict.",
    f"- Implementation: `{result['reviewed_implementation_sha']}`",
    f"- Evidence: `{result['reviewed_evidence_sha']}`",
    f"- Phase 1 baseline: `{result['phase1_baseline_sha']}`",
    f"- PostgreSQL: `{result['postgres']['version']}` at `127.0.0.1:{result['postgres']['port']}`; UTC session. Phase 1 database `researchbase_phase1_review` at migration 0018; Phase 2 database `researchbase_review` at migration 0022; user `researchbase`.",
    f"- Temporary cluster cleanup: `{result['postgres']['temporary_cluster_cleaned']}`.",
    "",
    "## Commands and Results",
    "",
]
for check in checks:
    lines.append(f"- `{check['id']}`: **{check['status']}** (`{check['command']}`); log: `{check['log']}`.")
lines += [
    "",
    "## Test Counts",
    "",
    f"- Focused PR2-02: `{focused_counts}`",
    f"- Full suite: `{full_counts}`",
    "",
    "## Gates",
    "",
    f"- Migration head: expected `{result['migration']['expected_unique_head']}`, observed `{result['migration']['observed_head']}`.",
    f"- Raw formatter: **{result['formatter']['raw_result']}**; FORMAT-BASELINE-01 delta: **{result['formatter']['baseline_delta_gate']}**.",
    f"- Phase 1 migration drift: `{result['phase1_migration_drift']}`.",
    f"- PR2-00 temporal: `{temporal_status}`; residual reopened: `{result['pr2_00_temporal']['residual_reopened']}`.",
    f"- Temporal proof: `{temporal_proof}`",
    f"- Verification gate: **{verification_gate}**.",
    "- P0/P1/P2 and reviewer verdict are intentionally unissued; the independent reviewer evaluates this result and the implementation.",
]
md_path = out_dir / "host_review_result.md"
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"JSON_RESULT={json_path}")
print(f"MARKDOWN_RESULT={md_path}")
print(f"VERIFICATION_GATE={verification_gate}")
PY
}

cleanup_and_report() {
  process_rc=$?
  trap - EXIT INT TERM
  if [ -n "$RUN_TMP" ] && [ -d "$RUN_TMP" ]; then
    case "$RUN_TMP" in
      /private/tmp/researchbase-host-review.*)
        if [ -n "$PGDATA" ] && [ -d "$PGDATA" ] && [ -x "$PG_BIN/pg_ctl" ]; then
          if "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
            if "$PG_BIN/pg_ctl" -D "$PGDATA" stop -m fast -w > "$RUN_OUTPUT_DIR/logs/postgres_stop.log" 2>&1; then
              CLEANUP_STATUS="PASS_SERVER_STOPPED"
            elif ! "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
              CLEANUP_STATUS="PASS_SERVER_STOPPED_AFTER_FAST_ATTEMPT"
            elif "$PG_BIN/pg_ctl" -D "$PGDATA" stop -m immediate -w >> "$RUN_OUTPUT_DIR/logs/postgres_stop.log" 2>&1; then
              CLEANUP_STATUS="PASS_SERVER_STOPPED_IMMEDIATELY"
            else
              CLEANUP_STATUS="FAIL_SERVER_STOP"
              process_rc=1
            fi
          else
            CLEANUP_STATUS="PASS_SERVER_NOT_RUNNING"
          fi
        else
          CLEANUP_STATUS="PASS_SERVER_NOT_STARTED"
        fi
        if [ -f "$PGLOG" ]; then
          cp "$PGLOG" "$RUN_OUTPUT_DIR/logs/postgres_server.log" 2>/dev/null || true
        fi
        if [ "$CLEANUP_STATUS" != "FAIL_SERVER_STOP" ]; then
          rm -rf -- "$RUN_TMP"
          RUN_TMP=""
        else
          printf 'Temporary cluster retained because PostgreSQL did not stop: %s\n' "$RUN_TMP" >&2
        fi
        ;;
      *)
        printf 'Refusing to remove unexpected temporary path: %s\n' "$RUN_TMP" >&2
        CLEANUP_STATUS="FAIL_UNSAFE_TEMP_PATH"
        process_rc=1
        ;;
    esac
  elif [ "$CLEANUP_STATUS" = "NOT_STARTED" ]; then
    CLEANUP_STATUS="NOT_CREATED"
  fi
  if [ -n "$RUN_OUTPUT_DIR" ]; then
    RB_CLEANUP_STATUS="$CLEANUP_STATUS" \
    RB_POSTGRES_VERSION="$POSTGRES_VERSION_TEXT" \
    RB_POSTGRES_PORT="$PORT" \
    RB_TEMPORAL_STATUS="$PR2_00_TEMPORAL_STATUS" \
    RB_PHASE1_MIGRATION_DRIFT="${PHASE1_MIGRATION_DRIFT:-UNKNOWN}" \
      write_result "$process_rc"
  fi
  exit "$process_rc"
}

if ! verify_pg18_binaries; then
  fail "PostgreSQL 18 binaries are unavailable at $PG_BIN"
fi
if ! verify_static_inputs; then
  PREFLIGHT_STATUS="FAIL"
  exit 1
fi
PREFLIGHT_STATUS="PASS"

if [ "$DRY_RUN" -eq 1 ]; then
  printf 'DRY_RUN=YES\n'
  printf 'MODE=%s\n' "$MODE"
  printf 'POSTGRESQL_LIFECYCLE=planned-only\n'
  printf 'PLANNED_PGDATA=/private/tmp/researchbase-host-review-<unique>/data\n'
  printf 'PHASE1_DATABASE=researchbase_phase1_review (migration 0018)\n'
  printf 'PHASE2_DATABASE=researchbase_review (migration 0022)\n'
  printf 'PLANNED_DATABASE_URL=postgresql+psycopg://researchbase@127.0.0.1:<temporary-port>/researchbase_review\n'
  printf 'PLANNED_PYTHONPATH=%s/src\n' "$REPO_ROOT"
  printf "COMMAND_FOCUSED=%s/pytest -o 'addopts=' tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_01_source_identity.py --junitxml=<run-output>/logs/focused_pr2_02.xml\n" "$PYTHON_SCRIPTS"
  printf "COMMAND_TEMPORAL=%s/pytest -o 'addopts=' -s tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait --junitxml=<run-output>/logs/pr2_00_temporal.xml\n" "$PYTHON_SCRIPTS"
  printf "COMMAND_FULL_SUITE=%s/pytest -o 'addopts=' -ra --junitxml=<run-output>/logs/full_suite.xml\n" "$PYTHON_SCRIPTS"
  printf 'COMMAND_PYRIGHT=%s/pyright --venvpath %s\n' "$PYTHON_SCRIPTS" "$PYTHON_ENV_ROOT"
  printf 'COMMAND_FORMATTER=%s/ruff format --check .\n' "$PYTHON_SCRIPTS"
  printf 'RUNNER_DOES_NOT_START_POSTGRESQL=YES\n'
  exit 0
fi

RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$$"
RUN_OUTPUT_DIR="$REPO_ROOT/artifacts/pr_evidence/PR2-02/host-review-runs/$RUN_ID"
mkdir -p "$RUN_OUTPUT_DIR/logs" || fail "could not create host result directory"
MANIFEST="$RUN_OUTPUT_DIR/checks.tsv"
: > "$MANIFEST" || fail "could not create check manifest"
trap cleanup_and_report EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

PREFLIGHT_LOG="$RUN_OUTPUT_DIR/logs/preflight.log"
printf 'mode=%s\npreflight=%s\nrepo=%s\n' "$MODE" "$PREFLIGHT_STATUS" "$REPO_ROOT" > "$PREFLIGHT_LOG"
record_check "preflight" 0 "repository subjects, PG18 binaries and Python dependency checks" "$PREFLIGHT_LOG"

RUN_TMP="$(mktemp -d /private/tmp/researchbase-host-review.XXXXXX 2> "$RUN_OUTPUT_DIR/logs/mktemp.log")"
if [ -z "$RUN_TMP" ] || [ ! -d "$RUN_TMP" ]; then
  record_check "create_temp_cluster_dir" 1 "mktemp -d /private/tmp/researchbase-host-review.XXXXXX" "$RUN_OUTPUT_DIR/logs/mktemp.log"
  exit 1
fi
PGDATA="$RUN_TMP/data"
PGLOG="$RUN_TMP/postgres.log"
PORT="$(choose_port 2> "$RUN_OUTPUT_DIR/logs/choose_port.log")"
if [ -z "$PORT" ]; then
  record_check "choose_port" 1 "bind 127.0.0.1:0 and read selected port" "$RUN_OUTPUT_DIR/logs/choose_port.log"
  exit 1
fi
DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:${PORT}/researchbase_review"
PHASE1_DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:${PORT}/researchbase_phase1_review"
export DATABASE_URL
record_check "create_temp_cluster_dir" 0 "mktemp -d /private/tmp/researchbase-host-review.XXXXXX" "$RUN_OUTPUT_DIR/logs/mktemp.log"
printf 'PGDATA=%s\nPGLOG=%s\nPORT=%s\nPHASE1_DATABASE=researchbase_phase1_review\nPHASE1_MIGRATION=0018_current_pointer_same_parent_integrity\nPHASE2_DATABASE=researchbase_review\nPHASE2_MIGRATION=0022_source_version_and_merge_lineage\n' "$PGDATA" "$PGLOG" "$PORT" > "$RUN_OUTPUT_DIR/environment.txt"

run_step "initdb" "$PG_BIN/initdb -D <run-temp>/data --username=researchbase --auth=trust" \
  "$PG_BIN/initdb" -D "$PGDATA" --username=researchbase --auth=trust
initdb_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$initdb_rc" -ne 0 ]; then
  exit 1
fi

run_step "pg_ctl_start" "$PG_BIN/pg_ctl -D <run-temp>/data -l <run-temp>/postgres.log -o '-h 127.0.0.1 -p <port>' start" \
  "$PG_BIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -o "-h 127.0.0.1 -p $PORT -c timezone=UTC" start
start_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$start_rc" -ne 0 ]; then
  if [ -f "$PGLOG" ]; then tail -n 100 "$PGLOG" > "$RUN_OUTPUT_DIR/logs/postgres_start_failure_tail.log"; fi
  exit 1
fi
SERVER_STARTED=1

ready=0
attempt=0
while [ "$attempt" -lt 30 ]; do
  if "$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PORT" -U researchbase > "$RUN_OUTPUT_DIR/logs/pg_isready.log" 2>&1; then
    ready=1
    break
  fi
  attempt=$((attempt + 1))
  sleep 1
done
record_check "pg_isready" "$((1 - ready))" "$PG_BIN/pg_isready -h 127.0.0.1 -p <port> -U researchbase (30 attempts)" "$RUN_OUTPUT_DIR/logs/pg_isready.log"
if [ "$ready" -ne 1 ]; then
  if [ -f "$PGLOG" ]; then tail -n 100 "$PGLOG" > "$RUN_OUTPUT_DIR/logs/postgres_readiness_failure_tail.log"; fi
  exit 1
fi

run_step "create_review_database" "$PG_BIN/createdb -h 127.0.0.1 -p <port> -U researchbase researchbase_review" \
  "$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_review
create_db_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$create_db_rc" -ne 0 ]; then exit 1; fi
run_step "create_phase1_review_database" "$PG_BIN/createdb -h 127.0.0.1 -p <port> -U researchbase researchbase_phase1_review" \
  "$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_phase1_review
phase1_create_db_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$phase1_create_db_rc" -ne 0 ]; then exit 1; fi

run_step "postgres_identity" "$PG_BIN/psql -h 127.0.0.1 -p <port> -U researchbase -d researchbase_review -c 'SELECT version(), current_database(), current_user, current_setting(...)'" \
  "$PG_BIN/psql" -h 127.0.0.1 -p "$PORT" -U researchbase -d researchbase_review -Atc \
  "SELECT version() || E'\\n' || current_database() || E'\\n' || current_user || E'\\n' || current_setting('server_version_num') || E'\\n' || current_setting('TimeZone')"
identity_log="$RUN_OUTPUT_DIR/logs/postgres_identity.log"
identity_lines="$(cat "$identity_log")"
POSTGRES_VERSION_TEXT="$(printf '%s\n' "$identity_lines" | sed -n '1p')"
server_db="$(printf '%s\n' "$identity_lines" | sed -n '2p')"
server_user="$(printf '%s\n' "$identity_lines" | sed -n '3p')"
server_version_num="$(printf '%s\n' "$identity_lines" | sed -n '4p')"
server_timezone="$(printf '%s\n' "$identity_lines" | sed -n '5p')"
case "$POSTGRES_VERSION_TEXT" in *"PostgreSQL 18."*) version_ok=1 ;; *) version_ok=0 ;; esac
if [ "$version_ok" -ne 1 ] || [ "$server_db" != "researchbase_review" ] || [ "$server_user" != "researchbase" ] || [ "${server_version_num:0:2}" != "18" ] || [ "$server_timezone" != "UTC" ]; then
  record_check "postgres_identity_assertions" 1 "assert PostgreSQL 18, researchbase_review, researchbase and UTC session timezone" "$identity_log"
  exit 1
fi
record_check "postgres_identity_assertions" 0 "assert PostgreSQL 18, researchbase_review, researchbase and UTC session timezone" "$identity_log"

cat > "$RUN_TMP/python_db_probe.py" <<'PY'
import os
import psycopg

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version(), current_database(), current_user, current_setting('TimeZone')")
        version, database, user, timezone = cur.fetchone()
print("SERVER_VERSION=" + version)
print("DATABASE=" + database)
print("USER=" + user)
print("TIMEZONE=" + timezone)
if not version.startswith("PostgreSQL 18.") or database != "researchbase_review" or user != "researchbase" or timezone != "UTC":
    raise SystemExit("PostgreSQL connection identity mismatch")
print("PYTHON_DATABASE_CONNECTION_OK")
PY
run_step "python_db_probe" "$PYTHON_BIN <python_db_probe.py> (DATABASE_URL supplied through environment)" \
  "$PYTHON_BIN" "$RUN_TMP/python_db_probe.py"

ALEMBIC="$PYTHON_SCRIPTS/alembic"
PYTEST="$PYTHON_SCRIPTS/pytest"
RUFF="$PYTHON_SCRIPTS/ruff"
PYRIGHT="$PYTHON_SCRIPTS/pyright"

run_step "migration_chain" "verify exact revision/down_revision edges from 0018 through 0022" \
  "$PYTHON_BIN" - "$REPO_ROOT" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = [
    ("0018_current_pointer_same_parent_integrity", "0017_persisted_canonical_enum_normalization"),
    ("0019_phase2_bootstrap_membership", "0018_current_pointer_same_parent_integrity"),
    ("0020_literature_source_identity", "0019_phase2_bootstrap_membership"),
    ("0021_source_merge_governance_bridge", "0020_literature_source_identity"),
    ("0021a_source_merge_gov_guards", "0021_source_merge_governance_bridge"),
    ("0022_source_version_and_merge_lineage", "0021a_source_merge_gov_guards"),
]
revisions = {}
for path in (root / "migrations/versions").glob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    values[target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in {"revision", "down_revision"}:
                values[node.target.id] = ast.literal_eval(node.value)
    if values.get("revision"):
        revisions[values["revision"]] = values.get("down_revision")
for revision, parent in expected:
    if revision not in revisions or revisions[revision] != parent:
        raise SystemExit(f"migration edge mismatch: {revision} -> {revisions.get(revision)!r}, expected {parent!r}")
print("MIGRATION_CHAIN_OK=YES")
for revision, parent in expected:
    print(f"{parent} -> {revision}")
PY

run_step "alembic_history" "$ALEMBIC history --verbose" "$ALEMBIC" history --verbose
run_step "alembic_heads" "$ALEMBIC heads" "$ALEMBIC" heads
heads_log="$RUN_OUTPUT_DIR/logs/alembic_heads.log"
head_count="$(grep -c '(head)' "$heads_log" 2>/dev/null || true)"
MIGRATION_HEAD="$(sed -n '1p' "$heads_log" | sed 's/ (head)$//')"
if [ "$head_count" = "1" ] && grep -F "$EXPECTED_HEAD_REVISION (head)" "$heads_log" >/dev/null 2>&1; then
  record_check "migration_unique_head_assertion" 0 "require unique Alembic head $EXPECTED_HEAD_REVISION" "$heads_log"
else
  record_check "migration_unique_head_assertion" 1 "require unique Alembic head $EXPECTED_HEAD_REVISION" "$heads_log"
fi
export RB_MIGRATION_HEAD="$MIGRATION_HEAD"

export DATABASE_URL="$PHASE1_DATABASE_URL"
run_step "migration_upgrade_0018" "$ALEMBIC upgrade $BASELINE_REVISION (DATABASE_URL database=researchbase_phase1_review)" "$ALEMBIC" upgrade "$BASELINE_REVISION"
phase1_base_upgrade_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$phase1_base_upgrade_rc" -eq 0 ]; then
  run_step "migration_current_0018" "$ALEMBIC current (DATABASE_URL database=researchbase_phase1_review)" "$ALEMBIC" current
  if grep -F "$BASELINE_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_0018.log" >/dev/null 2>&1; then
    record_check "migration_current_0018_assertion" 0 "require researchbase_phase1_review at $BASELINE_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_0018.log"
  else
    record_check "migration_current_0018_assertion" 1 "require researchbase_phase1_review at $BASELINE_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_0018.log"
  fi
fi

export DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:${PORT}/researchbase_review"
run_step "migration_upgrade_0018_phase2" "$ALEMBIC upgrade $BASELINE_REVISION (DATABASE_URL database=researchbase_review)" "$ALEMBIC" upgrade "$BASELINE_REVISION"
phase2_base_upgrade_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$phase2_base_upgrade_rc" -eq 0 ]; then
  run_step "migration_current_0018_phase2" "$ALEMBIC current (DATABASE_URL database=researchbase_review)" "$ALEMBIC" current
  if grep -F "$BASELINE_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_0018_phase2.log" >/dev/null 2>&1; then
    record_check "migration_current_0018_phase2_assertion" 0 "require researchbase_review at $BASELINE_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_0018_phase2.log"
  else
    record_check "migration_current_0018_phase2_assertion" 1 "require researchbase_review at $BASELINE_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_0018_phase2.log"
  fi
fi
run_step "migration_upgrade_head" "$ALEMBIC upgrade head (DATABASE_URL database=researchbase_review)" "$ALEMBIC" upgrade head
head_upgrade_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if [ "$head_upgrade_rc" -eq 0 ]; then
  run_step "migration_current_head" "$ALEMBIC current (DATABASE_URL database=researchbase_review)" "$ALEMBIC" current
  if grep -F "$EXPECTED_HEAD_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_head.log" >/dev/null 2>&1; then
    record_check "migration_current_head_assertion" 0 "require database at $EXPECTED_HEAD_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_head.log"
  else
    record_check "migration_current_head_assertion" 1 "require database at $EXPECTED_HEAD_REVISION" "$RUN_OUTPUT_DIR/logs/migration_current_head.log"
  fi
fi

run_step "focused_pr2_02" "$PYTEST -o addopts='' tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_01_source_identity.py --junitxml=<run-output>/logs/focused_pr2_02.xml (DATABASE_URL database=researchbase_review at 0022)" \
  "$PYTEST" -o "addopts=" \
  tests/integration/phase2/test_pr2_02_source_version_migration.py \
  tests/integration/phase2/test_pr2_02_gov_application.py \
  tests/integration/phase2/test_pr2_02_gov_migration.py \
  tests/integration/phase2/test_pr2_01_source_identity.py \
  --junitxml="$RUN_OUTPUT_DIR/logs/focused_pr2_02.xml"

run_step "pr2_00_temporal_expiry" "$PYTEST -o addopts='' -s tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait --junitxml=<run-output>/logs/pr2_00_temporal.xml (DATABASE_URL database=researchbase_review at 0022)" \
  "$PYTEST" -o "addopts=" -s \
  tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait \
  --junitxml="$RUN_OUTPUT_DIR/logs/pr2_00_temporal.xml"
temporal_rc="$(tail -n 1 "$MANIFEST" | cut -f2)"
if grep -F 'TEMP-AUTH challenge proof ' "$RUN_OUTPUT_DIR/logs/pr2_00_temporal_expiry.log" > "$RUN_OUTPUT_DIR/logs/temporal_proof_line.txt" 2>/dev/null; then
  "$PYTHON_BIN" - "$RUN_OUTPUT_DIR/logs/temporal_proof_line.txt" "$RUN_OUTPUT_DIR/temporal_proof.json" "$temporal_rc" > "$RUN_OUTPUT_DIR/logs/temporal_classification.log" 2>&1 <<'PY'
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

line_path, output_path = map(Path, sys.argv[1:3])
test_rc = int(sys.argv[3])
line = line_path.read_text(encoding="utf-8").strip().splitlines()[-1]
payload = json.loads(line.split("TEMP-AUTH challenge proof ", 1)[1])
issued = datetime.fromisoformat(str(payload["challenge_issued_at"]))
expiry = datetime.fromisoformat(str(payload["expiry_at"]))
lock_wait = datetime.fromisoformat(str(payload["lock_wait_started_at"]))
lock_acquired = datetime.fromisoformat(str(payload["lock_acquired_at"]))
authorization = datetime.fromisoformat(str(payload["authorization_clock_timestamp"]))
expiry_crossed = datetime.fromisoformat(str(payload["expiry_crossed_at"]))
lock_released = datetime.fromisoformat(str(payload["lock_released_at_observed"]))
expiry_safety_margin = timedelta(milliseconds=250)
observed_wait = payload["observed_wait"]
effects = payload["persisted_effects"]
successful_consumption = (
    effects.get("challenge_status") == "CONSUMED"
    or effects.get("bindings", 0) > 0
    or effects.get("binding_events", 0) > 0
)
residual = authorization >= expiry and successful_consumption
trace_checks = {
    "issued_before_expiry": issued < expiry,
    "lock_wait_began_before_expiry": lock_wait < expiry,
    "postgres_lock_wait_observed": observed_wait.get("wait_event_type") == "Lock"
    and "actor_enrollment_challenges" in str(observed_wait.get("query")),
    "expiry_elapsed_during_wait": expiry_crossed >= expiry + expiry_safety_margin,
    "lock_released_after_expiry": lock_released >= expiry + expiry_safety_margin,
    "durable_reread_lock_acquired_after_expiry": lock_acquired >= expiry + expiry_safety_margin,
    "fresh_authorization_time_after_lock_and_expiry": authorization >= lock_acquired and authorization >= expiry,
    "post_expiry_consumption_denied": payload.get("effect_result") == "DENY",
    "challenge_remains_unconsumed": effects.get("challenge_status") == "ISSUED",
    "zero_protected_effects": effects.get("bindings") == 0 and effects.get("binding_events") == 0,
}
verified = all(trace_checks.values()) and test_rc == 0
result = {
    "issued_at": str(payload["challenge_issued_at"]),
    "expires_at": str(payload["expiry_at"]),
    "lock_wait_started_at": str(payload["lock_wait_started_at"]),
    "lock_acquired_at": str(payload["lock_acquired_at"]),
    "fresh_authorization_database_time": str(payload["authorization_clock_timestamp"]),
    "expiry_crossed_at": str(payload["expiry_crossed_at"]),
    "expiry_safety_margin": str(expiry_safety_margin),
    "observed_postgres_wait_event": observed_wait.get("wait_event"),
    "effect_result": payload.get("effect_result"),
    "successful_challenge_consumption": successful_consumption,
    "challenge_status": effects.get("challenge_status"),
    "bindings": effects.get("bindings"),
    "binding_events": effects.get("binding_events"),
    "trace_checks": trace_checks,
    "trace_verified": verified,
    "successful_post_expiry_consumption": residual,
    "PR2_00_TEMPORAL_RESIDUAL_REOPENED": "YES" if residual else "NO" if verified else "INCONCLUSIVE",
}
output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("PR2_00_TEMPORAL_RESIDUAL_REOPENED=" + result["PR2_00_TEMPORAL_RESIDUAL_REOPENED"])
print("TEMPORAL_TRACE_VERIFIED=" + ("YES" if verified else "NO"))
if residual:
    raise SystemExit(2)
if not verified:
    raise SystemExit(1)
PY
  temporal_classify_rc=$?
  if [ "$temporal_classify_rc" -eq 2 ]; then
    PR2_00_TEMPORAL_STATUS="RESIDUAL_REOPENED"
    record_check "temporal_trace_assertions" 1 "stop on successful post-expiry challenge consumption" "$RUN_OUTPUT_DIR/logs/temporal_classification.log"
    exit 1
  elif [ "$temporal_classify_rc" -eq 0 ]; then
    PR2_00_TEMPORAL_STATUS="NO_RESIDUAL_REPRODUCED"
    record_check "temporal_trace_assertions" 0 "verify lock wait, expiry, fresh authorization, denial and zero protected effects" "$RUN_OUTPUT_DIR/logs/temporal_classification.log"
  else
    PR2_00_TEMPORAL_STATUS="INCONCLUSIVE"
    record_check "temporal_trace_assertions" 1 "require complete passing TEMP-AUTH trace" "$RUN_OUTPUT_DIR/logs/temporal_classification.log"
  fi
else
  PR2_00_TEMPORAL_STATUS="INCONCLUSIVE"
  printf 'TEMP-AUTH proof line missing; temporal verification did not demonstrate the expiry boundary.\n' > "$RUN_OUTPUT_DIR/logs/temporal_classification.log"
  record_check "temporal_trace_assertions" 1 "require complete passing TEMP-AUTH trace" "$RUN_OUTPUT_DIR/logs/temporal_classification.log"
fi

export DATABASE_URL="$PHASE1_DATABASE_URL"
run_step "full_suite" "$PYTEST -o addopts='' -ra --junitxml=<run-output>/logs/full_suite.xml (DATABASE_URL database=researchbase_phase1_review at 0018)" \
  "$PYTEST" -o "addopts=" -ra --junitxml="$RUN_OUTPUT_DIR/logs/full_suite.xml"
run_step "ruff_check" "$RUFF check ." "$RUFF" check .
run_step "pyright" "$PYRIGHT --venvpath $PYTHON_ENV_ROOT" "$PYRIGHT" --venvpath "$PYTHON_ENV_ROOT"
run_step "ruff_format_raw" "$RUFF format --check ." "$RUFF" format --check .
run_step "git_diff_check" "git diff --check" git -C "$REPO_ROOT" diff --check

formatter_log="$RUN_OUTPUT_DIR/logs/ruff_format_raw.log"
formatter_json="$RUN_OUTPUT_DIR/formatter_baseline_delta.json"
formatter_delta_log="$RUN_OUTPUT_DIR/logs/formatter_baseline_delta.log"
raw_formatter_rc="$(awk -F '\t' '$1 == "ruff_format_raw" { print $2 }' "$MANIFEST")"
"$PYTHON_BIN" - "$REPO_ROOT" "$formatter_log" "$formatter_json" "$raw_formatter_rc" > "$formatter_delta_log" 2>&1 <<'PY'
import json
import re
import sys
from pathlib import Path

root, raw_log, output = map(Path, sys.argv[1:4])
raw_exit_code = int(sys.argv[4])
baseline_path = root / "artifacts/pr_evidence/PR2-00/formatter_baseline.json"
baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
baseline_failures = set(baseline["baseline"]["failing_files"])
raw_text = raw_log.read_text(encoding="utf-8", errors="replace")
current_failures = set(re.findall(r"^Would reformat: (.+)$", raw_text, flags=re.MULTILINE))
new_failures = sorted(current_failures - baseline_failures)
resolved = sorted(baseline_failures - current_failures)
raw_result_consistent = (
    (raw_exit_code == 0 and not current_failures)
    or (raw_exit_code == 1 and bool(current_failures) and current_failures <= baseline_failures)
)
result = {
    "policy": "FORMAT-BASELINE-01",
    "baseline_subject": baseline["original_authorized_starting_subject"],
    "baseline_failures": sorted(baseline_failures),
    "current_failures": sorted(current_failures),
    "new_format_failures": new_failures,
    "resolved_inherited_failures": resolved,
    "raw_formatter_exit_code": raw_exit_code,
    "raw_result_consistent_with_baseline": raw_result_consistent,
    "gate": "PASS" if not new_failures and raw_result_consistent else "FAIL",
}
output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"RAW_FORMATTER_FILES={len(current_failures)}")
print(f"NEW_FORMATTER_FAILURES={len(new_failures)}")
print("FORMATTER_BASELINE_DELTA_GATE=" + result["gate"])
raise SystemExit(0 if not new_failures else 1)
PY
formatter_delta_rc=$?
record_check "formatter_baseline_delta" "$formatter_delta_rc" "compare raw ruff failures with accepted FORMAT-BASELINE-01 baseline" "$formatter_delta_log"

phase1_log="$RUN_OUTPUT_DIR/logs/phase1_non_drift.log"
phase1_rc=0
phase1_paths="$(git -C "$REPO_ROOT" ls-tree -r --name-only "$PHASE1_BASELINE" -- migrations/versions)"
for path in $phase1_paths; do
  if ! git -C "$REPO_ROOT" diff --quiet "$PHASE1_BASELINE" HEAD -- "$path"; then
    printf 'Phase 1 migration changed: %s\n' "$path" >> "$phase1_log"
    phase1_rc=1
  fi
done
if [ "$phase1_rc" -eq 0 ]; then printf 'PHASE1_MIGRATION_DRIFT=NO\n' > "$phase1_log"; PHASE1_MIGRATION_DRIFT="NO"; else PHASE1_MIGRATION_DRIFT="YES"; fi
record_check "phase1_non_drift" "$phase1_rc" "verify phase1-final-v4 and historical migration file identity" "$phase1_log"

final_rc=0
while IFS="$(printf '\t')" read -r check_id check_rc check_command check_log; do
  [ -n "$check_id" ] || continue
  if [ "$check_rc" -ne 0 ] && [ "$check_id" != "ruff_format_raw" ]; then final_rc=1; fi
done < "$MANIFEST"
if [ "$formatter_delta_rc" -ne 0 ] || [ "$PR2_00_TEMPORAL_STATUS" != "NO_RESIDUAL_REPRODUCED" ]; then final_rc=1; fi
exit "$final_rc"
