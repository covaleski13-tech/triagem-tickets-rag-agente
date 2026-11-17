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
