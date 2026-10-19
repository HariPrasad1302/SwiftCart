import pytest
from sqlalchemy import event

from app.core.db import engine


@pytest.fixture
def query_counter():
    count = {"n": 0}

    def before_cursor_execute(conn, cursor, statement, params, context, executemany):
        count["n"] += 1

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    yield count
    event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)