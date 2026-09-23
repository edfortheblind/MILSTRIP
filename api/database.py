"""Shared local database connection and transaction boundary."""
import os
from contextlib import contextmanager

import psycopg
from fastapi import HTTPException


def connect():
    value = os.getenv("MILSTRIP_DATABASE_URL")
    if not value:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return psycopg.connect(value, connect_timeout=5)


@contextmanager
def connection():
    try:
        with connect() as database:
            database.execute("SET LOCAL lock_timeout = '5s'")
            database.execute("SET LOCAL statement_timeout = '15s'")
            yield database
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
