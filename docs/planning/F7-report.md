# F7 — Report: agente em Google ADK 2.0 e comparação com LangGraph (Q4)

## 1. O que foi feito

1. **Passo 0 (viabilidade):**
   - `.venv-adk` com `requirements.txt` + `requirements-adk.txt` (`google-adk==2.14.1`, `litellm==1.111.0`), `pip check`
     limpo e F1–F6 passando nele;
   - payload provado contra servidor HTTP falso;
   - `tool_choice` por rodada;
   - fumaça real de 1 ticket.

   Aprovado pelo Gustavo, com o adendo da spec e a opção (b) para custos.
2. **Agente ADK em `src/triagem_rag/adk/`** (`workflow.py`, `nos.py`, `tools_adk.py`):
   - grafo `START → deterministico → (sugerir → guarda | guarda)`;
   - `triar()`, `rota`, `no_guarda`, `executar_tool`, `_ler_responder`, prompt v2 e as declarações das tools vêm do
     `agente.py`, por import.
3. **`tests/test_f7.py`** (21 testes, só no `.venv-adk`): os 5 da spec e os requisitos 1–4 e 6 do adendo.
4. **Avaliação `scripts/f7_avaliar.py`:**
   - aquecimento;
   - 402 + 402 execuções intercaladas;
   - golden nas duas implementações;
   - 20 falhas injetadas no ADK.

   A 1ª rodada foi descartada por uma questão de ambiente (§5) e refeita do zero com autorização (opção a).
5. **Métricas `scripts/f7_metricas.py`:** `q4.json`, `q4_lado_a_lado.csv` e `esforco.json`.
6. **Fechamento:**
   - README (Q4, bloco de 30 segundos, Stack, Como rodar, custos, limitações);
   - `docs/decisoes.md`;
   - `docs/custos.md` (acumulado do projeto);
   - `f6_somar_custos.py` e `test_f6.py` (valor esperado).

## 2. Resultados

| Item | LangGraph | ADK 2.0 | Fonte |
|---|---|---|---|
| Promoções indevidas (402 + golden; ADK também nas 20 falhas) | 0 | 0 | `results/f7/q4.json` (`por_impl`, `falhas_injetadas_adk`) |
| Falhas exercitadas que escalaram | — (F5) | 16/16: `recuperar_exemplos` 6/10 exercitadas (4 não: o LLM não chamou), timeout 10/10; exceções `RuntimeError` e `Timeout` (LiteLLM) | `results/f7/falhas_injetadas_adk.csv`, `q4.json` |
| Paridade com LLM falso (30 tickets × 13 roteiros) | — | 100% (`faixa_final`, `motivo_final`, tool calls, erros, rodadas) | `q4.json` (`paridade_teste`), `tests/test_f7.py::test_paridade` |
| **Veredicto mecânico "ADK preserva a segurança"** | | **sim** | `q4.json` (`veredicto`) |
| Escalonamentos IA sugere → humano | 60/402 = 14,9% (11,8–18,7%) | 53/402 = 13,2% (10,2–16,8%) | `results/f7/q4_lado_a_lado.csv` |
| Causas | 60 divergência | 53 divergência | idem |
| Desvio para o alvo do ataque | 20/333 = 6,0% (3,9–9,1%) | 20/333 = 6,0% (3,9–9,1%) | idem |
| Tools por execução com LLM (sem `responder`) | 0,66 | 0,67 | idem |
| Com `recuperar_exemplos` / `consultar_politica` | 264/400 / 0/400 | 268/400 / 0/400 | idem |
| Rodadas 1 / 2 | 136 / 264 | 132 / 268 | idem |
| Latência p50 / p95 (402) | 1.701,3 / 2.608,2 ms | 1.859,8 / 2.869,4 ms | idem |
| Custo por 1.000 execuções | US$ 0,2933 | US$ 0,2989 | idem |
| Concordância da categoria sugerida | LangGraph hoje × F5: 370/400 = 92,5% (89,5–94,7%) | ADK × LangGraph hoje: 378/400 = 94,5% (91,8–96,3%) | `q4.json` (`concordancia_categoria`) |
| Erros de API, TLS ou conexão na rodada final | 0 | 0 | `results/f7/execucoes.jsonl` |
| Linhas de código | 135 do `agente.py` específicas do LangGraph | 215 em `src/triagem_rag/adk/` | `results/f7/esforco.json` |
| Contornos específicos do framework | — | 6, cada um com motivo | `results/f7/esforco.json` |
| `pytest` padrão / `-m db` | `.venv`: 85 passed, 1 skipped (`test_f7.py`) / 8 passed | `.venv-adk`: 106 passed / 8 passed | execução de 18:27:06 |
| `scripts/f6_conferir_readme.py` | números faltantes: nenhum; links quebrados: nenhum | | execução no fechamento |
| Pastas de runtime separadas | 402 chaves, só as próprias | 402 chaves, só as próprias | `results/f7/tempos.json` (`runtime`) |

## 3. O que contraria a hipótese ou a expectativa

- **O porte não saiu "de graça":** foram 6 contornos, 4 além dos 2 previstos no adendo.
  - Três defaults do ADK contrariavam regras do agente:
    - o `FunctionTool` devolve erro de argumento ao LLM;
    - o laço do `Agent` chama o modelo de novo depois de cada tool;
    - o `BaseLlm` é pydantic e copiava o registro da execução.
  - Os outros são o `include_contents="none"` e as regras por resposta num `BaseLlm`.
- **O ADK foi 158,5 ms mais lento na p50** (1.859,8 × 1.701,3 ms) e 261,2 ms na p95. É uma rodada e não foi testado,
  então não é achado de superioridade. Uma explicação possível, não verificada, é que o `Workflow`, o `Runner` e o
  `asyncio.run` são montados a cada execução.
- **Concordância ADK × LangGraph (94,5%) acima de LangGraph × LangGraph F5 (92,5%):** os ICs se sobrepõem. A
  comparação de mesmo dia (ADK × LangGraph hoje) não tem a mudança de dia que a outra tem.
- **Premissa de custo da spec:** cerca de US$ 0,00022 por execução. O real ficou em US$ 0,2933 e US$ 0,2989 por
  1.000 execuções (`q4_lado_a_lado.csv`). O total ficou dentro da estimativa feita a partir da F5.
- **Questão de ambiente, não do framework:** a inspeção HTTPS do Kaspersky interceptava parte das conexões para
  `api.anthropic.com` (§5). Não estava prevista.
- **`consultar_politica` continua sem uso real:** 0/800 execuções com LLM, nas duas implementações.

## 4. Desvios da spec

- **Contornos além dos 2 do adendo:** `ToolBruta`, regras por resposta em `ModeloSugerir` (`BaseLlm`), `reg: Any` e
  `include_contents="none"`. Todos estão em `results/f7/esforco.json` com motivo.
- **Declaração das tools:** vem da tool LangChain do `agente.py` (`convert_to_openai_tool`). Assim o JSON schema
  enviado é idêntico ao do LangGraph, o que o `test_payload_adk` confere. Nenhuma função de tool foi copiada.
- **Pastas de runtime:** com as duas implementações intercaladas no mesmo processo, `TRIAGEM_RUNTIME_DIR` (global)
  não serve. O script troca `triagem.runtime_dir` por uma função que lê uma `ContextVar` fixada por tarefa. A lógica
  do case não muda, e o fim da rodada confere 402 chaves próprias em cada pasta.
- **Log do ADK:** um erro de API com `CERTIFICATE_VERIFY_FAILED` ganha o sufixo `: TLS` no tipo (por exemplo,
  `erro de API (InternalServerError: TLS)`). É diagnóstico para a regra de parada; sem TLS, o formato é igual ao do
  LangGraph. Essas 2 linhas de `nos.py` entram nas 215 de código.
- **Paridade mais estrita que a spec:** compara também tool calls (sem latência), erros, rodadas, `categoria_llm` e
  chave, além de `faixa_final` e `motivo_final`. Os 13 roteiros são 6 próprios e 7 casos de falha da F4.
- **Testes reaproveitam o `test_f4.py`** por import: os 30 tickets do treino, o LLM falso, os roteiros e o
  `_payload` do LangGraph para comparar os corpos.
- **`requirements-adk.txt`** fixa as 112 dependências que o ADK e o LiteLLM trazem e que não estão no
  `requirements.txt`, e não só os 2 pacotes. Assim a instalação fica reproduzível.
- **Contagem de esforço:** não conta comentários, linhas em branco nem docstrings (`linhas_codigo`). As "linhas do
  `agente.py` específicas do LangGraph" são os defs que o ADK teve de reescrever em vez de importar, mais os imports
  de LangChain/LangGraph. A lista está em `esforco.json` e foi escolha minha.
- **Golden rodou nas duas implementações**, com resultados iguais caso a caso (`results/f7/golden.jsonl`).
- **Arquivos da F6 mudados no fechamento:** `scripts/f6_somar_custos.py` (3 parcelas da F7) e `tests/test_f6.py`
  (valor esperado 0,7611218), conforme o adendo.
- **`.gitignore`:** recebeu `.venv-adk/` e `runtime_f7/`.

## 5. Erros e correções durante a execução

- **Registro copiado pelo pydantic** (`ModeloSugerir.reg: dict`): a sugestão do LLM sumia e a guarda escalava por
  `TypeError`. Apareceu na 1ª prova com LLM falso e foi corrigido com `reg: Any`.
- **Prova com runtime reaproveitado:** o 2º ticket virou duplicado. Só afetou a prova; ela foi refeita com pasta limpa.
- **Kaspersky (ambiente):**
  - 1ª tentativa: o aquecimento ADK falhou com `InternalServerError` e o script parou antes da avaliação, como
    previsto.
  - Diagnóstico: o LiteLLM verifica com certifi e rejeitava conexões re-assinadas pelo "Kaspersky Anti-Virus Personal
    Root Certificate". O SDK do LangGraph não falhava.
  - Pus `ssl.create_default_context()` no LiteLLM. O aquecimento passou, mas a avaliação teve TLS em 42 das 73
    execuções ADK (27 escalaram). Parei em 146/804; os testes sem custo, com chave inválida, não reproduziam o erro.
  - Decisão do Gustavo (opção a): ele excluiu `api.anthropic.com` da inspeção HTTPS, e o ajuste de TLS saiu do ADK.
  - 20 + 20 handshakes (certifi e repositório do Windows) deram emissor Google Trust Services / WE1 em todos.
  - As 146 parciais estão em `results/f7/descartadas/` (`MOTIVO.md`). A nova rodada teve a regra de parada (3 ou mais
    erros de TLS ou conexão numa implementação) e terminou com 0 erros.
- **Checagem do aquecimento:** exigia `llm_rodou` nos 3 tickets, mas o 3º ticket do treino não chama o LLM. Agora
  exige 0 erros e o LLM rodando em pelo menos 1 ticket de cada implementação.
- **Acumulado da F7 escrito errado** (0,045837 em vez da soma 0,044488) no registro parcial de `docs/custos.md`.
  Conferido por script e corrigido antes de qualquer commit.
- **`git mv -k` num arquivo não versionado não move nada.** Refeito com `mv` e conferido (146 linhas).

**Sondas do passo 0** (fora do repositório, adendo 6):

| Sonda | O que mostrou |
|---|---|
| `sonda.py` | `tool_choice` em `http_options.extra_body` vai como chave literal `"extra_body"` no corpo, sem mesclar |
| `sonda2.py` | `tool_choice`/`parallel_tool_calls` no formato OpenAI geram os dicts exatos da Anthropic; dicts da Anthropic são recusados pelo LiteLLM ("follows the OpenAI spec"). Virou `test_payload_adk` |
| `sonda_wf.py` / `sonda_wf2.py` | `before_model_callback` + subclasse controlam as 3 rodadas no `Workflow`; sem `skip_summarization` há uma 4ª chamada com `responder` forçado |
| `sonda_wf3.py` | o system é só a instrução (sem texto de identidade do ADK) e o resultado da tool vai como `{"result": ...}` |
| `fumaca.py` | fumaça real: `recuperar_exemplos` + `responder` válido, 3.066/84 tokens |
| `prova_wf.py` | 1ª prova do workflow com LLM falso; achou o registro copiado pelo pydantic |
| `tls.py` | taxas de falha de TLS por configuração, com chave inválida (sem custo) |

## 6. Custo de API da fase e acumulado

| Parcela | Custo | Fonte |
|---|---|---|
| Fumaça do passo 0 | US$ 0,000349 | `docs/custos.md` |
| Rodada interrompida (146), aquecimentos avulsos e diagnóstico | ≤ US$ 0,044139 | idem; o "≤" vem de 6 execuções de diagnóstico sem contagem de tokens, pelo maior custo por execução do log |
| Avaliação final (804 + golden + 20 falhas + aquecimento) | US$ 0,247431 | idem, a partir de `q4.json` e `tempos.json` |
| **Total da F7** | **≤ US$ 0,291919** de US$ 1 | estimativa final: ≤ US$ 0,42 |
| **Acumulado do projeto** | **≤ US$ 0,761122** de US$ 3 | `scripts/f6_somar_custos.py` |

## 7. Pendências e decisões que dependem do Gustavo

- **Push:** é seu.
- **Segurança:** com a inspeção HTTPS do Kaspersky ligada para outros domínios, o tráfego, chaves incluídas, passa
  decifrado pelo proxy local do antivírus. `api.anthropic.com` agora está excluído.
- **Não exercitado em execução real:**
  - falha de `consultar_politica` no ADK: o LLM não chama a tool (0/800); só os testes com LLM falso cobrem;
  - 4 das 10 falhas de `recuperar_exemplos`, em que o LLM respondeu sem buscar.
- **As 2 linhas de marca TLS em `nos.py`:** podem sair agora que a interceptação foi removida. Ficaram porque a regra
  de parada usa a marca.

## 8. Tempo gasto × orçado

- **Início:** 16:46:24, relógio no início do passo 0 (`date`).
- **Pausas esperando decisão:**
  - 17:11 → 17:14, aprovação do passo 0;
  - cerca de 17:46 → 17:58, Kaspersky. O início da retomada é o `date` 17:58:22.
- **Avaliação final:** 18:02:14 → 18:09:43 (`date` do comando; `results/f7/tempos.json`: 431,6 s).
- **Métricas:** `results/f7/q4.json` às 18:13:07.
- **Fim:** horário do commit da F7.
- **Orçado:** 150 min (teto de 120%: 180 min).
- **Total:** de 16:46:24 até o commit, menos de 120 min de relógio, com as pausas incluídas.
