import os
from functools import lru_cache

from dotenv import load_dotenv

from triagem_rag.dados import RAIZ

load_dotenv(RAIZ / ".env")

PG_DSN_PADRAO = "postgresql+psycopg://triagem:triagem@localhost:5433/triagem"
COLECAO = "treino_v1"
MODELO_EMB = "BAAI/bge-small-en-v1.5"
# revisão (commit do HF Hub) fixada após o primeiro download; ver docs/decisoes.md
REVISAO_EMB = os.environ.get("EMB_REVISAO", "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a")
DIM_EMB = 384
K_RRF = 60
N_CANDIDATOS = 50


def pg_dsn() -> str:
    return os.environ.get("PG_DSN", PG_DSN_PADRAO)


def pg_dsn_psycopg() -> str:
    # PG_DSN está no formato SQLAlchemy (usado pelo langchain-postgres); psycopg puro não aceita o "+psycopg"
    return pg_dsn().replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache(maxsize=1)
def embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    # sem prefixo de instrução do BGE: ticket contra ticket é tarefa simétrica (F0 §5)
    return HuggingFaceEmbeddings(model_name=MODELO_EMB, model_kwargs={"device": "cpu", "revision": REVISAO_EMB},
                                 encode_kwargs={"normalize_embeddings": True})


@lru_cache(maxsize=1)
def vector_store():
    from langchain_postgres import PGVector
    from langchain_postgres.vectorstores import DistanceStrategy
    return PGVector(embeddings=embeddings(), collection_name=COLECAO, connection=pg_dsn(), use_jsonb=True,
                    embedding_length=DIM_EMB, distance_strategy=DistanceStrategy.COSINE)


def buscar_vetorial(texto: str, n: int = N_CANDIDATOS) -> list[tuple[int, str, int]]:
    # busca exata: a coleção não tem índice HNSW/IVF (F0 §5)
    docs = vector_store().as_retriever(search_kwargs={"k": n}).invoke(texto)
    return [(int(d.metadata["id"]), d.metadata["categoria"], r) for r, d in enumerate(docs, 1)]


def montar_tsquery(con, texto: str) -> str:
    # OR dos lexemas: plainto_tsquery usa AND e zera consultas longas (F0 §5).
    # quote_literal escapa aspas e ':'; o cast ::tsquery não reaplica o stemmer aos lexemas já normalizados
    return con.execute("SELECT coalesce(string_agg(quote_literal(lexeme), ' | '), '') "
                       "FROM unnest(to_tsvector('english', %s))", (texto,)).fetchone()[0]


def buscar_fulltext(texto: str, n: int = N_CANDIDATOS, con=None) -> list[tuple[int, str, int]]:
    import psycopg
    fechar = con is None
    con = con or psycopg.connect(pg_dsn_psycopg())
    try:
        q = montar_tsquery(con, texto)
        if not q:
            return []
        # normalização 2 (divide pelo comprimento): emenda F1, congelada; ver docs/decisoes.md
        rows = con.execute("SELECT id, categoria FROM tickets_fts, CAST(%s AS tsquery) q WHERE tsv @@ q "
                           "ORDER BY ts_rank_cd(tsv, q, 2) DESC, id LIMIT %s", (q, n)).fetchall()
        return [(int(i), c, r) for r, (i, c) in enumerate(rows, 1)]
    finally:
        if fechar:
            con.close()


def rrf(listas, k_rrf: int = K_RRF, top: int = 5) -> list[tuple[int, float]]:
    """listas: sequências de ids em ordem de rank (rank 1 = primeiro). Devolve [(id, score)]."""
    score, melhor = {}, {}
    for lista in listas:
        for rank, i in enumerate(lista, 1):
            score[i] = score.get(i, 0.0) + 1.0 / (k_rrf + rank)
            melhor[i] = min(melhor.get(i, rank), rank)
    ordem = sorted(score, key=lambda i: (-score[i], melhor[i], i))
    return [(i, score[i]) for i in ordem[:top]]


def buscar_hibrida(texto: str, k: int = 5, con=None) -> list[tuple[int, str, int]]:
    vet, fts = buscar_vetorial(texto, N_CANDIDATOS), buscar_fulltext(texto, N_CANDIDATOS, con=con)
    cat = {i: c for i, c, _ in vet + fts}
    return [(i, cat[i], r) for r, (i, _) in enumerate(rrf([[i for i, _, _ in vet], [i for i, _, _ in fts]], top=k), 1)]
