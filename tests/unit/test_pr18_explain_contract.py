# pyright: reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false

from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest
from scripts import pr18_evidence
from scripts.pr18_evidence import PR18EvidenceError, validate_query_contract
from sqlalchemy import create_engine
from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS


def _classify_statement(sql: str) -> str:
    classifier = getattr(pr18_evidence, "classify_statement", None)
    assert callable(classifier)
    return classifier(sql)


def _validate_statement_purity(statements: object) -> dict[str, object]:
    validator = getattr(pr18_evidence, "validate_statement_purity", None)
    assert callable(validator)
    return validator(statements)


def _statement(
    sql: str,
    *,
    relations: list[str],
    nodes: list[str] | None = None,
    join_types: list[str] | None = None,
) -> dict[str, object]:
    return {
        "sql": sql,
        "plan": {
            "relations": relations,
            "node_types": nodes or ["Index Scan"],
            "join_types": join_types or [],
        },
    }


def _downstream_expectation() -> dict[str, object]:
    expectation = deepcopy(FROZEN_QUERY_EXPECTATIONS["downstream_impact"])
    topology = dict(cast(dict[str, object], expectation["topology"]))
    topology.update(
        {
            "allowed_relations": expectation["required_relations"],
            "closed_relation_set": True,
            "allow_single_relation_reads": True,
            "allow_cartesian_joins": False,
            "required_join_edges": (
                (
                    "artifact belongs to project",
                    ("artifacts", "artifact_versions"),
                    r"\bartifact_versions\.artifact_id\s*=\s*artifacts\.id\b",
                ),
                (
                    "run input reaches run",
                    ("run_artifact_inputs", "runs"),
                    r"\bruns\.id\s*=\s*run_artifact_inputs\.run_id\b",
                ),
                (
                    "measurement reaches statistical input",
                    ("measurements", "statistical_result_inputs"),
                    r"\bmeasurements\.id\s*=\s*statistical_result_inputs\.measurement_id\b",
                ),
                (
                    "statistical input reaches result",
                    ("statistical_result_inputs", "statistical_results"),
                    r"\bstatistical_results\.id\s*=\s*statistical_result_inputs\.statistical_result_id\b",
                ),
                (
                    "measurement reaches claim evidence",
                    ("evidence_relations", "claim_versions"),
                    r"\bclaim_versions\.id\s*=\s*evidence_relations\.claim_version_id\b",
                ),
                (
                    "claim version reaches claim",
                    ("claim_versions", "claims"),
                    r"\bclaims\.id\s*=\s*claim_versions\.claim_id\b",
                ),
            ),
            "allowed_join_edges": (),
        }
    )
    topology["allowed_join_edges"] = topology["required_join_edges"]
    expectation["topology"] = topology
    return expectation


def _valid_downstream_statements() -> list[dict[str, object]]:
    return [
        _statement(
            "SELECT artifacts.project_id, artifact_versions.content_hash "
            "FROM artifacts JOIN artifact_versions "
            "ON artifact_versions.artifact_id = artifacts.id "
            "WHERE artifact_versions.id = :id AND artifacts.project_id = :project",
            relations=["artifacts", "artifact_versions"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs "
            "ON runs.id = run_artifact_inputs.run_id "
            "WHERE run_artifact_inputs.artifact_version_id = :artifact "
            "AND runs.project_id = :project",
            relations=["run_artifact_inputs", "runs"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT measurements.run_id, measurements.id FROM measurements "
            "WHERE measurements.run_id IN (:run_id)",
            relations=["measurements"],
        ),
        _statement(
            "SELECT statistical_result_inputs.measurement_id "
            "FROM statistical_result_inputs JOIN measurements "
            "ON measurements.id = statistical_result_inputs.measurement_id "
            "JOIN statistical_results "
            "ON statistical_results.id = statistical_result_inputs.statistical_result_id "
            "WHERE statistical_result_inputs.measurement_id IN (:measurement) "
            "AND statistical_results.project_id = :project",
            relations=["statistical_result_inputs", "measurements", "statistical_results"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT evidence_relations.id FROM evidence_relations JOIN claim_versions "
            "ON claim_versions.id = evidence_relations.claim_version_id "
            "JOIN claims ON claims.id = claim_versions.claim_id "
            "WHERE evidence_relations.measurement_id IN (:measurement) "
            "AND claims.project_id = :project",
            relations=["evidence_relations", "claim_versions", "claims"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT evidence_relations.id FROM evidence_relations JOIN claim_versions "
            "ON claim_versions.id = evidence_relations.claim_version_id "
            "JOIN claims ON claims.id = claim_versions.claim_id "
            "WHERE evidence_relations.statistical_result_id IN (:statistical) "
            "AND claims.project_id = :project",
            relations=["evidence_relations", "claim_versions", "claims"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
    ]


def test_query_contract_is_frozen_independently_of_observed_plan() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]

    assert expectation["application_method"] == "GovernanceQueryService.list_audit_findings"
    assert expectation["required_relations"] == ("audit_findings",)
    assert expectation["required_predicates"]
    assert expectation["topology"]["mode"] == "batched_single_relation_selects"  # type: ignore[index]


def test_each_production_query_has_an_explicit_topology_contract() -> None:
    assert set(FROZEN_QUERY_EXPECTATIONS) == {
        "run_provenance",
        "claim_trace",
        "downstream_impact",
        "audit_findings",
    }
    for expectation in FROZEN_QUERY_EXPECTATIONS.values():
        topology = expectation["topology"]
        assert isinstance(topology, dict)
        assert topology["closed_relation_set"] is True
        required_relations = cast(tuple[str, ...], expectation["required_relations"])
        allowed_relations = cast(tuple[str, ...], topology["allowed_relations"])
        assert set(required_relations) <= set(allowed_relations)
        assert topology["forbidden_join_edges"] == "all_unlisted"
        assert topology["allow_cartesian_joins"] is False
        assert topology["forbidden_cartesian_joins"] is True


@pytest.mark.parametrize(
    ("sql", "expected_class"),
    [
        ("SELECT id FROM audit_findings", "READ_SELECT"),
        (
            "WITH x AS (SELECT id FROM audit_findings) SELECT id FROM x",
            "READ_SELECT",
        ),
        ("SELECT id FROM audit_findings FOR UPDATE", "READ_SELECT_LOCKING"),
        ("SELECT id FROM audit_findings FOR NO KEY UPDATE", "READ_SELECT_LOCKING"),
        ("SELECT id FROM audit_findings FOR SHARE", "READ_SELECT_LOCKING"),
        ("SELECT id FROM audit_findings FOR KEY SHARE", "READ_SELECT_LOCKING"),
        (
            "WITH x AS (SELECT id FROM audit_findings FOR UPDATE) SELECT id FROM x",
            "READ_SELECT_LOCKING",
        ),
        ("INSERT INTO audit_findings (id) VALUES (:id)", "WRITE_INSERT"),
        ("UPDATE audit_findings SET title = :title", "WRITE_UPDATE"),
        (
            "WITH changed AS (SELECT id FROM audit_findings) "
            "UPDATE audit_findings SET title = :title",
            "WRITE_UPDATE",
        ),
        (
            "WITH changed AS (UPDATE audit_findings SET title = :title RETURNING id) "
            "SELECT id FROM changed",
            "DATA_MODIFYING_CTE",
        ),
        (
            "WITH inserted AS (INSERT INTO audit_findings (id) VALUES (:id) RETURNING id) "
            "SELECT id FROM inserted",
            "DATA_MODIFYING_CTE",
        ),
        (
            "WITH removed AS (DELETE FROM audit_findings RETURNING id) SELECT id FROM removed",
            "DATA_MODIFYING_CTE",
        ),
        (
            "/* audit */ WITH changed AS (UPDATE audit_findings SET title = :title RETURNING id) "
            "SELECT id FROM changed",
            "DATA_MODIFYING_CTE",
        ),
        (
            "with removed as (delete from audit_findings returning id) select id from removed",
            "DATA_MODIFYING_CTE",
        ),
        (
            "WITH first_read AS (SELECT id FROM audit_findings), "
            "changed AS (UPDATE audit_findings SET title = :title RETURNING id) "
            "SELECT id FROM changed",
            "DATA_MODIFYING_CTE",
        ),
        ("SELECT id INTO new_table FROM audit_findings", "SELECT_INTO_WRITE"),
        ("DELETE FROM audit_findings", "WRITE_DELETE"),
        (
            "MERGE INTO audit_findings USING source ON true "
            "WHEN MATCHED THEN UPDATE SET title = :title",
            "WRITE_MERGE",
        ),
        ("CREATE TABLE temporary_evidence (id integer)", "DDL"),
        ("BEGIN", "TRANSACTION_CONTROL"),
        ("SET LOCAL statement_timeout = '1s'", "SESSION_OR_CONFIG_CHANGE"),
        ("VACUUM audit_findings", "UNKNOWN"),
    ],
)
def test_statement_classifier_is_explicit_and_fail_closed(sql: str, expected_class: str) -> None:
    assert _classify_statement(sql) == expected_class


def test_statement_capture_observes_update_before_valid_select() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE evidence (id integer, title text)")
        connection.exec_driver_sql("INSERT INTO evidence (id, title) VALUES (1, 'ok')")

    def callback() -> None:
        with engine.begin() as connection:
            connection.exec_driver_sql("UPDATE evidence SET title = 'changed' WHERE id = 1")
            connection.exec_driver_sql("SELECT id, title FROM evidence WHERE id = 1")

    capture = getattr(pr18_evidence, "_capture_sql_statements", None)
    assert callable(capture)
    captured = capture(engine, callback)

    assert [_classify_statement(statement) for statement, _parameters in captured] == [
        "WRITE_UPDATE",
        "READ_SELECT",
    ]


def test_statement_purity_positive_control_allows_only_read_selects() -> None:
    projection = _validate_statement_purity(
        [
            {"sql": "SELECT id FROM audit_findings WHERE project_id = :project"},
            {"sql": "SELECT id FROM audit_findings WHERE target_id = :target"},
        ]
    )

    assert projection["statement_count"] == 2
    assert projection["forbidden_statement_count"] == 0
    assert projection["unknown_statement_count"] == 0
    assert projection["write_or_lock_verdict"] == "PASS"
    assert projection["overall_verdict"] == "PASS"
    assert projection["verification_status"] == "VERIFIED"
    assert [item["statement_class"] for item in projection["statements"]] == [
        "READ_SELECT",
        "READ_SELECT",
    ]


@pytest.mark.parametrize(
    ("name", "forbidden_sql", "expected_class"),
    [
        ("update", "UPDATE audit_findings SET title = :title", "WRITE_UPDATE"),
        ("insert", "INSERT INTO audit_findings (id) VALUES (:id)", "WRITE_INSERT"),
        ("delete", "DELETE FROM audit_findings WHERE id = :id", "WRITE_DELETE"),
    ],
)
def test_statement_purity_rejects_write_with_valid_select(
    name: str, forbidden_sql: str, expected_class: str
) -> None:
    projection = _validate_statement_purity(
        [
            {"sql": forbidden_sql},
            {"sql": "SELECT id FROM audit_findings WHERE project_id = :project"},
        ]
    )

    assert name
    assert projection["statement_count"] == 2
    assert projection["forbidden_statement_count"] == 1
    assert projection["unknown_statement_count"] == 0
    assert projection["write_or_lock_verdict"] == "FAIL"
    assert projection["overall_verdict"] == "FAIL"
    assert projection["verification_status"] == "VERIFIED"
    assert projection["statements"][0]["statement_class"] == expected_class


def test_statement_purity_rejects_prohibited_locking_select() -> None:
    projection = _validate_statement_purity(
        [{"sql": ("SELECT id FROM audit_findings WHERE project_id = :project FOR UPDATE")}]
    )

    assert projection["forbidden_statement_count"] == 1
    assert projection["unknown_statement_count"] == 0
    assert projection["write_or_lock_verdict"] == "FAIL"
    assert projection["overall_verdict"] == "FAIL"
    assert projection["statements"][0]["statement_class"] == "READ_SELECT_LOCKING"
    assert projection["statements"][0]["locking_verdict"] == "FAIL"


def test_statement_purity_rejects_ddl_even_with_valid_select() -> None:
    projection = _validate_statement_purity(
        [
            {"sql": "CREATE TABLE temporary_evidence (id integer)"},
            {"sql": "SELECT id FROM audit_findings WHERE project_id = :project"},
        ]
    )

    assert projection["forbidden_statement_count"] == 1
    assert projection["unknown_statement_count"] == 0
    assert projection["write_or_lock_verdict"] == "FAIL"
    assert projection["overall_verdict"] == "FAIL"
    assert projection["verification_status"] == "VERIFIED"
    assert projection["statements"][0]["statement_class"] == "DDL"


def test_statement_purity_rejects_unknown_statement_fail_closed() -> None:
    projection = _validate_statement_purity(
        [
            {"sql": "VACUUM audit_findings"},
            {"sql": "SELECT id FROM audit_findings WHERE project_id = :project"},
        ]
    )

    assert projection["forbidden_statement_count"] == 1
    assert projection["unknown_statement_count"] == 1
    assert projection["write_or_lock_verdict"] == "FAIL"
    assert projection["overall_verdict"] == "FAIL"
    assert projection["verification_status"] == "NOT_VERIFIED"
    assert projection["statements"][0]["statement_class"] == "UNKNOWN"


@pytest.mark.parametrize(
    "sql",
    [
        "/* UPDATE audit_findings SET title = 'ignored' */ SELECT id FROM audit_findings",
        "-- DELETE FROM audit_findings\nSELECT id FROM audit_findings",
        "SELECT 'UPDATE audit_findings SET title = 1' FROM audit_findings",
        "SELECT $$DELETE FROM audit_findings$$ FROM audit_findings",
        'SELECT "INSERT" FROM "UPDATE"',
        "/* UPDATE */ WITH x AS (SELECT id FROM audit_findings) SELECT id FROM x",
    ],
)
def test_statement_classifier_ignores_sql_words_outside_executable_syntax(sql: str) -> None:
    assert _classify_statement(sql) == "READ_SELECT"


@pytest.mark.parametrize(
    "sql",
    [
        "/* unterminated SELECT id FROM audit_findings",
        "SELECT 'unterminated FROM audit_findings",
        'SELECT "unterminated FROM audit_findings',
        "SELECT $$unterminated UPDATE audit_findings",
        "WITH x AS (SELECT id FROM audit_findings SELECT id FROM x",
    ],
)
def test_statement_classifier_rejects_unterminated_or_unbalanced_sql(sql: str) -> None:
    assert _classify_statement(sql) == "UNKNOWN"


@pytest.mark.parametrize(
    ("sql", "expected_class", "reason_field"),
    [
        (
            "WITH changed AS (UPDATE audit_findings SET title = :title RETURNING id) "
            "SELECT id FROM changed",
            "DATA_MODIFYING_CTE",
            "mutating_cte_detected",
        ),
        (
            "WITH inserted AS (INSERT INTO audit_findings (id) VALUES (:id) RETURNING id) "
            "SELECT id FROM inserted",
            "DATA_MODIFYING_CTE",
            "mutating_cte_detected",
        ),
        (
            "WITH removed AS (DELETE FROM audit_findings RETURNING id) SELECT id FROM removed",
            "DATA_MODIFYING_CTE",
            "mutating_cte_detected",
        ),
        (
            "SELECT id INTO new_table FROM audit_findings",
            "SELECT_INTO_WRITE",
            "select_into_detected",
        ),
        (
            "SELECT id FROM audit_findings FOR UPDATE",
            "READ_SELECT_LOCKING",
            "locking_detected",
        ),
        (
            "SELECT id FROM audit_findings FOR SHARE",
            "READ_SELECT_LOCKING",
            "locking_detected",
        ),
        (
            "SELECT id FROM audit_findings; UPDATE audit_findings SET title = :title",
            "UNKNOWN",
            "multi_statement_detected",
        ),
        (
            "UPDATE audit_findings SET title = :title; SELECT id FROM audit_findings",
            "UNKNOWN",
            "multi_statement_detected",
        ),
        ("VACUUM audit_findings", "UNKNOWN", "unknown_detected"),
    ],
)
def test_statement_purity_projection_exposes_intended_rejection_reason(
    sql: str, expected_class: str, reason_field: str
) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == expected_class
    assert statement[reason_field] is True
    assert statement["purity_verdict"] == (
        "NOT_VERIFIED" if expected_class == "UNKNOWN" else "FAIL"
    )
    assert projection["overall_verdict"] == "FAIL"
    assert projection["verification_status"] == (
        "NOT_VERIFIED" if expected_class == "UNKNOWN" else "VERIFIED"
    )


def test_statement_purity_projection_marks_every_read_only_reason_false() -> None:
    projection = _validate_statement_purity(
        [{"sql": "WITH x AS (SELECT id FROM audit_findings) SELECT id FROM x"}]
    )
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["mutating_cte_detected"] is False
    assert statement["select_into_detected"] is False
    assert statement["locking_detected"] is False
    assert statement["multi_statement_detected"] is False
    assert statement["unknown_detected"] is False
    assert statement["purity_verdict"] == "PASS"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT 1;",
        "/* comment */ SELECT 1",
        "SELECT 'UPDATE x SET y = 1'",
        "SELECT 'value; still one statement'",
        "SELECT $$DELETE FROM x;$$",
        'SELECT "UPDATE" FROM "select"',
        'SELECT "value; still one statement"',
        (
            "SELECT id FROM evidence_relations "
            "ORDER BY CASE WHEN measurement_id IS NOT NULL THEN :first "
            "ELSE :second END, qualification ASC NULLS FIRST"
        ),
    ],
)
def test_r6_valid_selects_have_positive_proof(sql: str) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is True
    assert statement["statement_complete"] is True
    assert statement["mutating_cte_detected"] is False
    assert statement["select_into_detected"] is False
    assert statement["locking_detected"] is False
    assert statement["multi_statement_detected"] is False
    assert statement["unknown_detected"] is False
    assert statement["purity_verdict"] == "PASS"
    assert projection["overall_verdict"] == "PASS"


@pytest.mark.parametrize(
    ("sql", "expected_lexical", "expected_complete"),
    [
        ("SELECT;", True, False),
        ("SELECT", True, False),
        ("SELECT FROM t", True, False),
        ("SELECT WHERE true", True, False),
        ("WITH x AS (SELECT 1) SELECT", True, False),
        ("SELECT `x`", False, False),
        ("SELECT a FROM `table`", False, False),
        ("*/ SELECT 1", False, False),
        ("/* unterminated SELECT 1", False, False),
        ("SELECT 'unterminated", False, False),
        ('SELECT "unterminated', False, False),
        ("SELECT $$unterminated", False, False),
        ("SELECT (1", False, False),
        ("SELECT 1)", False, False),
        ("WITH x AS ((SELECT 1) SELECT 1", False, False),
        ("; SELECT 1", True, False),
        ("SELECT 1;;", True, False),
        ("SELECT 1; UPDATE t SET x = 1", True, False),
    ],
)
def test_r6_malformed_or_incomplete_sql_never_passes(
    sql: str, expected_lexical: bool, expected_complete: bool
) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "UNKNOWN"
    assert statement["lexical_valid"] is expected_lexical
    assert statement["grammar_supported"] is False
    assert statement["statement_complete"] is expected_complete
    assert statement["purity_verdict"] == "NOT_VERIFIED"
    assert projection["overall_verdict"] == "FAIL"
    assert projection["verification_status"] == "NOT_VERIFIED"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1 /* comment; */",
        "SELECT '-- not a comment; UPDATE x'",
        "SELECT $$-- not a comment; DELETE FROM x$$",
    ],
)
def test_r6_semicolons_inside_lexical_regions_do_not_split_statements(sql: str) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["multi_statement_detected"] is False
    assert statement["purity_verdict"] == "PASS"


def test_r6_nested_block_comment_state_fails_closed() -> None:
    projection = _validate_statement_purity([{"sql": "/* outer /* inner */ SELECT 1"}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "UNKNOWN"
    assert statement["lexical_valid"] is False
    assert statement["grammar_supported"] is False
    assert statement["statement_complete"] is False
    assert statement["purity_verdict"] == "NOT_VERIFIED"


def test_r6_unsupported_complete_syntax_is_not_verified() -> None:
    projection = _validate_statement_purity([{"sql": "EXPLAIN SELECT 1"}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "UNKNOWN"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is False
    assert statement["statement_complete"] is True
    assert statement["unknown_detected"] is True
    assert statement["purity_verdict"] == "NOT_VERIFIED"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1 +",
        "SELECT 1::",
        "SELECT 1,",
        "SELECT 1 FROM t WHERE x =",
        "SELECT (1 +)",
        "SELECT func(1,)",
        "SELECT 1 * / 2",
        "SELECT 1,,2",
        "SELECT 1 FROM t WHERE x = (1 2)",
        "SELECT DISTINCT FROM t",
        "SELECT CASE",
        "SELECT 1 FROM t JOIN u",
        "SELECT 1 FROM t WHERE x = ()",
        "SELECT 1 FROM t WHERE x IN",
        "SELECT DISTINCT ON () 1 FROM t",
        "SELECT 1 FROM t JOIN u USING ()",
        "SELECT 1 ORDER BY x NULLS",
        "SELECT 1 FROM t WHERE x IS NOT",
        "SELECT 1 FROM t WHERE x LIKE",
        "SELECT 1 FROM t WHERE x IN (1) OR",
        "SELECT 1 FROM t FOR NO KEY",
        "SELECT 1 FROM t FOR",
        "SELECT 1 FROM t WHERE x IS DISTINCT",
        "SELECT 1 FROM t WHERE x IS NOT DISTINCT",
        "SELECT 1 ORDER BY NULLS FIRST",
        "SELECT 1 FETCH FIRST",
        "SELECT DISTINCT ON (x) FROM t",
        "SELECT CASE WHEN x THEN END FROM t",
        "SELECT 1 . * FROM t",
        "SELECT TRUE.* FROM t",
        "SELECT EXISTS (DELETE FROM t)",
        "SELECT 1 FROM t WHERE x = (DELETE FROM t)",
        "SELECT CASE x THEN :v END FROM t",
        "SELECT CASE WHEN x THEN 1 ELSE 2 ELSE 3 END FROM t",
        "SELECT CASE ELSE 1 END FROM t",
        "SELECT 1 ORDER BY x COLLATE",
        "SELECT 1 ORDER BY x ASC DESC",
        "SELECT 1 ORDER BY x NULLS FIRST NULLS LAST",
        "SELECT 1 ORDER BY x ASC FIRST",
        "SELECT 1 FETCH FIRST ROWS ONLY ASC",
        "SELECT 1 FROM JOIN u ON x",
        "SELECT 1 FROM AS x",
        "SELECT 1 FROM t JOIN u ON x USING (id)",
        "SELECT 1 ORDER BY x WHERE y",
        "SELECT 1 GROUP BY x WHERE y",
        "SELECT 1 LIMIT 1 WHERE y",
        "SELECT 1 UPDATE t",
        "SELECT 1 FROM t UPDATE",
        "SELECT 1 FROM t WHERE (x AND) AND y",
        "SELECT 1 ORDER BY x NULLS FIRST DESC",
        "SELECT 1 ORDER BY x NULLS FIRST ASC",
        "SELECT DISTINCT ON (x FROM y) 1 FROM t",
        "SELECT 1 FROM t ON x",
        "SELECT 1 FROM t USING (id)",
        "SELECT 1 ORDER BY x UNION SELECT 2",
        "SELECT 1 LIMIT 1 UNION SELECT 2",
        "SELECT 1 FETCH FIRST 1 ROW ONLY UNION SELECT 2",
        "SELECT 1 FROM t WHERE x BETWEEN",
        "SELECT 1 FROM t WHERE x BETWEEN 1",
        "SELECT 1 FROM t WHERE x = ANY",
        "SELECT 1 FROM t WHERE (x BETWEEN 1) AND y",
        "SELECT func(x FROM) FROM t",
        "SELECT DISTINCT ON (x AND) 1 FROM t",
        "SELECT DISTINCT ON (x BETWEEN) 1 FROM t",
        "SELECT DISTINCT ON (x = ANY) 1 FROM t",
        "SELECT 1 FROM t WHERE = 1",
        "SELECT 1 FROM t WHERE @> x",
        "SELECT 1 FROM t WHERE IN (1)",
        "SELECT 1 FROM t WHERE IS TRUE",
        "SELECT 1 FROM t WHERE BETWEEN 1 AND 2",
        "SELECT 1 FROM t WHERE x = SOME",
        "SELECT func(x WHERE) FROM t",
        "SELECT func(x GROUP) FROM t",
        "SELECT func(x ORDER) FROM t",
        "SELECT func(x USING) FROM t",
        "SELECT 1 FROM t WHERE AND x",
        "SELECT 1 FROM t WHERE OR x",
        "SELECT 1 FROM t WHERE (= 1) AND y",
        "SELECT 1 FROM t WHERE (@> x) AND y",
        "SELECT func(SELECT x WHERE y) FROM t",
        "SELECT DISTINCT ON (AND x) 1 FROM t",
        "SELECT DISTINCT ON (OR x) 1 FROM t",
        "SELECT func(x, = 1) FROM t",
        "SELECT ARRAY[1, = 2]",
        "SELECT 1 FROM t WHERE x = ANY (ARRAY[,1])",
        "SELECT COUNT(*) FILTER (WHERE)",
        "SELECT COUNT(*) FILTER (WHERE AND x)",
        "SELECT array_agg(x ORDER BY)",
        "SELECT func(x FILTER (WHERE y)) FROM t",
        "SELECT 1 FROM t WHERE NOT AND x",
        "SELECT 1 FROM t WHERE x NOT AND y",
        "SELECT 1 FROM t WHERE x IS AND y",
        "SELECT 1 FROM t WHERE x LIKE AND y",
        "SELECT 1 FROM t WHERE x BETWEEN 1 AND AND 2",
        "SELECT 1 FROM t WHERE NOT ANY (ARRAY[1])",
        "SELECT 1 FROM t WHERE x + ANY (ARRAY[1])",
        "SELECT 1 FROM t WHERE x = NOT ANY (ARRAY[1])",
        "SELECT array_agg(x ORDER BY = 1)",
        "SELECT array_agg(x ORDER BY @> y)",
        "SELECT COUNT(*) FILTER (WHERE x) FILTER (WHERE y)",
        "SELECT 1 FROM t WHERE x AS y",
        "SELECT 1 FROM t WHERE x NULLS FIRST",
        "SELECT 1 FROM t WHERE (x ONLY)",
        "SELECT 1 HAVING NULLS FIRST",
        "SELECT 1 WINDOW x",
        "SELECT 1 NULLS FIRST",
        "SELECT x ONLY",
        "SELECT x DESC",
        "SELECT x BY y",
        "SELECT 1 FROM t WHERE x JOIN y",
        "SELECT 1 FROM t WHERE x ON y",
        "SELECT 1 FROM t WHERE x USING y",
        "SELECT x JOIN y",
        "SELECT x ON y",
        "SELECT x USING y",
        "SELECT x AS y AS z FROM t",
        "SELECT 1 FROM t AS x AS y",
        "SELECT 1 FROM t JOIN u ON x AS y",
        "SELECT 1 GROUP BY x AS y",
        "SELECT 1 ORDER BY x AS y",
        "SELECT 1 FROM t JOIN u ON NULLS FIRST",
        "SELECT 1 FROM t WHERE x, y",
        "SELECT 1 LIMIT 1, 2",
        "SELECT 1 OFFSET 1, 2",
        "SELECT 1 FETCH FIRST 1, 2 ROWS ONLY",
        "SELECT AS x FROM t",
        "SELECT x, AS y FROM t",
        "SELECT x AS (y) FROM t",
        "SELECT 1 GROUP BY NULLS FIRST",
        "SELECT 1 ORDER BY x ONLY",
        "SELECT 1 LIMIT NULLS FIRST",
        "SELECT 1 OFFSET NULLS FIRST",
        "SELECT 1 FETCH FIRST NULLS FIRST ROWS ONLY",
        "SELECT 1 FROM t NULLS FIRST",
        "SELECT 1 FROM t JOIN AS u ON x",
        "SELECT 1 FROM t JOIN USING (x) ON y",
        "SELECT (x ASC) FROM t",
        "SELECT f(x BY y) FROM t",
        "SELECT 1 GROUP BY (x ASC)",
        "SELECT 1 ORDER BY (x ASC)",
        "SELECT 1 OFFSET (x ASC)",
        "SELECT 1 FETCH FIRST (x ASC) ROWS ONLY",
        "SELECT array_agg(x ORDER BY (y ASC)) FROM t",
        "SELECT 1 ORDER BY (x NULLS FIRST)",
        "SELECT 1 FROM t JOIN u ON (x NULLS FIRST)",
        "SELECT 1 FROM t JOIN u USING (x NULLS FIRST)",
        "SELECT array_agg(x ORDER BY (y NULLS FIRST)) FROM t",
        "SELECT f(x AT y) FROM t",
        "SELECT f(x NULL y) FROM t",
        "SELECT f(x ROWS y) FROM t",
        "SELECT f(x NO KEY y) FROM t",
        "SELECT f(x KEY SHARE y) FROM t",
        "SELECT 1 FROM t WHERE x AT y",
        "SELECT 1 ORDER BY (x AT y)",
        "SELECT array_agg(x ORDER BY y NO KEY) FROM t",
        "SELECT array_agg(x ORDER BY y ROWS) FROM t",
        "SELECT array_agg(x ORDER BY y KEY SHARE) FROM t",
    ],
)
def test_r6_incomplete_expression_tokens_fail_closed(sql: str) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "UNKNOWN"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is False
    assert statement["statement_complete"] is False
    assert statement["purity_verdict"] == "NOT_VERIFIED"


def test_r6_nested_subquery_projection_alias_remains_supported() -> None:
    projection = _validate_statement_purity([{"sql": "SELECT EXISTS (SELECT x AS y FROM t)"}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is True
    assert statement["statement_complete"] is True
    assert statement["purity_verdict"] == "PASS"


def test_r6_supported_postgresql_operator_remains_read_only() -> None:
    projection = _validate_statement_purity([{"sql": "SELECT payload @> :filter FROM records"}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is True
    assert statement["statement_complete"] is True
    assert statement["purity_verdict"] == "PASS"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1 FROM t WHERE (x = 1)",
        "SELECT 1 FROM t WHERE (x = :a)",
        "SELECT 1 FROM t WHERE (x = %(a)s)",
    ],
)
def test_r6_parenthesized_predicates_remain_supported(sql: str) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is True
    assert statement["statement_complete"] is True
    assert statement["purity_verdict"] == "PASS"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM t",
        "SELECT t.* FROM t",
        "SELECT 1 UNION SELECT 2",
        "SELECT 1 UNION ALL SELECT 2",
        "SELECT EXISTS (SELECT 1 FROM t)",
        "SELECT ARRAY[1, 2]",
        "SELECT DISTINCT ON (x) x FROM t",
        "SELECT CASE WHEN true THEN 1 ELSE 2 END FROM t",
        "SELECT 1 FETCH FIRST 1 ROWS ONLY",
        "SELECT 1 FROM t WHERE x = ANY (ARRAY[1, 2])",
        "SELECT 1 FROM t WHERE x NOT IN (1)",
        "SELECT 1 FROM t WHERE x NOT LIKE y",
        "SELECT COUNT(*) FILTER (WHERE x) FROM t",
        "SELECT array_agg(x ORDER BY y) FROM t",
        "SELECT array_agg(x ORDER BY y ASC) FROM t",
        "SELECT array_agg(x ORDER BY y DESC NULLS LAST) FROM t",
        "SELECT 1 FROM t WHERE x IS DISTINCT FROM y",
        "SELECT 1 FROM t WHERE x IS NOT DISTINCT FROM y",
        "SELECT 1 FROM t WHERE x IS UNKNOWN",
        "SELECT 1 FROM t WHERE x IS NOT UNKNOWN",
        "SELECT a.id FROM a AS a JOIN b AS b ON b.id = a.id",
    ],
)
def test_r6_common_read_select_shapes_remain_supported(sql: str) -> None:
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT"
    assert statement["lexical_valid"] is True
    assert statement["grammar_supported"] is True
    assert statement["statement_complete"] is True
    assert statement["purity_verdict"] == "PASS"


def test_r6_select_into_after_from_is_rejected_as_write() -> None:
    projection = _validate_statement_purity([{"sql": "SELECT 1 FROM t INTO new_table"}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "UNKNOWN"
    assert statement["select_into_detected"] is True
    assert statement["purity_verdict"] == "NOT_VERIFIED"
    assert projection["overall_verdict"] == "FAIL"


def test_r6_nested_locking_read_remains_locking_classification() -> None:
    projection = _validate_statement_purity(
        [{"sql": "SELECT EXISTS (SELECT 1 FROM t FOR NO KEY UPDATE)"}]
    )
    statement = projection["statements"][0]

    assert statement["statement_class"] == "READ_SELECT_LOCKING"
    assert statement["locking_detected"] is True
    assert statement["purity_verdict"] == "FAIL"


def test_r6_nested_data_modifying_cte_is_rejected() -> None:
    sql = "SELECT 1 FROM (WITH changed AS (UPDATE t SET x = 1 RETURNING x) SELECT x FROM changed) q"
    projection = _validate_statement_purity([{"sql": sql}])
    statement = projection["statements"][0]

    assert statement["statement_class"] == "DATA_MODIFYING_CTE"
    assert statement["mutating_cte_detected"] is True
    assert statement["purity_verdict"] == "FAIL"
    assert projection["overall_verdict"] == "FAIL"


def test_r6_impossible_pass_projection_is_rejected() -> None:
    statement = {
        "sql": "SELECT 1",
        "lexical_valid": False,
        "grammar_supported": True,
        "statement_complete": True,
        "statement_class": "READ_SELECT",
        "purity_verdict": "PASS",
    }

    with pytest.raises(PR18EvidenceError, match="inconsistent purity evidence"):
        pr18_evidence.validate_statement_purity([statement])


def test_r6_contradictory_rejection_reason_fields_are_rejected() -> None:
    statement = {
        "sql": "SELECT 1",
        "classification": "READ_SELECT",
        "statement_class": "READ_SELECT",
        "lexical_valid": True,
        "grammar_supported": True,
        "statement_complete": True,
        "mutating_cte_detected": True,
        "select_into_detected": False,
        "locking_detected": False,
        "multi_statement_detected": False,
        "ambiguity_detected": True,
        "unknown_detected": True,
        "read_write_verdict": "FAIL",
        "locking_verdict": "PASS",
        "purity_verdict": "PASS",
    }

    with pytest.raises(PR18EvidenceError, match="inconsistent purity evidence"):
        pr18_evidence.validate_statement_purity([statement])


def test_query_contract_rejects_missing_required_relation() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]
    statements = [
        _statement(
            (
                "SELECT audit_findings.id FROM audit_findings "
                "WHERE audit_findings.project_id = :project"
            ),
            relations=[],
        )
    ]

    with pytest.raises(PR18EvidenceError, match="MISSING_REQUIRED_RELATION"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_missing_frozen_predicate() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]
    statements = [
        _statement(
            (
                "SELECT audit_findings.id FROM audit_findings "
                "WHERE audit_findings.project_id = :project"
            ),
            relations=["audit_findings"],
        )
    ]

    with pytest.raises(PR18EvidenceError, match="MISSING_REQUIRED_PREDICATE"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_wrong_join_topology() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1] = _statement(
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs "
        "ON runs.project_id = run_artifact_inputs.artifact_version_id "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project",
        relations=["run_artifact_inputs", "runs"],
        nodes=["Nested Loop", "Index Scan"],
        join_types=["Inner"],
    )

    with pytest.raises(PR18EvidenceError, match="INVALID_JOIN_TOPOLOGY"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_unexpected_extra_relation_in_isolation() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements.append(
        _statement(
            "SELECT unauthorized_relation.id FROM unauthorized_relation "
            "WHERE unauthorized_relation.id = :id",
            relations=["unauthorized_relation"],
        )
    )

    with pytest.raises(PR18EvidenceError, match="UNEXPECTED_RELATION"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_cartesian_join_in_isolation() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1] = _statement(
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs ON true "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project",
        relations=["run_artifact_inputs", "runs"],
        nodes=["Nested Loop", "Index Scan"],
        join_types=["Inner"],
    )

    with pytest.raises(PR18EvidenceError, match="CARTESIAN_JOIN"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_disconnected_join_graph_in_isolation() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1] = _statement(
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs, runs "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project",
        relations=["run_artifact_inputs", "runs"],
    )

    with pytest.raises(PR18EvidenceError, match="INVALID_JOIN_TOPOLOGY|NOT_VERIFIED"):
        validate_query_contract(expectation, statements)


def test_query_contract_accepts_legal_production_topology_control() -> None:
    projection = validate_query_contract(_downstream_expectation(), _valid_downstream_statements())

    assert projection["unexpected_relations"] == []
    assert projection["missing_relations"] == []
    assert projection["predicate_verdict"] == "PASS"
    assert projection["topology_verdict"] == "PASS"
    assert projection["cartesian_verdict"] == "PASS"
    assert projection["overall_verdict"] == "PASS"


def test_query_contract_rejects_unparseable_topology_fail_closed() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1]["sql"] = (
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project"
    )

    with pytest.raises(
        PR18EvidenceError,
        match="CARTESIAN_JOIN|INVALID_JOIN_TOPOLOGY|NOT_VERIFIED",
    ):
        validate_query_contract(expectation, statements)
