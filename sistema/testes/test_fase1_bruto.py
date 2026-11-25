"""Testes da Fase 1 — Cobertura 100% da Camada Bruta sobre o acervo real."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sistema.build import main as build_main
from sistema.config import ACERVO_DIR, LABORATORIO_DB, TRABALHO_DB


@pytest.fixture(scope="module")
def banco_bruto() -> sqlite3.Connection:
    if not LABORATORIO_DB.exists():
        build_main(["--camada", "bruto"])
    conn = sqlite3.connect(LABORATORIO_DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def test_todos_arquivos_inventariados_com_sha256(banco_bruto: sqlite3.Connection) -> None:
    total = banco_bruto.execute("SELECT COUNT(*) FROM bru_arquivo").fetchone()[0]
    assert total == 2357

    sem_hash = banco_bruto.execute(
        "SELECT COUNT(*) FROM bru_arquivo WHERE length(sha256) != 64"
    ).fetchone()[0]
    assert sem_hash == 0

    dups = banco_bruto.execute(
        "SELECT COUNT(*) FROM bru_arquivo WHERE papel_acervo = 'duplicata_sha256' AND duplicata_de_id IS NOT NULL"
    ).fetchone()[0]
    assert dups == 55

    consolidados = banco_bruto.execute(
        "SELECT COUNT(*), SUM(paginas_total) FROM bru_arquivo WHERE papel_acervo = 'consolidado_espelho'"
    ).fetchone()
    assert consolidados == (16, 847)


def test_zips_100_por_cento_mapeados(banco_bruto: sqlite3.Connection) -> None:
    total_zips = banco_bruto.execute(
        "SELECT COUNT(*) FROM bru_arquivo WHERE papel_acervo = 'container_zip'"
    ).fetchone()[0]
    assert total_zips == 8

    nao_mapeados = banco_bruto.execute(
        "SELECT COUNT(*) FROM bru_zip_entrada WHERE arquivo_disco_id IS NULL"
    ).fetchone()[0]
    assert nao_mapeados == 0


def test_pdfs_planilhas_e_documentos_extraidos(banco_bruto: sqlite3.Connection) -> None:
    pdfs_sem_linhas = banco_bruto.execute(
        """
        SELECT COUNT(*) FROM bru_arquivo a
        WHERE a.extensao = '.pdf' AND a.papel_acervo != 'duplicata_sha256'
          AND NOT EXISTS (SELECT 1 FROM bru_linha l WHERE l.arquivo_id = a.id)
        """
    ).fetchone()[0]
    assert pdfs_sem_linhas == 0

    # 6 planilhas .xlsx com formulas sem cache identificadas fielmente
    xlsx_count = banco_bruto.execute(
        "SELECT COUNT(DISTINCT arquivo_id) FROM bru_celula"
    ).fetchone()[0]
    assert xlsx_count == 6

    sem_cache = banco_bruto.execute(
        "SELECT COUNT(*) FROM bru_celula WHERE tipo_dado = 'formula' AND valor_cacheado IS NULL"
    ).fetchone()[0]
    assert sem_cache == 648

    docx_sem_par = banco_bruto.execute(
        """
        SELECT COUNT(*) FROM bru_arquivo a
        WHERE a.extensao = '.docx' AND a.papel_acervo = 'primario'
          AND NOT EXISTS (SELECT 1 FROM bru_paragrafo p WHERE p.arquivo_id = a.id)
        """
    ).fetchone()[0]
    assert docx_sem_par == 0


def test_sigaa_100_por_cento_mapeado_e_html_vazio_registrado(banco_bruto: sqlite3.Connection) -> None:
    total_sigaa, nao_mapeados = banco_bruto.execute(
        "SELECT COUNT(*), SUM(CASE WHEN arquivo_id IS NULL THEN 1 ELSE 0 END) FROM bru_sigaa_item"
    ).fetchone()
    assert total_sigaa == 135
    assert nao_mapeados == 0

    conf = banco_bruto.execute(
        "SELECT COUNT(*) FROM conferencia WHERE regra = 'sigaa_html_vazio'"
    ).fetchone()[0]
    assert conf == 1


def test_estabilidade_chaves_entre_rebuilds(tmp_path: Path) -> None:
    lab1 = tmp_path / "lab1.db"
    lab2 = tmp_path / "lab2.db"
    trab = tmp_path / "trab.db"

    assert build_main(["--camada", "bruto", "--acervo", str(ACERVO_DIR), "--lab-db", str(lab1), "--trab-db", str(trab)]) == 0
    assert build_main(["--camada", "bruto", "--acervo", str(ACERVO_DIR), "--lab-db", str(lab2), "--trab-db", str(trab)]) == 0

    c1 = sqlite3.connect(lab1)
    c2 = sqlite3.connect(lab2)
    try:
        for tabela in ("bru_arquivo", "bru_sigaa_item"):
            k1 = [r[0] for r in c1.execute(f"SELECT chave FROM {tabela} ORDER BY id").fetchall()]
            k2 = [r[0] for r in c2.execute(f"SELECT chave FROM {tabela} ORDER BY id").fetchall()]
            assert k1 == k2
    finally:
        c1.close()
        c2.close()
