# Decisões técnicas

## F1 (2026-11-17)

### Postgres + pgvector (passo 5)

- Imagem: `pgvector/pgvector:pg17`, fixada no `docker-compose.yml` pelo digest
  `sha256:b513c48566e4777cd3370451400000c78eda6a08131d68f4c31d4a76f27bd8fd`
  (`docker image inspect`, `Created` 2026-11-12T23:10:26Z).
- Servidor: PostgreSQL 17.12 (Debian 17.12-1.pgdg12+1); extensão `vector` 0.8.7.
- Porta `5433:5432`, volume nomeado `pgdata`, healthcheck `pg_isready`.
- Docker Desktop 4.99.0, Engine 29.9.3, Compose v5.7.0. Plano B (Supabase) **não** foi usado.

### Embeddings (passo 6)

- Modelo: `BAAI/bge-small-en-v1.5`, revisão (commit do HF Hub) `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`,
  lida com `huggingface_hub.model_info` e fixada em `src/triagem_rag/recuperacao.py` (`REVISAO_EMB`).
- Dimensão: 384 (assert no `scripts/f1_indexar.py`); `normalize_embeddings=True` (norma 1,0 conferida).
- Sem o prefixo de instrução de consulta do BGE: documento e consulta embutidos do mesmo jeito.
- `sentence-transformers` 6.3.0, `langchain-huggingface` 1.2.3, `torch` 2.15.0+cpu, CPU.
- Tempo para embutir o treino (38.270 textos): ver `results/f1/indexacao.json` (`embed_treino_s`).

### Índices (passo 7)

- Vetorial: `PGVector` (`langchain-postgres` 0.0.19), coleção `treino_v1`, distância cosseno,
  metadados `id` e `categoria`, sem índice HNSW/IVF (busca exata). O id do documento é o `id` do ticket.
- Full-text: tabela própria `tickets_fts` com `tsv` gerado por `to_tsvector('english', texto)` e índice GIN.
- Ingestão idempotente: a tabela é recriada (`DROP`/`CREATE`) e a coleção usa `pre_delete_collection=True`.

### Recuperadores (passo 8)

- Consulta full-text, montada no SQL:
  `SELECT coalesce(string_agg(quote_literal(lexeme), ' | '), '') FROM unnest(to_tsvector('english', texto))`,
  convertida com `CAST(... AS tsquery)`. `quote_literal` escapa aspas e `:`; o cast não reaplica o stemmer aos
  lexemas já normalizados (`to_tsquery('english', ...)` reaplicaria). A config continua `english`.
- Ordenação full-text: `ts_rank_cd(tsv, q, 2)` decrescente, desempate por `id` crescente (ver a emenda abaixo).

### Emenda F1 — normalização 2 no `ts_rank_cd` (decisão do Gustavo, 2026-11-17)

- **Mudança:** `ts_rank_cd(tsv, q)` (normalização 0, implícita na F0 §5) passa a `ts_rank_cd(tsv, q, 2)`,
  que divide o rank pelo comprimento do documento.
- **Motivo:** com a normalização 0, o `test_autorrecuperacao` falhou. Consultando com o próprio texto, os
  5 ids de treino (seed 42) ficaram nos ranks 204 a 1.277 do full-text. A consulta em OR casa de 28.301 a
  35.720 dos 38.270 documentos, e o topo era sempre ocupado por tickets longos (556 a 931 palavras).
- **Evidência:** só os 5 ids de treino do teste. Nenhuma métrica de rótulo foi calculada; nenhum ticket do
  holdout nem dos 400 foi consultado para escolher a normalização.
- No mesmo diagnóstico também foram vistas as normalizações 1 e 32 (ranks 13 a 231 e 204 a 1.277). Com a 2, o
  próprio id ficou em rank 1 ou 2. Detalhe no `docs/planning/F1-report.md` §3.
- **Congelada:** nenhuma outra normalização será testada.
- RRF própria (`rrf()`), `k_rrf=60`, 50 candidatos de cada recuperador, top 5; desempate pelo menor rank em
  qualquer lista e depois pelo menor id.
- **Híbrida nativa do `langchain-postgres`:** existe na versão 0.0.19, só na API v2 (`PGVectorStore`), em
  `langchain_postgres/v2/hybrid_search_config.py` (`HybridSearchConfig`, `reciprocal_rank_fusion`,
  `weighted_sum_ranking`). A API v1 usada aqui (`PGVector`) não tem. **Não usada** (G8).
