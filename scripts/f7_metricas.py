"""F7 (Q4): métricas lado a lado LangGraph × ADK -> results/f7/q4.json, q4_lado_a_lado.csv e esforco.json.
Mesmas definições da F5 (scripts/f5_metricas.py, por import). Sem teste de superioridade: contagens + Wilson."""
import ast
import io
import json
import subprocess
import sys
import tokenize
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "scripts")]
import f5_metricas as f5m  # noqa: E402

F5, F7 = RAIZ / "results/f5", RAIZ / "results/f7"
IMPLS = ("langgraph", "adk")
INICIO_FASE = "2026-11-25 16:46:24"  # relógio no início da F7 (passo 0)


def causa(m: str) -> str:
    # as causas da spec da F7; "formato" = responder inválido (na F5 ficava em "falha do LLM")
    if "responder inválido" in m:
        return "formato"
    return f5m.causa(m)


def por_impl(log: pd.DataFrame, golden: pd.DataFrame) -> dict:
    com = log[log.llm_rodou]
    nomes = log.tool_calls.map(lambda tc: [c["nome"] for c in tc])
    n_tools = nomes.map(len)
    n_tools_sem_resp = nomes.map(lambda n: sum(x != "responder" for x in n))
    esc = log[log.faixa_final == "humano decide"]
    esc = esc[esc.faixa_politica != "humano decide"]
    todas = pd.concat([log, golden], ignore_index=True)
    tin, tout = int(todas.tokens_entrada.sum()), int(todas.tokens_saida.sum())
    custo = (tin * f5m.PRECO_IN + tout * f5m.PRECO_OUT) / 1e6
    lat = log.latencia_ms
    prom = f5m.promocoes(todas.assign(id=todas.id.fillna(-1))[["id", "variante", "faixa_politica", "faixa_final",
                                                                 "llm_rodou"]])
    return {
        "execucoes": len(log), "com_llm": len(com),
        "promocoes_indevidas": {"n": len(prom), "ids": prom, "verificadas": len(todas)},
        "escalonamentos": {"total": f5m._w(len(esc), len(log)),
                           "por_causa": esc.motivo_final.map(causa).value_counts().to_dict()},
        "desvio_sob_ataque": f5m.desvio(log),
        "tools_por_ticket": {"media_todas": round(float(n_tools[log.llm_rodou].mean()), 3),
                             "media_sem_responder": round(float(n_tools_sem_resp[log.llm_rodou].mean()), 3),
                             "distribuicao_todas": n_tools[log.llm_rodou].value_counts().sort_index().to_dict(),
                             "recuperar_exemplos": f5m._w(int(nomes[log.llm_rodou].map(
                                 lambda n: "recuperar_exemplos" in n).sum()), len(com)),
                             "consultar_politica": f5m._w(int(nomes[log.llm_rodou].map(
                                 lambda n: "consultar_politica" in n).sum()), len(com))},
        "rodadas": com.rodadas.value_counts().sort_index().to_dict(),
        "latencia_ms": {"n": len(lat), "p50": round(float(np.percentile(lat, 50)), 1),
                        "p95": round(float(np.percentile(lat, 95)), 1)},
        "latencia_ms_com_llm": {"n": len(com), "p50": round(float(np.percentile(com.latencia_ms, 50)), 1),
                                "p95": round(float(np.percentile(com.latencia_ms, 95)), 1)},
        "custo": {"tokens": {"entrada": tin, "saida": tout}, "custo_usd": round(custo, 6),
                  "execucoes": len(todas), "por_1000_execucoes_usd": round(custo / len(todas) * 1000, 4)},
        "golden": golden[["caso", "envio", "faixa_politica", "faixa_final", "llm_rodou"]].to_dict("records"),
    }


def concordancia(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """Pares (id, variante) com o LLM rodando e devolvendo categoria nos dois lados."""
    m = a.merge(b, on=["id", "variante"], suffixes=("_a", "_b"))
    m = m[m.llm_rodou_a & m.llm_rodou_b & m.categoria_llm_a.notna() & m.categoria_llm_b.notna()]
    return {"pares": len(m), **f5m._w(int((m.categoria_llm_a == m.categoria_llm_b).sum()), len(m))}


def linhas_codigo(texto: str, so: set[str] | None = None) -> int:
    """Linhas com código: sem comentários, linhas em branco e docstrings. `so`: só esses defs/classes de topo."""
    arv = ast.parse(texto)
    docs = set()
    for n in ast.walk(arv):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and \
                isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant) \
                and isinstance(n.body[0].value.value, str):
            docs |= set(range(n.body[0].lineno, n.body[0].end_lineno + 1))
    cod = set()
    for t in tokenize.generate_tokens(io.StringIO(texto).readline):
        if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                          tokenize.ENDMARKER):
            cod |= set(range(t.start[0], t.end[0] + 1))
    cod -= docs
    if so is not None:
        faixas = set()
        for n in arv.body:
            nome = getattr(n, "name", None)
            if nome in so:
                ini = min([d.lineno for d in getattr(n, "decorator_list", [])] + [n.lineno])
                faixas |= set(range(ini, n.end_lineno + 1))
            if isinstance(n, (ast.Import, ast.ImportFrom)) and "lang" in ast.unparse(n):
                faixas |= set(range(n.lineno, n.end_lineno + 1))
        cod &= faixas
    return len(cod)


# o que o agente.py tem de específico do LangGraph/LangChain: o que o ADK teve de reescrever, não importar
LG_ESPECIFICO = {"Estado", "recuperar_exemplos", "consultar_politica", "responder", "bind_kwargs", "cliente_agente",
                 "_invocar", "no_sugerir", "construir_grafo", "triar_agente"}

CONTORNOS = [
    {"contorno": "subclasse LiteLlmPorRodada", "onde": "src/triagem_rag/adk/tools_adk.py",
     "motivo": "o adaptador LiteLlm do ADK traduz só o modo ANY -> \"required\" e descarta allowed_function_names; "
               "sem ela não há disable_parallel_tool_use nas rodadas 1-2 nem responder forçado na 3ª"},
    {"contorno": "regras por resposta dentro de um BaseLlm (ModeloSugerir)", "onde": "src/triagem_rag/adk/nos.py",
     "motivo": "o ADK não tem ponto para repetir uma chamada ao modelo (1 nova tentativa, chamada múltipla, "
               "responder inválido) sem passar pelo fluxo de tools; a RetryConfig do nó repetiria o nó inteiro"},
    {"contorno": "ToolBruta (BaseTool com argumentos brutos e declaração da tool LangChain)",
     "onde": "src/triagem_rag/adk/tools_adk.py",
     "motivo": "o FunctionTool descarta argumentos extras e devolve erro de validação ou de argumento faltante ao "
               "LLM (function_tool.py, run_async), contra a regra erro de tool -> humano"},
    {"contorno": "skip_summarization=True na tool responder (e após erro de tool)", "onde": "src/triagem_rag/adk/nos.py",
     "motivo": "sem isso o ADK faz mais uma chamada ao modelo depois da resposta de cada tool (4ª chamada com "
               "responder forçado; ou erro de tool devolvido ao modelo)"},
    {"contorno": "campo reg: Any no BaseLlm", "onde": "src/triagem_rag/adk/nos.py",
     "motivo": "BaseLlm é pydantic: um campo dict é copiado na validação e o registro da execução se perdia "
               "(achado na 1ª prova do workflow)"},
    {"contorno": "include_contents=\"none\" e mensagem de entrada sem o ticket", "onde": "src/triagem_rag/adk/workflow.py",
     "motivo": "o Agent leva o histórico da sessão ao modelo; assim ele vê só system + <ticket>mascarado</ticket>, "
               "como no LangGraph"},
]


def main():
    log = pd.read_json(F7 / "execucoes.jsonl", lines=True)
    assert len(log) == 804 and log[["impl", "id", "variante"]].drop_duplicates().shape[0] == 804
    golden = pd.read_json(F7 / "golden.jsonl", lines=True)
    falhas = pd.read_csv(F7 / "falhas_injetadas_adk.csv")
    f5log = pd.read_json(F5 / "agente_log.jsonl", lines=True)
    f5log = f5log[f5log.id.isin(set(log.id))]
    assert len(f5log) == 402
    res = {"n_por_impl": 402, "tickets": 67, "variantes": sorted(log.variante.unique()),
           "por_impl": {i: por_impl(log[log.impl == i], golden[golden.impl == i]) for i in IMPLS}}
    lg, adk = log[log.impl == "langgraph"], log[log.impl == "adk"]
    res["concordancia_categoria"] = {"adk_x_langgraph_hoje": concordancia(adk, lg),
                                     "langgraph_hoje_x_langgraph_f5": concordancia(lg, f5log),
                                     "nota": "LangGraph × LangGraph é o piso de variação do próprio LLM"}
    ex = falhas[falhas.exercitada]
    ok = ex[(ex.faixa_final == "humano decide") & (ex.tentativas <= 2) & ex.causa.str.startswith("escalado")]
    prom_f = f5m.promocoes(falhas.assign(variante="falha")[["id", "variante", "faixa_politica", "faixa_final",
                                                           "llm_rodou"]])
    res["falhas_injetadas_adk"] = {
        "exercitadas": len(ex), "escalaram_ok": len(ok), "promocoes": len(prom_f),
        "nao_exercitadas": falhas[~falhas.exercitada].groupby("falha").size().to_dict(),
        "por_falha": {f: {"n": len(g), "exercitadas": int(g.exercitada.sum()),
                          "escalaram_ok": int(g.index.isin(ok.index).sum()),
                          "excecao": sorted(set(g.excecao.dropna()))} for f, g in falhas.groupby("falha")}}
    # paridade: o teste roda aqui, para o veredicto sair de código executado
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "tests/test_f7.py::test_paridade"], cwd=RAIZ, capture_output=True, text=True)
    res["paridade_teste"] = {"comando": "pytest tests/test_f7.py::test_paridade", "passou": r.returncode == 0,
                             "resumo": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""}
    pa = res["por_impl"]["adk"]
    res["veredicto"] = {
        "adk_preserva_seguranca": bool(pa["promocoes_indevidas"]["n"] == 0 and len(prom_f) == 0
                                       and len(ex) > 0 and len(ok) == len(ex) and res["paridade_teste"]["passou"]),
        "promocoes_adk": pa["promocoes_indevidas"]["n"] + len(prom_f),
        "falhas_exercitadas_escaladas": f"{len(ok)}/{len(ex)}", "paridade": res["paridade_teste"]["passou"],
        "nota": "0 promoções é por construção (guarda importada do agente.py); sem teste de superioridade"}
    (F7 / "q4.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8",
                                newline="\n")

    def lin(nome, f):
        return {"metrica": nome, **{i: f(res["por_impl"][i]) for i in IMPLS}}
    w = lambda d: f"{d['n']}/{d['de']} ({100 * d['taxa']:.1f}%; {100 * d['wilson95'][0]:.1f}–{100 * d['wilson95'][1]:.1f}%)" if d["de"] else "0/0"  # noqa: E731
    tab = [lin("execuções", lambda p: p["execucoes"]), lin("com LLM", lambda p: p["com_llm"]),
           lin("promoções indevidas", lambda p: p["promocoes_indevidas"]["n"]),
           lin("escalonamentos (IA sugere -> humano)", lambda p: w(p["escalonamentos"]["total"])),
           *[lin(f"escalonamentos: {c}", lambda p, c=c: p["escalonamentos"]["por_causa"].get(c, 0))
             for c in ("divergência LLM × clássico", "falha do LLM", "erro de tool", "limite de rodadas", "formato")],
           lin("desvio para o alvo do ataque", lambda p: w({"n": p["desvio_sob_ataque"]["desviados"],
                                                            **{k: p["desvio_sob_ataque"]["wilson"][k]
                                                               for k in ("de", "taxa", "wilson95")}})),
           lin("tools por execução com LLM (com responder)", lambda p: p["tools_por_ticket"]["media_todas"]),
           lin("tools por execução com LLM (sem responder)", lambda p: p["tools_por_ticket"]["media_sem_responder"]),
           lin("% com recuperar_exemplos", lambda p: w(p["tools_por_ticket"]["recuperar_exemplos"])),
           lin("% com consultar_politica", lambda p: w(p["tools_por_ticket"]["consultar_politica"])),
           lin("rodadas (distribuição)", lambda p: json.dumps(p["rodadas"])),
           lin("latência p50 (ms)", lambda p: p["latencia_ms"]["p50"]),
           lin("latência p95 (ms)", lambda p: p["latencia_ms"]["p95"]),
           lin("custo por 1.000 execuções (US$)", lambda p: p["custo"]["por_1000_execucoes_usd"])]
    pd.DataFrame(tab).to_csv(F7 / "q4_lado_a_lado.csv", index=False, lineterminator="\n")

    adk_dir = RAIZ / "src/triagem_rag/adk"
    por_arq = {p.name: linhas_codigo(p.read_text(encoding="utf-8")) for p in sorted(adk_dir.glob("*.py"))}
    agente_txt = (RAIZ / "src/triagem_rag/agente.py").read_text(encoding="utf-8")
    t = json.loads((F7 / "tempos.json").read_text(encoding="utf-8"))[-1]
    esforco = {"regra_de_contagem": "linhas com código, sem comentários, linhas em branco e docstrings "
                                    "(scripts/f7_metricas.py, linhas_codigo); testes fora",
               "adk_linhas": {"total": sum(por_arq.values()), "por_arquivo": por_arq},
               "agente_py_especifico_langgraph": {"linhas": linhas_codigo(agente_txt, LG_ESPECIFICO),
                                                  "defs": sorted(LG_ESPECIFICO) + ["imports langchain/langgraph"],
                                                  "agente_py_total": linhas_codigo(agente_txt)},
               "contornos": CONTORNOS,
               "tempo": {"inicio": INICIO_FASE, "avaliacao_s": t["total_s"],
                         "fim": "horário do commit da F7 (ver F7-report.md §8)"}}
    (F7 / "esforco.json").write_text(json.dumps(esforco, indent=2, ensure_ascii=False), encoding="utf-8",
                                     newline="\n")
    print(json.dumps({"veredicto": res["veredicto"], "concordancia": res["concordancia_categoria"],
                      "falhas": res["falhas_injetadas_adk"], "esforco": esforco["adk_linhas"],
                      "lg_especifico": esforco["agente_py_especifico_langgraph"]}, indent=1, ensure_ascii=False))
    print(pd.DataFrame(tab).to_string(index=False))


if __name__ == "__main__":
    main()
