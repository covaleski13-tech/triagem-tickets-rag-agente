import psycopg
import pytest

from triagem_rag.dados import SEED, ler_splits, treino
from triagem_rag.recuperacao import COLECAO, buscar_fulltext, buscar_vetorial, montar_tsquery, pg_dsn_psycopg

pytestmark = pytest.mark.db

SQL_IDS_VET = ("SELECT (e.cmetadata->>'id')::int FROM langchain_pg_embedding e "
               "JOIN langchain_pg_collection c ON e.collection_id = c.uuid WHERE c.name = %s")


@pytest.fixture(scope="module")
def con():
    with psycopg.connect(pg_dsn_psycopg()) as c:
        yield c


def test_indice_sem_holdout(con):
    sp = ler_splits()
    holdout = set(sp.loc[sp.split_grupo == "holdout", "id"])
    ids_vet = {r[0] for r in con.execute(SQL_IDS_VET, (COLECAO,))}
    ids_vet_doc = {int(r[0]) for r in con.execute(
        "SELECT e.id FROM langchain_pg_embedding e JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
        "WHERE c.name = %s", (COLECAO,))}
    ids_fts = {r[0] for r in con.execute("SELECT id FROM tickets_fts")}
    assert not (ids_vet & holdout)
    assert not (ids_vet_doc & holdout)
    assert not (ids_fts & holdout)


def test_tsquery_or(con):
    # a consulta é montada no SQL (emenda F1), por isso o teste precisa do banco
    assert montar_tsquery(con, "printer jam office") == "'jam' | 'offic' | 'printer'"
    assert montar_tsquery(con, "") == ""
    assert montar_tsquery(con, "the of a") == ""
    # aspas simples e ':' no texto: o parser separa os tokens e o resultado continua uma tsquery válida
    q = montar_tsquery(con, "it's printer:jam o'brien 10:30")
    assert q == "'10' | '30' | 'brien' | 'jam' | 'o' | 'printer'"
    assert con.execute("SELECT %s::tsquery::text", (q,)).fetchone()[0] == q
    # lexema com aspas e ':' dentro (o parser english não gera, mas o escape tem de aguentar):
    # mesma expressão de montar_tsquery, aplicada a uma tsvector literal
    assert con.execute("SELECT string_agg(quote_literal(lexeme), ' | ')::tsquery::text "
                       "FROM unnest($$'o''b:c' x$$::tsvector)").fetchone()[0] == "'o''b:c' | 'x'"


def test_indice_contagem(con):
    n = len(treino())
    assert n == 38270
    assert len(list(con.execute(SQL_IDS_VET, (COLECAO,)))) == n
    assert con.execute("SELECT count(*) FROM tickets_fts").fetchone()[0] == n


def test_autorrecuperacao(con):
    amostra = treino().sample(5, random_state=SEED)
    for i, texto in zip(amostra["id"], amostra["Document"]):
        assert buscar_vetorial(texto, 5)[0][0] == i
        assert i in [j for j, _, _ in buscar_fulltext(texto, 3, con=con)]


def test_hibrida_csv_igual_ao_vivo(con):
    import pandas as pd

    from triagem_rag.dados import RAIZ, ds2_com_splits
    from triagem_rag.recuperacao import buscar_hibrida
    arq = RAIZ / "results/f2/hibrida_top5_400.csv"
    if not arq.exists():
        pytest.skip("results/f2/hibrida_top5_400.csv ainda não gerado")
    hib = pd.read_csv(arq)
    texto = ds2_com_splits().set_index("id")["Document"]
    for i in hib["id_consulta"].drop_duplicates().iloc[:3]:
        esperado = hib[hib.id_consulta == i].sort_values("rank")["id_vizinho"].tolist()
        assert [j for j, _, _ in buscar_hibrida(texto[i], 5, con=con)] == esperado
