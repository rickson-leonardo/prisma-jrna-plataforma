"""Camada 3 — Normalizacao em 3FN, linhagem (evidencia) e resolucao de entidades."""

from __future__ import annotations

import sqlite3

from sistema.normalizacao.entidades import normalizar_cadastro_e_historia
from sistema.normalizacao.operacoes import normalizar_operacoes_e_contabilidade


def normalizar_tudo(conn: sqlite3.Connection) -> dict[str, int]:
    """Executa toda a Camada 3 (cadastro temporal + operacoes + curso + evidencia)."""
    ctx = normalizar_cadastro_e_historia(conn)
    res_ops = normalizar_operacoes_e_contabilidade(conn, ctx)
    return {
        "pessoas": len(ctx.pessoas_por_chave),
        "empresas": len(ctx.empresas_por_chave),
        "estabelecimentos": len(ctx.estabelecimentos_por_chave),
        "contas_bancarias": len(ctx.contas_por_chave),
        "eventos": ctx.n_eventos,
        "fatos": ctx.n_fatos,
        **res_ops,
    }
