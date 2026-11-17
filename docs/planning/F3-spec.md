# F3 — V2, V3, família pré-registrada (Q1) e qualidade de recuperação (Q2)

**Pré-requisito:** portão F2 aprovado em 2026-11-17 (commit `dca94e9`). **G9** decidida (ver §Q2).
**Orçamento:** 75 min. Ao passar de 120% (90 min), pare e reporte.
**Hora de início:** anote o relógio ao começar (`CLAUDE.md` §8).

## Objetivo

1. Corrigir o tempo do report da F2.
2. Rodar V2 e V3 nos 400, com o template e a ordem congelados na F2.
3. Fechar a família pré-registrada de Q1 (McNemar exato + Holm) e os veredictos da F0.
4. Medir a qualidade de recuperação (Q2) numa amostra do holdout definida antes de rodar.

- **Fora da F3:**
  - sensibilidade a k: decidida no portão F3, conforme o tempo que sobrar;
  - V0z;
  - o agente.

## Passos

### 0. Correções herdadas

- **`CLAUDE.md` §8.** O Gustavo já acrescentou a regra de tempos por timestamp e de correção de erros, sem commit ainda. Ela entra no commit da F3. Não altere o texto.
- **`docs/planning/F2-report.md` §8.** Troque "19:57 → ~20:20, ~23 min" por "19:57 → 20:16 (horário do commit `dca94e9`), ~19 min de 60 orçados".
  - O início, 19:57, foi informado pelo Gustavo.
  - Registre a correção na §5 do F2-report.
- **Teste de fumaça:**
  - rode `pytest -m api` uma vez;
  - registre o resultado e o custo (tokens) em `docs/custos.md`;
  - se falhar, corrija o **teste**, não o cliente, e registre.

### 1. Estimativa de custo (antes de chamar)

- **V2 e V3:**
  - meça com `count_tokens` o system de 5 tickets de cada variante;
  - estime 400 × 1,05 × 2 variantes, com saída de 64 tokens como teto, e o preço já registrado em `docs/custos.md` (consulta de 2026-11-17).
- Registre a estimativa. Pare se o acumulado mais a estimativa passar de US$ 3.
- Acumulado atual: US$ 0,1034, mais o teste de fumaça.

### 2. V2 e V3 nos 400: `scripts/f2_llm.py --variante v2|v3` (estender o script da F2)

- **Exemplos:**
  - **V2:** ranks 1 a 5 de `recuperador == vetorial` em `results/f2/vizinhos_400.csv`;
  - **V3:** `results/f2/hibrida_top5_400.csv`;
  - não consultar o banco de novo.
- **Prompt:**
  - template `prompts/classificar_rag_v1.txt`, sem alteração;
  - exemplos em ordem de rank, rank 1 primeiro;
  - formato de cada exemplo igual ao do case.
- Grave `results/f3/exemplos_v2.csv` e `results/f3/exemplos_v3.csv` (`id, ordem, id_exemplo, categoria_exemplo`).
- **Asserts:**
  - 5 exemplos por ticket;
  - todos do treino;
  - nenhum igual ao ticket;
  - nenhum do grupo do ticket.
- **Execução idêntica a V1:**
  - mesmo cliente, concorrência 8 e política de repetição do case;
  - uma rodada por variante;
  - logs `results/f3/llm_log_v2.jsonl` e `results/f3/llm_log_v3.jsonl`, no mesmo formato e sem texto de ticket.
- **Proibido:** ajustar prompt, k ou ordem depois de ver qualquer resultado de V2 ou V3.

### 3. Família pré-registrada de Q1: `scripts/f3_familia.py`

- Junte `predicoes_400.csv` (F2) com V2 e V3 em `results/f3/predicoes_400.csv`, com as colunas `id, rotulo, v0, v1, v2, v3, k1, c, v0_caso`.
- Para cada variante (V0, V1, V2, V3, K1 e C), calcule:
  - acertos;
  - acurácia;
  - Wilson 95%;
  - macro-F1;
  - matriz de confusão;
  - falhas;
  - categoria mais prevista;
  - nas variantes com LLM, também custo por 1.000 tickets e latência p50 e p95.
- **Família, exatamente estas 4 comparações, nesta ordem:**
  - V3 × V1 (primária);
  - V3 × K1;
  - V3 × C;
  - V2 × V3.
- Para cada comparação, McNemar exato (`metricas.mcnemar_exato`). Colunas:
  - acurácias A e B;
  - diferença em pp;
  - b e c;
  - p bruto;
  - p ajustado por Holm sobre as 4.
- Grave `results/f3/familia_q1.csv`. É a única tabela de comparações que vai para o README.
- **Veredictos pré-registrados (F0 §2), aplicados mecanicamente e gravados em `results/f3/veredictos.json`:**
  - "RAG ajuda" = V3 > V1 e p ajustado < 0,05;
  - "o LLM agrega" = V3 > K1 e p ajustado < 0,05;
  - "vale para produção" = acurácia de V3 ≥ acurácia de C.
    - A F0 não definiu teste para esse critério. Aplique a comparação pontual e grave ao lado o p ajustado de V3 × C.
    - Registre a ambiguidade no report. Não escolha outro critério.
- Comparações fora da família (V2 × V1, V2 × K1 e outras) só entram no report rotuladas "exploratório", sem Holm.

### 4. Q2 — qualidade de recuperação: `scripts/f3_recuperacao.py`

#### Amostra (G9)

Varrer o holdout inteiro sequencialmente leva cerca de 2,5 h com as listas reaproveitadas (premissa: p50 de 115 ms na vetorial e 817 ms no full-text, F1). A estimativa de 4,6 h da F1 contava a híbrida como consulta separada.

- **Padrão (G9-a):**
  - amostra aleatória simples de **2.000** tickets do holdout por grupo, `seed=42`, definida antes de qualquer consulta;
  - grave `results/f3/amostra_q2_ids.csv` antes de rodar;
  - os 400 entram com as listas que já existem, como recorte separado.
- **Alternativa (G9-b):** o holdout inteiro, 9.567 tickets, se o Gustavo escolher.
- **Execução:**
  - **vetorial:**
    - embuta as consultas em lote (`embed_documents`);
    - busque com `similarity_search_by_vector` (LangChain), top 50;
  - **full-text:**
    - `buscar_fulltext(texto, 50)`;
    - até 4 threads, cada uma com sua conexão psycopg;
  - **híbrida:** `rrf()` sobre as duas listas, top 5, sem nova consulta.
- Grave `results/f3/vizinhos_q2.csv` (`id_consulta, recuperador, rank, id_vizinho, categoria_vizinho`), sem texto.
- **Asserts:**
  - vizinhos só do treino;
  - nenhum do grupo da consulta.
- **Teste de igualdade:** para 3 ids, a vetorial em lote dá o mesmo top 5 que `buscar_vetorial` ao vivo, e a híbrida do CSV é igual a `buscar_hibrida` ao vivo.
- Registre o tempo de parede.
  - Se a extrapolação passar de 30 min, pare depois de gravar a amostra e reporte. Não reduza a amostra por conta própria.

#### Métricas por recuperador (vetorial, full-text e híbrida), na amostra Q2 e no recorte dos 400

- **Precisão de rótulo@5:**
  - média, por consulta, da fração dos 5 primeiros vizinhos com o mesmo rótulo da consulta;
  - no full-text e na vetorial, use os ranks 1 a 5 de cada lista.
- **Acurácia de K1:** voto majoritário dos 5 vizinhos; empate resolvido pelo melhor rank, com a mesma função da F2.
- **% de consultas sem resultado no full-text.**
- **Diferenças pareadas:**
  - pares: híbrida − vetorial, híbrida − full-text e full-text − vetorial;
  - em precisão@5 e em acerto de K1;
  - IC 95% por bootstrap percentil sobre as consultas, 2.000 reamostragens, `seed=42`.
- Grave em `results/f3/q2_recuperacao.json` e `results/f3/q2_diferencas.csv`.
- **Critério pré-registrado:** "a híbrida recupera melhor que a vetorial" só se o IC de (híbrida − vetorial) em precisão@5 ficar inteiro acima de 0.
- **Contexto obrigatório no report:**
  - teto de ruído de rótulo: 3,82% de discordância entre quase-duplicados (case) e 46,7% de concordância do revisor externo;
  - a normalização 2 favorece documentos curtos (F1 §3).
- **Diferença de universos:**
  - a amostra Q2 cobre todas as faixas do clássico;
  - os 400 cobrem só a faixa de dúvida (`p_max < 0,74`).
  - Reporte os dois, sem misturar.

### 5. Testes

**Execução padrão:**
- `test_familia_ordem`: exatamente 4 comparações, na ordem pré-registrada; Holm aplicado sobre as 4.
- `test_veredictos`: os veredictos são aplicados mecanicamente a partir de `familia_q1.csv`. Teste com um CSV sintético.
- `test_precisao_rotulo`: caso à mão, com consulta Access e vizinhos `[Access, Hardware, Access, Access, Storage]` → 0,6.
- `test_bootstrap_seed`: mesma seed, mesmo IC.
- `test_exemplos_v2_v3`, que lê os CSV de exemplos: 5 por ticket, só do treino, nenhum do grupo do ticket, ordem por rank.

**`@pytest.mark.db`:**
- `test_vetorial_lote_igual_ao_vivo`;
- `test_hibrida_q2_igual_ao_vivo`.

### 6. Fechamento

- Rode `pytest` e `pytest -m db`.
- Confira `git diff --cached`: nada de `.env`, `data/raw/`, `*.joblib` ou `sk-ant`. Confira também:
  - nenhum texto de ticket em `results/` (mesma checagem por amostragem da F2);
  - `git ls-files --eol` sem `w/crlf`.
- Faça um commit local: `F3: V2, V3, família pré-registrada de Q1 e qualidade de recuperação (Q2); corrige tempo da F2`. **Sem push.**
- Escreva `docs/planning/F3-report.md` no formato do `CLAUDE.md` §8.
  - **§2:** a tabela da família e a tabela de Q2.
  - **§3:** cada hipótese da F0 confirmada ou refutada:
    - V2 e V3 > V1;
    - K1 ≈ V3;
    - C ≥ V3;
    - full-text ≥ vetorial;
    - híbrida ≥ ambas.
  - **§7:** a decisão sobre a sensibilidade a k, com o tempo restante.
- Pare.

## Critérios de aceite

1. Tempo da F2 corrigido; regra do `CLAUDE.md` commitada; teste de fumaça executado, com custo registrado.
2. V2 e V3 com o template e a ordem congelados; exemplos só do treino e fora do grupo.
3. `familia_q1.csv` com as 4 comparações, p bruto e p de Holm; `veredictos.json` aplicado mecanicamente.
4. Q2:
   - amostra gravada antes de rodar;
   - precisão@5, K1 e % sem resultado por recuperador;
   - diferenças pareadas com IC.
5. Custo real registrado e acumulado ≤ US$ 3.
6. Nenhum texto de ticket em `results/`, nenhum segredo e nenhum CRLF.

## Não faça nesta fase

- Mudar o prompt, o k, a ordem dos exemplos, a normalização ou a RRF depois de ver qualquer resultado.
- Rodar V2 ou V3 mais de uma vez.
- Acrescentar comparações à família ou trocar a primária.
- Reinterpretar um veredicto negativo ("quase significativo", "tendência"). Reporte o número e o p ajustado.
- Rodar a sensibilidade a k ou o V0z.
