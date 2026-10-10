#!/usr/bin/env bash
set -uo pipefail

REPO="/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/f2-p1-remediation"
EXPECTED_BRANCH="recovery/f2-p1-remediation"
EXPECTED_HEAD=""
readonly RECOVERY_COMPARISON_BASE="14143dc09983ce1765b3b39fda536691193fd868"
readonly FROZEN_CONTRACT="ea216c9babea322808b3885f563d276b571575ab"
readonly EXPECTED_MIGRATION="0025_pr2_04_reservation_guards"
PG_BIN="${PG_BIN:-}"
POSTGRES_VERSION="${POSTGRES_VERSION:-}"
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) printf 'ERROR: unsupported argument: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

# Candidate selection is exclusively a dry-run input. Live host verification
# retains its fixed checkout/branch and all original evidence/runtime gates.
if [ "${PR204_DRY_RUN_REPO+x}${PR204_DRY_RUN_EXPECTED_BRANCH+x}${PR204_DRY_RUN_EXPECTED_HEAD+x}" != "" ]; then
  if [ "$DRY_RUN" -ne 1 ]; then
    printf 'ERROR: candidate overrides require --dry-run\n' >&2; exit 2
  fi
  if [ "${PR204_DRY_RUN_REPO+x}${PR204_DRY_RUN_EXPECTED_BRANCH+x}${PR204_DRY_RUN_EXPECTED_HEAD+x}" != "xxx" ]; then
    printf 'ERROR: all three dry-run candidate overrides are required\n' >&2; exit 2
  fi
  if [[ "$PR204_DRY_RUN_REPO" != /* ]] || [ -z "$PR204_DRY_RUN_EXPECTED_BRANCH" ] ||
     [[ ! "$PR204_DRY_RUN_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]]; then
    printf 'ERROR: invalid dry-run candidate inputs\n' >&2; exit 2
  fi
  REPO="$PR204_DRY_RUN_REPO"
  EXPECTED_BRANCH="$PR204_DRY_RUN_EXPECTED_BRANCH"
  EXPECTED_HEAD="$PR204_DRY_RUN_EXPECTED_HEAD"
fi
readonly REPO EXPECTED_BRANCH EXPECTED_HEAD

cd "$REPO" || exit 2
HEAD="$(git rev-parse HEAD 2>/dev/null)" || exit 2
BRANCH="$(git branch --show-current)" || exit 2
if [ -n "$EXPECTED_HEAD" ] && [ "$HEAD" != "$EXPECTED_HEAD" ]; then
  printf 'CHECK expected_head FAIL\n'; exit 2
fi
if [ "$BRANCH" != "$EXPECTED_BRANCH" ]; then
  printf 'CHECK branch FAIL\n'; exit 2
fi
# A02: FROZEN_CONTRACT remains a historical identifier, not recovered ancestry.
if ! python3 scripts/pr2_04_recovery_bindings.py; then
  printf 'CHECK explicit_recovery_content_binding FAIL\n'; exit 2
fi
if [ "$DRY_RUN" -eq 1 ]; then
  printf 'MODE=pr2-04-verification\nEXECUTION_HEAD=%s\nFROZEN_CONTRACT_SHA=%s\n' "$HEAD" "$FROZEN_CONTRACT"
  printf 'EXPECTED_BRANCH=%s\nEXPECTED_MIGRATION=%s\n' "$EXPECTED_BRANCH" "$EXPECTED_MIGRATION"
  printf 'REQUIRED_GATES=postgres18,phase1_non_drift,prior_pr_regression,migration0024,focused_pr204,full_suite,ruff,pyright,formatter_delta,diff_check,matrix_65\n'
  python3 scripts/pr2_04_recovery_static_gates.py lineage || exit 2
  exit 0
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="artifacts/pr_evidence/PR2-04/host-review-runs/$RUN_ID"
RUN_STARTED_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
mkdir -p "$OUT/logs" || exit 2
RUN_TMP=""
PGDATA=""
PGLOG=""
PORT=""
SERVER_STARTED=0
OVERALL=0
MATRIX_WRITTEN=0
declare -a CHECKS=()

record() {
  local name="$1" status="$2" command="$3"
  CHECKS+=("$name|$status|$command")
  printf '%s|%s|%s\n' "$name" "$status" "$command" >> "$OUT/checks.txt"
  printf 'CHECK %s %s\n' "$name" "$status"
  [ "$status" = PASS ] || [ "$status" = INHERITED ] || [ "$status" = BLOCKED ] || OVERALL=1
}

cleanup() {
  local rc=$?
  local run_finished_utc
  run_finished_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  trap - EXIT INT TERM
  local cleanup_status=PASS
  if [ "$SERVER_STARTED" -eq 1 ]; then
    if ! "$PG_BIN/pg_ctl" -D "$PGDATA" stop -m fast -w > "$OUT/logs/postgres_stop.log" 2>&1; then
      cleanup_status=FAIL
      OVERALL=1
    fi
  fi
  if [ -n "$RUN_TMP" ] && [ -d "$RUN_TMP" ]; then
    rm -rf -- "$RUN_TMP"
  fi
  if [ "$MATRIX_WRITTEN" -eq 0 ]; then
    uv run python -m scripts.pr2_04_verification_matrix --head "$HEAD" --run-id "$RUN_ID" --output "$OUT/verification_matrix_result.json" \
      > "$OUT/logs/matrix.log" 2>&1 || OVERALL=1
  fi
  python3 - "$OUT" "$HEAD" "$FROZEN_CONTRACT" "$POSTGRES_VERSION" "$RUN_ID" "$cleanup_status" "$OVERALL" "$RUN_STARTED_UTC" "$run_finished_utc" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
out=Path(sys.argv[1])
checks=[]
for line in (out/"checks.txt").read_text().splitlines() if (out/"checks.txt").exists() else []:
    name,status,command=line.split("|",2)
    checks.append({"id":name,"status":status,"command":command})
matrix=json.loads((out/"verification_matrix_result.json").read_text()) if (out/"verification_matrix_result.json").exists() else None
def junit(path, log_path):
    if not path.exists(): return None
    import xml.etree.ElementTree as ET
    cases=list(ET.parse(path).getroot().iter("testcase"))
    failed=sum(c.find("failure") is not None for c in cases)
    errors=sum(c.find("error") is not None for c in cases)
    skipped=sum(c.find("skipped") is not None for c in cases)
    import re
    log=log_path.read_text(errors="replace") if log_path.exists() else ""
    warning_counts=re.findall(r"\b(\d+) warnings?\b",log)
    return {"collected":len(cases),"passed":len(cases)-failed-errors-skipped,"failed":failed,"errors":errors,"skipped":skipped,"warnings":int(warning_counts[-1]) if warning_counts else 0}
version_path=out/"logs/postgres_version.log"
summary={"schema_version":"pr2-04-host-review-v1","run_id":sys.argv[5],"execution_head":sys.argv[2],"frozen_contract_sha":sys.argv[3],"postgres_version":sys.argv[4] or None,"postgres_version_text":version_path.read_text().strip() if version_path.exists() else None,"started_at_utc":sys.argv[8],"finished_at_utc":sys.argv[9],"accepted_baseline":None,"recovery_comparison_baseline":"14143dc09983ce1765b3b39fda536691193fd868","original_history_recovered":False,"historical_lineage":next((c["status"] for c in checks if c["id"]=="frozen_contract_lineage"),"NOT_RUN"),"cleanup":sys.argv[6],"checks":checks,"focused_counts":junit(out/"logs/focused.xml",out/"logs/focused.log"),"full_suite_counts":junit(out/"logs/full_suite.xml",out/"logs/full_suite.log"),"verification_matrix":matrix,"status":"PASS" if sys.argv[7]=="0" and matrix and matrix.get("counts",{}).get("PASS")==65 else "BLOCKED_OR_FAIL"}
(out/"host_review_result.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
(out/"host_review_result.md").write_text("# PR2-04 host verification\n\n"+"\n".join(f"- {c['id']}: {c['status']} — `{c['command']}`" for c in checks)+f"\n\nMatrix: `{summary['verification_matrix'].get('counts') if summary['verification_matrix'] else 'missing'}`\n")
digests={str(path.relative_to(out)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(out.rglob("*")) if path.is_file() and path.name!="artifact_sha256.json"}
(out/"artifact_sha256.json").write_text(json.dumps({"execution_head":sys.argv[2],"sha256":digests},indent=2,sort_keys=True)+"\n")
PY
  if [ "$rc" -ne 0 ] || [ "$OVERALL" -ne 0 ]; then exit 1; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
: > "$OUT/checks.txt"

TRACKED_STATE="$(python3 - <<'PY'
import subprocess
rows=subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],text=True).splitlines()
state="CLEAN"
for row in rows:
    code=row[:2]
    path=row[3:]
    if code=="??" and path.startswith("artifacts/pr_evidence/"):
        state="CLEAN_WITH_EVIDENCE"
    else:
        state="DIRTY"
        break
print(state)
PY
)"
record candidate_cleanliness "$([ "$TRACKED_STATE" != DIRTY ] && echo PASS || echo FAIL)" "tracked tree clean; only artifacts/pr_evidence untracked ($TRACKED_STATE)"
record postgres18_binary "$([ -n "$PG_BIN" ] && [ -x "$PG_BIN/postgres" ] && [[ "$POSTGRES_VERSION" == 18.* ]] && echo PASS || echo FAIL)" "PostgreSQL 18 binary and version"
python3 scripts/pr2_04_recovery_static_gates.py lineage > "$OUT/recovery_lineage.json" 2> "$OUT/logs/recovery_lineage.log"
lineage_rc=$?
if [ "$lineage_rc" -ne 0 ]; then
  record recovery_baseline_lineage FAIL "recovery baseline prerequisite or comparison failed"
  record frozen_contract_lineage NOT_RUN "historical ancestry prerequisite not established"
  exit 2
fi
historical_lineage_status="$(python3 - "$OUT/recovery_lineage.json" <<'PY_STATUS'
import json,sys
print(json.load(open(sys.argv[1]))["historical_lineage"]["status"])
PY_STATUS
)" || exit 2
record recovery_baseline_lineage PASS "verified actual recovery comparison $RECOVERY_COMPARISON_BASE..$HEAD; not historical ancestry"
record frozen_contract_lineage "$historical_lineage_status" "actual historical object/ancestry status; see recovery_lineage.json"
record phase1_migration_non_drift "$(git diff --quiet d2400fbeca835c89bd802a4e9d647bda01cfd115 "$HEAD" -- migrations/versions/000*.py migrations/versions/001[0-8]*.py && echo PASS || echo FAIL)" "compare frozen Phase 1 migration files"

if [ "$TRACKED_STATE" = DIRTY ] || [ -z "$PG_BIN" ] || [ ! -x "$PG_BIN/initdb" ] || [[ "$POSTGRES_VERSION" != 18.* ]]; then
  record postgres_runtime BLOCKED "candidate must be committed/clean and PostgreSQL 18 binaries available"
  exit 2
fi

export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
RUN_TMP="$(mktemp -d /private/tmp/researchbase-pr2-04-host.XXXXXX)" || exit 2
PGDATA="$RUN_TMP/data"
PGLOG="$RUN_TMP/postgres.log"
PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
set +e
"$PG_BIN/initdb" -D "$PGDATA" --username=researchbase --auth=trust > "$OUT/logs/initdb.log" 2>&1
init_rc=$?
record postgres_initdb "$([ "$init_rc" -eq 0 ] && echo PASS || echo BLOCKED)" "initdb isolated PostgreSQL 18 cluster"
if [ "$init_rc" -ne 0 ]; then exit 2; fi
"$PG_BIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -o "-h 127.0.0.1 -p $PORT -c timezone=UTC" start > "$OUT/logs/postgres_start.log" 2>&1
start_rc=$?
record postgres_start "$([ "$start_rc" -eq 0 ] && echo PASS || echo BLOCKED)" "start isolated PostgreSQL 18 cluster"
if [ "$start_rc" -ne 0 ]; then exit 2; fi
SERVER_STARTED=1
for attempt in $(seq 1 30); do "$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PORT" -U researchbase >/dev/null 2>&1 && break; sleep 1; done
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_review > "$OUT/logs/createdb.log" 2>&1
db_rc=$?
record postgres_database "$([ "$db_rc" -eq 0 ] && echo PASS || echo FAIL)" "create isolated review database"
if [ "$db_rc" -ne 0 ]; then exit 2; fi
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_phase1_review > "$OUT/logs/createdb_phase1.log" 2>&1
phase1_db_rc=$?
record phase1_database "$([ "$phase1_db_rc" -eq 0 ] && echo PASS || echo FAIL)" "create isolated Phase 1 regression database"
if [ "$phase1_db_rc" -ne 0 ]; then exit 2; fi
export DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_review"
export PHASE1_DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_phase1_review"
"$PG_BIN/psql" -h 127.0.0.1 -p "$PORT" -U researchbase -d researchbase_review -Atc 'select version()' > "$OUT/logs/postgres_version.log" 2>&1
version_rc=$?
record postgres_version_query "$([ "$version_rc" -eq 0 ] && echo PASS || echo FAIL)" "PostgreSQL SELECT version()"
if [ "$version_rc" -ne 0 ]; then exit 2; fi
DATABASE_URL="$PHASE1_DATABASE_URL" uv run alembic upgrade 0018_current_pointer_same_parent_integrity > "$OUT/logs/phase1_migration.log" 2>&1
phase1_migration_rc=$?
record phase1_migration "$([ "$phase1_migration_rc" -eq 0 ] && echo PASS || echo FAIL)" "alembic upgrade frozen Phase 1 boundary 0018"
if [ "$phase1_migration_rc" -ne 0 ]; then exit 2; fi
export RB_EXECUTION_HEAD="$HEAD" RB_FROZEN_CONTRACT_SHA="$FROZEN_CONTRACT" RB_POSTGRES_VERSION="$POSTGRES_VERSION"

uv run alembic upgrade "$EXPECTED_MIGRATION" > "$OUT/logs/migration_upgrade.log" 2>&1
rc=$?; record migration0024 "$([ "$rc" -eq 0 ] && echo PASS || echo FAIL)" "uv run alembic upgrade $EXPECTED_MIGRATION"
uv run alembic heads > "$OUT/logs/alembic_heads.log" 2>&1
heads_rc=$?; head_count="$(grep -c '(head)' "$OUT/logs/alembic_heads.log" || true)"
record unique_alembic_head "$([ "$heads_rc" -eq 0 ] && [ "$head_count" = 1 ] && grep -F "$EXPECTED_MIGRATION (head)" "$OUT/logs/alembic_heads.log" >/dev/null && echo PASS || echo FAIL)" "uv run alembic heads"
PR204_EVIDENCE_DIR="$REPO/$OUT/evidence" PR204_RUN_ID="$RUN_ID" PR204_CANDIDATE_HEAD="$HEAD" \
  uv run pytest -q tests/unit tests/integration/phase2 --junitxml="$OUT/logs/focused.xml" > "$OUT/logs/focused.log" 2>&1
focused_rc=$?; record focused_pr204_and_prior_regressions "$([ "$focused_rc" -eq 0 ] && echo PASS || echo FAIL)" "uv run pytest tests/unit tests/integration/phase2"
uv run python -m scripts.pr2_04_evidence --head "$HEAD" --run-id "$RUN_ID" \
  --bindings scripts/pr2_04_requirement_bindings.json \
  --ledger "$OUT/evidence/pytest_ledger.json" --junit "$OUT/logs/focused.xml" \
  --output "$OUT/evidence/run_manifest.json" --acceptance-output "$OUT/acceptance_results.json" \
  > "$OUT/logs/evidence_producer.log" 2>&1
evidence_rc=$?; record evidence_producer "$([ "$evidence_rc" -eq 0 ] && echo PASS || echo FAIL)" "validate marked exact test nodes, observed facts, run bindings and artifact digests"
uv run pytest -q --junitxml="$OUT/logs/full_suite.xml" > "$OUT/logs/full_suite.log" 2>&1
full_rc=$?; record full_suite "$([ "$full_rc" -eq 0 ] && echo PASS || echo FAIL)" "uv run pytest -q"
uv run ruff check src migrations tests scripts > "$OUT/logs/ruff.log" 2>&1
lint_rc=$?; record ruff "$([ "$lint_rc" -eq 0 ] && echo PASS || echo FAIL)" "uv run ruff check src migrations tests scripts"
uv run pyright > "$OUT/logs/pyright.log" 2>&1
type_rc=$?; record pyright "$([ "$type_rc" -eq 0 ] && echo PASS || echo FAIL)" "uv run pyright"
uv run ruff format --check . > "$OUT/logs/formatter_raw.log" 2>&1
raw_format_rc=$?
record formatter_raw "$([ "$raw_format_rc" -eq 0 ] && echo PASS || echo INHERITED)" "uv run ruff format --check . (raw result; delta gate follows)"
python3 scripts/pr2_04_recovery_static_gates.py formatter > "$OUT/logs/formatter_changed_scope.log" 2>&1
changed_format_rc=$?
record formatter_changed_scope "$([ "$changed_format_rc" -eq 0 ] && echo PASS || echo FAIL)" "verified recovery baseline $RECOVERY_COMPARISON_BASE..$HEAD; ruff format --check every extant changed Python file"
python3 - "$OUT/logs/formatter_raw.log" "$OUT/formatter_baseline_delta.json" "$raw_format_rc" <<'PY'
import json,re,sys
from pathlib import Path
raw_path,out_path=map(Path,sys.argv[1:3]); raw_rc=int(sys.argv[3])
baseline_path=Path("artifacts/pr_evidence/PR2-00/formatter_baseline.json")
baseline=set(json.loads(baseline_path.read_text())["baseline"]["failing_files"])
text=raw_path.read_text(errors="replace")
current=set(re.findall(r"^Would reformat: (.+)$",text,re.M))
new=sorted(current-baseline)
consistent=(raw_rc==0 and not current) or (raw_rc!=0 and bool(current) and current<=baseline)
result={"policy":"FORMAT-BASELINE-01","raw_exit_code":raw_rc,"baseline_failures":sorted(baseline),"current_failures":sorted(current),"new_failures":new,"gate":"PASS" if not new and consistent else "FAIL"}
out_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
raise SystemExit(0 if result["gate"]=="PASS" else 1)
PY
formatter_delta_rc=$?
record formatter_baseline_delta "$([ "$formatter_delta_rc" -eq 0 ] && echo PASS || echo FAIL)" "compare raw formatter failures with frozen FORMAT-BASELINE-01"
python3 scripts/pr2_04_recovery_static_gates.py diff-check > "$OUT/logs/diff_check.log" 2>&1
diff_rc=$?; record git_diff_check "$([ "$diff_rc" -eq 0 ] && echo PASS || echo FAIL)" "git diff --check recovery baseline $RECOVERY_COMPARISON_BASE..$HEAD"

# A result index is created only by explicit test/evidence instrumentation. A command summary
# alone never advances requirement rows from NOT_RUN.
if [ -f "$OUT/evidence/run_manifest.json" ] && [ -f "$OUT/acceptance_results.json" ]; then
  uv run python -m scripts.pr2_04_verification_matrix --head "$HEAD" --run-id "$RUN_ID" \
    --run-manifest "$OUT/evidence/run_manifest.json" --results "$OUT/acceptance_results.json" \
    --output "$OUT/verification_matrix_result.json" > "$OUT/logs/matrix.log" 2>&1
else
  uv run python -m scripts.pr2_04_verification_matrix --head "$HEAD" --run-id "$RUN_ID" \
    --output "$OUT/verification_matrix_result.json" > "$OUT/logs/matrix.log" 2>&1
fi
matrix_rc=$?
MATRIX_WRITTEN=1
matrix_status="FAIL"
if [ "$matrix_rc" -eq 0 ]; then
  matrix_counts="$(python3 - "$OUT/verification_matrix_result.json" <<'PY'
import json,sys
print(json.dumps(json.load(open(sys.argv[1]))["counts"],sort_keys=True))
PY
)"
  matrix_status="$(python3 - "$OUT/verification_matrix_result.json" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))["counts"]
print("PASS" if c=={"BLOCKED":0,"FAIL":0,"NOT_RUN":0,"PASS":65} else "BLOCKED" if c["FAIL"]==0 else "FAIL")
PY
)"
else
  matrix_counts="invalid"
fi
record verification_matrix "$matrix_status" "requirement-level result counts=$matrix_counts"
if [ "$OVERALL" -eq 0 ] && [ "$matrix_status" = PASS ]; then
  exit 0
fi
exit 1
