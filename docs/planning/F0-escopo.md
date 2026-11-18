# F0 — Escopo: triagem-tickets-rag-agente

Status: **aprovado no portão F0 em 2026-11-17, com ajustes** (seção 10). As marcas **[G#]** remetem às decisões registradas.

## 1. O que este repositório é

- É uma extensão pessoal, feita depois do case técnico do G4 (PR #228: https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228).
- O case mostrou três coisas:
  - o classificador clássico acerta 85,07% no holdout por grupo;
  - um LLM sem contexto da convenção de rótulos acerta 26,5% na faixa de dúvida, contra 69,5% do clássico nos mesmos 400 tickets;
  - a política por categoria contém injeção (0 casos silenciosos em 6.395).
- O repositório testa se três técnicas mudam esse quadro: RAG, busca híbrida e agente com tool calling.
- **Regra central:** cada tecnologia responde a uma pergunta mensurável, com baseline e controle. Resultado negativo é publicado como achado.

## 2. Perguntas, métricas e hipóteses pré-registradas

As hipóteses ficam registradas **antes** de qualquer execução. O report de cada fase compara o resultado com elas.

### Q1 — Exemplos recuperados (RAG) melhoram o LLM na faixa de dúvida?

- **Amostra:** os mesmos 400 tickets do case (`f3_llm_log.jsonl`):
  - holdout por grupo;
  - `p_max < 0,74` do classificador;
  - seed 42.
- **Variantes:** mesmos 400 tickets, mesmo modelo e mesmo formato de saída.

| Id | Variante | O que isola |
|---|---|---|
| V0 | Prompt do case sem alteração (**8 exemplos fixos**, 1 por categoria) | Reprodução do case |
| V1 | k = 5 exemplos **aleatórios** do treino, fixos por ticket (seed 42) | Controle: "qualquer exemplo ajuda?" |
| V2 | k = 5 vizinhos por busca **vetorial** | Efeito da seleção por similaridade |
| V3 | k = 5 vizinhos por busca **híbrida** (RRF) | Efeito da fusão |
| K1 | Voto majoritário dos 5 vizinhos híbridos, **sem LLM** | Controle: "o LLM agrega algo ao vizinho?" |
| C | Classificador clássico (probabilidades do case) | Baseline de produção |

- **Correção do plano original:** V0 **não é zero-shot.** O `classificar_v1.txt` do case injeta 8 exemplos fixos do treino. Um zero-shot real (V0z) é opcional **[G3]**.
- **Métricas:**
  - acurácia com IC de Wilson 95%;
  - macro-F1;
  - matriz de confusão;
  - custo por 1.000 tickets;
  - latência p50 e p95.
- **Teste pré-registrado:** McNemar pareado com correção de Holm sobre 4 comparações:
  - **primária:** V3 × V1;
  - **secundárias:** V3 × K1, V3 × C e V2 × V3.
- **Critério:**
  - "RAG ajuda" só se V3 > V1 com p ajustado < 0,05;
  - "o LLM agrega" só se V3 > K1 com p ajustado < 0,05;
  - "vale para produção" só se V3 ≥ C. Mesmo assim, o LLM fica só como sugestão (ver Q3).
- **Hipóteses direcionais (não verificadas):**
  - V2 e V3 ficam acima de V1, e V1 acima de V0: o erro do case parece vir da convenção de rótulos, e os vizinhos carregam a convenção;
  - K1 empata com V3: o LLM pode só copiar o rótulo majoritário dos vizinhos;
  - C ≥ V3.
- **Reprodução de V0:**
  - o Haiku 5.5 não aceita `temperature` diferente do padrão, então a saída não é determinística;
  - critério: a acurácia de V0 cai dentro do IC do case (22,25% a 31,0%);
  - medir também a concordância por ticket com as respostas do case, que dá a variação entre rodadas.
  - Se V0 cair fora do IC: parar e investigar antes de rodar V1 a V3.

### Q2 — A busca híbrida recupera vizinhos melhores que a busca só vetorial?

- **Sem custo de API:** medida em **todo o holdout por grupo** (9.567 tickets), além do recorte dos 400.
- **Métricas:**
  - precisão de rótulo@5: % dos 5 vizinhos com o mesmo rótulo da consulta;
  - acurácia de K1 por recuperador;
  - % de consultas com zero resultados no full-text.
- **Comparação:** vetorial × full-text × híbrida.
  - Diferenças pareadas com IC por bootstrap (2.000 reamostragens, seed 42).
  - O efeito na classificação é V2 × V3 de Q1.
- **Hipótese (não verificada):** o full-text fica perto da vetorial ou acima dela, porque o texto do DS2 já vem sem palavras funcionais e funciona como saco de termos. A híbrida fica ≥ às duas.
- **Teto:** o ruído de rótulo limita qualquer recuperador (discordância de 3,82% entre quase-duplicados; o revisor externo do case concordou em 46,7%). A acurácia mede aderência à convenção do dataset, não "verdade".

### Q3 — Um agente com tools executa a política do case sem violar as regras de segurança?

- **Conjunto:**
  - o golden set do case (11 casos);
  - mais 200 tickets do holdout (seed 42, estratificados por faixa da política);
  - os 5 ataques de `ataques_v1.json` aplicados a esses 200;
  - falha simulada de cada tool.
- **Métricas e metas:**

| Métrica | Meta |
|---|---|
| Promoções indevidas para "IA decide" (LLM participou ou a política não colocaria o ticket lá) | **0** |
| Concordância de faixa com `triar()` do case | 100% |
| Falha simulada por tool → `escalar_humano`, com ≤ 1 nova tentativa e evento no log | 100% |
| Sugestões do LLM alteradas pelo ataque | medida, sem meta |
| % de tickets em que o LLM chamou cada tool, e nº de chamadas por ticket | medidos, sem meta |
| Custo e latência por ticket | medidos |

- **Ressalva pré-registrada:** a meta de 0 promoções é garantida **por construção**, porque a faixa é atribuída por código determinístico. Esse teste prova a guarda, não o "bom comportamento" do LLM. O que mede o LLM é a métrica de sugestões alteradas pelo ataque. O README apresenta as duas separadas.

## 3. Anti-vazamento

- O índice contém **só** `split_grupo == treino` de `f1_splits.csv` (38.270 linhas esperadas; conferir na F1).
- Os grupos de quase-duplicados não cruzam o split, por construção do case. Um vizinho nunca é cópia de um ticket do holdout.
- Teste obrigatório: nenhum id do holdout está no índice.
- k, RRF, número de candidatos, prompt e configuração do full-text ficam **fixados a priori** (seção 5). Nenhum é ajustado olhando os 400 tickets ou o holdout.
- Se o prompt de RAG precisar de ajuste, use **uma amostra de validação do treino** (200 tickets), recuperando vizinhos **sem o grupo do próprio ticket**. Nunca use os 400.

## 4. Limitações registradas desde já

- O texto do DS2 vem pré-processado: 0% de maiúsculas, palavras funcionais removidas. Isso prejudica embeddings de frase treinados em texto natural e favorece busca por termos.
- Os 400 tickets vêm da faixa `p_max < 0,74`, o limiar antigo do case. Os limiares implantados depois são 0,64 e 0,71, então parte desses tickets hoje cairia em "IA sugere". Mantidos para comparar com o case.
- Com n = 400 pareado, diferenças abaixo de ~5 pp provavelmente não serão significativas. **Premissa:** depende dos pares discordantes.
- LLM não determinístico: cada variante roda uma vez. A variação entre rodadas é estimada só para V0, contra o case.

## 5. Arquitetura e escolhas fixadas a priori

| Componente | Escolha | Motivo |
|---|---|---|
| Banco | Postgres + pgvector, imagem oficial `pgvector/pgvector`, tag fixa. **Plano B [G2]:** Supabase com pgvector, só se o Docker falhar na F1 | Vetor e full-text no mesmo banco; reproduzível via `docker compose` |
| Busca vetorial | **Exata** (sem HNSW/IVF), cosseno, embeddings normalizados | Com ~38 mil vetores, a busca exata é viável e evita confundir a medida com a aproximação do índice |
| Full-text | `tsvector` com config `english`, índice GIN, consulta em **OR** dos lexemas, `ts_rank_cd`, top 50 (emenda F1: normalização 2) | `plainto_tsquery` usa AND e zera consultas longas |
| Fusão | RRF com constante 60, top 50 de cada recuperador, top 5 final | Constante usual da literatura (Cormack et al., 2009) |
| Embeddings | `sentence-transformers` local, `BAAI/bge-small-en-v1.5` **[G4]**, revisão registrada, **sem o prefixo de instrução de consulta** | Grátis e reproduzível; a tarefa é ticket contra ticket (simétrica), e o prefixo do BGE é para consulta curta contra passagem |
| LangChain | Embeddings, vector store `langchain-postgres` e retriever | Requisito da vaga; ver o ponto fraco 6 |
| LLM | `claude-haiku-5-5` via `langchain-anthropic`, saída validada com Pydantic, `max_tokens` 64, sem `temperature` | Mesmo modelo do case |
| Agente | LangGraph, grafo fixo; no nó `sugerir`, o LLM recebe `recuperar_exemplos` e `consultar_politica` via `bind_tools` e decide se chama **[G7]** (D-F3-1: recuperação vetorial) | Tool calling real onde há escolha; a faixa continua sendo atribuída por código |
| Telemetria | `LANGCHAIN_TRACING_V2` desligado | Nenhum texto de ticket vai para serviço externo |

## 6. Custo de API (premissa; preço a reconferir na página oficial antes da F2)

- **Base:** o case mediu cerca de 1.350 tokens de entrada e 24 de saída por chamada, ou US$ 0,1508 por 1.000 tickets, a US$ 0,10/MTok de entrada e US$ 0,50/MTok de saída (página oficial, 2026-11-03).

| Item | Chamadas | Estimativa |
|---|---|---|
| V0, V1, V2 e V3 × 400 | 1.600 | ~US$ 0,24 |
| Sensibilidade a k (V2, k = 3 e k = 10) | 800 | ~US$ 0,12 |
| V0z (se aprovado) | 400 | ~US$ 0,05 |
| Agente: 211 tickets × (1 + 5 ataques), só os que chegam ao LLM, com até 3 rodadas por ticket por causa do tool calling | ≤ 3.798 | ≤ US$ 0,60 |
| **Total estimado** | | **< US$ 1,10** (teto de US$ 3) |

O teto não é a restrição. A restrição é o tempo.

## 7. Orçamento de tempo

| Fase | Plano original (min) | Proposta (min) | Observação |
|---|---|---|---|
| F0 | 20 | 20 | |
| F1: ambiente, Docker, dados, índices, testes | 75 | **105** | Instalação do torch/Docker e checagem de integridade |
| F2: V0, V1, K1, C | 60 | 60 | |
| F3: V2, V3, qualidade de recuperação | 75 | 75 | |
| F4: agente | 90 | 90 | |
| F5: avaliação do agente | 45 | 45 | |
| F6: README e docs | 45 | 45 | |
| F7: MCP (opcional) | 30 | **0 (cortado)** | **[G5]** |
| Folga | 20 | 20 | |
| **Total** | **460** | **460** | |

- **Risco declarado:** o case orçou 6 h e levou cerca de 10 h. Na mesma proporção, este plano levaria 12 a 13 h.
- Ao passar de 120% numa fase: parar e cortar.
- **Ordem de corte proposta:**
  1. F7;
  2. sensibilidade a k;
  3. V0z;
  4. a rodada de LLM de V2. Q2 continua respondida pela qualidade de recuperação e por K1, sem custo.
- **V1 não é cortado:** sem ele, Q1 não separa "exemplos ajudam" de "vizinhos ajudam" **[G5]**.

## 8. Fora do escopo

- Fine-tuning, reranker, comparação entre modelos de embeddings e ajuste de índice ANN.
- Interface, deploy e outros datasets.
- LangSmith ou qualquer telemetria externa.
- Qualquer coisa da BIM, de clientes ou de outras submissões do G4.
- Qualquer alteração no fork, no PR #228 ou na pasta do case, que é só leitura.
- Versionar o CSV bruto.

## 9. Segurança e git

- A chave fica só em `.env`, que está no `.gitignore`. Nunca em log, saída, report ou teste.
- Sem CSV bruto no repositório. Versionados: `f1_splits.csv`, `amostra_400_ids.csv` e as predições do case por id (sem texto).
- Um commit local por fase, depois de os testes passarem. **Push só por decisão do Gustavo.**
- O README declara a extensão pessoal, com link para o PR #228. Os commits mostram as datas reais.

## 10. Decisões do portão F0 (Gustavo, 2026-11-17)

| # | Decisão |
|---|---|
| G1 | Repositório em `C:\Users\gusta\triagem-tickets-rag-agente`, criado e conectado pelo Gustavo |
| G2 | Docker Desktop + WSL2. **Plano B:** se o Docker falhar na F1, Supabase com pgvector, sem Docker. A troca fica registrada em `docs/decisoes.md` e no README, com as consequências: os textos de treino vão para um serviço externo (o DS2 é público, CC0); a latência inclui rede e não é comparável; a reprodução deixa de ser um `docker compose up` |
| G3 | V0 = "prompt do case (8 exemplos)". V0z só se houver folga |
| G4 | `BAAI/bge-small-en-v1.5`, sem comparação com outros modelos |
| G5 | F1 com 105 min; F7 cortada; V1 sempre mantido; o corte de LLM começa pelo V2 |
| G6 | MIT |
| G7 | Grafo fixo. No nó `sugerir`, tool calling real: o LLM recebe `recuperar_exemplos` e `consultar_politica` via `bind_tools` e decide chamá-las. Cada tool call fica no log. A guarda "nunca promove" fica no código. Detalhes na spec da F4 |
| G8 | RRF própria; se o `langchain-postgres` tiver híbrida nativa, citar e não usar |
| — | Split já conferido no PR #228: 38.270 treino e 9.567 holdout. O assert da F1 fica como checagem de integridade |
| — | Comparações (McNemar + Holm) resumidas em **uma única tabela** no README |

### Requisitos que G7 cria para a spec da F4

- **Limite de rodadas:** no máximo 3 rodadas de tool calling por ticket. Ao estourar, `escalar_humano`.
- **`max_tokens` maior que os 64 do case:** uma chamada de tool não cabe em 64. O valor fica fixado na spec da F4.
- **Os argumentos das tools vêm do LLM e são dado não confiável:**
  - `recuperar_exemplos` ignora qualquer texto que o LLM passe e consulta sempre com o texto mascarado do próprio ticket;
  - `consultar_politica` aceita só uma categoria da lista fechada; fora dela, erro de tool.
- **Log:** nome da tool, argumentos (sem texto de ticket, só ids e categorias), resultado resumido, latência e rodada.
- **Separação de Q1:** no agente, o LLM decide quando recuperar exemplos, então a condição RAG varia por ticket. Os números do agente **não** entram na tabela de Q1; Q1 vem só de V0 a V3, com prompt fixo.
