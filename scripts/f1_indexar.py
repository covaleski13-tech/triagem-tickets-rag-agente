"""F1 passo 7: índices vetorial (langchain-postgres, coleção treino_v1) e full-text (tickets_fts), só treino.
Idempotente: recria a coleção e a tabela a cada execução."""
import json
import sys
import time
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import ds2_com_splits  # noqa: E402
from triagem_rag.recuperacao import (COLECAO, DIM_EMB, embeddings, pg_dsn, pg_dsn_psycopg)  # noqa: E402


def main():
    df = ds2_com_splits()
    tr = df[df["split_grupo"] == "treino"]  # anti-vazamento: o índice só recebe treino
    assert len(tr) == 38270 and (tr["split_grupo"] == "treino").all()
    textos, ids, cats = tr["Document"].astype(str).tolist(), tr["id"].astype(int).tolist(), tr["Topic_group"].tolist()

    with psycopg.connect(pg_dsn_psycopg(), autocommit=True) as con:
        con.execute("CREATE EXTENSION IF NOT EXISTS vector")
        con.execute("DROP TABLE IF EXISTS tickets_fts")
        con.execute("CREATE TABLE tickets_fts (id int PRIMARY KEY, categoria text, texto text, "
                    "tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', texto)) STORED)")
        with con.cursor().copy("COPY tickets_fts (id, categoria, texto) FROM STDIN") as cp:
            for linha in zip(ids, cats, textos):
                cp.write_row(linha)
        con.execute("CREATE INDEX tickets_fts_tsv_gin ON tickets_fts USING GIN (tsv)")
        n_fts = con.execute("SELECT count(*) FROM tickets_fts").fetchone()[0]
    assert n_fts == len(tr), n_fts
    if "--so-fulltext" in sys.argv:  # reindexa só o full-text, sem os ~15 min de embeddings
        print(json.dumps({"n_treino": len(tr), "n_fulltext": n_fts}))
        return

    emb = embeddings()
    t0 = time.perf_counter()
    vetores = emb.embed_documents(textos)
    t_emb = time.perf_counter() - t0
    assert len(vetores[0]) == DIM_EMB

    from langchain_postgres import PGVector
    from langchain_postgres.vectorstores import DistanceStrategy
    vs = PGVector(embeddings=emb, collection_name=COLECAO, connection=pg_dsn(), use_jsonb=True,
                  embedding_length=DIM_EMB, distance_strategy=DistanceStrategy.COSINE, pre_delete_collection=True)
    t1 = time.perf_counter()
    lote = 2000
    for i in range(0, len(ids), lote):
        vs.add_embeddings(texts=textos[i:i + lote], embeddings=vetores[i:i + lote],
                          metadatas=[{"id": j, "categoria": c} for j, c in zip(ids[i:i + lote], cats[i:i + lote])],
                          ids=[str(j) for j in ids[i:i + lote]])
    t_ins = time.perf_counter() - t1

    with psycopg.connect(pg_dsn_psycopg()) as con:
        n_vet = con.execute("SELECT count(*) FROM langchain_pg_embedding e JOIN langchain_pg_collection c "
                            "ON e.collection_id = c.uuid WHERE c.name = %s", (COLECAO,)).fetchone()[0]
    assert n_vet == n_fts == len(tr), (n_vet, n_fts)

    out = {"n_treino": len(tr), "n_vetorial": n_vet, "n_fulltext": n_fts, "embed_treino_s": round(t_emb, 1),
           "insercao_vetorial_s": round(t_ins, 1)}
    (RAIZ / "results/f1").mkdir(parents=True, exist_ok=True)
    (RAIZ / "results/f1/indexacao.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
