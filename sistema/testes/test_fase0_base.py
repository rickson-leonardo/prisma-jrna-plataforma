"""Testes da Fase 0 — Base, schemas SQL, docs e preservacao de trabalho.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sistema.build import inicializar_bancos
from sistema.config import SCHEMA_DIR
from sistema.gerar_docs import gerar_documentacao


def test_schemas_aplicam_sem_erros_e_fks_ok(tmp_path: Path) -> None:
    lab_db = tmp_path / "laboratorio.db"
    trab_db = tmp_path / "trabalho.db"
    conn_lab, conn_trab = inicializar_bancos(lab_db, trab_db, recriar_lab=True)
    try:
        fk_lab = conn_lab.execute("PRAGMA foreign_key_check;").fetchall()
        fk_trab = conn_trab.execute("PRAGMA foreign_key_check;").fetchall()
        assert fk_lab == []
        assert fk_trab == []

        tabelas_lab = {
            r[0]
            for r in conn_lab.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for obrig in (
            "bru_arquivo",
            "bru_zip_entrada",
            "bru_linha",
            "bru_celula",
            "bru_paragrafo",
            "bru_sigaa_item",
            "ext_documento",
            "ext_diario_lancamento",
            "nrm_empresa",
            "nrm_transacao",
            "evidencia",
            "conferencia",
        ):
            assert obrig in tabelas_lab

        tabelas_trab = {
            r[0]
            for r in conn_trab.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"anotacao", "decisao", "classificacao", "resposta_requisito"}.issubset(tabelas_trab)
    finally:
        conn_lab.close()
        conn_trab.close()


def test_trabalho_db_preservado_no_rebuild(tmp_path: Path) -> None:
    lab_db = tmp_path / "laboratorio.db"
    trab_db = tmp_path / "trabalho.db"

    conn_lab, conn_trab = inicializar_bancos(lab_db, trab_db, recriar_lab=True)
    conn_trab.execute(
        "INSERT INTO anotacao (chave, alvo_tabela, alvo_chave, autor, dossie, conteudo) "
        "VALUES ('anot:1', 'bru_arquivo', 'arq:D4/M01_2025-01-04_TRF106997_01_NFe-1243.pdf', 'dupla', 'D4', 'Teste')"
    )
    conn_trab.commit()
    conn_lab.close()
    conn_trab.close()

    conn_lab2, conn_trab2 = inicializar_bancos(lab_db, trab_db, recriar_lab=True)
    try:
        rows = conn_trab2.execute("SELECT chave, alvo_chave, conteudo FROM anotacao").fetchall()
        assert rows == [("anot:1", "arq:D4/M01_2025-01-04_TRF106997_01_NFe-1243.pdf", "Teste")]
    finally:
        conn_lab2.close()
        conn_trab2.close()


def test_gerar_docs_cria_dicionario_e_er(tmp_path: Path) -> None:
    lab_db = tmp_path / "laboratorio.db"
    trab_db = tmp_path / "trabalho.db"
    docs_dir = tmp_path / "docs"
    conn_lab, conn_trab = inicializar_bancos(lab_db, trab_db, recriar_lab=True)
    conn_lab.close()
    conn_trab.close()

    dic, er = gerar_documentacao(lab_db, trab_db, docs_dir)
    assert dic.exists() and er.exists()
    assert "bru_arquivo" in dic.read_text(encoding="utf-8")
    assert "erDiagram" in er.read_text(encoding="utf-8")
    assert len(list(SCHEMA_DIR.glob("*.sql"))) == 5
