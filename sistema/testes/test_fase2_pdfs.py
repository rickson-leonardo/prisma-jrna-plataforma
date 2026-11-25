"""Testes da Fase 2 — Motor declarativo, 51 modelos de PDF e cobertura 100% do D4."""

from __future__ import annotations

import json
import sqlite3

import pytest

from sistema.build import main as build_main
from sistema.config import LABORATORIO_DB
from sistema.extracao.modelos import CATALOGO_MODELOS


@pytest.fixture(scope="module")
def banco_pdfs() -> sqlite3.Connection:
    if not LABORATORIO_DB.exists():
        build_main(["--camada", "tudo"])
    else:
        conn_check = sqlite3.connect(LABORATORIO_DB)
        cnt = conn_check.execute("SELECT COUNT(*) FROM ext_documento").fetchone()[0]
        conn_check.close()
        if cnt == 0:
            build_main(["--camada", "extraido"])
    conn = sqlite3.connect(LABORATORIO_DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def test_todos_51_modelos_extraidos_e_zero_linhas_sem_destino_d4(banco_pdfs: sqlite3.Connection) -> None:
    assert len(CATALOGO_MODELOS) == 51

    total_docs = banco_pdfs.execute("SELECT COUNT(*) FROM ext_documento").fetchone()[0]
    assert total_docs == 2191

    modelos_no_banco = {
        r[0] for r in banco_pdfs.execute("SELECT DISTINCT modelo FROM ext_documento").fetchall()
    }
    assert modelos_no_banco == set(CATALOGO_MODELOS.keys())

    sem_dest = banco_pdfs.execute(
        """
        SELECT a.caminho_relativo, COUNT(*)
        FROM bru_linha l
        JOIN bru_arquivo a ON a.id = l.arquivo_id
        WHERE a.dossie = 'D4' AND l.destino IS NULL
        GROUP BY a.id
        """
    ).fetchall()
    assert sem_dest == []


def test_gabarito_documentos_representativos(banco_pdfs: sqlite3.Connection) -> None:
    # 1. NFe-1243
    nfe1243 = banco_pdfs.execute(
        """
        SELECT d.modelo, d.numero, d.data_emissao, d.doc_ref, d.valor_total_centavos, d.moeda
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        WHERE a.nome = 'M01_2025-01-04_TRF106997_01_NFe-1243.pdf'
        """
    ).fetchone()
    assert nfe1243 == ("NFe", "1.243 / 1", "2025-01-02", "TRF106997", 964272, "BRL")

    # 2. Commercial-Invoice em USD
    inv = banco_pdfs.execute(
        """
        SELECT d.modelo, d.doc_ref, d.data_emissao, d.valor_total_centavos, d.moeda
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        WHERE a.nome = 'G016_2026-01-12_CAMB546217_02_Commercial-Invoice.pdf'
        """
    ).fetchone()
    assert inv == ("Commercial-Invoice", "CAMB546217", "2025-12-22", 4889390, "USD")

    # 3. Contrato-cambio
    camb = banco_pdfs.execute(
        """
        SELECT d.modelo, d.doc_ref, d.data_emissao, d.valor_total_centavos
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        WHERE a.nome = 'M04_2025-01-08_CAMB151714_01_Contrato-cambio.pdf'
        """
    ).fetchone()
    assert camb == ("Contrato-cambio", "CAMB151714", "2025-01-08", 10127923)

    # 4. Cronograma-pagamentos (60 parcelas + linha TOTAIS em 2 paginas)
    doc_cron_id = banco_pdfs.execute(
        """
        SELECT d.id FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        WHERE a.nome = 'M25_2025-04-18_EMP2221_02_Cronograma-pagamentos.pdf'
        """
    ).fetchone()[0]
    itens_cron = banco_pdfs.execute(
        "SELECT COUNT(*) FROM ext_item WHERE documento_id = ?", (doc_cron_id,)
    ).fetchone()[0]
    assert itens_cron == 61  # 60 parcelas + 1 linha TOTAIS

    # 5. Extrato-DI (2 adicoes + linha TOTAIS + itens de debito em conta)
    di = banco_pdfs.execute(
        """
        SELECT d.numero, d.data_emissao, d.valor_total_centavos
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        WHERE a.nome = 'G021_2026-02-13_DI423697_01_Extrato-DI.pdf'
        """
    ).fetchone()
    assert di == ("26/0001505-3", "2026-02-13", 26392927)

    # 6. Recibo em prosa (Recibo-prolabore)
    rec = banco_pdfs.execute(
        """
        SELECT d.modelo, d.data_emissao, d.valor_total_centavos
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        WHERE a.nome = 'G006_2026-01-05_PIX999674_01_Recibo-prolabore.pdf'
        """
    ).fetchone()
    assert rec == ("Recibo-prolabore", "2026-01-05", 162100)


def test_cli_filtro_modelo_reextrai_sem_quebrar_demais() -> None:
    rc = build_main(["--camada", "extraido", "--modelo", "Guia-AFRMM"])
    assert rc == 0
    conn = sqlite3.connect(LABORATORIO_DB)
    try:
        cnt = conn.execute("SELECT COUNT(*) FROM ext_documento WHERE modelo = 'Guia-AFRMM'").fetchone()[0]
        assert cnt == 4
        sem_dest = conn.execute(
            """
            SELECT COUNT(*) FROM bru_linha l
            JOIN bru_arquivo a ON a.id = l.arquivo_id
            WHERE a.dossie = 'D4' AND l.destino IS NULL
            """
        ).fetchone()[0]
        assert sem_dest == 0
    finally:
        conn.close()
