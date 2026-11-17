# F1 — Ambiente, dados, índices e anti-vazamento

**Pré-requisito:** portão F0 aprovado em 2026-11-17 (ver `F0-escopo.md` §10).
**Orçamento:** 105 min. Ao passar de 120% (126 min), pare e reporte.
**Sem chamadas de LLM nesta fase.** Custo de API esperado: US$ 0.

## Objetivo

Deixar o repositório pronto para os experimentos:

- dados íntegros e iguais aos do case;
- Postgres + pgvector rodando via Docker;
- índice vetorial e índice full-text contendo **só o treino**;
- RRF implementada e testada;
- testes de anti-vazamento passando.

## Origens (somente leitura)

```
CASE = C:\Users\gusta\challenge-g4-ai-master
SOL  = CASE\ai-master-challenge\submissions\gustavo-covaleski\solution
```

| Arquivo de origem | Destino no repo |
|---|---|
| `SOL\triagem.py` | `src/triagem_rag/caso/triagem.py` |
| `SOL\comum.py` | `src/triagem_rag/caso/comum.py` |
| `SOL\prompts\classificar_v1.txt` | `prompts/classificar_v1.txt` |
| `SOL\tests\golden\golden_v1.jsonl` | `tests/golden/golden_v1.jsonl` |
| `SOL\tests\golden\ataques_v1.json` | `tests/golden/ataques_v1.json` |
| `SOL\outputs\f1_splits.csv` | `data/f1_splits.csv` |
| `SOL\outputs\f3_probs_holdout_grupo.csv` | `data/caso/f3_probs_holdout_grupo.csv` |
| `SOL\outputs\f8_politica_por_categoria.csv` e `SOL\outputs\f8_faixas.json` | `data/caso/` |
| `CASE\planning\F3\f3_llm_log.jsonl` | **não copiar**. Só derivar os arquivos do passo 3 |
| `CASE\data\all_tickets_processed_improved_v3.csv` | `data/raw/` (fora do git) |

- Se algum arquivo não existir no caminho indicado, **pare e reporte**.
- Não procure substitutos.

## Passos

### 0. Checagem do ambiente (pare se algo falhar)

- Rode `python --version` (esperado 3.11 ou mais), `git --version`, `docker version` e `docker compose version`.
- Confira se há pelo menos 5 GB livres em disco.
- Registre as saídas no report.
- Se o Docker não responder:
  - **pare e reporte**;
  - não instale Postgres nativo;
  - não crie conta em serviço nenhum.
- **Plano B (G2), só depois de o Gustavo autorizar:**
  - o Gustavo cria o projeto no Supabase e põe a string de conexão em `PG_DSN` no `.env`;
  - a execução retoma pelo passo 1 e pula o passo 5;
  - no lugar do passo 5, rode `create extension if not exists vector` no banco do Supabase;
  - registre a troca e as consequências (F0 §10, G2) em `docs/decisoes.md`.
  - A `PG_DSN` contém senha: nunca a imprima.

### 1. Esqueleto do repositório

- Na pasta definida em G1, rode `git init`.
- Crie a estrutura do `CLAUDE.md` §6.
- Crie o `.gitignore` com: `.env`, `data/raw/`, `.venv/`, `__pycache__/`, `*.joblib`, `results/**/*.log`.
- Crie o `.env.example` com:
  - `ANTHROPIC_API_KEY=`
  - `PG_DSN=postgresql+psycopg://triagem:triagem@localhost:5433/triagem`
  - `DATA_DIR=data`
  - `LANGCHAIN_TRACING_V2=false`
- Crie o `LICENSE` conforme G6.
- Crie um `README.md` mínimo, com uma linha e o link do PR #228. O README completo fica para a F6.
- Use um ambiente virtual em `.venv`.

### 2. Cópia com atribuição

- Copie os arquivos da tabela de origens.
- No topo de cada `.py` copiado, adicione um comentário de origem com o PR #228 e o commit `3a880f2`.
- Não mude a lógica.
- Crie `docs/origem.md`: uma linha por arquivo, com caminho de origem, destino, SHA-256 da origem e SHA-256 do destino.
- O SHA-256 dos `.py` difere da origem só pelo comentário. Registre também o SHA-256 da origem sem o comentário, para provar que o código é o mesmo.

### 3. Amostra dos 400 tickets e predições do case

- Leia `f3_llm_log.jsonl`. O esperado são 401 linhas e 400 ids únicos.
- Gere `data/amostra_400_ids.csv` com a coluna `id`, na ordem da primeira aparição.
- Gere `data/caso/f3_v0_pred.csv` com `id`, `pred_caso` e `valida`:
  - `pred_caso` é a categoria extraída de `resposta_bruta`;
  - se a resposta for inválida, `pred_caso` fica vazio;
  - para id repetido, use a **última** linha e registre no report qual id estava repetido e por quê, se der para inferir.
- Nenhum texto de ticket entra nesses arquivos.
- **Asserts:**
  - 400 ids;
  - todos com `split_grupo == holdout`;
  - todos com `p_max < 0,74` em `f3_probs_holdout_grupo.csv`;
  - a acurácia de `pred_caso` contra o rótulo é 26,5% (106/400). Se não bater, pare.

### 4. Integridade dos dados

- Registre o SHA-256 do CSV bruto em `docs/origem.md`.
- **Asserts:**
  - o CSV tem 47.837 linhas;
  - `f1_splits.csv` tem 47.837 linhas, com as colunas `id`, `group_id`, `split_grupo` e `split_aleatorio`;
  - o join por `id` é 1:1;
  - treino tem 38.270 linhas e holdout tem 9.567, valores já conferidos no PR #228. Se divergirem, **pare**: o arquivo copiado não é o do case.
  - nenhum `group_id` aparece nos dois lados de `split_grupo`.
- **Reprodução do clássico:**
  - retreine com a receita do case (TF-IDF (1,2), `min_df=2`, `sublinear_tf`; `LogisticRegression(max_iter=2000, random_state=42)`) só no treino;
  - acurácia no holdout: **85,07%**, com tolerância de ±0,05 pp por diferença de versão do scikit-learn;
  - acurácia nos 400: **69,5%** (278/400);
  - salve o modelo em `data/modelos/` (fora do git, `*.joblib`) com o hash do treino no nome, como no case.
  - Se não reproduzir, **pare**.

### 5. Postgres + pgvector

- Crie o `docker-compose.yml`:
  - serviço `db` com `pgvector/pgvector:pg17`, ou a tag pg17 estável mais recente;
  - porta `5433:5432`;
  - volume nomeado e healthcheck com `pg_isready`.
- Registre a tag e o digest (`docker image inspect`) em `docs/decisoes.md`.
- Habilite `CREATE EXTENSION vector`.

### 6. Embeddings

- Use `BAAI/bge-small-en-v1.5` (G4) via `langchain-huggingface` (`HuggingFaceEmbeddings`) com `normalize_embeddings=True`.
- **Não** adicione o prefixo de instrução de consulta do BGE. Documento e consulta são embutidos do mesmo jeito, porque a tarefa é ticket contra ticket.
- Assert: dimensão 384.
- Rode em CPU. Instale o torch pela roda de CPU.
- Registre em `docs/decisoes.md`:
  - nome do modelo;
  - revisão (hash do commit do Hugging Face Hub);
  - dimensão;
  - versão do `sentence-transformers`.
- Meça e registre o tempo para embutir o treino.

### 7. Índices (só treino)

- **Vetorial:**
  - use `PGVector` do `langchain-postgres`, coleção `treino_v1`;
  - metadados: `id` e `categoria`;
  - documento: o texto do ticket;
  - **sem** índice HNSW ou IVF: busca exata por cosseno (F0 §5).
- **Full-text:**
  - tabela própria `tickets_fts(id int primary key, categoria text, texto text, tsv tsvector generated always as (to_tsvector('english', texto)) stored)`;
  - índice GIN em `tsv`;
  - não altere as tabelas criadas pelo LangChain.
- O script de ingestão deve ser **idempotente**: recriar não duplica linhas. Faça um assert de contagem igual à do treino nas duas estruturas.
- Antes de inserir, filtre explicitamente com `split_grupo == "treino"`. O filtro fica no código, não só no dado.

### 8. Recuperadores e RRF

Todos os recuperadores ficam em `src/triagem_rag/recuperacao.py`.

- **Vetorial:**
  - `buscar_vetorial(texto, n=50)`, usando o retriever do LangChain;
  - retorna `[(id, categoria, rank)]`.
- **Full-text:**
  - `buscar_fulltext(texto, n=50)`;
  - monte a consulta como **OR** dos lexemas: `to_tsvector('english', texto)` → lexemas → `to_tsquery` unido por ` | `;
  - ordene por `ts_rank_cd`;
  - texto sem lexema retorna lista vazia, sem erro.
- **RRF:**
  - `rrf(listas, k_rrf=60, top=5)` é uma função pura, sem banco;
  - score = Σ 1/(k_rrf + rank), com rank começando em 1;
  - desempate pelo menor rank em qualquer lista e depois pelo menor id, para ser determinístico.
- **Híbrida:** `buscar_hibrida(texto, k=5)` = `rrf([vetorial(50), fulltext(50)], top=k)`.
- Verifique se o `langchain-postgres` instalado tem busca híbrida nativa. Registre a resposta em `docs/decisoes.md`. Não use a nativa (G8).

### 9. Testes

**Sem banco e sem chave** (execução padrão):

- `test_rrf_manual`:
  - listas `A=[1,2,3]` e `B=[3,1,4]`, `k_rrf=60`;
  - scores esperados, calculados à mão e escritos no teste:
    - 1 = 1/61 + 1/62;
    - 3 = 1/63 + 1/61;
    - 2 = 1/62;
    - 4 = 1/63;
  - ordem esperada: `[1, 3, 2, 4]`;
  - inclua também um caso de empate.
- `test_amostra_400`: 400 ids únicos, todos no holdout.
- `test_splits_sem_grupo_cruzado`: nenhum `group_id` aparece nos dois splits.
- `test_tsquery_or`: a função que monta a consulta gera ` | ` entre os lexemas e devolve vazio para texto vazio.

**Com banco** (`@pytest.mark.db`):

- `test_indice_sem_holdout`: nenhum id do holdout nas duas estruturas. Este é o teste anti-vazamento obrigatório.
- `test_indice_contagem`: as duas estruturas têm o mesmo número de linhas do treino.
- `test_autorrecuperacao`: em 5 ids de treino (seed 42), consultar o próprio texto devolve o próprio id em rank 1 na vetorial e no top 3 do full-text.

Configuração:

- `pytest.ini` registra os marcadores `db` e `api`;
- `api` fica excluído por padrão;
- comandos esperados: `pytest` passa sem o Docker de pé; `pytest -m db` passa com o Docker de pé.

### 10. Medidas de sanidade (sem LLM; não são o experimento da F3)

Nos 400 tickets, registre:

- % de consultas com zero resultados no full-text;
- latência p50 dos três recuperadores.

Não calcule precisão de rótulo nem K1: isso é F3.

### 11. Fechamento

- Fixe as versões efetivamente instaladas no `requirements.txt` (`pip freeze` filtrado aos pacotes diretos e suas versões).
- Rode `git status` e `git diff --cached`, e confirme que **não** entraram:
  - `.env`;
  - `data/raw/`;
  - `*.joblib`;
  - nenhuma string `sk-ant`.
- Faça um commit local: `F1: ambiente, dados do case, índices só-treino e testes anti-vazamento`.
- **Sem push.**
- Escreva `docs/planning/F1-report.md` no formato do `CLAUDE.md` §8 e pare.

## Critérios de aceite

1. O passo 0 passou, com as versões registradas.
2. Os asserts de 3 e 4 passaram: 26,5% do case, 85,07% e 69,5% do clássico, contagens e splits.
3. O índice vetorial e o full-text têm só o treino. `test_indice_sem_holdout` passa.
4. `pytest` passa sem banco e sem chave. `pytest -m db` passa com o Docker de pé.
5. `docs/origem.md` e `docs/decisoes.md` estão preenchidos: SHA-256, tag e digest da imagem, modelo e revisão dos embeddings, resposta sobre a híbrida nativa.
6. Nenhum segredo e nenhum CSV bruto no commit.

## Não faça nesta fase

- Chamar a API da Anthropic.
- Calcular precisão de rótulo, K1 ou qualquer métrica de Q1 a Q3.
- Criar índice ANN, mudar `k_rrf`, o número de candidatos ou a configuração `english`.
- Escrever qualquer arquivo na pasta do case.
