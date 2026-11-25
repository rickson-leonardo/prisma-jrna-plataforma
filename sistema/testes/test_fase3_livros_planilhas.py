"""Testes da Fase 3 — Livros contabeis, balancetes, extratos e planilhas."""

from __future__ import annotations

import sqlite3

import pytest

from sistema.build import main as build_main
from sistema.config import LABORATORIO_DB


@pytest.fixture(scope="module")
def banco_extraido() -> sqlite3.Connection:
    if not LABORATORIO_DB.exists():
        build_main(["--camada", "tudo"])
    else:
        conn_check = sqlite3.connect(LABORATORIO_DB)
        cnt = conn_check.execute("SELECT COUNT(*) FROM ext_diario_lancamento").fetchone()[0]
        conn_check.close()
        if cnt == 0:
            build_main(["--camada", "extraido"])
    conn = sqlite3.connect(LABORATORIO_DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def test_diarios_contagens_e_totais_batem(banco_extraido: sqlite3.Connection) -> None:
    c2025 = banco_extraido.execute(
        "SELECT COUNT(*), SUM(CASE WHEN tag_ref IS NOT NULL THEN 1 ELSE 0 END) FROM ext_diario_lancamento WHERE ano = 2025"
    ).fetchone()
    c2026 = banco_extraido.execute(
        "SELECT COUNT(*), SUM(CASE WHEN tag_ref IS NOT NULL THEN 1 ELSE 0 END) FROM ext_diario_lancamento WHERE ano = 2026"
    ).fetchone()
    assert c2025 == (1134, 1098)
    assert c2026 == (739, 715)

    # D = C em 100% dos 1.873 lancamentos
    desbalanceados = banco_extraido.execute(
        """
        SELECT l.ano, l.numero_lancamento,
               SUM(CASE WHEN p.dc = 'D' THEN p.valor_centavos ELSE 0 END) AS deb,
               SUM(CASE WHEN p.dc = 'C' THEN p.valor_centavos ELSE 0 END) AS cred
        FROM ext_diario_lancamento l
        JOIN ext_diario_partida p ON p.lancamento_id = l.id
        GROUP BY l.id
        HAVING deb != cred
        """
    ).fetchall()
    assert desbalanceados == []

    # Totais do periodo impressos no Diario
    tot2025 = banco_extraido.execute(
        """
        SELECT SUM(CASE WHEN p.dc = 'D' THEN p.valor_centavos ELSE 0 END),
               SUM(CASE WHEN p.dc = 'C' THEN p.valor_centavos ELSE 0 END)
        FROM ext_diario_partida p
        JOIN ext_diario_lancamento l ON l.id = p.lancamento_id
        WHERE l.ano = 2025
        """
    ).fetchone()
    assert tot2025 == (1448951175, 1448951175)

    tot2026 = banco_extraido.execute(
        """
        SELECT SUM(CASE WHEN p.dc = 'D' THEN p.valor_centavos ELSE 0 END),
               SUM(CASE WHEN p.dc = 'C' THEN p.valor_centavos ELSE 0 END)
        FROM ext_diario_partida p
        JOIN ext_diario_lancamento l ON l.id = p.lancamento_id
        WHERE l.ano = 2026
        """
    ).fetchone()
    assert tot2026 == (905074606, 905074606)


def test_razao_e_balancetes_pdf_vs_xlsx(banco_extraido: sqlite3.Connection) -> None:
    raz_2025 = banco_extraido.execute("SELECT COUNT(*) FROM ext_razao_linha WHERE ano = 2025").fetchone()[0]
    raz_2026 = banco_extraido.execute("SELECT COUNT(*) FROM ext_razao_linha WHERE ano = 2026").fetchone()[0]
    assert raz_2025 > 2000
    assert raz_2026 > 1000

    periodos_pdf = banco_extraido.execute(
        "SELECT COUNT(DISTINCT periodo) FROM ext_balancete_linha WHERE fonte = 'pdf'"
    ).fetchone()[0]
    periodos_xlsx = banco_extraido.execute(
        "SELECT COUNT(DISTINCT periodo) FROM ext_balancete_linha WHERE fonte = 'xlsx'"
    ).fetchone()[0]
    assert periodos_pdf == 21
    assert periodos_xlsx == 22  # 21 mensais + abertura 2024-12

    # Conferir que todos os 21 periodos coincidem 100% entre PDF e XLSX
    diffs = banco_extraido.execute(
        """
        SELECT p.periodo, p.conta_codigo, p.saldo_atual_centavos, x.saldo_atual_centavos
        FROM ext_balancete_linha p
        JOIN ext_balancete_linha x
          ON x.fonte = 'xlsx' AND x.periodo = p.periodo AND x.conta_codigo = p.conta_codigo
        WHERE p.fonte = 'pdf'
          AND (
            p.saldo_anterior_centavos != x.saldo_anterior_centavos
            OR p.debito_centavos != x.debito_centavos
            OR p.credito_centavos != x.credito_centavos
            OR p.saldo_atual_centavos != x.saldo_atual_centavos
          )
        """
    ).fetchall()
    assert diffs == []


def test_extratos_e_cobertura_100_por_cento_planilhas_e_livros(banco_extraido: sqlite3.Connection) -> None:
    contas = dict(
        banco_extraido.execute(
            "SELECT conta_codigo, COUNT(*) FROM ext_extrato_linha GROUP BY conta_codigo"
        ).fetchall()
    )
    assert set(contas.keys()) == {"matriz_2025", "matriz_2026", "filial", "goiania"}
    assert contas["goiania"] == 428

    calc_goiania = banco_extraido.execute(
        "SELECT COUNT(*) FROM ext_extrato_linha WHERE conta_codigo = 'goiania' AND origem_valor = 'calculado_formula'"
    ).fetchone()[0]
    assert calc_goiania == 428

    saldo_ago_ini = banco_extraido.execute(
        "SELECT valor_texto FROM ext_parametro_planilha WHERE chave = 'param:extrato:goiania:L411'"
    ).fetchone()[0]
    assert saldo_ago_ini != "2026-08-01 | 0"

    # 0 celulas sem destino em bru_celula
    cel_sem_dest = banco_extraido.execute(
        "SELECT COUNT(*) FROM bru_celula WHERE destino IS NULL"
    ).fetchone()[0]
    assert cel_sem_dest == 0

    # 0 linhas sem destino nos 4 livros e no balancete PDF
    lin_sem_dest = banco_extraido.execute(
        """
        SELECT a.caminho_relativo, COUNT(*)
        FROM bru_linha l
        JOIN bru_arquivo a ON a.id = l.arquivo_id
        WHERE a.caminho_relativo IN (
            'D4/Livro_Diario_2025.pdf',
            'D4/Livro_Diario_2026.pdf',
            'D4/Livro_Razao_2025.pdf',
            'D4/Livro_Razao_2026.pdf',
            'D4/Balancetes_Verificacao_Mensais_2025-2026.pdf'
        )
          AND l.destino IS NULL
        GROUP BY a.id
        """
    ).fetchall()
    assert lin_sem_dest == []
