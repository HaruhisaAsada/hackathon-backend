from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from gensim.models import KeyedVectors


def rrf_add(scores: Dict[str, float], ranked: List[str], base: float, rrf_k: int):
    for r, pid in enumerate(ranked, 1):
        scores[pid] += base * (1.0 / (rrf_k + r))


def generate_candidates_item2vec(
    history: List[str],
    wv: KeyedVectors,
    *,
    seed_k: int,
    per_seed_item2vec: int,
    out_k: int,
    rrf_k: int,
    decay: float,
    alpha: float,
) -> List[str]:
    hist = [str(x) for x in history if x]
    if not hist:
        return []

    seeds = hist[-seed_k:][::-1]
    seen_in_history = set(hist)
    scores = defaultdict(float)

    for t, seed in enumerate(seeds):
        w = decay ** t
        if seed in wv:
            ranked = [pid for pid, _ in wv.most_similar(seed, topn=per_seed_item2vec)]
            rrf_add(scores, ranked, alpha * w, rrf_k)

    for pid in list(scores.keys()):
        if pid in seen_in_history:
            del scores[pid]

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [pid for pid, _ in ranked if pid in wv][:out_k]


class Recommender:
    def __init__(
        self,
        *,
        wv_kv_path: str,
        seed_k: int = 20,
        per_seed_item2vec: int = 1200,
        out_k: int = 2000,
        rrf_k: int = 10,
        decay: float = 0.8,
        alpha: float = 1.0,
    ):
        self.wv = KeyedVectors.load(wv_kv_path, mmap="r")
        self.seed_k = seed_k
        self.per_seed_item2vec = per_seed_item2vec
        self.out_k = out_k
        self.rrf_k = rrf_k
        self.decay = decay
        self.alpha = alpha

    def recommend(self, history: List[str], topn: int = 50) -> List[Tuple[str, float]]:
        cands = generate_candidates_item2vec(
            history,
            self.wv,
            seed_k=self.seed_k,
            per_seed_item2vec=self.per_seed_item2vec,
            out_k=self.out_k,
            rrf_k=self.rrf_k,
            decay=self.decay,
            alpha=self.alpha,
        )
        return [(pid, 0.0) for pid in cands[:topn]]
