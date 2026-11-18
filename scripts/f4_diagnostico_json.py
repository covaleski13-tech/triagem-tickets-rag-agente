"""Emenda F4 (diagnóstico): roda o agente real, sem alterá-lo, nos 5 tickets do treino da fumaça e grava o texto bruto
de cada resposta do LLM em results/f4/diagnostico_json.jsonl. O LLM entra pelo parâmetro `llm=` de triar_agente,
envolvido num gravador que só repassa as chamadas. Antes de gravar, cada resposta passa pela checagem de nenhum
trecho de 30 ou mais caracteres do ticket (bruto ou mascarado); uma resposta reprovada não é gravada.
Histórico: rodou uma vez com o agente v1 (resposta final em JSON livre), antes da emenda `responder`.
`--resumo` regera results/f4/diagnostico_resumo.json a partir do jsonl, sem API."""
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))
os.environ["TRIAGEM_RUNTIME_DIR"] = tempfile.mkdtemp(prefix="diag_rt_")
os.environ["TRIAGEM_AGENTE_LOG"] = str(Path(tempfile.mkdtemp(prefix="diag_log_")) / "agente_log.jsonl")

from triagem_rag import agente  # noqa: E402
from triagem_rag import politica_caso as pc  # noqa: E402
from test_f4 import _cinco_fora_de_ia_decide  # noqa: E402  (mesma seleção da fumaça)

SAIDA = RAIZ / "results/f4/diagnostico_json.jsonl"


class Gravador:
    """Repassa bind_tools/invoke ao modelo real e guarda cada resposta. Não altera mensagens nem respostas."""

    def __init__(self, real):
        self.real, self.respostas = real, []

    def bind_tools(self, tools, **kw):
        self.ligado = self.real.bind_tools(tools, **kw)
        return self

    def invoke(self, msgs, **kw):
        r = self.ligado.invoke(msgs, **kw)
        self.respostas.append(r)
        return r


def vaza(texto: str, fontes: list[str]) -> bool:
    return any(len(f) >= 30 and any(f[k:k + 30] in texto for k in range(len(f) - 29)) for f in fontes)


def main():
    agente.checar_tracing()
    linhas, barradas = [], 0
    for i, txt in _cinco_fora_de_ia_decide():
        g = Gravador(agente.cliente_agente())
        s = agente.triar_agente({"texto": txt, "event_id": f"diag-json-{i}"}, llm=g)
        for n, r in enumerate(g.respostas, 1):
            bruto = r.text
            if vaza(bruto, [txt, pc.mascarar(txt)]):
                barradas += 1
                bruto = None
            u = r.usage_metadata or {}
            linhas.append({"id": i, "chamada": n, "n_chamadas": len(g.respostas), "tool_calls": [c["name"] for c in r.tool_calls],
                           "resposta_bruta": bruto, "barrada_por_trecho_do_ticket": bruto is None,
                           "stop_reason": r.response_metadata.get("stop_reason"),
                           "tokens_entrada": u.get("input_tokens", 0), "tokens_saida": u.get("output_tokens", 0),
                           "faixa_final": s["faixa_final"], "motivo_final": s["motivo_final"] if s["motivo_final"].startswith(("escalado", "divergência")) else "outro"})
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        for l in linhas:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    ti, to = sum(l["tokens_entrada"] for l in linhas), sum(l["tokens_saida"] for l in linhas)
    print(json.dumps({"chamadas": len(linhas), "barradas": barradas, "tokens": [ti, to],
                      "custo_usd": round((ti * 0.10 + to * 0.50) / 1e6, 6)}))


def resumir():
    """Resumo sem texto (versionado): o jsonl tem frases do LLM com fragmentos curtos de tickets e fica fora do git."""
    linhas = [json.loads(l) for l in SAIDA.read_text(encoding="utf-8").splitlines()]
    finais = [l for l in linhas if not l["tool_calls"]]
    por_ticket = {l["id"]: l for l in linhas}
    tools = {}
    for l in linhas:
        for t in l["tool_calls"]:
            tools[t] = tools.get(t, 0) + 1
    ti, to = sum(l["tokens_entrada"] for l in linhas), sum(l["tokens_saida"] for l in linhas)
    res = {"fonte": "results/f4/diagnostico_json.jsonl (fora do git), 1 execução, 5 tickets do treino",
           "ids": sorted(por_ticket), "chamadas": len(linhas), "respostas_finais": len(finais),
           "respostas_finais_com_texto_antes_do_json": sum(not str(l["resposta_bruta"]).lstrip().startswith("{")
                                                          for l in finais),
           "escalonamentos": {m: sum(1 for l in por_ticket.values() if l["motivo_final"] == m)
                              for m in sorted({l["motivo_final"] for l in por_ticket.values()})},
           "tools_chamadas": tools, "tokens": {"entrada": ti, "saida": to},
           "custo_usd": round((ti * 0.10 + to * 0.50) / 1e6, 6)}
    (RAIZ / "results/f4/diagnostico_resumo.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                                              encoding="utf-8", newline="\n")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    resumir() if "--resumo" in sys.argv else main()
