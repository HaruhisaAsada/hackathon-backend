import argparse
import sqlite3

from sqlalchemy import text

from db import engine


def _chunked(iterable, size):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _create_tables(conn, *, truncate: bool) -> None:
    if truncate:
        conn.execute(text("DROP TABLE IF EXISTS pid_matcher_token_index"))
        conn.execute(text("DROP TABLE IF EXISTS pid_matcher_tokens"))
        conn.execute(text("DROP TABLE IF EXISTS pid_matcher_items"))

    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS pid_matcher_items ("
            "  idx INT PRIMARY KEY,"
            "  title MEDIUMTEXT NOT NULL,"
            "  pid VARCHAR(64) NOT NULL"
            ") ENGINE=InnoDB"
        )
    )
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS pid_matcher_tokens ("
            "  token_id INT PRIMARY KEY,"
            "  token VARCHAR(255) NOT NULL,"
            "  UNIQUE KEY tokens_token_uq (token)"
            ") ENGINE=InnoDB"
        )
    )
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS pid_matcher_token_index ("
            "  token_id INT NOT NULL,"
            "  idx INT NOT NULL,"
            "  KEY token_id_idx (token_id, idx)"
            ") ENGINE=InnoDB"
        )
    )


def _insert_items(conn, src_cur, batch_size: int) -> None:
    src_cur.execute("SELECT idx, title, pid FROM items")
    rows = src_cur.fetchall()
    for chunk in _chunked(rows, batch_size):
        payload = [{"idx": r[0], "title": r[1], "pid": r[2]} for r in chunk]
        conn.execute(
            text("INSERT INTO pid_matcher_items (idx, title, pid) VALUES (:idx, :title, :pid)"),
            payload,
        )


def _insert_tokens(conn, src_cur, batch_size: int) -> None:
    src_cur.execute("SELECT token_id, token FROM tokens")
    rows = src_cur.fetchall()
    for chunk in _chunked(rows, batch_size):
        payload = [{"token_id": r[0], "token": r[1]} for r in chunk]
        conn.execute(
            text("INSERT INTO pid_matcher_tokens (token_id, token) VALUES (:token_id, :token)"),
            payload,
        )


def _insert_token_index(conn, src_cur, batch_size: int) -> None:
    src_cur.execute("SELECT token_id, idx FROM token_index")
    while True:
        rows = src_cur.fetchmany(batch_size)
        if not rows:
            break
        payload = [{"token_id": r[0], "idx": r[1]} for r in rows]
        conn.execute(
            text("INSERT INTO pid_matcher_token_index (token_id, idx) VALUES (:token_id, :idx)"),
            payload,
        )


def load_sqlite_to_mysql(sqlite_path: str, *, batch_size: int, truncate: bool) -> None:
    src_conn = sqlite3.connect(sqlite_path)
    src_cur = src_conn.cursor()

    conn = engine.connect()
    try:
        with conn.begin():
            _create_tables(conn, truncate=truncate)

        with conn.begin():
            _insert_items(conn, src_cur, batch_size)

        with conn.begin():
            _insert_tokens(conn, src_cur, batch_size)

        with conn.begin():
            _insert_token_index(conn, src_cur, batch_size)
    finally:
        src_cur.close()
        src_conn.close()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True, help="Path to source sqlite file")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--truncate", action="store_true", help="Drop and recreate tables before loading")
    args = parser.parse_args()
    load_sqlite_to_mysql(args.sqlite, batch_size=args.batch_size, truncate=args.truncate)


if __name__ == "__main__":
    main()
