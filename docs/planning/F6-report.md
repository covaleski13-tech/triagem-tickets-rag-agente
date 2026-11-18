# F6 — Report

Status: **concluída.** O README foi reescrito e todos os seus números conferem por script com `results/` e
`docs/custos.md`. As decisões e os custos estão fechados. O clone limpo passou depois de corrigir 2 defeitos (§5).
Sem chamadas de API. Commit local, sem push e sem remoto.

## 1. O que foi feito

1. Li os números-chave de `results/f3`, `results/f5` e `docs/custos.md`. Conferi a URL do DS2 no Kaggle por busca na web: não estava em nenhum arquivo do repositório, e a spec não libera ler o README do case.
2. Acrescentei ao `docs/decisoes.md`, sem reescrever nada, uma seção com G1 a G8 (as que mudaram o plano: G4, G5, G7 e G8), G9, a F3b, o corte da sensibilidade a k e o V0z não rodado.
3. Criei `scripts/f6_somar_custos.py`, que soma as 11 parcelas de custo real achadas literalmente em `docs/custos.md` e confere com o último acumulado. Acrescentei o total final ao `custos.md`.
4. Reescrevi o `README.md` com as 9 seções da spec.
5. Criei `scripts/f6_conferir_readme.py`, que confere os números-chave e os links relativos, e `tests/test_f6.py`.
6. Fiz o clone limpo (clone local + o que estava em stage, numa pasta temporária, só com o CSV bruto copiado), achei 2 defeitos, corrigi e repeti até passar. Apaguei a pasta no fim.
7. Fiz as checagens de segredos, dados, fins de linha e autoria, rodei os testes e fiz o commit.

## 2. Resultados

| Checagem | Resultado | Fonte |
|---|---|---|
| Números-chave no README | nenhum faltante (acurácia das 6 variantes, p de Holm das 4 comparações, 3 veredictos de Q1, precisão@5 dos 3 recuperadores × 2 universos, híbrida − vetorial × 2, veredicto e falhas por tipo de Q3, desvio total, rebaixamento ponderado, dano silencioso, custo total) | `python scripts/f6_conferir_readme.py` |
| O conferidor acusa número trocado | sim (troca "45,25%" por "45,52%" → faltante) | `tests/test_f6.py::test_readme_numeros` |
| Links relativos do README | nenhum quebrado | `python scripts/f6_conferir_readme.py` |
| Custo total do projeto | ≤ US$ 0,4651878 = último acumulado (≤ US$ 0,465188); F2 0,103379; F3 ≤ 0,0794798; F4 0,006221; F5 0,276108 | `python scripts/f6_somar_custos.py` |
| `pytest` (repositório de trabalho) | 84 passed, 10 deselected | `.venv/Scripts/python -m pytest -q` |
| `pytest -m db` (repositório de trabalho) | 8 passed | `.venv/Scripts/python -m pytest -q -m db` |
| `pytest` (clone limpo, depois de `f1_integridade.py`) | 84 passed, 10 deselected | clone em pasta temporária, interpretador do `.venv` existente, sem `pip install` novo |
| `pytest -m db` (clone limpo) | 8 passed | idem; o Postgres e os índices são os mesmos do repositório de trabalho |
| Modelo gerado no clone | `modelo_d2522e1b9442.joblib`, com 8.139/9.567 no holdout e 278/400 | saída do `scripts/f1_integridade.py` no clone |
| `git grep` por `sk-ant` | só o texto dos checklists nas specs (F1, F2, F3, F4, F4-emenda, F5, F6) | `git grep --cached -n sk-ant` |
| `ANTHROPIC_API_KEY=` com valor | nenhum (só texto das specs) | `git grep --cached -nE "ANTHROPIC_API_KEY=.+"` |
| DSN com senha diferente da do compose | nenhum | `git grep --cached` por `postgres...://usuário:senha@` excluindo `triagem:triagem@` |
| `data/raw/`, `*.joblib`, `diagnostico_json.jsonl`, pastas de runtime no git | nenhum | `git ls-files --cached` |
| `git ls-files --eol` com `w/crlf` | 0 | `git ls-files --eol` |
| Autores dos commits | `Gustavo Covaleski <e-mail pessoal do autor>` | `git log --format='%an <%ae>' \| sort -u` |

## 3. O que contraria a hipótese ou a expectativa

- **O clone limpo não rodava só com o README original da F6.** Faltava o passo de gerar o modelo clássico, e um teste dependia do mtime dos arquivos (§5). As duas coisas foram corrigidas.
- **O nome do modelo muda num clone** (`d2522e1b9442` em vez de `f71cfd480a50`). É o mesmo efeito do CRLF da F1, registrado na F4. O modelo reproduz os mesmos acertos, e o adaptador lê a versão pelo nome do arquivo, então nada quebra. Isso ficou documentado no README.
- O resto bateu com o esperado.

## 4. Desvios da spec

- **Passo novo no "Como rodar"** (passo 6: `python scripts/f1_integridade.py` antes dos testes). A spec listava 7 passos, e o README tem 8. Sem esse passo, um clone não roda os testes (§5).
- **Link do Kaggle:** obtido por busca na web (resultado da página do dataset: CC0, 47.837 linhas, arquivo `all_tickets_processed_improved_v3.csv`). Não estava no repositório.
- **`docs/decisoes.md`:** G1 a G8 aparecem por referência à tabela do `F0-escopo.md` §10, com destaque só para as que mudaram o plano. A F0 não foi alterada.
- **Diferenças pareadas de Q2 no README:** usam "-" (hífen) como sinal, para o conferidor achar o mesmo texto do CSV. As diferenças em pp de Q1 usam "−".
- **Clone limpo com o que está em stage:** o clone de `HEAD` não teria os arquivos da F6. Apliquei o `git diff --cached --binary` sobre o clone, o que testa exatamente o conteúdo do commit.
- **Seção "Como foi feito":** usa o texto da spec, sujeito à sua aprovação (§7).

## 5. Erros e correções durante a execução

- **Defeito 1 do clone: modelo clássico ausente.**
  - No clone, `pytest` falhou na coleta (`AssertionError: esperado 1 modelo da F1 em data/modelos, achei 0`). Os `*.joblib` não são versionados, por regra, e o adaptador do agente exige o modelo.
  - Correção: o README ganhou o passo 6 (`python scripts/f1_integridade.py`, 41,5 s, sem API). O agente e o adaptador não mudaram.
- **Defeito 2 do clone: teste dependente de mtime.**
  - O `test_amostra_q3_estratos` (F5) comparava os mtimes de `amostra_q3.csv` e `agente_log.jsonl`. Num clone, eles refletem a ordem do checkout, e o teste falhou.
  - Correção: o teste agora confere a ordem no script, como a spec da F5 também admite. Ele verifica que `fase_estratos` tem `assert not LOG.exists()` e que o `main` chama `fase_estratos` antes de `executar`.
- **Regex do somador de custos:** a 1ª versão não achava a linha "Acumulado do projeto"; corrigida antes do uso.
- **README, 1º rascunho do passo 6:** a lista ficou com a numeração errada, e uma frase dizia que o `integridade.json` muda "só o tempo de treino" (também muda o nome do modelo). Corrigi as duas coisas antes do commit.

## 6. Custo de API

Fase: US$ 0 (sem chamadas). Acumulado do projeto: **≤ US$ 0,465188** de US$ 3 (`docs/custos.md`, conferido por `scripts/f6_somar_custos.py`).

## 7. Pendências e decisões que dependem do Gustavo

1. **Texto final da seção "Como foi feito",** para aprovação:
   > O planejamento, a revisão e as decisões ficaram com o Gustavo, com apoio de um assistente de IA no chat do projeto. A execução foi do Claude Code, seguindo o `CLAUDE.md` e as specs em `docs/planning/`.
2. **E-mail de autor nos commits:** todos os commits estão como `Gustavo Covaleski <e-mail pessoal do autor>`.
   - É um e-mail pessoal e ficará público no push. Não alterei nada.
   - Trocar exigiria reescrever o histórico, o que só acontece com ordem expressa sua.
   - Os commits também levam o trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
3. **Idioma:** o README fica só em português ou ganha um resumo em inglês?
4. **Próximo passo:** a revisão independente (sessão nova do Claude Code, só leitura, com o roteiro da `F6-spec.md`). Depois, a decisão de push.

## 8. Tempo gasto × orçado

- **Início:** 14:56:39 (`date` no início).
- **Fim:** 15:10:32 (`date` depois dos testes finais) + este report e o commit (horário no `git log`).
- **Total:** ~14 min com timestamp, de 45 orçados.

---

# Correção pós-revisão (`docs/planning/F6-correcao-spec.md`)

Status: **concluída.** Os achados da revisão independente sobre `effdc6b` foram corrigidos ou registrados como não
feitos, com motivo. O complemento de falhas em "IA sugere" rodou uma vez. O agente, os prompts, a guarda, a política e
os `results/` existentes não mudaram; o `veredicto_q3.json` só ganhou um campo novo. Commit local, sem push.

## 1. O que foi feito

1. **B1:** comparei os `import` diretos com o `requirements.txt` (`scripts/f6_conferir_imports.py`); faltava `httpx2==2.16.2`, que foi acrescentado.
2. **B2:** `politica_caso.py` define `DATA_DIR` padrão antes de importar o case, com teste em subprocesso sem `DATA_DIR`.
3. **A2:** rodei o complemento de falhas em "IA sugere" (`scripts/f5_avaliar.py --falhas-ia-sugere`, `event_id` `f5c-…`, runtime próprio), com o custo estimado antes. Acrescentei `veredicto_com_complemento` ao `veredicto_q3.json`.
4. **A1 e A3:** acrescentei ao `docs/decisoes.md` a seção "Critérios: o que mudou entre a F0 e a execução".
5. **README:** topo, Q3 por partes, origem dos números, p95, matrizes, custo por 1.000, "Como rodar" refeito e limitações (achados A1, A2, M2, M3, Q4, Q5.1, B1 a B4).
6. **M1:** tirei o e-mail pessoal deste report.
7. **M5:** fiz uma instalação limpa num caminho curto fora do repositório: clone, patch do stage, `.venv` novo, `pip install`, CSV bruto, `.env` sem chave, modelo e testes. Apaguei a pasta no fim.

## 2. Resultados

**Achado → o que foi feito:**

| Achado | O que foi feito ou por que não |
|---|---|
| A1 (critérios trocados sem registro; "agente seguro" sem qualificação; topo do README) | Registrado em `docs/decisoes.md`. O README agora traz o aviso de "não recomendado para produção", diz onde está cada critério e mostra o veredicto de Q3 por partes (guarda, falhas, não medido) |
| A2 (falhas só em "humano decide") | Complemento em "IA sugere" rodado (abaixo) e campo `veredicto_com_complemento`; o campo antigo não mudou |
| A3 (ordem spec × execução dentro da fase) | Registrado de forma explícita; não há como provar retroativamente |
| M1 (e-mail pessoal no F6-report) | Trocado por "e-mail pessoal do autor" no working tree. O histórico do git mantém o e-mail (decisão do Gustavo) |
| M2 (números sem fonte) | Fontes acrescentadas: 6.395, 3,82%, 46,7% (F0 §1–§2, PR #228); 0,64/0,71 (`data/caso/f8_faixas.json`); 85,07% (PR #228 e `results/f1/integridade.json`); ranks 204–1.277 (F1-report §3); "3 de 7" (`results/f4/diagnostico_resumo.json`); "3 de 826" (`results/f5/agente_log.jsonl`, F5-report §3); "~27 min" (F1-report §3). A frase "todo número sai de `results/`" foi corrigida |
| M3 (métricas faltando) | p95 na tabela de Q1, link para as matrizes em `results/f3/metricas_f3.json` e custo de US$ 0,2225 por 1.000 execuções em Q3 |
| M4 (conferidor checa presença, não célula) | **Não feito:** o custo de tempo é maior que o ganho. Registrado como limitação no README |
| M5 (instalação limpa) | Feita (abaixo) |
| Q4 (como rodar) | Ativação do `.venv`; Kaggle com conta, login e arquivo compactado; nova ordem (compose → modelo → índices → testes); requisitos do `pytest`; caminho "conferir sem reexecutar"; aviso único de sobrescrita; F3b ~80 min sem testes `db` ao mesmo tempo; `DATA_DIR` no `.env`; "testado só no Windows 11 com Docker Desktop" |
| Q4, `kaggle` CLI | **Não incluído:** a documentação oficial (`Kaggle/kaggle-cli`, `docs/README.md`) confirmou a autenticação, mas a busca não trouxe a sintaxe de `kaggle datasets download` |
| Q5.1 (recomendação de uso) | Aviso no topo do README |
| B1 (dependência faltando; promessa de Linux/macOS) | `httpx2==2.16.2` no `requirements.txt`; comentário da wheel `+cpu`; retirada a promessa de Linux/macOS |
| B2 (`DATA_DIR` do case) | `os.environ.setdefault("DATA_DIR", <repo>/data)` antes do import do case, com teste. `caso/*.py` não mudou |
| B3 (PII no golden) | README: PII sintética (nome, `example.com`, telefone e CPF fictícios) |
| B4 (tools sem timeout) | **Não corrigido:** exigiria mudar o agente congelado. README: `recuperar_exemplos` de 38,5 a 40,1 s antes dos 3 `InvalidRequestError` (`results/f5/agente_log.jsonl`) |
| `InvalidRequestError` | **Não corrigido:** mesmo motivo. Fica como limitação, sem diagnóstico |

**Complemento das falhas injetadas em "IA sugere"** (`results/f5/falhas_injetadas_ia_sugere.csv`; 10 primeiros ids do estrato; 15:33:16 → 15:34:39):

| Falha | Exercitada | Escalou (`faixa_politica` "IA sugere" → `faixa_final` "humano decide", causa "escalado") |
|---|---|---|
| `recuperar_exemplos` levanta exceção | 6/10 | 6 |
| `consultar_politica` levanta exceção | 0/10 | — (o LLM não chamou a tool) |
| Timeout do LLM (0,001 s) | 10/10 | 10 |

`veredicto_com_complemento` (`results/f5/veredicto_q3.json`, por `scripts/f5_metricas.py`):

- agente seguro;
- 0 promoções (principal + golden + as duas tabelas de falhas);
- **35/35** falhas exercitadas escalaram;
- não medido: a falha real de `consultar_politica` (0/20).

O `q3.json` e os campos antigos do `veredicto_q3.json` foram conferidos iguais ao commit anterior.

**Checagens:**

| Checagem | Resultado | Fonte |
|---|---|---|
| Conferidor do README | nenhum número faltante, nenhum link quebrado | `python scripts/f6_conferir_readme.py` |
| Imports × `requirements.txt` | nenhum faltante (depois de acrescentar `httpx2`) | `python scripts/f6_conferir_imports.py` |
| Custo total | ≤ US$ 0,4692028 = último acumulado (≤ US$ 0,469203) | `python scripts/f6_somar_custos.py` |
| `pytest` / `pytest -m db` (repositório de trabalho) | 85 passed / 8 passed | `.venv` do trabalho |
| Instalação limpa: `pip install -r requirements.txt` num `.venv` novo | 531 s, `pip check` sem conflitos | caminho curto `C:\Users\gusta\f6tmp` |
| Instalação limpa: `f1_integridade.py` | 8.139/9.567 e 278/400; modelo `modelo_d2522e1b9442.joblib` | clone + patch do stage, CSV bruto e `.env` sem chave |
| Instalação limpa: `pytest` / `pytest -m db` | 85 passed / 8 passed | `.venv` novo; o `pytest -m db` usou o Postgres já indexado |
| Segredos, dados, `w/crlf` | nada de `sk-ant`, `.env`, `data/raw/`, `*.joblib`, runtime ou `diagnostico_json.jsonl` no stage; 0 `w/crlf` | `git diff --cached`, `git ls-files --eol` |

## 3. O que contraria a hipótese ou a expectativa

- **`consultar_politica` não foi chamada também em "IA sugere"** (0/10). A meta da F0 para essa tool continua não medida, agora com 0/20.
- **Em "IA sugere", `recuperar_exemplos` foi exercitada em 6/10, contra 9/10 em "humano decide".** Nos outros 4, o LLM respondeu sem recuperar.
- **A primeira instalação limpa falhou** com `WinError 206` (caminho longo) dentro da pasta temporária profunda da sessão: os arquivos de licença do `torch` passam do limite de caminho do Windows. Num caminho curto, passou. O README ganhou o aviso.
- O resto bateu com o esperado: as falhas exercitadas escalaram e derrubaram a faixa, e o clone limpo reproduz os testes.

## 4. Desvios da spec

- **`scripts/f5_avaliar.py` foi parametrizado** (`fase_falhas` com estrato, arquivo e prefixo; padrões iguais aos da F5) e ganhou o modo `--falhas-ia-sugere`. As definições das falhas não mudaram. O complemento também grava o log do agente em `results/f5/agente_log_falhas_ia_sugere.jsonl`, separado.
- **Fonte de "3 de 826":** a spec pedia citar o número; citei `results/f5/agente_log.jsonl` e o F5-report §3.
- **Instalação limpa num caminho curto** (`C:\Users\gusta\f6tmp`), fora do repositório e fora do scratchpad, por causa do `WinError 206`.
- **O modelo BGE não foi baixado de novo na instalação limpa:** o cache do Hugging Face do usuário já o tinha, e a indexação não rodou, como manda a spec. Fica sem verificação, no clone, o download do zero.
- **Uma frase a mais no README:** o aviso de caminho curto, que nasceu da checagem de instalação.

## 5. Erros e correções durante a execução

- **1ª instalação limpa:** `WinError 206` no `pip install` do `torch`. Refeita num caminho curto, onde passou.
- **Varredura do e-mail:** a busca com `grep -r` pela pasta inteira passou do tempo limite (2 min), varrendo os CSVs de `data/`. Cancelei e troquei por `git grep` mais a busca nos `.md`: nenhuma ocorrência no working tree.
- **Busca de latências de tool:** a 1ª versão quebrou num `jsonl` antigo (`tool_calls` como lista de nomes). Corrigida com checagem de tipo.

## 6. Custo de API

| | Estimado | Real |
|---|---|---|
| Complemento de falhas em "IA sugere" | ≤ US$ 0,010 | **US$ 0,004015** (34.602 de entrada e 1.110 de saída) |
| **Acumulado do projeto** | | **≤ US$ 0,469203** de US$ 3 |

Fonte: `docs/custos.md`, conferido por `scripts/f6_somar_custos.py`.

## 7. Pendências e decisões que dependem do Gustavo

1. **Itens da §7 da F6 ainda abertos:** o texto de "Como foi feito", a pergunta sobre um resumo em inglês e a decisão de push.
2. **Não feitos, por motivo registrado:** M4 (conferidor por célula), B4 e o `InvalidRequestError` (exigem mudar o agente congelado) e A3 (sem prova retroativa).
3. **O e-mail pessoal continua no histórico do git** (commit `effdc6b` e autoria de todos os commits), como decidido.

## 8. Tempo gasto × orçado

- **Início:** 15:31:35 (`date` no início).
- **Fim:** 15:52:57 (`date` depois das checagens finais) + este report e o commit (horário no `git log`).
- **Total:** ~21 min com timestamp, de 40 orçados. Desse tempo, 531 s foram do `pip install` limpo, que rodou em paralelo com as edições.
