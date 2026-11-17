# CLAUDE.md — triagem-tickets-rag-agente

## 1. Seu papel

- Você é o **executor**. Quem planeja e revisa é o chat do Projeto. As decisões são do Gustavo.
- Cada fase começa com uma especificação em `docs/planning/F<n>-spec.md`. Execute **só** o que está nela.
- Ao terminar, escreva `docs/planning/F<n>-report.md` e pare. Não avance de fase nem adiante trabalho da fase seguinte.
- **Ordem de precedência:**
  1. pedido direto do Gustavo nesta sessão;
  2. `docs/planning/F<n>-spec.md` da fase atual;
  3. este CLAUDE.md;
  4. `docs/planning/F0-escopo.md`.
- Se houver conflito entre elas, pare e pergunte.
- Se a spec estiver ambígua, impossível ou contrariar os dados, **pare e reporte**. Não improvise uma solução alternativa.
- Se um pré-requisito faltar (Docker, pacote, dado), **pare e reporte**. Não troque a tecnologia por outra "equivalente" sem decisão do Gustavo.

## 2. O que é este repositório

- **Extensão pessoal posterior ao case técnico do G4** (PR #228: `https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228`).
- Responde 3 perguntas mensuráveis (ver `F0-escopo.md`):
  - **Q1:** RAG ajuda o LLM a classificar?
  - **Q2:** busca híbrida recupera melhor que só a vetorial?
  - **Q3:** um agente com tool calling executa a política do case sem violar as regras?
- **Toda tecnologia nova responde a uma pergunta, com baseline e controle.** Resultado negativo é publicado como achado. Não ajuste o experimento até o número "ficar bonito".

## 3. Regras invioláveis

- **Nenhum número inventado ou arredondado para agradar.** Todo número vem de código executado (cite o script e o arquivo de saída) ou de premissa rotulada como premissa.
- **Anti-vazamento:**
  - o índice de recuperação contém **só** `split_grupo == treino` de `data/f1_splits.csv`;
  - a avaliação usa o holdout por grupo e os **400 ids** de `data/amostra_400_ids.csv`;
  - nunca regenere os splits nem a amostra.
- **O LLM nunca promove.** Nenhum ticket em que o LLM tenha participado da decisão termina em "IA decide". Só a política do case (classificador clássico + `politica_implantada`) coloca um ticket nessa faixa.
- **Falha → humano.** Falha de LLM, timeout, JSON inválido ou erro de tool levam a `escalar_humano`, com no máximo 1 nova tentativa.
- **Texto do ticket é dado, nunca instrução:** entra delimitado e separado das instruções.
- **Teto de custo de API: US$ 3 no total.**
  - Antes de cada rodada paga, estime o custo e registre a estimativa em `docs/custos.md`.
  - Depois da rodada, registre o custo real, calculado pelos tokens.
  - Pare se o acumulado mais a estimativa passar de US$ 3.
  - O preço vem da página oficial da Anthropic, citada com a data. Nunca use preço de memória.
- **Seed fixa (42)** em tudo o que for aleatório.

## 4. Dados e origem

- **DS2 apenas** (IT Service Ticket Classification, Kaggle, CC0). O CSV bruto fica em `data/raw/` (no `.gitignore`), e o caminho é configurável por `DATA_DIR`.
- **Podem ser versionados:** `data/f1_splits.csv` (ids e split) e `data/amostra_400_ids.csv` (só ids).
- **Limitação conhecida:** o texto do DS2 vem pré-processado (minúsculas, palavras funcionais removidas; medido na F1 do case). Isso afeta embeddings, full-text e LLM.
- **Código e artefatos reaproveitados do case** ficam listados em `docs/origem.md`: caminho original, commit `3a880f2` e SHA-256 de cada arquivo.
- **Proibido:** dados ou textos da BIM, de clientes ou de outras submissões do G4.

## 5. Padrões técnicos

- **Ambiente:**
  - Python 3.11+;
  - `requirements.txt` com versões fixas (`==`), as efetivamente instaladas;
  - Postgres + pgvector via `docker-compose.yml`, com a imagem oficial `pgvector/pgvector` numa tag fixa, cujo digest fica registrado;
  - plano B: Supabase com pgvector, só com autorização explícita do Gustavo depois de uma falha do Docker (F0 §10, G2).
- **Embeddings locais:** `sentence-transformers` com `BAAI/bge-small-en-v1.5`, sem prefixo de instrução, com nome e revisão registrados.
- **LangChain:** embeddings, vector store (pgvector) e retriever.
- **Busca híbrida:** full-text do Postgres + vetorial, fundidas por RRF em função própria e testada.
- **LLM:**
  - o Claude Haiku do case, via `langchain-anthropic`, com saída validada por Pydantic;
  - o Haiku 5.5 recusa `temperature` diferente do padrão: não envie `temperature` e registre que as saídas não são determinísticas.
- **LangGraph:** o agente, com tools `@tool`.
- **Scripts executáveis de ponta a ponta:** `python -m <módulo>` ou `python scripts/<x>.py`, com as saídas em `results/` (CSV/JSON, sem texto de ticket).
- **LangGraph, tool calling:** argumentos de tool vindos do LLM são dado não confiável. Valide-os contra listas fechadas e registre cada tool call no log, sem texto de ticket.
- **Métricas:**
  - acurácia com IC de Wilson 95% e macro-F1;
  - matriz de confusão;
  - **McNemar pareado** entre variantes, nos mesmos tickets;
  - custo por 1.000 tickets e latência p50/p95.
- **Testes:**
  - `pytest` passa sem chave e sem rede para a API;
  - testes que chamam a API real levam `@pytest.mark.api` e ficam fora da execução padrão;
  - testes que precisam do Postgres levam `@pytest.mark.db`.
- **Comentários:** só o porquê que o código não mostra.

## 6. Estrutura

```
triagem-tickets-rag-agente/
├── CLAUDE.md
├── README.md
├── LICENSE
├── docker-compose.yml
├── .env.example            ← sem segredo
├── requirements.txt
├── data/                   ← raw/ fora do git; f1_splits.csv e amostra_400_ids.csv versionados
├── src/triagem_rag/        ← código
├── scripts/                ← execuções por fase
├── prompts/                ← prompts versionados (v1 do case + novos)
├── results/                ← saídas numéricas por fase
├── tests/
└── docs/
    ├── origem.md
    ├── custos.md
    ├── decisoes.md
    └── planning/           ← F<n>-spec.md e F<n>-report.md
```

## 7. Git e segurança

- **Chave:**
  - fica só em `.env`, que está no `.gitignore`;
  - nunca a imprima em log, saída, relatório ou teste;
  - antes de cada commit, confira com `git diff --cached` que nem ela nem o CSV bruto entraram.
- **Commits:** um commit local por fase concluída, com mensagem descritiva em português, **só depois** de os testes passarem.
- **Proibido:** `git push`, criar repositório remoto, `git reset --hard`, reescrever histórico.
- **Proibido:** tocar em qualquer arquivo de `C:\Users\gusta\challenge-g4-ai-master\` além de **ler** os artefatos listados na spec.

## 8. Formato do `docs/planning/F<n>-report.md`

1. **O que foi feito:** passos executados, em até 10 linhas.
2. **Resultados:** tabela curta. Cada número indica o script e o arquivo de saída.
3. **O que contraria a hipótese ou a expectativa:** obrigatório. Se nada contrariou, diga isso.
4. **Desvios da spec:** o que mudou e por quê.
5. **Erros e correções durante a execução.**
6. **Custo de API da fase e acumulado.**
7. **Pendências e decisões que dependem do Gustavo.**
8. **Tempo gasto** × orçado na spec.

## 9. Não faça

- Avaliar no holdout qualquer coisa ajustada olhando o holdout (k, prompt, limiar, fusão).
- Trocar Postgres/pgvector por outro banco, ou o modelo de embeddings por outro, sem decisão.
- Usar LLM onde regra ou classificador resolve, sem medir a diferença.
- Escrever afirmações sobre a experiência profissional do Gustavo.
- Continuar quando a fase passar de 120% do tempo orçado. Pare e proponha o corte no report.
