"""Testes das Fases 6 e 7 — Camada 3 3FN, evidencia, transacoes, views e trabalho.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sistema.build import main as build_main
from sistema.config import LABORATORIO_DB, TRABALHO_DB


@pytest.fixture(scope="module")
def bancos_completos() -> tuple[sqlite3.Connection, sqlite3.Connection]:
    if not LABORATORIO_DB.exists():
        build_main(["--camada", "tudo"])
    else:
        c = sqlite3.connect(LABORATORIO_DB)
        cnt = c.execute("SELECT COUNT(*) FROM nrm_transacao").fetchone()[0]
        c.close()
        if cnt == 0:
            build_main(["--camada", "tudo"])
    conn_lab = sqlite3.connect(LABORATORIO_DB)
    conn_lab.execute("PRAGMA foreign_keys = ON;")
    conn_trab = sqlite3.connect(TRABALHO_DB)
    conn_trab.execute("PRAGMA foreign_keys = ON;")
    yield conn_lab, conn_trab
    conn_lab.close()
    conn_trab.close()


def test_todas_tabelas_nrm_populadas_fks_e_evidencias_ok(
    bancos_completos: tuple[sqlite3.Connection, sqlite3.Connection],
) -> None:
    conn_lab, conn_trab = bancos_completos
    assert conn_lab.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn_trab.execute("PRAGMA foreign_key_check").fetchall() == []

    nrm_tabs = [
        r[0]
        for r in conn_lab.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'nrm_%' ORDER BY name"
        ).fetchall()
    ]
    assert len(nrm_tabs) == 46
    for tab in nrm_tabs:
        assert conn_lab.execute(f"SELECT COUNT(*) FROM {tab}").fetchone()[0] > 0, f"Tabela vazia: {tab}"
        assert conn_lab.execute("SELECT COUNT(*) FROM evidencia WHERE tabela_destino = ?", (tab,)).fetchone()[0] > 0, (
            f"Sem evidencia: {tab}"
        )


def test_pessoas_temporais_e_navegacao_doc_ref(
    bancos_completos: tuple[sqlite3.Connection, sqlite3.Connection],
) -> None:
    conn_lab, _ = bancos_completos

    # Helena D4 e Tereza mantidas distintas apesar do CPF compartilhado
    pessoas = {
        r[0]: r[1]
        for r in conn_lab.execute(
            "SELECT chave, nome_canonico FROM nrm_pessoa WHERE chave IN ('pes:pf:helena_duarte_lima', 'pes:pf:tereza_cristina_alves_brandao')"
        ).fetchall()
    }
    assert len(pessoas) == 2

    # As 4 empresas centrais + G07
    emps = {r[0] for r in conn_lab.execute("SELECT chave FROM nrm_empresa").fetchall()}
    assert {"emp:rota_sul_d2", "emp:rota_sul_d4", "emp:meia_ponte", "emp:horizonte"}.issubset(emps)

    # Linha do tempo (vw_linha_do_tempo) traz fatos de capital e regime
    tl = conn_lab.execute("SELECT COUNT(*) FROM vw_linha_do_tempo").fetchone()[0]
    assert tl >= 10

    # Navegacao por Doc/Ref TRF106997 une documento, movimento bancario e lancamento
    membros = conn_lab.execute(
        """
        SELECT DISTINCT papel_membro FROM vw_navegacao_doc_ref WHERE transacao_chave = 'tx:TRF106997'
        """
    ).fetchall()
    assert {r[0] for r in membros} == {"documento", "movimento_bancario", "lancamento_contabil"}

    # Auditoria D3 (NFSe Horizonte Projetos) tem os 5 tributos
    tribs_d3 = conn_lab.execute("SELECT tributo, valor_centavos FROM vw_auditoria_retencoes_d3").fetchall()
    assert len(tribs_d3) == 5
    assert sum(r[1] for r in tribs_d3) == 106148

    # G07 marcada como nossa_dupla = 1 em nrm_devolutiva
    g07 = conn_lab.execute(
        "SELECT grupo, nossa_dupla FROM nrm_devolutiva WHERE nossa_dupla = 1"
    ).fetchall()
    assert g07 == [("G07", 1)]


def test_rebuild_completo_preserva_anotacao_no_trabalho_db(tmp_path: Path) -> None:
    conn_trab = sqlite3.connect(TRABALHO_DB)
    chave_teste = "anot:teste_persistencia_tx_TRF106997"
    conn_trab.execute(
        """
        INSERT OR REPLACE INTO anotacao (chave, alvo_tabela, alvo_chave, autor, dossie, conteudo)
        VALUES (?, 'nrm_transacao', 'tx:TRF106997', 'G07', 'D4', 'Conferencia de persistencia pos-rebuild')
        """,
        (chave_teste,),
    )
    conn_trab.commit()
    conn_trab.close()

    lab_tmp = tmp_path / "lab_rebuild.db"
    assert build_main(["--camada", "tudo", "--lab-db", str(lab_tmp)]) == 0

    conn_trab2 = sqlite3.connect(TRABALHO_DB)
    conn_lab2 = sqlite3.connect(lab_tmp)
    try:
        row = conn_trab2.execute(
            "SELECT alvo_chave, conteudo FROM anotacao WHERE chave = ?", (chave_teste,)
        ).fetchone()
        assert row == ("tx:TRF106997", "Conferencia de persistencia pos-rebuild")
        existe_tx = conn_lab2.execute("SELECT COUNT(*) FROM nrm_transacao WHERE chave = ?", (row[0],)).fetchone()[0]
        assert existe_tx == 1
        conn_trab2.execute("DELETE FROM anotacao WHERE chave = ?", (chave_teste,))
        conn_trab2.commit()
    finally:
        conn_trab2.close()
        conn_lab2.close()
