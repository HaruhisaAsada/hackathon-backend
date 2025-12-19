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


def build_sqlite(pkl_path: str, sqlite_path: str, *, batch_size: int = 10000) -> None:
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
    cur.execute("CREATE TABLE token_index (token TEXT NOT NULL, idx INTEGER NOT NULL)")
    cur.execute("CREATE INDEX token_index_token_idx ON token_index(token, idx)")
    conn.commit()

    items_iter = ((i, titles[i], pids[i]) for i in range(len(titles)))
    for chunk in _chunked(items_iter, batch_size):
        cur.executemany("INSERT INTO items (idx, title, pid) VALUES (?, ?, ?)", chunk)
        conn.commit()

    token_rows = ((tok, idx) for tok, idxs in token2idx.items() for idx in idxs)
    for chunk in _chunked(token_rows, batch_size):
        cur.executemany("INSERT INTO token_index (token, idx) VALUES (?, ?)", chunk)
        conn.commit()

    cur.close()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkl", required=True, help="Path to pid_matcher.pkl")
    parser.add_argument("--out", required=True, help="Path to output sqlite file")
    parser.add_argument("--batch-size", type=int, default=10000)
    args = parser.parse_args()
    build_sqlite(args.pkl, args.out, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
