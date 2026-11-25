# Custos de API

Teto total: **US$ 3** (`CLAUDE.md` §3).

## Preço

| Consulta | URL | Modelo | Entrada | Saída |
|---|---|---|---|---|
| 2026-11-17 | https://platform.claude.com/docs/en/about-claude/pricing.md | `claude-haiku-5-5` (prompts de até 100.000 tokens) | US$ 0,10 / MTok | US$ 0,50 / MTok |
| 2026-11-25 (F7) | https://platform.claude.com/docs/en/about-claude/pricing.md | `claude-haiku-5-5` (prompts de até 100.000 tokens) | US$ 0,10 / MTok | US$ 0,50 / MTok |

- Igual ao preço usado no case (US$ 0,10 / US$ 0,50, consultado em 2026-11-03): sem divergência.
- A página também lista US$ 0,50 / US$ 2,50 para prompts acima de 100.000 tokens. Nenhuma chamada deste projeto
  chega perto disso (prompts de ~1.000 a ~1.500 tokens).
- Não há cache de prompt nas chamadas (sem `cache_control`), então só as colunas de entrada e saída se aplicam.

## F2 — estimativa (antes das chamadas)

Fonte: `python scripts/f2_llm.py --variante v0|v1 --estimar` (`count_tokens` via
`ChatAnthropic.get_num_tokens_from_messages`, nos 5 primeiros ids de `data/amostra_400_ids.csv`).

| Variante | Tokens de entrada (5 tickets) | Média | Premissa de saída | Chamadas | Estimativa |
|---|---|---|---|---|---|
| V0 | 1.337, 1.353, 1.454, 1.318, 1.339 | 1.360,2 | 64 (= `max_tokens`, teto) | 400 × 1,05 = 420 | US$ 0,0706 |
| V1 | 772, 803, 873, 842, 1.461 | 950,2 | 64 (= `max_tokens`, teto) | 420 | US$ 0,0533 |
| **Total F2** | | | | 840 | **US$ 0,1239** |

- Fórmula: `chamadas × (média_entrada × 0,10 + 64 × 0,50) / 1e6`. A saída usa o teto de 64 tokens, por isso a
  estimativa é conservadora (o case mediu ~24 tokens de saída por chamada).
- Acumulado antes da F2: US$ 0. Acumulado + estimativa: US$ 0,1239 < US$ 3. Pode rodar.

## F2 — custo real

Fonte: tokens de `usage_metadata` somados em `results/f2/llm_log_v0.jsonl` e `llm_log_v1.jsonl`, e
`scripts/f2_metricas.py` → `results/f2/metricas_f2.json`.

| Variante | Chamadas | Tokens de entrada | Tokens de saída | Custo real | Por 1.000 tickets |
|---|---|---|---|---|---|
| V0 | 400 | 553.381 | 9.569 | US$ 0,060123 | US$ 0,1503 |
| V1 | 400 | 384.873 | 9.537 | US$ 0,043256 | US$ 0,1081 |
| **Total F2** | 800 | 938.254 | 19.106 | **US$ 0,103379** | |

- Estimativa: US$ 0,1239. O real ficou abaixo porque a saída média foi ~24 tokens, e não o teto de 64 usado na
  estimativa, e não houve repetição (1,0 chamada por ticket).
- O teste `@pytest.mark.api` (`test_fumaca_api`) não foi executado.
- **Acumulado do projeto: US$ 0,103379** de US$ 3.

## F3 — teste de fumaça (`pytest -m api`, 2026-11-17)

- Resultado: 1 passed (`tests/test_f2.py::test_fumaca_api`), 1 chamada.
- Os tokens não foram registrados pelo teste. Para não repetir a chamada, calculei o teto: entrada de 48 tokens
  (`count_tokens` do mesmo system e da mesma mensagem) + saída de até 64 tokens (`max_tokens`) =
  **≤ US$ 0,0000368**. Esse teto entra no acumulado.

## F3 — estimativa (antes das chamadas)

Fonte: `python scripts/f2_llm.py --variante v2|v3 --estimar` (`count_tokens` nos 5 primeiros ids). Mesmo preço e
mesma fórmula da F2.

| Variante | Tokens de entrada (5 tickets) | Média | Chamadas | Estimativa |
|---|---|---|---|---|
| V2 | 739, 858, 1.152, 585, 1.107 | 888,2 | 420 | US$ 0,0507 |
| V3 | 692, 680, 1.094, 528, 776 | 754,0 | 420 | US$ 0,0451 |
| **Total F3** | | | 840 | **US$ 0,0958** |

- Acumulado antes da F3: US$ 0,103379 + ≤ US$ 0,0000368 (fumaça) = US$ 0,1034. Somado à estimativa, dá
  US$ 0,1992 < US$ 3. Pode rodar.

## F3 — custo real

Fonte: tokens de `results/f3/llm_log_v2.jsonl` e `llm_log_v3.jsonl` (`scripts/f3_familia.py` → `results/f3/metricas_f3.json`).

| Variante | Chamadas | Tokens de entrada | Tokens de saída | Custo real |
|---|---|---|---|---|
| V2 | 400 | 391.969 | 9.579 | US$ 0,043986 |
| V3 | 400 | 306.495 | 9.615 | US$ 0,035457 |
| Fumaça (teto) | 1 | 48 | ≤ 64 | ≤ US$ 0,0000368 |
| **Total F3** | 801 | | | **≤ US$ 0,079480** |

- **Acumulado do projeto: ≤ US$ 0,182859** de US$ 3 (F2 US$ 0,103379 + F3 ≤ US$ 0,079480).

## F4 — fumaça do agente: estimativa (antes da chamada)

Fonte: `count_tokens` (`ChatAnthropic.get_num_tokens_from_messages`, com as 2 tools) da 1ª rodada dos 5 tickets
do treino escolhidos (seed 42, fora de "IA decide"; ids 18556, 22958, 34269, 9983, 35859): 921, 911, 954, 900, 931.

- Teto por ticket: 4 chamadas (3 rodadas + 1 nova tentativa de JSON) com entrada ≤ 930 + 3 × 2.100 (premissa:
  ~1.200 tokens a mais quando os 5 exemplos entram na conversa) = 7.230 tokens, e saída ≤ 4 × 256 = 1.024 tokens
  → ≤ US$ 0,00124. Com 1 nova tentativa por erro de API em cada chamada (×2): ≤ US$ 0,00247.
- 5 tickets: **≤ US$ 0,0124** (teto).
- Acumulado antes: ≤ US$ 0,182859. Acumulado + estimativa ≤ US$ 0,1953 < US$ 3. Pode rodar.

## F4 — fumaça do agente: custo real

Fonte: tokens de `results/f4/agente_log.jsonl` (5 linhas, `tests/test_f4.py::test_fumaca_agente`, 1 execução).

| Tickets | Tokens de entrada | Tokens de saída | Custo real |
|---|---|---|---|
| 5 | 9.172 | 433 | **US$ 0,001134** |

- **Acumulado do projeto: ≤ US$ 0,183993** de US$ 3.
- **2ª execução, não planejada (erro):** o `pytest -m db` do fechamento também selecionou o `test_fumaca_agente`,
  que tinha os marcadores `api` e `db`. O `-m db` substitui o filtro padrão `not api`. Custo real, pelos tokens do
  `results/f4/agente_log.jsonl` dessa execução, que sobrescreveu o da 1ª: 9.713 de entrada e 509 de saída =
  **US$ 0,001226**. O marcador `db` foi retirado do teste de fumaça.
- **Acumulado do projeto, corrigido: ≤ US$ 0,185219** de US$ 3.

## F4 — emenda de diagnóstico (JSON inválido): estimativa

Mesmos 5 tickets do treino da fumaça (ids 18556, 22958, 34269, 9983, 35859), mesmo agente, 1 execução. Mesmo teto
da fumaça (mesma conta): **≤ US$ 0,0124**. As duas fumaças reais custaram US$ 0,001134 e US$ 0,001226.
Acumulado antes: ≤ US$ 0,185219; acumulado + estimativa ≤ US$ 0,1976 < US$ 3.

## F4 — emenda de diagnóstico: custo real

Fonte: tokens de `results/f4/diagnostico_json.jsonl` (`python scripts/f4_diagnostico_json.py`, 1 execução,
11 chamadas): 12.433 de entrada e 571 de saída = **US$ 0,001529**.

- **Acumulado do projeto: ≤ US$ 0,186748** de US$ 3.

## F4 — emenda `responder`: fumaça, estimativa (antes da chamada)

Mesmos 5 tickets do treino, 1 execução. A conta do teto não muda: até 4 chamadas por ticket (3 rodadas + 1 nova
tentativa de `responder`), entrada ≤ 7.230 tokens e saída ≤ 1.024 por ticket, ×2 por erro de API: **≤ US$ 0,0124**.
Acumulado antes: ≤ US$ 0,186748; acumulado + estimativa ≤ US$ 0,1991 < US$ 3.

## F4 — emenda `responder`: fumaça, custo real

Fonte: tokens de `results/f4/emenda_agente_log.jsonl` / `emenda_fumaca_resumo.json` (1 execução,
`pytest -m api -k fumaca_agente`): 7.971 de entrada e 434 de saída = **US$ 0,001014**.

- **Acumulado do projeto: ≤ US$ 0,187762** de US$ 3.

## F4 — emenda 2 (uma tool por rodada): fumaça, estimativa (antes da chamada)

Mesmos 5 tickets do treino, 1 execução. A conta do teto não muda: até 4 chamadas por ticket (3 rodadas + 1 nova
tentativa), entrada ≤ 7.230 tokens e saída ≤ 1.024 por ticket, ×2 por erro de API: **≤ US$ 0,0124**.
Acumulado antes: ≤ US$ 0,187762; acumulado + estimativa ≤ US$ 0,2002 < US$ 3.

## F4 — emenda 2: fumaça, custo real

Fonte: tokens de `results/f4/emenda2_fumaca_resumo.json` / `emenda2_agente_log.jsonl` (1 execução,
`pytest -m api -k fumaca_agente`): 11.284 de entrada e 379 de saída = **US$ 0,001318**.

- **Acumulado do projeto: ≤ US$ 0,189080** de US$ 3.

## F5 — avaliação do agente: estimativa (antes das chamadas)

Fonte da taxa por execução: fumaça da emenda 2 da F4 (`results/f4/emenda2_fumaca_resumo.json`): 11.284 de entrada e
379 de saída em 5 execuções com LLM → 2.257 e 76 por execução → US$ 0,0002635 por execução com LLM.

- Execuções com LLM (teto): estratos "IA sugere" (67) e "humano decide" (66) × 6 variantes = 798; "IA decide" atacado
  que sai da faixa ≤ 67 × 5 = 335 (os limpos de "IA decide" não chamam o LLM); golden ≤ 5; falhas injetadas com
  tool = 20 (as 10 de timeout não geram tokens faturados). Total ≤ 1.158.
- 1.158 × US$ 0,0002635 = US$ 0,305. Com folga de 1,5× (mais rodadas, novas tentativas, texto atacado maior):
  **≤ US$ 0,46**.
- Acumulado antes: ≤ US$ 0,189080. Acumulado + estimativa ≤ US$ 0,649 < US$ 3. Pode rodar.

## F5 — avaliação do agente: custo real

Fonte: tokens somados de `results/f5/agente_log.jsonl` (1.200 execuções), `golden.jsonl` (11) e
`falhas_injetadas.csv` (30), por `scripts/f5_metricas.py` → `results/f5/q3.json` (`custo_latencia`):
2.425.030 de entrada e 67.209 de saída = **US$ 0,276108** (estimativa: ≤ US$ 0,46).

- **Acumulado do projeto: ≤ US$ 0,465188** de US$ 3.

## Total final do projeto (F6)

Soma conferida por `python scripts/f6_somar_custos.py`, que procura cada parcela de custo real neste arquivo e compara
o total com o último acumulado registrado. Preço: US$ 0,10 / US$ 0,50 por MTok (Haiku 5.5, prompts de até 100.000
tokens), https://platform.claude.com/docs/en/about-claude/pricing.md, consultado em 2026-11-17.

| Fase | Custo real |
|---|---|
| F1 | US$ 0 (sem API) |
| F2 (V0, V1) | US$ 0,103379 |
| F3 (V2, V3, teste de fumaça com teto de US$ 0,0000368) | ≤ US$ 0,079480 |
| F4 (2 fumaças, diagnóstico, emendas 1 e 2) | US$ 0,006221 |
| F5 (avaliação do agente) | US$ 0,276108 |
| F6 | US$ 0 (sem API) |
| **Total** | **≤ US$ 0,465188** de US$ 3 |

## F6, correção pós-revisão — falhas injetadas em "IA sugere": estimativa (antes das chamadas)

30 execuções (10 tickets × 3 falhas); o LLM roda nas 20 de tool (as 10 de timeout não geram tokens faturados).
Custo médio por execução com LLM na F5: US$ 0,276108 / 826 = US$ 0,000334 (`results/f5/q3.json`).
20 × US$ 0,000334 = US$ 0,0067; com folga de 1,5×: **≤ US$ 0,010**.
Acumulado antes: ≤ US$ 0,465188; acumulado + estimativa ≤ US$ 0,4752 < US$ 3.

## F6, correção pós-revisão — falhas injetadas em "IA sugere": custo real

Fonte: tokens de `results/f5/falhas_injetadas_ia_sugere.csv` (30 execuções, 1 rodada), por `scripts/f5_metricas.py`
→ `results/f5/veredicto_q3.json` (`veredicto_com_complemento`): 34.602 de entrada e 1.110 de saída =
**US$ 0,004015** (estimativa: ≤ US$ 0,010).

- **Acumulado do projeto: ≤ US$ 0,469203** de US$ 3.

## F7, passo 0 — fumaça ADK: estimativa (antes da chamada)

1 execução real (1 ticket do treino, `Workflow` ADK com nó `Agent` + `LiteLlm`), até 3 rodadas.
Custo médio por execução com LLM na F5: US$ 0,000334 (`results/f5/q3.json`); com folga de 3×: **≤ US$ 0,001**.
Teto da F7: US$ 1. Acumulado antes: ≤ US$ 0,469203; acumulado + estimativa ≤ US$ 0,4702 < US$ 3.

## F7, passo 0 — fumaça ADK: custo real

Fonte: `usage_metadata` dos eventos do ADK (tokens da Anthropic repassados pelo LiteLLM), 1 execução, 2 respostas do
modelo: 3.066 de entrada e 84 de saída = **US$ 0,000349** (estimativa: ≤ US$ 0,001).

- **Acumulado da F7: US$ 0,000349** de US$ 1 (F1–F6 ≤ US$ 0,469203 + F7 = ≤ US$ 0,469552 de US$ 3; o acumulado do
  projeto entra só no fechamento da F7, adendo da spec).

## F7 — avaliação LangGraph × ADK: estimativa (antes das chamadas)

Execuções com LLM previstas: 804 da avaliação principal (67 tickets "IA sugere" × 6 variantes × 2 implementações),
6 de aquecimento (3 tickets do treino × 2), até 20 do golden (10 casos × 2; os que param na política não chamam o
LLM) e 10 de falha em `recuperar_exemplos` no ADK (1 rodada cada; as 10 de timeout não chegam a ser faturadas).
Custo médio por execução com LLM na F5: US$ 0,000334 (`results/f5/q3.json`, premissa).
840 × US$ 0,000334 = US$ 0,281; com folga de 1,5×: **≤ US$ 0,42**.

- F7: acumulado US$ 0,000349 + estimativa ≤ US$ 0,42 = ≤ US$ 0,421 < US$ 1 (teto da fase).
- Projeto: ≤ US$ 0,469203 (F1–F6) + ≤ US$ 0,421 = ≤ US$ 0,890 < US$ 3.

## F7 — avaliação LangGraph × ADK: custo real até a interrupção

A avaliação foi interrompida em 146 de 804 execuções (erros de TLS só no lado ADK; F7-report). Parcelas:

| Rodada | Fonte | Custo |
|---|---|---|
| Aquecimento da 1ª tentativa (abortada no aquecimento) | tokens impressos pelo script: 8.720 de entrada, 250 de saída | US$ 0,000997 |
| Aquecimento avulso (`--so-aquecimento`) | 11.886 / 334 | US$ 0,001356 |
| Aquecimento da 2ª tentativa | 11.886 / 334 | US$ 0,001356 |
| 146 execuções da avaliação (73 por implementação) | `results/f7/execucoes.jsonl`: LangGraph 193.509 / 5.671; ADK 127.149 / 3.595 | US$ 0,036698 |
| Diagnóstico sem contagem de tokens (6 execuções com LLM) | teto: 6 × US$ 0,000622 (maior custo por execução no log) | ≤ US$ 0,003732 |

- **Acumulado da F7: ≤ US$ 0,044488** de US$ 1 (fumaça US$ 0,000349 + parcelas acima). F1–F6 ≤ US$ 0,469203 + F7 =
  ≤ US$ 0,513691 de US$ 3; o acumulado do projeto entra só no fechamento da F7.

## F7 — avaliação refeita do zero (opção a do Gustavo): estimativa (antes das chamadas)

Mesmas execuções da estimativa anterior (≈ 840 com LLM, US$ 0,000334 cada, premissa da F5): **≤ US$ 0,42**.
F7: ≤ US$ 0,044488 + ≤ US$ 0,42 = ≤ US$ 0,465 < US$ 1. Projeto: ≤ US$ 0,469203 + ≤ US$ 0,465 = ≤ US$ 0,934 < US$ 3.

## F7 — avaliação refeita do zero: custo real

Fonte: tokens de `results/f7/execucoes.jsonl`, `results/f7/golden.jsonl` e `results/f7/falhas_injetadas_adk.csv`
(`scripts/f7_metricas.py` → `results/f7/q4.json`, `custo`) e do aquecimento (`results/f7/tempos.json`).

| Rodada | Tokens (entrada / saída) | Custo |
|---|---|---|
| LangGraph: 402 execuções + golden | 1.055.101 / 31.237 | US$ 0,121129 |
| ADK: 402 execuções + golden | 1.077.948 / 31.343 | US$ 0,123466 |
| Falhas injetadas no ADK (20) | 12.933 / 374 | US$ 0,001480 |
| Aquecimento (3 + 3) | 11.886 / 334 | US$ 0,001356 |
| **Avaliação final** | | **US$ 0,247431** (estimativa: ≤ US$ 0,42) |

## F7 — fechamento

| Parcela da F7 | Custo |
|---|---|
| Fumaça do passo 0 | US$ 0,000349 |
| Rodada interrompida pelo Kaspersky, aquecimentos avulsos e diagnóstico | ≤ US$ 0,044139 |
| Avaliação final | US$ 0,247431 |
| **Total da F7** | **≤ US$ 0,291919** de US$ 1 |

- **Acumulado do projeto: ≤ US$ 0,761122** de US$ 3.
