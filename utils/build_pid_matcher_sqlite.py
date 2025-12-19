import argparse
import os
import pickle
import sqlite3


def _chunked(iterable, size):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def build_sqlite(
    pkl_path: str,
    sqlite_path: str,
    *,
    batch_size: int = 10000,
    max_token_df: int | None = None,
) -> None:
    with open(pkl_path, "rb") as f:
        obj = pickle.load(f)

    titles = obj["titles_flat"]
    pids = obj["pids_flat"]
    token2idx = obj["token2idx"]

    if len(titles) != len(pids):
        raise ValueError("titles_flat and pids_flat length mismatch")

    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)

    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=OFF")
    cur.execute("PRAGMA synchronous=OFF")
    cur.execute("CREATE TABLE items (idx INTEGER PRIMARY KEY, title TEXT NOT NULL, pid TEXT NOT NULL)")
    cur.execute("CREATE TABLE tokens (token_id INTEGER PRIMARY KEY, token TEXT NOT NULL)")
    cur.execute("CREATE UNIQUE INDEX tokens_token_uq ON tokens(token)")
    cur.execute("CREATE TABLE token_index (token_id INTEGER NOT NULL, idx INTEGER NOT NULL)")
    cur.execute("CREATE INDEX token_index_token_id_idx ON token_index(token_id, idx)")
    conn.commit()

    items_iter = ((i, titles[i], pids[i]) for i in range(len(titles)))
    for chunk in _chunked(items_iter, batch_size):
        cur.executemany("INSERT INTO items (idx, title, pid) VALUES (?, ?, ?)", chunk)
        conn.commit()

    if max_token_df is not None:
        token2idx = {tok: idxs for tok, idxs in token2idx.items() if len(idxs) <= max_token_df}

    tokens_iter = ((i, tok) for i, tok in enumerate(token2idx.keys(), start=1))
    for chunk in _chunked(tokens_iter, batch_size):
        cur.executemany("INSERT INTO tokens (token_id, token) VALUES (?, ?)", chunk)
        conn.commit()

    token_id_map = {tok: i for i, tok in enumerate(token2idx.keys(), start=1)}
    token_rows = (
        (token_id_map[tok], idx)
        for tok, idxs in token2idx.items()
        for idx in idxs
    )
    for chunk in _chunked(token_rows, batch_size):
        cur.executemany("INSERT INTO token_index (token_id, idx) VALUES (?, ?)", chunk)
        conn.commit()

    cur.close()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkl", required=True, help="Path to pid_matcher.pkl")
    parser.add_argument("--out", required=True, help="Path to output sqlite file")
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument(
        "--max-token-df",
        type=int,
        default=1000,
        help="Drop tokens that appear in more than this many items (stopwordize).",
    )
    args = parser.parse_args()
    max_token_df = args.max_token_df if args.max_token_df > 0 else None
    build_sqlite(args.pkl, args.out, batch_size=args.batch_size, max_token_df=max_token_df)


if __name__ == "__main__":
    main()
