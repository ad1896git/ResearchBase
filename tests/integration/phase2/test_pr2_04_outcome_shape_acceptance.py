"""Direct SQL complete failure tuple constraints, including uncertainty safety."""
from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.integration.phase2.test_pr2_04_schema_coverage import A, _material, _reject, _rows

FAILURES = [
    ("RETRYABLE_FAILURE", "PROVIDER_TRANSIENT", "NOT_SENT"),
    ("PERMANENT_FAILURE", "PROVIDER_PERMANENT", "RESPONSE_RECEIVED"),
    ("CANCELLED", "CANCELLED", "NOT_SENT"),
    ("UNKNOWN", "RECOVERY_OUTCOME_UNKNOWN", "MAY_HAVE_BEEN_SENT"),
]


@pytest.mark.pr204_requirements("PR204-DOM-02", "PR204-DB-01", "PR204-DB-05")
@pytest.mark.parametrize("status,reason,certainty", FAILURES, ids=[row[0] for row in FAILURES])
@pytest.mark.parametrize("violation", ["null_completed", "null_certainty", "null_reason", "retrieval_claim",
                                      "completion_before_reserve", "uncertainty_relabel"])
def test_pg_failure_tuple_required_fields_and_uncertainty(status, reason, certainty, violation,
                                                         phase2_database_url, pr204_trace):
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    attempt = _rows(engine)[A][0]
    try:
        values = dict(id=attempt["id"], status=status, reason=reason, certainty=certainty,
                      completed=attempt["reserved_at"], retrieved=None)
        if violation == "null_completed":
            values["completed"] = None
        elif violation == "null_certainty":
            values["certainty"] = None
        elif violation == "null_reason":
            values["reason"] = None
        elif violation == "retrieval_claim":
            values["retrieved"] = attempt["reserved_at"]
        elif violation == "completion_before_reserve":
            values["completed"] = attempt["reserved_at"] - timedelta(seconds=1)
        elif violation == "uncertainty_relabel":
            values["certainty"] = "NOT_SENT" if status == "UNKNOWN" else "MAY_HAVE_BEEN_SENT"

        def mutate(connection):
            connection.execute(text(f"UPDATE {A} SET status=:status,completed_at=:completed,"
                                    "delivery_certainty=:certainty,failure_code=:reason,"
                                    "retrieved_at=:retrieved,warning_codes='[]'::jsonb,result_count=0,"
                                    "row_version=2 WHERE id=:id"), values)

        _reject(engine, mutate, "23514", pr204_trace, case=f"{status}-{violation}")
    finally:
        engine.dispose()
