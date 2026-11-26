"""Testes end-to-end da interface Flask CRUD, simulacao e exportador do Dossie 1."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from sistema.erp.importar_rascunhos_nath import importar_dossie1_quarentena
from sistema.erp.motor_contabil import recalcular_todos_cenarios_d1
from sistema.pg.db import ENV_PATH, conectar_pg, obter_database_url
from sistema.web.app import create_app
from sistema.web.exportador_dossie1 import exportar_dossie1


def _pg_disponivel() -> bool:
    try:
        obter_database_url()
        c = conectar_pg()
        c.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")


def test_web_rotas_leitura_5_estacoes() -> None:
    importar_dossie1_quarentena()
    recalcular_todos_cenarios_d1()

    app = create_app()
    client = app.test_client()

    for rota, trecho in (
        ("/", b"Painel da Contadora"),
        ("/cadastro", b"Quadro de S"),
        ("/instrumentos", b"Instrumentos Societ"),
        ("/legalizacao", b"Workflow Paralegal"),
        ("/planejamento", b"Comparativo de Teses Tribut"),
        ("/sustentacao", b"Matriz IABP"),
    ):
        resp = client.get(rota)
        assert resp.status_code == 200, f"Falha GET {rota}: {resp.status_code}"
        assert trecho in resp.data, f"Conteudo esperado ausente em {rota}"


def test_web_crud_clausula_etapa_cenario_e_exportacao(tmp_path: Path) -> None:
    app = create_app()
    client = app.test_client()

    # 1. CRUD Clausula Societaria (cria -> edita -> homologa -> exclui)
    r_add = client.post(
        "/instrumentos/clausula/nova",
        data={
            "ordem": "999",
            "bloco": "Z",
            "codigo_criterio": "Z1",
            "numero_clausula": "Cláusula Teste Temporária",
            "titulo": "Clausula CRUD Pytest",
            "aplica_contrato": "on",
            "metodo_haveres": "balanco_determinacao",
            "quorum_tipo": "unanimidade",
            "alcada_reais": "15000,00",
            "regra_texto": "Regra criada em teste automatizado CRUD.",
            "status_validacao": "pendente_revisao",
            "justificativa_contadora": "Inicial",
        },
        follow_redirects=True,
    )
    assert r_add.status_code == 200
    assert b"Clausula CRUD Pytest" in r_add.data

    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.instrumento_societario_clausula WHERE numero_clausula = 'Cláusula Teste Temporária'")
            cl_id = int(cur.fetchone()["id"])
            # Simula registro importado: a edicao na tela deve preservar o rastro de origem
            cur.execute("UPDATE erp.instrumento_societario_clausula SET origem_registro = 'importado_rascunho_v2' WHERE id = %s", (cl_id,))
        conn.commit()

    r_upd = client.post(
        f"/instrumentos/clausula/{cl_id}/salvar",
        data={
            "ordem": "999",
            "bloco": "Z",
            "codigo_criterio": "Z1",
            "numero_clausula": "Cláusula Teste Temporária",
            "titulo": "Clausula CRUD Homologada",
            "aplica_contrato": "on",
            "metodo_haveres": "balanco_determinacao",
            "quorum_tipo": "unanimidade",
            "regra_texto": "Texto revisado e homologado.",
            "status_validacao": "homologado_contadora",
            "justificativa_contadora": "Homologado em teste",
        },
        follow_redirects=True,
    )
    assert r_upd.status_code == 200
    assert b"Clausula CRUD Homologada" in r_upd.data
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT origem_registro FROM erp.instrumento_societario_clausula WHERE id = %s", (cl_id,))
            assert cur.fetchone()["origem_registro"] == "importado_rascunho_v2"

    r_del = client.post(f"/instrumentos/clausula/{cl_id}/excluir", follow_redirects=True)
    assert r_del.status_code == 200
    assert b"Clausula CRUD Homologada" not in r_del.data

    # 2. CRUD Etapa Paralegal DF
    r_leg = client.post(
        "/legalizacao/etapa/nova",
        data={
            "ordem": "99",
            "bloco": "H",
            "codigo": "H99",
            "raia_responsavel": "escritorio_contabil",
            "nome_etapa": "Etapa Pytest DF",
            "orgao": "CRC-DF",
            "entrada_docs": "Doc teste",
            "saida_doc": "Protocolo teste",
            "regra_retorno_exigencia": "Sanear em 30d",
            "classificacao_risco": "baixo",
            "status": "concluida",
            "status_validacao": "homologado_contadora",
        },
        follow_redirects=True,
    )
    assert r_leg.status_code == 200
    assert b"Etapa Pytest DF" in r_leg.data

    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.processo_legalizacao_etapa WHERE codigo = 'H99'")
            et_id = int(cur.fetchone()["id"])
    client.post(f"/legalizacao/etapa/{et_id}/excluir", follow_redirects=True)

    # 3. CRUD Cenario Financeiro (cria com ticket alterado -> verifica BP fechado -> exclui)
    r_cen = client.post(
        "/planejamento/cenario/novo",
        data={
            "codigo_cenario": "pytest_sim_temp",
            "nome": "Simulacao Pytest 2000",
            "regime_simulacao": "simples_fator_r_global",
            "ticket_medio_reais": "2000,00",
            "novos_clientes_mes": "2",
            "pct_cnae_principal": "0,00",
            "prolabore_m1_3_reais": "0,00",
            "justificativa_contadora": "Simulacao temporaria pytest",
        },
        follow_redirects=True,
    )
    assert r_cen.status_code == 200
    assert b"Simulacao Pytest 2000" in r_cen.data

    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.orcamento_cenario WHERE codigo_cenario = 'pytest_sim_temp'")
            cen_id = int(cur.fetchone()["id"])
            cur.execute("SELECT receita_bruta_centavos, bp_diferenca_centavos FROM erp.orcamento_demonstrativo_anual WHERE cenario_id = %s AND ano_ordem = 1", (cen_id,))
            dem1 = cur.fetchone()
            assert int(dem1["receita_bruta_centavos"]) == 31_200_000  # 13 media * 12 * R$ 2.000 = R$ 312.000
            assert int(dem1["bp_diferenca_centavos"]) == 0

    client.post(f"/planejamento/cenario/{cen_id}/excluir", follow_redirects=True)

    # 4. Exportador limpo para pasta temporaria (sem sujar repo)
    exp = exportar_dossie1(destino_dir=tmp_path)
    assert len(exp["arquivos"]) == 6
    xlsx_path = tmp_path / "02_Plano_Financeiro_ERP.xlsx"
    assert xlsx_path.exists()
    wb = openpyxl.load_workbook(xlsx_path)
    assert "DRE_e_BP_3_Anos" in wb.sheetnames
    assert "Projecao_Mensal_M0_M36" in wb.sheetnames


def test_parsers_e_isolamento_dossie1() -> None:
    from sistema.web.repo import parse_int_br, parse_reais_centavos, salvar_identificador

    assert parse_reais_centavos("1.500") == 150_000
    assert parse_reais_centavos("1.500,50") == 150_050
    assert parse_reais_centavos("1500.50") == 150_050
    assert parse_int_br("20.000") == 20_000

    with pytest.raises(ValueError):
        parse_reais_centavos("abc")

    # Tentativa de inserir identificador em pessoa fora do Dossie 1 (D2/D4) deve falhar
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.pessoa WHERE chave = 'pes:pj:rota_sul_d4' LIMIT 1")
            row = cur.fetchone()
    if row:
        with pytest.raises(PermissionError):
            salvar_identificador(
                None,
                {
                    "pessoa_id": str(row["id"]),
                    "tipo_id": "OUTRO",
                    "valor": "teste",
                    "status_validacao": "pendente_revisao",
                },
            )

    # Placar IABP: 0 itens avaliados precisa dar nota 0.00 (sem inflacao por NULL)
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(nota_estimada_10) AS mx FROM auditoria.vw_placar_conformidade")
            assert float(cur.fetchone()["mx"]) == 0.0
            cur.execute("SELECT COUNT(DISTINCT modulo) AS mods FROM auditoria.vw_pendencias_quarentena")
            assert int(cur.fetchone()["mods"]) >= 10

    # Erro de formulario nao devolve HTTP 500
    app = create_app()
    client = app.test_client()
    resp = client.post(
        "/planejamento/cenario/novo",
        data={"codigo_cenario": "bad", "nome": "Bad", "regime_simulacao": "simples_segregado", "ticket_medio_reais": "invalido"},
    )
    assert resp.status_code == 302
