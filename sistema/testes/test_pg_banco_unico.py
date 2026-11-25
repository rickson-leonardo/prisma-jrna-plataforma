"""Testes estruturais e de integridade do banco unico PostgreSQL 17 (lab_contabil)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg2
import pytest

from sistema.config import LABORATORIO_DB
from sistema.pg.db import ENV_PATH, conectar_pg, obter_database_url
from sistema.pg.migrar_para_pg import extrair_criterios_matrizes_d1, migrar_staging_para_pg


def _pg_disponivel() -> bool:
    try:
        obter_database_url()
        conn = conectar_pg()
        conn.close()
        return True
    except Exception:
        return False


def test_extracoes_criterios_matrizes_d1_pesos_100() -> None:
    """Valida offline a extracao dos 200 criterios reais das 4 matrizes do D1 (peso=100 cada)."""
    assert LABORATORIO_DB.exists(), "Rode 'python -m sistema.build --camada tudo' antes."
    sl = sqlite3.connect(LABORATORIO_DB)
    try:
        criterios = extrair_criterios_matrizes_d1(sl)
    finally:
        sl.close()

    assert len(criterios) == 200
    por_matriz: dict[str, list] = {}
    for c in criterios:
        por_matriz.setdefault(c.matriz, []).append(c)

    assert {k: len(v) for k, v in por_matriz.items()} == {
        "plano_negocios": 51,
        "contrato_social": 54,
        "memorando": 52,
        "fluxo_abertura": 43,
    }
    for mat, itens in por_matriz.items():
        blocos = {i.bloco: i.bloco_peso for i in itens}
        assert sum(blocos.values()) == 100, f"Peso da matriz {mat} != 100"


@pytest.mark.skipif(
    not _pg_disponivel(),
    reason=f"PostgreSQL 17 sem credencial configurada em {ENV_PATH} / DATABASE_URL.",
)
def test_pg_banco_unico_integridade_completa() -> None:
    res = migrar_staging_para_pg(gerar_backup=False)
    assert res["banco"] == "lab_contabil"

    conn = conectar_pg()
    sl = sqlite3.connect(LABORATORIO_DB)
    try:
        with conn.cursor() as cur:
            # 1. Zero Foreign Keys sem indice nos schemas acervo, erp e auditoria
            cur.execute("SELECT * FROM auditoria.vw_pg_fks_sem_indice")
            sem_idx = cur.fetchall()
            assert sem_idx == [], f"FKs sem indice encontradas: {sem_idx}"

            # 2. Paridade exata SQLite -> PostgreSQL 17
            pares = [
                ("bru_arquivo", "acervo.bru_arquivo"),
                ("bru_linha", "acervo.bru_linha"),
                ("bru_celula", "acervo.bru_celula"),
                ("bru_paragrafo", "acervo.bru_paragrafo"),
                ("ext_documento", "acervo.ext_documento"),
                ("nrm_lancamento", "erp.lancamento"),
                ("nrm_partida", "erp.partida"),
                ("nrm_movimento_bancario", "erp.movimento_bancario"),
                ("nrm_transacao", "erp.transacao"),
                ("evidencia", "auditoria.evidencia"),
                ("conferencia", "auditoria.conferencia"),
            ]
            for tab_sl, tab_pg in pares:
                cnt_sl = sl.execute(f"SELECT COUNT(*) FROM {tab_sl}").fetchone()[0]
                if tab_pg == "erp.lancamento":
                    cur.execute("SELECT COUNT(*) AS c FROM erp.lancamento WHERE origem_registro = 'acervo_sigaa'")
                elif tab_pg == "erp.partida":
                    cur.execute("SELECT COUNT(*) AS c FROM erp.partida pt JOIN erp.lancamento l ON l.id = pt.lancamento_id WHERE l.origem_registro = 'acervo_sigaa'")
                else:
                    cur.execute(f"SELECT COUNT(*) AS c FROM {tab_pg}")
                cnt_pg = int(cur.fetchone()["c"])
                assert cnt_pg == cnt_sl, f"Divergencia {tab_sl} ({cnt_sl}) vs {tab_pg} ({cnt_pg})"

            # 3. Catalogo de conformidade e placar ativos (D1 isolado)
            cur.execute("SELECT COUNT(*) AS c FROM auditoria.criterio_conformidade WHERE dossie = 'D1'")
            assert int(cur.fetchone()["c"]) == 200
            cur.execute("SELECT empresa_chave, matriz FROM auditoria.vw_placar_conformidade WHERE dossie = 'D1'")
            assert len(cur.fetchall()) == 4

            # 4. Protecao de dados humanos (origem_registro = 'usuario') no re-import
            cur.execute("SELECT id FROM erp.pessoa WHERE chave = 'pes:pj:prisma_jrna_g07'")
            pid = int(cur.fetchone()["id"])
            cur.execute(
                """
                INSERT INTO erp.empresa (chave, pessoa_id, nome_curto, papel_no_caso, origem_registro)
                VALUES ('emp:teste_usuario_temp', %s, 'Escritorio Teste Temporario', 'escritorio_contabil', 'usuario')
                ON CONFLICT (chave) DO NOTHING
                """,
                (pid,),
            )
            conn.commit()

            migrar_staging_para_pg(gerar_backup=False)
            cur.execute("SELECT nome_curto, origem_registro FROM erp.empresa WHERE chave = 'emp:teste_usuario_temp'")
            row_u = cur.fetchone()
            assert row_u is not None and row_u["origem_registro"] == "usuario"
            cur.execute("DELETE FROM erp.empresa WHERE chave = 'emp:teste_usuario_temp'")
            conn.commit()

            # 5. Trigger de Partidas Dobradas bloqueia COMMIT com D != C
            cur.execute("SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07'")
            emp_id = int(cur.fetchone()["id"])
            cur.execute("SELECT id FROM erp.conta_contabil LIMIT 1")
            cc_id = int(cur.fetchone()["id"])

            cur.execute(
                """
                INSERT INTO erp.lancamento (chave, empresa_id, ano, numero_lancamento, data_lancamento, historico, origem_registro)
                VALUES ('lanc:teste_desb', %s, 2026, 99991, '2026-09-14', 'Teste trigger D!=C', 'usuario')
                RETURNING id
                """,
                (emp_id,),
            )
            lid = int(cur.fetchone()["id"])
            cur.execute(
                """
                INSERT INTO erp.partida (chave, lancamento_id, ordem, conta_id, dc, valor_centavos)
                VALUES ('part:teste_desb:1', %s, 1, %s, 'D', 1000),
                       ('part:teste_desb:2', %s, 2, %s, 'C', 500)
                """,
                (lid, cc_id, lid, cc_id),
            )
            with pytest.raises(psycopg2.errors.RaiseException):
                conn.commit()
            conn.rollback()
    finally:
        sl.close()
        conn.close()
