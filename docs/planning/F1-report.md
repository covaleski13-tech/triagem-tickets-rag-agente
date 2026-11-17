# F1 — Report

Status: **concluída.** Os passos 0 a 11 foram executados com a emenda da F1 (`ts_rank_cd(tsv, q, 2)`, decisão do
Gustavo, opção b). `pytest` e `pytest -m db` passam. Commit local feito, sem push.

## 1. O que foi feito

1. Passo 0: conferi o ambiente. O Docker respondeu depois que atualizei o PATH da sessão (ver §5).
2. Rodei `git init`. Criei a estrutura do `CLAUDE.md` §6, o `.gitignore`, o `.env.example`, o `LICENSE` (MIT), um `README.md` mínimo e a `.venv` (Python 3.12.10).
3. Copiei os arquivos do case com atribuição e escrevi o `docs/origem.md` com os SHA-256 (`scripts/f1_copiar_origem.py`).
4. Gerei a amostra dos 400 e as predições V0 do case (`scripts/f1_amostra.py`).
5. Conferi a integridade dos dados e reproduzi o clássico (`scripts/f1_integridade.py`).
6. Subi Postgres 17 + pgvector pelo `docker-compose.yml`, com o digest fixado.
7. Gerei os embeddings bge-small (revisão fixada) e montei os índices vetorial e full-text, só com treino (`scripts/f1_indexar.py`).
8. Implementei os recuperadores e a RRF em `src/triagem_rag/recuperacao.py` e os testes em `tests/`.
9. Rodei a sanidade nos 400 (`scripts/f1_sanidade.py`) e fixei o `requirements.txt`.
10. Apliquei a emenda F1: normalização 2 no `ts_rank_cd` e tsquery montada no SQL com `quote_literal`. Rodei a ingestão do full-text duas vezes, depois os testes e o commit.

## 2. Resultados

| Medida | Valor | Fonte |
|---|---|---|
| Linhas do log do case / ids únicos | 401 / 400 | `scripts/f1_amostra.py` (saída do console) |
| Acurácia V0 do case nos 400 | 106/400 = 26,50% | `scripts/f1_amostra.py` → `data/caso/f3_v0_pred.csv` |
| CSV bruto / splits | 47.837 / 47.837 linhas, join 1:1 | `scripts/f1_integridade.py` → `results/f1/integridade.json` |
| Treino / holdout (`split_grupo`) | 38.270 / 9.567 | idem |
| Grupos nos dois lados | 0 | idem |
| Clássico, holdout | 8.139/9.567 = 85,0737% (alvo 85,07% ± 0,05 pp) | idem |
| Clássico, 400 | 278/400 = 69,5% | idem |
| Concordância das predições com `f3_probs_holdout_grupo.csv` do case | 100,0% | idem |
| Tempo de treino do clássico | 41,5 s | idem |
| Modelo salvo | `data/modelos/modelo_f71cfd480a50.joblib` (fora do git) | idem |
| Linhas no índice vetorial / full-text | 38.270 / 38.270 | `scripts/f1_indexar.py` → `results/f1/indexacao.json` |
| Tempo para embutir o treino (CPU) | 867,4 s | idem |
| Tempo de inserção no PGVector | 29,4 s | idem |
| Full-text depois de 2 ingestões seguidas | 38.270 linhas, 38.270 ids distintos | `scripts/f1_indexar.py --so-fulltext` (2×) + `count(*)`, `count(distinct id)` |
| `pytest` (sem banco, sem chave) | 6 passed, 4 deselected | `.venv/Scripts/python -m pytest -q` |
| `pytest -m db` (com a emenda) | 4 passed (`test_indice_sem_holdout`, `test_tsquery_or`, `test_indice_contagem`, `test_autorrecuperacao`) | `.venv/Scripts/python -m pytest -q -m db` |
| Full-text com zero resultados nos 400 | 0/400 = 0,0% | `scripts/f1_sanidade.py` → `results/f1/sanidade_400.json` |
| Latência p50 vetorial / full-text / híbrida | 137,6 / 982,9 / 1.150,3 ms (n = 400, 1 passada sequencial, CPU local) | idem; **medida antes da emenda** (normalização 0) |

Ambiente (passo 0, 2026-11-17 17:44): Python 3.12.10; git 2.56.0.windows.4; Docker Client/Engine 29.9.3
(Docker Desktop 4.99.0, contexto `desktop-linux`); Docker Compose v5.7.0; 338 GB livres em `C:`.

## 3. O que contraria a hipótese ou a expectativa

**O full-text com `ts_rank_cd` sem normalização (configuração da F0 §5) contrariou a expectativa: não recupera o
próprio texto.** Com essa configuração, `test_autorrecuperacao` falhou. Diagnóstico nos 5 ids de treino do teste
(seed 42), feito só no treino:

| id | palavras | lexemas na consulta | docs que casam (de 38.270) | rank do próprio id, norm. 0 (F0) | norm. 1 | norm. 2 (adotada) | norm. 32 |
|---|---|---|---|---|---|---|---|
| 18556 | 18 | 14 | 35.342 | 758 | 155 | 1 | 758 |
| 22958 | 13 | 10 | 34.188 | 1.277 | 231 | 1 | 1.277 |
| 34269 | 35 | 19 | 35.040 | 252 | 44 | 1 | 252 |
| 11585 | 26 | 16 | 35.720 | 674 | 118 | 2 | 674 |
| 37714 | 16 | 12 | 28.301 | 204 | 13 | 1 | 204 |

- **Por que falha:** a consulta em OR casa de 74% a 93% do índice. Sem normalização, o `ts_rank_cd` premia documentos longos, e o topo é ocupado sempre pelos mesmos tickets de 556 a 931 palavras (ids 4427, 1319, 3277, 774, 39442, 10977). A vetorial deu rank 1 nos 5.
- **Decisão:** o Gustavo escolheu a normalização 2 (emenda F1, congelada; ver `docs/decisoes.md`). Com ela, o teste passa sem mudanças (top 3 no full-text). A evidência para a escolha vem só desses 5 tickets de treino. Nenhuma métrica de rótulo foi calculada e nada do holdout foi consultado.
- **Q2 ainda não respondida:** a hipótese "o full-text fica perto da vetorial ou acima" segue sem teste. Isso é F3. O que se viu aqui é que a configuração original do full-text tinha um viés de tamanho.
- **Lentidão:** a mesma causa deixa o full-text lento, porque cada consulta ranqueia ~35 mil documentos. O p50 foi de 982,9 ms, contra 137,6 ms da vetorial. A sanidade (800 consultas full-text) levou ~28 min (18:09 → 18:37). A normalização não muda o número de documentos que casam.
- **Zero resultados:** 0% nos 400, o esperado para uma consulta em OR.
- **Erro de estimativa meu durante a execução:** previ 60 a 70 min para a sanidade, a partir de uma única consulta observada em 4,5 s. Levou ~28 min. A estimativa não entra em nenhum número.

## 4. Desvios da spec

- **Python 3.12.10** em vez de 3.11: é a única versão instalada e atende o "3.11+" do `CLAUDE.md`.
- **Digest fixado no `docker-compose.yml`** (`pgvector/pgvector:pg17@sha256:b513c485…`), além de registrado: a tag `pg17` é móvel.
- **Emenda F1 (decisão do Gustavo):** `ts_rank_cd(tsv, q, 2)` no lugar de `ts_rank_cd(tsv, q)`. A F0 §5 foi anotada com "(emenda F1: normalização 2)".
- **tsquery montada no SQL** (instrução do Gustavo): `string_agg(quote_literal(lexeme), ' | ')` sobre `unnest(to_tsvector('english', texto))`, com cast para `tsquery`. O cast evita reaplicar o stemmer, o que aconteceria com `to_tsquery('english', ...)`.
- **`test_tsquery_or` agora precisa do banco** (`@pytest.mark.db`). A spec o listava entre os testes sem banco, mas a função que monta a consulta passou a ser SQL. O teste cobre ` | ` entre lexemas, texto vazio, texto só com palavras funcionais, texto com aspas simples e `:`, e um lexema literal `o'b:c`. Por isso a execução padrão tem 6 testes, e não 7.
- **`src/triagem_rag/dados.py` próprio** para ler o DS2, em vez de importar o `caso/comum.py`. O `comum.py` copiado usa caminhos padrão relativos à pasta do case. A convenção de id é a mesma (índice da linha, base 0), e a concordância de 100% com as predições do case confirma o alinhamento.
- **Idempotência da ingestão:**
  - **full-text:** verificada, com 2 execuções seguidas e 38.270 linhas, sem duplicata;
  - **vetorial:** **não verificada** por reexecução, porque custaria mais ~15 min de embeddings. Ela é garantida só por construção (`pre_delete_collection=True` e id do documento = id do ticket).
- **`scripts/f1_indexar.py --so-fulltext`:** opção acrescentada para reindexar só o full-text.
- **Sanidade (passo 10) não refeita depois da emenda:** a % de zeros não depende do ranqueamento, mas a latência do full-text e da híbrida foi medida com a normalização 0.

## 5. Erros e correções durante a execução

- **Bloqueio anterior (17:36–17:37, ~1 min):**
  - na primeira tentativa, o passo 0 retornou `docker: command not found` no Git Bash, e o `Get-Command docker` voltou vazio no PowerShell;
  - concluí que o Docker Desktop não estava instalado, porque procurei só em `C:\Program Files\Docker` e dentro do WSL. Parei e reportei;
  - o Gustavo informou que o problema era o PATH e o engine parado. O Docker está em `C:\Users\gusta\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe` (instalação por usuário), fora do PATH herdado pela sessão;
  - correção: recarreguei o PATH de Máquina e Usuário no PowerShell e acrescentei o diretório no Bash. Retomei do passo 0 às 17:44.
- **Revisão do modelo de embeddings:** escrevi no código, por um instante, um hash de memória. Troquei por `PENDENTE` antes de qualquer execução e só fixei o valor depois de lê-lo com `huggingface_hub.model_info`. O valor lido coincidiu.
- **pip:** deu timeouts de leitura no PyPI (sympy, pandas), e o pip retomou sozinho.
- **`test_autorrecuperacao`:** falhou no full-text com a normalização 0. Parei e reportei. Foi corrigido pela emenda F1 depois da decisão do Gustavo (§3).

## 6. Custo de API

Fase: US$ 0 (nenhuma chamada). Acumulado: US$ 0.

## 7. Pendências e decisões que dependem do Gustavo

1. **Risco de tempo para a F3: latência do full-text de ~1 s por consulta.** O p50 foi de 982,9 ms (híbrida: 1.150,3 ms), medido com a normalização 0. A normalização 2 não reduz os ~35 mil documentos ranqueados por consulta.
   - **400 consultas:** cada passada custa ~6,5 min no full-text (400 × 0,983 s) e ~7,7 min na híbrida (400 × 1,150 s).
   - **Holdout inteiro (Q2):** 9.567 consultas × (0,983 + 1,150 s) dão ~5,7 h em sequência, se a híbrida recalcular o full-text. **Premissa:** extrapolação linear do p50.
   - **Mitigação possível, sem mudar a configuração:** calcular o full-text e a vetorial uma vez por consulta e fundir com a `rrf()` em memória. A decisão fica para a spec da F3.
2. `src/triagem_rag/caso/triagem.py` importa `from comum import ...` sem pacote, e o `comum.py` aponta para caminhos do case. Os dois funcionam com o `sys.path` apontando para `caso/`, como em `scripts/f1_integridade.py`. Falta definir na F4 como chamar `triar()`.
3. A idempotência da ingestão vetorial não foi verificada por reexecução (§4).

## 8. Tempo gasto × orçado

- **Primeira tentativa (bloqueio):** ~1 min.
- **Retomada:** 17:44 → 18:39 (~55 min). Desse tempo, ~15 min foram de embeddings e ~28 min da sanidade, em espera.
- **Emenda e fechamento, depois da decisão:** ~10 min (até ~18:50).
- **Total:** ~66 min de 105 min orçados (o limite de 120% é 126 min).
