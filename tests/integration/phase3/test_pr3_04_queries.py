"""One read-only snapshot; expiry is projected without modifying request history."""

from sqlalchemy import event, text
from tests.integration.phase3.test_pr3_04_application import bind, command, service

from researchbase.foundation.ids import new_uuid7


def test_missing_bundle_backward_read_and_snapshot(planning):
    p = planning
    task = p.create()
    observed = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        observed.append(statement)

    event.listen(p.engine, "before_cursor_execute", capture)
    try:
        view = service(p).get_task_safety(p.principal, p.project, task)
    finally:
        event.remove(p.engine, "before_cursor_execute", capture)
    assert view.budget is None and view.reserved.llm_calls == 0 and not view.execution_enabled
    assert all(
        not s.lstrip().startswith(("UPDATE", "INSERT", "LOCK", "SET CONSTRAINTS"))
        and "FOR UPDATE" not in s
        and "pg_advisory" not in s
        for s in observed
    )
    assert sum("transaction_timestamp()" in s for s in observed) == 1


def test_database_expiry_projection_and_explicit_evaluation(planning):
    p = planning
    task = p.create()
    bind(p, task, checkpoint={"timeout_seconds": 1})
    request = command(
        p,
        task,
        2,
        "request_human_checkpoint",
        {
            "checkpoint_id": str(new_uuid7()),
            "step_id": None,
            "checkpoint_type": "plan_review",
            "reason": "Expiring review.",
        },
    )
    service(p).execute(p.principal, request)
    # Wait until database time reaches the stored deadline, never rewrite history.
    with p.engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (expires_at-clock_timestamp())))) FROM human_checkpoints WHERE research_task_id=:id"  # noqa: E501
            ),
            {"id": task},
        )
    view = service(p).get_task_checkpoint_history(p.principal, p.project, task)
    assert (
        view.checkpoints[0].status == "PENDING"
        and view.checkpoints[0].effective_status == "EXPIRED"
    )
    service(p).execute(
        p.principal,
        command(p, task, 3, "evaluate_task_termination", {"reason": "Expire elapsed checkpoints."}),
    )
    after = service(p).get_task_checkpoint_history(p.principal, p.project, task)
    assert (
        after.checkpoints[0].status == "EXPIRED"
        and after.checkpoints[0].response_reason == "Checkpoint expired."
    )
    assert after.checkpoints[0].responded_by is None
