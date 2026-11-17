# F2 — V0, V1, K1 e C nos 400 tickets

**Pré-requisito:** portão F1 aprovado em 2026-11-17 (commits `6dc8e3b` e `83f090c`).
**Orçamento:** 60 min. Ao passar de 120% (72 min), pare e reporte.
**Primeira fase com chamadas pagas.** Teto acumulado de US$ 3 (`CLAUDE.md` §3).

## Objetivo

Produzir 4 das 6 variantes de Q1 nos mesmos 400 tickets (`data/amostra_400_ids.csv`):

| Id | Variante | Fonte |
|---|---|---|
| V0 | LLM com o prompt do case, 8 exemplos fixos (1 por categoria) | API, replicando o `f3_llm.py` do case |
| V1 | LLM com 5 exemplos **aleatórios** do treino, fixos por ticket | API, prompt novo `classificar_rag_v1.txt` |
| K1 | Voto majoritário dos 5 vizinhos híbridos, sem LLM | Banco, sem API |
| C | Classificador clássico | `data/caso/f3_probs_holdout_grupo.csv`, sem API |

- Também nesta fase: gravar as listas de vizinhos dos 400 para a F3 reaproveitar, e o módulo de métricas com testes.
- **Fora da F2:**
  - V2 e V3;
  - qualquer comparação da família pré-registrada (V3 × V1, V3 × K1, V3 × C, V2 × V3);
  - correção de Holm aplicada a resultados. Tudo isso fica para a F3.

## Referência do case (somente leitura)

`C:\Users\gusta\challenge-g4-ai-master\ai-master-challenge\submissions\gustavo-covaleski\solution\f3_llm.py`, commit `3a880f2`. Parâmetros que V0 precisa replicar:

| Item | Valor no case |
|---|---|
| Modelo | `claude-haiku-5-5` |
| `max_tokens` | 64 |
| `thinking` | `{"type": "disabled"}` |
| `output_config` | `{"effort": "low"}` |
| `temperature`, `top_p`, `top_k` | **não enviados** |
| System | `classificar_v1.txt` com `{exemplos}` substituído |
| Exemplos | Para cada categoria, na ordem de `CATEGORIAS`: `treino[treino["Topic_group"] == c].sample(1, random_state=42)` sobre o treino em ordem de `ler_ds2().merge(f1_splits)`. Formato: `<ticket>{texto}</ticket>\n{"categoria": c, "confianca": 1.0}`, unidos por `\n\n` |
| Mensagem do usuário | `<ticket>{texto}</ticket>` |
| Validação | JSON estrito: o texto inteiro, sem espaços nas pontas, é um objeto; `categoria` está entre as 8; `confianca` é número (int ou float, não bool) entre 0 e 1 |
| Repetições | Até 3 tentativas para erro de API (`RateLimitError`, `APIConnectionError`, `InternalServerError`), com espera de 2^n s; mais 1 repetição se a saída for inválida; se continuar inválida, `falha` |
| Concorrência | 8 chamadas simultâneas; latência medida por chamada, no cliente |

**Exceção registrada ao `CLAUDE.md` §3 ("no máximo 1 nova tentativa"):**
- a regra vale para o agente (F4);
- nas variantes de experimento, a política de repetição é a do case, para V0 ser reprodução e V1 ser comparável;
- registre a exceção em `docs/decisoes.md`.

## Passos

### 0. Pré-condições (pare se alguma falhar)

- `.env` contém `ANTHROPIC_API_KEY`. Confira só a presença, **nunca imprima o valor nem parte dele**.
- `LANGCHAIN_TRACING_V2` não é `true`. Faça um assert no início dos scripts que chamam a API.
- Docker de pé; `pytest` e `pytest -m db` passando.
- Instale `langchain-anthropic` e `pydantic`, e fixe as versões no `requirements.txt`.
- Fixe também o `scipy`, que já vem com o scikit-learn.

### 1. Preço e estimativa de custo (antes de qualquer chamada)

- Consulte a página oficial de preços da API da Anthropic. Registre em `docs/custos.md`:
  - a URL;
  - a data da consulta;
  - o preço de entrada e de saída do `claude-haiku-5-5` em US$/MTok.
- Se o preço divergir do case (US$ 0,10 de entrada, US$ 0,50 de saída, consultado em 2026-11-03), registre a divergência.
- **Não use preço de memória.** Se a página não for acessível, pare e reporte.
- Estime antes de chamar:
  - com `count_tokens`, meça o system de V0 e o de V1 de 5 tickets de exemplo;
  - estime 400 tickets × 1,05 chamada por ticket (folga para repetições) × 2 variantes;
  - registre a estimativa em `docs/custos.md`.
- Pare se o acumulado mais a estimativa passar de US$ 3. Referência do case: ~US$ 0,06 por 400 tickets em V0.

### 2. Cliente LLM via LangChain: `src/triagem_rag/llm.py`

- Use `ChatAnthropic` (`langchain-anthropic`) com:
  - `model="claude-haiku-5-5"`;
  - `max_tokens=64`;
  - `max_retries=0`: as repetições ficam no nosso código, como no case;
  - `thinking={"type": "disabled"}`;
  - `output_config={"effort": "low"}`, pelo parâmetro que a versão instalada expuser (`model_kwargs` ou equivalente).
- **Não envie `temperature`.**
- Entrada: `SystemMessage(system)` e `HumanMessage("<ticket>{texto}</ticket>")`.
- **Saída como texto livre validada depois.** Não use `with_structured_output` nem tool calling: isso mudaria o formato e quebraria a reprodução de V0.
- Pegue os tokens de `usage_metadata` (entrada e saída) para o custo real.
- **Teste sem rede** (`test_payload_llm`): obtenha o payload que o `ChatAnthropic` enviaria, pelo método interno de montagem de payload da versão instalada ou por um transporte HTTP falso. Verifique:
  - `model`, `max_tokens == 64`, `thinking` e `output_config` iguais ao case;
  - ausência de `temperature`, `top_p` e `top_k`;
  - system e mensagem do usuário no formato acima.
- **Se a versão instalada não conseguir enviar `thinking` ou `output_config` como no case, pare e reporte.** Não troque pelo SDK puro sem decisão.

### 3. Validação com Pydantic: `src/triagem_rag/esquema.py`

- `Classificacao(BaseModel)`:
  - `categoria: Literal[...]` com as 8 categorias de `dados.CATEGORIAS`;
  - `confianca`: int ou float estrito (bool rejeitado), entre 0 e 1;
  - chaves extras ignoradas, como no case.
- `validar(texto) -> Classificacao | None`: faz `json.loads(texto.strip())`, sem tolerar texto antes ou depois do objeto nem cercas de markdown.
- **Teste de paridade** (`test_validar_paridade`): o novo `validar` e o `validar` do case (copie a função para o teste, com atribuição) dão o mesmo veredito em pelo menos estes casos:
  - JSON válido;
  - `confianca` igual a `1` (int), `true`, `1.5`, `-0.1` ou `"0.9"` (string);
  - categoria fora da lista;
  - capitalização errada (`"access"`);
  - texto antes do JSON;
  - cerca ```` ```json ````;
  - chave extra;
  - string vazia;
  - JSON truncado (como no id 5909 do case).

### 4. Métricas: `src/triagem_rag/metricas.py`

- `wilson(k, n, z=1.959964)` → (inferior, superior).
- `macro_f1(y, p)`: sobre as 8 categorias, com `falha` contando como erro.
- `matriz_confusao(y, p)`: 8 linhas × 9 colunas (8 categorias mais `falha`).
- `mcnemar_exato(acertos_a, acertos_b)`:
  - b = A acerta e B erra; c = B acerta e A erra;
  - p bilateral por `scipy.stats.binomtest(min(b, c), b + c, 0.5)`;
  - b + c = 0 → p = 1;
  - devolve b, c e p.
- `holm(pvalores)`: p ajustados, monotônicos, limitados a 1.
- **Testes com valores calculados à mão, escritos no teste:**
  - `wilson(106, 400)` = (0,2241; 0,3103) e `wilson(278, 400)` = (0,6482; 0,7381), com 4 casas;
  - `wilson(0, 10)` = (0,0; 0,2775);
  - `mcnemar_exato` com b = 2 e c = 10: p = 0,038574 (6 casas);
  - b = c = 0: p = 1;
  - `holm([0.01, 0.04, 0.03, 0.2])` = `[0.04, 0.09, 0.09, 0.2]`.
- **Nota para o report:** o IC do case (22,25% a 31,0%) era bootstrap. O Wilson de 106/400 é 22,41% a 31,03%. O **critério de reprodução continua sendo o pré-registrado na F0:** acurácia de V0 dentro de [22,25%; 31,0%].

### 5. Vizinhos dos 400, K1 e C (sem API): `scripts/f2_vizinhos.py`

- **Vizinhos:**
  - para cada um dos 400, rode `buscar_vetorial(texto, 50)` e `buscar_fulltext(texto, 50)` uma vez cada;
  - grave em `results/f2/vizinhos_400.csv`: `id_consulta, recuperador (vetorial|fulltext), rank, id_vizinho, categoria_vizinho`;
  - **sem texto.**
  - Conexão psycopg reaproveitada. Paralelismo opcional, com no máximo 4 conexões.
- **Asserts anti-vazamento:**
  - todo `id_vizinho` está no treino;
  - nenhum `id_vizinho` é igual ao `id_consulta`;
  - nenhum `id_vizinho` pertence ao `group_id` do `id_consulta`.
- **Híbrida:** use `rrf()` sobre as duas listas lidas desse CSV, sem consultar o banco de novo. Grave `results/f2/hibrida_top5_400.csv`: `id_consulta, rank, id_vizinho, categoria_vizinho`.
  - Teste: para 3 ids, `buscar_hibrida(texto, 5)` ao vivo devolve os mesmos ids que o CSV.
- **K1:**
  - categoria mais frequente entre os 5 vizinhos híbridos;
  - empate: vence a categoria do vizinho de **melhor rank** entre as empatadas;
  - teste com um caso de empate escrito à mão.
- **C:** a predição do clássico nos 400, tirada de `data/caso/f3_probs_holdout_grupo.csv`. Assert: 278/400 acertos.
- Registre o tempo total da etapa.

### 6. V0: `scripts/f2_llm.py --variante v0`

- **Montagem do system:**
  - monte o system como no case e grave os 8 ids de exemplo em `results/f2/exemplos_v0.csv` (`categoria, id_exemplo`);
  - assert: os 8 ids estão no treino e têm a categoria indicada;
  - grave o SHA-256 do system em `results/f2/metricas_f2.json`.
- **Execução:** 400 tickets, concorrência 8, política de repetição do case.
- **Log `results/f2/llm_log_v0.jsonl`:** uma linha por chamada, com `id, variante, tentativa, latencia_ms, tokens_entrada, tokens_saida, resposta_bruta, valida, erros_api`. A `resposta_bruta` é só a saída do LLM; o texto do ticket **não entra**.
- **Portão de reprodução:**
  - calcule a acurácia de V0;
  - **se cair fora de [22,25%; 31,0%], pare antes de V1** e reporte com a matriz de confusão e a comparação com o case.
- **Variação entre rodadas:** compare V0 novo com `data/caso/f3_v0_pred.csv`:
  - % de tickets com a mesma predição;
  - McNemar exato entre os acertos dos dois, exploratório.

### 7. V1: `scripts/f2_llm.py --variante v1`

- **Prompt `prompts/classificar_rag_v1.txt`:** cópia de `classificar_v1.txt` com **uma única mudança**: a linha `Labeled examples (one per category):` passa a `Labeled examples from the training set:`.
  - Nada mais muda: instruções, delimitação, formato de saída e formato dos exemplos.
  - **O mesmo template serve para V2 e V3 na F3.** Registre em `docs/decisoes.md` que ele fica congelado.
- **Exemplos por ticket:**
  - 5 tickets do treino, sorteados sem reposição com `np.random.default_rng([42, id])`, fixos por ticket;
  - ordem do prompt = ordem do sorteio;
  - formato de cada exemplo igual ao do case;
  - grave `results/f2/exemplos_v1.csv` com `id, ordem, id_exemplo, categoria_exemplo`.
- **Regra de ordem congelada para a F3:** em V2 e V3, os vizinhos entram em ordem de rank, com o rank 1 primeiro.
- Assert: nenhum exemplo é do holdout. Asserts adicionais:
  - `exemplos_v1.csv` tem exatamente 5 exemplos por ticket;
  - ids de exemplo distintos dentro de cada ticket;
  - nenhum exemplo é o próprio ticket.
- Mesma execução e o mesmo formato de log de V0: `results/f2/llm_log_v1.jsonl`.

### 8. Consolidação: `scripts/f2_metricas.py`

- **`results/f2/predicoes_400.csv`:** `id, rotulo, v0, v1, k1, c, v0_caso`. Valores possíveis: categoria ou `falha`.
- **`results/f2/metricas_f2.json`:**
  - por variante:
    - n;
    - acertos;
    - acurácia;
    - Wilson 95%;
    - macro-F1;
    - matriz de confusão;
    - falhas;
    - saídas inválidas na primeira tentativa;
    - erros de API.
  - só para V0 e V1:
    - tokens médios de entrada e saída;
    - chamadas por ticket;
    - custo real total e por 1.000 tickets;
    - latência p50 e p95.
  - por variante, a categoria mais prevista, para verificar se repete a superprevisão de `Access` do case.
- **Comparações exploratórias** (McNemar exato, **sem** Holm, rotuladas "exploratório, fora da família pré-registrada"):
  - V0 novo × V0 do case;
  - V1 × V0;
  - K1 × C;
  - V1 × C.
- Atualize `docs/custos.md` com o custo real da fase e o acumulado.

### 9. Testes

Execução padrão, sem banco e sem chave:

- `test_payload_llm`;
- `test_validar_paridade`;
- os testes de métricas;
- `test_k1_empate`;
- `test_template_rag`: `classificar_rag_v1.txt` difere de `classificar_v1.txt` em exatamente uma linha;
- `test_exemplos_v1`, que lê `results/f2/exemplos_v1.csv`. Em `test_exemplos_v1`, confira:
  - 5 exemplos por ticket;
  - nenhum do holdout;
  - nenhum igual ao ticket;
  - reprodução idêntica com a mesma seed.

Testes marcados:

- `@pytest.mark.db`: `test_hibrida_csv_igual_ao_vivo`;
- `@pytest.mark.api`: uma chamada real de fumaça, que **não roda por padrão**.

### 10. Fechamento

- Rode `pytest` e `pytest -m db`.
- Confira `git diff --cached`: nada de `.env`, `data/raw/`, `*.joblib` nem `sk-ant`.
- Confira também que os logs `.jsonl` não contêm texto de ticket. Teste por amostragem: nenhuma `resposta_bruta` contém trecho de 30 ou mais caracteres de um texto do DS2.
- Confira que `git ls-files --eol` não tem `w/crlf`.
- Faça um commit local: `F2: V0, V1, K1 e C nos 400; vizinhos para a F3; métricas`. **Sem push.**
- Escreva `docs/planning/F2-report.md` no formato do `CLAUDE.md` §8.
  - A §3 compara com as hipóteses da F0: V1 > V0? K1 perto de C? V0 reproduz?
  - A §6 traz o custo real.
- Pare.

## Critérios de aceite

1. Preço consultado na página oficial, com data. Estimativa registrada antes e custo real depois, em `docs/custos.md`.
2. `test_payload_llm` prova `thinking` e `output_config` iguais ao case e sem `temperature`.
3. V0 dentro de [22,25%; 31,0%], ou fase parada no passo 6 com o report.
4. `vizinhos_400.csv` só com treino, sem o próprio ticket e sem o próprio grupo. A híbrida do CSV bate com a ao vivo.
5. C = 278/400.
6. `predicoes_400.csv` e `metricas_f2.json` completos para V0, V1, K1 e C.
7. Nenhum texto de ticket em `results/`, nenhum segredo no commit e nenhum arquivo com CRLF.

## Não faça nesta fase

- Rodar V2, V3 ou a sensibilidade a k.
- Calcular a precisão de rótulo dos recuperadores (Q2): isso é F3.
- Ajustar o prompt, o k ou a ordem dos exemplos depois de ver resultado. Se V1 parecer ruim, reporte; não corrija.
- Repetir V0 ou V1 para "melhorar" um número. Uma rodada por variante.
- Usar `with_structured_output`, tool calling ou o SDK puro sem decisão.
