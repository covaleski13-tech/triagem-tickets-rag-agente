# Custos de API

Teto total: **US$ 3** (`CLAUDE.md` §3).

## Preço

| Consulta | URL | Modelo | Entrada | Saída |
|---|---|---|---|---|
| 2026-11-17 | https://platform.claude.com/docs/en/about-claude/pricing.md | `claude-haiku-5-5` (prompts de até 100.000 tokens) | US$ 0,10 / MTok | US$ 0,50 / MTok |

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
