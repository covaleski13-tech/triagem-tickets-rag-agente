"""F6: soma o custo real de API do projeto a partir das linhas de custo real de docs/custos.md.
Cada parcela é procurada literalmente no arquivo (falha se não estiver lá); a soma tem de bater com o último
acumulado registrado."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CUSTOS = (RAIZ / "docs/custos.md").read_text(encoding="utf-8")

# (fase, rodada, valor como escrito em docs/custos.md)
PARCELAS = [
    ("F2", "V0", "US$ 0,060123"),
    ("F2", "V1", "US$ 0,043256"),
    ("F3", "teste de fumaça (teto)", "≤ US$ 0,0000368"),
    ("F3", "V2", "US$ 0,043986"),
    ("F3", "V3", "US$ 0,035457"),
    ("F4", "fumaça 1", "US$ 0,001134"),
    ("F4", "fumaça 2 (não planejada)", "US$ 0,001226"),
    ("F4", "diagnóstico do JSON", "US$ 0,001529"),
    ("F4", "fumaça da emenda 1", "US$ 0,001014"),
    ("F4", "fumaça da emenda 2", "US$ 0,001318"),
    ("F5", "avaliação do agente", "US$ 0,276108"),
]


def valor(txt: str) -> float:
    return float(re.search(r"US\$ ([0-9,]+)", txt).group(1).replace(",", "."))


def somar() -> dict:
    faltam = [p for p in PARCELAS if p[2] not in CUSTOS]
    assert not faltam, f"parcelas não encontradas em docs/custos.md: {faltam}"
    por_fase = {}
    for fase, _, v in PARCELAS:
        por_fase[fase] = por_fase.get(fase, 0.0) + valor(v)
    total = sum(por_fase.values())
    ultimo = re.findall(r"Acumulado do projeto[^:]*: (?:≤ )?US\$ ([0-9,]+)\*\*", CUSTOS)[-1]
    assert abs(total - float(ultimo.replace(",", "."))) < 5e-7, (total, ultimo)
    return {"por_fase": {f: round(v, 7) for f, v in por_fase.items()}, "total": round(total, 7), "ultimo_acumulado": ultimo}


if __name__ == "__main__":
    print(somar())
