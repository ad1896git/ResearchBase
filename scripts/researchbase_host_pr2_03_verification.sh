#!/usr/bin/env bash
set -uo pipefail

readonly REPO="/private/tmp/ResearchBase-phase2-recovered"
readonly PG_BIN="${PG_BIN:-}"
readonly POSTGRES_VERSION="${POSTGRES_VERSION:-}"
readonly PYTHON="/Users/onephone/Documents/Codex/ResearchBase/.venv/bin/python"
readonly TOOLS="/Users/onephone/Documents/Codex/ResearchBase/.venv/bin"
readonly EXPECTED_BRANCH="phase2/entry-gate"
readonly IMPLEMENTATION="14e3aaeaea8f3673a7672f07a98a6fc37ac7b9fc"
readonly DESIGN="8c4355b7b8f25450a97436c1989e254c023ad34e"
readonly PHASE1="d2400fbeca835c89bd802a4e9d647bda01cfd115"
RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$$"
OUT="$REPO/artifacts/pr_evidence/PR2-03/host-review-runs/$RUN_ID"
RUN_TMP=""
PGDATA=""
PGLOG=""
PORT=""
STARTED=0
FAIL=0
DRY_RUN=0
declare -a RESULTS=()

record() {
  local name="$1" code="$2" command="$3"
  RESULTS+=("$name|$code|$command")
  printf '%s|%s|%s\n' "$name" "$code" "$command" >> "$OUT/checks.txt"
  printf 'CHECK %s %s\n' "$name" "$([ "$code" -eq 0 ] && echo PASS || echo FAIL)"
  if [ "$code" -ne 0 ] && [ "$name" != "formatter_raw" ]; then FAIL=1; fi
}

cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  if [ "$STARTED" -eq 1 ]; then
    if "$PG_BIN/pg_ctl" -D "$PGDATA" stop -m fast -w > "$OUT/logs/postgres_stop.log" 2>&1; then
      cleanup_status="PASS_SERVER_STOPPED"
    else
      cleanup_status="FAIL_SERVER_STOP"
      FAIL=1
    fi
  else
    cleanup_status="PASS_SERVER_NOT_STARTED"
  fi
  [ -n "$RUN_TMP" ] && [ -d "$RUN_TMP" ] && rm -rf -- "$RUN_TMP"
  RB_CLEANUP="$cleanup_status" "$PYTHON" - "$OUT" "$RUN_ID" "$FAIL" <<'PY'
import json, os, sys
import re
from pathlib import Path
import xml.etree.ElementTree as ET
out=Path(sys.argv[1]); run_id=sys.argv[2]; failed=int(sys.argv[3])
checks=[]
for line in (out/"checks.txt").read_text().splitlines():
    name, code, command=line.split("|",2)
    checks.append({"id":name,"exit_code":int(code),"status":"PASS" if code=="0" else "FAIL","command":command})
def counts(name):
    path=out/"logs"/name
    if not path.exists(): return None
    root=ET.parse(path).getroot(); cases=list(root.iter("testcase"))
    result={"collected":len(cases),"passed":0,"failed":0,"skipped":0,"errors":0}
    for case in cases:
        if case.find("error") is not None: result["errors"]+=1
        elif case.find("failure") is not None: result["failed"]+=1
        elif case.find("skipped") is not None: result["skipped"]+=1
        else: result["passed"]+=1
    return result
full=counts("full_suite.xml"); focused=counts("focused.xml"); temporal=counts("temporal.xml")
concurrency=counts("concurrency.xml"); idempotency=counts("idempotency.xml")
warnings=0
suite_log=out/"logs/full_suite.log"
if suite_log.exists():
    import re
    matches=re.findall(r"\b(\d+) warnings?\b",suite_log.read_text(errors="replace"))
    warnings=int(matches[-1]) if matches else 0
raw=(out/"logs/formatter_raw.log").read_text(errors="replace") if (out/"logs/formatter_raw.log").exists() else ""
raw_files=re.findall(r"^Would reformat: (.+)$",raw,re.M)
delta=json.loads((out/"formatter_delta.json").read_text()) if (out/"formatter_delta.json").exists() else None
temporal_trace=json.loads((out/"temporal_trace.json").read_text()) if (out/"temporal_trace.json").exists() else None
required_xml = ['focused.xml','concurrency.xml','idempotency.xml','temporal.xml'] + [c['id']+'.xml' for c in checks if c['id'].startswith('pr2_03_') and c['id'] not in {'pr2_03_concurrency','pr2_03_idempotency'}]
missing_or_skipped = [name for name in required_xml if not counts(name) or counts(name)['collected']==0 or counts(name)['skipped'] or counts(name)['failed'] or counts(name)['errors']]
if missing_or_skipped: failed=1
matrix=json.loads(Path("/private/tmp/ResearchBase-phase2-recovered/execution/phase2/PR2-03_Verification_Matrix.json").read_text())
observations=[]
for xml_path in (out/"logs").glob("*.xml"):
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        observations.append((case.get("classname", ""),case.get("name", ""),case))
for row in matrix["rows"]:
    check=next((c for c in checks if c["id"]==row["host_check"]),None)
    node_results=[]
    for node in row["tests"]:
        file,name=node.split("::",1)
        module=file.removesuffix(".py").replace("/", ".")
        exact="[" in name
        matches=[case for classname,case_name,case in observations if classname==module and (case_name==name if exact else case_name==name or case_name.startswith(name+"["))]
        if not matches:
            status="NOT_RUN"
        elif any(case.find("failure") is not None or case.find("error") is not None for case in matches):
            status="FAIL"
        elif any(case.find("skipped") is not None for case in matches):
            status="BLOCKED"
        else:
            status="PASS"
        node_results.append({"node":node,"observations":len(matches),"status":status})
    row["node_results"]=node_results
    if node_results:
        statuses={n["status"] for n in node_results}
        row["result"]="PASS" if statuses=={"PASS"} else "FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "NOT_RUN"
    else:
        row["result"]="PASS" if check and check["status"]=="PASS" else "FAIL" if check else "NOT_RUN"
if any(row["result"]!="PASS" for row in matrix["rows"]): failed=1
matrix["execution_head"]=os.getenv("RB_EXECUTION_HEAD")
(out/"verification_matrix_result.json").write_text(json.dumps(matrix,indent=2)+"\n")
result={"required_xml_missing_or_skipped":missing_or_skipped,"run_id":run_id,"mode":"pr2-03-verification","result_role":"host execution evidence only; no reviewer verdict",
 "implementation_sha":os.getenv("RB_IMPLEMENTATION_SHA"),"design_subject":"8c4355b7b8f25450a97436c1989e254c023ad34e",
 "phase1_baseline":"d2400fbeca835c89bd802a4e9d647bda01cfd115","postgres_version":os.getenv("RB_PG_VERSION"),
 "expected_migration_head":"0023a_search_plan_review_guards",
 "phase2_migration_head":"0023a_search_plan_review_guards" if any(c["id"]=="migration_current_0023a" and c["status"]=="PASS" for c in checks) else None,
 "execution_head":os.getenv("RB_EXECUTION_HEAD"),"execution_branch":os.getenv("RB_EXECUTION_BRANCH"),
 "tracked_state":os.getenv("RB_TRACKED_STATE"),"production_subject":os.getenv("RB_EXECUTION_HEAD"),"database":"researchbase_review",
 "cleanup":os.getenv("RB_CLEANUP"),"checks":checks,"focused_counts":focused,"temporal_counts":temporal,
 "pr2_03_concurrency_counts":concurrency,"pr2_03_idempotency_counts":idempotency,
 "full_suite_counts":({**full,"warnings":warnings} if full is not None else None),"temporal_trace":temporal_trace,
 "PR2_00_TEMPORAL_RESIDUAL_REOPENED":"YES" if temporal_trace and (temporal_trace["successful_post_expiry_consumption"] or temporal_trace["protected_post_expiry_effects"]) else "NO" if temporal_trace and all(temporal_trace["checks"].values()) else "INCONCLUSIVE",
 "formatter":{"raw_exit_code":next((c["exit_code"] for c in checks if c["id"]=="formatter_raw"),None),"raw_failures":raw_files,"baseline_delta":delta},
 "log_files":sorted(p.name for p in (out/"logs").iterdir()),
 "verification_gate":"PASS" if not failed else "FAIL",
 "P0":None,"P1":None,"P2":None,"verdict":"NOT_ISSUED_INDEPENDENT_REVIEW_REQUIRED"}
(out/"host_review_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
lines=["# PR2-03 Host Verification","",f"Run: `{run_id}`","","Role: host DB execution evidence only; independent reviewer verdict not issued.",
 f"Implementation: `{result['implementation_sha']}`",f"Design: `{result['design_subject']}`",
 f"PostgreSQL: `{result['postgres_version']}`; database: `{result['database']}`; migration head: `{result['phase2_migration_head']}`",
 f"Focused counts: `{focused}`",f"Concurrency counts: `{concurrency}`",
 f"Idempotency counts: `{idempotency}`",f"Temporal counts: `{temporal}`",f"Full-suite counts: `{full}`",
 f"Temporary cluster cleanup: `{result['cleanup']}`","","## Checks",""]
for c in checks: lines.append(f"- `{c['id']}`: **{c['status']}** — `{c['command']}`")
lines += ["",f"Verification gate: **{result['verification_gate']}**"]
(out/"host_review_result.md").write_text("\n".join(lines)+"\n")
raise SystemExit(1 if failed else 0)
PY
  if [ "$?" -ne 0 ]; then FAIL=1; fi
  exit "$((FAIL == 0 && rc == 0 ? 0 : 1))"
}

mkdir -p "$OUT/logs" || exit 2
: > "$OUT/checks.txt"
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=1; fi
if [ -z "$PG_BIN" ] || [ ! -x "$PG_BIN/postgres" ] || [ -z "$POSTGRES_VERSION" ]; then
  printf 'CHECK postgres18_binary FAIL\nHOST_POSTGRESQL_18_UNAVAILABLE\n' >&2
  exit 2
fi
record postgres18_binary 0 "parent runner validated PostgreSQL $POSTGRES_VERSION at $PG_BIN"
cd "$REPO" || exit 2
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
if [ "$(git branch --show-current)" != "$EXPECTED_BRANCH" ] || ! git merge-base --is-ancestor "$DESIGN" HEAD; then
  printf 'Repository branch or immutable design ancestry mismatch.\n' >&2; exit 2
fi
git merge-base --is-ancestor "$IMPLEMENTATION" HEAD || {
  printf 'PR2-03 implementation subject is absent from current history.\n' >&2; exit 2;
}
export RB_EXECUTION_HEAD="$(git rev-parse HEAD)"
export RB_EXECUTION_BRANCH="$(git branch --show-current)"
RB_TRACKED_STATE="$(if git diff --quiet && git diff --cached --quiet; then echo CLEAN; else echo DIRTY; fi)"
export RB_TRACKED_STATE
if [ "$DRY_RUN" -ne 1 ] && [ "$RB_TRACKED_STATE" != CLEAN ]; then
  printf 'Host verification requires a committed, clean tracked subject.\n' >&2; exit 2
fi
git diff --quiet "$IMPLEMENTATION" HEAD -- migrations/versions/0023_literature_search_plan.py || exit 2
tag_commit="$(git rev-parse 'phase1-final-v4^{commit}')"
[ "$tag_commit" = "$PHASE1" ] || { printf 'Frozen Phase 1 tag mismatch.\n' >&2; exit 2; }
git diff --quiet "$PHASE1" -- 'migrations/versions/000*.py' 'migrations/versions/001[0-8]*.py' || {
  printf 'Frozen Phase 1 migrations drifted.\n' >&2; exit 2;
}
record phase1_non_drift 0 'phase1-final-v4 and historical Phase 1 migrations unchanged'
acceptance_path="$(git grep -l -F 'PR2_02_ACCEPTED = YES' HEAD -- artifacts/pr_evidence/PR2-02 2>/dev/null || true)"
acceptance_valid=1
if [ -z "$acceptance_path" ] || [ "$(printf '%s\n' "$acceptance_path" | wc -l | tr -d ' ')" -ne 1 ]; then
  acceptance_valid=0
else
  acceptance_path="${acceptance_path#HEAD:}"
  acceptance_text="$(git show "HEAD:$acceptance_path" 2>/dev/null || true)"
  for required in \
    'PR2_02_ACCEPTED = YES' \
    '3de5e897cc72de3e4c4f7b86d83ed8ae2b13fc93' \
    'a8fd1fef2475b12c50e6f18a4aaa6d9b0e663d02' \
    '20261004T092722Z-79123' \
    '18.6 (Homebrew)' \
    'Host verification gate: `PASS`' \
    'Reviewer identity/context:' \
    'NEW_P0_GAPS = 0' \
    'NEW_P1_GAPS = 0' \
    'NEW_P2_GAPS = 0' \
    'Verdict: `PASS`'; do
    printf '%s\n' "$acceptance_text" | grep -F "$required" >/dev/null || acceptance_valid=0
  done
fi
if [ "$acceptance_valid" -ne 1 ]; then
  record durable_pr2_02_acceptance 1 'validate tracked PR2-02 acceptance artifact, host run, subjects, independent verdict and zero findings'
  printf 'PR2_02_DURABLE_ACCEPTANCE_MISSING\n' >&2
  exit 2
fi
record durable_pr2_02_acceptance 0 "tracked acceptance artifact $acceptance_path binds required subjects and independent PASS"
if [ "$DRY_RUN" -eq 1 ]; then
  printf 'DRY_RUN=YES\nMODE=pr2-03-verification\nDURABLE_PR2_02_ACCEPTANCE=PASS\nIMPLEMENTATION=%s\nPLANNED_MIGRATION_HEAD=0023a_search_plan_review_guards\n' "$IMPLEMENTATION"
  trap - EXIT INT TERM
  exit 0
fi
"$PYTHON" -c 'import sqlalchemy, psycopg, pytest' || exit 2
implementation_sha="$IMPLEMENTATION"
export RB_IMPLEMENTATION_SHA="$implementation_sha"
RUN_TMP="$(mktemp -d /private/tmp/researchbase-pr2-03-host.XXXXXX)" || exit 2
PGDATA="$RUN_TMP/data"
PGLOG="$RUN_TMP/postgres.log"
PORT="$("$PYTHON" -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
"$PG_BIN/initdb" -D "$PGDATA" --username=researchbase --auth=trust > "$OUT/logs/initdb.log" 2>&1
record initdb "$?" 'initdb isolated temporary PostgreSQL 18 cluster'
if [ "$FAIL" -ne 0 ]; then exit 1; fi
"$PG_BIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -o "-h 127.0.0.1 -p $PORT -c timezone=UTC" start > "$OUT/logs/pg_start.log" 2>&1
record postgres_start "$?" 'pg_ctl start isolated PostgreSQL 18 cluster'
if [ "$FAIL" -ne 0 ]; then exit 1; fi
STARTED=1
for attempt in $(seq 1 30); do
  if "$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PORT" -U researchbase > "$OUT/logs/pg_isready.log" 2>&1; then break; fi
  sleep 1
done
"$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PORT" -U researchbase >/dev/null 2>&1
record postgres_ready "$?" 'pg_isready localhost on selected temporary port'
if [ "$FAIL" -ne 0 ]; then cat "$PGLOG" >&2; exit 1; fi
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_review
record create_review_db "$?" 'createdb researchbase_review'
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_phase1_review
record create_phase1_db "$?" 'createdb researchbase_phase1_review'
export DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_review"
export PHASE1_DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_phase1_review"
"$PG_BIN/psql" -h 127.0.0.1 -p "$PORT" -U researchbase -d researchbase_review -Atc 'select version()' > "$OUT/logs/postgres_version.log"
RB_PG_VERSION="$(cat "$OUT/logs/postgres_version.log")"
export RB_PG_VERSION
"$TOOLS/alembic" upgrade 0023_literature_search_plan > "$OUT/logs/migration_upgrade_0023.log" 2>&1
record migration_upgrade_0023 "$?" 'alembic upgrade original PR2-03 boundary0023'
"$TOOLS/alembic" current > "$OUT/logs/migration_current_0023.log" 2>&1
grep -F '0023_literature_search_plan' "$OUT/logs/migration_current_0023.log" >/dev/null
record migration_current_0023 "$?" 'alembic current original PR2-03 boundary0023'
"$TOOLS/alembic" upgrade head > "$OUT/logs/migration_upgrade_0023a.log" 2>&1
record migration_upgrade_0023a "$?" 'alembic upgrade remediated PR2-03 head0023a'
"$TOOLS/alembic" current > "$OUT/logs/migration_current.log" 2>&1
grep -F '0023a_search_plan_review_guards' "$OUT/logs/migration_current.log" >/dev/null
record migration_current_0023a "$?" 'alembic current unique remediated Phase 2 head'
"$TOOLS/alembic" heads > "$OUT/logs/alembic_heads.log" 2>&1
head_count="$(grep -c '(head)' "$OUT/logs/alembic_heads.log" || true)"
[ "$head_count" = 1 ] && grep -F '0023a_search_plan_review_guards (head)' "$OUT/logs/alembic_heads.log" >/dev/null
record migration_unique_head "$?" 'alembic heads requires one remediated PR2-03 head'
DATABASE_URL="$PHASE1_DATABASE_URL" "$TOOLS/alembic" upgrade 0018_current_pointer_same_parent_integrity > "$OUT/logs/phase1_upgrade.log" 2>&1
record phase1_upgrade_0018 "$?" 'alembic upgrade to frozen Phase 1 boundary'
"$TOOLS/pytest" -o 'addopts=' -ra tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_01_source_identity.py --junitxml="$OUT/logs/focused.xml" > "$OUT/logs/focused.log" 2>&1
record focused_pr2_03 "$?" 'pytest PR2-03 migration + accepted PR2-01/02 PostgreSQL regressions'
"$TOOLS/pytest" -o 'addopts=' -ra tests/integration/phase2/test_pr2_03_literature_search_plan_concurrency.py --junitxml="$OUT/logs/concurrency.xml" > "$OUT/logs/concurrency.log" 2>&1
record pr2_03_concurrency "$?" 'pytest PR2-03 PostgreSQL freeze/edit/remove race invariants'
"$TOOLS/pytest" -o 'addopts=' -ra tests/integration/phase2/test_pr2_03_literature_search_plan_idempotency.py --junitxml="$OUT/logs/idempotency.xml" > "$OUT/logs/idempotency.log" 2>&1
record pr2_03_idempotency "$?" 'pytest PR2-03 PostgreSQL canonical command-key idempotency invariants'
run_review_check() {
  local check="$1"
  shift
  "$TOOLS/pytest" -o 'addopts=' -ra "$@" --junitxml="$OUT/logs/$check.xml" > "$OUT/logs/$check.log" 2>&1
  record "$check" "$?" "pytest $* (required, no skips)"
}
run_review_check pr2_03_effective_authority tests/integration/phase2/test_pr2_03_effective_authority.py
run_review_check pr2_03_db_guards tests/integration/phase2/test_pr2_03_review_guards.py
run_review_check pr2_03_identity_uniqueness tests/integration/phase2/test_pr2_03_review_guards.py::test_direct_question_identity_uniqueness_race
run_review_check pr2_03_http_validation tests/unit/phase2/test_search_plan_review_regressions.py::test_malformed_http_material_is_typed_422
run_review_check pr2_03_ordinal_determinism tests/integration/phase2/test_pr2_03_review_guards.py::test_ordinal_determinism_revision_supersession_and_hash
run_review_check pr2_03_schema_guards tests/integration/phase2/test_pr2_03_review_guards.py::test_objective_nonblank_database_check
run_review_check pr2_03_fk_indexes tests/integration/phase2/test_pr2_03_review_guards.py::test_required_fk_leading_indexes
run_review_check pr2_03_verification_matrix tests/integration/phase2/test_pr2_03_command_matrix.py tests/unit/phase2/test_search_plan_review_regressions.py
"$TOOLS/pytest" -o 'addopts=' -s tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait --junitxml="$OUT/logs/temporal.xml" > "$OUT/logs/temporal.log" 2>&1
record pr2_00_temporal "$?" 'pytest TEMP-AUTH lock-wait expiry boundary test'
if grep -F 'TEMP-AUTH challenge proof ' "$OUT/logs/temporal.log" > "$OUT/logs/temporal_proof_line.txt"; then
  "$PYTHON" - "$OUT/logs/temporal_proof_line.txt" "$OUT/temporal_trace.json" <<'PY' > "$OUT/logs/temporal_trace.log" 2>&1
import json,sys
from datetime import datetime,timedelta
from pathlib import Path
line=Path(sys.argv[1]).read_text().strip().splitlines()[-1]
p=json.loads(line.split("TEMP-AUTH challenge proof ",1)[1])
issued=datetime.fromisoformat(p["challenge_issued_at"]); expiry=datetime.fromisoformat(p["expiry_at"])
locked=datetime.fromisoformat(p["lock_acquired_at"]); authorized=datetime.fromisoformat(p["authorization_clock_timestamp"])
crossed=datetime.fromisoformat(p["expiry_crossed_at"]); released=datetime.fromisoformat(p["lock_released_at_observed"])
wait=p.get("observed_wait",{})
effects=p["persisted_effects"]
checks={"issued_before_expiry":issued<expiry,"postgres_lock_wait_observed":wait.get("wait_event_type")=="Lock",
 "expiry_elapsed_during_wait":crossed>=expiry+timedelta(milliseconds=250),
 "lock_acquired_after_expiry":locked>=expiry,"lock_released_after_expiry":released>=expiry,
 "fresh_authorization_after_lock":authorized>=locked,"authorization_after_expiry":authorized>=expiry,
 "denied":p.get("effect_result")=="DENY","challenge_unconsumed":effects.get("challenge_status")=="ISSUED",
 "zero_protected_effects":effects.get("bindings")==0 and effects.get("binding_events")==0}
result={"checks":checks,"successful_post_expiry_consumption":authorized>=expiry and effects.get("challenge_status")=="CONSUMED",
 "protected_post_expiry_effects":effects.get("bindings",0)>0 or effects.get("binding_events",0)>0}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("TEMPORAL_TRACE="+("PASS" if all(checks.values()) else "FAIL"))
raise SystemExit(0 if all(checks.values()) and not result["successful_post_expiry_consumption"] and not result["protected_post_expiry_effects"] else 1)
PY
  record temporal_trace "$?" 'assert lock-wait expiry, post-wait DB authorization denial and zero effects'
else
  printf 'TEMP-AUTH proof line missing\n' > "$OUT/logs/temporal_trace.log"
  record temporal_trace 1 'require complete TEMP-AUTH proof line'
fi
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_pr11_matrix
record create_pr11_matrix_db "$?" 'createdb isolated historical migration matrix database'
export PR11R2_MIGRATION_DB_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_pr11_matrix"
DATABASE_URL="$PHASE1_DATABASE_URL" "$TOOLS/pytest" -o 'addopts=' -ra --junitxml="$OUT/logs/full_suite.xml" > "$OUT/logs/full_suite.log" 2>&1
record full_suite "$?" 'pytest full suite with Phase 1 catalog boundary database'
"$TOOLS/ruff" check . > "$OUT/logs/ruff.log" 2>&1; record ruff "$?" 'ruff check .'
"$TOOLS/pyright" --venvpath /Users/onephone/Documents/Codex/ResearchBase > "$OUT/logs/pyright.log" 2>&1; record pyright "$?" 'pyright --venvpath ResearchBase'
"$TOOLS/ruff" format --check . > "$OUT/logs/formatter_raw.log" 2>&1; raw=$?; record formatter_raw "$raw" 'ruff format --check .'
"$PYTHON" - "$OUT/logs/formatter_raw.log" "$REPO/artifacts/pr_evidence/PR2-00/formatter_baseline.json" "$OUT/formatter_delta.json" <<'PY' > "$OUT/logs/formatter_delta.log" 2>&1
import json,re,sys
from pathlib import Path
raw,base,out=map(Path,sys.argv[1:])
baseline=set(json.loads(base.read_text())["baseline"]["failing_files"])
current=set(re.findall(r"^Would reformat: (.+)$",raw.read_text(errors="replace"),re.M))
new=sorted(current-baseline)
out.write_text(json.dumps({"baseline":sorted(baseline),"current":sorted(current),"new":new,"gate":"PASS" if not new else "FAIL"},indent=2)+"\n")
raise SystemExit(bool(new))
PY
record formatter_baseline_delta "$?" 'FORMAT-BASELINE-01 new-failure delta'
git diff --check > "$OUT/logs/diff_check.log" 2>&1; record git_diff_check "$?" 'git diff --check'
exit "$FAIL"
#!/usr/bin/env bash
set -uo pipefail

readonly REPO="/private/tmp/ResearchBase-phase2-recovered"
readonly PG_BIN="/opt/homebrew/opt/postgresql@18/bin"
readonly PYTHON="/Users/onephone/Documents/Codex/ResearchBase/.venv/bin/python"
readonly TOOLS="/Users/onephone/Documents/Codex/ResearchBase/.venv/bin"
readonly EXPECTED_BRANCH="phase2/entry-gate"
readonly IMPLEMENTATION="14e3aaeaea8f3673a7672f07a98a6fc37ac7b9fc"
readonly DESIGN="8c4355b7b8f25450a97436c1989e254c023ad34e"
readonly PHASE1="d2400fbeca835c89bd802a4e9d647bda01cfd115"
RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$$"
OUT="$REPO/artifacts/pr_evidence/PR2-03/host-review-runs/$RUN_ID"
RUN_TMP=""
PGDATA=""
PGLOG=""
PORT=""
STARTED=0
FAIL=0
DRY_RUN=0
declare -a RESULTS=()

record() {
  local name="$1" code="$2" command="$3"
  RESULTS+=("$name|$code|$command")
  printf '%s|%s|%s\n' "$name" "$code" "$command" >> "$OUT/checks.txt"
  printf 'CHECK %s %s\n' "$name" "$([ "$code" -eq 0 ] && echo PASS || echo FAIL)"
  if [ "$code" -ne 0 ] && [ "$name" != "formatter_raw" ]; then FAIL=1; fi
}

cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  if [ "$STARTED" -eq 1 ]; then
    if "$PG_BIN/pg_ctl" -D "$PGDATA" stop -m fast -w > "$OUT/logs/postgres_stop.log" 2>&1; then
      cleanup_status="PASS_SERVER_STOPPED"
    else
      cleanup_status="FAIL_SERVER_STOP"
      FAIL=1
    fi
  else
    cleanup_status="PASS_SERVER_NOT_STARTED"
  fi
  [ -n "$RUN_TMP" ] && [ -d "$RUN_TMP" ] && rm -rf -- "$RUN_TMP"
  RB_CLEANUP="$cleanup_status" "$PYTHON" - "$OUT" "$RUN_ID" "$FAIL" <<'PY'
import json, os, sys
import re
from pathlib import Path
import xml.etree.ElementTree as ET
out=Path(sys.argv[1]); run_id=sys.argv[2]; failed=int(sys.argv[3])
checks=[]
for line in (out/"checks.txt").read_text().splitlines():
    name, code, command=line.split("|",2)
    checks.append({"id":name,"exit_code":int(code),"status":"PASS" if code=="0" else "FAIL","command":command})
def counts(name):
    path=out/"logs"/name
    if not path.exists(): return None
    root=ET.parse(path).getroot(); cases=list(root.iter("testcase"))
    result={"collected":len(cases),"passed":0,"failed":0,"skipped":0,"errors":0}
    for case in cases:
        if case.find("error") is not None: result["errors"]+=1
        elif case.find("failure") is not None: result["failed"]+=1
        elif case.find("skipped") is not None: result["skipped"]+=1
        else: result["passed"]+=1
    return result
full=counts("full_suite.xml"); focused=counts("focused.xml"); temporal=counts("temporal.xml")
concurrency=counts("concurrency.xml"); idempotency=counts("idempotency.xml")
warnings=0
suite_log=out/"logs/full_suite.log"
if suite_log.exists():
    import re
    matches=re.findall(r"\b(\d+) warnings?\b",suite_log.read_text(errors="replace"))
    warnings=int(matches[-1]) if matches else 0
raw=(out/"logs/formatter_raw.log").read_text(errors="replace") if (out/"logs/formatter_raw.log").exists() else ""
raw_files=re.findall(r"^Would reformat: (.+)$",raw,re.M)
delta=json.loads((out/"formatter_delta.json").read_text()) if (out/"formatter_delta.json").exists() else None
temporal_trace=json.loads((out/"temporal_trace.json").read_text()) if (out/"temporal_trace.json").exists() else None
required_xml = ['focused.xml','concurrency.xml','idempotency.xml','temporal.xml'] + [c['id']+'.xml' for c in checks if c['id'].startswith('pr2_03_') and c['id'] not in {'pr2_03_concurrency','pr2_03_idempotency'}]
missing_or_skipped = [name for name in required_xml if not counts(name) or counts(name)['collected']==0 or counts(name)['skipped'] or counts(name)['failed'] or counts(name)['errors']]
if missing_or_skipped: failed=1
result={"required_xml_missing_or_skipped":missing_or_skipped,"run_id":run_id,"mode":"pr2-03-verification","result_role":"host execution evidence only; no reviewer verdict",
 "implementation_sha":os.getenv("RB_IMPLEMENTATION_SHA"),"design_subject":"8c4355b7b8f25450a97436c1989e254c023ad34e",
 "phase1_baseline":"d2400fbeca835c89bd802a4e9d647bda01cfd115","postgres_version":os.getenv("RB_PG_VERSION"),
 "expected_migration_head":"0023a_search_plan_review_guards",
 "phase2_migration_head":"0023a_search_plan_review_guards" if any(c["id"]=="migration_current_0023a" and c["status"]=="PASS" for c in checks) else None,
 "execution_head":os.getenv("RB_EXECUTION_HEAD"),"execution_branch":os.getenv("RB_EXECUTION_BRANCH"),
 "tracked_state":os.getenv("RB_TRACKED_STATE"),"production_subject":os.getenv("RB_EXECUTION_HEAD"),"database":"researchbase_review",
 "cleanup":os.getenv("RB_CLEANUP"),"checks":checks,"focused_counts":focused,"temporal_counts":temporal,
 "pr2_03_concurrency_counts":concurrency,"pr2_03_idempotency_counts":idempotency,
 "full_suite_counts":({**full,"warnings":warnings} if full is not None else None),"temporal_trace":temporal_trace,
 "PR2_00_TEMPORAL_RESIDUAL_REOPENED":"YES" if temporal_trace and (temporal_trace["successful_post_expiry_consumption"] or temporal_trace["protected_post_expiry_effects"]) else "NO" if temporal_trace and all(temporal_trace["checks"].values()) else "INCONCLUSIVE",
 "formatter":{"raw_exit_code":next((c["exit_code"] for c in checks if c["id"]=="formatter_raw"),None),"raw_failures":raw_files,"baseline_delta":delta},
 "log_files":sorted(p.name for p in (out/"logs").iterdir()),
 "verification_gate":"PASS" if not failed else "FAIL",
 "P0":None,"P1":None,"P2":None,"verdict":"NOT_ISSUED_INDEPENDENT_REVIEW_REQUIRED"}
(out/"host_review_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
lines=["# PR2-03 Host Verification","",f"Run: `{run_id}`","","Role: host DB execution evidence only; independent reviewer verdict not issued.",
 f"Implementation: `{result['implementation_sha']}`",f"Design: `{result['design_subject']}`",
 f"PostgreSQL: `{result['postgres_version']}`; database: `{result['database']}`; migration head: `{result['phase2_migration_head']}`",
 f"Focused counts: `{focused}`",f"Concurrency counts: `{concurrency}`",
 f"Idempotency counts: `{idempotency}`",f"Temporal counts: `{temporal}`",f"Full-suite counts: `{full}`",
 f"Temporary cluster cleanup: `{result['cleanup']}`","","## Checks",""]
for c in checks: lines.append(f"- `{c['id']}`: **{c['status']}** — `{c['command']}`")
lines += ["",f"Verification gate: **{result['verification_gate']}**"]
(out/"host_review_result.md").write_text("\n".join(lines)+"\n")
raise SystemExit(1 if failed else 0)
PY
  exit "$((FAIL == 0 && rc == 0 ? 0 : 1))"
}

mkdir -p "$OUT/logs" || exit 2
: > "$OUT/checks.txt"
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=1; fi
cd "$REPO" || exit 2
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
if [ "$(git branch --show-current)" != "$EXPECTED_BRANCH" ] || ! git merge-base --is-ancestor "$DESIGN" HEAD; then
  printf 'Repository branch or immutable design ancestry mismatch.\n' >&2; exit 2
fi
git merge-base --is-ancestor "$IMPLEMENTATION" HEAD || {
  printf 'PR2-03 implementation subject is absent from current history.\n' >&2; exit 2;
}
export RB_EXECUTION_HEAD="$(git rev-parse HEAD)"
export RB_EXECUTION_BRANCH="$(git branch --show-current)"
RB_TRACKED_STATE="$(if git diff --quiet && git diff --cached --quiet; then echo CLEAN; else echo DIRTY; fi)"
export RB_TRACKED_STATE
if [ "$DRY_RUN" -ne 1 ] && [ "$RB_TRACKED_STATE" != CLEAN ]; then
  printf 'Host verification requires a committed, clean tracked subject.\n' >&2; exit 2
fi
git diff --quiet "$IMPLEMENTATION" HEAD -- migrations/versions/0023_literature_search_plan.py || exit 2
tag_commit="$(git rev-parse 'phase1-final-v4^{commit}')"
[ "$tag_commit" = "$PHASE1" ] || { printf 'Frozen Phase 1 tag mismatch.\n' >&2; exit 2; }
git diff --quiet "$PHASE1" -- 'migrations/versions/000*.py' 'migrations/versions/001[0-8]*.py' || {
  printf 'Frozen Phase 1 migrations drifted.\n' >&2; exit 2;
}
record phase1_non_drift 0 'phase1-final-v4 and historical Phase 1 migrations unchanged'
acceptance_path="$(git grep -l -F 'PR2_02_ACCEPTED = YES' HEAD -- artifacts/pr_evidence/PR2-02 2>/dev/null || true)"
acceptance_valid=1
if [ -z "$acceptance_path" ] || [ "$(printf '%s\n' "$acceptance_path" | wc -l | tr -d ' ')" -ne 1 ]; then
  acceptance_valid=0
else
  acceptance_path="${acceptance_path#HEAD:}"
  acceptance_text="$(git show "HEAD:$acceptance_path" 2>/dev/null || true)"
  for required in \
    'PR2_02_ACCEPTED = YES' \
    '3de5e897cc72de3e4c4f7b86d83ed8ae2b13fc93' \
    'a8fd1fef2475b12c50e6f18a4aaa6d9b0e663d02' \
    '20261004T092722Z-79123' \
    '18.6 (Homebrew)' \
    'Host verification gate: `PASS`' \
    'Reviewer identity/context:' \
    'NEW_P0_GAPS = 0' \
    'NEW_P1_GAPS = 0' \
    'NEW_P2_GAPS = 0' \
    'Verdict: `PASS`'; do
    printf '%s\n' "$acceptance_text" | grep -F "$required" >/dev/null || acceptance_valid=0
  done
fi
if [ "$acceptance_valid" -ne 1 ]; then
  record durable_pr2_02_acceptance 1 'validate tracked PR2-02 acceptance artifact, host run, subjects, independent verdict and zero findings'
  printf 'PR2_02_DURABLE_ACCEPTANCE_MISSING\n' >&2
  exit 2
fi
record durable_pr2_02_acceptance 0 "tracked acceptance artifact $acceptance_path binds required subjects and independent PASS"
if [ "$DRY_RUN" -eq 1 ]; then
  printf 'DRY_RUN=YES\nMODE=pr2-03-verification\nDURABLE_PR2_02_ACCEPTANCE=PASS\nIMPLEMENTATION=%s\nPLANNED_MIGRATION_HEAD=0023a_search_plan_review_guards\n' "$IMPLEMENTATION"
  trap - EXIT INT TERM
  exit 0
fi
"$PG_BIN/postgres" --version | grep -E 'PostgreSQL 18\.' >/dev/null || { printf 'PostgreSQL 18 unavailable.\n' >&2; exit 2; }
"$PYTHON" -c 'import sqlalchemy, psycopg, pytest' || exit 2
implementation_sha="$IMPLEMENTATION"
export RB_IMPLEMENTATION_SHA="$implementation_sha"
RUN_TMP="$(mktemp -d /private/tmp/researchbase-pr2-03-host.XXXXXX)" || exit 2
PGDATA="$RUN_TMP/data"
PGLOG="$RUN_TMP/postgres.log"
PORT="$("$PYTHON" -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
"$PG_BIN/initdb" -D "$PGDATA" --username=researchbase --auth=trust > "$OUT/logs/initdb.log" 2>&1
record initdb "$?" 'initdb isolated temporary PostgreSQL 18 cluster'
if [ "$FAIL" -ne 0 ]; then exit 1; fi
"$PG_BIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -o "-h 127.0.0.1 -p $PORT -c timezone=UTC" start > "$OUT/logs/pg_start.log" 2>&1
record postgres_start "$?" 'pg_ctl start isolated PostgreSQL 18 cluster'
if [ "$FAIL" -ne 0 ]; then exit 1; fi
STARTED=1
for attempt in $(seq 1 30); do
  if "$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PORT" -U researchbase > "$OUT/logs/pg_isready.log" 2>&1; then break; fi
  sleep 1
done
"$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PORT" -U researchbase >/dev/null 2>&1
record postgres_ready "$?" 'pg_isready localhost on selected temporary port'
if [ "$FAIL" -ne 0 ]; then cat "$PGLOG" >&2; exit 1; fi
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_review
record create_review_db "$?" 'createdb researchbase_review'
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_phase1_review
record create_phase1_db "$?" 'createdb researchbase_phase1_review'
export DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_review"
export PHASE1_DATABASE_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_phase1_review"
"$PG_BIN/psql" -h 127.0.0.1 -p "$PORT" -U researchbase -d researchbase_review -Atc 'select version()' > "$OUT/logs/postgres_version.log"
RB_PG_VERSION="$(cat "$OUT/logs/postgres_version.log")"
export RB_PG_VERSION
"$TOOLS/alembic" upgrade 0023_literature_search_plan > "$OUT/logs/migration_upgrade_0023.log" 2>&1
record migration_upgrade_0023 "$?" 'alembic upgrade original PR2-03 boundary0023'
"$TOOLS/alembic" current > "$OUT/logs/migration_current_0023.log" 2>&1
grep -F '0023_literature_search_plan' "$OUT/logs/migration_current_0023.log" >/dev/null
record migration_current_0023 "$?" 'alembic current original PR2-03 boundary0023'
"$TOOLS/alembic" upgrade head > "$OUT/logs/migration_upgrade_0023a.log" 2>&1
record migration_upgrade_0023a "$?" 'alembic upgrade remediated PR2-03 head0023a'
"$TOOLS/alembic" current > "$OUT/logs/migration_current.log" 2>&1
grep -F '0023a_search_plan_review_guards' "$OUT/logs/migration_current.log" >/dev/null
record migration_current_0023a "$?" 'alembic current unique remediated Phase 2 head'
"$TOOLS/alembic" heads > "$OUT/logs/alembic_heads.log" 2>&1
head_count="$(grep -c '(head)' "$OUT/logs/alembic_heads.log" || true)"
[ "$head_count" = 1 ] && grep -F '0023a_search_plan_review_guards (head)' "$OUT/logs/alembic_heads.log" >/dev/null
record migration_unique_head "$?" 'alembic heads requires one remediated PR2-03 head'
DATABASE_URL="$PHASE1_DATABASE_URL" "$TOOLS/alembic" upgrade 0018_current_pointer_same_parent_integrity > "$OUT/logs/phase1_upgrade.log" 2>&1
record phase1_upgrade_0018 "$?" 'alembic upgrade to frozen Phase 1 boundary'
"$TOOLS/pytest" -o 'addopts=' -ra tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_01_source_identity.py --junitxml="$OUT/logs/focused.xml" > "$OUT/logs/focused.log" 2>&1
record focused_pr2_03 "$?" 'pytest PR2-03 migration + accepted PR2-01/02 PostgreSQL regressions'
"$TOOLS/pytest" -o 'addopts=' -ra tests/integration/phase2/test_pr2_03_literature_search_plan_concurrency.py --junitxml="$OUT/logs/concurrency.xml" > "$OUT/logs/concurrency.log" 2>&1
record pr2_03_concurrency "$?" 'pytest PR2-03 PostgreSQL freeze/edit/remove race invariants'
"$TOOLS/pytest" -o 'addopts=' -ra tests/integration/phase2/test_pr2_03_literature_search_plan_idempotency.py --junitxml="$OUT/logs/idempotency.xml" > "$OUT/logs/idempotency.log" 2>&1
record pr2_03_idempotency "$?" 'pytest PR2-03 PostgreSQL canonical command-key idempotency invariants'
"$TOOLS/pytest" -o 'addopts=' -s tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait --junitxml="$OUT/logs/temporal.xml" > "$OUT/logs/temporal.log" 2>&1
record pr2_00_temporal "$?" 'pytest TEMP-AUTH lock-wait expiry boundary test'
if grep -F 'TEMP-AUTH challenge proof ' "$OUT/logs/temporal.log" > "$OUT/logs/temporal_proof_line.txt"; then
  "$PYTHON" - "$OUT/logs/temporal_proof_line.txt" "$OUT/temporal_trace.json" <<'PY' > "$OUT/logs/temporal_trace.log" 2>&1
import json,sys
from datetime import datetime,timedelta
from pathlib import Path
line=Path(sys.argv[1]).read_text().strip().splitlines()[-1]
p=json.loads(line.split("TEMP-AUTH challenge proof ",1)[1])
issued=datetime.fromisoformat(p["challenge_issued_at"]); expiry=datetime.fromisoformat(p["expiry_at"])
locked=datetime.fromisoformat(p["lock_acquired_at"]); authorized=datetime.fromisoformat(p["authorization_clock_timestamp"])
crossed=datetime.fromisoformat(p["expiry_crossed_at"]); released=datetime.fromisoformat(p["lock_released_at_observed"])
wait=p.get("observed_wait",{})
effects=p["persisted_effects"]
checks={"issued_before_expiry":issued<expiry,"postgres_lock_wait_observed":wait.get("wait_event_type")=="Lock",
 "expiry_elapsed_during_wait":crossed>=expiry+timedelta(milliseconds=250),
 "lock_acquired_after_expiry":locked>=expiry,"lock_released_after_expiry":released>=expiry,
 "fresh_authorization_after_lock":authorized>=locked,"authorization_after_expiry":authorized>=expiry,
 "denied":p.get("effect_result")=="DENY","challenge_unconsumed":effects.get("challenge_status")=="ISSUED",
 "zero_protected_effects":effects.get("bindings")==0 and effects.get("binding_events")==0}
result={"checks":checks,"successful_post_expiry_consumption":authorized>=expiry and effects.get("challenge_status")=="CONSUMED",
 "protected_post_expiry_effects":effects.get("bindings",0)>0 or effects.get("binding_events",0)>0}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("TEMPORAL_TRACE="+("PASS" if all(checks.values()) else "FAIL"))
raise SystemExit(0 if all(checks.values()) and not result["successful_post_expiry_consumption"] and not result["protected_post_expiry_effects"] else 1)
PY
  record temporal_trace "$?" 'assert lock-wait expiry, post-wait DB authorization denial and zero effects'
else
  printf 'TEMP-AUTH proof line missing\n' > "$OUT/logs/temporal_trace.log"
  record temporal_trace 1 'require complete TEMP-AUTH proof line'
fi
"$PG_BIN/createdb" -h 127.0.0.1 -p "$PORT" -U researchbase researchbase_pr11_matrix
record create_pr11_matrix_db "$?" 'createdb isolated historical migration matrix database'
export PR11R2_MIGRATION_DB_URL="postgresql+psycopg://researchbase@127.0.0.1:$PORT/researchbase_pr11_matrix"
DATABASE_URL="$PHASE1_DATABASE_URL" "$TOOLS/pytest" -o 'addopts=' -ra --junitxml="$OUT/logs/full_suite.xml" > "$OUT/logs/full_suite.log" 2>&1
record full_suite "$?" 'pytest full suite with Phase 1 catalog boundary database'
"$TOOLS/ruff" check . > "$OUT/logs/ruff.log" 2>&1; record ruff "$?" 'ruff check .'
"$TOOLS/pyright" --venvpath /Users/onephone/Documents/Codex/ResearchBase > "$OUT/logs/pyright.log" 2>&1; record pyright "$?" 'pyright --venvpath ResearchBase'
"$TOOLS/ruff" format --check . > "$OUT/logs/formatter_raw.log" 2>&1; raw=$?; record formatter_raw "$raw" 'ruff format --check .'
"$PYTHON" - "$OUT/logs/formatter_raw.log" "$REPO/artifacts/pr_evidence/PR2-00/formatter_baseline.json" "$OUT/formatter_delta.json" <<'PY' > "$OUT/logs/formatter_delta.log" 2>&1
import json,re,sys
from pathlib import Path
raw,base,out=map(Path,sys.argv[1:])
baseline=set(json.loads(base.read_text())["baseline"]["failing_files"])
current=set(re.findall(r"^Would reformat: (.+)$",raw.read_text(errors="replace"),re.M))
new=sorted(current-baseline)
out.write_text(json.dumps({"baseline":sorted(baseline),"current":sorted(current),"new":new,"gate":"PASS" if not new else "FAIL"},indent=2)+"\n")
raise SystemExit(bool(new))
PY
record formatter_baseline_delta "$?" 'FORMAT-BASELINE-01 new-failure delta'
git diff --check > "$OUT/logs/diff_check.log" 2>&1; record git_diff_check "$?" 'git diff --check'
exit "$FAIL"
