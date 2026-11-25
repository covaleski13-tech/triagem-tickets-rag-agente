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
    assert abs(s["total"] - 0.7611218) < 5e-7  # F1–F6 0,4692028 + F7 0,291919 (fechamento da F7)


def test_adaptador_data_dir_padrao(tmp_path):
    """B2: sem DATA_DIR no ambiente, o adaptador faz o comum do case resolver para o data/ do repositório."""
    import os
    import subprocess
    import sys
    amb = {k: v for k, v in os.environ.items() if k != "DATA_DIR"}
    codigo = ("import sys; sys.path.insert(0, 'src'); from triagem_rag import politica_caso; import comum; "
              "print(comum.DATA_DIR)")
    # cwd = raiz, mas sem .env carregado antes do adaptador
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=amb, capture_output=True, text=True, check=True)
    assert Path(r.stdout.strip()) == (RAIZ / "data").resolve()
