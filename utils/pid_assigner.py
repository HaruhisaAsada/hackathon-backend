import pickle
import re
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import process, fuzz
from sqlalchemy import bindparam, text


_token_re = re.compile(r"[0-9a-zA-Zぁ-んァ-ヶ一-龥ー]+")


def normalize_title(s: str) -> str:
    s = unicodedata.normalize("NFKC", (s or "").strip()).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokenize(s: str) -> List[str]:
    return [t for t in _token_re.findall(s) if len(t) >= 1]


@dataclass
class PIDMatch:
    pid: Optional[str]
    score: float
    source: str


class LazyPIDAssigner:
    def __init__(self, factory):
        self._factory = factory
        self._assigner = None
        self._lock = threading.Lock()

    def _get_assigner(self):
        if self._assigner is None:
            with self._lock:
                if self._assigner is None:
                    self._assigner = self._factory()
        return self._assigner

    def assign(self, *args, **kwargs):
        return self._get_assigner().assign(*args, **kwargs)

class PIDAssigner:
    def __init__(
        self,
        matcher_pkl: str,
        *,
        max_candidates: int = 20000,
        max_tokens: int = 0,
        token_limit: int = 0,
    ):
        with open(matcher_pkl, "rb") as f:
            obj = pickle.load(f)
        self.titles_flat: List[str] = obj["titles_flat"]
        self.pids_flat: List[str] = obj["pids_flat"]
        self.token2idx: Dict[str, List[int]] = obj["token2idx"]
        self.max_candidates = max_candidates
        self.max_tokens = max_tokens
        self.token_limit = token_limit

    def _limit_tokens(self, toks: List[str]) -> List[str]:
        if self.max_tokens and len(toks) > self.max_tokens:
            return toks[: self.max_tokens]
        return toks

    def _candidate_indices(self, q: str) -> List[int]:
        toks = self._limit_tokens(tokenize(q))
        if not toks:
            return []

        seen = set()
        out = []
        for tok in toks:
            idxs = self.token2idx.get(tok, [])
            if self.token_limit and len(idxs) > self.token_limit:
                idxs = idxs[: self.token_limit]
            for i in idxs:
                if i in seen:
                    continue
                seen.add(i)
                out.append(i)
                if len(out) >= self.max_candidates:
                    return out
        return out

    def assign(self, raw_title: str, *, min_score: float = 0.0) -> PIDMatch:
        q = normalize_title(raw_title)
        if not q:
            return PIDMatch(None, 0.0, "unmatched")

        idxs = self._candidate_indices(q)
        if not idxs:
            return PIDMatch(None, 0.0, "unmatched")

        candidates = [self.titles_flat[i] for i in idxs]

        m = process.extractOne(q, candidates, scorer=fuzz.token_set_ratio)
        if m is None:
            return PIDMatch(None, 0.0, "unmatched")

        best_title, score, pos = m
        if score < min_score:
            return PIDMatch(None, float(score), "unmatched")

        flat_i = idxs[pos]
        pid = self.pids_flat[flat_i]
        return PIDMatch(pid, float(score), "rapidfuzz")


class SQLitePIDAssigner:
    def __init__(
        self,
        db_path: str,
        *,
        max_candidates: int = 20000,
        max_tokens: int = 0,
        token_limit: int = 0,
    ):
        self.db_path = db_path
        self.max_candidates = max_candidates
        self.max_tokens = max_tokens
        self.token_limit = token_limit
        self._conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self._lock = threading.Lock()

    def _limit_tokens(self, toks: List[str]) -> List[str]:
        if self.max_tokens and len(toks) > self.max_tokens:
            return toks[: self.max_tokens]
        return toks

    def _candidate_indices(self, q: str) -> List[int]:
        toks = self._limit_tokens(tokenize(q))
        if not toks:
            return []

        seen = set()
        out = []
        with self._lock:
            cur = self._conn.cursor()
            placeholders = ",".join("?" for _ in toks)
            cur.execute(
                f"SELECT token, token_id FROM tokens WHERE token IN ({placeholders})",
                toks,
            )
            token_id_by_token = {token: token_id for token, token_id in cur.fetchall()}
            for tok in toks:
                token_id = token_id_by_token.get(tok)
                if token_id is None:
                    continue
                cur.execute(
                    "SELECT idx FROM token_index WHERE token_id=? LIMIT ?",
                    (token_id, self.token_limit or self.max_candidates),
                )
                for (idx,) in cur.fetchall():
                    if idx in seen:
                        continue
                    seen.add(idx)
                    out.append(idx)
                    if len(out) >= self.max_candidates:
                        cur.close()
                        return out
            cur.close()
        return out

    def _fetch_candidates(self, idxs: List[int]) -> Tuple[List[str], List[str]]:
        if not idxs:
            return [], []

        placeholders = ",".join("?" for _ in idxs)
        sql = f"SELECT idx, title, pid FROM items WHERE idx IN ({placeholders})"
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, idxs)
            rows = cur.fetchall()
            cur.close()

        by_idx = {row[0]: (row[1], row[2]) for row in rows}
        titles = []
        pids = []
        for idx in idxs:
            row = by_idx.get(idx)
            if row:
                titles.append(row[0])
                pids.append(row[1])
        return titles, pids

    def assign(self, raw_title: str, *, min_score: float = 0.0) -> PIDMatch:
        q = normalize_title(raw_title)
        if not q:
            return PIDMatch(None, 0.0, "unmatched")

        idxs = self._candidate_indices(q)
        if not idxs:
            return PIDMatch(None, 0.0, "unmatched")

        best_pid = None
        best_score = 0.0
        chunk_size = 1000
        with self._lock:
            cur = self._conn.cursor()
            for i in range(0, len(idxs), chunk_size):
                chunk = idxs[i:i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                cur.execute(
                    f"SELECT idx, title, pid FROM items WHERE idx IN ({placeholders})",
                    chunk,
                )
                for _, title, pid in cur.fetchall():
                    score = fuzz.token_set_ratio(q, title)
                    if score > best_score:
                        best_score = score
                        best_pid = pid
            cur.close()

        if best_pid is None:
            return PIDMatch(None, 0.0, "unmatched")

        score = best_score
        if score < min_score:
            return PIDMatch(None, float(score), "unmatched")

        return PIDMatch(best_pid, float(score), "rapidfuzz-sqlite")


class MySQLPIDAssigner:
    def __init__(
        self,
        engine,
        *,
        max_candidates: int = 20000,
        max_tokens: int = 0,
        token_limit: int = 0,
    ):
        self.engine = engine
        self.max_candidates = max_candidates
        self.max_tokens = max_tokens
        self.token_limit = token_limit

    def _limit_tokens(self, toks: List[str]) -> List[str]:
        if self.max_tokens and len(toks) > self.max_tokens:
            return toks[: self.max_tokens]
        return toks

    def _candidate_indices(self, q: str) -> List[int]:
        toks = self._limit_tokens(tokenize(q))
        if not toks:
            return []

        seen = set()
        out = []
        with self.engine.connect() as conn:
            token_rows = conn.execute(
                text(
                    "SELECT token, token_id FROM pid_matcher_tokens "
                    "WHERE token IN :toks"
                ).bindparams(bindparam("toks", expanding=True)),
                {"toks": toks},
            ).fetchall()
            token_id_by_token = {token: token_id for token, token_id in token_rows}

            for tok in toks:
                token_id = token_id_by_token.get(tok)
                if token_id is None:
                    continue
                rows = conn.execute(
                    text(
                        "SELECT idx FROM pid_matcher_token_index "
                        "WHERE token_id = :token_id LIMIT :limit"
                    ),
                    {"token_id": token_id, "limit": self.token_limit or self.max_candidates},
                ).fetchall()
                for (idx,) in rows:
                    if idx in seen:
                        continue
                    seen.add(idx)
                    out.append(idx)
                    if len(out) >= self.max_candidates:
                        return out
        return out

    def _fetch_candidates(self, idxs: List[int]) -> Tuple[List[str], List[str]]:
        if not idxs:
            return [], []

        titles: List[str] = []
        pids: List[str] = []
        chunk_size = 1000
        with self.engine.connect() as conn:
            for i in range(0, len(idxs), chunk_size):
                chunk = idxs[i:i + chunk_size]
                rows = conn.execute(
                    text(
                        "SELECT idx, title, pid FROM pid_matcher_items "
                        "WHERE idx IN :idxs"
                    ).bindparams(bindparam("idxs", expanding=True)),
                    {"idxs": chunk},
                ).fetchall()
                by_idx = {row[0]: (row[1], row[2]) for row in rows}
                for idx in chunk:
                    row = by_idx.get(idx)
                    if row:
                        titles.append(row[0])
                        pids.append(row[1])
        return titles, pids

    def assign(self, raw_title: str, *, min_score: float = 0.0) -> PIDMatch:
        q = normalize_title(raw_title)
        if not q:
            return PIDMatch(None, 0.0, "unmatched")

        idxs = self._candidate_indices(q)
        if not idxs:
            return PIDMatch(None, 0.0, "unmatched")

        best_pid = None
        best_score = 0.0
        chunk_size = 1000
        with self.engine.connect() as conn:
            for i in range(0, len(idxs), chunk_size):
                chunk = idxs[i:i + chunk_size]
                rows = conn.execute(
                    text(
                        "SELECT title, pid FROM pid_matcher_items "
                        "WHERE idx IN :idxs"
                    ).bindparams(bindparam("idxs", expanding=True)),
                    {"idxs": chunk},
                ).fetchall()
                for title, pid in rows:
                    score = fuzz.token_set_ratio(q, title)
                    if score > best_score:
                        best_score = score
                        best_pid = pid

        if best_pid is None:
            return PIDMatch(None, 0.0, "unmatched")

        score = best_score
        if score < min_score:
            return PIDMatch(None, float(score), "unmatched")

        return PIDMatch(best_pid, float(score), "rapidfuzz-mysql")
