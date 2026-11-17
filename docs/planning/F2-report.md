# F2 — Report

Status: **concluída.** V0, V1, K1 e C rodaram nos 400 tickets, e V0 passou no portão de reprodução. Os vizinhos dos
400 ficaram gravados para a F3. Os testes passam: `pytest` 31 passed e `pytest -m db` 5 passed. Commit local feito,
sem push.

## 1. O que foi feito

1. Pré-condições: chave presente no `.env` (só conferi a presença), `LANGCHAIN_TRACING_V2=false`, Docker de pé e testes da F1 passando. Instalei `langchain-anthropic` e fixei `anthropic`, `langchain-anthropic`, `pydantic` e `scipy`.
2. Consultei o preço na página oficial (2026-11-17) e estimei o custo com `count_tokens` antes de chamar (`docs/custos.md`).
3. Escrevi `src/triagem_rag/llm.py` (`ChatAnthropic`), `esquema.py` (Pydantic) e `metricas.py` (Wilson, macro-F1, matriz de confusão, McNemar exato, Holm), com testes.
4. Gravei vizinhos, híbrida top 5, K1 e C sem API (`scripts/f2_vizinhos.py`).
5. Rodei V0 (`scripts/f2_llm.py --variante v0`). Passou no portão.
6. Rodei V1 (`scripts/f2_llm.py --variante v1`) com `prompts/classificar_rag_v1.txt`.
7. Consolidei as métricas (`scripts/f2_metricas.py`) e atualizei `docs/custos.md` e `docs/decisoes.md`.

## 2. Resultados

Todas as linhas abaixo vêm de `scripts/f2_metricas.py` → `results/f2/metricas_f2.json` e `results/f2/predicoes_400.csv`, salvo indicação.

| Variante | Acertos | Acurácia | Wilson 95% | Macro-F1 | Falhas | Mais prevista |
|---|---|---|---|---|---|---|
| V0 (prompt do case, nova rodada) | 104/400 | 26,00% | 21,94% a 30,51% | 0,2577 | 0 | Access (159) |
| V1 (5 exemplos aleatórios do treino) | 95/400 | 23,75% | 19,84% a 28,16% | 0,2231 | 0 | Access (161) |
| K1 (voto dos 5 vizinhos híbridos, sem LLM) | 219/400 | 54,75% | 49,85% a 59,56% | 0,5128 | 0 | HR Support (133) |
| C (classificador clássico) | 278/400 | 69,50% | 64,82% a 73,81% | 0,7095 | 0 | Hardware (143) |
| V0 do case (`data/caso/f3_v0_pred.csv`) | 106/400 | 26,50% | 22,41% a 31,03% | 0,2667 | 0 | Access (160) |

Distribuição real dos rótulos nos 400: Hardware 112, Miscellaneous 87, HR Support 83, Access 49, Storage 29,
Administrative rights 26, Internal Project 10, Purchase 4.

| LLM | Chamadas | Por ticket | Inválidas na 1ª tentativa | Erros de API | Tokens de entrada (média) | Tokens de saída (média) | Custo | Por 1.000 tickets | Latência p50 | Latência p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| V0 | 400 | 1,00 | 0 | 0 | 1.383,5 | 23,9 | US$ 0,060123 | US$ 0,1503 | 1.087,0 ms | 1.458,0 ms |
| V1 | 400 | 1,00 | 0 | 0 | 962,2 | 23,8 | US$ 0,043256 | US$ 0,1081 | 985,1 ms | 1.553,1 ms |

Latência medida por chamada, no cliente, com concorrência 8.

**Comparações exploratórias.** McNemar exato, fora da família pré-registrada, **sem Holm**:

| Comparação | b (A acerta, B erra) | c (B acerta, A erra) | p |
|---|---|---|---|
| V0 novo × V0 do case | 9 | 11 | 0,824 |
| V1 × V0 | 16 | 25 | 0,211 |
| K1 × C | 43 | 102 | 1,05e-06 |
| V1 × C | 22 | 205 | 2,19e-38 |

**Outros números:**

- **V0 novo × V0 do case:** mesma predição em 88,25% dos tickets (`metricas_f2.json`, `v0_mesma_predicao_que_caso_pct`).
- **V1 × V0:** mesma predição em 76,75% (cálculo direto sobre `predicoes_400.csv`).
- **System do V0:** os 8 exemplos estão em `results/f2/exemplos_v0.csv`. SHA-256 do system: `462ed6042d90eeea…` (completo em `metricas_f2.json`). Os tokens de entrada por id são **idênticos** aos do log do case nos 400 tickets (diferença 0 em todos; comparação só de leitura com `planning/F3/f3_llm_log.jsonl`). Isso é forte evidência de que o system e a mensagem são os mesmos.
- **Vizinhos:** 40.000 linhas (50 por recuperador por ticket). Todos os asserts anti-vazamento passaram: vizinhos só do treino, nenhum igual à consulta, nenhum do grupo da consulta. As buscas levaram 539,2 s com 4 conexões (`scripts/f2_vizinhos.py` → `results/f2/vizinhos_meta.json`).
- **Híbrida:** a do CSV bate com a ao vivo em 3 ids (`test_hibrida_csv_igual_ao_vivo`).
- **Custo da F2:** US$ 0,103379 (real), contra US$ 0,1239 estimados.

## 3. O que contraria a hipótese ou a expectativa

Comparação com as hipóteses direcionais da F0 §2 (Q1):

- **V0 reproduz?** **Sim.** 26,00% fica dentro do critério pré-registrado [22,25%; 31,0%]. O McNemar contra o case dá b = 9, c = 11, p = 0,824, com 88,25% de predições iguais. A variação entre rodadas troca o acerto em 20 dos 400 tickets (5%).
  - **Nota (spec §4):** o IC do case (22,25% a 31,0%) era bootstrap. O Wilson de 106/400 é 22,41% a 31,03%. O critério usado foi o pré-registrado.
- **V1 acima de V0? Contrariada na direção, sem significância.** V1 acertou 95 e V0 104: −2,25 pp. O McNemar exploratório dá b = 16, c = 25, p = 0,211. Cinco exemplos aleatórios do treino não ajudaram o LLM. Na amostra, a tendência é o contrário, mas não dá para distinguir de zero.
  - Isso não responde a Q1, que depende de V3 × V1 (F3).
  - Ressalva: V1 muda duas coisas ao mesmo tempo em relação a V0: exemplos aleatórios no lugar de 1 por categoria, e 5 no lugar de 8.
- **Superprevisão de `Access`: repetiu.** V0 previu Access 159 vezes, V1 161 e o case 160, contra 49 tickets que são Access de fato. Os exemplos aleatórios não corrigiram a convenção de rótulos.
- **K1 perto de C? Não.** K1 acertou 54,75% e C 69,50%: −14,75 pp, com McNemar exploratório p = 1,05e-06.
  - **Expectativa contrariada:** K1, sem LLM, ficou **muito acima** de V0 e V1 (+28,75 pp sobre V0). O voto dos vizinhos carrega a convenção de rótulos que o LLM sozinho não tem. Isso apoia a premissa da F0 de que "os vizinhos carregam a convenção". A hipótese de que "K1 empata com V3" só é testável na F3.
  - K1 superprevê HR Support (133 contra 83 reais).
- **C ≥ V3:** não testável nesta fase.

## 4. Desvios da spec

- **`count_tokens`:** foi chamado pelo `ChatAnthropic.get_num_tokens_from_messages`, que usa o endpoint de contagem da API, sem geração. O valor contado para o id 44115 (1.337) difere em +1 do faturado no case (1.336), mas os tokens faturados nesta rodada bateram exatamente com o case. A estimativa usa o valor contado.
- **Arquivos intermediários além dos pedidos:** `results/f2/pred_v0.csv`, `pred_v1.csv`, `pred_k1_c.csv`, `llm_meta_v0.json`, `llm_meta_v1.json` e `vizinhos_meta.json`. Todos são só ids, categorias e números. O SHA-256 do system vai para o `llm_meta_v0.json` e é copiado para o `metricas_f2.json`.
- **p do McNemar gravado sem arredondamento** no JSON: com 6 casas, os p de K1 × C e V1 × C viravam 0.
- **`wilson()` limitado a [0, 1]:** evita um −0,0 de ponto flutuante em k = 0. Os valores do teste batem com 4 casas.
- **`test_exemplos_v1`:** confere a reprodução do sorteio em 20 dos 400 tickets, e não em todos. A contagem, a ausência de holdout e a ausência do próprio ticket são conferidas nos 400.
- **Paridade de `validar`:** foi testada em 17 casos, além dos pedidos: espaços nas pontas, lista JSON, chave `categoria` ausente e JSON sem `}`.
- **Report e commit:** o report foi escrito antes do commit e entrou nele, como na F1.

## 5. Erros e correções durante a execução

- O `f2_metricas.py` arredondava o p do McNemar para 6 casas, o que gravava 0 em duas comparações. Corrigi para gravar o p sem arredondar e rodei o script de novo. Não há chamada de API nesse script.
- Nenhum erro de API, nenhuma saída inválida e nenhuma repetição nas 800 chamadas.
- **Correção posterior (commit da F3):** a §8 dizia "19:57 → ~20:20, ~23 min", um fim estimado. O fim real é
  20:16, horário do commit `dca94e9`, então a fase levou ~19 min. O início, 19:57, foi informado pelo Gustavo.

## 6. Custo de API

| | Estimado | Real |
|---|---|---|
| V0 | US$ 0,0706 | US$ 0,060123 |
| V1 | US$ 0,0533 | US$ 0,043256 |
| **F2** | **US$ 0,1239** | **US$ 0,103379** |
| **Acumulado do projeto** | | **US$ 0,103379** de US$ 3 |

Fonte: `docs/custos.md`, preço oficial de 2026-11-17 (US$ 0,10 / US$ 0,50 por MTok, igual ao do case). O teste `api` de fumaça não foi executado.

## 7. Pendências e decisões que dependem do Gustavo

1. **K1 muito acima do LLM:** K1 acertou 54,75%, contra 26,00% do V0 e 23,75% do V1. Na F3, V3 × K1 vai dizer se o LLM com vizinhos agrega ou só copia (hipótese F0: empate). Nada foi ajustado por causa disso.
2. **Reaproveitamento na F3:** os vizinhos dos 400 estão em `results/f2/vizinhos_400.csv` (top 50 de cada recuperador). V2 pode usar o top 5 vetorial dele e V3 o `hibrida_top5_400.csv`, sem refazer buscas.
3. **Risco de tempo de Q2 no holdout inteiro:** continua o mesmo da F1 §7 (~4,6 h em sequência). Com 4 conexões, os 400 levaram 539 s (~1,35 s por ticket para vetorial + full-text). O paralelismo rendeu pouco.
4. **V1 confunde duas mudanças:** aleatório em vez de estratificado, e 5 em vez de 8 exemplos. A comparação primária pré-registrada é V3 × V1, então isso não muda o plano. Fica registrado.

## 8. Tempo gasto × orçado

- 19:57 → 20:16 (horário do commit `dca94e9`), ~19 min de 60 orçados.
- Desse tempo, ~9 min foram as buscas de vizinhos (em espera) e ~2 min as duas rodadas de LLM.
