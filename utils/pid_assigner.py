import pickle
import re
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import process, fuzz


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

class PIDAssigner:
    def __init__(self, matcher_pkl: str, *, max_candidates: int = 20000):
        with open(matcher_pkl, "rb") as f:
            obj = pickle.load(f)
        self.titles_flat: List[str] = obj["titles_flat"]
        self.pids_flat: List[str] = obj["pids_flat"]
        self.token2idx: Dict[str, List[int]] = obj["token2idx"]
        self.max_candidates = max_candidates

    def _candidate_indices(self, q: str) -> List[int]:
        toks = tokenize(q)
        if not toks:
            return []

        seen = set()
        out = []
        for tok in toks:
            for i in self.token2idx.get(tok, []):
                if i in seen:
                    continue
                seen.add(i)
                out.append(i)
                if len(out) >= self.max_candidates:
                    return out
        return out

    def assign(self, raw_title: str, *, min_score: float = 80.0) -> PIDMatch:
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
    def __init__(self, db_path: str, *, max_candidates: int = 20000):
        self.db_path = db_path
        self.max_candidates = max_candidates
        self._conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self._lock = threading.Lock()

    def _candidate_indices(self, q: str) -> List[int]:
        toks = tokenize(q)
        if not toks:
            return []

        seen = set()
        out = []
        with self._lock:
            cur = self._conn.cursor()
            for tok in toks:
                cur.execute(
                    "SELECT idx FROM token_index WHERE token=? LIMIT ?",
                    (tok, self.max_candidates),
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

    def assign(self, raw_title: str, *, min_score: float = 80.0) -> PIDMatch:
        q = normalize_title(raw_title)
        if not q:
            return PIDMatch(None, 0.0, "unmatched")

        idxs = self._candidate_indices(q)
        if not idxs:
            return PIDMatch(None, 0.0, "unmatched")

        titles, pids = self._fetch_candidates(idxs)
        if not titles:
            return PIDMatch(None, 0.0, "unmatched")

        m = process.extractOne(q, titles, scorer=fuzz.token_set_ratio)
        if m is None:
            return PIDMatch(None, 0.0, "unmatched")

        best_title, score, pos = m
        if score < min_score:
            return PIDMatch(None, float(score), "unmatched")

        pid = pids[pos]
        return PIDMatch(pid, float(score), "rapidfuzz-sqlite")
