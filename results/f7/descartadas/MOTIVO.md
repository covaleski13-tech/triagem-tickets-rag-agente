# Execuções descartadas da F7 (2026-11-25)

`execucoes_146.jsonl`: as primeiras 146 de 804 execuções da avaliação LangGraph × ADK (73 por implementação),
interrompidas às 17:41.

- **Motivo:** questão de ambiente, não do framework. O Kaspersky Anti-Virus da máquina interceptava parte das
  conexões TLS para `api.anthropic.com` (certificado "Kaspersky Anti-Virus Personal Root Certificate"). O LiteLLM
  (lado ADK, verificação com certifi) rejeitava essas conexões: 42 das 73 execuções ADK tiveram erro
  `InternalServerError: TLS` e 27 escalaram por "erro de API". O lado LangGraph teve 0 erros.
- **Correção:** o Gustavo excluiu `api.anthropic.com` da inspeção HTTPS do Kaspersky; o ajuste de TLS no ADK foi
  removido (cada implementação com a verificação padrão dela) e as 804 rodaram do zero (F7-report §5).
- Estes números não entram em nenhuma métrica. O custo entra no custo da F7 (`docs/custos.md`).
