"""Testes da Fase 5 — Gates deterministicos de fidelidade e registro de conferencias."""

from __future__ import annotations

import sqlite3

import pytest

from sistema.build import main as build_main
from sistema.config import LABORATORIO_DB


@pytest.fixture(scope="module")
def banco_fidelidade() -> sqlite3.Connection:
    if not LABORATORIO_DB.exists():
        build_main(["--camada", "tudo"])
    else:
        c = sqlite3.connect(LABORATORIO_DB)
        cnt = c.execute("SELECT COUNT(*) FROM conferencia WHERE severidade = 'gate_ok'").fetchone()[0]
        c.close()
        if cnt == 0:
            build_main(["--camada", "normalizado"])
    conn = sqlite3.connect(LABORATORIO_DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def test_zero_gate_falha_e_todos_gates_ok(banco_fidelidade: sqlite3.Connection) -> None:
    falhas = banco_fidelidade.execute(
        "SELECT chave, descricao FROM conferencia WHERE severidade = 'gate_falha'"
    ).fetchall()
    assert falhas == []

    gates_ok = {
        r[0]
        for r in banco_fidelidade.execute(
            "SELECT regra FROM conferencia WHERE severidade = 'gate_ok'"
        ).fetchall()
    }
    assert {
        "gate_cobertura_bruto",
        "gate_diario_partidas_dobradas",
        "gate_diario_vs_razao",
        "gate_balancete_pdf_vs_xlsx",
        "gate_consolidado_vs_individual_goiania",
        "gate_extratos_saldos_recalculados",
        "gate_integridade_camada3",
    }.issubset(gates_ok)


def test_conflitos_deliberados_registrados_em_conferencia(banco_fidelidade: sqlite3.Connection) -> None:
    regras = {r[0] for r in banco_fidelidade.execute("SELECT regra FROM conferencia").fetchall()}
    assert {
        "sigaa_html_vazio",
        "gate_sigaa_html_vazio",
        "cpf_compartilhado_pessoas_distintas",
        "versoes_empresa_d2_vs_d4",
        "prazo_dossie4_divergente",
    }.issubset(regras)
