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

## F2 (2026-11-17)

### Exceção ao `CLAUDE.md` §3 ("no máximo 1 nova tentativa")

- A regra vale para o agente (F4).
- Nas variantes de experimento de Q1 (V0 a V3), a política de repetição é a do `f3_llm.py` do case: até 3
  tentativas para erro de API (`RateLimitError`, `APIConnectionError`, `InternalServerError`, espera de 2^n s)
  e mais 1 repetição se a saída for inválida; se continuar inválida, `falha`. Motivo: V0 é reprodução do case e
  V1 a V3 precisam ser comparáveis a ele (F2-spec).

### Cliente LLM

- `ChatAnthropic` (`langchain-anthropic` 1.7.10, SDK `anthropic` 2.10.0) com `model="claude-haiku-5-5"`,
  `max_tokens=64`, `max_retries=0`, `thinking={"type": "disabled"}`, `output_config={"effort": "low"}`, ambos
  como campos nativos da classe. Sem `temperature`, `top_p` e `top_k`: as saídas não são determinísticas.
- O payload montado (`_get_request_payload`) é igual ao do case; conferido em `tests/test_f2.py::test_payload_llm`.
- Saída como texto livre, validada depois por `esquema.validar` (Pydantic), com paridade testada contra o
  `validar` do case.

### Template RAG congelado

- `prompts/classificar_rag_v1.txt` = `classificar_v1.txt` com uma única linha trocada:
  `Labeled examples (one per category):` → `Labeled examples from the training set:`.
- O mesmo template serve para V1 (F2) e para V2 e V3 (F3). Fica congelado.
- Ordem dos exemplos: em V1, a ordem do sorteio (`np.random.default_rng([42, id])`, 5 sem reposição sobre os ids
  de treino em ordem crescente); em V2 e V3, a ordem de rank, com o rank 1 primeiro.

## Decisões posteriores aos resultados da F3 (Gustavo, 2026-11-17)

Tomadas **depois** de ver os resultados da F3; não alteram a família pré-registrada de Q1 nem os veredictos.

- **D-F3-1 — `recuperar_exemplos` do agente usa a busca vetorial, não a híbrida.** Evidência (recorte dos 400):
  precisão@5 da híbrida − vetorial = −0,0365 (IC 95% −0,0645 a −0,009); V2 47,75% × V3 45,25% (p Holm 0,229).
- **D-F3-2 — o agente existe para responder a Q3** (segurança da execução da política sob tool calling), não
  acurácia. O README dirá que, em acurácia, o voto dos vizinhos (K1) supera o LLM com os mesmos vizinhos.
  Evidência: V3 × K1 = −9,5 pp, p Holm 9,5e-04.

## F4 (2026-11-17)

- `langgraph` 1.2.22 instalado e fixado.
- Política do case reutilizada via `triar()` por um adaptador (`src/triagem_rag/politica_caso.py`), sem alterar
  `src/triagem_rag/caso/*.py`: `triagem.OUT_DIR` → `data/caso`; `TRIAGEM_CACHE_DIR=data/modelos`;
  `TRIAGEM_MODELO_VERSAO` = versão do joblib da F1 (calculada pela fórmula do case, `versao_atual`, sobre
  `data/f1_splits.csv`); `TRIAGEM_RUNTIME_DIR=runtime_agente/` (fora do git).
- O joblib da F1 já está no formato do case (`{"pipeline", "versao", "treino_s"}`): nenhuma conversão foi necessária.
- **Versão do modelo:** `TRIAGEM_MODELO_VERSAO=f71cfd480a50`, lida do nome do joblib da F1. A fórmula do case
  (`sha256(sha256(f1_splits.csv) + PARAMS)[:12]`) aplicada ao `data/f1_splits.csv` atual dá `d2522e1b9442`. Na F1,
  o hash foi calculado sobre a cópia do checkout do case no Windows (CRLF), antes da correção para LF; o conteúdo
  dos splits é o mesmo, só os fins de linha diferem. O modelo carregado pelo adaptador continua com 278/400.
- Prompt do agente: `prompts/agente_sugerir_v1.txt`, congelado, SHA-256
  `a9201dd9aa2b49271b50de31a11a74dfc469321f38b4a964e8d9a20aed98858e`.

## Emenda F4 — resposta final pela tool `responder` (Gustavo, 2026-11-17)

- Motivo: na fumaça e no diagnóstico (5 tickets do treino), o LLM com tools escreveu texto antes do JSON em 3 de 7
  respostas finais; a validação estrita rejeita. Leitura tolerante do JSON rejeitada (ataque `json_pronto`, paridade
  com a F2). Evidência só do treino; congelada antes da F5.
- Nova tool `responder(categoria, confianca)` com o schema de `esquema.Classificacao`, validada no código (exatamente as
  2 chaves, tipos estritos). `tool_choice`: `any` nas rodadas 1 e 2; `{"type": "tool", "name": "responder"}` na 3ª.
  Aceito pela API com `thinking` desligado (conferido com `count_tokens` e na fumaça).
- Texto livre do modelo descartado (não validado, não logado, fora do estado). `responder` junto com outra tool na
  mesma resposta: vale `responder`; as outras são ignoradas e registradas como `ignorada`.
- Prompt `prompts/agente_sugerir_v2.txt` (v1 fica como histórico), SHA-256
  `ffc25ce7d56cd341281c263da7044d597ada86752fb73eb6efbeb4752d079bd8`.
- `results/f4/diagnostico_json.jsonl` fora do git (frases do LLM com fragmentos curtos de tickets do treino);
  versionado só o resumo sem texto `results/f4/diagnostico_resumo.json`.
