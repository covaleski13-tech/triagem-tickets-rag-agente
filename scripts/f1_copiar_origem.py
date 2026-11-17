"""F1 passos 2 e 4: copia os artefatos do case a partir do blob git do commit 3a880f2 (só leitura no fork)
e escreve docs/origem.md. A âncora de proveniência é o blob, não a cópia em disco: o checkout do case no
Windows tem CRLF, que não é o conteúdo versionado."""
import hashlib
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CASE = Path(os.environ.get("CASE_DIR", r"C:\Users\gusta\challenge-g4-ai-master"))
FORK = CASE / "ai-master-challenge"
SOL = "submissions/gustavo-covaleski/solution"
COMMIT = "3a880f2"
CABECALHO = (f"# Origem: case técnico do G4, PR #228 "
             f"(https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228), commit {COMMIT},\n"
             f"# arquivo {{orig}}. Copiado sem alterar a lógica; só este cabeçalho foi adicionado.\n")

# (caminho no fork em 3a880f2, destino)
ARQUIVOS = [
    (f"{SOL}/triagem.py", "src/triagem_rag/caso/triagem.py"),
    (f"{SOL}/comum.py", "src/triagem_rag/caso/comum.py"),
    (f"{SOL}/prompts/classificar_v1.txt", "prompts/classificar_v1.txt"),
    (f"{SOL}/tests/golden/golden_v1.jsonl", "tests/golden/golden_v1.jsonl"),
    (f"{SOL}/tests/golden/ataques_v1.json", "tests/golden/ataques_v1.json"),
    (f"{SOL}/outputs/f1_splits.csv", "data/f1_splits.csv"),
    (f"{SOL}/outputs/f3_probs_holdout_grupo.csv", "data/caso/f3_probs_holdout_grupo.csv"),
    (f"{SOL}/outputs/f8_politica_por_categoria.csv", "data/caso/f8_politica_por_categoria.csv"),
    (f"{SOL}/outputs/f8_faixas.json", "data/caso/f8_faixas.json"),
]
# fora do fork (sem blob): o CSV bruto do DS2 vem do Kaggle e fica em data/raw/, fora do git
RAW = (CASE / "data/all_tickets_processed_improved_v3.csv", "data/raw/all_tickets_processed_improved_v3.csv")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args) -> bytes:
    return subprocess.run(["git", "-C", str(FORK), *args], check=True, capture_output=True).stdout


def main():
    linhas = ["# Origem dos artefatos reaproveitados do case", "",
              f"Case: PR #228 (https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228), "
              f"commit `{COMMIT}`.",
              "Gerado por `python scripts/f1_copiar_origem.py`. A âncora de proveniência é o blob git do arquivo em "
              f"`{COMMIT}` (`git rev-parse {COMMIT}:<caminho>` no fork); o SHA-256 da origem é calculado sobre o "
              f"conteúdo do blob (`git show {COMMIT}:<caminho>`), não sobre o checkout em disco. Nos `.py`, a "
              "coluna \"destino sem cabeçalho\" remove as 2 linhas de origem adicionadas e deve ser igual ao "
              "SHA-256 da origem.", "",
              f"| Origem (fork, `{COMMIT}`) | Destino | blob git ({COMMIT}) | SHA-256 origem (blob) | "
              "SHA-256 destino | SHA-256 destino sem cabeçalho |",
              "|---|---|---|---|---|---|"]
    for orig, dest in ARQUIVOS:
        blob_id = git("rev-parse", f"{COMMIT}:{orig}").decode().strip()
        bruto = git("show", f"{COMMIT}:{orig}")
        d = RAIZ / dest
        d.parent.mkdir(parents=True, exist_ok=True)
        if orig.endswith(".py"):
            cab = CABECALHO.format(orig=orig).encode("utf-8")
            d.write_bytes(cab + bruto)
            sem = d.read_bytes()[len(cab):]
            assert sha(sem) == sha(bruto)
            col_sem = f"`{sha(sem)}`"
        else:
            d.write_bytes(bruto)
            assert d.read_bytes() == bruto
            col_sem = "—"
        linhas.append(f"| `{orig}` | `{dest}` | `{blob_id}` | `{sha(bruto)}` | `{sha(d.read_bytes())}` | {col_sem} |")

    raw_orig, raw_dest = RAW
    if not raw_orig.exists():
        raise SystemExit(f"origem ausente: {raw_orig}")
    d = RAIZ / raw_dest
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_bytes(raw_orig.read_bytes())
    linhas.append(f"| `{raw_orig.relative_to(CASE).as_posix()}` (fora do fork) | `{raw_dest}` | — | "
                  f"`{sha(raw_orig.read_bytes())}` (arquivo em disco) | `{sha(d.read_bytes())}` | — |")

    linhas += ["", "`data/raw/` fica fora do git; o SHA-256 do CSV bruto do DS2 é o do arquivo em disco.",
               "`planning/F3/f3_llm_log.jsonl` (fora do fork) não é copiado: dele derivam "
               "`data/amostra_400_ids.csv` e `data/caso/f3_v0_pred.csv` (`python scripts/f1_amostra.py`)."]
    with open(RAIZ / "docs/origem.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas) + "\n")
    print("ok:", len(ARQUIVOS) + 1, "arquivos")


if __name__ == "__main__":
    main()
