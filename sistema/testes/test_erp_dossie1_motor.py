"""Testes do Motor Contabil-Tributario, Coerencia Societaria e Quarentena Anti-Enviesamento (Etapa 1 / Dossie 1)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from sistema.erp.importar_rascunhos_nath import importar_dossie1_quarentena
from sistema.erp.motor_contabil import (
    aliquota_efetiva_simples,
    calcular_tir,
    calcular_vpl,
    recalcular_todos_cenarios_d1,
    simular_cenario,
    validar_coerencia_dossie1,
)
from sistema.pg.db import ENV_PATH, conectar_pg, obter_database_url


def _pg_disponivel() -> bool:
    try:
        obter_database_url()
        c = conectar_pg()
        c.close()
        return True
    except Exception:
        return False


def test_aliquotas_progressivas_simples_nacional() -> None:
    assert aliquota_efetiva_simples(18_000_000, "Anexo_III") == Decimal("0.060")
    aliq_198 = aliquota_efetiva_simples(19_800_000, "Anexo_III")
    assert round(float(aliq_198), 6) == pytest.approx(0.064727, rel=1e-4)
    aliq_216_iii = aliquota_efetiva_simples(21_600_000, "Anexo_III")
    assert round(float(aliq_216_iii), 6) == pytest.approx(0.068667, rel=1e-4)
    aliq_216_v = aliquota_efetiva_simples(21_600_000, "Anexo_V")
    assert round(float(aliq_216_v), 6) == pytest.approx(0.159167, rel=1e-4)


def test_fechamento_patrimonial_zero_centavos_e_cenarios() -> None:
    cen_base = {
        "regime_simulacao": "simples_segregado",
        "horizonte_meses": 36,
        "capital_social_centavos": 4_000_000,
        "capex_m0_centavos": 1_000_000,
        "capex_ano2_centavos": 1_200_000,
        "capex_ano3_centavos": 1_500_000,
        "taxa_depreciacao_anual_micro": 200_000,
        "ticket_medio_centavos": 150_000,
        "novos_clientes_mes": 2,
        "inadimplencia_micro": 50_000,
        "custo_variavel_micro": 30_000,
        "cac_centavos": 50_000,
        "retencao_meses": 24,
        "tma_anual_micro": 150_000,
        "taxa_reserva_lucros_micro": 200_000,
        "pct_cnae_principal_micro": 850_000,
        "opex_fixo_ano1_mensal_centavos": 300_000,
        "opex_fixo_ano2_mensal_centavos": 650_000,
        "opex_fixo_ano3_mensal_centavos": 950_000,
        "prolabore_m1_3_mensal_centavos": 0,
        "prolabore_m4_12_mensal_centavos": 450_000,
        "prolabore_ano2_mensal_centavos": 700_000,
        "prolabore_ano3_mensal_centavos": 1_000_000,
        "folha_clt_ano2_mensal_centavos": 1_000_000,
        "folha_clt_ano3_mensal_centavos": 2_520_000,
        "encargos_clt_micro": 296_400,
    }
    res = simular_cenario(cen_base)
    assert len(res.projecao_mensal) == 37  # M0 + M1..M36
    assert len(res.demonstrativo_anual) == 4  # M0 + A1..A3
    for d in res.demonstrativo_anual:
        assert d["bp_diferenca_centavos"] == 0

    # Ano 1 deve bater exato com R$ 234.000,00 receita, R$ 17.806,05 DAS e R$ 106.973,95 lucro
    a1 = res.demonstrativo_anual[1]
    assert a1["receita_bruta_centavos"] == 23_400_000
    assert a1["das_centavos"] == 1_780_605
    assert a1["lucro_liquido_centavos"] == 10_697_395
    assert res.indicadores["vpl_centavos"] > 0
    assert res.indicadores["tir_pct"] is not None and res.indicadores["tir_pct"] > 100.0
    assert len(res.indicadores["cenarios_estrategicos"]) == 3
    assert len(res.indicadores["matriz_sensibilidade"]["linhas"]) == 5

    # Teste extremo com prejuizo (0 clientes): Balanco deve continuar fechando a 0 centavos
    cen_prejuizo = dict(cen_base, novos_clientes_mes=0, regime_simulacao="simples_fator_r_global")
    res_p = simular_cenario(cen_prejuizo, incluir_derivados=False)
    for d in res_p.demonstrativo_anual:
        assert d["bp_diferenca_centavos"] == 0
    assert res_p.demonstrativo_anual[1]["lucro_liquido_centavos"] < 0
    assert res_p.demonstrativo_anual[1]["distribuicao_lucros_centavos"] == 0

    # Teste de absorcao de prejuizos acumulados antes de distribuir lucros (Lei 6.404 art. 189)
    cen_recup = dict(cen_base, opex_fixo_ano1_mensal_centavos=1_500_000, prolabore_ano2_mensal_centavos=0, folha_clt_ano2_mensal_centavos=0)
    res_rec = simular_cenario(cen_recup, incluir_derivados=False)
    a1_rec, a2_rec = res_rec.demonstrativo_anual[1], res_rec.demonstrativo_anual[2]
    assert a1_rec["lucro_liquido_centavos"] < 0
    assert a2_rec["lucro_liquido_centavos"] > 0
    # Reserva do Ano 2 precisa absorver o prejuizo antes de distribuir
    assert a2_rec["distribuicao_lucros_centavos"] <= max(0, a2_rec["lucro_liquido_centavos"] + a1_rec["lucro_liquido_centavos"])
    for d in res_rec.demonstrativo_anual:
        assert d["bp_diferenca_centavos"] == 0

    # Churn por coortes: com retencao de 24 meses, a coorte do M1 sai no M25 e a carteira estabiliza em 2 x 24
    cli = {x["mes_ordem"]: x["clientes_ativos"] for x in res.projecao_mensal}
    assert cli[24] == 48 and cli[25] == 48 and cli[36] == 48
    assert res.demonstrativo_anual[3]["clientes_fim"] == 48
    res_r12 = simular_cenario(dict(cen_base, retencao_meses=12), incluir_derivados=False)
    assert res_r12.projecao_mensal[13]["clientes_ativos"] == 24


def test_tir_fluxo_nao_convencional() -> None:
    # (-, +, +, -) com VPL positivo a 15%: bisseccao simples em [-95%, 5000%] nao achava raiz
    fluxos = [-4_000_000, 5_178_793, 5_455_162, -2_328_881]
    assert calcular_vpl(fluxos, Decimal("0.15")) > 0
    tir = calcular_tir(fluxos)
    assert tir is not None and tir > 0.15
    assert abs(calcular_vpl(fluxos, Decimal(str(round(tir, 10))))) <= 1


def test_vpl_e_tir_deterministico() -> None:
    fluxos = [-10_000, 6_000, 6_000]
    tir = calcular_tir(fluxos)
    assert tir is not None
    assert tir == pytest.approx(0.130662, abs=1e-4)
    vpl_zero = calcular_vpl(fluxos, Decimal(str(round(tir, 8))))
    assert abs(vpl_zero) <= 1


@pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")
def test_pg_quarentena_motor_e_detector_coerencia() -> None:
    importar_dossie1_quarentena()
    out = recalcular_todos_cenarios_d1()
    assert len(out["cenarios"]) >= 4

    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07'")
            emp_id = int(cur.fetchone()["id"])

            # 1. Injeta conflito temporario FCD no MoU -> validador precisa detectar CONFLITO_HAVERES_MOU_CONTRATO
            cur.execute(
                """
                UPDATE erp.instrumento_societario_clausula
                SET metodo_haveres = 'fcd'
                WHERE chave = 'inst:mou:08'
                """
            )
            alertas_conflito = validar_coerencia_dossie1(conn, emp_id)
            cods = {a["codigo_regra"] for a in alertas_conflito}
            assert "CONFLITO_HAVERES_MOU_CONTRATO" in cods
            conn.rollback()

            # 2. Protecao de homologacao humana ao re-rodar o importador
            cur.execute(
                """
                UPDATE erp.consulta_normativa
                SET origem_registro = 'usuario',
                    status_validacao = 'homologado_contadora',
                    justificativa_contadora = 'Homologado pela contadora em teste.'
                WHERE chave = 'cons:q01'
                RETURNING id
                """
            )
            q1_id = int(cur.fetchone()["id"])
            conn.commit()

        importar_dossie1_quarentena()

        with conn.cursor() as cur:
            cur.execute("SELECT origem_registro, status_validacao, justificativa_contadora FROM erp.consulta_normativa WHERE id = %s", (q1_id,))
            r = cur.fetchone()
            assert r["origem_registro"] == "usuario"
            assert r["status_validacao"] == "homologado_contadora"
            assert r["justificativa_contadora"] == "Homologado pela contadora em teste."
            # Restaura para estado de quarentena original do caso
            cur.execute(
                """
                UPDATE erp.consulta_normativa
                SET origem_registro = 'importado_rascunho_v2',
                    status_validacao = 'pendente_revisao',
                    justificativa_contadora = NULL
                WHERE id = %s
                """,
                (q1_id,),
            )
            conn.commit()
