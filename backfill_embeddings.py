# backfill_embeddings.py
import os
import json
import pymysql
import numpy as np
from sentence_transformers import SentenceTransformer

DB_HOST = os.getenv("MYSQL_HOST")
DB_PORT = int(os.getenv("MYSQL_PORT"))
DB_USER = os.getenv("MYSQL_USER")
DB_PASS = os.getenv("MYSQL_PASSWORD")
DB_NAME = os.getenv("MYSQL_DATABASE")

BATCH = int("128")

def build_item_text(row: dict) -> str:
    name = row.get("name") or ""
    desc = row.get("description") or ""
    cat0 = row.get("cat0") or ""
    cat1 = row.get("cat1") or ""
    cat2 = row.get("cat2") or ""
    # E5は passage/query のprefixを付けるのが定石
    return f"passage: {name}\n{desc}\nカテゴリ: {cat0}/{cat1}/{cat2}".strip()

def vec_to_json(vec: np.ndarray) -> str:
    # string_to_vector が読める形にする: "[0.1, -0.02, ...]"
    # 桁を丸めてサイズ削減（精度に影響しにくい範囲）
    return "[" + ",".join(f"{x:.6f}" for x in vec.tolist()) + "]"

def main():
    assert all([DB_HOST, DB_USER, DB_PASS, DB_NAME]), "DB env vars are missing"

    model = SentenceTransformer("intfloat/multilingual-e5-base")

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

    try:
        with conn.cursor() as cur:
            # embedding が NULL の行を順次処理
            cur.execute(
                """
                SELECT item_id, name, description, cat0, cat1, cat2
                FROM items
                WHERE embedding IS NULL
                LIMIT %s
                """,
                (BATCH,),
            )
            rows = cur.fetchall()

            if not rows:
                print("No rows to backfill. (embedding is already filled)")
                return

            texts = [build_item_text(r) for r in rows]

            # まとめて埋め込み生成（正規化しておくとCOSINEが安定）
            embs = model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                batch_size=32,
                show_progress_bar=True,
            )

            # DBへ保存
            for r, e in zip(rows, embs):
                emb_json = vec_to_json(e)
                cur.execute(
                    """
                    UPDATE items
                    SET embedding = string_to_vector(%s)
                    WHERE item_id = %s
                    """,
                    (emb_json, r["item_id"]),
                )

            conn.commit()
            print(f"Backfilled {len(rows)} rows.")
            print("Run again until it prints 'No rows to backfill'.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
