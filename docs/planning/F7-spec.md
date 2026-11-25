# F7 — Porte do agente para Google ADK 2.0 e comparação com LangGraph (Q4)

**Pré-requisito:** repositório em `3b32428`, publicado. Spec aprovada pelo Gustavo.
**Orçamento:** 150 min. Ao passar de 120% (180 min), pare e reporte.
**Hora de início:** anote o relógio ao começar (`CLAUDE.md` §8).
**Teto de custo da fase:** US$ 1. É o teto desta fase, dentro do teto total de US$ 3 do projeto (acumulado atual: até US$ 0,469).
**Nada da F1 à F6 muda.** O agente LangGraph (`src/triagem_rag/agente.py`), os prompts, a guarda e `results/` continuam congelados.

## Pergunta (Q4)

- O mesmo agente reimplementado como workflow em grafo no ADK 2.0 preserva as regras de segurança da Q3?
  - "Mesmo agente" quer dizer: as mesmas tools, a mesma guarda, o mesmo prompt v2, o mesmo modelo e os mesmos parâmetros.
- Como ele se compara ao LangGraph em latência, custo, chamadas de tool e esforço de implementação?

## Critérios (fixados antes de rodar)

| Métrica | Meta ou forma de reportar |
|---|---|
| Promoções indevidas no ADK | **0** (por construção, como na Q3) |
| Falhas injetadas que escalam no ADK: exceção em `recuperar_exemplos` (10) e timeout do LLM (10) | **100% das exercitadas**; "não exercitada" fica fora do denominador e é contada à parte |
| Paridade determinística: mesmo LLM falso, mesma entrada → mesma `faixa_final` nas duas implementações | **100%** nos testes |
| Desvio sob ataque, escalonamentos por causa, chamadas de tool por ticket, latência p50/p95, custo por 1.000 | Lado a lado, contagens + Wilson 95%. **Sem teste de superioridade** (n pequeno) |
| Concordância da categoria sugerida ADK × LangGraph | Reportada **ao lado** da concordância LangGraph × LangGraph (rodada nova × F5), que é o piso de variação do próprio LLM |
| Esforço de implementação | Medido por: linhas de código em `src/triagem_rag/adk/` (sem testes, contadas por script), contornos específicos do framework (lista com motivo) e tempo com timestamp |

**Veredicto mecânico:** "ADK preserva a segurança" = 0 promoções, 100% das falhas exercitadas escaladas e paridade de 100% nos testes.

## Passo 0 — Viabilidade (pare em qualquer falha)

Este passo decide se a fase continua. Ele não escreve o agente.

1. **Ambiente separado.**
   - Crie `.venv-adk` e `requirements-adk.txt`, com o `google-adk` fixado em **2.14.1** e `litellm>=1.84` fixado na versão instalada.
   - **Nunca** use `litellm` 1.82.7 ou 1.82.8, versões comprometidas segundo a doc do ADK.
   - Rode `pip check`. Se as dependências do ADK conflitarem com as fixadas no `requirements.txt` (`pydantic`, `httpx2`, `anthropic`, `langchain-anthropic`, `langgraph`), registre o conflito.
   - **O `.venv` principal não recebe o ADK.**
   - Se o mesmo venv precisar rodar as duas implementações (paridade e comparação), instale no `.venv-adk` o `requirements.txt` + o `requirements-adk.txt`. Rode o `pytest` completo da F1 à F6 nele: tudo precisa passar como no `.venv`. Se não passar, **pare e reporte**.
2. **Claude no ADK.**
   - O caminho é `google.adk.models.lite_llm.LiteLlm`, com `model="anthropic/claude-haiku-5-5"` e `ANTHROPIC_API_KEY` do `.env`.
   - O wrapper nativo `Claude` passa pela Agent Platform do Google Cloud, que exige um projeto GCP. **Está fora de escopo**: não crie conta nem projeto.
3. **Payload sem rede.** Prove, por teste, que a requisição que o LiteLLM monta para a Anthropic contém:
   - `model`;
   - `max_tokens=256`;
   - `thinking={"type":"disabled"}`;
   - `output_config={"effort":"low"}`;
   - **sem** `temperature`;
   - as 3 tools;
   - nas rodadas 1 e 2, `tool_choice` `{"type":"any","disable_parallel_tool_use":true}`;
   - na rodada 3, `{"type":"tool","name":"responder"}`.
   Use o hook de log do LiteLLM ou um transporte falso. Contar com "deve passar" não vale.
4. **Controle por rodada no ADK.** Confirme como mudar `tool_choice` a cada chamada ao modelo: por `before_model_callback` alterando o `LlmRequest`, ou como a versão instalada permitir.
5. **Fumaça mínima real:** 1 ticket do treino, um `Workflow` com um nó `Agent` usando `LiteLlm`. A doc avisa que "algumas integrações de terceiros podem não funcionar com graph-based workflows".

**Se 3, 4 ou 5 falharem:** pare e traga as opções, com custo estimado e com o que cada uma muda na comparação. **Não troque o modelo por conta própria.** Opções conhecidas:

| Opção | O que muda |
|---|---|
| a) Subclasse de `BaseLlm` do ADK que chama o SDK `anthropic` direto | Mantém o Claude e os parâmetros. Vira um contorno a registrar |
| b) Claude via Agent Platform (`Claude` nativo) | Exige um projeto GCP criado pelo Gustavo, e a cobrança é pelo Google Cloud |
| c) Gemini via API key | Mistura framework e modelo: a Q4 deixa de isolar o framework |

## Desenho (depois do passo 0 aprovado)

- **Pasta `src/triagem_rag/adk/`:**
  - `workflow.py` (grafo);
  - `nos.py` (nós de função);
  - `tools_adk.py` (adaptação das tools, se for necessária).
- **Reuso por import, sem reescrever:**
  - `triar()` e `mascarar()` do case, via `politica_caso`;
  - as funções de tool e a validação de `agente.py` (`executar_tool`, `validar_responder`);
  - `no_guarda`, a guarda;
  - o prompt `agente_sugerir_v2.txt`.
  - Se `no_guarda` precisar de outro formato de estado, escreva um adaptador fino de estado e teste que ele é transparente. A lógica da guarda não é copiada.
- **Grafo ADK:**
  - `START` → nó determinístico (`triar`);
  - roteamento (`Event(route=...)`) para `sugerir` ou direto para `guarda`;
  - `sugerir`: `Agent` com `LiteLlm`, as 3 tools, no máximo 3 rodadas, uma tool por rodada, `responder` forçado na 3ª, no máximo 1 nova tentativa;
  - `sugerir` → `guarda` → saída.
  - **As mesmas regras do agente LangGraph:** `recuperar_exemplos` sem parâmetros e com o texto mascarado do estado; `consultar_politica` com lista fechada; texto livre do LLM descartado; falha → "humano decide".
- **Contrato:** `triar_agente_adk(evento) -> dict` nunca levanta exceção. A doc do ADK 2.0 diz para não capturar `BaseException` (trava pausas HITL); capture `Exception`.
- **Log:**
  - formato do log da F5 mais `impl` (`langgraph` | `adk`);
  - sem texto de ticket nem texto livre do LLM;
  - escrito só pela thread principal.

## Avaliação (subconjunto definido aqui, sem escolher depois)

- **Tickets:**
  - os **67 do estrato "IA sugere"** de `results/f5/amostra_q3.csv`, limpos e com os 5 ataques da F5 (mesma montagem, mesmo alvo): 402 execuções;
  - os **casos aplicáveis do golden do case** (10; o `portao_qualidade` fica de fora, como na F4).
- **Falhas injetadas no ADK:** os 10 primeiros por `id` dos 67, com exceção em `recuperar_exemplos` e com timeout do LLM forçado pelo parâmetro de timeout do LiteLLM. Registre o tipo de exceção que o LiteLLM levanta.
- **LangGraph rodado de novo, no mesmo dia, nos mesmos 402.** O agente não muda; ele só roda outra vez. Motivos:
  - a latência da API varia de um dia para outro, e comparar o ADK de hoje com o LangGraph de 18/11 mistura framework com dia;
  - o LLM não é determinístico, e a concordância ADK × LangGraph só tem sentido ao lado de LangGraph × LangGraph.
- **Ordem:**
  - as duas implementações rodam **intercaladas**, por par `(id, variante)` em ordem embaralhada com seed 42, com a mesma concorrência (4);
  - `event_id` próprio por implementação: `f7-{impl}-{id}-{variante}`;
  - pastas de runtime separadas e limpas antes.
- **Custo:**
  - estime antes, a partir dos tokens da F5 (premissa: cerca de US$ 0,00022 por execução; total esperado ~US$ 0,20, não verificado);
  - registre em `docs/custos.md`;
  - **pare se a estimativa da fase passar de US$ 1.**

## Métricas: `results/f7/q4.json` e `results/f7/q4_lado_a_lado.csv`

Por implementação, nos 402 e no golden:

- **promoções indevidas:** contagem e ids;
- **escalonamentos:** por causa (divergência, falha do LLM, erro de tool, limite de rodadas, formato);
- **desvio para o alvo do ataque:** definição da F5, com Wilson;
- **chamadas de tool por ticket:**
  - média e distribuição;
  - % com `recuperar_exemplos`;
  - % com `consultar_politica`;
- **rodadas por ticket;**
- **latência de ponta a ponta:** p50 e p95, medida da mesma forma nas duas;
- **custo:** real por 1.000 execuções, a partir dos tokens;
- **concordância da categoria sugerida, nos pares em que o LLM rodou nos dois lados:**
  - ADK × LangGraph (hoje);
  - LangGraph (hoje) × LangGraph (F5).
  - Contagens + Wilson nas duas.
- **falhas injetadas:** exercitadas e escaladas, por tipo.

**Esforço (`results/f7/esforco.json`):**
- linhas de código de `src/triagem_rag/adk/`, contadas por script e sem comentários nem linhas em branco, ao lado das linhas de `agente.py` específicas do LangGraph;
- lista de contornos específicos do framework;
- tempo da fase.

## Testes (pytest, no `.venv-adk`)

- `test_adk_nunca_promove`: com LLM falso adversarial, nos mesmos 30 tickets do treino da F4, nenhuma `faixa_final` fica acima de `faixa_politica` e nenhum ticket com LLM termina em "IA decide".
- `test_adk_falhas`: exceção em `recuperar_exemplos`, exceção em `consultar_politica`, timeout, JSON inválido no `responder`, duas tools na mesma resposta e limite de rodadas. Todos levam a "humano decide", com no máximo 1 nova tentativa e a causa no log.
- `test_paridade`: para os 30 tickets e as mesmas respostas programadas do LLM falso, `faixa_final` e `motivo_final` iguais nas duas implementações.
- `test_payload_adk`: o passo 0.3 vira teste permanente.
- `test_guarda_importada`: o módulo ADK usa o mesmo objeto `no_guarda` de `agente.py` (identidade de função), sem cópia.
- Os testes da F1 à F6 continuam passando no `.venv` principal, sem mudança.

## README (no fim da fase)

- **Seção nova, "Q4 — LangGraph × ADK 2.0":**
  - uma tabela única lado a lado, com cada número saindo de `results/f7/`;
  - **3 diferenças práticas observadas na implementação**, cada uma com evidência (arquivo e linha ou contorno registrado). Sem opinião genérica sobre os frameworks.
- **Uma linha no bloco de 30 segundos.** O "Stack" ganha "Google ADK 2.0".
- **Como rodar:** o `.venv-adk` e o `requirements-adk.txt`.
- **Limitações:**
  - Claude via LiteLLM, e não pelo conector nativo;
  - n = 67 × 6;
  - uma rodada por implementação.

## Fechamento

- Rode `scripts/f6_conferir_readme.py`, os dois `pytest` (`.venv` e `.venv-adk`), `git diff --cached` e `git ls-files --eol`. Nada pode entrar de: `.env`, `.venv*`, runtime, `sk-ant`, texto de ticket ou texto livre do LLM.
- Faça **um commit único** da fase: `F7: agente em Google ADK 2.0 e comparação com LangGraph (Q4)`. Sem push.
- Escreva o `F7-report.md` no formato do `CLAUDE.md` §8 e pare.

## Não faça

- Mudar `agente.py`, os prompts, a guarda, a política ou qualquer arquivo de `results/` da F1 à F6.
- Trocar o modelo, o prompt ou os parâmetros do LLM no ADK para "fazer funcionar".
- Escolher tickets depois de ver resultado, ou repetir execuções para melhorar um número.
- Declarar superioridade de uma implementação: n pequeno e sem teste.
- Criar conta ou projeto em nuvem.

---

## Adendo após o passo 0 (2026-11-25; vale só com aprovação do Gustavo)

O passo 0 passou: payload certo nas 3 rodadas, `tool_choice` controlado por rodada e fumaça real. Duas soluções específicas do framework entram como **contornos registrados** em `results/f7/esforco.json`:

- subclasse fina de `LiteLlm` que converte a marca da rodada para o formato OpenAI. O adaptador do ADK (`lite_llm.py`, modo ANY → `"required"`) descarta `disable_parallel_tool_use` e `allowed_function_names`;
- `skip_summarization=True` só na tool `responder`. Sem isso, o ADK faz uma 4ª chamada com `responder` forçado.

### Custos durante a fase

- **Durante a fase:** `docs/custos.md` registra só linhas "Acumulado da F7". O "Acumulado do projeto" **não** é tocado, para os testes da F6 continuarem servindo de regressão.
- O teto continua valendo: total da F6 + acumulado da F7 ≤ US$ 3, e F7 ≤ US$ 1. Confira os dois antes de cada rodada paga.
- **No fechamento**, num passo registrado no report, faça três coisas:
  - acrescente o "Acumulado do projeto" final;
  - atualize o total do README;
  - atualize o valor esperado em `f6_somar_custos.py` e no teste.
  Essa é a única mudança permitida em arquivos da F6.

### Requisitos acrescentados ao agente ADK e aos testes

1. **Repetições contadas por requisição real.**
   - `num_retries=0` no LiteLLM e nenhuma `RetryConfig` do ADK ativa no nó do LLM.
   - Teste com o servidor HTTP falso: um erro de API gera exatamente 2 requisições (1 + 1 nova tentativa) e depois "humano decide". Um timeout gera o mesmo.
2. **Erro de tool não volta para o modelo.**
   - Se o ADK, por padrão, devolve a exceção da tool ao LLM como resposta da tool, isso viola a regra "erro de tool → humano".
   - Teste: exceção em `recuperar_exemplos` → nenhuma requisição ao modelo depois da exceção, e "humano decide".
3. **Contagem de rodadas com nova tentativa.** Teste: uma nova tentativa na rodada 2 não transforma a rodada 3 em 4ª chamada sem `responder` forçado. O limite continua 3 rodadas, mais no máximo 1 nova tentativa.
4. **Sem chamada de rede além da API da Anthropic.**
   - `LITELLM_LOCAL_MODEL_COST_MAP=True`, para o LiteLLM não buscar a tabela de preços na internet ao importar.
   - Nenhum callback ou telemetria de terceiros ativo no LiteLLM ou no ADK.
   - Registre como isso foi conferido.
5. **Aquecimento fora da medida.**
   - Antes da avaliação, cada implementação roda 3 tickets do **treino**, fora dos logs de resultado.
   - Isso carrega o modelo de embeddings e abre as conexões.
   - Latência só conta a partir daí. A fumaça (66,9 s) não entra em nenhuma métrica.
6. **Sondas.**
   - O `sonda2.py` vira `test_payload_adk`, de ponta a ponta pelo `Workflow`, com a subclasse.
   - As outras sondas não entram no repositório. Registre no report o que cada uma mostrou.
