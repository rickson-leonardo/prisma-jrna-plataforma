"""Testes automatizados end-to-end do Dossie 2 (Rota Sul Importadora — Set/2026)."""

from __future__ import annotations

import io

import openpyxl

from sistema.erp.motor_folha import recalcular_folha_d2
from sistema.pg.db import conectar_pg
from sistema.web.app import create_app
from sistema.web.emissor_dossie2 import DOCUMENTOS


def test_motor_folha_d2_reconciliacao_e_partidas_dobradas():
    with conectar_pg() as conn:
        res = recalcular_folha_d2(conn)
        conn.commit()
    tot = res["totais"]
    assert tot["bruto"] == 283_333
    assert tot["inss"] == 21_268
    assert tot["irrf"] == 0
    assert tot["fgts"] == 22_667
    assert tot["vt_desc"] == 11_000
    assert tot["vt_subs"] == 23_400
    assert tot["vt_subs_2d"] == 6_200
    assert tot["vr"] == 33_000
    assert tot["neg_a"] == 9_435
    assert tot["liq_a"] == 241_630
    assert tot["liq_b"] == 251_065
    assert tot["prov_total"] == 50_400
    assert res["custo_total_centavos"] == 412_800
    assert tot["custo_adm"] == 224_720
    assert tot["custo_com"] == 188_080
    assert res["exclusao_simples_extra_centavos"] == 91_740
    assert res["partidas_debito_centavos"] == 423_800
    assert res["partidas_credito_centavos"] == 423_800
    assert res["diferenca_partidas"] == 0


def test_seletor_contexto_d1_d2_e_isolamento_d4():
    app = create_app()
    c = app.test_client()

    # Padrao inicia em D1 (PRISMA JRNA)
    r1 = c.get("/")
    assert r1.status_code == 200
    assert "PRISMA JRNA" in r1.get_data(as_text=True)

    # Alterna para D2 via query ou POST
    r2 = c.get("/?dossie=D2")
    assert r2.status_code == 200
    html_d2 = r2.get_data(as_text=True)
    assert "Rota Sul" in html_d2
    assert "2.833,33" in html_d2
    assert "Joinville" not in html_d2

    # Todas as rotas em D2 abrem sem erros e sem chaves de ajuda faltantes
    for url in ("/cadastro", "/instrumentos", "/legalizacao", "/onboarding", "/dp", "/folha", "/sustentacao", "/emissao"):
        resp = c.get(url)
        html = resp.get_data(as_text=True)
        assert resp.status_code == 200, url
        assert "data-help-missing" not in html, url
        assert 'data-modo="consulta"' in html, url

    # Alterna de volta para D1 via POST
    r_back = c.post("/contexto/selecionar", data={"dossie": "D1", "next": "/"}, follow_redirects=True)
    assert r_back.status_code == 200
    assert "PRISMA JRNA" in r_back.get_data(as_text=True)


def test_esocial_recusa_transmitido_sem_recibo_e_homologar_exige_justificativa():
    app = create_app()
    c = app.test_client()
    c.get("/dp")
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM erp.esocial_evento WHERE codigo_evento = 'S-2220' LIMIT 1")
        ev_id = int(cur.fetchone()["id"])

    r1 = c.post(
        f"/dp/esocial/{ev_id}/salvar",
        data={
            "prazo_legal": "Até 15/10/2026",
            "status_envio": "transmitido",
            "numero_recibo": "",
            "observacao": "teste",
            "status_validacao": "pendente_revisao",
            "acao": "rascunho",
        },
        follow_redirects=True,
    )
    assert "recibo" in r1.get_data(as_text=True).lower()

    r2 = c.post(
        f"/dp/esocial/{ev_id}/salvar",
        data={
            "prazo_legal": "Até 15/10/2026",
            "status_envio": "pendente",
            "numero_recibo": "",
            "observacao": "bloqueado ASO",
            "status_validacao": "pendente_revisao",
            "justificativa_contadora": "",
            "acao": "homologar",
        },
        follow_redirects=True,
    )
    assert "justificativa" in r2.get_data(as_text=True).lower()


def test_planilha_aberta_d2_formulas_e_16_previas():
    app = create_app()
    c = app.test_client()
    c.get("/?dossie=D2")

    rx = c.get("/emissao/planilha.xlsx")
    assert rx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(rx.data), data_only=False)
    assert set(wb.sheetnames) == {"Leia-me", "Parametros", "Folha_Set2026", "Memoria_Calculo", "Provisoes_e_Integracao"}
    formulas = [
        v for s in wb.worksheets for row in s.iter_rows(values_only=True) for v in row
        if isinstance(v, str) and v.startswith("=")
    ]
    assert len(formulas) >= 100

    for doc in DOCUMENTOS:
        rp = c.get(f"/emissao/previa/{doc}")
        assert rp.status_code == 200, doc
        assert "Rota Sul" in rp.get_data(as_text=True) or "PRISMA JRNA" in rp.get_data(as_text=True)
