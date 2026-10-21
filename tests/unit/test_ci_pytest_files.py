from pathlib import Path

import pytest
from scripts.ci_pytest_files import shard_files


def test_shards_partition_all_pytest_files_deterministically(tmp_path: Path) -> None:
    names = [f"tests/nested/test_{index}.py" for index in range(13)]
    names += ["tests/legacy_test.py"]
    for name in [*names, "tests/conftest.py", "tests/support.py"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    shards = [shard_files(tmp_path, index, 4) for index in range(4)]
    flattened = [name for shard in shards for name in shard]
    assert sorted(flattened) == sorted(names)
    assert len(flattened) == len(set(flattened))
    assert max(map(len, shards)) - min(map(len, shards)) <= 1
    assert shards == [sorted(names)[index::4] for index in range(4)]


@pytest.mark.parametrize("index,count", [(-1, 4), (4, 4), (0, 0)])
def test_invalid_shards_fail_closed(tmp_path: Path, index: int, count: int) -> None:
    with pytest.raises(ValueError):
        shard_files(tmp_path, index, count)


def test_measured_shards_balance_expensive_files_and_include_unmeasured_files(
    tmp_path: Path,
) -> None:
    names = [f"tests/test_{index}.py" for index in range(5)]
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# same size\n")
    # Round-robin puts both long files in shard 0; measured balancing separates them.
    durations = dict(zip(names[:4], [100.0, 1.0, 100.0, 1.0], strict=True))
    shards = [shard_files(tmp_path, index, 2, durations) for index in range(2)]
    assert sorted(path for shard in shards for path in shard) == names
    assert next(index for index, shard in enumerate(shards) if names[0] in shard) != next(
        index for index, shard in enumerate(shards) if names[2] in shard
    )
    assert shards == [shard_files(tmp_path, index, 2, durations) for index in range(2)]
    assert sum(names[4] in shard for shard in shards) == 1


@pytest.mark.parametrize("seconds", [-1.0, float("nan"), float("inf")])
def test_invalid_measured_durations_fail_closed(tmp_path: Path, seconds: float) -> None:
    with pytest.raises(ValueError, match="finite nonnegative"):
        shard_files(tmp_path, 0, 2, {"tests/test_example.py": seconds})
