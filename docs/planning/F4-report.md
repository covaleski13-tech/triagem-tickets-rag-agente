# F4 — Report

Status: **concluída.** Agente LangGraph com tool calling real e guarda determinística. A política do case é reusada via
`triar()`, sem alterar `caso/*.py`. Testes passando. A fumaça real rodou, mas **duas vezes**: a 2ª foi um erro meu
(§5). Commit local só com os arquivos da F4, sem push. A F3b continuou rodando: não toquei no Docker nem em
`results/f3/`.

## 1. O que foi feito

1. Registrei D-F3-1 e D-F3-2 em `docs/decisoes.md` e anotei a linha "Agente" da F0 §5. Instalei `langgraph` 1.2.22 e fixei as versões.
2. Criei o adaptador `src/triagem_rag/politica_caso.py`: `sys.path`, `triagem.OUT_DIR = data/caso`, `TRIAGEM_CACHE_DIR`, `TRIAGEM_MODELO_VERSAO` e `TRIAGEM_RUNTIME_DIR=runtime_agente/` (no `.gitignore`).
3. Criei o prompt `prompts/agente_sugerir_v1.txt`, congelado (SHA-256 em `docs/decisoes.md`).
4. Escrevi `src/triagem_rag/agente.py` com:
   - tools `@tool`;
   - grafo `deterministico → [rota] → sugerir → guarda` / `deterministico → guarda`;
   - laço de até 3 rodadas;
   - guarda;
   - log;
   - `triar_agente`.
5. Escrevi `tests/test_f4.py`: 28 testes sem rede (modelo falso do `langchain_core` com `tool_calls` programados, tickets do treino), 1 `db` e 1 `api`.
6. Estimei o custo da fumaça (≤ US$ 0,0124) e rodei a fumaça real com 5 tickets do treino. Depois veio a 2ª execução não planejada (§5).
7. Rodei `pytest` e `pytest -m db`, fiz as checagens e o commit local com `git add` por caminho.

## 2. Resultados

| Item | Valor | Fonte |
|---|---|---|
| `pytest` (sem banco, sem chave) | 66 passed, 10 deselected | `.venv/Scripts/python -m pytest -q` |
| `pytest -m db` (com a F3b rodando) | 8 passed, em 79,4 s | `.venv/Scripts/python -m pytest -q -m db` |
| Testes da F4 sem rede | 28 passed | `tests/test_f4.py` |
| Golden do case via `triar_agente` | 10 casos passam (`portao_qualidade` fica de fora, como a spec manda) | `test_golden_agente` |
| `test_nunca_promove` | 30 tickets do treino, 10 por faixa: nenhuma `faixa_final` acima da `faixa_politica` e nenhum "IA decide" com o LLM rodando | `tests/test_f4.py` |
| `test_falhas` | 9 casos, todos "humano decide", causa no log, ≤ 1 nova tentativa | `tests/test_f4.py` |
| Modelo da F1 via adaptador | 278/400 nos 400; versão `f71cfd480a50` | `test_modelo_f1_no_adaptador` |
| SHA-256 do prompt do agente | `a9201dd9aa2b49271b50de31a11a74dfc469321f38b4a964e8d9a20aed98858e` | `sha256sum prompts/agente_sugerir_v1.txt` |

**Fumaça real.** Não é métrica; a avaliação é a F5. Cinco tickets do treino (seed 42), fora de "IA decide":
ids 18556, 22958, 34269, 9983 e 35859.

| Execução | Faixas (política → final) | LLM rodou | Rodadas | Tools chamadas | JSON inválido | Tokens (entrada / saída) | Custo |
|---|---|---|---|---|---|---|---|
| 1ª (planejada) | 4× humano → humano; 1× IA sugere → IA sugere | 5/5 | 2, 1, 1, 2, 1 | `recuperar_exemplos` em 2 tickets; `consultar_politica` nunca | 1ª tentativa inválida em 2 tickets; 1 escalou ("json inválido" duas vezes) | 9.172 / 433 | US$ 0,001134 |
| 2ª (não planejada, §5) | mesmas faixas | 5/5 | 2, 1, 1, 2, 1 | `recuperar_exemplos` em 2 tickets | 2 tickets escalaram ("json inválido" duas vezes) | 9.713 / 509 | US$ 0,001226 |

- **Fontes:** a 1ª execução vem da saída do console e do `results/f4/fumaca_resumo.json` daquela execução, que foi sobrescrito. A 2ª vem de `results/f4/agente_log.jsonl` e `results/f4/fumaca_resumo.json`, os arquivos atuais.
- **Concordância:** onde o LLM concordou com o clássico em "IA sugere", a faixa ficou em "IA sugere". Nenhuma promoção nas duas execuções.
- **Log:** nenhum trecho de 30 ou mais caracteres de texto do DS2 no log real da 1ª execução (checagem sobre o arquivo daquela execução).

## 3. O que contraria a hipótese ou a expectativa

- **JSON inválido é frequente com tools:** foram 2 de 5 tickets na 1ª tentativa, nas duas execuções. Na F2, sem tools, foram 0 de 800.
  - O log não guarda a resposta bruta: a spec não pede, e ela pode repetir texto. Por isso não sei a forma do erro.
  - Hipótese não verificada: com tools disponíveis, o modelo escreve texto antes do JSON ou responde sem o objeto.
  - O prompt está congelado; não o ajustei. A F5 vai medir a taxa de escalonamento por essa causa.
- **`consultar_politica` não foi chamada** em nenhum dos 10 tickets reais. `recuperar_exemplos` foi chamada em 2 de 5 por execução.
- **Versão do modelo:** a fórmula do case, aplicada ao `data/f1_splits.csv` atual, dá `d2522e1b9442`, e não a versão `f71cfd480a50` do joblib da F1. Na F1, o hash foi calculado sobre a cópia CRLF, antes da correção para LF. O adaptador lê a versão do nome do joblib, e o modelo carregado continua com 278/400. Registrado em `docs/decisoes.md`.
- **O resto bateu com a expectativa:** a guarda nunca promoveu, nem nos testes nem nas fumaças.

## 4. Desvios da spec

- **Versão do modelo:** lida do nome do arquivo `data/modelos/modelo_*.joblib` (deve haver exatamente 1), e não recalculada pela fórmula do case (§3). O joblib já estava no formato do case, então não houve conversão.
- **`motivo_final` no log:** o trecho "termos: ..." do motivo do case (palavras do ticket com os pesos) é substituído por "termos: <omitidos no log>". A spec proíbe texto de ticket no log. O dict devolvido por `triar_agente` mantém o motivo completo para o humano.
- **Argumentos das tools no log:** só a categoria, quando é da lista fechada, e o número de argumentos. Nenhum valor livre vindo do LLM é gravado.
- **Timeout:** `default_request_timeout=30` s no `ChatAnthropic` do agente. A spec não fixava um valor.
- **Erros de API tratados:** `anthropic.APIError` (inclui conexão e timeout), `TimeoutError` e `ConnectionError`. Até 1 nova tentativa por rodada; na 2ª falha, escala como "erro de API" ou "timeout".
- **Resposta final com tool call na nova tentativa de JSON:** conta como JSON inválido.
- **Falha da guarda:** se um assert da guarda falhar, o motivo é "escalado: guarda (<exceção>)". Se o grafo inteiro falhar, `triar_agente` devolve "falha interna do agente".
- **`falha_classificador` no golden:** usa a variável do case `TRIAGEM_MODELO_VERSAO=000000000000`. O case a testava com `monkeypatch` de `classificar`; a spec pede as variáveis de ambiente.
- **Teste do golden:** roda `triar` e `triar_agente` em pastas de runtime separadas, para a idempotência do case não marcar o 2º como duplicado.
- **Testes a mais:** `test_recuperar_real_vetorial` (`db`) e `test_modelo_f1_no_adaptador`.
- **Testes `db` da F3 rodando agora:** com o `vizinhos_q2.csv` parcial da F3b no disco, `test_vetorial_lote_igual_ao_vivo` e `test_hibrida_q2_igual_ao_vivo` deixaram de ser skipped e passaram, nos 3 primeiros ids.

## 5. Erros e correções durante a execução

- **2ª execução da fumaça real, não planejada:**
  - o `test_fumaca_agente` tinha os marcadores `api` e `db`;
  - no fechamento, `pytest -m db` substituiu o filtro padrão `not api` e rodou a fumaça de novo, com chamadas reais;
  - custo: US$ 0,001226. Ela sobrescreveu `results/f4/agente_log.jsonl` e `fumaca_resumo.json`;
  - correção: tirei o marcador `db` da fumaça, que fica só com `api`. Conferi que `pytest -m db --collect-only` não a coleta mais, rodei `pytest -m db` de novo (8 passed, sem API) e registrei o custo em `docs/custos.md`;
  - a spec pedia uma execução; foram duas. Os dados da 1ª ficaram só na saída do console (§2).
- **Buscar falso nos testes:** usava os ids 1 a 5, que não são todos de treino, e a tool falhava. Troquei pelos 5 primeiros ids reais do treino.
- **Fake do modelo:** a 1ª versão de `FakeTools._generate` era ilegível. Simplifiquei antes de rodar os testes.

## 6. Custo de API

| | Estimado | Real |
|---|---|---|
| Fumaça, 1ª execução | ≤ US$ 0,0124 (teto) | US$ 0,001134 |
| Fumaça, 2ª execução (erro) | — | US$ 0,001226 |
| **F4** | | **US$ 0,002360** |
| **Acumulado do projeto** | | **≤ US$ 0,185219** de US$ 3 |

Fonte: `docs/custos.md`, preço oficial de 2026-11-17.

## 7. Pendências e decisões que dependem do Gustavo

1. **JSON inválido com tools:** 2 de 5 na 1ª tentativa. Com a guarda, isso vira escalonamento, que é seguro, mas reduz o que chega como sugestão. Na F5, decidir se:
   - mede só a taxa;
   - ou se o log passa a guardar a resposta bruta da rodada final, truncada e sem texto de ticket, para diagnóstico. Hoje o log não tem campo para isso.
2. **Concorrência do log:** `_registrar` faz append sem lock. A F5, se rodar tickets em paralelo, precisa de um lock (o case usa sqlite) ou de uma execução sequencial.
3. **Fumaça com dados de uma só execução:** o arquivo atual tem os dados da 2ª execução. Se quiser só a 1ª nos artefatos, seria preciso rodar de novo, com custo. Não fiz.

## 8. Tempo gasto × orçado

- **Início:** 22:02:42 (`date` no início da execução).
- **Fim:** 22:18:05 (`date` depois dos testes finais) + escrita deste report e commit (horário no `git log`).
- **Total:** ~16 min com timestamp, de 90 orçados.

---

# Emenda — resposta final pela tool `responder` (`docs/planning/F4-emenda-spec.md`)

Status: **concluída.** O objetivo foi atingido: **0 escalonamento por formato** na fumaça. Há um efeito colateral
novo, registrado na §3 e na §7 desta seção. Commit local, sem push.

## 1. O que foi feito

1. Conferi, com `count_tokens` (sem custo), que a API aceita `tool_choice` `{"type": "any"}` e `{"type": "tool", "name": "responder"}` com `thinking` desligado. Aceitou os dois.
2. Criei `prompts/agente_sugerir_v2.txt` = v1 com uma única troca: o parágrafo do JSON vira "Give your final answer by calling the tool responder…", com a descrição dos argumentos. A v1 fica como histórico.
3. Mudanças no `src/triagem_rag/agente.py`:
   - tool `responder` com o `args_schema` de `esquema.Classificacao` e validação no código (`validar_responder`: exatamente as 2 chaves, tipos estritos);
   - `tool_choice` por rodada: `any`, `any`, `responder`;
   - a resposta final é a chamada a `responder`; o texto livre do modelo é descartado;
   - outras tools na mesma resposta que `responder` ficam como `ignorada`.
   A guarda, o roteamento, as tools de busca e política, o limite de rodadas, a regra de repetição e o contrato não mudaram.
4. Testes atualizados: `test_responder_valido`, `test_responder_invalido` (6 casos), `test_texto_livre_descartado`, `test_rodada3_forca_responder` e `test_payload_agente`. O caso de falha "JSON inválido 2×" virou "sem `responder` 2×".
5. Diagnóstico anterior: `results/f4/diagnostico_json.jsonl` foi para o `.gitignore`. Versionei `scripts/f4_diagnostico_json.py` (com `--resumo`) e `results/f4/diagnostico_resumo.json`, sem texto.
6. Estimei o custo e rodei a fumaça real uma vez (`pytest -m api -k fumaca_agente`, só o marcador `api`), gravando em arquivos próprios da emenda.

## 2. Resultados

| Item | Valor | Fonte |
|---|---|---|
| `pytest` | 75 passed, 10 deselected | `.venv/Scripts/python -m pytest -q` |
| `pytest -m db` | 8 passed | `.venv/Scripts/python -m pytest -q -m db` |
| Testes da F4 sem rede | 37 passed (nunca promove, falhas, contrato e golden incluídos) | `tests/test_f4.py` |
| SHA-256 do prompt v2 | `ffc25ce7d56cd341281c263da7044d597ada86752fb73eb6efbeb4752d079bd8` | `sha256sum prompts/agente_sugerir_v2.txt` |
| Diagnóstico anterior (agente v1) | 11 chamadas, 7 respostas finais, 3 com texto antes do JSON, 1 escalonamento por "json inválido"; `recuperar_exemplos` 3×, `consultar_politica` 1×; US$ 0,001529 | `scripts/f4_diagnostico_json.py --resumo` → `results/f4/diagnostico_resumo.json` |

**Fumaça da emenda.** Mesmos 5 tickets do treino, 1 execução (`results/f4/emenda_fumaca_resumo.json`, `results/f4/emenda_agente_log.jsonl`):

| Ticket (classe do clássico) | Política → final | Rodadas | Tools (destino) | Sugestão do LLM | Escalonamento por formato |
|---|---|---|---|---|---|
| 18556 (Hardware) | humano → humano | 1 | `recuperar_exemplos` (**ignorada**), `responder` | Access | não |
| 22958 (Storage) | humano → humano | 1 | `recuperar_exemplos` (**ignorada**), `responder` | Access | não |
| 34269 (Hardware) | humano → humano | 2 | `recuperar_exemplos` (executada), depois `responder` | Miscellaneous | não |
| 9983 (HR Support) | IA sugere → **humano** | 1 | `recuperar_exemplos` (**ignorada**), `responder` | Access | não |
| 35859 (Administrative rights) | humano → humano | 1 | `responder` | Access | não |

- **Escalonamentos por formato:** **0** de 5. O objetivo da emenda foi atingido.
- **Erros:** nenhum erro de API e nenhum `responder` inválido.
- **Guarda:** nenhuma promoção. Os 5 tickets divergem do clássico e, portanto, ficam em "humano decide".
- **Tokens e custo:** 7.971 de entrada e 434 de saída = US$ 0,001014.

## 3. O que contraria a hipótese ou a expectativa

**A regra "vale `responder`, as outras são ignoradas" anulou a recuperação na maioria dos tickets.**

- Com `tool_choice: any`, o modelo chamou `recuperar_exemplos` e `responder` **na mesma resposta** em 3 dos 5 tickets. Pela regra da emenda, a recuperação foi ignorada, e o LLM respondeu sem ver os exemplos.
- Só em 1 ticket (34269) ele recuperou primeiro e respondeu na rodada seguinte.
- Sem exemplos, 4 das 5 respostas foram "Access", a mesma superprevisão do V0 da F2 (159 de 400).
- Os 5 divergiram do clássico. Isso inclui o ticket 9983: na fumaça original o LLM concordava (HR Support) e o ticket ficava em "IA sugere"; agora cai para "humano decide".

O comportamento é **seguro**, porque a guarda só rebaixa. Mas a sugestão do LLM perde valor, e a F5 mediria um agente que quase nunca usa os exemplos. A emenda resolveu o formato e criou esse efeito de ordem das chamadas. Não mexi no prompt nem na regra; a spec proíbe iterar.

Fora isso: o diagnóstico anterior confirmou a hipótese da emenda. O texto em volta do JSON era uma justificativa ou um anúncio, e o JSON em si estava correto.

## 4. Desvios da spec

- **Resposta sem nenhuma tool call:** tratada como `responder` ausente, com 1 nova tentativa e depois "escalado: responder inválido". Com `tool_choice` `any` ou `tool`, isso não deveria acontecer. A causa no log não distingue "inválido" de "ausente", mas os `erros` dizem "responder inválido ou ausente".
- **Fumaça da emenda em arquivos próprios** (`emenda_agente_log.jsonl`, `emenda_fumaca_resumo.json`): os da fumaça original ficam como histórico.
- **`scripts/f4_diagnostico_json.py`:** o docstring registra que ele rodou com o agente v1. Com o agente atual, não há mais texto bruto na resposta final para gravar.
- **Schema enviado ao modelo para `confianca`:** `anyOf integer/number`, sem limites. A faixa [0, 1] é validada só no código, pelo `Classificacao`.

## 5. Erros e correções durante a execução

- **Indentação:** ao trocar o laço do `no_sugerir`, o bloco das tools ficou com indentação errada. O `py_compile` acusou, e eu corrigi antes de rodar os testes.
- **Heredoc:** a 1ª tentativa de acrescentar esta seção via heredoc no bash falhou no parser, e nada foi gravado. Acrescentei com edição direta.
- **Seleção da fumaça:** para evitar repetir o erro da F4, rodei com `-m api -k fumaca_agente` e conferi antes, com `--collect-only`, que só esse teste seria selecionado. O `-m api` sozinho pegaria também a fumaça da F2.

## 6. Custo de API

| | Estimado | Real |
|---|---|---|
| Diagnóstico do JSON (emenda anterior) | ≤ US$ 0,0124 | US$ 0,001529 |
| Fumaça da emenda `responder` | ≤ US$ 0,0124 | US$ 0,001014 |
| **Acumulado do projeto** | | **≤ US$ 0,187762** de US$ 3 |

Fonte: `docs/custos.md`.

## 7. Pendências e decisões que dependem do Gustavo

1. **Chamadas paralelas `recuperar_exemplos` + `responder` (§3).** Opções:
   - a) manter: é seguro, e a F5 mede o agente assim;
   - b) `disable_parallel_tool_use: true` (compatível com `tool_choice` `any`): o modelo teria de escolher uma tool por rodada;
   - c) trocar a regra para "outra tool junto com `responder` → executa a outra e ignora o `responder` da rodada", o que força recuperar antes de responder;
   - d) `tool_choice` `{"type": "tool", "name": "recuperar_exemplos"}` na rodada 1.
   - b, c e d mudam a emenda congelada. Exigem decisão e uma nova fumaça no treino antes da F5.
2. **`consultar_politica`:** foi chamada só 1 vez em 3 execuções reais.

## 8. Tempo gasto × orçado

- **Início:** 22:30:11 (`date` no início).
- **Fim:** 22:34:54 (`date` depois dos testes finais) + este report e o commit (horário no `git log`).
- **Total:** ~5 min com timestamp, de 30 orçados.
