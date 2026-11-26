"""Motor Contabil-Tributario e Validador de Coerencia (Etapa 1 — Dossie 1).

Implementa:
- Apuracao mensal (M0..M36) do Simples Nacional (LC 123/2006 Anexos III e V + Res. CGSN 140/2018);
- Fator R dinamico (proporcionalizado nos 12 primeiros meses e janela movel 12m em M13..M36);
- Demonstracoes integradas: Fluxo de Caixa Mensal, DRE (3 anos), Balanco Patrimonial (Check = R$ 0,00);
- Indicadores de Viabilidade: Ponto de Equilibrio duplo, Unit Economics (LTV s/ margem, CAC, Payback CAC),
  VPL, TIR, Payback Simples/Descontado, 3 Cenarios e Matriz de Sensibilidade 5x5;
- Validador cruzado de coerencia (QSA x Capital x CRC-DF x CNAEs x Contrato Social x MoU x Plano).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from psycopg2.extras import execute_values

from sistema.pg.db import conectar_pg

# Tabelas oficiais Simples Nacional (LC 123/2006) — (limite_superior_centavos, aliquota_nominal, parcela_deduzir_centavos)
FAIXAS_ANEXO_III: tuple[tuple[int, Decimal, int], ...] = (
    (18_000_000, Decimal("0.060"), 0),
    (36_000_000, Decimal("0.112"), 936_000),
    (72_000_000, Decimal("0.135"), 1_764_000),
    (180_000_000, Decimal("0.160"), 3_564_000),
    (360_000_000, Decimal("0.210"), 12_564_000),
    (480_000_000, Decimal("0.330"), 64_800_000),
)

FAIXAS_ANEXO_V: tuple[tuple[int, Decimal, int], ...] = (
    (18_000_000, Decimal("0.155"), 0),
    (36_000_000, Decimal("0.180"), 450_000),
    (72_000_000, Decimal("0.195"), 990_000),
    (180_000_000, Decimal("0.205"), 1_710_000),
    (360_000_000, Decimal("0.230"), 6_210_000),
    (480_000_000, Decimal("0.305"), 54_000_000),
)

LIMITE_ME_CENTAVOS = 36_000_000
LIMITE_EPP_CENTAVOS = 480_000_000
MESES_ABREV = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _brl(centavos: int) -> str:
    return f"{centavos / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def porte_por_receita(rb_ano_centavos: int, meses_atividade: int = 12) -> str:
    """Porte do ano-calendario SEGUINTE dada a receita do ano (LC 123/2006, art. 3o, par. 2o e 9o).

    No ano de inicio os limites sao proporcionais aos meses de atividade (fracao de mes = mes inteiro).
    # ponytail: nao modela o excesso > 20% no ano de inicio (par. 12, efeito retroativo a abertura);
    # se precisar, aplicar o porte retroativo quando rb > 1,2 x limite proporcional.
    """
    if rb_ano_centavos <= LIMITE_ME_CENTAVOS * meses_atividade // 12:
        return "ME"
    if rb_ano_centavos <= LIMITE_EPP_CENTAVOS * meses_atividade // 12:
        return "EPP"
    return "Demais"


def _r_centavos(val: Decimal) -> int:
    return int(val.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _r_micro(val: Decimal) -> int:
    return int((val * Decimal("1000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def aliquota_efetiva_simples(rbt12_centavos: int, anexo: str) -> Decimal:
    """Calcula a aliquota efetiva progressiva da LC 123/2006 para RBT12 em centavos."""
    tabela = FAIXAS_ANEXO_III if anexo == "Anexo_III" else FAIXAS_ANEXO_V
    rbt = max(0, int(rbt12_centavos))
    if rbt <= tabela[0][0]:
        return tabela[0][1]
    limite, aliq_nom, pd_cent = tabela[-1]
    for lim, al, pd in tabela:
        if rbt <= lim:
            limite, aliq_nom, pd_cent = lim, al, pd
            break
    numerador = Decimal(rbt) * aliq_nom - Decimal(pd_cent)
    if numerador <= 0:
        return Decimal("0")
    return numerador / Decimal(rbt)


def calcular_vpl(fluxos_centavos: list[int], tma_anual: Decimal) -> int:
    """Calcula VPL em centavos sobre fluxos anuais [FC0, FC1, FC2, ...]."""
    total = Decimal("0")
    um = Decimal("1")
    for t, fc in enumerate(fluxos_centavos):
        fator = (um + tma_anual) ** t
        total += Decimal(fc) / fator
    return _r_centavos(total)


def calcular_tir(fluxos_centavos: list[int]) -> float | None:
    """Calcula a TIR por varredura de grade + bisseccao, sem dependencias externas.

    Fluxos nao convencionais (mais de uma troca de sinal, ex.: -, +, +, -) podem ter duas raizes:
    a varredura localiza todas e devolve a menor raiz >= 0 (a relevante para comparar com a TMA);
    sem raiz nao negativa, devolve a maior raiz negativa. Sem raiz alguma, devolve None.
    """
    tem_pos = any(x > 0 for x in fluxos_centavos)
    tem_neg = any(x < 0 for x in fluxos_centavos)
    if not (tem_pos and tem_neg):
        return None

    def npv(rate: float) -> float:
        return sum(fc / ((1.0 + rate) ** t) for t, fc in enumerate(fluxos_centavos))

    def bisseccao(lo: float, hi: float, f_lo: float) -> float:
        for _ in range(200):
            mid = (lo + hi) / 2.0
            f_mid = npv(mid)
            if f_mid == 0 or (hi - lo) < 1e-12:
                return mid
            if f_lo * f_mid < 0:
                hi = mid
            else:
                lo, f_lo = mid, f_mid
        return (lo + hi) / 2.0

    # Grade: passo fino perto de zero, mais largo em taxas altas (-95% .. 5000%)
    grade = [-0.95 + i * 0.01 for i in range(295)]            # -0.95 .. 1.99
    grade += [2.0 + i * 0.1 for i in range(481)]              # 2.0 .. 50.0
    raizes: list[float] = []
    r_ant, f_ant = grade[0], npv(grade[0])
    for r in grade[1:]:
        f_r = npv(r)
        if f_ant == 0:
            raizes.append(r_ant)
        elif f_ant * f_r < 0:
            raizes.append(bisseccao(r_ant, r, f_ant))
        r_ant, f_ant = r, f_r
    if not raizes:
        return None
    nao_neg = [x for x in raizes if x >= 0]
    return min(nao_neg) if nao_neg else max(raizes)


def calcular_payback(fluxos_centavos: list[int], tma_anual: Decimal | None = None) -> float | None:
    """Calcula Payback em anos (simples se tma_anual=None, descontado caso contrario)."""
    if not fluxos_centavos or fluxos_centavos[0] >= 0:
        return 0.0
    acum = Decimal(fluxos_centavos[0])
    um = Decimal("1")
    for t in range(1, len(fluxos_centavos)):
        fator = (um + tma_anual) ** t if tma_anual is not None else um
        fc_t = Decimal(fluxos_centavos[t]) / fator
        if acum + fc_t >= 0:
            fracao = float((-acum) / fc_t) if fc_t > 0 else 0.0
            return (t - 1) + fracao
        acum += fc_t
    return None


@dataclass
class ResultadoSimulacao:
    projecao_mensal: list[dict[str, Any]]
    demonstrativo_anual: list[dict[str, Any]]
    indicadores: dict[str, Any]


def simular_cenario(
    cenario: Mapping[str, Any],
    clientes_fator: float = 1.0,
    inadimplencia_override_micro: int | None = None,
    ticket_override_centavos: int | None = None,
    incluir_derivados: bool = True,
    inicio: date | None = None,
) -> ResultadoSimulacao:
    """Executa simulacao contabil e tributaria completa (M0..M36 + Anos 0..3).

    `inicio` = data de inicio das atividades (M1). Sem ela, o ano do plano e tratado como ano-calendario.
    """
    horizonte = int(cenario.get("horizonte_meses") or 36)
    anos_total = max(1, horizonte // 12)
    regime = str(cenario["regime_simulacao"])

    cap_social = int(cenario["capital_social_centavos"])
    capex_m0 = int(cenario["capex_m0_centavos"])
    capex_y2 = int(cenario["capex_ano2_centavos"])
    capex_y3 = int(cenario["capex_ano3_centavos"])
    taxa_dep = Decimal(int(cenario["taxa_depreciacao_anual_micro"])) / Decimal("1000000")

    ticket = int(ticket_override_centavos if ticket_override_centavos is not None else cenario["ticket_medio_centavos"])
    novos_base = int(cenario["novos_clientes_mes"])
    inad_taxa = Decimal(
        int(inadimplencia_override_micro if inadimplencia_override_micro is not None else cenario["inadimplencia_micro"])
    ) / Decimal("1000000")
    cvar_taxa = Decimal(int(cenario["custo_variavel_micro"])) / Decimal("1000000")
    cac_unit = int(cenario["cac_centavos"])
    retencao_meses = int(cenario["retencao_meses"])
    tma_anual = Decimal(int(cenario["tma_anual_micro"])) / Decimal("1000000")
    taxa_res = Decimal(int(cenario["taxa_reserva_lucros_micro"])) / Decimal("1000000")
    pct_pri = Decimal(int(cenario["pct_cnae_principal_micro"])) / Decimal("1000000")
    pct_sec = Decimal("1") - pct_pri

    opex_y = {
        1: int(cenario["opex_fixo_ano1_mensal_centavos"]),
        2: int(cenario["opex_fixo_ano2_mensal_centavos"]),
        3: int(cenario["opex_fixo_ano3_mensal_centavos"]),
    }
    pro_m1_3 = int(cenario["prolabore_m1_3_mensal_centavos"])
    pro_m4_12 = int(cenario["prolabore_m4_12_mensal_centavos"])
    pro_y2 = int(cenario["prolabore_ano2_mensal_centavos"])
    pro_y3 = int(cenario["prolabore_ano3_mensal_centavos"])

    encargos_clt = Decimal(int(cenario["encargos_clt_micro"])) / Decimal("1000000")
    folha_bruta_m = {
        1: 0,
        2: int(cenario["folha_clt_ano2_mensal_centavos"]),
        3: int(cenario["folha_clt_ano3_mensal_centavos"]),
    }
    folha_clt_m = {
        y: _r_centavos(Decimal(folha_bruta_m[y]) * (Decimal("1") + encargos_clt))
        for y in (1, 2, 3)
    }

    # Provisoes de fechamento contabil por exercicio (garante Ativo == Passivo + PL a zero centavos)
    capex_por_ano = {1: 0, 2: capex_y2, 3: capex_y3}
    imob_bruto_y = capex_m0
    obrig_trab_saldo = {0: 0}
    clt_anual_prev = {y: folha_clt_m[y] * 12 for y in (1, 2, 3)}
    for y in range(1, anos_total + 1):
        obrig_trab_saldo[y] = clt_anual_prev.get(y, clt_anual_prev[3]) // 12

    proj_mensal: list[dict[str, Any]] = []
    # M0 (Abertura)
    caixa_saldo = cap_social - capex_m0
    proj_mensal.append({
        "mes_ordem": 0,
        "ano_num": 0,
        "competencia_ym": "M00",
        "novos_clientes": 0,
        "clientes_ativos": 0,
        "receita_bruta_centavos": 0,
        "receita_cnae_principal_centavos": 0,
        "receita_cnae_secundario_centavos": 0,
        "prolabore_centavos": 0,
        "folha_clt_encargos_centavos": 0,
        "rbt12_proporcional_centavos": 0,
        "fs12_proporcional_centavos": 0,
        "fator_r_micro": 0,
        "anexo_cnae_principal": "Anexo_III",
        "anexo_cnae_secundario": "Anexo_V",
        "aliquota_anexo_iii_micro": 0,
        "aliquota_anexo_v_micro": 0,
        "aliquota_efetiva_micro": 0,
        "das_apurado_centavos": 0,
        "das_pago_caixa_centavos": 0,
        "inadimplencia_centavos": 0,
        "recebimentos_centavos": 0,
        "custos_variaveis_centavos": 0,
        "cac_despesa_centavos": 0,
        "opex_fixo_centavos": 0,
        "depreciacao_centavos": 0,
        "ebitda_centavos": 0,
        "lucro_liquido_centavos": 0,
        "fco_centavos": 0,
        "capex_saida_centavos": capex_m0,
        "distribuicao_lucros_centavos": 0,
        "fluxo_liquido_caixa_centavos": caixa_saldo,
        "saldo_caixa_centavos": caixa_saldo,
        "alerta_porte": None,
    })

    # Acumuladores anuais e historicos para RBT12 / FS12
    rec_hist: list[int] = []
    fs_hist: list[int] = []
    das_anterior = 0
    dep_acum = 0
    reservas_acum = 0
    imob_bruto_corrente = capex_m0
    passivo_anterior_total = 0

    demonstrativos: list[dict[str, Any]] = [{
        "ano_ordem": 0,
        "rotulo_periodo": "Abertura (M0)",
        "porte_estimado": "ME",
        "clientes_fim": 0,
        "clientes_media_micro": 0,
        "receita_bruta_centavos": 0,
        "das_centavos": 0,
        "inadimplencia_centavos": 0,
        "receita_liquida_centavos": 0,
        "custos_variaveis_centavos": 0,
        "margem_contribuicao_centavos": 0,
        "cac_centavos": 0,
        "prolabore_centavos": 0,
        "folha_clt_centavos": 0,
        "opex_fixo_centavos": 0,
        "ebitda_centavos": 0,
        "depreciacao_centavos": 0,
        "lucro_liquido_centavos": 0,
        "distribuicao_lucros_centavos": 0,
        "reserva_lucros_centavos": 0,
        "fator_r_anual_micro": 0,
        "aliquota_efetiva_anual_micro": 0,
        "bp_caixa_centavos": caixa_saldo,
        "bp_imobilizado_bruto_centavos": capex_m0,
        "bp_depreciacao_acumulada_centavos": 0,
        "bp_ativo_total_centavos": cap_social,
        "bp_das_a_recolher_centavos": 0,
        "bp_obrigacoes_trabalhistas_centavos": 0,
        "bp_passivo_total_centavos": 0,
        "bp_capital_social_centavos": cap_social,
        "bp_reservas_lucros_centavos": 0,
        "bp_pl_total_centavos": cap_social,
        "bp_diferenca_centavos": 0,
        "fluxo_livre_projeto_centavos": -cap_social,
        "indicadores_json": {},
    }]

    fator_dec = Decimal(str(clientes_fator))
    clientes_acum_nominal = 0
    ano_atual = 1
    # Porte por ano-calendario: receita e meses de atividade de cada ano civil
    ano0, mes0 = (inicio.year, inicio.month) if inicio else (1, 1)
    rec_cal: dict[int, int] = {}
    meses_cal: dict[int, int] = {}
    porte_atual = "ME"

    # Variaveis por ano
    meses_por_ano: dict[int, list[dict[str, Any]]] = {y: [] for y in range(1, anos_total + 1)}

    for m in range(1, horizonte + 1):
        y = ((m - 1) // 12) + 1
        mes_do_ano = ((m - 1) % 12) + 1
        if mes_do_ano == 1 and y > 1:
            imob_bruto_corrente += capex_por_ano.get(y, 0)

        idx_cal = mes0 - 1 + (m - 1)
        ano_cal, mes_cal = ano0 + idx_cal // 12, idx_cal % 12 + 1
        rot_mes = f"{MESES_ABREV[mes_cal - 1]}/{ano_cal}" if inicio else f"A{y}-M{mes_do_ano:02d}"
        alerta_porte = None
        if ano_cal not in rec_cal:
            if rec_cal:  # virada de ano-calendario: porte do novo ano depende da receita do anterior
                porte_novo = porte_por_receita(rec_cal[ano_cal - 1], meses_cal[ano_cal - 1])
                if porte_novo != porte_atual:
                    rot_ano_ant = str(ano_cal - 1) if inicio else f"do Ano {ano_cal - 1}"
                    alerta_porte = (
                        f"{porte_novo} desde {rot_mes}: receita {'de ' if inicio else ''}{rot_ano_ant} = "
                        f"R$ {_brl(rec_cal[ano_cal - 1])} (LC 123/2006, art. 3º, § 9º)"
                    )
                    porte_atual = porte_novo
            rec_cal[ano_cal] = 0
            meses_cal[ano_cal] = 0

        # Carteira por coortes: cada cliente permanece `retencao_meses` meses (coerente com LTV = MC x retencao).
        # Coortes ativas no mes m: as adquiridas em [m - retencao + 1, m].
        clientes_acum_nominal = novos_base * min(m, retencao_meses)
        clientes_eff_float = clientes_acum_nominal * clientes_fator
        clientes_int = int(round(clientes_eff_float))
        novos_eff_float = novos_base * clientes_fator
        novos_int = int(round(novos_eff_float))

        rec_bruta = _r_centavos(Decimal(clientes_acum_nominal * ticket) * fator_dec)
        rec_cal[ano_cal] += rec_bruta
        meses_cal[ano_cal] += 1
        rec_pri = _r_centavos(Decimal(rec_bruta) * pct_pri) if regime == "simples_segregado" else 0
        rec_sec = rec_bruta - rec_pri

        # Folha CLT mensal contabil + pro-labore
        folha_m = folha_clt_m.get(y, folha_clt_m[3])
        if y == 1:
            pro_m = pro_m1_3 if m <= 3 else pro_m4_12
        elif y == 2:
            pro_m = pro_y2
        else:
            pro_m = pro_y3

        if regime == "simples_auto_prolabore_28" and rec_bruta > 0:
            # Garante razao folha mensal >= 28.2% caso base fique abaixo (planejamento tributario)
            alvo_fs = _r_centavos(Decimal(rec_bruta) * Decimal("0.282"))
            if (pro_m + folha_m) < alvo_fs:
                pro_m = alvo_fs - folha_m

        fs_m = pro_m + folha_m

        # RBT12 e FS12 simetricos conforme Res. CGSN 140/2018 art. 21 e art. 26 (meses anteriores ao PA em m >= 2)
        if m == 1:
            rbt12 = rec_bruta * 12
            fs12 = fs_m * 12
        elif m <= 12:
            rbt12 = _r_centavos((Decimal(sum(rec_hist)) / Decimal(m - 1)) * Decimal("12"))
            fs12 = _r_centavos((Decimal(sum(fs_hist)) / Decimal(m - 1)) * Decimal("12"))
        else:
            rbt12 = sum(rec_hist[-12:])
            fs12 = sum(fs_hist[-12:])

        fator_r = (Decimal(fs12) / Decimal(rbt12)) if rbt12 > 0 else Decimal("0")

        if regime == "v1_fixo_6_erro":
            aliq_iii = Decimal("0.060")
            aliq_v = Decimal("0.060")
            anexo_pri = "Anexo_III"
            anexo_sec = "Anexo_III"
            das_m = _r_centavos(Decimal(rec_bruta) * Decimal("0.060"))
        else:
            aliq_iii = aliquota_efetiva_simples(rbt12, "Anexo_III")
            aliq_v = aliquota_efetiva_simples(rbt12, "Anexo_V")
            anexo_pri = "Anexo_III"
            if regime == "simples_segregado":
                anexo_sec = "Anexo_III" if fator_r >= Decimal("0.28") else "Anexo_V"
                aliq_sec = aliq_iii if anexo_sec == "Anexo_III" else aliq_v
                das_m = _r_centavos(Decimal(rec_pri) * aliq_iii + Decimal(rec_sec) * aliq_sec)
            else:
                # 100% sujeito ao Fator R
                anexo_sec = "Anexo_III" if fator_r >= Decimal("0.28") else "Anexo_V"
                anexo_pri = anexo_sec
                aliq_u = aliq_iii if anexo_sec == "Anexo_III" else aliq_v
                das_m = _r_centavos(Decimal(rec_bruta) * aliq_u)

        aliq_ef_m = (Decimal(das_m) / Decimal(rec_bruta)) if rec_bruta > 0 else Decimal("0")

        inad_m = _r_centavos(Decimal(rec_bruta) * inad_taxa)
        receb_m = rec_bruta - inad_m
        cvar_m = _r_centavos(Decimal(rec_bruta) * cvar_taxa)
        cac_m = _r_centavos(Decimal(novos_base * cac_unit) * fator_dec)
        opex_m = opex_y.get(y, opex_y[3])

        # Depreciacao exata no ano (20% a.a. sobre imobilizado bruto corrente, ajustando centavo residual no mes 12)
        dep_ano_alvo = _r_centavos(Decimal(imob_bruto_corrente) * taxa_dep)
        if mes_do_ano < 12:
            dep_m = dep_ano_alvo // 12
        else:
            dep_ja = sum(item["depreciacao_centavos"] for item in meses_por_ano[y])
            dep_m = dep_ano_alvo - dep_ja

        ebitda_m = receb_m - das_m - cvar_m - cac_m - pro_m - folha_m - opex_m
        lucro_m = ebitda_m - dep_m

        # Pagamento em caixa do DAS ocorre no mes seguinte (dia 20), e 1/12 de CLT permanece em obrigacoes trabalhistas no fechamento do mes 12
        das_pago_m = das_anterior
        capex_saida_m = capex_por_ano.get(y, 0) if mes_do_ano == 1 else 0
        delta_obrig_m12 = (obrig_trab_saldo[y] - obrig_trab_saldo[y - 1]) if mes_do_ano == 12 else 0
        fco_m = receb_m - das_pago_m - cvar_m - cac_m - pro_m - (folha_m - delta_obrig_m12) - opex_m

        row_m = {
            "mes_ordem": m,
            "ano_num": y,
            "competencia_ym": f"A{y}-M{mes_do_ano:02d}" + (f" · {rot_mes}" if inicio else ""),
            "novos_clientes": novos_int,
            "clientes_ativos": clientes_int,
            "receita_bruta_centavos": rec_bruta,
            "receita_cnae_principal_centavos": rec_pri,
            "receita_cnae_secundario_centavos": rec_sec,
            "prolabore_centavos": pro_m,
            "folha_clt_encargos_centavos": folha_m,
            "rbt12_proporcional_centavos": rbt12,
            "fs12_proporcional_centavos": fs12,
            "fator_r_micro": _r_micro(fator_r),
            "anexo_cnae_principal": anexo_pri,
            "anexo_cnae_secundario": anexo_sec,
            "aliquota_anexo_iii_micro": _r_micro(aliq_iii),
            "aliquota_anexo_v_micro": _r_micro(aliq_v),
            "aliquota_efetiva_micro": _r_micro(aliq_ef_m),
            "das_apurado_centavos": das_m,
            "das_pago_caixa_centavos": das_pago_m,
            "inadimplencia_centavos": inad_m,
            "recebimentos_centavos": receb_m,
            "custos_variaveis_centavos": cvar_m,
            "cac_despesa_centavos": cac_m,
            "opex_fixo_centavos": opex_m,
            "depreciacao_centavos": dep_m,
            "ebitda_centavos": ebitda_m,
            "lucro_liquido_centavos": lucro_m,
            "fco_centavos": fco_m,
            "capex_saida_centavos": capex_saida_m,
            "distribuicao_lucros_centavos": 0,
            "fluxo_liquido_caixa_centavos": fco_m - capex_saida_m,
            "saldo_caixa_centavos": 0,
            "alerta_porte": alerta_porte,
            "porte_vigente": porte_atual,  # so em memoria (rotulo anual); nao persistido
        }

        rec_hist.append(rec_bruta)
        fs_hist.append(fs_m)
        das_anterior = das_m
        meses_por_ano[y].append(row_m)

        # Fechamento anual no mes 12 de cada ano
        if mes_do_ano == 12:
            ms = meses_por_ano[y]
            rb_y = sum(x["receita_bruta_centavos"] for x in ms)
            das_y = sum(x["das_apurado_centavos"] for x in ms)
            inad_y = sum(x["inadimplencia_centavos"] for x in ms)
            rl_y = rb_y - das_y - inad_y
            cv_y = sum(x["custos_variaveis_centavos"] for x in ms)
            mc_y = rl_y - cv_y
            cac_y = sum(x["cac_despesa_centavos"] for x in ms)
            pro_y = sum(x["prolabore_centavos"] for x in ms)
            folha_y = sum(x["folha_clt_encargos_centavos"] for x in ms)
            opex_tot_y = sum(x["opex_fixo_centavos"] for x in ms)
            ebitda_y = sum(x["ebitda_centavos"] for x in ms)
            dep_y = sum(x["depreciacao_centavos"] for x in ms)
            lucro_y = sum(x["lucro_liquido_centavos"] for x in ms)

            # Caixa disponivel no fechamento do ano antes da distribuicao de dividendos
            caixa_antes_dist = caixa_saldo + sum(item["fluxo_liquido_caixa_centavos"] for item in ms)

            # Absorve eventuais prejuizos acumulados (Lei 6.404/76 art. 189) e limita dividendos a solvencia (Contrato Cl. 15 § 2o)
            if lucro_y <= 0:
                res_y = lucro_y
                dist_y = 0
            elif reservas_acum < 0:
                compensado = min(lucro_y, -reservas_acum)
                lucro_distribuivel = lucro_y - compensado
                dist_ideal = lucro_distribuivel - _r_centavos(Decimal(lucro_distribuivel) * taxa_res)
                dist_y = min(dist_ideal, max(0, caixa_antes_dist))
                res_y = lucro_y - dist_y
            else:
                dist_ideal = lucro_y - _r_centavos(Decimal(lucro_y) * taxa_res)
                dist_y = min(dist_ideal, max(0, caixa_antes_dist))
                res_y = lucro_y - dist_y

            row_m["distribuicao_lucros_centavos"] = dist_y
            row_m["fluxo_liquido_caixa_centavos"] -= dist_y

            for item in ms:
                caixa_saldo += item["fluxo_liquido_caixa_centavos"]
                item["saldo_caixa_centavos"] = caixa_saldo
                proj_mensal.append(item)

            dep_acum += dep_y
            reservas_acum += res_y
            das_a_rec = das_m
            obrig_y = obrig_trab_saldo[y]
            passivo_y = das_a_rec + obrig_y
            ativo_imob_liq = imob_bruto_corrente - dep_acum
            ativo_tot = caixa_saldo + ativo_imob_liq
            pl_tot = cap_social + reservas_acum
            diff_bp = ativo_tot - (passivo_y + pl_tot)

            # Fluxo de Caixa Livre do Projeto no Ano y = FCO_y - CAPEX_y
            fc_livre_y = lucro_y + dep_y + (passivo_y - passivo_anterior_total) - capex_por_ano.get(y, 0)
            passivo_anterior_total = passivo_y

            p_ini, p_fim = ms[0]["porte_vigente"], ms[-1]["porte_vigente"]
            porte_y = p_ini if p_ini == p_fim else f"{p_ini}→{p_fim}"
            fator_r_y = (Decimal(pro_y + folha_y) / Decimal(rb_y)) if rb_y > 0 else Decimal("0")
            aliq_y = (Decimal(das_y) / Decimal(rb_y)) if rb_y > 0 else Decimal("0")
            cli_med_micro = _r_micro(Decimal(sum(x["clientes_ativos"] for x in ms)) / Decimal("12"))

            demonstrativos.append({
                "ano_ordem": y,
                "rotulo_periodo": f"Ano {y} ({porte_y})",
                "porte_estimado": porte_y,
                "clientes_fim": clientes_int,
                "clientes_media_micro": cli_med_micro,
                "receita_bruta_centavos": rb_y,
                "das_centavos": das_y,
                "inadimplencia_centavos": inad_y,
                "receita_liquida_centavos": rl_y,
                "custos_variaveis_centavos": cv_y,
                "margem_contribuicao_centavos": mc_y,
                "cac_centavos": cac_y,
                "prolabore_centavos": pro_y,
                "folha_clt_centavos": folha_y,
                "opex_fixo_centavos": opex_tot_y,
                "ebitda_centavos": ebitda_y,
                "depreciacao_centavos": dep_y,
                "lucro_liquido_centavos": lucro_y,
                "distribuicao_lucros_centavos": dist_y,
                "reserva_lucros_centavos": res_y,
                "fator_r_anual_micro": _r_micro(fator_r_y),
                "aliquota_efetiva_anual_micro": _r_micro(aliq_y),
                "bp_caixa_centavos": caixa_saldo,
                "bp_imobilizado_bruto_centavos": imob_bruto_corrente,
                "bp_depreciacao_acumulada_centavos": -dep_acum,
                "bp_ativo_total_centavos": ativo_tot,
                "bp_das_a_recolher_centavos": das_a_rec,
                "bp_obrigacoes_trabalhistas_centavos": obrig_y,
                "bp_passivo_total_centavos": passivo_y,
                "bp_capital_social_centavos": cap_social,
                "bp_reservas_lucros_centavos": reservas_acum,
                "bp_pl_total_centavos": pl_tot,
                "bp_diferenca_centavos": diff_bp,
                "fluxo_livre_projeto_centavos": fc_livre_y,
                "indicadores_json": {},
            })

    # Indicadores consolidados (Viabilidade + Break-even + Unit Economics)
    fluxos_fc = [d["fluxo_livre_projeto_centavos"] for d in demonstrativos]
    vpl_cent = calcular_vpl(fluxos_fc, tma_anual)
    tir_val = calcular_tir(fluxos_fc)
    pb_simp = calcular_payback(fluxos_fc, None)
    pb_desc = calcular_payback(fluxos_fc, tma_anual)

    # Ponto de equilibrio Fase 1 (M1-M3) e Fase 2 (M4-M12)
    m1_3 = [x for x in proj_mensal if 1 <= x["mes_ordem"] <= 3]
    m4_12 = [x for x in proj_mensal if 4 <= x["mes_ordem"] <= 12]
    rb_1_3 = sum(x["receita_bruta_centavos"] for x in m1_3)
    das_1_3 = sum(x["das_apurado_centavos"] for x in m1_3)
    tx_var_1 = ((Decimal(das_1_3) / Decimal(rb_1_3)) if rb_1_3 > 0 else Decimal("0")) + inad_taxa + cvar_taxa
    mc_unit_1 = Decimal(ticket) * (Decimal("1") - tx_var_1)
    cf_1 = Decimal(opex_y[1] + (m1_3[0]["prolabore_centavos"] if m1_3 else 0))
    pe_cli_1 = float(cf_1 / mc_unit_1) if mc_unit_1 > 0 else 0.0

    rb_ano1 = demonstrativos[1]["receita_bruta_centavos"] if len(demonstrativos) > 1 else 0
    das_ano1 = demonstrativos[1]["das_centavos"] if len(demonstrativos) > 1 else 0
    tx_var_a1 = ((Decimal(das_ano1) / Decimal(rb_ano1)) if rb_ano1 > 0 else Decimal("0")) + inad_taxa + cvar_taxa
    mc_unit_a1 = Decimal(ticket) * (Decimal("1") - tx_var_a1)
    cf_2 = Decimal(opex_y[1] + (m4_12[0]["prolabore_centavos"] if m4_12 else 0))
    pe_cli_2 = float(cf_2 / mc_unit_a1) if mc_unit_a1 > 0 else 0.0

    ltv_cent = _r_centavos(mc_unit_a1 * Decimal(retencao_meses))
    ltv_cac = float(Decimal(ltv_cent) / Decimal(cac_unit)) if cac_unit > 0 else 0.0
    payback_cac_meses = float(Decimal(cac_unit) / mc_unit_a1) if mc_unit_a1 > 0 else 0.0

    rb_tot = sum(d["receita_bruta_centavos"] for d in demonstrativos if d["ano_ordem"] >= 1)
    das_tot = sum(d["das_centavos"] for d in demonstrativos if d["ano_ordem"] >= 1)
    lucro_tot = sum(d["lucro_liquido_centavos"] for d in demonstrativos if d["ano_ordem"] >= 1)

    indicadores: dict[str, Any] = {
        "receita_3_anos_centavos": rb_tot,
        "das_3_anos_centavos": das_tot,
        "das_medio_3_anos_pct": round((das_tot / rb_tot * 100.0), 2) if rb_tot > 0 else 0.0,
        "lucro_3_anos_centavos": lucro_tot,
        "vpl_centavos": vpl_cent,
        "tir_pct": round(tir_val * 100.0, 2) if tir_val is not None else None,
        "payback_simples_anos": round(pb_simp, 2) if pb_simp is not None else None,
        "payback_simples_meses": round(pb_simp * 12.0, 2) if pb_simp is not None else None,
        "payback_descontado_anos": round(pb_desc, 2) if pb_desc is not None else None,
        "payback_descontado_meses": round(pb_desc * 12.0, 2) if pb_desc is not None else None,
        "break_even_fase1_clientes": round(pe_cli_1, 2),
        "break_even_fase1_receita_centavos": _r_centavos(Decimal(str(pe_cli_1)) * Decimal(ticket)),
        "break_even_fase2_clientes": round(pe_cli_2, 2),
        "break_even_fase2_receita_centavos": _r_centavos(Decimal(str(pe_cli_2)) * Decimal(ticket)),
        "mc_unitaria_ano1_centavos": _r_centavos(mc_unit_a1),
        "ltv_centavos": ltv_cent,
        "cac_centavos": cac_unit,
        "ltv_cac": round(ltv_cac, 2),
        "payback_cac_meses": round(payback_cac_meses, 2),
        "mes_transicao_epp": next((x["mes_ordem"] for x in proj_mensal if x.get("alerta_porte")), None),
    }

    if incluir_derivados:
        cenarios_estrat = []
        for cod_e, nome_e, f_cli, in_m in (
            ("pessimista", "Pessimista (-30% Clientes / 8% Inad.)", 0.7, 80_000),
            ("base", "Provavel (Base 100% / Premissa Atual)", 1.0, None),
            ("otimista", "Otimista (+20% Clientes / 3% Inad.)", 1.2, 30_000),
        ):
            r_sub = simular_cenario(cenario, clientes_fator=f_cli, inadimplencia_override_micro=in_m, incluir_derivados=False, inicio=inicio)
            cenarios_estrat.append({
                "codigo": cod_e,
                "nome": nome_e,
                "receita_3_anos_centavos": r_sub.indicadores["receita_3_anos_centavos"],
                "das_medio_pct": r_sub.indicadores["das_medio_3_anos_pct"],
                "lucro_3_anos_centavos": r_sub.indicadores["lucro_3_anos_centavos"],
                "vpl_centavos": r_sub.indicadores["vpl_centavos"],
                "tir_pct": r_sub.indicadores["tir_pct"],
            })
        indicadores["cenarios_estrategicos"] = cenarios_estrat

        tickets_sens = [120_000, 135_000, 150_000, 165_000, 180_000]
        if ticket not in tickets_sens:
            tickets_sens = [int(ticket * 0.8), int(ticket * 0.9), ticket, int(ticket * 1.1), int(ticket * 1.2)]
        inads_sens = [20_000, 50_000, 80_000, 100_000, 120_000]
        matriz = []
        for tk in tickets_sens:
            linha = {"ticket_centavos": tk, "valores_vpl_centavos": []}
            for inad_m_s in inads_sens:
                rs_m = simular_cenario(
                    cenario,
                    clientes_fator=1.0,
                    inadimplencia_override_micro=inad_m_s,
                    ticket_override_centavos=tk,
                    incluir_derivados=False,
                    inicio=inicio,
                )
                linha["valores_vpl_centavos"].append(rs_m.indicadores["vpl_centavos"])
            matriz.append(linha)
        indicadores["matriz_sensibilidade"] = {
            "inadimplencias_pct": [x / 10_000.0 for x in inads_sens],
            "linhas": matriz,
        }

    demonstrativos[0]["indicadores_json"] = indicadores
    return ResultadoSimulacao(
        projecao_mensal=proj_mensal,
        demonstrativo_anual=demonstrativos,
        indicadores=indicadores,
    )


def recalcular_cenario_no_banco(conn: Any, cenario_id: int) -> ResultadoSimulacao:
    """Recalcula e persiste projecoes mensais e demonstrativos anuais de um cenario no Postgres."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM erp.orcamento_cenario WHERE id = %s", (cenario_id,))
        cen = cur.fetchone()
        if not cen:
            raise KeyError(f"Cenario id={cenario_id} nao encontrado.")
        # Fonte unica do M1: inicio do enquadramento no Cadastro (Estacao 1)
        cur.execute("SELECT MIN(vigente_de) AS inicio FROM erp.enquadramento_historico WHERE empresa_id = %s", (cen["empresa_id"],))
        row_ini = cur.fetchone()
        res = simular_cenario(cen, inicio=row_ini["inicio"] if row_ini else None)

        cur.execute("DELETE FROM erp.orcamento_projecao_mensal WHERE cenario_id = %s", (cenario_id,))
        cur.execute("DELETE FROM erp.orcamento_demonstrativo_anual WHERE cenario_id = %s", (cenario_id,))

        execute_values(
            cur,
            """
            INSERT INTO erp.orcamento_projecao_mensal (
                chave, cenario_id, mes_ordem, ano_num, competencia_ym, novos_clientes, clientes_ativos,
                receita_bruta_centavos, receita_cnae_principal_centavos, receita_cnae_secundario_centavos,
                prolabore_centavos, folha_clt_encargos_centavos, rbt12_proporcional_centavos,
                fs12_proporcional_centavos, fator_r_micro, anexo_cnae_principal, anexo_cnae_secundario,
                aliquota_anexo_iii_micro, aliquota_anexo_v_micro, aliquota_efetiva_micro,
                das_apurado_centavos, das_pago_caixa_centavos, inadimplencia_centavos, recebimentos_centavos,
                custos_variaveis_centavos, cac_despesa_centavos, opex_fixo_centavos, depreciacao_centavos,
                ebitda_centavos, lucro_liquido_centavos, fco_centavos, capex_saida_centavos,
                distribuicao_lucros_centavos, fluxo_liquido_caixa_centavos, saldo_caixa_centavos, alerta_porte
            ) VALUES %s
            """,
            [
                (
                    f"proj:{cen['codigo_cenario']}:m{p['mes_ordem']:02d}",
                    cenario_id,
                    p["mes_ordem"], p["ano_num"], p["competencia_ym"], p["novos_clientes"], p["clientes_ativos"],
                    p["receita_bruta_centavos"], p["receita_cnae_principal_centavos"], p["receita_cnae_secundario_centavos"],
                    p["prolabore_centavos"], p["folha_clt_encargos_centavos"], p["rbt12_proporcional_centavos"],
                    p["fs12_proporcional_centavos"], p["fator_r_micro"], p["anexo_cnae_principal"], p["anexo_cnae_secundario"],
                    p["aliquota_anexo_iii_micro"], p["aliquota_anexo_v_micro"], p["aliquota_efetiva_micro"],
                    p["das_apurado_centavos"], p["das_pago_caixa_centavos"], p["inadimplencia_centavos"], p["recebimentos_centavos"],
                    p["custos_variaveis_centavos"], p["cac_despesa_centavos"], p["opex_fixo_centavos"], p["depreciacao_centavos"],
                    p["ebitda_centavos"], p["lucro_liquido_centavos"], p["fco_centavos"], p["capex_saida_centavos"],
                    p["distribuicao_lucros_centavos"], p["fluxo_liquido_caixa_centavos"], p["saldo_caixa_centavos"], p["alerta_porte"],
                )
                for p in res.projecao_mensal
            ],
        )

        execute_values(
            cur,
            """
            INSERT INTO erp.orcamento_demonstrativo_anual (
                chave, cenario_id, ano_ordem, rotulo_periodo, porte_estimado, clientes_fim, clientes_media_micro,
                receita_bruta_centavos, das_centavos, inadimplencia_centavos, receita_liquida_centavos,
                custos_variaveis_centavos, margem_contribuicao_centavos, cac_centavos, prolabore_centavos,
                folha_clt_centavos, opex_fixo_centavos, ebitda_centavos, depreciacao_centavos,
                lucro_liquido_centavos, distribuicao_lucros_centavos, reserva_lucros_centavos,
                fator_r_anual_micro, aliquota_efetiva_anual_micro, bp_caixa_centavos,
                bp_imobilizado_bruto_centavos, bp_depreciacao_acumulada_centavos, bp_ativo_total_centavos,
                bp_das_a_recolher_centavos, bp_obrigacoes_trabalhistas_centavos, bp_passivo_total_centavos,
                bp_capital_social_centavos, bp_reservas_lucros_centavos, bp_pl_total_centavos,
                bp_diferenca_centavos, fluxo_livre_projeto_centavos, indicadores_json
            ) VALUES %s
            """,
            [
                (
                    f"dem:{cen['codigo_cenario']}:a{d['ano_ordem']}",
                    cenario_id,
                    d["ano_ordem"], d["rotulo_periodo"], d["porte_estimado"], d["clientes_fim"], d["clientes_media_micro"],
                    d["receita_bruta_centavos"], d["das_centavos"], d["inadimplencia_centavos"], d["receita_liquida_centavos"],
                    d["custos_variaveis_centavos"], d["margem_contribuicao_centavos"], d["cac_centavos"], d["prolabore_centavos"],
                    d["folha_clt_centavos"], d["opex_fixo_centavos"], d["ebitda_centavos"], d["depreciacao_centavos"],
                    d["lucro_liquido_centavos"], d["distribuicao_lucros_centavos"], d["reserva_lucros_centavos"],
                    d["fator_r_anual_micro"], d["aliquota_efetiva_anual_micro"], d["bp_caixa_centavos"],
                    d["bp_imobilizado_bruto_centavos"], d["bp_depreciacao_acumulada_centavos"], d["bp_ativo_total_centavos"],
                    d["bp_das_a_recolher_centavos"], d["bp_obrigacoes_trabalhistas_centavos"], d["bp_passivo_total_centavos"],
                    d["bp_capital_social_centavos"], d["bp_reservas_lucros_centavos"], d["bp_pl_total_centavos"],
                    d["bp_diferenca_centavos"], d["fluxo_livre_projeto_centavos"],
                    json.dumps(d["indicadores_json"], ensure_ascii=False),
                )
                for d in res.demonstrativo_anual
            ],
        )
    return res


def validar_coerencia_dossie1(conn: Any, empresa_id: int) -> list[dict[str, Any]]:
    """Executa auditoria cruzada completa dos dados no ERP e grava em auditoria.alerta_coerencia."""
    alertas: list[dict[str, Any]] = []

    def add_alerta(cod: str, sev: str, cat: str, mod: str, tit: str, desc: str, rec: str, resolvido: bool = False, ancora: str | None = None) -> None:
        alertas.append({
            "ancora": ancora,
            "chave": f"alert:d1:{empresa_id}:{cod}",
            "codigo_regra": cod,
            "severidade": sev,
            "categoria": cat,
            "modulo_alvo": mod,
            "titulo": tit,
            "descricao": desc,
            "recomendacao": rec,
            "resolvido": resolvido,
        })

    with conn.cursor() as cur:
        # 1. QSA e Capital Social
        cur.execute(
            """
            SELECT ps.*, p.nome_canonico
            FROM erp.participacao_societaria ps
            JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id
            WHERE ps.empresa_id = %s AND ps.vigente_ate IS NULL
            """,
            (empresa_id,),
        )
        socias = cur.fetchall()
        soma_pct = sum(int(s["percentual_micro"] or 0) for s in socias)
        soma_cap = sum(int(s["valor_centavos"] or 0) for s in socias)
        eh_paritaria_50_50 = len(socias) == 2 and all(int(s["percentual_micro"] or 0) == 500_000 for s in socias)

        if soma_pct != 1_000_000:
            add_alerta(
                "QSA_PCT_100", "critico", "societario", "cadastro",
                "Soma de participacao societaria diferente de 100%",
                f"As quotas ativas somam {soma_pct / 10_000:.2f}% em vez de 100,00%.",
                "Ajustar percentuais em Estacao 1 (/cadastro) para fechar exatamente 100%.",
                ancora="/cadastro#socios",
            )

        # 2. Enquadramento e Responsavel Tecnico
        cur.execute(
            """
            SELECT enq.*, pi.valor AS crc_rt
            FROM erp.enquadramento_historico enq
            LEFT JOIN erp.pessoa_identificador pi
                ON pi.pessoa_id = enq.responsavel_tecnico_pessoa_id AND pi.tipo_id = 'CRC'
            WHERE enq.empresa_id = %s AND enq.vigente_ate IS NULL
            ORDER BY enq.vigente_de DESC LIMIT 1
            """,
            (empresa_id,),
        )
        enq = cur.fetchone()
        inicio_socias = min((s["vigente_de"] for s in socias if s["vigente_de"]), default=None)
        if enq and inicio_socias and enq["vigente_de"] < inicio_socias:
            add_alerta(
                "ENQUADRAMENTO_ANTES_DO_CONTRATO", "alerta", "societario", "cadastro",
                "Enquadramento vigente antes do contrato social",
                f"Enquadramento desde {enq['vigente_de']:%d/%m/%Y}, mas as participacoes societarias so comecam em {inicio_socias:%d/%m/%Y}.",
                "Alinhar a vigencia do enquadramento a data de registro/abertura do CNPJ (posterior ao contrato) em /cadastro.",
                ancora="/cadastro#enquadramento",
            )
        if not enq or not enq["responsavel_tecnico_pessoa_id"] or not enq["crc_rt"]:
            add_alerta(
                "RT_CRC_OBRIGATORIO", "critico", "regulatorio", "cadastro",
                "Responsavel Tecnico sem CRC ativo vinculado",
                "Organizacao contabil exige contador com CRC ativo (DL 9.295/46 e Res. CFC 1.708/2023).",
                "Vincular pessoa com registro CRC em Enquadramento e Identificadores (/cadastro).",
                ancora="/cadastro#enquadramento",
            )

        # 3. Instrumentos Societarios (Contrato x MoU)
        cur.execute(
            """
            SELECT * FROM erp.instrumento_societario_clausula
            WHERE empresa_id = %s ORDER BY ordem
            """,
            (empresa_id,),
        )
        clausulas = cur.fetchall()

        metodos_cs = {c["metodo_haveres"] for c in clausulas if c["aplica_contrato"] and c["metodo_haveres"] != "nao_aplicavel"}
        metodos_mou = {c["metodo_haveres"] for c in clausulas if c["aplica_mou"] and c["metodo_haveres"] != "nao_aplicavel"}
        for c in clausulas:
            txt_l = f"{c['titulo']} {c['regra_texto']}".lower()
            if c["aplica_contrato"] and ("balanço de determinação" in txt_l or "balanco de determinacao" in txt_l) and "afastada" in txt_l and "fcd" in txt_l:
                metodos_cs.add("balanco_determinacao")
            elif c["aplica_contrato"] and "fluxo de caixa descontado" in txt_l and "afastada" not in txt_l:
                metodos_cs.add("fcd")
            if c["aplica_mou"] and ("fluxo de caixa descontado" in txt_l or " fcd " in txt_l) and "afastada" not in txt_l and "eliminando qualquer menção anterior a fcd" not in txt_l and "eliminando qualquer mencao anterior a fcd" not in txt_l:
                metodos_mou.add("fcd")
            elif c["aplica_mou"] and ("balanço de determinação" in txt_l or "balanco de determinacao" in txt_l):
                metodos_mou.add("balanco_determinacao")

        if metodos_cs != metodos_mou and (metodos_cs or metodos_mou):
            cl_hav = next((c for c in clausulas if c["aplica_mou"] and "haveres" in (c["titulo"] or "").lower()), None) or next(
                (c for c in clausulas if "haveres" in (c["titulo"] or "").lower()), None
            )
            add_alerta(
                "CONFLITO_HAVERES_MOU_CONTRATO", "critico", "societario", "instrumentos",
                "Conflito de Apuracao de Haveres entre Contrato Social e MoU",
                f"Contrato adota {sorted(metodos_cs)} enquanto o MoU adota {sorted(metodos_mou)}.",
                "Unificar ambos os instrumentos (ex.: Balanco de Determinacao sem FCD) em Estacao 2 (/instrumentos).",
                ancora=f"/instrumentos#clausula-{cl_hav['id']}" if cl_hav else "/instrumentos",
            )

        # Impasse 50/50 vs Quorum maioria simples
        if eh_paritaria_50_50:
            cl_maioria_sem_saida = []
            cl_maioria_ids = []
            tem_deadlock = any(
                any(k in (c["regra_texto"] or "").lower() for k in ("deadlock", "shotgun", "1.030", "empate"))
                for c in clausulas
            )
            for c in clausulas:
                t = (c["regra_texto"] or "").lower()
                if ("mais da metade do capital" in t or "maioria do capital" in t) and not any(
                    k in t for k in ("empate", "deadlock", "1.030", "shotgun", "composição futura", "composicao futura")
                ):
                    cl_maioria_sem_saida.append(c["numero_clausula"])
                    cl_maioria_ids.append(c["id"])
            if cl_maioria_sem_saida or not tem_deadlock:
                add_alerta(
                    "IMPASSE_50_50_QUORUM", "critico", "societario", "instrumentos",
                    "Quorum de maioria incompatível com paridade 50/50",
                    f"Em sociedade 50%/50%, maioria simples e inalcancavel em empate. Clausulas afetadas: {cl_maioria_sem_saida or 'ausencia de regra de deadlock'}.",
                    "Prever mediacao + Shotgun no MoU e via judicial (art. 1.030 CC) em Estacao 2 (/instrumentos).",
                    ancora=f"/instrumentos#clausula-{cl_maioria_ids[0]}" if cl_maioria_ids else "/instrumentos",
                )

        # Objeto Auditoria x CNAE 6920-6/02
        cnaes_ativos = [enq["cnae_principal"]] + list(enq["cnaes_secundarios"] or []) if enq else []
        menciona_auditoria = any("auditoria" in (c["regra_texto"] or "").lower() for c in clausulas if c["aplica_contrato"])
        if menciona_auditoria and "6920-6/02" not in cnaes_ativos:
            add_alerta(
                "CNAE_AUDITORIA_AUSENTE", "critico", "tributario", "cadastro",
                "Objeto social cita Auditoria sem CNAE 6920-6/02",
                "Contrato Social inclui Auditoria, mas Enquadramento possui apenas 6920-6/01.",
                "Incluir CNAE secundario 6920-6/02 em Estacao 1 (/cadastro) e revisar impacto no Fator R.",
                ancora="/cadastro#enquadramento",
            )

        # Cl. inicio atividades na assinatura ou dissolucao 180d sem SLU
        for c in clausulas:
            if not c["aplica_contrato"]:
                continue
            tl = (c["regra_texto"] or "").lower()
            if "na data de assinatura" in tl and "registro" not in tl:
                add_alerta(
                    "INICIO_NA_ASSINATURA", "alerta", "societario", "instrumentos",
                    "Inicio de atividades fixado na assinatura (e nao no registro JUCIS-DF)",
                    f"{c['numero_clausula']} fixa inicio na assinatura, contrariando arts. 1.151 e 1.154 do CC.",
                    "Corrigir clausula para iniciar formalmente na data de registro/arquivamento na JUCIS-DF.",
                    ancora=f"/instrumentos#clausula-{c['id']}",
                )
            if "dissolvida" in tl and "180 dias" in tl and "slu" not in tl and "unipessoal" not in tl:
                add_alerta(
                    "DISSOLUCAO_180D_SEM_SLU", "alerta", "societario", "instrumentos",
                    "Clausula obsoleta de dissolucao em 180 dias por unipessoalidade",
                    f"{c['numero_clausula']} nao contempla Sociedade Limitada Unipessoal (Lei 13.874/2019).",
                    "Adequar clausula para continuidade como SLU mantendo contadora RT.",
                    ancora=f"/instrumentos#clausula-{c['id']}",
                )

        # 4. Orcamento Oficial, Capital, Porte ME->EPP e Risco Tributario
        cur.execute(
            """
            SELECT * FROM erp.orcamento_cenario
            WHERE empresa_id = %s AND eh_oficial = true
            ORDER BY id DESC LIMIT 1
            """,
            (empresa_id,),
        )
        cen_of = cur.fetchone()
        if cen_of:
            anc_cen = f"/planejamento?cenario_id={cen_of['id']}#cenario-{cen_of['id']}"
            if soma_cap != int(cen_of["capital_social_centavos"]):
                add_alerta(
                    "CAPITAL_SOCIAL_DIVERGENTE", "critico", "contabil", "planejamento",
                    "Capital Social do Planejamento diverge das Quotas do QSA",
                    f"QSA soma R$ {soma_cap/100:,.2f} enquanto o cenario oficial usa R$ {cen_of['capital_social_centavos']/100:,.2f}.",
                    "Igualar o capital social entre Cadastro (/cadastro) e Planejamento (/planejamento).",
                    ancora=anc_cen,
                )
            if cen_of["regime_simulacao"] == "v1_fixo_6_erro":
                add_alerta(
                    "REGIME_V1_6PCT_INVALIDO", "critico", "tributario", "planejamento",
                    "Cenario oficial marcado com aliquota fixa erronea de 6% (v1)",
                    "O Simples Nacional exige calculo progressivo por RBT12 e avaliacao do Fator R.",
                    "Alterar regime_simulacao em /planejamento para calculo progressivo real.",
                    ancora=anc_cen,
                )
            if cen_of["regime_simulacao"] == "simples_segregado":
                add_alerta(
                    "PREMISSA_SEGREGACAO_85_15", "alerta", "tributario", "planejamento",
                    "Premissa de segregacao de receitas (85% / 15%) exige validacao da contadora",
                    (
                        f"O cenario '{cen_of['codigo_cenario']}' segrega {cen_of['pct_cnae_principal_micro']/10000:.1f}% "
                        "no CNAE 6920-6/01 (Anexo III sem Fator R) e o restante em 6920-6/02 (Anexo V se Fator R < 28%). "
                        "Essa premissa veio de rascunho_v2 e exige emissao discriminada em NFS-e/PGDAS-D."
                    ),
                    "Comparar no simulador com 'stress_fator_r_global' e 'planejamento_prolabore_28' antes de homologar.",
                    ancora=anc_cen,
                )
            cur.execute(
                """
                SELECT ano_ordem, rotulo_periodo, porte_estimado, receita_bruta_centavos,
                       fator_r_anual_micro, bp_caixa_centavos, bp_diferenca_centavos
                FROM erp.orcamento_demonstrativo_anual
                WHERE cenario_id = %s ORDER BY ano_ordem
                """,
                (cen_of["id"],),
            )
            dems = cur.fetchall()
            epp_checado = False
            for d in dems:
                if d["ano_ordem"] == 1 and d["fator_r_anual_micro"] < 280_000 and cen_of["regime_simulacao"] != "v1_fixo_6_erro":
                    add_alerta(
                        "FATOR_R_ANO1_ABAIXO_28", "info", "tributario", "planejamento",
                        f"Fator R do Ano 1 ({d['fator_r_anual_micro']/10000:.2f}%) abaixo de 28%",
                        "Devido a trava de 90d de pro-labore e ausencia de equipe CLT no Ano 1, receitas sujeitas ao Fator R (6920-6/02) tributam no Anexo V.",
                        "Ter a justificativa tecnica pronta na defesa (segregacao PGDAS-D ou ajuste de pro-labore).",
                        ancora=anc_cen,
                    )
                if d["bp_caixa_centavos"] < 0:
                    add_alerta(
                        f"CAIXA_NEGATIVO_ANO_{d['ano_ordem']}", "critico", "contabil", "planejamento",
                        f"Caixa negativo projetado em {d['rotulo_periodo']} ({d['bp_caixa_centavos']/100:,.2f})",
                        "As saidas operacionais e investimentos superaram o capital de giro disponivel no encerramento do periodo.",
                        "Reforcar capital inicial, postergar CAPEX ou ajustar custos fixos no cenario oficial.",
                        ancora=anc_cen,
                    )
                if not epp_checado and "EPP" in (d["porte_estimado"] or "") and enq and enq["porte"] == "ME":
                    epp_checado = True
                    menciona_epp = any("epp" in (c["regra_texto"] or "").lower() for c in clausulas if c["aplica_contrato"])
                    if not menciona_epp:
                        add_alerta(
                            "TRANSICAO_ME_EPP_OMISSA", "alerta", "tributario", "instrumentos",
                            "Projecao passa a EPP sem previsao contratual",
                            f"{d['rotulo_periodo']}: a receita do ano-calendario anterior ultrapassa R$ 360 mil, mas o Contrato Cl. 3ª nao menciona migracao ME -> EPP.",
                            "Registrar ciencia da transicao automatica (LC 123 art. 3º § 9º) na Cl. 3ª.",
                            ancora=next(
                                (f"/instrumentos#clausula-{c['id']}" for c in clausulas if c["aplica_contrato"] and "enquadramento" in (c["titulo"] or "").lower()),
                                "/instrumentos",
                            ),
                        )

        # 5. Backlog de Quarentena Anti-Enviesamento
        cur.execute(
            """
            SELECT modulo, COUNT(*) AS qtd
            FROM auditoria.vw_pendencias_quarentena
            WHERE empresa_id = %s AND status_validacao IN ('pendente_revisao', 'alerta_inconsistencia')
            GROUP BY modulo
            ORDER BY modulo
            """,
            (empresa_id,),
        )
        pends = cur.fetchall()
        total_pends = sum(int(p["qtd"]) for p in pends)
        if total_pends > 0:
            resumo_mod = ", ".join(f"{p['modulo']}: {p['qtd']}" for p in pends)
            add_alerta(
                "BACKLOG_QUARENTENA_REVISAO", "info", "governanca", "sustentacao",
                f"{total_pends} registros importados aguardando revisao/homologacao da contadora",
                f"Itens em quarentena por modulo -> {resumo_mod}.",
                "Inspecionar, ajustar se necessario, registrar justificativa tecnica e homologar nas 5 Estacoes.",
                ancora="/emissao#quarentena",
            )

        # Persiste substituindo alertas anteriores da empresa (mantem snapshot limpo do estado atual)
        cur.execute("DELETE FROM auditoria.alerta_coerencia WHERE empresa_id = %s", (empresa_id,))
        if alertas:
            execute_values(
                cur,
                """
                INSERT INTO auditoria.alerta_coerencia
                    (chave, empresa_id, codigo_regra, severidade, categoria, modulo_alvo, titulo, descricao, recomendacao, resolvido, ancora)
                VALUES %s
                """,
                [
                    (
                        a["chave"], empresa_id, a["codigo_regra"], a["severidade"], a["categoria"],
                        a["modulo_alvo"], a["titulo"], a["descricao"], a["recomendacao"], a["resolvido"], a["ancora"],
                    )
                    for a in alertas
                ],
            )
    return alertas


def recalcular_cenarios_empresa(conn: Any, emp_id: int) -> dict[str, Any]:
    """Recalcula todos os cenarios de uma empresa (sem commit). Retorna indicadores por codigo_cenario."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, codigo_cenario FROM erp.orcamento_cenario WHERE empresa_id = %s ORDER BY id", (emp_id,))
        cenarios = cur.fetchall()
    return {str(c["codigo_cenario"]): recalcular_cenario_no_banco(conn, int(c["id"])).indicadores for c in cenarios}


def recalcular_todos_cenarios_d1() -> dict[str, Any]:
    """Recalcula todos os cenarios da Prisma JRNA e atualiza os alertas de coerencia."""
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07'")
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Empresa emp:prisma_jrna_g07 nao encontrada.")
            emp_id = int(row["id"])
        resultados = recalcular_cenarios_empresa(conn, emp_id)
        alertas = validar_coerencia_dossie1(conn, emp_id)
        conn.commit()
    return {"cenarios": resultados, "qtd_alertas": len(alertas)}


if __name__ == "__main__":
    out = recalcular_todos_cenarios_d1()
    print("Recalculo Dossie 1 concluido. Qtd alertas:", out["qtd_alertas"])
    for k, v in out["cenarios"].items():
        print(f" - {k}: VPL=R${v['vpl_centavos']/100:,.2f} | TIR={v['tir_pct']}% | DAS3y=R${v['das_3_anos_centavos']/100:,.2f}")
