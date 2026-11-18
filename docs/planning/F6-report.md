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
| Autores dos commits | `Gustavo Covaleski <covaleski13@gmail.com>` | `git log --format='%an <%ae>' \| sort -u` |

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
2. **E-mail de autor nos commits:** todos os commits estão como `Gustavo Covaleski <covaleski13@gmail.com>`.
   - É um e-mail pessoal e ficará público no push. Não alterei nada.
   - Trocar exigiria reescrever o histórico, o que só acontece com ordem expressa sua.
   - Os commits também levam o trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
3. **Idioma:** o README fica só em português ou ganha um resumo em inglês?
4. **Próximo passo:** a revisão independente (sessão nova do Claude Code, só leitura, com o roteiro da `F6-spec.md`). Depois, a decisão de push.

## 8. Tempo gasto × orçado

- **Início:** 14:56:39 (`date` no início).
- **Fim:** 15:10:32 (`date` depois dos testes finais) + este report e o commit (horário no `git log`).
- **Total:** ~14 min com timestamp, de 45 orçados.
