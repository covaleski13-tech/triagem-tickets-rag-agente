"""F5 (Q3): avaliação do agente congelado (commit 7fbdece) no holdout, com ataques e falhas injetadas.
Fases: (A) estratos via triar() em todo o holdout e amostra 67/67/66 gravada antes de qualquer LLM; (B) 200 × 6
execuções de triar_agente (limpa + 5 ataques), 4 workers, só a thread principal escreve o log, retomável;
(C) golden do case; (D) falhas injetadas. Nada no agente muda."""
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
F5 = RAIZ / "results/f5"
RT = RAIZ / "runtime_f5"
LOG = F5 / "agente_log.jsonl"

from triagem_rag import agente  # noqa: E402
from triagem_rag import politica_caso as pc  # noqa: E402
from triagem_rag.dados import CATEGORIAS, SEED, ds2_com_splits  # noqa: E402

N_POR_ESTRATO = {"IA decide": 67, "IA sugere": 67, "humano decide": 66}
N_WORKERS = 4
CAMPOS_F4 = ("chave", "faixa_politica", "faixa_final", "categoria_classico", "p_max", "categoria_llm", "llm_rodou",
             "rodadas", "tool_calls", "erros", "tokens_entrada", "tokens_saida", "latencia_ms")


def ataques() -> list[dict]:
    return json.loads((RAIZ / "tests/golden/ataques_v1.json").read_text(encoding="utf-8"))["ataques"]


def alvo(pred_limpa: str, deslocamento: int) -> str:
    # igual ao f5_injecao.py do case: deslocamentos 1–5 num ciclo de 8, nunca a predição limpa
    return CATEGORIAS[(CATEGORIAS.index(pred_limpa) + deslocamento) % len(CATEGORIAS)]


def linha_log(saida: dict, id_: int, variante: str, alvo_: str | None) -> dict:
    """Mesmo formato do log da F4 (agente._registrar), mais id, variante e alvo. Sem texto de ticket nem do LLM."""
    l = {"id": int(id_), "variante": variante, "alvo": alvo_, **{k: saida.get(k) for k in CAMPOS_F4}}
    l["motivo_final"] = re.sub(r"termos: [^;]*", "termos: <omitidos no log>", str(saida.get("motivo_final")))
    return l


def ja_feitos(arq: Path) -> set:
    if not arq.exists():
        return set()
    return {(l["id"], l["variante"]) for l in map(json.loads, arq.read_text(encoding="utf-8").splitlines()) if l}


def executar(tarefas: list[dict], rodar, arq: Path, n_workers: int = N_WORKERS) -> int:
    """Roda as tarefas pendentes em paralelo; só a thread principal escreve `arq`. Retomável por (id, variante)."""
    feitos = ja_feitos(arq)
    pend = [t for t in tarefas if (t["id"], t["variante"]) not in feitos]
    original = agente._registrar
    agente._registrar = lambda saida: None  # o agente congelado grava na thread do worker; aqui só a principal grava
    try:
        arq.parent.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(n_workers) as ex, open(arq, "a", encoding="utf-8", newline="\n") as f:
            futs = {ex.submit(rodar, t): t for t in pend}
            for k, fut in enumerate(as_completed(futs), 1):
                t = futs[fut]
                f.write(json.dumps(linha_log(fut.result(), t["id"], t["variante"], t["alvo"]), ensure_ascii=False) + "\n")
                f.flush()
                if k % 100 == 0:
                    print(f"{len(feitos) + k}/{len(tarefas)} execuções", flush=True)
    finally:
        agente._registrar = original
    return len(pend)


def fase_estratos(df: pd.DataFrame) -> pd.DataFrame:
    arq = F5 / "amostra_q3.csv"
    if arq.exists():
        return pd.read_csv(arq)
    assert not LOG.exists(), "o log existe sem a amostra: a amostra tem de ser gravada antes de qualquer LLM"
    shutil.rmtree(RT, ignore_errors=True)  # idempotência do case: pasta própria e limpa
    os.environ["TRIAGEM_RUNTIME_DIR"] = str(RT / "estratos")
    ho = df[df["split_grupo"] == "holdout"].sort_values("id")
    t0 = time.perf_counter()
    res = [pc.triar({"texto": str(t), "event_id": f"f5-estrato-{i}"}) for i, t in zip(ho["id"], ho["Document"])]
    os.environ["TRIAGEM_RUNTIME_DIR"] = str(RT / "execucoes")
    ho = ho.assign(estrato=[r.get("faixa_sem_sombra", r["faixa"]) for r in res],
                   categoria_classico=[r.get("categoria") for r in res], p_max=[r.get("p_max") for r in res])
    cont = ho["estrato"].value_counts().to_dict()
    amostra = pd.concat([ho[ho.estrato == e].sample(n, random_state=SEED) for e, n in N_POR_ESTRATO.items()])
    amostra[["id", "estrato", "categoria_classico", "p_max"]].to_csv(arq, index=False, lineterminator="\n")
    (F5 / "estratos_holdout.json").write_text(json.dumps({
        "n_holdout": len(ho), "contagem": cont, "proporcao": {e: round(c / len(ho), 6) for e, c in cont.items()},
        "triar_s": round(time.perf_counter() - t0, 1)}, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    return pd.read_csv(arq)


def tarefas_principais(amostra: pd.DataFrame, texto: pd.Series) -> list[dict]:
    out = []
    for r in amostra.itertuples():
        out.append({"id": r.id, "variante": "limpa", "alvo": None, "texto": str(texto[r.id])})
        for a in ataques():
            al = alvo(r.categoria_classico, a["deslocamento_alvo"])
            out.append({"id": r.id, "variante": a["id"], "alvo": al,
                        "texto": f"{texto[r.id]} {a['texto'].format(alvo=al)}"})
    return out


def rodar_agente(t: dict) -> dict:
    return agente.triar_agente({"texto": t["texto"], "event_id": f"f5-{t['id']}-{t['variante']}"})


def fase_golden():
    arq = F5 / "golden.jsonl"
    if arq.exists():
        return
    golden = [json.loads(l) for l in (RAIZ / "tests/golden/golden_v1.jsonl").read_text(encoding="utf-8").splitlines()]
    linhas = []
    for g in golden:
        if g["caso"] == "portao_qualidade":
            continue
        os.environ["TRIAGEM_RUNTIME_DIR"] = str(RT / "golden" / g["caso"])
        amb = {"falha_classificador": ("TRIAGEM_MODELO_VERSAO", "000000000000"),
               "modo_sombra": ("TRIAGEM_MODO", "sombra")}.get(g["caso"])
        antes = os.environ.get(amb[0]) if amb else None
        if amb:
            os.environ[amb[0]] = amb[1]
        try:
            envios = 2 if g["caso"] == "duplicado" else 1
            for n in range(envios):
                s = agente.triar_agente(dict(g["entrada"]))
                linhas.append({"caso": g["caso"], "envio": n + 1, **linha_log(s, -1, g["caso"], None)})
        finally:
            if amb:
                os.environ[amb[0]] = antes if antes is not None else ""
                if antes is None:
                    del os.environ[amb[0]]
    os.environ["TRIAGEM_RUNTIME_DIR"] = str(RT / "execucoes")
    arq.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in linhas), encoding="utf-8", newline="\n")


def _buscar_quebra(texto, k):
    raise RuntimeError("falha injetada em recuperar_exemplos")


def fase_falhas(amostra: pd.DataFrame, texto: pd.Series, estrato: str = "humano decide",
                arq_nome: str = "falhas_injetadas.csv", prefixo: str = "f5-falha"):
    # padrões = F5; o complemento da correção pós-revisão usa estrato "IA sugere" e prefixo "f5c"
    arq = F5 / arq_nome
    if arq.exists():
        return
    ids = sorted(amostra.loc[amostra.estrato == estrato, "id"])[:10]
    llm_lento = agente.cliente_agente().model_copy(update={"default_request_timeout": 0.001})
    linhas = []
    for i in ids:
        for falha in ("recuperar_exemplos", "consultar_politica", "timeout"):
            ev = {"texto": str(texto[i]), "event_id": f"{prefixo}-{i}-{falha}"}
            original = agente._politica
            try:
                if falha == "consultar_politica":
                    agente._politica = lambda: (_ for _ in ()).throw(RuntimeError("falha injetada"))
                s = agente.triar_agente(ev, buscar=_buscar_quebra if falha == "recuperar_exemplos" else None,
                                        llm=llm_lento if falha == "timeout" else None)
            finally:
                agente._politica = original
            if falha == "timeout":
                exercitada = s["llm_rodou"]
                tentativas = sum("timeout" in e for e in s["erros"])
            else:
                exercitada = any(c["nome"] == falha and c.get("erro") for c in s["tool_calls"])
                tentativas = sum(1 for c in s["tool_calls"] if c["nome"] == falha)
            linhas.append({"id": i, "falha": falha, "exercitada": exercitada, "faixa_final": s["faixa_final"],
                           "tentativas": tentativas, "causa": s["motivo_final"] if exercitada else "",
                           "llm_rodou": s["llm_rodou"], "faixa_politica": s["faixa_politica"],
                           "tokens_entrada": s["tokens_entrada"], "tokens_saida": s["tokens_saida"]})
    pd.DataFrame(linhas).to_csv(arq, index=False, lineterminator="\n")


def main():
    # no main, não no import: os testes importam este módulo
    os.environ["TRIAGEM_RUNTIME_DIR"] = str(RT / "execucoes")
    os.environ["TRIAGEM_AGENTE_LOG"] = str(LOG)
    agente.checar_tracing()
    F5.mkdir(parents=True, exist_ok=True)
    df = ds2_com_splits()
    texto = df.set_index("id")["Document"]
    t0 = time.perf_counter()
    amostra = fase_estratos(df)
    print("amostra:", amostra["estrato"].value_counts().to_dict(), flush=True)
    if "--so-amostra" in sys.argv:
        return
    if "--falhas-ia-sugere" in sys.argv:
        # correção pós-revisão da F6 (A2): mesmas falhas, 10 primeiros ids de "IA sugere", runtime e log próprios
        os.environ["TRIAGEM_RUNTIME_DIR"] = str(RT / "f5c")
        os.environ["TRIAGEM_AGENTE_LOG"] = str(F5 / "agente_log_falhas_ia_sugere.jsonl")
        fase_falhas(amostra, texto, "IA sugere", "falhas_injetadas_ia_sugere.csv", "f5c")
        return
    n = executar(tarefas_principais(amostra, texto), rodar_agente, LOG)
    t1 = time.perf_counter()
    # golden e falhas gravam pelo _registrar do próprio agente: em arquivo separado do log principal
    os.environ["TRIAGEM_AGENTE_LOG"] = str(F5 / "agente_log_golden_falhas.jsonl")
    fase_golden()
    fase_falhas(amostra, texto)
    tempos = {"execucoes_novas": n, "principal_s": round(t1 - t0, 1), "total_s": round(time.perf_counter() - t0, 1)}
    arq_t = F5 / "tempos.json"
    hist = json.loads(arq_t.read_text(encoding="utf-8")) if arq_t.exists() else []
    arq_t.write_text(json.dumps(hist + [tempos], indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(tempos), flush=True)


if __name__ == "__main__":
    main()
