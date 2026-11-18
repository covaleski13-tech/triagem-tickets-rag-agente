# F6 — README, documentação final e checagem de reprodutibilidade

**Pré-requisito:** portão F5 aprovado em 2026-11-18 (commit `622562f`).
**Orçamento:** 45 min. Ao passar de 120% (54 min), pare e reporte.
**Hora de início:** anote o relógio ao começar (`CLAUDE.md` §8).
**Sem chamadas de API.** Nenhum experimento novo, nenhum número novo: só o que já está em `results/`.

## Objetivo

Deixar o repositório pronto para o Gustavo decidir o push:

- README que um avaliador técnico leia em 5 minutos e consiga verificar;
- documentação de decisões e custos fechada;
- prova de que um clone limpo roda.

## Regras de redação

- **Todo número do README sai de um arquivo de `results/` ou de `docs/custos.md`.** Cada tabela indica a fonte na legenda (caminho do arquivo).
- **Nenhum arredondamento que mude o sentido.**
  - Acurácia com 2 casas, em %;
  - diferenças em pp com 1 ou 2 casas;
  - p-valores em notação científica.
- **Resultado negativo vem com o mesmo destaque do positivo.** Proibido: "quase significativo", "tendência", "promissor", "robusto" sem número.
- **Rótulos obrigatórios:**
  - "exploratório" em todo número fora dos critérios pré-registrados;
  - "por construção" na garantia de 0 promoções.
- **Nenhuma afirmação sobre a experiência profissional do Gustavo** (`CLAUDE.md` §9). Nada de "em produção", "em clientes" ou nomes de empresas.
- **Nada da BIM, de clientes ou de outras submissões do G4.**
- Português, frases curtas e diretas, sem marketing.

## README.md (substitui o mínimo da F1)

Seções, nesta ordem:

1. **Título e uma linha:**
   - "Extensão pessoal do case técnico do G4 (PR #228): RAG, busca híbrida e agente com tool calling, medidos contra baseline e controle";
   - link do PR;
   - "não faz parte da submissão ao G4".
2. **As 3 respostas, em números.** Uma frase por pergunta com o veredicto pré-registrado, seguida da evidência mínima:
   - **Q1** (`results/f3/familia_q1.csv`, `results/f3/veredictos.json`, `results/f3/metricas_f3.json`):
     - tabela das 6 variantes: acertos, acurácia, Wilson 95%, macro-F1, custo por 1.000, latência p50;
     - a **tabela única da família**: comparação, diferença em pp, b, c, p bruto, p de Holm;
     - os três veredictos.
   - **Q2** (`results/f3/q2_recuperacao.json`, `results/f3/q2_diferencas.csv`):
     - precisão@5 e K1 por recuperador, nos dois universos (amostra de 2.000 e recorte dos 400), lado a lado e sem misturar;
     - diferenças pareadas com IC;
     - veredicto;
     - exploratório: K1 vetorial × clássico nos mesmos 2.000.
   - **Q3** (`results/f5/veredicto_q3.json`, `results/f5/q3.json`, `results/f5/q3_por_ataque.csv`, `results/f5/falhas_injetadas.csv`):
     - veredicto, com a ressalva de `consultar_politica` (0/10 exercitada em execução real);
     - falhas por tipo;
     - desvio sob ataque (total e por ataque, com Wilson);
     - rebaixamento por estrato e ponderado;
     - os 6 de 7 rebaixamentos com o clássico certo, **sem virar taxa**;
     - dano silencioso no clássico, rotulado "sem LLM";
     - uso de tools.
3. **O que falhou ou contrariou a hipótese.** Lista curta, cada item com número e link para o report da fase:
   - V1 não superou V0;
   - K1 superou V3 (o LLM piora o voto dos vizinhos);
   - nenhuma variante alcançou o clássico;
   - a híbrida perdeu para a vetorial nos dois universos;
   - superprevisão de Access;
   - full-text sem normalização (emenda F1);
   - texto em volta do JSON com tools e as duas emendas da F4;
   - paralelismo que não acelerou a F3b;
   - SHA-256 calculado sobre a cópia CRLF (F1);
   - `InvalidRequestError` com 4 threads (F5).
4. **Arquitetura.**
   - Diagrama em Mermaid (o GitHub renderiza) com:
     - entrada;
     - `triar()` do case (mascaramento, idempotência, clássico, política);
     - roteamento;
     - nó `sugerir`, com as 3 tools (`recuperar_exemplos` vetorial, `consultar_politica`, `responder`);
     - guarda;
     - faixa final.
   - Abaixo do diagrama, uma tabela "onde o LLM escolhe / onde o código decide".
   - Componentes, cada um com a versão fixada:
     - Postgres + pgvector, com tag e digest;
     - `bge-small-en-v1.5` e a revisão;
     - LangChain, LangGraph e `langchain-anthropic`;
     - `claude-haiku-5-5`.
5. **Como rodar.** Passo a passo:
   1. clonar;
   2. criar o `.venv` e rodar `pip install -r requirements.txt`;
   3. baixar o DS2 (link do Kaggle, nome do arquivo, destino `data/raw/`, SHA-256 esperado de `docs/origem.md`);
   4. `docker compose up -d`;
   5. copiar `.env.example` para `.env` e preencher `ANTHROPIC_API_KEY`, só para as fases com API;
   6. `pytest` (sem banco e sem chave), `pytest -m db` e, com ressalva de custo, `pytest -m api`;
   7. scripts por fase, na ordem, com tempo e custo de referência de cada um, tirados dos reports e de `docs/custos.md`.
6. **Custo total de API do projeto**, com o detalhe por fase (`docs/custos.md`) e o preço com data e URL.
7. **Limitações.** Os itens de "O que falhou" não se repetem aqui.
   - Texto do DS2 pré-processado.
   - Teto de ruído de rótulo:
     - 3,82% de discordância entre quase-duplicados;
     - 46,7% de concordância do revisor externo do case.
   - Os 400 vêm do limiar antigo (`p_max < 0,74`).
   - LLM não determinístico: uma rodada por variante, com a variação medida só em V0 (88,25% de predições iguais às do case).
   - Q3 com estratos de tamanho igual e taxas ponderadas.
   - `consultar_politica` sem falha exercitada em execução real.
   - Normalização 2 do full-text favorece documentos curtos.
   - n pequeno nos rebaixamentos.
   - A instância `PGVector` é compartilhada entre threads, com a hipótese não verificada.
8. **Decisões registradas.**
   - Link para `docs/decisoes.md` e para `docs/planning/` (specs e reports por fase).
   - Uma tabela curta das decisões que mudaram o plano:
     - G4 (embeddings);
     - G7 (desenho do agente);
     - G9 (amostra da Q2);
     - D-F3-1 (busca vetorial);
     - D-F3-2 (papel do agente);
     - emenda da F1 (normalização 2);
     - emendas 1 e 2 da F4.
9. **Como foi feito.** Uma frase: o planejamento, a revisão e as decisões ficaram com o Gustavo, com apoio de um assistente de IA no chat do projeto; a execução foi do Claude Code, seguindo `CLAUDE.md` e as specs em `docs/planning/`. **Texto final sujeito à aprovação do Gustavo (ver §7 do report).**
10. **Dados, licença e reuso.**
    - DS2 (Kaggle, CC0): não redistribuído; só ids e splits.
    - Código e artefatos reaproveitados do PR #228, com a proveniência por blob em `docs/origem.md`.
    - Licença MIT.

## Documentação

- **`docs/decisoes.md`:** confira que tem todas as decisões e emendas acima, com data e evidência. Complete o que faltar a partir dos reports. Não reescreva o histórico.
- **`docs/custos.md`:** total final do projeto, com a soma conferida por script a partir das linhas de custo real de cada fase.
- **`docs/planning/F0-escopo.md`:** **não alterar**. É o pré-registro; as emendas ficam em `decisoes.md`.

## Checagens

1. **`scripts/f6_conferir_readme.py`:**
   - lê os arquivos de `results/` e `docs/custos.md`;
   - confere que cada número-chave aparece no README com a formatação usada. Números-chave:
     - acurácia das 6 variantes;
     - p de Holm das 4 comparações;
     - os 3 veredictos de Q1;
     - precisão@5 dos 3 recuperadores nos dois universos;
     - diferença híbrida − vetorial nos dois universos;
     - veredicto e falhas por tipo de Q3;
     - desvio total;
     - rebaixamento ponderado;
     - dano silencioso;
     - custo total.
   - Saída: lista de faltantes. Esperado: vazia.
   - Teste `test_readme_numeros` chama o script.
2. **Clone limpo:**
   - `git clone` do repositório local para uma pasta temporária fora do repositório;
   - copie só `data/raw/all_tickets_processed_improved_v3.csv`, como um usuário faria depois do download;
   - rode `pytest` e `pytest -m db` com o interpretador do `.venv` existente. As dependências são as do `requirements.txt`; registre que não houve `pip install` novo.
   - Esperado: os mesmos resultados do repositório de trabalho.
   - Qualquer falha por arquivo não versionado é um defeito: corrija e registre.
   - Apague a pasta temporária no fim.
3. **Links:** todo link relativo do README aponta para um arquivo que existe. Faça uma checagem por script.
4. **Segredos e dados:**
   - `git grep` por `sk-ant`, `ANTHROPIC_API_KEY=` com valor e `PG_DSN` com senha diferente da do compose;
   - nenhum arquivo de `data/raw/`;
   - nenhum `*.joblib`;
   - nenhum log com texto livre do LLM: o `diagnostico_json.jsonl` continua fora do git.
5. **Autoria dos commits:** liste `git log --format='%an <%ae>' | sort -u` no report. **Não altere nada.** Se aparecer um e-mail pessoal, é decisão do Gustavo antes do push, porque mudar exigiria reescrever o histórico, o que é proibido sem ordem expressa.
6. `git ls-files --eol` sem `w/crlf`.

## Fechamento

- Rode `pytest` e `pytest -m db`.
- Confira `git diff --cached`.
- Commit local: `F6: README, decisões, custos e checagem de clone limpo`. **Sem push, sem criar remoto.**
- Escreva o `F6-report.md` no formato do `CLAUDE.md` §8. Na §7, liste:
  - o texto final da seção "Como foi feito", para aprovação;
  - os e-mails de autor encontrados;
  - a pergunta: README só em português ou com um resumo em inglês;
  - o próximo passo: revisão independente (abaixo) e, depois, a decisão de push.
- Pare.

## Depois da F6: revisão independente (não é tarefa desta execução)

O Gustavo abre **uma sessão nova** do Claude Code, sem o histórico deste projeto, e pede uma revisão só leitura com este roteiro:

1. Cada número do README bate com o arquivo citado?
2. Algum veredicto está mais forte do que o critério pré-registrado em `F0-escopo.md` permite?
3. Algum dado, segredo, texto de ticket, nome de empresa ou afirmação sobre experiência profissional no repositório?
4. Um avaliador consegue rodar a partir do README sem perguntar nada?
5. O que um avaliador de vaga de Engenharia de IA júnior questionaria primeiro?

O resultado volta para o chat do projeto antes do push.

## Não faça

- Rodar experimentos, chamar a API ou recalcular métricas com outra definição.
- Mudar `results/`, o agente, os prompts ou o `F0-escopo.md`.
- `git push`, criar remoto, `git commit --amend` ou reescrever histórico.
