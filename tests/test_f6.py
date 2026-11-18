import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_readme_numeros():
    c = _carregar("f6_conferir_readme")
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert c.faltantes(readme) == []
    assert c.links_quebrados(readme) == []
    # o conferidor acusa um número trocado
    assert c.faltantes(readme.replace("45,25%", "45,52%"))


def test_custos_somados():
    s = _carregar("f6_somar_custos").somar()
    assert abs(s["total"] - 0.4651878) < 5e-7
