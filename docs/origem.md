# Origem dos artefatos reaproveitados do case

Case: PR #228 (https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228), commit `3a880f2`.
Gerado por `python scripts/f1_copiar_origem.py`. Nos `.py`, a coluna "destino sem cabeçalho" remove as 2 linhas de origem adicionadas e deve ser igual ao SHA-256 da origem.

| Origem | Destino | SHA-256 origem | SHA-256 destino | SHA-256 destino sem cabeçalho |
|---|---|---|---|---|
| `ai-master-challenge/submissions/gustavo-covaleski/solution/triagem.py` | `src/triagem_rag/caso/triagem.py` | `477e491af04e97ce884a287bb918af778fdfebacd9ea616bf4c71d7a4238b549` | `89287bedd5104da7de5ad2ee9a7982e53ca2f231ece80b59f047df25075aa1bd` | `477e491af04e97ce884a287bb918af778fdfebacd9ea616bf4c71d7a4238b549` |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/comum.py` | `src/triagem_rag/caso/comum.py` | `9351694e735d1081d9e0fb8a599a8312c4d8b4ada21f87aa0b407a79253114e6` | `2137e5c4414b12d80c273716552fe7970ba55c9619c424208bad7ba74a1e9dd1` | `9351694e735d1081d9e0fb8a599a8312c4d8b4ada21f87aa0b407a79253114e6` |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/prompts/classificar_v1.txt` | `prompts/classificar_v1.txt` | `62e285f13850d8a56f9812ec6416395a5abde12e651c47a614dc7541e3fb2dea` | `62e285f13850d8a56f9812ec6416395a5abde12e651c47a614dc7541e3fb2dea` | — |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/tests/golden/golden_v1.jsonl` | `tests/golden/golden_v1.jsonl` | `ac9b67e6741a7912c9777976aad57bc1a60a98184d1ba66781ed7f8a971a4bc1` | `ac9b67e6741a7912c9777976aad57bc1a60a98184d1ba66781ed7f8a971a4bc1` | — |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/tests/golden/ataques_v1.json` | `tests/golden/ataques_v1.json` | `2d765b4941f0e6cb081698e64b2db0d62cc73c81acee5edbba99899a104aed55` | `2d765b4941f0e6cb081698e64b2db0d62cc73c81acee5edbba99899a104aed55` | — |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/outputs/f1_splits.csv` | `data/f1_splits.csv` | `37703450a50c406a9c46fe62fa9ecea167b90fa41c4ee0e106d91a6d72865ba0` | `37703450a50c406a9c46fe62fa9ecea167b90fa41c4ee0e106d91a6d72865ba0` | — |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/outputs/f3_probs_holdout_grupo.csv` | `data/caso/f3_probs_holdout_grupo.csv` | `643c5515e1d5280b54623218084dbed1799142c374bfcb68816940a80139089a` | `643c5515e1d5280b54623218084dbed1799142c374bfcb68816940a80139089a` | — |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/outputs/f8_politica_por_categoria.csv` | `data/caso/f8_politica_por_categoria.csv` | `2286d8760acaaabfff72f54fc2c0e98334485ead7b6f7f24367874eb59ec3cb1` | `2286d8760acaaabfff72f54fc2c0e98334485ead7b6f7f24367874eb59ec3cb1` | — |
| `ai-master-challenge/submissions/gustavo-covaleski/solution/outputs/f8_faixas.json` | `data/caso/f8_faixas.json` | `19fd12f87c75f4825ed1571da18caa73d27152d58b2d79998175d6c026768e3b` | `19fd12f87c75f4825ed1571da18caa73d27152d58b2d79998175d6c026768e3b` | — |
| `data/all_tickets_processed_improved_v3.csv` | `data/raw/all_tickets_processed_improved_v3.csv` | `044fdace33fa564e1e60453f2941dafc95539c99878b0d32746950394b9dd4d4` | `044fdace33fa564e1e60453f2941dafc95539c99878b0d32746950394b9dd4d4` | — |

`data/raw/` fica fora do git; o SHA-256 acima é o do CSV bruto do DS2.
`planning/F3/f3_llm_log.jsonl` não é copiado: dele derivam `data/amostra_400_ids.csv` e `data/caso/f3_v0_pred.csv` (`python scripts/f1_amostra.py`).
