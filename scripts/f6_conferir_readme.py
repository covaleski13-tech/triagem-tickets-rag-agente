"""F6: confere que os números-chave de results/ e docs/custos.md aparecem no README.md com a formatação usada,
e que todo link relativo do README aponta para um arquivo que existe. Saída: faltantes (esperado: nenhum)."""
import json
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def pct(x: float) -> str:  # 0.26 -> "26,00%"
    return f"{100 * x:.2f}%".replace(".", ",")


def dec4(x: float) -> str:  # 0.7406 -> "0,7406"; -0.0514 -> "-0,0514"
    return f"{x:.4f}".replace(".", ",")


def sci(x: float) -> str:  # 1.395e-16 -> "1,40e-16"
    return f"{x:.2e}".replace(".", ",")


def esperados() -> dict:
    ler = lambda p: json.loads((RAIZ / p).read_text(encoding="utf-8"))
    m3, ver = ler("results/f3/metricas_f3.json"), ler("results/f3/veredictos.json")
    fam = pd.read_csv(RAIZ / "results/f3/familia_q1.csv")
    q2, v3q = ler("results/f3/q2_recuperacao.json"), ler("results/f5/veredicto_q3.json")
    q3 = ler("results/f5/q3.json")
    dif = pd.read_csv(RAIZ / "results/f3/q2_diferencas.csv")
    e = {}
    for v, r in m3["variantes"].items():
        e[f"acurácia {v}"] = pct(r["acuracia"])
    for r in fam.itertuples():
        e[f"p Holm {r.comparacao}"] = sci(r.p_holm)
    sim = lambda b: "sim" if b else "não"
    e["RAG ajuda"] = f"**RAG ajuda: {sim(ver['rag_ajuda'])}.**"
    e["LLM agrega"] = f"**O LLM agrega: {sim(ver['llm_agrega'])}.**"
    e["produção"] = f"**Vale para produção: {sim(ver['vale_para_producao'])}.**"
    for u in ("amostra_q2", "recorte_400"):
        for rec, r in q2[u]["por_recuperador"].items():
            e[f"precisão@5 {rec} {u}"] = dec4(r["precisao5_media"])
        hv = dif[(dif.universo == u) & (dif.par == "hibrida-vetorial") & (dif.metrica == "precisao5")].iloc[0]
        e[f"híbrida − vetorial {u}"] = dec4(hv.diferenca_media)
    vc = v3q["veredicto_com_complemento"]
    n_exec = sum(q3["promocoes_indevidas"]["execucoes_verificadas"].values()) + len(
        pd.read_csv(RAIZ / "results/f5/falhas_injetadas_ia_sugere.csv"))
    e["guarda Q3"] = f"{vc['promocoes_indevidas']} promoções em {n_exec:,} execuções (**por construção**)".replace(",", ".")
    e["falhas Q3"] = f"**Falhas:** {vc['falhas_exercitadas_escaladas']} exercitadas escalaram"
    fal = pd.read_csv(RAIZ / "results/f5/falhas_injetadas.csv")
    fis = pd.read_csv(RAIZ / "results/f5/falhas_injetadas_ia_sugere.csv")
    for f in sorted(fal.falha.unique()):
        cel = []
        for t in (fal, fis):
            g = t[t.falha == f]
            cel += [f"{int(g.exercitada.sum())}/{len(g)}", str(int(((g.faixa_final == "humano decide") & g.exercitada).sum()))]
        e[f"falha {f}"] = "| " + " | ".join(cel) + " |"
    d = q3["desvio_llm_sob_ataque"]["total"]
    e["desvio total"] = f"**{d['desviados']}/{d['denominador']}** | **{pct(d['wilson']['taxa'])}**"
    e["rebaixamento ponderado"] = f"**{pct(q3['rebaixamento_limpos']['ponderado_holdout'])}**"
    s = q3["dano_silencioso_classico"]["silencioso"]
    e["dano silencioso"] = f"{s['n']}/{s['de']:,}".replace(",", ".")
    total = re.findall(r"Acumulado do projeto[^:]*: (?:≤ )?US\$ ([0-9,]+)\*\*",
                       (RAIZ / "docs/custos.md").read_text(encoding="utf-8"))[-1]
    e["custo total"] = f"**≤ US$ {total}**"
    return e


def faltantes(readme: str) -> list[str]:
    return [f"{k}: {v!r}" for k, v in esperados().items() if v not in readme]


def links_quebrados(readme: str) -> list[str]:
    alvos = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", readme)
    return [a for a in alvos if not a.startswith(("http://", "https://")) and not (RAIZ / a).exists()]


if __name__ == "__main__":
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    f, l = faltantes(texto), links_quebrados(texto)
    print("números faltantes:", f or "nenhum")
    print("links quebrados:", l or "nenhum")
    sys.exit(1 if f or l else 0)
