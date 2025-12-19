from __future__ import annotations

import pickle
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from gensim.models import KeyedVectors


def rrf_add(scores: Dict[str, float], ranked: List[str], base: float, rrf_k: int):
    for r, pid in enumerate(ranked, 1):
        scores[pid] += base * (1.0 / (rrf_k + r))


def generate_candidates_rrf(
    history: List[str],
    wv: KeyedVectors,
    lift_dict: Dict[str, List[Tuple[str, float, int]]],
    popular_pids: Optional[List[str]],
    *,
    seed_k: int,
    per_seed_item2vec: int,
    per_seed_lift: int,
    out_k: int,
    rrf_k: int,
    decay: float,
    alpha: float,
    beta: float,
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

        triples = lift_dict.get(seed)
        if triples:
            ranked = [pid for pid, _, _ in triples[:per_seed_lift]]
            rrf_add(scores, ranked, beta * w, rrf_k)

    for pid in list(scores.keys()):
        if pid in seen_in_history:
            del scores[pid]

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    cands = [pid for pid, _ in ranked if pid in wv][:out_k]

    if popular_pids is not None and len(cands) < out_k:
        seen = set(hist) | set(cands)
        for pid in popular_pids:
            if pid in seen:
                continue
            if pid not in wv:
                continue
            cands.append(pid)
            if len(cands) >= out_k:
                break

    return cands


class GRUNext(nn.Module):
    def __init__(self, vocab_size: int, emb_dim: int, hidden_dim: int):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.gru = nn.GRU(input_size=emb_dim, hidden_size=hidden_dim, batch_first=True)
        self.proj = nn.Linear(hidden_dim, emb_dim, bias=False)

    def forward(self, x, lengths):
        e = self.emb(x)
        packed = nn.utils.rnn.pack_padded_sequence(e, lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, h = self.gru(packed)
        h = h.squeeze(0)
        z = self.proj(h)
        z = nn.functional.normalize(z, dim=-1)
        return z


def encode_prefix(prefix: List[str], token2id: Dict[str, int], max_len: int, device: str):
    toks = [t for t in prefix if t in token2id]
    if len(toks) > max_len:
        toks = toks[-max_len:]
    ids = [token2id[t] for t in toks]
    x = torch.tensor(ids, dtype=torch.long, device=device).unsqueeze(0)
    lengths = torch.tensor([len(ids)], dtype=torch.long, device=device)
    return x, lengths


@torch.no_grad()
def rerank_candidates(
    prefix: List[str],
    candidates: List[str],
    model: GRUNext,
    token2id: Dict[str, int],
    max_len: int,
    device: str,
) -> List[Tuple[str, float]]:
    x, lengths = encode_prefix(prefix, token2id, max_len, device=device)
    z = model(x, lengths).squeeze(0)

    cand_tokens: List[str] = []
    cand_ids: List[int] = []
    for c in candidates:
        tid = token2id.get(c, 0)
        if tid != 0:
            cand_tokens.append(c)
            cand_ids.append(tid)

    if not cand_ids:
        return []

    cand_ids_t = torch.tensor(cand_ids, dtype=torch.long, device=device)
    v = model.emb.weight[cand_ids_t]
    v = nn.functional.normalize(v, dim=-1)

    scores = (v * z.view(1, -1)).sum(dim=-1)
    order = torch.argsort(scores, descending=True)

    ranked = [(cand_tokens[i], float(scores[i].item())) for i in order.tolist()]
    return ranked


class Recommender:
    def __init__(
        self,
        *,
        wv_kv_path: str,
        lift_dict_path: str,
        popular_pkl_path: str,
        gru_ckpt_path: str,
        device: str = "cpu",
        seed_k: int = 20,
        per_seed_item2vec: int = 1200,
        per_seed_lift: int = 800,
        out_k: int = 2000,
        rrf_k: int = 10,
        decay: float = 0.8,
        alpha: float = 1.0,
        beta: float = 1.0,
    ):
        self.device = device
        self.wv = KeyedVectors.load(wv_kv_path, mmap="r")

        with open(lift_dict_path, "rb") as f:
            self.lift_dict = pickle.load(f)
        with open(popular_pkl_path, "rb") as f:
            self.popular_pids = pickle.load(f)["popular_pids"]

        ckpt = torch.load(gru_ckpt_path, map_location="cpu")
        self.token2id = ckpt["token2id"]
        self.max_len = ckpt["max_len"]
        emb_dim = ckpt["emb_dim"]
        hidden = ckpt["hidden"]

        self.model = GRUNext(vocab_size=len(self.token2id) + 1, emb_dim=emb_dim, hidden_dim=hidden)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.seed_k = seed_k
        self.per_seed_item2vec = per_seed_item2vec
        self.per_seed_lift = per_seed_lift
        self.out_k = out_k
        self.rrf_k = rrf_k
        self.decay = decay
        self.alpha = alpha
        self.beta = beta

    def recommend(self, history: List[str], topn: int = 50) -> List[Tuple[str, float]]:
        cands = generate_candidates_rrf(
            history, self.wv, self.lift_dict, self.popular_pids,
            seed_k=self.seed_k,
            per_seed_item2vec=self.per_seed_item2vec,
            per_seed_lift=self.per_seed_lift,
            out_k=self.out_k,
            rrf_k=self.rrf_k,
            decay=self.decay,
            alpha=self.alpha,
            beta=self.beta,
        )
        if not cands:
            return []

        ranked = rerank_candidates(
            history, cands, self.model, self.token2id, max_len=self.max_len, device=self.device
        )
        return ranked[:topn]
