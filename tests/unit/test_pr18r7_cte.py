from typing import Any, cast

import pytest
from scripts.pr18_evidence import validate_statement_purity


def test_r7_frozen_read_only_cte_positive_control() -> None:
    result = validate_statement_purity([{"sql": "WITH x AS (\n    SELECT 1\n)\nSELECT * FROM x;"}])
    statement = cast(list[dict[str, Any]], result["statements"])[0]
    assert statement["statement_class"] == "READ_SELECT", statement
    assert statement["purity_verdict"] == "PASS"
    assert result["overall_verdict"] == "PASS"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM x;",
        'SELECT "count"(*) FROM x;',
        "WITH x AS (SELECT 1 AS id) SELECT id FROM x;",
        "WITH a AS (SELECT 1 AS id), b AS (SELECT id FROM a) SELECT * FROM b;",
        "WITH x AS (SELECT (1 + 2) AS id) SELECT * FROM x;",
    ],
)
def test_r7_supported_projection_proof(sql: str) -> None:
    result = validate_statement_purity([{"sql": sql}])
    statement = cast(list[dict[str, Any]], result["statements"])[0]
    for field in ("lexical_valid", "grammar_supported", "statement_complete"):
        assert statement[field] is True
    for field in ("mutating_cte_detected", "locking_detected", "select_into_detected"):
        assert statement[field] is False
    assert statement["statement_class"] == "READ_SELECT"
    assert statement["purity_verdict"] == "PASS"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT *;",
        "SELECT * UNION SELECT 1 FROM x;",
        "SELECT * INTERSECT SELECT 1 FROM x;",
        "SELECT * EXCEPT SELECT 1 FROM x;",
        "WITH x AS (SELECT * UNION SELECT 1 FROM t) SELECT * FROM x;",
        "SELECT *, id FROM x;",
        "SELECT id, * FROM x;",
        "SELECT *, FROM x;",
        "SELECT * + FROM x;",
        "SELECT ** FROM x;",
        "SELECT (*) FROM x;",
        "SELECT * AS id FROM x;",
        "WITH x AS (UPDATE t SET x = 1 RETURNING id) SELECT * FROM x;",
        "WITH x AS (INSERT INTO t (id) VALUES (1) RETURNING id) SELECT * FROM x;",
        "WITH x AS (DELETE FROM t RETURNING id) SELECT * FROM x;",
        "WITH a AS (SELECT 1), b AS (UPDATE t SET x = 1 RETURNING id) SELECT * FROM a;",
        "WITH x AS () SELECT 1;",
        "WITH x AS (SELECT) SELECT * FROM x;",
        "WITH x AS (SELECT FROM t) SELECT * FROM x;",
        "WITH x AS (SELECT 1) SELECT;",
        "WITH x AS (SELECT 1) SELECT FROM x;",
        "WITH x AS (SELECT 1)",
        "WITH AS (SELECT 1) SELECT * FROM x;",
        "WITH x (SELECT 1) SELECT * FROM x;",
        "WITH x AS SELECT 1) SELECT * FROM x;",
        "WITH x AS (SELECT 1 SELECT * FROM x;",
        "WITH x AS (SELECT 1) SELECT * INTO t FROM x;",
        "WITH x AS (SELECT 1) SELECT * FROM x FOR UPDATE;",
        "WITH x AS (SELECT 1) SELECT * FROM x; DELETE FROM t;",
    ],
)
def test_r7_invalid_or_impure_cte_never_passes(sql: str) -> None:
    result = validate_statement_purity([{"sql": sql}])
    assert result["overall_verdict"] == "FAIL"
    assert cast(list[dict[str, Any]], result["statements"])[0]["purity_verdict"] != "PASS"
