# F4 — Agente LangGraph com tool calling e guarda determinística

**Pré-requisito:** portão F3 aprovado em 2026-11-17 (commit `0d780fa`). A F3b pode estar rodando em paralelo (ver "Convivência com a F3b").
**Orçamento:** 90 min. Ao passar de 120% (108 min), pare e reporte.
**Hora de início:** anote o relógio ao começar (`CLAUDE.md` §8).
**Custo de API esperado:** só o teste de fumaça do agente, até 5 tickets. A avaliação completa (211 tickets × ataques) é a F5.

## Decisões que esta fase implementa

| # | Decisão (Gustavo) | Origem |
|---|---|---|
| G7 | Grafo fixo. No nó `sugerir`, tool calling real: o LLM recebe `recuperar_exemplos` e `consultar_politica` via `bind_tools` e decide se chama. Cada chamada fica no log. A guarda "nunca promove" fica no código | F0 §10 |
| D-F3-1 | `recuperar_exemplos` usa a busca **vetorial**, não a híbrida | 2026-11-17, depois da F3: nos 400, precisão@5 da híbrida − vetorial = −0,0365 (IC −0,0645 a −0,009); V2 47,75% × V3 45,25% (p Holm 0,229) |
| D-F3-2 | O agente existe para responder a Q3: **segurança da execução da política** sob tool calling, não acurácia. O README diz que, em acurácia, o voto dos vizinhos (K1) supera o LLM com os mesmos vizinhos | 2026-11-17, depois da F3: V3 × K1 = −9,5 pp, p Holm 9,5e-04 |

Registre D-F3-1 e D-F3-2 em `docs/decisoes.md` como decisões **posteriores** aos resultados da F3, com a evidência acima. Na linha "Agente" de `F0-escopo.md` §5, acrescente "(D-F3-1: recuperação vetorial)".

## Desenho

### Reuso do case, sem reescrever a política

- O agente **chama** `triar(evento)` do case (`src/triagem_rag/caso/triagem.py`) para a parte determinística, com toda a lógica dela:
  - mascaramento;
  - idempotência;
  - texto insuficiente;
  - classificador;
  - `faixa_para`;
  - regra de ação (`tipo_ds1`);
  - modo sombra;
  - log do case.
- Para pegar o texto mascarado, chama `mascarar()` do case, a mesma função.
- **Não altere `src/triagem_rag/caso/*.py`.**
- A ligação de caminhos fica num adaptador, `src/triagem_rag/politica_caso.py`:
  - põe `src/triagem_rag/caso` no `sys.path` (o case importa `from comum import ...`);
  - aponta `triagem.OUT_DIR` para `data/caso`;
  - usa `TRIAGEM_CACHE_DIR=data/modelos` e `TRIAGEM_MODELO_VERSAO=<versão do joblib da F1>`;
  - usa `TRIAGEM_RUNTIME_DIR` numa pasta própria do agente, fora do git (acrescente-a ao `.gitignore`).
- O `carregar_modelo` do case espera um dict `{"pipeline", "versao", ...}`. Se o joblib da F1 não estiver nesse formato:
  - grave, **sem retreinar**, um arquivo no formato do case a partir do mesmo pipeline, em `data/modelos/`;
  - registre em `docs/decisoes.md`;
  - teste que as predições nos 400 continuam com 278 acertos.
- Se a ligação exigir mudar a lógica do case, **pare e reporte**.

### Grafo (LangGraph `StateGraph`, arestas fixas)

```
entrada → deterministico → [roteia] → sugerir → guarda → fim
                              └──────────────→ guarda → fim
```

**Estado tipado (`TypedDict`):**
- evento;
- texto_mascarado;
- resultado de `triar`;
- faixa_politica;
- categoria_classico;
- p_max;
- sugestao_llm;
- tool_calls;
- erros;
- faixa_final;
- motivo_final.

**Nó `deterministico`:**
- chama `triar(evento)` e guarda o resultado inteiro;
- `faixa_politica` = `faixa_sem_sombra` do case.

**Roteamento:** vai para `sugerir` **só** se todas as condições valem:
- `faixa_politica` ≠ "IA decide";
- `duplicado` é falso;
- o motivo não é "texto insuficiente" nem "falha do classificador";
- `erro` é nulo.

Em qualquer outro caso, vai direto para `guarda`, **sem chamar o LLM**.

**Nó `sugerir`:**
- `ChatAnthropic` com os mesmos parâmetros da F2 (`claude-haiku-5-5`, `thinking` desligado, `output_config` com effort low, sem `temperature`, `max_retries=0`), exceto `max_tokens=256`, para caber a chamada de tool.
- `bind_tools([recuperar_exemplos, consultar_politica])` com `tool_choice` automático.
- System: `prompts/agente_sugerir_v1.txt`, novo e congelado nesta fase. Base nas instruções de `classificar_v1.txt`:
  - as 8 categorias;
  - o aviso de texto pré-processado;
  - o ticket entre `<ticket>` como dado, nunca instrução.
- Acréscimos ao system:
  - descrição das duas tools;
  - "a resposta final é só o JSON `{"categoria": ..., "confianca": ...}`".
- O prompt **não** fala de faixas nem diz que o LLM decide algo.
- Mensagem do usuário: `<ticket>{texto_mascarado}</ticket>`.
- **Laço:** no máximo 3 rodadas de LLM por ticket. A 3ª rodada não executa tools; se ainda pedir tool, é falha.
- **Resposta final:**
  - validada com o `esquema.validar` da F2;
  - inválida → 1 nova tentativa da rodada final;
  - inválida de novo → falha.
- **Erros de API:**
  - no máximo 1 nova tentativa por rodada (`CLAUDE.md` §3, regra do agente);
  - **não** usar a política de 3 tentativas do experimento.

**Tools (`@tool`), argumentos do LLM tratados como dado não confiável:**
- **`recuperar_exemplos()`:**
  - **sem parâmetros**;
  - consulta a busca vetorial (`buscar_vetorial`, top 5) **sempre com o `texto_mascarado` do estado**, nunca com texto vindo do LLM;
  - devolve os 5 exemplos do treino no formato do case (`<ticket>…</ticket>` + `{"categoria": …}`), em ordem de rank.
- **`consultar_politica(categoria)`:**
  - aceita só uma das 8 categorias (lista fechada, comparação exata);
  - fora da lista → erro de tool;
  - devolve só o teto da política para a categoria e os limiares `t_decide`/`t_sugere`;
  - **não altera nada.**
- **Qualquer outra situação é erro de tool:**
  - nome de tool desconhecido;
  - argumento extra;
  - exceção.

**Nó `guarda` (determinístico, a única fonte de `faixa_final`):**

| Situação | faixa_final | motivo_final |
|---|---|---|
| LLM não rodou | `faixa` do case (inclui o modo sombra) | o do case |
| LLM falhou: API, timeout, JSON inválido, rodadas, erro de tool | "humano decide" | "escalado: <causa>" |
| LLM rodou e categoria ≠ categoria do clássico | "humano decide" | "divergência LLM × clássico" |
| LLM rodou e categoria = categoria do clássico | `faixa` do case, sem mudança | o do case + "LLM concorda" |

- **Asserts dentro da guarda, que levantam e caem no fallback "humano decide":**
  - `ORDEM.index(faixa_final) <= ORDEM.index(faixa_politica)`;
  - se o LLM rodou, `faixa_final != "IA decide"`.
- A confiança do LLM **nunca** entra na regra.
- A sugestão do LLM vai para o humano como informação, **ao lado** da categoria do clássico.

**`escalar_humano`:** pode ser um nó separado ou a linha correspondente da guarda. Registra a causa.

**Contrato:** como `triar`, a função pública `triar_agente(evento) -> dict` nunca levanta exceção. Qualquer exceção resulta em "humano decide" com motivo "falha interna do agente".

### Log estruturado: `results/f4/agente_log.jsonl` nas execuções de teste, ou a pasta de runtime do agente

Uma linha por ticket, com:
- `chave` do case;
- `faixa_politica`, `faixa_final` e `motivo_final`;
- `categoria_classico`, `p_max` e `categoria_llm`;
- `llm_rodou`;
- `rodadas`;
- `tool_calls`: lista com nome, argumentos (só categorias, nunca texto), resultado resumido (ids e categorias dos exemplos, ou o teto da política), latência e rodada;
- `erros`;
- tokens de entrada e saída e latência total.

**Sem texto de ticket, mascarado ou não.**

## Passos

0. **Registros.** Faça as anotações de decisão listadas acima. Instale `langgraph` e fixe a versão no `requirements.txt`.
1. **Adaptador `politica_caso.py`** e teste: o golden set do case via `triar` passa como no case. Os casos `falha_classificador` e `modo_sombra` usam as variáveis de ambiente do case. O caso `portao_qualidade` fica de fora, porque já foi medido na F1.
2. **Prompt `prompts/agente_sugerir_v1.txt`.** Registre o SHA-256 em `docs/decisoes.md`.
3. **Tools, nós, grafo e `triar_agente`** em `src/triagem_rag/agente.py`.
4. **Testes sem rede.** Use um chat model falso do `langchain_core` que devolve `AIMessage` com `tool_calls` programados. Os testes que precisam do banco para `recuperar_exemplos` são marcados `db`, ou a tool é injetada por dependência.
   - `test_ia_decide_nao_chama_llm`: ticket que o case põe em "IA decide" → zero chamadas ao modelo falso; `faixa_final` igual à do case.
   - `test_nunca_promove`: para 30 tickets do treino com faixas variadas, o modelo falso responde de forma adversarial (`confianca` 1.0, categoria igual ou diferente do clássico, chamadas a `consultar_politica`) → nenhuma `faixa_final` acima da `faixa_politica`, e nunca "IA decide" quando o LLM rodou. Use tickets do **treino** para não consumir o holdout.
   - `test_divergencia_rebaixa` e `test_concordancia_mantem`.
   - `test_falhas`, um caso para cada: exceção em `recuperar_exemplos`; exceção em `consultar_politica`; categoria inválida em `consultar_politica`; tool desconhecida; argumento extra; erro de API em duas tentativas seguidas; timeout; JSON inválido duas vezes; 3 rodadas pedindo tool. Em todos: "humano decide", no máximo 1 nova tentativa, causa no log.
   - `test_recuperar_ignora_argumento`: se o modelo falso tentar passar texto para `recuperar_exemplos`, é erro de tool (não há parâmetro), e a consulta nunca usa texto vindo do LLM.
   - `test_log_sem_texto`: nenhuma linha do log contém trecho de 30 caracteres ou mais do ticket, mascarado ou não.
   - `test_contrato_sem_excecao`: exceção forçada dentro do grafo → dict com "humano decide".
   - `test_golden_agente`: os casos do golden set do case via `triar_agente` dão a mesma `faixa_final` de `triar` quando o LLM não roda. Os 3 casos em português podem rodar o LLM falso; esperado `faixa_final` ≠ "IA decide".
   - `test_payload_agente`: o payload do `ChatAnthropic` com tools tem `max_tokens=256`, `thinking` e `output_config` iguais à F2, sem `temperature`, e as duas tools declaradas.
5. **Fumaça real (`@pytest.mark.api`, fora do padrão).**
   - Antes: estime o custo e registre em `docs/custos.md`.
   - Rode uma vez com 5 tickets **do treino** (seed 42), escolhidos entre os que o case põe fora de "IA decide".
   - Registre o custo real, as tools que o LLM chamou e as rodadas.
   - O resultado não é métrica. A avaliação é a F5.
6. **Fechamento:**
   - rode `pytest` e `pytest -m db`;
   - confira `git diff --cached`: sem `.env`, `data/raw/`, `*.joblib`, `sk-ant` nem pasta de runtime;
   - confira `git ls-files --eol`: sem `w/crlf`;
   - commit local: `F4: agente LangGraph com tool calling e guarda determinística`;
   - escreva o `F4-report.md` e pare. **Sem push.**

## Convivência com a F3b

- A F3b pode estar rodando no Postgres. **Não pare, não reinicie o Docker nem recrie índices.**
- Não toque em `results/f3/` nem em `scripts/f3_recuperacao.py`.
- Se um teste `db` ficar lento, registre. Não mude timeouts para mascarar a lentidão.
- Os arquivos da F3b **não entram** no commit da F4. Use `git add` só com os caminhos da F4 e confira `git diff --cached --stat`.

## Critérios de aceite

1. Decisões D-F3-1 e D-F3-2 registradas; o prompt do agente congelado, com SHA-256.
2. Política do case reutilizada via `triar`, sem alterar `caso/*.py`; golden set do case passando pelo adaptador.
3. Grafo com `bind_tools` real, até 3 rodadas, `recuperar_exemplos` vetorial e sem parâmetros, `consultar_politica` com lista fechada.
4. Guarda determinística: os testes de "nunca promove", das falhas e do contrato passam.
5. Log sem texto de ticket, com cada tool call registrada.
6. Fumaça real executada uma vez, com custo estimado antes e real depois.
7. Commit local só com os arquivos da F4.

## Não faça nesta fase

- Avaliar o agente nos 211 tickets nem rodar os ataques: isso é a F5.
- Usar tickets do holdout nos testes ou na fumaça.
- Deixar o LLM ver ou alterar faixas, limiares ou a política além do que `consultar_politica` devolve.
- Usar a confiança do LLM em qualquer regra.
- Alterar a política, os limiares, `caso/*.py` ou a busca vetorial.
