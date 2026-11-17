"""Cliente LLM das variantes de Q1, replicando o f3_llm.py do case (commit 3a880f2) via langchain-anthropic."""
import json
import os
import time

import numpy as np
from dotenv import load_dotenv

from triagem_rag.dados import CATEGORIAS, RAIZ, SEED
from triagem_rag.esquema import validar
from triagem_rag.metricas import FALHA

load_dotenv(RAIZ / ".env")

MODELO = "claude-haiku-5-5"
MAX_TOKENS = 64
PROMPT_V0 = RAIZ / "prompts" / "classificar_v1.txt"
PROMPT_RAG = RAIZ / "prompts" / "classificar_rag_v1.txt"


def checar_tracing():
    # nenhum texto de ticket pode ir para telemetria externa (F0 §5)
    assert os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() != "true", "LANGCHAIN_TRACING_V2=true"
    assert os.environ.get("LANGSMITH_TRACING", "false").lower() != "true", "LANGSMITH_TRACING=true"


def cliente(api_key: str | None = None):
    from langchain_anthropic import ChatAnthropic
    # sem temperature: o Haiku 5.5 recusa valor diferente do padrão; saídas não são determinísticas
    return ChatAnthropic(model=MODELO, max_tokens=MAX_TOKENS, max_retries=0,
                         thinking={"type": "disabled"}, output_config={"effort": "low"},
                         api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))


def mensagens(system: str, texto: str):
    from langchain_core.messages import HumanMessage, SystemMessage
    return [SystemMessage(system), HumanMessage(f"<ticket>{texto}</ticket>")]


def exemplo(texto: str, categoria: str) -> str:
    return f"<ticket>{texto}</ticket>\n{json.dumps({'categoria': categoria, 'confianca': 1.0})}"


def system_v0(treino) -> tuple[str, list[tuple[str, int]]]:
    """Mesma montagem do case: 1 exemplo por categoria, sample(1, random_state=42) sobre o treino em ordem de id."""
    ex, ids = [], []
    for c in CATEGORIAS:
        linha = treino[treino["Topic_group"] == c].sample(1, random_state=SEED).iloc[0]
        ex.append(exemplo(linha["Document"], c))
        ids.append((c, int(linha["id"])))
    return PROMPT_V0.read_text(encoding="utf-8").replace("{exemplos}", "\n\n".join(ex)), ids


def sortear_v1(id_ticket: int, ids_treino: np.ndarray, k: int = 5) -> list[int]:
    # fixo por ticket; o ticket é do holdout, então nunca está em ids_treino
    rng = np.random.default_rng([SEED, int(id_ticket)])
    return [int(i) for i in rng.choice(ids_treino, size=k, replace=False)]


def system_rag(exemplos: list[tuple[str, str]]) -> str:
    return PROMPT_RAG.read_text(encoding="utf-8").replace("{exemplos}", "\n\n".join(exemplo(t, c) for t, c in exemplos))


def chamar(llm, system: str, texto: str) -> dict:
    import anthropic
    erros, ultimo = 0, None
    for tentativa in range(3):
        try:
            t0 = time.perf_counter()
            r = llm.invoke(mensagens(system, texto))
            lat = (time.perf_counter() - t0) * 1000
            u = r.usage_metadata or {}
            return {"lat_ms": lat, "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
                    "bruto": r.text, "erros_api": erros}
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            erros += 1
            ultimo = type(e).__name__
            time.sleep(2 ** tentativa)
    return {"lat_ms": None, "in": 0, "out": 0, "bruto": None, "erros_api": erros, "erro": ultimo}


def classificar(llm, system: str, id_: int, texto: str) -> tuple[list[dict], str]:
    """Política de repetição do case: até 3 tentativas por erro de API; 1 repetição se a saída for inválida."""
    tentativas, obj = [], None
    for n in range(2):
        r = chamar(llm, system, texto)
        obj = validar(r["bruto"]) if r["bruto"] is not None else None
        r.update(id=int(id_), tentativa=n + 1, valida="s" if obj else "n")
        tentativas.append(r)
        if obj or r["bruto"] is None:
            break
    return tentativas, (obj.categoria if obj else FALHA)
