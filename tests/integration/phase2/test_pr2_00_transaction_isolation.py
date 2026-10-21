from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def test_phase2_command_transaction_uses_serializable_isolation() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        with SqlAlchemyUnitOfWork(factory) as uow:
            uow.begin_serializable()
            assert uow.phase2_identity.transaction_isolation() == "serializable"
            uow.rollback()
    finally:
        engine.dispose()
