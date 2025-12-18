import json, os, math
import urllib.request
from typing import List

_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"

def _l2_normalize(vec: List[float]) -> List[float]:
    s = math.sqrt(sum(x * x for x in vec))
    if s == 0:
        return vec
    return [x / s for x in vec]

def gemini_embed(text: str, *, task_type: str, dims: int = 768) -> List[float]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    payload = {
        "content": {"parts": [{"text": text}]},
        "task_type": task_type,
        "output_dimensionality": dims,
    }

    req = urllib.request.Request(
        _EMBED_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    vec = data["embedding"]["values"]
    if len(vec) != dims:
        raise ValueError(f"Embedding dims mismatch: got {len(vec)} expected {dims}")

    return _l2_normalize([float(x) for x in vec])

def vec_to_string_to_vector_arg(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.9f}" for x in vec) + "]"
