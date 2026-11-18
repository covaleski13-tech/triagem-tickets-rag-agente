# F6 — Correção pós-revisão independente

**Origem:** revisão só leitura numa sessão nova do Claude Code, em 2026-11-18, sobre o HEAD `effdc6b`. Os achados são citados pelo código da revisão (A1, M2, Q4.3…).
**Orçamento:** 40 min. Ao passar de 120% (48 min), pare e reporte.
**Hora de início:** anote o relógio ao começar.
**Agente, prompts, guarda, política e `results/` existentes: sem mudança.** A única medição nova é a do passo 2, aprovada pelo Gustavo.

## 1. Registro das mudanças de critério (A1, A3)

Em `docs/decisoes.md`, acrescente a seção "Critérios: o que mudou entre a F0 e a execução", com data e motivo, **sem reescrever nada**:

- **Concordância de faixa com `triar()` = 100% (F0 §2, Q3).**
  - Ficou incompatível com a regra "divergência rebaixa", aprovada pelo Gustavo na F4. A faixa final pode ficar abaixo da do case por desenho.
  - Substituída na F5 por "faixa final nunca acima da do case", e a taxa de rebaixamento passou a ser medida.
  - A spec da F5 fez a troca sem registro. Registre agora.
- **"Falha simulada por tool → 100%" virou "100% das exercitadas"** na F5-spec. O LLM nunca chamou `consultar_politica`, então a meta da F0 **não foi medida** para essa tool.
- **A regra de decisão da Q2** ("IC de híbrida − vetorial inteiro acima de 0") não estava na F0, que só tinha a hipótese. Ela entrou na F3-spec.
  - O `vizinhos_400.csv` já estava versionado desde a F2, então a precisão@5 do recorte era calculável antes da regra.
  - O resultado foi negativo, e a regra não o favorece. Mesmo assim, ela **não é pré-registro verificável**.
- **Ordem dos commits:**
  - o `F0-escopo.md` entrou em `6dc8e3b`, antes de qualquer resultado de LLM (F2 em `dca94e9`);
  - a partir da F2, cada spec entrou no mesmo commit dos resultados da fase. Por isso o git não prova que a spec veio antes da execução dentro da fase.

## 2. Medição complementar das falhas (A2), com custo de API

- **Problema:** as 30 falhas injetadas da F5 rodaram em tickets "humano decide". Escalar não mudava a faixa, e só o campo de causa provava o caminho de erro.
- **Complemento:**
  - 10 tickets do estrato "IA sugere" de `results/f5/amostra_q3.csv`, os 10 primeiros por `id`;
  - as mesmas falhas da F5: exceção em `recuperar_exemplos`, exceção em `consultar_politica` e timeout de 0,001 s;
  - script e definições da F5, sem mudança;
  - `event_id` `f5c-{id}-{falha}` e pasta de runtime própria.
- **Antes de rodar:** estime o custo e registre em `docs/custos.md`.
- Grave em `results/f5/falhas_injetadas_ia_sugere.csv`, com a mesma estrutura de `falhas_injetadas.csv`.
- **Métrica, para as exercitadas:** `faixa_final == "humano decide"`, com `faixa_politica == "IA sugere"` e causa "escalado".
- Uma rodada, sem repetição. O veredicto é recalculado com as duas tabelas e gravado num campo novo de `veredicto_q3.json` (`veredicto_com_complemento`). O campo antigo **não muda**.

## 3. README

**Topo (A1, Q5.1):**
- Logo abaixo da primeira linha, deixe explícito: "O agente **não é recomendado para produção**. Ele existe para medir a Q3. Em acurácia, o classificador clássico é melhor que qualquer variante com LLM (Q1), e quase todo rebaixamento do agente foi alarme falso (6 de 7, n pequeno)."
- **Troque** "critérios registrados antes de qualquer execução" por uma frase verdadeira:
  - o escopo e os critérios de Q1 estão no `F0-escopo.md`, commitado antes dos resultados de LLM;
  - as regras de cada fase estão nas specs, commitadas junto com os resultados;
  - as mudanças de critério estão em `docs/decisoes.md`.

**Veredicto de Q3 (A1, A2).** Substitua "agente seguro" sem qualificação por:
- "guarda: 0 promoções em N execuções (por construção)";
- "falhas: X/Y exercitadas escalaram (por tool, por faixa)";
- "não medido: falha real de `consultar_politica`, porque o LLM nunca a chamou".

**Origem dos números (M2):**
- **Corrija** a frase "todo número sai de `results/` ou `custos.md`". Ela passa a dizer: números do case citam o PR #228 ou o arquivo copiado do case; números de reports citam o report.
- Acrescente a fonte em cada número listado no M2: 6.395, 3,82%, 46,7%, 0,64/0,71, 85,07%, ranks 204–1.277, "3 de 7", "3 de 826" e "~27 min".

**Métricas que faltam (M3):**
- Q1: latência p95 na tabela de variantes; matrizes de confusão por link para `results/f3/metricas_f3.json`.
- Q3: custo por 1.000 execuções.

**Como rodar (Q4):**
1. Ative o `.venv` (Windows e Unix) logo após criá-lo. Os comandos seguintes assumem o venv ativo.
2. Kaggle: exige conta e login; o arquivo vem compactado; diga o nome do arquivo depois de descompactado. Inclua o download pelo `kaggle` CLI como alternativa, só se o comando for conferido na documentação oficial. Se não for, não inclua.
3. Reordene: `docker compose up -d` → `f1_integridade.py` (modelo, 41,5 s) → `f1_indexar.py` (baixa o BGE do Hugging Face; cerca de 15 min; rede necessária) → `pytest` → `pytest -m db`.
4. Diga que `pytest` precisa do CSV bruto e do modelo do `f1_integridade.py`.
5. Caminho "conferir sem reexecutar", **antes** dos scripts de fase: `python scripts/f6_conferir_readme.py` e `python scripts/f6_somar_custos.py`.
6. Aviso único: **todo** script de fase sobrescreve `results/`, com ou sem API. Para conferir, use o caminho do item 5.
7. F3b: cerca de 80 min, usa o mesmo Postgres; não rode testes `db` ao mesmo tempo.
8. `.env`: além da chave, define `DATA_DIR`. Sem ele, o código do case resolve caminhos fora do repositório (B2). Mantenha o `.env` criado a partir do `.env.example`.
9. Sistema: "testado só no Windows 11 com Docker Desktop". Retire qualquer promessa de macOS ou Linux não testada (B1).

**Limitações (acrescente):**
- Tools sem timeout: uma levou 38,5 s antes do erro (B4).
- `InvalidRequestError` com threads continua sem diagnóstico.
- Uma rodada por variante: a variação entre rodadas foi medida só em V0.
- O golden do case tem PII **sintética** (nome, e-mail `example.com`, telefone e CPF fictícios), usada para testar o mascaramento (B3).
- O conferidor do README testa presença do número no texto, não a célula da tabela (M4).

## 4. Correções pequenas de código e dados

- **M1:** tire o e-mail pessoal de `docs/planning/F6-report.md`. Troque por "e-mail pessoal do autor". O histórico do git continua com o e-mail; isso já foi decidido pelo Gustavo.
- **B1:**
  - acrescente ao `requirements.txt`, com a versão instalada, todo pacote importado diretamente no código ou nos testes que não estiver lá. Confira por script, comparando os `import` com o `requirements.txt`;
  - a linha do `torch` com `+cpu` fica, com um comentário no README dizendo que é a wheel de CPU para Windows e Linux.
- **B2:** em `src/triagem_rag/politica_caso.py`, defina `DATA_DIR` padrão (`os.environ.setdefault`) apontando para o `data/` do repositório, **antes** de importar o `comum` do case.
  - Teste: sem `DATA_DIR` no ambiente, o adaptador resolve para `data/` do repositório.
  - Não altere `caso/*.py`.

## 5. Instalação limpa (M5)

- Faça um clone temporário fora do repositório.
- Crie um **`.venv` novo** e rode `pip install -r requirements.txt`, registrando o tempo.
- Copie só o CSV bruto e um `.env` criado a partir do `.env.example`, sem chave.
- Rode `f1_integridade.py`, `pytest` e `pytest -m db`. O `pytest -m db` usa o Postgres já indexado.
- **A indexação do zero (`f1_indexar.py`) não roda**, para não sobrescrever o índice do trabalho. O README registra: "indexação validada na F1; não reexecutada na checagem de clone".
- Apague a pasta temporária no fim.

## Fechamento

- Rode `scripts/f6_conferir_readme.py` (sem faltantes), `pytest`, `pytest -m db`, `git diff --cached` e `git ls-files --eol`.
- Commit local: `F6: correções da revisão independente; falhas injetadas em IA sugere`. Sem push.
- Na seção "Correção pós-revisão" do `F6-report.md`, inclua:
  - a tabela achado → o que foi feito ou por que não;
  - o resultado do complemento de falhas;
  - o custo.
- Pare.

## Fora desta correção (registrar como não feito, com motivo)

- **M4:** reescrever o conferidor para checar célula por célula. Custo de tempo maior que o ganho; registrado como limitação.
- **B4 e o `InvalidRequestError`:** corrigir exigiria mudar o agente, que está congelado. Registrado como limitação.
- **A3:** não há como provar retroativamente a ordem dentro das fases. Registrado de forma explícita.
