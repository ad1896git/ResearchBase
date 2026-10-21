"""Print a deterministic, exhaustive file shard for a single-process pytest run.

Use --durations with a measured seconds_by_file JSON profile to balance work.
CI publishes JUnit timing artifacts for refreshing that profile. Without a
profile, files are assigned round-robin by path.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping
from pathlib import Path


def shard_files(
    root: Path,
    index: int,
    count: int,
    durations: Mapping[str, float] | None = None,
) -> list[str]:
    if count < 1 or not 0 <= index < count:
        raise ValueError("require count > 0 and 0 <= index < count")
    files = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "tests").rglob("*.py")
        if path.name.startswith("test_") or path.name.endswith("_test.py")
    )
    if durations is None:
        return files[index::count]
    if any(not math.isfinite(value) or value < 0 for value in durations.values()):
        raise ValueError("durations must be finite nonnegative seconds")
    measured = [path for path in files if path in durations]
    measured_bytes = sum((root / path).stat().st_size for path in measured)
    seconds_per_byte = (
        sum(durations[path] for path in measured) / measured_bytes if measured_bytes else 1.0
    )
    costs = {
        path: durations.get(path, (root / path).stat().st_size * seconds_per_byte) for path in files
    }
    loads = [0.0] * count
    shards: list[list[str]] = [[] for _ in range(count)]
    # Longest files first; path and shard index break ties reproducibly.
    for path in sorted(files, key=lambda path: (-costs[path], path)):
        target = min(range(count), key=lambda shard: (loads[shard], len(shards[shard]), shard))
        shards[target].append(path)
        loads[target] += costs[path]
    return shards[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--durations", type=Path, help="JSON profile containing seconds_by_file")
    args = parser.parse_args()
    try:
        durations = None
        if args.durations is not None:
            profile = json.loads(args.durations.read_text())
            if profile["schema_version"] != 1:
                raise ValueError("unsupported timing profile schema")
            durations = {
                path: float(seconds) for path, seconds in profile["seconds_by_file"].items()
            }
        files = shard_files(Path(__file__).resolve().parents[1], args.index, args.count, durations)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.error(str(error))
    if not files:
        parser.error("empty test shard")
    print("\n".join(files))


if __name__ == "__main__":
    main()
