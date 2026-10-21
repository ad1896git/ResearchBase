"""Read-only safety snapshot time. The Application owns one formal-read transaction."""

from sqlalchemy import text


def snapshot_time(session):
    return session.execute(text("SELECT transaction_timestamp()")).scalar_one()
