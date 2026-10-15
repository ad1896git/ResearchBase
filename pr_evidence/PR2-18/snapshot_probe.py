"""Disposable PostgreSQL probe of the specified direct-SQL trigger lock sequence."""

import os
import threading
from uuid import uuid4

import psycopg
from sqlalchemy.engine import make_url

url = make_url(os.environ["RB_TEST_ADMIN_URL"])
kwargs = dict(url.query)
kwargs.update(
    user=url.username, password=url.password, host=url.host, port=url.port, dbname="postgres"
)
kwargs = {key: value for key, value in kwargs.items() if value is not None}
name = "researchbase_pr2_test_" + uuid4().hex
with psycopg.connect(**kwargs, autocommit=True) as admin:
    admin.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(name)))
    kwargs["dbname"] = name
    try:
        with psycopg.connect(**kwargs, autocommit=True) as setup:
            print("server_version:", setup.execute("SHOW server_version").fetchone()[0])
            setup.execute("CREATE TABLE validity (id INT PRIMARY KEY, usable BOOLEAN NOT NULL)")
            setup.execute("INSERT INTO validity VALUES (1,TRUE)")
            setup.execute("CREATE TABLE captures (id INT PRIMARY KEY, saw_usable BOOLEAN)")
            setup.execute("""CREATE FUNCTION capture_guard() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  LOCK TABLE validity IN SHARE MODE;
                  SELECT usable INTO NEW.saw_usable FROM validity WHERE id=1;
                  IF NOT NEW.saw_usable THEN RAISE EXCEPTION 'invalid input'; END IF;
                  RETURN NEW;
                END $$""")
            setup.execute(
                "CREATE TRIGGER guard BEFORE INSERT ON captures "
                "FOR EACH ROW EXECUTE FUNCTION capture_guard()"
            )
        writer = psycopg.connect(**kwargs)
        capture = psycopg.connect(**kwargs)
        observer = psycopg.connect(**kwargs, autocommit=True)
        try:
            writer.execute("UPDATE validity SET usable=FALSE WHERE id=1")
            writer_pid = writer.info.backend_pid
            capture_pid = capture.info.backend_pid
            capture.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")
            capture.execute("SET LOCAL lock_timeout='10s'")
            errors = []

            def record():
                try:
                    capture.execute("INSERT INTO captures (id) VALUES (1)")
                    capture.commit()
                except Exception as exc:
                    errors.append((getattr(exc, "sqlstate", None), type(exc).__name__))
                    capture.rollback()

            thread = threading.Thread(target=record)
            thread.start()
            witnessed = False
            for _ in range(200):
                blocking = observer.execute(
                    "SELECT pg_blocking_pids(%s)", (capture_pid,)
                ).fetchone()[0]
                if writer_pid in blocking:
                    witnessed = True
                    print("lock witness: capture backend blocked by validity writer:", True)
                    break
                threading.Event().wait(0.01)
            if not witnessed:
                raise RuntimeError("lock wait not witnessed")
            writer.commit()
            thread.join(12)
            if thread.is_alive():
                raise RuntimeError("capture did not finish")
            print("capture errors:", errors)
            print(
                "current validity:", observer.execute("SELECT usable FROM validity").fetchone()[0]
            )
            print(
                "persisted capture:",
                observer.execute("SELECT id,saw_usable FROM captures").fetchall(),
            )
        finally:
            writer.close()
            capture.close()
            observer.close()
    finally:
        admin.execute(
            psycopg.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(psycopg.sql.Identifier(name))
        )
