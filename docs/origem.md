# Origem dos artefatos reaproveitados do case

Case: PR #228 (https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228), commit `3a880f2`.
Gerado por `python scripts/f1_copiar_origem.py`. A âncora de proveniência é o blob git do arquivo em `3a880f2` (`git rev-parse 3a880f2:<caminho>` no fork); o SHA-256 da origem é calculado sobre o conteúdo do blob (`git show 3a880f2:<caminho>`), não sobre o checkout em disco. Nos `.py`, a coluna "destino sem cabeçalho" remove as 2 linhas de origem adicionadas e deve ser igual ao SHA-256 da origem.

| Origem (fork, `3a880f2`) | Destino | blob git (3a880f2) | SHA-256 origem (blob) | SHA-256 destino | SHA-256 destino sem cabeçalho |
|---|---|---|---|---|---|
| `submissions/gustavo-covaleski/solution/triagem.py` | `src/triagem_rag/caso/triagem.py` | `67e060347e2e9c2e7cb102652a16b4010498a263` | `477e491af04e97ce884a287bb918af778fdfebacd9ea616bf4c71d7a4238b549` | `5b9a02a3507eb9add87fc8ab10cb28d8f81ee6e97798aec6ee34611275a61492` | `477e491af04e97ce884a287bb918af778fdfebacd9ea616bf4c71d7a4238b549` |
| `submissions/gustavo-covaleski/solution/comum.py` | `src/triagem_rag/caso/comum.py` | `797c78f2ee5425df92e32687c4fb9d45e64ef40d` | `9351694e735d1081d9e0fb8a599a8312c4d8b4ada21f87aa0b407a79253114e6` | `0413fe54b759fe2a12ca09f8d0bd16ac45cb2afe84af20846c0a1d8e7da24aee` | `9351694e735d1081d9e0fb8a599a8312c4d8b4ada21f87aa0b407a79253114e6` |
| `submissions/gustavo-covaleski/solution/prompts/classificar_v1.txt` | `prompts/classificar_v1.txt` | `fd4b1d2044b5def7364be6f90299e9f1b05132b7` | `62e285f13850d8a56f9812ec6416395a5abde12e651c47a614dc7541e3fb2dea` | `62e285f13850d8a56f9812ec6416395a5abde12e651c47a614dc7541e3fb2dea` | — |
| `submissions/gustavo-covaleski/solution/tests/golden/golden_v1.jsonl` | `tests/golden/golden_v1.jsonl` | `6836e8b30c45bea2ea40b822be6d1a2d67761fca` | `ac9b67e6741a7912c9777976aad57bc1a60a98184d1ba66781ed7f8a971a4bc1` | `ac9b67e6741a7912c9777976aad57bc1a60a98184d1ba66781ed7f8a971a4bc1` | — |
| `submissions/gustavo-covaleski/solution/tests/golden/ataques_v1.json` | `tests/golden/ataques_v1.json` | `d09e5c6ef7e5180129526d91d421fbd3faecc12a` | `2d765b4941f0e6cb081698e64b2db0d62cc73c81acee5edbba99899a104aed55` | `2d765b4941f0e6cb081698e64b2db0d62cc73c81acee5edbba99899a104aed55` | — |
| `submissions/gustavo-covaleski/solution/outputs/f1_splits.csv` | `data/f1_splits.csv` | `19d8741e4703447bb1ef6f0ed579d4d921d4207b` | `ce0a3194448fb19c51540d40ac55cdc866113251bd585f98f9f0614feaa87de8` | `ce0a3194448fb19c51540d40ac55cdc866113251bd585f98f9f0614feaa87de8` | — |
| `submissions/gustavo-covaleski/solution/outputs/f3_probs_holdout_grupo.csv` | `data/caso/f3_probs_holdout_grupo.csv` | `e2698db038a5e2758c74b76c562c68bd474033ef` | `d5b940bfd415b59bfd93cf003b236b81e39dedadc23abb17b01a6c7bd35776ad` | `d5b940bfd415b59bfd93cf003b236b81e39dedadc23abb17b01a6c7bd35776ad` | — |
| `submissions/gustavo-covaleski/solution/outputs/f8_politica_por_categoria.csv` | `data/caso/f8_politica_por_categoria.csv` | `8cb19dff96cde05633bb8e4e62d77e365c018571` | `4f657689e8fccb776c8898cf432534b1f01f93396e8567b65c2b7bd4e58130c5` | `4f657689e8fccb776c8898cf432534b1f01f93396e8567b65c2b7bd4e58130c5` | — |
| `submissions/gustavo-covaleski/solution/outputs/f8_faixas.json` | `data/caso/f8_faixas.json` | `1491b141c9e9b43182e788f2e7bc27737b08e6af` | `93a137df7a4afdedfc77e1aa336008d478977b06f4ec0e634c2b85b418d42562` | `93a137df7a4afdedfc77e1aa336008d478977b06f4ec0e634c2b85b418d42562` | — |
| `data/all_tickets_processed_improved_v3.csv` (fora do fork) | `data/raw/all_tickets_processed_improved_v3.csv` | — | `044fdace33fa564e1e60453f2941dafc95539c99878b0d32746950394b9dd4d4` (arquivo em disco) | `044fdace33fa564e1e60453f2941dafc95539c99878b0d32746950394b9dd4d4` | — |

`data/raw/` fica fora do git; o SHA-256 do CSV bruto do DS2 é o do arquivo em disco.
`planning/F3/f3_llm_log.jsonl` (fora do fork) não é copiado: dele derivam `data/amostra_400_ids.csv` e `data/caso/f3_v0_pred.csv` (`python scripts/f1_amostra.py`).
