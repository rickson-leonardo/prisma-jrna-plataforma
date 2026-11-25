"""Testes da Fase 4 — Cobertura 100% do curso (D1-D3 e _paginas) e zero itens brutos sem destino."""

from __future__ import annotations

import sqlite3

import pytest

from sistema.build import main as build_main
from sistema.config import LABORATORIO_DB


@pytest.fixture(scope="module")
def banco_curso() -> sqlite3.Connection:
    if not LABORATORIO_DB.exists():
        build_main(["--camada", "tudo"])
    else:
        c = sqlite3.connect(LABORATORIO_DB)
        cnt = c.execute("SELECT COUNT(*) FROM ext_material").fetchone()[0]
        c.close()
        if cnt == 0:
            build_main(["--camada", "extraido"])
    conn = sqlite3.connect(LABORATORIO_DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def test_cobertura_100_por_cento_camada_bruta(banco_curso: sqlite3.Connection) -> None:
    linhas_sem = banco_curso.execute("SELECT COUNT(*) FROM bru_linha WHERE destino IS NULL").fetchone()[0]
    celulas_sem = banco_curso.execute("SELECT COUNT(*) FROM bru_celula WHERE destino IS NULL").fetchone()[0]
    pars_sem = banco_curso.execute("SELECT COUNT(*) FROM bru_paragrafo WHERE destino IS NULL").fetchone()[0]
    assert (linhas_sem, celulas_sem, pars_sem) == (0, 0, 0)


def test_materiais_curso_e_53_devolutivas_extraidas(banco_curso: sqlite3.Connection) -> None:
    mats = banco_curso.execute("SELECT COUNT(*) FROM ext_material").fetchone()[0]
    secs = banco_curso.execute("SELECT COUNT(*) FROM ext_secao").fetchone()[0]
    devs = banco_curso.execute("SELECT COUNT(*) FROM ext_material WHERE categoria = 'devolutiva'").fetchone()[0]
    assert mats == 76  # 13 PDFs fora D4 + 63 arquivos texto/docx/html/txt/.2026
    assert secs > 200
    assert devs == 53  # 30 D1 + 23 D2

    g07 = banco_curso.execute(
        """
        SELECT GROUP_CONCAT(s.conteudo, '\n')
        FROM ext_secao s
        JOIN ext_material m ON m.id = s.material_id
        JOIN bru_arquivo a ON a.id = m.arquivo_id
        WHERE a.nome = 'Devolutiva_Dossie1_G07.docx'
        """
    ).fetchone()[0]
    assert "Prisma JRNA Auditoria e Contabilidade Ltda." in g07
    assert "4.77" in g07
