import argparse
import os
import pickle
import sqlite3
from typing import Dict, List, Tuple


def _chunked(iterable, size):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _filter_by_allowed_pids(
    titles: List[str],
    pids: List[str],
    token2idx: Dict[str, List[int]],
    allowed_pids: set[str],
) -> Tuple[List[str], List[str], Dict[str, List[int]]]:
    keep_old_idxs = [i for i, pid in enumerate(pids) if pid in allowed_pids]
    if not keep_old_idxs:
        raise ValueError("No pids left after filtering by allowed_pids")

    old_to_new = {old_i: new_i for new_i, old_i in enumerate(keep_old_idxs)}
    new_titles = [titles[i] for i in keep_old_idxs]
    new_pids = [pids[i] for i in keep_old_idxs]

    new_token2idx: Dict[str, List[int]] = {}
    for tok, idxs in token2idx.items():
        remapped = [old_to_new[i] for i in idxs if i in old_to_new]
        if remapped:
            new_token2idx[tok] = remapped

    return new_titles, new_pids, new_token2idx


def build_sqlite(
    pkl_path: str,
    sqlite_path: str,
    *,
    batch_size: int = 10000,
    max_token_df: int | None = None,
    allow_pids_kv: str | None = None,
) -> None:
    with open(pkl_path, "rb") as f:
        obj = pickle.load(f)

    titles = obj["titles_flat"]
    pids = obj["pids_flat"]
    token2idx = obj["token2idx"]

    if allow_pids_kv:
        from gensim.models import KeyedVectors
        wv = KeyedVectors.load(allow_pids_kv, mmap="r")
        allowed_pids = set(wv.index_to_key)
        titles, pids, token2idx = _filter_by_allowed_pids(
            titles,
            pids,
            token2idx,
            allowed_pids,
        )

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
    parser.add_argument(
        "--allow-pids-kv",
        default=None,
        help="Path to item2vec KeyedVectors (.kv) to filter pids to its vocabulary.",
    )
    args = parser.parse_args()
    max_token_df = args.max_token_df if args.max_token_df > 0 else None
    build_sqlite(
        args.pkl,
        args.out,
        batch_size=args.batch_size,
        max_token_df=max_token_df,
        allow_pids_kv=args.allow_pids_kv,
    )


if __name__ == "__main__":
    main()
