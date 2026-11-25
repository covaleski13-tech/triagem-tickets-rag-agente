"""F7 (Q4): LangGraph (agente.py congelado) e ADK (src/triagem_rag/adk) nos mesmos 67 tickets "IA sugere" da F5,
limpos + 5 ataques (402 execuções por implementação), intercalados por par (id, variante) em ordem embaralhada
(seed 42), 4 workers, só a thread principal escreve o log. Depois: golden do case nas duas e falhas injetadas no
ADK. Roda no .venv-adk. Uso: python scripts/f7_avaliar.py [--so-aquecimento]"""
import contextvars
import json
import os
import random
import shutil
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "scripts")]
F7 = RAIZ / "results/f7"
RT = RAIZ / "runtime_f7"
LOG = F7 / "execucoes.jsonl"

from triagem_rag import agente  # noqa: E402
from triagem_rag import politica_caso as pc  # noqa: E402
from triagem_rag.adk import workflow  # noqa: E402
from triagem_rag.dados import SEED, ds2_com_splits, treino  # noqa: E402
import f5_avaliar as f5  # noqa: E402  mesma montagem dos ataques, mesmo formato de log

IMPLS = ("langgraph", "adk")
N_WORKERS = 4

# pastas de runtime separadas por implementação: TRIAGEM_RUNTIME_DIR é global do processo e as duas rodam
# intercaladas, então a pasta vem de uma ContextVar fixada em cada tarefa (o asyncio do ADK copia o contexto)
_RT_ATUAL: contextvars.ContextVar = contextvars.ContextVar("rt_f7", default=None)
_runtime_dir_case = pc.triagem.runtime_dir


def _runtime_dir():
    d = _RT_ATUAL.get()
    if d is None:
        return _runtime_dir_case()
    d.mkdir(parents=True, exist_ok=True)
    return d


pc.triagem.runtime_dir = _runtime_dir


def rodar(t: dict, rt: Path | None = None) -> dict:
    _RT_ATUAL.set(rt or RT / t["impl"])
    ev = {"texto": t["texto"], "event_id": f"f7-{t['impl']}-{t['id']}-{t['variante']}"}
    return agente.triar_agente(ev) if t["impl"] == "langgraph" else workflow.triar_agente_adk(ev)


def linha(saida: dict, t: dict) -> dict:
    return {"impl": t["impl"], **f5.linha_log(saida, t["id"], t["variante"], t["alvo"])}


def ja_feitos(arq: Path) -> set:
    if not arq.exists():
        return set()
    return {(l["impl"], l["id"], l["variante"]) for l in map(json.loads, arq.read_text(encoding="utf-8").splitlines())
            if l}


def tarefas_intercaladas(amostra: pd.DataFrame, texto: pd.Series) -> list[dict]:
    pares = f5.tarefas_principais(amostra, texto)  # 67 × 6, mesma montagem e alvo da F5
    rng = random.Random(SEED)
    rng.shuffle(pares)
    out = []
    for p in pares:
        ordem = list(IMPLS)
        rng.shuffle(ordem)  # qual implementação vai primeiro no par também é sorteado
        out += [{**p, "impl": i} for i in ordem]
    return out


def erro_rede(e: str) -> bool:
    """Erro de TLS ou de conexão. Regra de parada do Gustavo (2026-11-25): 3 ou mais numa implementação."""
    return ": TLS" in e or "Connection" in e


class ParadaRede(Exception):
    pass


def executar(tarefas: list[dict], arq: Path) -> int:
    feitos = ja_feitos(arq)
    pend = [t for t in tarefas if (t["impl"], t["id"], t["variante"]) not in feitos]
    rede = {i: 0 for i in IMPLS}
    original = agente._registrar
    agente._registrar = lambda saida: None  # o agente congelado grava na thread do worker; aqui só a principal
    try:
        arq.parent.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(N_WORKERS) as ex, open(arq, "a", encoding="utf-8", newline="\n") as f:
            futs = {ex.submit(rodar, t): t for t in pend}
            for k, fut in enumerate(as_completed(futs), 1):
                s, t = fut.result(), futs[fut]
                f.write(json.dumps(linha(s, t), ensure_ascii=False) + "\n")
                f.flush()
                rede[t["impl"]] += sum(erro_rede(e) for e in s["erros"])
                if max(rede.values()) >= 3:
                    for x in futs:
                        x.cancel()
                    raise ParadaRede(f"erros de TLS/conexão: {rede}")
                if k % 100 == 0:
                    print(f"{len(feitos) + k}/{len(tarefas)} execuções", flush=True)
    finally:
        agente._registrar = original
    return len(pend)


def aquecimento():
    """Adendo 5: 3 tickets do treino por implementação, fora dos logs de resultado; carrega embeddings e conexões."""
    shutil.rmtree(RT / "aquecimento", ignore_errors=True)  # roda de novo a cada execução: chaves novas
    original = agente._registrar
    agente._registrar = lambda saida: None
    out = []
    try:
        for i, txt in treino().sort_values("id").head(3)[["id", "Document"]].itertuples(index=False):
            for impl in IMPLS:
                s = rodar({"impl": impl, "id": int(i), "variante": "aquecimento", "texto": str(txt)},
                          RT / "aquecimento" / impl)
                out.append({"impl": impl, "llm_rodou": s["llm_rodou"], "erros": s["erros"],
                            "tokens_entrada": s["tokens_entrada"], "tokens_saida": s["tokens_saida"]})
    finally:
        agente._registrar = original
    return out


def fase_golden():
    arq = F7 / "golden.jsonl"
    if arq.exists():
        return
    golden = [json.loads(l) for l in (RAIZ / "tests/golden/golden_v1.jsonl").read_text(encoding="utf-8").splitlines()]
    linhas = []
    original = agente._registrar
    agente._registrar = lambda saida: None
    try:
        for impl in IMPLS:
            for g in golden:
                if g["caso"] == "portao_qualidade":
                    continue
                _RT_ATUAL.set(RT / "golden" / impl / g["caso"])
                amb = {"falha_classificador": ("TRIAGEM_MODELO_VERSAO", "000000000000"),
                       "modo_sombra": ("TRIAGEM_MODO", "sombra")}.get(g["caso"])
                antes = os.environ.get(amb[0]) if amb else None
                if amb:
                    os.environ[amb[0]] = amb[1]
                try:
                    for n in range(2 if g["caso"] == "duplicado" else 1):
                        ev = dict(g["entrada"])
                        s = agente.triar_agente(ev) if impl == "langgraph" else workflow.triar_agente_adk(ev)
                        linhas.append({"impl": impl, "caso": g["caso"], "envio": n + 1,
                                       **f5.linha_log(s, -1, g["caso"], None)})
                finally:
                    if amb:
                        if antes is None:
                            del os.environ[amb[0]]
                        else:
                            os.environ[amb[0]] = antes
    finally:
        agente._registrar = original
    arq.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in linhas), encoding="utf-8", newline="\n")


def fase_falhas(amostra: pd.DataFrame, texto: pd.Series):
    """Só no ADK: 10 primeiros ids dos 67, exceção em recuperar_exemplos e timeout pelo parâmetro do LiteLLM."""
    arq = F7 / "falhas_injetadas_adk.csv"
    if arq.exists():
        return
    ids = sorted(amostra["id"])[:10]
    lento = workflow.chamar_litellm(workflow.modelo_litellm(timeout_s=0.001))
    linhas = []
    for i in ids:
        for falha in ("recuperar_exemplos", "timeout"):
            _RT_ATUAL.set(RT / "falhas" / falha)
            ev = {"texto": str(texto[i]), "event_id": f"f7-adk-falha-{i}-{falha}"}
            s = workflow.triar_agente_adk(ev, buscar=f5._buscar_quebra if falha == "recuperar_exemplos" else None,
                                          chamar=lento if falha == "timeout" else None)
            if falha == "timeout":
                exercitada = s["llm_rodou"]
                tentativas = sum("timeout" in e for e in s["erros"])
                excecao = sorted({e.split("(")[1].split(")")[0] for e in s["erros"] if "(" in e})
            else:
                exercitada = any(c["nome"] == falha and c.get("erro") for c in s["tool_calls"])
                tentativas = sum(1 for c in s["tool_calls"] if c["nome"] == falha)
                excecao = sorted({c["erro"] for c in s["tool_calls"] if c.get("erro")})
            linhas.append({"id": i, "falha": falha, "exercitada": exercitada, "faixa_final": s["faixa_final"],
                           "tentativas": tentativas, "causa": s["motivo_final"] if exercitada else "",
                           "excecao": ";".join(excecao), "llm_rodou": s["llm_rodou"],
                           "faixa_politica": s["faixa_politica"], "tokens_entrada": s["tokens_entrada"],
                           "tokens_saida": s["tokens_saida"]})
    pd.DataFrame(linhas).to_csv(arq, index=False, lineterminator="\n")


def conferir_runtime(tarefas: list[dict]) -> dict:
    """Cada implementação gravou só as próprias chaves, na própria pasta."""
    out = {}
    for impl in IMPLS:
        dbs = list((RT / impl).glob("*.db")) + list((RT / impl).glob("*.sqlite*"))
        chaves = set()
        for db in dbs:
            with sqlite3.connect(db) as con:
                try:
                    chaves |= {r[0] for r in con.execute("SELECT chave FROM eventos")}
                except sqlite3.OperationalError:
                    pass
        esperadas = {f"evt:f7-{impl}-{t['id']}-{t['variante']}" for t in tarefas if t["impl"] == impl}
        out[impl] = {"chaves": len(chaves), "esperadas": len(esperadas), "iguais": chaves == esperadas}
    return out


def main():
    agente.checar_tracing()
    F7.mkdir(parents=True, exist_ok=True)
    df = ds2_com_splits()
    texto = df.set_index("id")["Document"]
    amostra = pd.read_csv(RAIZ / "results/f5/amostra_q3.csv")
    amostra = amostra[amostra.estrato == "IA sugere"].reset_index(drop=True)
    assert len(amostra) == 67
    tarefas = tarefas_intercaladas(amostra, texto)
    assert len(tarefas) == 804
    if not LOG.exists():
        for p in [RT / i for i in IMPLS] + [RT / "aquecimento"]:
            shutil.rmtree(p, ignore_errors=True)  # pastas de runtime limpas antes
    t0 = time.perf_counter()
    aq = aquecimento()
    print("aquecimento:", json.dumps(aq), flush=True)
    if any(a["erros"] for a in aq) or not all(any(a["llm_rodou"] for a in aq if a["impl"] == i) for i in IMPLS):
        sys.exit("aquecimento com erro: parar antes da avaliação")
    if "--so-aquecimento" in sys.argv:
        return
    t1 = time.perf_counter()
    n = executar(tarefas, LOG)
    t2 = time.perf_counter()
    fase_golden()
    fase_falhas(amostra, texto)
    tempos = {"execucoes_novas": n, "aquecimento_s": round(t1 - t0, 1), "principal_s": round(t2 - t1, 1),
              "total_s": round(time.perf_counter() - t0, 1), "runtime": conferir_runtime(tarefas),
              "aquecimento_tokens": {i: [sum(a[k] for a in aq if a["impl"] == i)
                                         for k in ("tokens_entrada", "tokens_saida")] for i in IMPLS}}
    arq_t = F7 / "tempos.json"
    hist = json.loads(arq_t.read_text(encoding="utf-8")) if arq_t.exists() else []
    arq_t.write_text(json.dumps(hist + [tempos], indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(tempos), flush=True)


if __name__ == "__main__":
    main()
