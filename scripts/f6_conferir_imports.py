"""F6 (B1): todo pacote importado diretamente em src/, scripts/ ou tests/ tem de estar no requirements.txt.
Saída: pacotes faltantes com a versão instalada (esperado: nenhum)."""
import ast
import re
import sys
from importlib.metadata import packages_distributions, version
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LOCAIS = {"triagem_rag", "comum", "triagem", "test_f4", "f5_avaliar"}


def faltantes() -> list[str]:
    mods = set()
    for p in [*RAIZ.joinpath("src").rglob("*.py"), *RAIZ.joinpath("scripts").glob("*.py"),
              *RAIZ.joinpath("tests").glob("*.py")]:
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                mods.add(n.module.split(".")[0])
    mods -= set(sys.stdlib_module_names) | LOCAIS
    req = {re.split("==", l)[0].lower().replace("_", "-")
           for l in (RAIZ / "requirements.txt").read_text().splitlines() if l and not l.startswith("-")}
    dist = packages_distributions()
    out = []
    for m in sorted(mods):
        ds = dist.get(m)
        if not ds:
            out.append(f"{m}: distribuição não encontrada")
        elif not any(d.lower().replace("_", "-") in req for d in ds):
            out.append(f"{ds[0]}=={version(ds[0])} (import {m})")
    return out


if __name__ == "__main__":
    f = faltantes()
    print("faltantes:", f or "nenhum")
    sys.exit(1 if f else 0)
