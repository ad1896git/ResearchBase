import json

import pytest
from scripts.pipeline_commander import command_once, decision
from scripts.pipeline_protocol import ProtocolError, StateStore


def test_validated_decision_cannot_select_blocked_or_stale_task():
    valid = dict(revision=3, action="dispatch", task_id="ready", reason="dependencies done")
    assert decision(json.dumps(valid), 3, ["ready"]) == valid
    with pytest.raises(ProtocolError, match="stale"):
        decision(json.dumps(valid), 4, ["ready"])
    with pytest.raises(ProtocolError, match="ineligible"):
        decision(json.dumps(valid), 3, [])


@pytest.mark.parametrize("update", [dict(action="merge"), dict(extra=True), dict(task_id="other")])
def test_invalid_command_fields_deny(update):
    value = dict(revision=0, action="wait", task_id="", reason="human gate")
    value.update(update)
    with pytest.raises(ProtocolError):
        decision(json.dumps(value), 0, [])


def test_command_session_is_read_only_proposal_and_does_not_spend_round(tmp_path, monkeypatch):
    from scripts import pipeline_commander as commander

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("work")
        revision = store.state["revision"]

    def session(cwd, output, prompt, schema, **kwargs):
        assert not kwargs.get("writable", False)
        assert "eligible" in prompt and schema.name == "pipeline_commander.schema.json"
        output.mkdir()
        (output / "answer.json").write_text(
            json.dumps(
                dict(
                    revision=revision,
                    action="dispatch",
                    task_id="work",
                    reason="eligible",
                )
            )
        )
        return dict(exit_code=0, timed_out=False, descendants_stopped=True)

    monkeypatch.setattr(commander, "run_session", session)
    assert command_once(control, evidence, tmp_path)["task_id"] == "work"
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 0
        assert store.state["tasks"]["work"]["status"] == "ready"


def test_state_change_during_commander_session_denies_proposal(tmp_path, monkeypatch):
    from scripts import pipeline_commander as commander

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("work")

    def session(cwd, output, prompt, schema, **kwargs):
        output.mkdir()
        state = json.loads((control / "state.json").read_text())
        state["revision"] += 1
        (control / "state.json").write_text(json.dumps(state))
        return dict(exit_code=0, timed_out=False, descendants_stopped=True)

    monkeypatch.setattr(commander, "run_session", session)
    with pytest.raises(ProtocolError, match="state changed"):
        command_once(control, evidence, tmp_path)
