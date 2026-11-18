# F4 — Emenda: resposta final por tool (`responder`)

**Pré-requisito:** diagnóstico da F4 concluído (`scripts/f4_diagnostico_json.py`, 2026-11-17).
**Orçamento:** 30 min. Ao passar de 120% (36 min), pare e reporte.
**Hora de início:** anote o relógio ao começar.

## Motivo

- Na fumaça e no diagnóstico (5 tickets do **treino**), o LLM com tools escreveu uma frase de justificativa antes do JSON em 3 de 7 respostas finais.
- A validação estrita herdada do case rejeita isso. Um ticket escalou por esse motivo nas duas tentativas.
- O JSON em si estava sempre correto: o defeito é de formato, não de conteúdo.
- Sem a correção, a Q3 na F5 mediria escalonamentos por formato, não a segurança da guarda.
- **Leitura tolerante do JSON foi rejeitada:**
  - abriria espaço para pegar um JSON citado pelo ataque `json_pronto`;
  - afastaria a validação da usada na F2.

A evidência vem só de tickets do treino. O holdout não foi tocado. A mudança fica congelada antes da F5.

## Mudança

1. **Nova tool `responder(categoria, confianca)`:**
   - schema Pydantic igual a `esquema.Classificacao`: `categoria` como `Literal` das 8 categorias, `confianca` como int ou float estrito entre 0 e 1, sem bool;
   - argumentos validados no código, não só pelo schema enviado ao modelo;
   - argumento inválido → 1 nova tentativa da rodada → falha → "humano decide".
2. **`tool_choice`:**
   - rodadas 1 e 2: `{"type": "any"}`, ou seja, o modelo tem de chamar uma das três tools (`recuperar_exemplos`, `consultar_politica`, `responder`);
   - rodada 3: `{"type": "tool", "name": "responder"}`.
   - Se a versão instalada não aceitar esses valores com `thinking` desligado, **pare e reporte**.
3. **Resposta final = a chamada a `responder`:**
   - texto livre do modelo, se houver, é **descartado**: não é validado, não é logado, não entra no estado;
   - chamada a `responder` junto com outra tool na mesma rodada: vale a chamada a `responder`, e as outras são ignoradas e registradas como `ignorada`.
4. **Prompt `prompts/agente_sugerir_v2.txt`:**
   - cópia da v1 com só duas mudanças: a descrição da tool `responder` e "dê a resposta final chamando `responder`", no lugar do parágrafo do JSON;
   - a v1 fica no repositório como histórico;
   - registre o SHA-256 da v2 em `docs/decisoes.md`.
5. **Guarda, roteamento, `recuperar_exemplos` (vetorial, sem parâmetros), `consultar_politica`, limite de 3 rodadas, regra de repetição e contrato sem exceção: sem mudança.**
6. **Log:**
   - continua sem texto de ticket e passa a não ter nenhum texto livre do LLM;
   - da chamada a `responder`, grava só `categoria` e `confianca`.

## Diagnóstico da emenda anterior

- `results/f4/diagnostico_json.jsonl` contém frases do LLM com fragmentos curtos de tickets do treino, como "port-opening" e "site folder". A checagem de trechos de 30 caracteres não pega isso.
- Tire esse arquivo do git: acrescente ao `.gitignore` e não o commite.
- Versione `scripts/f4_diagnostico_json.py` e um resumo sem texto em `results/f4/diagnostico_resumo.json`, com:
  - número de chamadas;
  - respostas finais;
  - quantas tinham texto antes do JSON;
  - escalonamentos;
  - tools chamadas;
  - custo.

## Testes

Atualize `tests/test_f4.py` com o LLM falso:

- `test_responder_valido` e `test_responder_invalido`. Casos inválidos:
  - categoria fora da lista;
  - `confianca` igual a `true`, `1.5` ou `"0.9"`;
  - argumento extra;
  - argumento faltando.
  Todos levam a 1 nova tentativa e depois "humano decide".
- `test_texto_livre_descartado`: um `AIMessage` com texto e chamada a `responder` → vale a chamada; o texto não aparece no log nem no estado.
- `test_rodada3_forca_responder`: o payload da 3ª rodada tem `tool_choice` `{"type": "tool", "name": "responder"}`.
- `test_payload_agente`: as três tools declaradas, `tool_choice` `any` nas rodadas 1 e 2, `max_tokens=256`, `thinking` e `output_config` iguais à F2, sem `temperature`.
- Os testes de "nunca promove", das falhas, do contrato e do golden continuam passando.

## Fumaça real (`@pytest.mark.api`, só esse marcador)

- Estime o custo antes e registre em `docs/custos.md`.
- Rode **uma vez**, nos mesmos 5 tickets do treino.
- Registre:
  - escalonamentos por formato (esperado 0, que é o objetivo da emenda);
  - tools chamadas;
  - rodadas;
  - custo real.
- **Se ainda houver escalonamento por formato, pare e reporte.** Não mexa de novo no prompt.

## Fechamento

- Rode `pytest`, `pytest -m db`, `git diff --cached` (sem `.env`, `data/raw/`, `*.joblib`, `sk-ant`, `diagnostico_json.jsonl`) e `git ls-files --eol` (sem `w/crlf`).
- Commit local: `F4: emenda — resposta final pela tool responder; diagnóstico do JSON`. Sem push.
- Acrescente ao `F4-report.md` uma seção "Emenda" no formato do `CLAUDE.md` §8 e pare.

## Não faça

- Usar tickets do holdout.
- Ler o JSON de forma tolerante (regex, último objeto do texto).
- Mudar a guarda, as regras de rebaixamento, a busca ou a política.
- Iterar no prompt v2 depois da fumaça.

---

# Emenda 2: uma tool por rodada (proposta, 2026-11-17; vale só com aprovação do Gustavo)

**Orçamento:** 20 min. **Esta é a última mudança no agente antes da F5.** O resultado da fumaça abaixo não autoriza nova iteração: depois dela, o agente fica congelado como estiver.

## Motivo

- A regra 3 da emenda 1 ("`responder` junto com outra tool: vale `responder`, as outras são ignoradas") veio da spec, não do Claude Code.
- Na fumaça (5 tickets do treino), o modelo chamou `recuperar_exemplos` e `responder` na mesma resposta em 3 dos 5 tickets. Com essa regra, a recuperação foi descartada.
- Resultado: 4 de 5 respostas "Access" e as 5 divergindo do clássico.
- O LLM continua escolhendo se recupera (G7). O defeito era a regra de desempate.

## Mudança

1. Rodadas 1 e 2:
   - `tool_choice` `any` com **chamadas paralelas desligadas** (`disable_parallel_tool_use: true` na API da Anthropic; no `langchain-anthropic`, o parâmetro equivalente do `bind_tools`, por exemplo `parallel_tool_calls=False`);
   - o modelo chama exatamente uma tool por rodada.
2. Rodada 3: sem mudança (`{"type": "tool", "name": "responder"}`).
3. A regra 3 da emenda 1 sai. Se, mesmo assim, vier mais de uma chamada de tool numa resposta, é erro de tool: 1 nova tentativa da rodada e, depois, "humano decide".
4. Prompt: sem mudança (`agente_sugerir_v2.txt`).
5. Guarda, busca, política, log e limites: sem mudança.

## Testes

- Atualize `test_payload_agente`: rodadas 1 e 2 com chamadas paralelas desligadas.
- Substitua o teste "`responder` junto com outra tool" por `test_duas_tools_erro`: duas chamadas na mesma resposta → 1 nova tentativa → "humano decide".
- Os demais testes continuam passando.

## Fumaça real (só o marcador `api`, uma vez, mesmos 5 tickets do treino)

- Estime o custo antes; registre o real depois.
- Registre, por ticket:
  - sequência de tools;
  - rodadas;
  - categoria do LLM e do clássico;
  - `faixa_final`;
  - escalonamentos e a causa.
- Resumo: tickets que recuperaram exemplos antes de responder; escalonamentos por formato ou por chamada múltipla.
- **Qualquer que seja o resultado, não altere mais nada.** Reporte e congele.
- Se a versão instalada não aceitar desligar as chamadas paralelas com `tool_choice` `any`, pare e reporte antes de codar.

## Fechamento

- Rode `pytest`, `pytest -m db`, `git diff --cached` e `git ls-files --eol`.
- Commit local: `F4: emenda 2 — uma tool por rodada; agente congelado para a F5`.
- Seção "Emenda 2" no `F4-report.md`. Pare. Sem push.
