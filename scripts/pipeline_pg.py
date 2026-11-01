"""Host-only PostgreSQL verification: four identity pins and one random database."""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from uuid import uuid4
from xml.etree import ElementTree

from scripts.pipeline_protocol import atomic_write, encoded, require
from scripts.pipeline_sessions import stop_group
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

PINS = (
    "RB_TEST_ADMIN_USER",
    "RB_TEST_ADMIN_PORT",
    "RB_TEST_ADMIN_DATA_DIRECTORY",
    "RB_TEST_ADMIN_SYSTEM_ID",
)


def validate_environment(env):
    require(type(env) is dict, "PG environment type")
    if not env:
        return
    require(set(env) == {"RB_TEST_ADMIN_URL", *PINS}, "PG requires explicit four identity pins")
    url = make_url(env["RB_TEST_ADMIN_URL"])
    require(
        url.drivername == "postgresql+psycopg"
        and url.database == "postgres"
        and url.host in ("localhost", "127.0.0.1", "::1")
        and not url.query,
        "local TCP disposable admin only",
    )
    require(
        str(url.username) == env[PINS[0]] and str(url.port or 5432) == env[PINS[1]],
        "PG URL/pin mismatch",
    )
    require(all(type(env[k]) is str and env[k] for k in PINS), "PG pin values")


@contextmanager
def isolated_environment(env):
    validate_environment(env)
    require(env, "PG stage held: explicit environment/four pins missing")
    engine = create_engine(env["RB_TEST_ADMIN_URL"])
    name = "researchbase_throughput_test_" + uuid4().hex
    created = False
    try:
        with engine.connect() as connection:
            actual = connection.execute(
                text("""SELECT current_user,current_database(),
                current_setting('port'),current_setting('data_directory'),
                (SELECT system_identifier FROM pg_control_system()),
                current_setting('server_version_num')""")
            ).one()
        require(
            actual[1] == "postgres" and 180000 <= int(actual[5]) < 190000, "PG18 admin identity"
        )
        require(
            tuple(map(str, (actual[0], actual[2], actual[3], actual[4])))
            == tuple(env[k] for k in PINS),
            "PG four-pin identity mismatch",
        )
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            require(
                not connection.execute(
                    text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:n)"), dict(n=name)
                ).scalar_one(),
                "random PG database exists",
            )
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        yield {
            **env,
            "DATABASE_URL": make_url(env["RB_TEST_ADMIN_URL"])
            .set(database=name)
            .render_as_string(hide_password=False),
        }
    finally:
        if created:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname=:n AND pid<>pg_backend_pid()"
                    ),
                    dict(n=name),
                )
                connection.execute(text(f'DROP DATABASE "{name}"'))
        engine.dispose()


def execute(argv, checkout, env, output, terminal):
    """Joined process group; never let an unjoined PG process free its lease."""
    atomic_write(terminal, encoded(dict(descendants_stopped=False)))
    with output.open("xb") as stream:
        process = subprocess.Popen(
            argv,
            cwd=checkout,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            process.wait(timeout=7200)
        finally:
            stopped = stop_group(process.pid, process.poll)
            atomic_write(terminal, encoded(dict(descendants_stopped=stopped)))
    require(stopped, "unjoined PG descendants; resource must remain quarantined")
    require(output.stat().st_size <= 16 * 1024 * 1024, "PG output evidence budget")
    return process.returncode


def passed_cases(xml):
    require(
        xml.is_file() and not xml.is_symlink() and xml.stat().st_size <= 8 * 1024 * 1024,
        "missing/unsafe PG JUnit evidence",
    )
    tree = ElementTree.fromstring(xml.read_bytes())
    require(tree.tag in ("testsuites", "testsuite"), "unknown PG JUnit root")
    suites = [tree, *tree.findall(".//testsuite")]
    require(
        all(
            all(int(suite.get(key, "0")) == 0 for key in ("errors", "failures", "skipped"))
            for suite in suites
        ),
        "PG JUnit suite reports skipped/failed/error cases",
    )
    cases = tree.findall(".//testcase")
    require(
        bool(cases)
        and all(
            not list(case) or all(node.tag not in ("skipped", "failure", "error") for node in case)
            for case in cases
        ),
        "PG acceptance needs actual passes and zero skipped/failed/error cases",
    )
    return len(cases)
