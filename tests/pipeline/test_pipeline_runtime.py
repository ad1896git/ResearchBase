import pytest
from scripts.pipeline_runtime import dispatch


def test_wait_dispatch_does_not_execute_or_mutate(tmp_path):
    value = dict(action="wait", task_id="", revision=0, reason="awaiting human")
    assert dispatch(value, {}, tmp_path, tmp_path)["status"] == "wait"
    assert list(tmp_path.iterdir()) == []


def test_model_cannot_dispatch_arbitrary_shell_or_merge(tmp_path):
    value = dict(action="dispatch", task_id="work", revision=0, reason="")
    with pytest.raises(ValueError, match="unsupported executor"):
        dispatch(value, {"work": dict(kind="merge", config={})}, tmp_path, tmp_path)
