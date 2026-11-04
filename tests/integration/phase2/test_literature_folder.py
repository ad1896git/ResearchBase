"""Literature folder scans on a disposable PostgreSQL database (migration 0084)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from researchbase.adapters.literature_folder import scan_folder
from researchbase.application.literature_folder import LiteratureFolderService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


class _Ticks:
    """A clock that moves forward one second per read, so scans order deterministically."""

    def __init__(self) -> None:
        self._now = datetime(2026, 11, 3, tzinfo=UTC)

    def now(self) -> datetime:
        self._now += timedelta(seconds=1)
        return self._now


def _allow(uow, project_id, write, actor_id) -> None:
    return None


def _migrate(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def _seed(url: str) -> tuple[UUID, UUID]:
    actor, project = uuid4(), uuid4()
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'Owner', now())"
                ),
                {"id": actor},
            )
            conn.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Folder project', :actor, now())"
                ),
                {"id": project, "actor": actor},
            )
    finally:
        engine.dispose()
    return actor, project


def test_migration_downgrades_once_and_reupgrades(phase2_database_url):
    _migrate(phase2_database_url)
    engine = create_engine(phase2_database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    try:
        # Head is 0085 now; a single downgrade reverts 0085, so step back to 0083 first.
        command.downgrade(config, "0083_bearing_evaluation_guards")
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT to_regclass('literature_folder_observations') IS NOT NULL")
            ).scalar_one()
        assert exists is False
        command.upgrade(config, "head")
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT to_regclass('literature_folder_observations') IS NOT NULL")
            ).scalar_one()
        assert exists is True
    finally:
        engine.dispose()


def test_observations_are_append_only(phase2_database_url):
    _migrate(phase2_database_url)
    actor, project = _seed(phase2_database_url)
    engine = create_engine(phase2_database_url)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO literature_folder_observations (id, project_id, scan_id, "
                    "folder_path, file_path, observation_status, content_sha256, size_bytes, "
                    "file_mtime, observed_by, request_id, observed_at) VALUES (:id, :p, :s, "
                    "'/f', 'a.txt', 'PRESENT', :h, 1, now(), :a, :r, now())"
                ),
                {
                    "id": uuid4(),
                    "p": project,
                    "s": uuid4(),
                    "h": "a" * 64,
                    "a": actor,
                    "r": uuid4(),
                },
            )
        with pytest.raises(Exception, match="append-only"), engine.begin() as conn:
            conn.execute(text("UPDATE literature_folder_observations SET file_path = 'x'"))
        with pytest.raises(Exception, match="append-only"), engine.begin() as conn:
            conn.execute(text("DELETE FROM literature_folder_observations"))
    finally:
        engine.dispose()


def test_scan_records_new_moved_duplicate_and_missing(phase2_database_url, tmp_path, monkeypatch):
    _migrate(phase2_database_url)
    actor, project = _seed(phase2_database_url)
    monkeypatch.setenv("DATABASE_URL", phase2_database_url)
    sessions = create_session_factory(create_database_engine())
    service = LiteratureFolderService(lambda: SqlAlchemyUnitOfWork(sessions), _Ticks(), _allow)
    folder = tmp_path / "papers"
    folder.mkdir()
    folder_path = str(folder.resolve())

    (folder / "a.txt").write_text("study A DOI 10.1111/a.1", encoding="utf-8")
    (folder / "b.txt").write_text("study B", encoding="utf-8")
    first = service.scan(
        project_id=project,
        folder=folder_path,
        files=scan_folder(folder),
        actor_id=actor,
        request_id=uuid4(),
    )
    assert first["new"] == ["a.txt", "b.txt"]

    (folder / "b.txt").rename(folder / "b-moved.txt")
    (folder / "copy-of-a.txt").write_text("study A DOI 10.1111/a.1", encoding="utf-8")
    second = service.scan(
        project_id=project,
        folder=folder_path,
        files=scan_folder(folder),
        actor_id=actor,
        request_id=uuid4(),
    )
    assert second["moved"] == [{"from": "b.txt", "to": "b-moved.txt"}]
    assert second["new"] == ["copy-of-a.txt"]
    assert second["duplicates"] == [["a.txt", "copy-of-a.txt"]]

    (folder / "a.txt").unlink()
    third = service.scan(
        project_id=project,
        folder=folder_path,
        files=scan_folder(folder),
        actor_id=actor,
        request_id=uuid4(),
    )
    assert third["missing"] == ["a.txt"]

    status = service.status(project_id=project, folder=folder_path, actor_id=actor)
    assert [item["file_path"] for item in status["files"]] == ["b-moved.txt", "copy-of-a.txt"]
    assert status["files"][1]["doi"] == "10.1111/a.1"
    # b.txt moved away in the second scan, so its old path is recorded as missing.
    assert status["missing"] == ["a.txt", "b.txt"]


def test_refused_scan_writes_nothing(phase2_database_url, tmp_path, monkeypatch):
    _migrate(phase2_database_url)
    actor, project = _seed(phase2_database_url)
    monkeypatch.setenv("DATABASE_URL", phase2_database_url)
    sessions = create_session_factory(create_database_engine())

    def refuse(uow, project_id, write, actor_id):
        raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority is unavailable")

    folder = tmp_path / "refused"
    folder.mkdir()
    (folder / "x.txt").write_text("x", encoding="utf-8")
    service = LiteratureFolderService(lambda: SqlAlchemyUnitOfWork(sessions), _Ticks(), refuse)
    with pytest.raises(ResearchBaseError):
        service.scan(
            project_id=project,
            folder=str(folder),
            files=scan_folder(folder),
            actor_id=actor,
            request_id=uuid4(),
        )
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT count(*) FROM literature_folder_observations")
            ).scalar_one()
    finally:
        engine.dispose()
    assert count == 0
