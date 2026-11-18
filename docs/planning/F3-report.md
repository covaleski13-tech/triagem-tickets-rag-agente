# F3 — Report

Status: **concluída, com Q2 fechada no recorte dos 400 (faixa de dúvida).** Decisão do Gustavo: a amostra de 2.000
(G9-a) fica pendente como **F3b**, sem alteração do pré-registro. Commit local feito, sem push.

- **1ª sonda** (4 threads): a extrapolação deu 61,4 min, acima do limite de 30.
- **2ª sonda** (1 conexão, decisão "c reduzida, seguida de b"): a extrapolação deu 66,6 min, acima do limite de 35. Parei.
- **3ª decisão:** fechar a F3 e deixar a amostra como F3b. O `scripts/f3_recuperacao.py` ficou pronto para execução longa: 4 threads, gravação em lotes de 100, retomável e com progresso.
- **O que rodou:** correções herdadas, V2, V3, a família de Q1, os veredictos, Q2 no recorte dos 400 (sem consulta nova) e os testes.
- **A 2ª sonda contrariou o item 3 da decisão anterior** (§3): em sequência ficou mais lento que com 4 threads.
- **F3b concluída (commit "F3b: Q2 na amostra de 2.000"):** as 2.000 consultas rodaram com 4 threads, em 4.785,3 s de parede, ao mesmo tempo que a F4 no mesmo Postgres. O critério pré-registrado de Q2 ("a híbrida recupera melhor que a vetorial") **não é atendido em nenhum dos dois universos** (§2 e §3).
- **Testes antes skipped:** `test_vetorial_lote_igual_ao_vivo` e `test_hibrida_q2_igual_ao_vivo` (`pytest -m db`) dependiam de `results/f3/vizinhos_q2.csv`. Com a F3b, passam.

## 1. O que foi feito

1. Corrigi a §8 e registrei a correção na §5 do `F2-report.md`. A regra nova do `CLAUDE.md` §8 ficou sem alteração. Rodei `pytest -m api` uma vez: 1 passed.
2. Estimei o custo de V2 e V3 com `count_tokens` e registrei em `docs/custos.md` antes de chamar.
3. Estendi `scripts/f2_llm.py` para `--variante v2|v3`: exemplos lidos dos CSV da F2, template e ordem congelados. Rodei V2 e V3 uma vez cada.
4. Escrevi `scripts/f3_familia.py`: família de 4 comparações (McNemar exato + Holm) e veredictos mecânicos.
5. Escrevi `scripts/f3_recuperacao.py`. Ele gravou `results/f3/amostra_q2_ids.csv` (2.000 ids, seed 42) antes de consultar, rodou a vetorial em lote e a sonda de 100 consultas full-text, extrapolou o tempo e **parou**.
6. Calculei Q2 no recorte dos 400 com as listas da F2 (`--so-400`, sem consulta nova). Escrevi os testes e rodei `pytest` e `pytest -m db`.
7. Rodei a 2ª sonda (1 conexão) e parei pelo limite de 35 min.
8. Adaptei o `f3_recuperacao.py` para a F3b, com a retomada em `src/triagem_rag/lotes.py`. A retomada tem teste com 3 ids falsos, e o laço foi conferido com 4 ids reais numa pasta temporária, sem tocar `results/`. Depois fiz o commit.

## 2. Resultados

**Variantes nos 400** (`scripts/f3_familia.py` → `results/f3/metricas_f3.json`, `results/f3/predicoes_400.csv`):

| Variante | Acertos | Acurácia | Wilson 95% | Macro-F1 | Mais prevista | Custo/1.000 | Latência p50 / p95 |
|---|---|---|---|---|---|---|---|
| V0 | 104 | 26,00% | 21,94–30,51% | 0,2577 | Access (159) | US$ 0,1503 | 1.087 / 1.458 ms |
| V1 | 95 | 23,75% | 19,84–28,16% | 0,2231 | Access (161) | US$ 0,1081 | 985 / 1.553 ms |
| V2 (vetorial) | 191 | 47,75% | 42,90–52,64% | 0,4693 | Access (124) | US$ 0,1100 | 987 / 1.248 ms |
| V3 (híbrida) | 181 | 45,25% | 40,44–50,15% | 0,4505 | Access (113) | US$ 0,0886 | 988 / 1.479 ms |
| K1 | 219 | 54,75% | 49,85–59,56% | 0,5128 | HR Support (133) | — | — |
| C | 278 | 69,50% | 64,82–73,81% | 0,7095 | Hardware (143) | — | — |

Nenhuma falha, nenhuma saída inválida na 1ª tentativa e nenhum erro de API em V2 e V3.

**Família pré-registrada de Q1** (`results/f3/familia_q1.csv`; McNemar exato, Holm sobre as 4):

| Comparação | Acurácia A | Acurácia B | Dif. (pp) | b | c | p bruto | p Holm |
|---|---|---|---|---|---|---|---|
| V3 × V1 (primária) | 45,25% | 23,75% | +21,50 | 100 | 14 | 3,49e-17 | 1,40e-16 |
| V3 × K1 | 45,25% | 54,75% | −9,50 | 38 | 76 | 4,75e-04 | 9,50e-04 |
| V3 × C | 45,25% | 69,50% | −24,25 | 37 | 134 | 4,14e-14 | 1,24e-13 |
| V2 × V3 | 47,75% | 45,25% | +2,50 | 33 | 23 | 0,229 | 0,229 |

**Veredictos** (`results/f3/veredictos.json`, aplicados mecanicamente):

| Critério (F0 §2) | Veredicto |
|---|---|
| "RAG ajuda" = V3 > V1 e p Holm < 0,05 | **sim** |
| "O LLM agrega" = V3 > K1 e p Holm < 0,05 | **não**: V3 ficou abaixo de K1 |
| "Vale para produção" = acurácia V3 ≥ C (pontual; p Holm de V3 × C = 1,24e-13, ao lado) | **não** |

**Comparações exploratórias**, fora da família e sem Holm (`metricas_f3.json`):

| Comparação | b | c | p |
|---|---|---|---|
| V2 × V1 | 106 | 10 | 2,2e-21 |
| V2 × K1 | 51 | 79 | 0,0175 |
| V2 × C | 38 | 125 | 5,0e-12 |
| V3 × V0 | 96 | 19 | 1,4e-13 |

**Q2 no recorte dos 400**, faixa de dúvida `p_max < 0,74` (`scripts/f3_recuperacao.py --so-400` → `results/f3/q2_recuperacao.json`, `q2_diferencas.csv`):

| Recuperador | Precisão@5 (IC 95% bootstrap) | Acurácia K1 | Sem resultado |
|---|---|---|---|
| Vetorial | 0,5145 (0,482–0,5465) | 235/400 = 58,75% | 0% |
| Full-text | 0,3565 (0,327–0,389) | 165/400 = 41,25% | 0% |
| Híbrida | 0,478 (0,447–0,509) | 219/400 = 54,75% | 0% |

| Diferença pareada | Precisão@5 (IC 95%) | Acerto de K1 (IC 95%) |
|---|---|---|
| Híbrida − vetorial | −0,0365 (−0,0645 a −0,009) | −0,040 (−0,0875 a +0,010) |
| Híbrida − full-text | +0,1215 (+0,094 a +0,148) | +0,135 (+0,0825 a +0,185) |
| Full-text − vetorial | −0,158 (−0,197 a −0,117) | −0,175 (−0,235 a −0,1125) |

A K1 híbrida do recorte (219) bate com a K1 da F2.

**Q2 na amostra G9-a** (2.000 tickets do holdout, todas as faixas do clássico; F3b; `scripts/f3_recuperacao.py` → `results/f3/vizinhos_q2.csv`, `q2_recuperacao.json` → `amostra_q2`, e `q2_diferencas.csv`):

| Recuperador | Precisão@5 (IC 95% bootstrap) | Acurácia K1 | Sem resultado |
|---|---|---|---|
| Vetorial | 0,7406 (0,7264–0,7546) | 1.606/2.000 = 80,30% | 0% |
| Full-text | 0,5388 (0,5233–0,5543) | 1.225/2.000 = 61,25% | 0% |
| Híbrida | 0,6892 (0,6748–0,7030) | 1.542/2.000 = 77,10% | 0% |

| Diferença pareada (amostra) | Precisão@5 (IC 95%) | Acerto de K1 (IC 95%) |
|---|---|---|
| Híbrida − vetorial | −0,0514 (−0,0616 a −0,0418) | −0,032 (−0,049 a −0,0155) |
| Híbrida − full-text | +0,1504 (+0,1391 a +0,1616) | +0,1585 (+0,138 a +0,1795) |
| Full-text − vetorial | −0,2018 (−0,2177 a −0,186) | −0,1905 (−0,2145 a −0,1675) |

- **Exploratório, fora do pré-registro, sem teste** (`scripts/f3b_fechamento.py` → `q2_recuperacao.json`, `exploratorio_classico_vs_k1_amostra`): o clássico acerta 1.710/2.000 = 85,50% (Wilson 83,89–86,98%) nos mesmos 2.000 ids, de `data/caso/f3_probs_holdout_grupo.csv`. O K1 fica abaixo: vetorial 80,30%, híbrida 77,10%, full-text 61,25%.
- **Recorte dos 400:** idêntico ao commit da F3. Conferido com a comparação do bloco `recorte_400` contra o `HEAD` e com o `git diff` do CSV (só linhas `amostra_q2` acrescentadas).
- **Tempos** (`q2_recuperacao.json` → `tempos`): execução da F3b com 4 threads e 2.000 consultas, **4.785,3 s de parede (~79,8 min)**, com a F4 rodando no mesmo Postgres ao mesmo tempo. As sondas ficam como histórico. A extrapolação da 1ª sonda (61,4 min) subestimou a parede real, mas essa execução teve concorrência da F4, então os números não são comparáveis.

**Sondas (histórico).** Tempos das duas sondas, ambas sobre os mesmos 100 primeiros ids de `amostra_q2_ids.csv` (`results/f3/q2_tempos.json`; a 1ª sonda está em `rodada_anterior`):

| Sonda | Conexões | Vetorial em lote (2.000) | 100 consultas full-text (parede) | Por consulta | Extrapolação total | Limite |
|---|---|---|---|---|---|---|
| 1ª (20:25 → 20:32) | 4 | 236,4 s | 172,5 s | 1,73 s | 61,4 min | 30 min |
| 2ª (20:37:45 → 20:44:21) | 1 | 198,6 s | 190,0 s | 1,90 s | 66,6 min | 35 min |

- `SHOW shared_buffers` = `128MB`, o padrão da imagem. Só li o valor; nenhuma configuração do Postgres foi alterada.
- **Extrapolação:** vetorial + (tempo da sonda × 2.000 / 100).

**Tamanho dos textos** (palavras por ticket; cálculo direto sobre o DS2, sem banco):

| Conjunto | Média | Mediana | p90 |
|---|---|---|---|
| Recorte dos 400 | 45,0 | 26 | 99 |
| Sonda (100 primeiros ids da amostra) | 56,0 | 30 | 107 |
| Amostra Q2 (2.000) | 44,5 | 27 | 103 |

## 3. O que contraria a hipótese ou a expectativa

Hipóteses da F0 §2:

- **V2 e V3 > V1: confirmada.**
  - V3 × V1: +21,5 pp, p Holm 1,40e-16.
  - V2 × V1: +24,0 pp, exploratório, p 2,2e-21.
  - Exemplos recuperados por similaridade ajudam muito. Exemplos aleatórios não ajudam (V1 ≈ V0, F2).
- **K1 ≈ V3: refutada, e na direção oposta à esperada.**
  - K1 fica **acima** de V3: +9,5 pp, p Holm 9,50e-04.
  - V2 também fica abaixo de K1: −7,0 pp, exploratório, p 0,0175.
  - O LLM com os mesmos 5 vizinhos erra mais que o voto majoritário deles: os vizinhos ajudam o LLM, mas ele ainda perde para o voto.
  - A superprevisão de Access cai (V3: 113; V0: 159), mas persiste. Há 49 Access reais.
- **C ≥ V3: confirmada.** C fica +24,25 pp acima, p Holm 1,24e-13.
- **Full-text ≥ vetorial: refutada nos dois universos.**
  - Recorte dos 400: precisão@5 −0,158 (IC −0,197 a −0,117); K1 −17,5 pp.
  - Amostra de 2.000: precisão@5 −0,2018 (IC −0,2177 a −0,186); K1 −19,05 pp.
  - A expectativa era que o texto pré-processado favorecesse a busca por termos. Não se confirmou.
- **Híbrida ≥ ambas:**
  - **sobre o full-text:** confirmada nos dois universos;
  - **sobre a vetorial:** refutada nos dois. Precisão@5: −0,0365 no recorte e −0,0514 na amostra, com os dois IC inteiros abaixo de 0. Em K1, a amostra também fica abaixo: −3,2 pp, IC −4,9 a −1,55.
  - O critério pré-registrado ("a híbrida recupera melhor que a vetorial" só se o IC de híbrida − vetorial ficar inteiro acima de 0) **não é atendido em nenhum dos dois universos**. A híbrida RRF recupera pior que a vetorial sozinha.
  - Coerente com isso: V2 × V3 dá +2,5 pp para a vetorial, p Holm 0,229, sem diferença significativa.

**Contexto obrigatório:**

- **Teto de ruído de rótulo:** 3,82% de discordância entre quase-duplicados (case) e 46,7% de concordância do revisor externo. A acurácia mede aderência à convenção do dataset, não "verdade".
- **Normalização 2:** ela favorece documentos curtos (F1 §3). Isso pode explicar parte do desempenho do full-text.
- **Universos diferentes:** o recorte dos 400 cobre só a faixa de dúvida do clássico; a amostra G9-a cobre todas as faixas. Os dois são reportados separados. A amostra é aleatória simples de 2.000 dos 9.567 do holdout; os números são estimativas para o holdout, com os IC acima.

**Ambiguidade registrada:** a F0 não definiu teste para "vale para produção". Apliquei a comparação pontual (V3 ≥ C) e gravei ao lado o p Holm de V3 × C. As duas leituras dão "não".

**Paralelismo: minha leitura anterior estava errada, e o item 3 da decisão contraria os dados.**

- **Leitura anterior:** a 1ª versão deste report dizia que as 4 threads tinham deixado o full-text mais lento. Comparei os 1,7 s por consulta da 1ª sonda com o p50 sequencial de 817 ms da F1.
- **Por que estava errada:** comparei medidas diferentes, em consultas diferentes. Uma é tempo de parede médio, nos 100 primeiros ids da amostra Q2. A outra é a mediana da latência, nos 400.
- **O que mostra a 2ª sonda,** com os mesmos 100 ids e 1 conexão: **190,0 s**. Com 4 threads, tinham sido **172,5 s**. Nesses 100 ids, as 4 threads deram vazão igual ou um pouco maior, e não menor.
- **O que a decisão pede:** que eu registre "o paralelismo com 4 threads reduziu a vazão (172,5 s para 100 consultas, contra a medição sequencial)". Não escrevi essa frase, porque a medição sequencial nas mesmas consultas a contradiz. Registro aqui os dois números.
- **O que fica em aberto:** por que o paralelismo quase não ajudou (ganho de ~9%, com 12 CPUs no Docker). A hipótese de disputa de cache e I/O, com `shared_buffers` em 128 MB, não foi verificada.

**A extrapolação provavelmente superestima o tempo total.**

- A sonda usa os 100 primeiros ids da amostra, que são mais longos: média de 56,0 palavras, contra 44,5 da amostra inteira (tabela na §2).
- Mais palavras dão mais lexemas na consulta em OR.
- Não medi o tempo da amostra inteira, então isso é **hipótese**. Mesmo assim, parei pela regra, sem reinterpretar o limite.

## 4. Desvios da spec

- **Q2 em dois commits:** a F3 fechou a Q2 no recorte dos 400. A amostra de 2.000 (G9-a) rodou como F3b, por decisão do Gustavo, sem alteração do pré-registro: mesma amostra, seed, k, RRF e normalização.
- **`scripts/f3b_fechamento.py`:** reorganiza o bloco `tempos` de `q2_recuperacao.json` (status, execução, sondas como histórico) e acrescenta o exploratório do clássico. Não altera nenhuma métrica.
- **`scripts/f3_recuperacao.py --so-400`:** modo acrescentado para calcular Q2 no recorte dos 400 só com as listas da F2, sem consultar o banco.
- **`scripts/f3_recuperacao.py` sem argumento (F3b):**
  - 4 threads no full-text, a vetorial embutida em lote e buscada com `similarity_search_by_vector`, top 50;
  - grava `results/f3/vizinhos_q2.csv` em lotes de 100, só depois dos asserts anti-vazamento do lote;
  - retomável: na partida, regrava o arquivo só com as consultas completas (as que têm as 5 linhas da híbrida e categoria válida) e pula essas;
  - imprime n feito, tempo decorrido e tempo restante extrapolado;
  - só calcula as métricas com os 2.000 presentes. Se faltar algum, sai com "incompleto".
  - O limite de 30/35 min e as opções `--threads`/`--limite` da 2ª sonda foram removidos. As sondas não gravaram resultado parcial, então a F3b começa do zero.
- **Testes antes skipped:** `test_vetorial_lote_igual_ao_vivo` e `test_hibrida_q2_igual_ao_vivo` passam desde a F3b. Durante a F4 eles já tinham passado sobre o CSV parcial, nos 3 primeiros ids.
- **Arquivos além dos pedidos:** `results/f3/pred_v2.csv`, `pred_v3.csv`, `llm_meta_v2.json`, `llm_meta_v3.json`, `metricas_f3.json` e `q2_tempos.json`. São só ids, categorias e números.
- **Q2 com resultados incompletos:** quando há menos de 5 vizinhos, a precisão@5 usa como denominador o número de vizinhos devolvidos. Uma consulta sem resultado vale precisão 0 e K1 errado. No recorte, nenhuma consulta ficou sem resultado.

## 5. Erros e correções durante a execução

- **F2-report §8:** corrigido para "19:57 → 20:16 (horário do commit `dca94e9`), ~19 min de 60 orçados", com registro na §5 do F2-report.
- **Teste de fumaça sem tokens:** o `test_fumaca_api` passou, mas não registra os tokens. Para não repetir a chamada, registrei em `docs/custos.md` um teto: 48 tokens de entrada (`count_tokens`) + 64 de saída = ≤ US$ 0,0000368. O teste não foi alterado: ele passou, e a spec só manda corrigir o teste em caso de falha.
- **Edição de script por heredoc:** uma substituição via Python em heredoc gravou uma quebra de linha literal no lugar de `\n` em `scripts/f2_llm.py`. O `py_compile` acusou o erro, e eu corrigi com edição direta antes de rodar. Mesmo erro da F1. Para editar código, uso o Edit, não heredoc.
- **Q2:** parado pela regra de 30 min na 1ª sonda e pela regra de 35 min na 2ª (§2).
- **Diagnóstico errado na 1ª versão deste report:** concluí que 4 threads eram mais lentas que 1, comparando medidas diferentes em consultas diferentes. A 2ª sonda corrigiu isso (§3).
- **Monitor da 2ª sonda:** o primeiro monitor que armei lia "o arquivo de saída mais recente" e podia ler o próprio log. Cancelei e rearmei com o nome explícito do arquivo, antes de qualquer leitura de resultado.
- **Frase duplicada na §8** do commit `0d780fa` ("As esperas pelas decisões do Gustavo não entram na conta." duas vezes): corrigida no commit da F3b.
- **Retomada da F3b:** uma linha truncada no fim do CSV (execução morta durante a escrita) podia sobreviver com valores errados. Passei a validar categoria e recuperador ao ler e cobri o caso no `test_retomada_lotes`.

## 6. Custo de API

| | Estimado | Real |
|---|---|---|
| V2 | US$ 0,0507 | US$ 0,043986 |
| V3 | US$ 0,0451 | US$ 0,035457 |
| Teste de fumaça | — | ≤ US$ 0,0000368 (teto) |
| **F3** | **US$ 0,0958** | **≤ US$ 0,079480** |
| **Acumulado do projeto** | | **≤ US$ 0,182859** de US$ 3 |

Fonte: `docs/custos.md`, preço oficial de 2026-11-17. Q2 não usa API.

## 7. Pendências e decisões que dependem do Gustavo

1. **F3b: concluída.** Q2 na amostra de 2.000 está na §2, e o critério pré-registrado não é atendido (§3).
2. **Commits:** F3 (`0d780fa`, Q2 no recorte dos 400) e F3b ("F3b: Q2 na amostra de 2.000").
3. **Sensibilidade a k: cortada** (decisão do Gustavo, pela ordem de corte da F0 §7, 2º item). Não rodou.
4. **"Vale para produção"** sem teste definido na F0 (§3). As duas leituras dão "não", então não há impacto prático agora.

## 8. Tempo gasto × orçado

- **1º trecho:** 20:20:56 → 20:35:03, ~14 min (`date` no início e depois do report; 1ª sonda de 20:25:17 a 20:32:08).
- **2º trecho, após a decisão:** 20:37:21 → 20:45:40, ~8 min (`date` no início e depois dos testes finais; 2ª sonda de 20:37:45 a 20:44:21).
- **3º trecho, após a decisão F3b:** 20:51:47 → 20:53:36, ~2 min, mais o tempo antes do primeiro arquivo (leitura do script), que ficou sem timestamp.
  - Início: mtime de `src/triagem_rag/lotes.py`, o primeiro arquivo criado no trecho.
  - Fim: `date` antes do commit. O horário exato do commit está no `git log`.
- **Total da F3:** ~24 min com timestamp de 75 orçados (14 + 8 + 2), mais o trecho sem timestamp do início do 3º. As esperas pelas decisões do Gustavo não entram na conta.
- **F3b:**
  - execução em terminal separado, sem acompanhamento: 4.785,3 s de parede (`q2_tempos.json`, `execucoes_f3b`), com a F4 rodando no mesmo Postgres;
  - fechamento: de 22:23:11 (`date` no início) até o commit da F3b (horário no `git log`).
