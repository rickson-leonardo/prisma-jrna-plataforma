"""Motor deterministico de calculo da Folha 09/2026, Provisoes, Partidas Dobradas e Coerencia (Dossie 2).

Todos os calculos sao em centavos inteiros. Le parametros de erp.parametro_legal e erp.contrato_trabalho
e grava erp.folha_competencia, erp.folha_item e lotes contabeis L1..L4 em erp.lancamento / erp.partida
(origem_registro = 'motor_calculo').
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any

from psycopg2.extras import execute_values

from sistema.pg.db import conectar_pg

EMPRESA_CHAVE_D2 = "emp:rota_sul_d2"

# ponytail: CPP 20% + RAT 2% + Terceiros FPAS 515 5,8% = 27,8% (278_000 micro); evolução: ler de erp.parametro_legal quando parametrizado.
ALIQ_EXCLUSAO_SIMPLES_MICRO_PADRAO = 278_000


def _round_cent(valor: Decimal) -> int:
    return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def impacto_exclusao_simples(itens: list[dict[str, Any]], parametros: list[dict[str, Any]] | None = None) -> int | None:
    """Calcula o custo patronal extra se a Rota Sul for excluida do Simples Nacional (PR-17)."""
    if not itens:
        return None
    base_exclusao = sum(
        int(it.get("valor_centavos") or 0)
        for it in itens
        if it.get("tipo_rubrica") == "provento" or it.get("codigo_rubrica") in ("PROV-13", "PROV-FER", "PROV-1/3")
    )
    if base_exclusao <= 0:
        return None
    par_excl = next((p for p in (parametros or []) if p.get("codigo") in ("EXCL-SIMPLES", "CPP-FORA-SIMPLES")), None)
    aliq_micro = int(par_excl["aliquota_micro"]) if par_excl and par_excl.get("aliquota_micro") else ALIQ_EXCLUSAO_SIMPLES_MICRO_PADRAO
    return _round_cent(Decimal(base_exclusao) * Decimal(aliq_micro) / Decimal("1000000"))


def detectar_residuos_texto_d2(
    secoes: list[dict[str, Any]],
    contratos_servico: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Detecta residuos de rascunho/IA ([INSERIR, [cite, 1.555/2018 nao revogada, XX.XXX, TODO, ???)."""
    achados: list[dict[str, str]] = []
    re_inserir = re.compile(r"(?<!`)\[INSERIR[^\]\n]*\](?!`)", re.IGNORECASE)
    re_cite = re.compile(r"(?<!`)\[cite[^\]]*\](?!`)", re.IGNORECASE)
    re_1555 = re.compile(r"1\.555/2018")
    re_xxxx = re.compile(r"XX\.XXX", re.IGNORECASE)
    re_todo = re.compile(r"\bTODO\b")
    re_interr = re.compile(r"\?\?\?")

    fontes: list[tuple[str, str]] = []
    for s in secoes or []:
        doc = str(s.get("documento") or "secao")
        cod = str(s.get("codigo_secao") or "")
        fontes.append((f"{doc}:{cod}", str(s.get("conteudo_md") or "")))
    for cs in contratos_servico or []:
        cod = str(cs.get("codigo_documento") or "contrato_servico")
        fontes.append((f"contrato_servico:{cod}", str(cs.get("conteudo_md") or "")))

    for origem, txt in fontes:
        if not txt:
            continue
        for nome_p, rx in (
            ("[INSERIR", re_inserir),
            ("[cite", re_cite),
            ("XX.XXX", re_xxxx),
            ("TODO", re_todo),
            ("???", re_interr),
        ):
            m = rx.search(txt)
            if m:
                ini = max(0, m.start() - 25)
                fim = min(len(txt), m.end() + 35)
                achados.append({"documento": origem, "padrao": nome_p, "trecho": txt[ini:fim].replace("\n", " ").strip()})
        for m in re_1555.finditer(txt):
            ini_frase = max(0, txt.rfind("\n", 0, m.start()), m.start() - 120)
            fim_nl = txt.find("\n", m.end())
            fim_frase = min(len(txt), fim_nl if fim_nl != -1 else len(txt), m.end() + 120)
            frase = txt[ini_frase:fim_frase].lower()
            # "revoga" cobre revogada, revogado, revogando e revogação
            if "revoga" not in frase and "1.708/2023" not in frase:
                achados.append({"documento": origem, "padrao": "1.555/2018", "trecho": txt[ini_frase:fim_frase].replace("\n", " ").strip()[:80]})
    return achados


def detectar_divergencia_contratos_d2(contratos_servico: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compara proposta, contrato e termo_rt (procuracao fica fora). Vigencia so compara contrato x termo_rt."""
    por_cod = {str(c.get("codigo_documento")): c for c in (contratos_servico or [])}
    comerciais = [por_cod[k] for k in ("proposta", "contrato", "termo_rt") if k in por_cod]
    if len(comerciais) < 2:
        return []
    divs: list[dict[str, Any]] = []
    for campo, rot in (
        ("honorario_mensal_centavos", "Honorário mensal"),
        ("tem_decimo_terceiro", "13º honorário"),
        ("valor_hora_centavos", "Valor da hora técnica"),
    ):
        vals = {str(c["codigo_documento"]): c.get(campo) for c in comerciais}
        if len(set(vals.values())) > 1:
            divs.append({"campo": campo, "rotulo": rot, "valores": vals})
    if "contrato" in por_cod and "termo_rt" in por_cod:
        vc = str(por_cod["contrato"].get("vigencia_inicio") or "")
        vt = str(por_cod["termo_rt"].get("vigencia_inicio") or "")
        if vc != vt:
            divs.append({"campo": "vigencia_inicio", "rotulo": "Vigência inicial (contrato × termo RT)", "valores": {"contrato": vc or "—", "termo_rt": vt or "—"}})
    return divs


def detectar_salario_abaixo_piso_d2(
    contratos_trabalho: list[dict[str, Any]],
    parametros: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Verifica salario_base_centavos < piso_cct_centavos e ausencia de piso/referencia CCT."""
    achados: list[dict[str, Any]] = []
    garantia_com = next(
        (int(p["valor_centavos"]) for p in (parametros or []) if p.get("codigo") == "CCT-GARANTIA-COM" and p.get("valor_centavos")),
        None,
    )
    for ct in contratos_trabalho or []:
        cod = str(ct.get("codigo_empregado") or "?")
        sal = int(ct.get("salario_base_centavos") or 0)
        piso = int(ct.get("piso_cct_centavos") or 0)
        ref = str(ct.get("cct_referencia") or "").strip()
        if piso <= 0 or not ref:
            achados.append({
                "codigo_empregado": cod,
                "tipo": "piso_ausente",
                "severidade": "alerta",
                "mensagem": f"{cod}: piso_cct_centavos ou cct_referencia vazio.",
            })
        piso_efetivo = garantia_com if (int(ct.get("comissao_pct_micro") or 0) > 0 and garantia_com) else piso
        if piso_efetivo > 0 and sal < piso_efetivo:
            achados.append({
                "codigo_empregado": cod,
                "tipo": "abaixo_piso",
                "severidade": "critico",
                "mensagem": f"{cod}: salário base ({sal/100:.2f}) abaixo do piso CCT ({piso_efetivo/100:.2f}).",
            })
    return achados


def recalcular_folha_independente_dados(
    comp: dict[str, Any],
    contratos: list[dict[str, Any]],
    parametros: list[dict[str, Any]],
    itens_motor: list[dict[str, Any]],
    parametros_ausentes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Recalculo independente (sem reutilizar funcoes do motor) de 100% das rubricas da folha D2."""
    if not comp or not contratos:
        return []

    ausentes = parametros_ausentes if parametros_ausentes is not None else []
    ausentes.clear()

    def _faltou(codigo: str) -> None:
        if codigo not in ausentes:
            ausentes.append(codigo)

    def rnd(val: Decimal) -> int:
        return int(val.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    dias_mes_raw = comp.get("dias_mes_padrao")
    if dias_mes_raw is None or int(dias_mes_raw) <= 0:
        _faltou("dias_mes_padrao")
        return []
    dias_mes = int(dias_mes_raw)

    por_cat: dict[str, list[dict[str, Any]]] = {}
    for p in parametros or []:
        por_cat.setdefault(str(p.get("categoria") or ""), []).append(p)

    faixas_inss = sorted(por_cat.get("inss", []), key=lambda x: int(x.get("ordem") or 0))
    pars_irrf = por_cat.get("irrf", [])
    pars_red = por_cat.get("reducao_irrf_2026", [])

    par_sf = (por_cat.get("salario_familia") or [None])[0]
    sf_ok = (
        par_sf is not None
        and par_sf.get("limite_centavos") is not None
        and par_sf.get("valor_centavos") is not None
    )
    teto_sf = int(par_sf["limite_centavos"]) if sf_ok else None
    cota_sf = int(par_sf["valor_centavos"]) if sf_ok else None

    par_fgts = (por_cat.get("fgts") or [None])[0]
    fgts_ok = par_fgts is not None and par_fgts.get("aliquota_micro") is not None
    aliq_fgts = Decimal(int(par_fgts["aliquota_micro"])) / Decimal("1000000") if fgts_ok else None

    ccts = por_cat.get("cct_clausula", [])
    par_vt_misto = next((p for p in ccts if p.get("codigo") == "CCT-VT-MISTO"), None)
    teto_vt_misto = (
        int(par_vt_misto["limite_centavos"])
        if par_vt_misto is not None and par_vt_misto.get("limite_centavos") is not None
        else None
    )

    par_neg = next((p for p in ccts if p.get("codigo") == "CCT-NEGOCIAL"), None)
    neg_ok = (
        par_neg is not None
        and par_neg.get("aliquota_micro") is not None
        and par_neg.get("limite_centavos") is not None
    )
    aliq_neg = Decimal(int(par_neg["aliquota_micro"])) / Decimal("1000000") if neg_ok else None
    teto_neg = int(par_neg["limite_centavos"]) if neg_ok else None

    par_simplif = next((p for p in pars_irrf if p.get("codigo") == "IRRF-SIMPLIF"), None)
    par_dep = next((p for p in pars_irrf if p.get("codigo") == "IRRF-DEP"), None)
    faixas_irrf = sorted(
        (p for p in pars_irrf if str(p.get("codigo") or "").startswith("IRRF-F")),
        key=lambda x: int(x.get("ordem") or 0),
    )
    par_red_isento = next((p for p in pars_red if p.get("codigo") == "RED-ISENTO"), None)
    par_red_trans = next((p for p in pars_red if p.get("codigo") == "RED-TRANS"), None)

    vendas_e2 = int(comp.get("vendas_liquidas_e2_centavos") or 0)
    dias_uteis_com_raw = comp.get("dias_uteis_comissao_e2")
    dom_e2_raw = comp.get("domingos_feriados_e2")
    cenario_neg = str(comp.get("cenario_negocial") or "A_desconta")

    motor_idx: dict[tuple[str, str], dict[str, Any]] = {
        (str(it.get("codigo_empregado") or ""), str(it.get("codigo_rubrica") or "")): it
        for it in (itens_motor or [])
    }
    vistos: set[tuple[str, str]] = set()
    puladas: set[tuple[str, str]] = set()
    resultado: list[dict[str, Any]] = []

    for ct in sorted(contratos, key=lambda x: str(x.get("codigo_empregado") or "")):
        cod = str(ct.get("codigo_empregado") or "")
        nome_emp = str(ct.get("nome_empregado") or cod)
        sal_base = int(ct.get("salario_base_centavos") or 0)
        dias_trab = int((comp.get("dias_trabalhados_e1") if cod == "E1" else comp.get("dias_trabalhados_e2")) or 0)
        dias_vt = int((comp.get("dias_uteis_vt_e1") if cod == "E1" else comp.get("dias_uteis_vt_e2")) or 0)
        dias_vr = int((comp.get("dias_uteis_vr_e1") if cod == "E1" else 0) or 0)

        sal_prop = rnd(Decimal(sal_base) * Decimal(dias_trab) / Decimal(dias_mes))
        rubricas_emp: list[tuple[str, str, int, int]] = [
            ("SAL-PROP", f"Salário Proporcional ({dias_trab}/{dias_mes})", sal_base, sal_prop),
        ]

        comissao = 0
        dsr = 0
        if int(ct.get("comissao_pct_micro") or 0) > 0:
            pct_com = Decimal(int(ct["comissao_pct_micro"])) / Decimal("1000000")
            comissao = rnd(Decimal(vendas_e2) * pct_com)
            rubricas_emp.append(("COMISSAO", "Comissão sobre Vendas Líquidas", vendas_e2, comissao))
            if dias_uteis_com_raw is not None and int(dias_uteis_com_raw) > 0 and dom_e2_raw is not None:
                dsr = rnd(Decimal(comissao) / Decimal(int(dias_uteis_com_raw)) * Decimal(int(dom_e2_raw)))
                rubricas_emp.append(("DSR-COM", "DSR sobre Comissões", comissao, dsr))
            else:
                if dias_uteis_com_raw is None or int(dias_uteis_com_raw) <= 0:
                    _faltou("dias_uteis_comissao_e2")
                if dom_e2_raw is None:
                    _faltou("domingos_feriados_e2")
                puladas.add((cod, "DSR-COM"))

        bruto = sal_prop + comissao + dsr
        deps_sf = int(ct.get("qtd_dependentes_sf") or 0)
        if sf_ok and teto_sf is not None and cota_sf is not None:
            sf_val = cota_sf * deps_sf if (sal_base <= teto_sf and deps_sf > 0) else 0
            rubricas_emp.append(("SAL-FAMILIA", "Salário-Família", sal_base, sf_val))
        else:
            _faltou("SF-2026")
            puladas.add((cod, "SAL-FAMILIA"))

        # INSS progressivo independente
        inss: int | None = None
        if not faixas_inss:
            _faltou("INSS-TABELA")
            puladas.add((cod, "INSS-RET"))
        else:
            ant = 0
            inss_acc = Decimal("0")
            inss_ok = True
            for fx in faixas_inss:
                if fx.get("limite_centavos") is None or fx.get("aliquota_micro") is None:
                    _faltou(str(fx.get("codigo") or "INSS-TABELA"))
                    inss_ok = False
                    break
                teto_fx = int(fx["limite_centavos"])
                aliq_fx = Decimal(int(fx["aliquota_micro"])) / Decimal("1000000")
                if bruto <= ant:
                    break
                fatia = min(bruto, teto_fx) - ant
                if fatia > 0:
                    inss_acc += Decimal(fatia) * aliq_fx
                ant = teto_fx
            if inss_ok:
                inss = rnd(inss_acc)
                rubricas_emp.append(("INSS-RET", "INSS Retido", bruto, inss))
            else:
                puladas.add((cod, "INSS-RET"))

        # IRRF 2026 independente
        irrf_ok = True
        if inss is None:
            irrf_ok = False
        if par_simplif is None or par_simplif.get("valor_centavos") is None:
            _faltou("IRRF-SIMPLIF")
            irrf_ok = False
        if par_dep is None or par_dep.get("valor_centavos") is None:
            _faltou("IRRF-DEP")
            irrf_ok = False
        if not faixas_irrf:
            _faltou("IRRF-TABELA")
            irrf_ok = False
        if par_red_isento is None or par_red_isento.get("limite_centavos") is None:
            _faltou("RED-ISENTO")
            irrf_ok = False

        if irrf_ok and inss is not None and par_simplif and par_dep and par_red_isento:
            simplif = int(par_simplif["valor_centavos"])
            val_dep = int(par_dep["valor_centavos"])
            ded_ir = max(inss + int(ct.get("qtd_dependentes_ir") or 0) * val_dep, simplif)
            base_ir = max(0, bruto - ded_ir)
            imp_tab: int | None = None
            for fx in faixas_irrf:
                lim = fx.get("limite_centavos")
                if lim is None or base_ir <= int(lim):
                    if fx.get("aliquota_micro") is None or fx.get("deducao_centavos") is None:
                        _faltou(str(fx.get("codigo") or "IRRF-TABELA"))
                        irrf_ok = False
                        break
                    aliq_ir = Decimal(int(fx["aliquota_micro"])) / Decimal("1000000")
                    ded_fx = int(fx["deducao_centavos"])
                    imp_tab = max(0, rnd(Decimal(base_ir) * aliq_ir) - ded_fx)
                    break
            if irrf_ok and imp_tab is None:
                _faltou("IRRF-TABELA")
                irrf_ok = False

            teto_isento = int(par_red_isento["limite_centavos"])
            red = 0
            if irrf_ok and imp_tab is not None:
                if bruto <= teto_isento:
                    red = imp_tab
                else:
                    if (
                        par_red_trans is None
                        or par_red_trans.get("limite_centavos") is None
                        or par_red_trans.get("deducao_centavos") is None
                        or par_red_trans.get("aliquota_micro") is None
                    ):
                        _faltou("RED-TRANS")
                        irrf_ok = False
                    elif bruto <= int(par_red_trans["limite_centavos"]):
                        fixo = int(par_red_trans["deducao_centavos"])
                        fator = Decimal(int(par_red_trans["aliquota_micro"])) / Decimal("1000000")
                        red = max(0, fixo - rnd(Decimal(bruto) * fator))
            if irrf_ok and imp_tab is not None:
                irrf = max(0, imp_tab - red)
                rubricas_emp.append(("IRRF", "IRRF 2026", base_ir, irrf))
            else:
                puladas.add((cod, "IRRF"))
        else:
            puladas.add((cod, "IRRF"))

        # VT (6% limitado ao custo) e subsidio
        if not ct.get("vt_optante"):
            rubricas_emp.append(("VT-DESC", "Desconto Vale-Transporte (6%)", sal_prop, 0))
            rubricas_emp.append(("VT-SUBS", "Subsídio Vale-Transporte Empresa", 0, 0))
        else:
            vt_ok = True
            tarifa_raw = ct.get("vt_tarifa_centavos")
            passagens_raw = ct.get("vt_passagens_dia")
            if tarifa_raw is None:
                _faltou(f"{cod}:vt_tarifa_centavos")
                vt_ok = False
            if passagens_raw is None:
                _faltou(f"{cod}:vt_passagens_dia")
                vt_ok = False
            if cod == "E2" and teto_vt_misto is None:
                _faltou("CCT-VT-MISTO")
                vt_ok = False
            if vt_ok and tarifa_raw is not None and passagens_raw is not None:
                vt_bruto = dias_vt * int(passagens_raw) * int(tarifa_raw)
                base_vt = (
                    min(sal_prop, rnd(Decimal(teto_vt_misto) * Decimal(dias_trab) / Decimal(dias_mes)))
                    if cod == "E2" and teto_vt_misto is not None
                    else sal_prop
                )
                vt_desc = min(rnd(Decimal(base_vt) * Decimal("0.06")), vt_bruto)
                vt_subs = max(0, vt_bruto - vt_desc)
                rubricas_emp.append(("VT-DESC", "Desconto Vale-Transporte (6%)", base_vt, vt_desc))
                rubricas_emp.append(("VT-SUBS", "Subsídio Vale-Transporte Empresa", vt_bruto, vt_subs))
            else:
                puladas.add((cod, "VT-DESC"))
                puladas.add((cod, "VT-SUBS"))

        # VR
        vr_val = dias_vr * int(ct.get("vr_valor_dia_centavos") or 0) if ct.get("vr_elegivel") else 0
        if vr_val > 0:
            rubricas_emp.append(("VR-PAT", "Vale-Refeição (CLT art. 457, § 2º)", vr_val, vr_val))

        # Contribuicao Negocial e FGTS
        if neg_ok and aliq_neg is not None and teto_neg is not None:
            neg_a = min(rnd(Decimal(bruto) * aliq_neg), teto_neg)
            neg_ativo = neg_a if cenario_neg == "A_desconta" else 0
            rubricas_emp.append(("NEGOCIAL", "Contribuição Negocial CCT", bruto, neg_ativo))
        else:
            _faltou("CCT-NEGOCIAL")
            puladas.add((cod, "NEGOCIAL"))

        if fgts_ok and aliq_fgts is not None:
            fgts = rnd(Decimal(bruto) * aliq_fgts)
            rubricas_emp.append(("FGTS-8", "FGTS (8%)", bruto, fgts))
        else:
            _faltou("FGTS-8")
            puladas.add((cod, "FGTS-8"))

        # Provisoes (>= 15 dias)
        if dias_trab >= 15:
            p13 = rnd(Decimal(sal_base) / Decimal("12"))
            pfer = rnd(Decimal(sal_base) / Decimal("12"))
            pter = rnd(Decimal(pfer) / Decimal("3"))
            rubricas_emp.extend([
                ("PROV-13", "Provisão 13º Salário (1/12 avo)", sal_base, p13),
                ("PROV-FER", "Provisão Férias (1/12 avo)", sal_base, pfer),
                ("PROV-1/3", "Provisão 1/3 Constitucional de Férias", pfer, pter),
            ])
            if fgts_ok and aliq_fgts is not None:
                pfgts = rnd(Decimal(p13 + pfer + pter) * aliq_fgts)
                rubricas_emp.append(("PROV-FGTS", "FGTS s/ Provisões (8%)", p13 + pfer + pter, pfgts))
            else:
                _faltou("FGTS-8")
                puladas.add((cod, "PROV-FGTS"))

        for cod_rub, nome_rub, base_rec, val_rec in rubricas_emp:
            vistos.add((cod, cod_rub))
            it_m = motor_idx.get((cod, cod_rub))
            val_mot = int(it_m.get("valor_centavos") or 0) if it_m else 0
            resultado.append({
                "codigo_empregado": cod,
                "nome_empregado": nome_emp,
                "codigo_rubrica": cod_rub,
                "nome_rubrica": str(it_m.get("nome_rubrica") or nome_rub) if it_m else nome_rub,
                "base_centavos": int(it_m.get("base_centavos") or base_rec) if it_m else base_rec,
                "valor_motor_centavos": val_mot,
                "valor_recalculado_centavos": val_rec,
                "diferenca_centavos": val_mot - val_rec,
            })

    for (cod, cod_rub), it_m in motor_idx.items():
        if (cod, cod_rub) not in vistos and (cod, cod_rub) not in puladas:
            val_mot = int(it_m.get("valor_centavos") or 0)
            resultado.append({
                "codigo_empregado": cod,
                "nome_empregado": str(it_m.get("nome_empregado") or cod),
                "codigo_rubrica": cod_rub,
                "nome_rubrica": str(it_m.get("nome_rubrica") or cod_rub),
                "base_centavos": int(it_m.get("base_centavos") or 0),
                "valor_motor_centavos": val_mot,
                "valor_recalculado_centavos": 0,
                "diferenca_centavos": val_mot,
            })

    return resultado


def detectar_recalculo_divergente_d2(comparativo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retorna rubricas com diferenca diferente de zero entre motor e recalculo independente."""
    return [r for r in (comparativo or []) if int(r.get("diferenca_centavos") or 0) != 0]


def recalcular_folha_independente(conn: Any, competencia_id: int | None = None) -> list[dict[str, Any]]:
    """Le competencia, contratos, parametros e folha_item no PostgreSQL e executa o recalculo independente."""
    with conn.cursor() as cur:
        if competencia_id is None:
            cur.execute(
                """
                SELECT fc.*
                FROM erp.folha_competencia fc
                JOIN erp.empresa e ON e.id = fc.empresa_id
                WHERE e.chave = %s
                ORDER BY fc.competencia DESC LIMIT 1
                """,
                (EMPRESA_CHAVE_D2,),
            )
        else:
            cur.execute("SELECT * FROM erp.folha_competencia WHERE id = %s", (competencia_id,))
        fc = cur.fetchone()
        if not fc:
            return []
        emp_id = int(fc["empresa_id"])
        cur.execute("SELECT * FROM erp.contrato_trabalho WHERE empresa_id = %s ORDER BY codigo_empregado, id", (emp_id,))
        cts = cur.fetchall()
        cur.execute("SELECT * FROM erp.parametro_legal WHERE empresa_id = %s ORDER BY categoria, ordem, id", (emp_id,))
        pars = cur.fetchall()
        cur.execute(
            """
            SELECT fi.*, ct.codigo_empregado, ct.nome_empregado
            FROM erp.folha_item fi
            JOIN erp.contrato_trabalho ct ON ct.id = fi.contrato_trabalho_id
            WHERE fi.competencia_id = %s
            ORDER BY ct.codigo_empregado, fi.ordem, fi.id
            """,
            (fc["id"],),
        )
        itens = cur.fetchall()
    return recalcular_folha_independente_dados(dict(fc), [dict(c) for c in cts], [dict(p) for p in pars], [dict(i) for i in itens])


def _calc_inss_progressivo(base_centavos: int, faixas: list[dict[str, Any]]) -> tuple[int, str]:
    """INSS progressivo por faixas (Portaria MPS/MF no 13/2026)."""
    if base_centavos <= 0 or not faixas:
        return 0, "Base zero"
    anterior = 0
    total = Decimal("0")
    partes: list[str] = []
    for f in sorted(faixas, key=lambda x: int(x["ordem"])):
        teto = int(f["limite_centavos"] or 847555)
        aliq = Decimal(int(f["aliquota_micro"] or 0)) / Decimal("1000000")
        if base_centavos <= anterior:
            break
        fatia = min(base_centavos, teto) - anterior
        if fatia > 0:
            imp = Decimal(fatia) * aliq
            total += imp
            partes.append(f"{fatia/100:.2f}x{float(aliq)*100:.1f}%")
        anterior = teto
    return _round_cent(total), " + ".join(partes)


def _calc_irrf_2026(
    bruto_centavos: int,
    inss_centavos: int,
    qtd_deps: int,
    params_irrf: list[dict[str, Any]],
    params_red: list[dict[str, Any]],
) -> tuple[int, int, str]:
    """IRRF 2026 com comparacao (INSS + dependentes vs Desconto Simplificado) e Reducao Lei 15.270/2025."""
    simplif = next((int(p["valor_centavos"] or 60720) for p in params_irrf if p["codigo"] == "IRRF-SIMPLIF"), 60720)
    val_dep = next((int(p["valor_centavos"] or 18959) for p in params_irrf if p["codigo"] == "IRRF-DEP"), 18959)
    ded_legais = inss_centavos + qtd_deps * val_dep
    ded_usada = max(ded_legais, simplif)
    base = max(0, bruto_centavos - ded_usada)
    faixas = [p for p in params_irrf if p["codigo"].startswith("IRRF-F")]
    imposto_tabela = 0
    for f in sorted(faixas, key=lambda x: int(x["ordem"])):
        lim = f["limite_centavos"]
        if lim is None or base <= int(lim):
            aliq = Decimal(int(f["aliquota_micro"] or 0)) / Decimal("1000000")
            ded_fx = int(f["deducao_centavos"] or 0)
            imposto_tabela = max(0, _round_cent(Decimal(base) * aliq) - ded_fx)
            break

    redutor = 0
    teto_isento = next((int(p["limite_centavos"] or 500000) for p in params_red if p["codigo"] == "RED-ISENTO"), 500000)
    teto_trans = next((int(p["limite_centavos"] or 735000) for p in params_red if p["codigo"] == "RED-TRANS"), 735000)
    if bruto_centavos <= teto_isento:
        redutor = imposto_tabela
    elif bruto_centavos <= teto_trans:
        p_trans = next((p for p in params_red if p["codigo"] == "RED-TRANS"), None)
        fixo = int(p_trans["deducao_centavos"] or 97862) if p_trans else 97862
        fator = Decimal(int(p_trans["aliquota_micro"] or 133145)) / Decimal("1000000") if p_trans else Decimal("0.133145")
        redutor = max(0, fixo - _round_cent(Decimal(bruto_centavos) * fator))

    irrf_final = max(0, imposto_tabela - redutor)
    modo = "Simplificado" if ded_usada == simplif else "Legal"
    return irrf_final, base, f"Base {base/100:.2f} ({modo} {ded_usada/100:.2f}); Lei 15.270 zera ate 5k"


CONTAS_FOLHA_D2: tuple[tuple[str, str, int, str], ...] = (
    ("2.1.2.01", "Salários a Pagar", 2, "C"),
    ("2.1.2.02", "INSS a Recolher (Retido — DCTFWeb)", 2, "C"),
    ("2.1.2.03", "FGTS a Recolher (FGTS Digital)", 2, "C"),
    ("2.1.2.05", "Contribuição Negocial a Recolher (CCT SECEG)", 2, "C"),
    ("2.1.2.06", "VT/VR a Pagar (Operadoras de Benefícios)", 2, "C"),
    ("2.1.2.10", "Provisão para 13º Salário", 2, "C"),
    ("2.1.2.11", "Provisão para Férias e 1/3 Constitucional", 2, "C"),
    ("2.1.2.12", "Provisão de FGTS s/ 13º e Férias", 2, "C"),
    ("4.1.1.01", "Despesas Administrativas — Salários (E1)", 4, "D"),
    ("4.1.1.03", "Despesas Administrativas — FGTS (E1)", 4, "D"),
    ("4.1.1.05", "Despesas Administrativas — Vale-Transporte (E1)", 4, "D"),
    ("4.1.1.06", "Despesas Administrativas — Vale-Refeição (E1)", 4, "D"),
    ("4.1.1.07", "Despesas Administrativas — Provisão 13º Salário (E1)", 4, "D"),
    ("4.1.1.08", "Despesas Administrativas — Provisão Férias e 1/3 (E1)", 4, "D"),
    ("4.1.1.09", "Despesas Administrativas — FGTS s/ Provisões (E1)", 4, "D"),
    ("4.2.1.01", "Despesas Comerciais — Salários Fixos (E2)", 4, "D"),
    ("4.2.1.02", "Despesas Comerciais — Comissões e DSR (E2)", 4, "D"),
    ("4.2.1.03", "Despesas Comerciais — FGTS (E2)", 4, "D"),
    ("4.2.1.05", "Despesas Comerciais — Vale-Transporte (E2)", 4, "D"),
)


def _garantir_contas_folha_d2(cur: Any, emp_id: int) -> dict[str, int]:
    for codigo, nome, grupo, nat in CONTAS_FOLHA_D2:
        cur.execute(
            """
            INSERT INTO erp.conta_contabil (chave, codigo, nome, grupo, natureza, empresa_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (codigo) DO UPDATE SET nome = EXCLUDED.nome
            """,
            (f"cc:d2:{codigo}", codigo, nome, grupo, nat, emp_id),
        )
    cur.execute(
        "SELECT id, codigo FROM erp.conta_contabil WHERE codigo = ANY(%s)",
        ([c[0] for c in CONTAS_FOLHA_D2],),
    )
    return {r["codigo"]: int(r["id"]) for r in cur.fetchall()}


def _historico_lote_l3(cts: list[dict[str, Any]], competencia: str) -> str:
    """Monta o historico do lote L3 a partir de vt_passagens_dia dos contratos e da competencia."""
    comp_fmt = f"{competencia[5:7]}/{competencia[:4]}" if len(competencia) == 7 and competencia[4] == "-" else competencia
    vt_itens = [
        (str(ct.get("codigo_empregado") or "?"), int(ct["vt_passagens_dia"]))
        for ct in cts
        if ct.get("vt_optante") and ct.get("vt_passagens_dia") is not None
    ]
    if not vt_itens:
        vt_txt = "VT"
    elif len({p for _, p in vt_itens}) == 1:
        vt_txt = f"VT ({vt_itens[0][1]}/dia)"
    else:
        vt_txt = "VT (" + ", ".join(f"{cod} {p}/dia" for cod, p in vt_itens) + ")"
    return f"L3 — Apropriação de Benefícios {vt_txt} e VR {comp_fmt}"


def recalcular_folha_d2(conn: Any, competencia_id: int | None = None) -> dict[str, Any]:
    """Recalcula a folha 09/2026 da Rota Sul, grava rubricas e lotes L1..L4 em partidas dobradas."""
    with conn.cursor() as cur:
        if competencia_id is None:
            cur.execute(
                """
                SELECT fc.*
                FROM erp.folha_competencia fc
                JOIN erp.empresa e ON e.id = fc.empresa_id
                WHERE e.chave = %s
                ORDER BY fc.competencia DESC LIMIT 1
                """,
                (EMPRESA_CHAVE_D2,),
            )
        else:
            cur.execute("SELECT * FROM erp.folha_competencia WHERE id = %s", (competencia_id,))
        fc = cur.fetchone()
        if not fc:
            raise RuntimeError("Competencia de folha nao encontrada para D2.")
        fc_id = int(fc["id"])
        emp_id = int(fc["empresa_id"])

        cur.execute("SELECT * FROM erp.contrato_trabalho WHERE empresa_id = %s ORDER BY codigo_empregado, id", (emp_id,))
        cts = cur.fetchall()
        if len(cts) < 2:
            raise RuntimeError("Contratos de trabalho E1/E2 nao encontrados para Rota Sul D2.")

        cur.execute("SELECT * FROM erp.parametro_legal WHERE empresa_id = %s ORDER BY categoria, ordem", (emp_id,))
        pars = cur.fetchall()
        by_cat: dict[str, list[dict[str, Any]]] = {}
        for p in pars:
            by_cat.setdefault(p["categoria"], []).append(dict(p))

        par_sf = (by_cat.get("salario_familia") or [{}])[0]
        teto_sf = int(par_sf.get("limite_centavos") or 198038)
        cota_sf = int(par_sf.get("valor_centavos") or 6754)
        aliq_fgts = Decimal(int((by_cat.get("fgts") or [{}])[0].get("aliquota_micro") or 80000)) / Decimal("1000000")
        par_vt_cct = next((p for p in by_cat.get("cct_clausula", []) if p["codigo"] == "CCT-VT-MISTO"), {})
        teto_vt_misto = int(par_vt_cct.get("limite_centavos") or 225750)
        par_neg = next((p for p in by_cat.get("cct_clausula", []) if p["codigo"] == "CCT-NEGOCIAL"), {})
        aliq_neg = Decimal(int(par_neg.get("aliquota_micro") or 33300)) / Decimal("1000000")
        teto_neg = int(par_neg.get("limite_centavos") or 14800)

        dias_mes = max(int(fc["dias_mes_padrao"] or 30), 1)
        vendas_e2 = int(fc["vendas_liquidas_e2_centavos"] or 0)
        dias_uteis_com = max(int(fc["dias_uteis_comissao_e2"] or 9), 1)
        dom_e2 = int(fc["domingos_feriados_e2"] or 1)
        cenario_neg = str(fc["cenario_negocial"] or "A_desconta")

        itens: list[tuple[Any, ...]] = []
        tot = {
            "bruto": 0, "inss": 0, "irrf": 0, "fgts": 0,
            "vt_desc": 0, "vt_subs": 0, "vt_subs_2d": 0, "vr": 0,
            "neg_a": 0, "neg_b": 0, "liq_a": 0, "liq_b": 0,
            "prov_13": 0, "prov_ferias": 0, "prov_terco": 0, "prov_fgts": 0, "prov_total": 0,
            "custo_adm": 0, "custo_com": 0,
        }
        res_emp: dict[str, dict[str, int]] = {}

        for ct in cts:
            cod = ct["codigo_empregado"]
            ct_id = int(ct["id"])
            sal_base = int(ct["salario_base_centavos"])
            dias_trab = int(fc["dias_trabalhados_e1"] if cod == "E1" else fc["dias_trabalhados_e2"])
            dias_vt = int(fc["dias_uteis_vt_e1"] if cod == "E1" else fc["dias_uteis_vt_e2"])
            dias_vr = int(fc["dias_uteis_vr_e1"] if cod == "E1" else 0)

            sal_prop = _round_cent(Decimal(sal_base) * Decimal(dias_trab) / Decimal(dias_mes))
            itens.append((
                f"fi:{fc['competencia']}:{cod}:SAL", fc_id, ct_id, 1, "SAL-PROP",
                f"Salário {'Fixo ' if cod == 'E2' else ''}Proporcional ({dias_trab}/{dias_mes})",
                "provento", f"{dias_trab} dias", sal_base, sal_prop,
                f"{sal_base/100:.2f} / {dias_mes} * {dias_trab}", "CLT art. 64 / Admissão set/2026",
                True, True, True, "motor_calculo", "pendente_revisao",
            ))

            comissao = 0
            dsr = 0
            if int(ct["comissao_pct_micro"] or 0) > 0:
                pct_com = Decimal(int(ct["comissao_pct_micro"])) / Decimal("1000000")
                comissao = _round_cent(Decimal(vendas_e2) * pct_com)
                dsr = _round_cent(Decimal(comissao) / Decimal(dias_uteis_com) * Decimal(dom_e2))
                itens.append((
                    f"fi:{fc['competencia']}:{cod}:COM", fc_id, ct_id, 2, "COMISSAO",
                    "Comissão sobre Vendas Líquidas (1,5%)", "provento", "1,50%", vendas_e2, comissao,
                    f"1,5% * {vendas_e2/100:.2f}", "Contrato Cl. 3ª / Lei 3.207/1957",
                    True, True, True, "motor_calculo", "pendente_revisao",
                ))
                itens.append((
                    f"fi:{fc['competencia']}:{cod}:DSR", fc_id, ct_id, 3, "DSR-COM",
                    "DSR sobre Comissões (rubrica destacada)", "provento", f"{dom_e2}/{dias_uteis_com}", comissao, dsr,
                    f"{comissao/100:.2f} / {dias_uteis_com} * {dom_e2}", "Lei nº 605/1949; Súmula 27 TST",
                    True, True, True, "motor_calculo", "pendente_revisao",
                ))

            bruto = sal_prop + comissao + dsr
            # Salario-Familia: aferido pelo salario contratual integral na admissao
            sf_val = cota_sf * int(ct["qtd_dependentes_sf"] or 0) if sal_base <= teto_sf and int(ct["qtd_dependentes_sf"] or 0) > 0 else 0
            itens.append((
                f"fi:{fc['competencia']}:{cod}:SF", fc_id, ct_id, 4, "SAL-FAMILIA",
                "Salário-Família (Portaria MPS/MF 13/2026)", "informativo",
                "Inelegível (> R$ 1.980,38)" if sf_val == 0 and int(ct["qtd_dependentes_sf"] or 0) > 0 else "0 dep.",
                sal_base, sf_val, f"Sal. contratual {sal_base/100:.2f} vs teto {teto_sf/100:.2f}",
                "Dec. 3.048/1999 art. 82; Port. MPS/MF 13/2026", False, False, False, "motor_calculo", "pendente_revisao",
            ))

            inss, mem_inss = _calc_inss_progressivo(bruto, by_cat.get("inss", []))
            itens.append((
                f"fi:{fc['competencia']}:{cod}:INSS", fc_id, ct_id, 5, "INSS-RET",
                "INSS Retido (Tabela Progressiva 2026)", "desconto", "Progressivo", bruto, inss,
                mem_inss, "Portaria MPS/MF nº 13/2026", False, False, False, "motor_calculo", "pendente_revisao",
            ))

            irrf, base_irrf, mem_irrf = _calc_irrf_2026(
                bruto, inss, int(ct["qtd_dependentes_ir"] or 0),
                by_cat.get("irrf", []), by_cat.get("reducao_irrf_2026", []),
            )
            itens.append((
                f"fi:{fc['competencia']}:{cod}:IRRF", fc_id, ct_id, 6, "IRRF",
                "IRRF 2026 (Lei 15.270/2025 + Simplificado)", "desconto", "Isento", base_irrf, irrf,
                mem_irrf, "Lei nº 15.270/2025; RFB 2026", False, False, False, "motor_calculo", "pendente_revisao",
            ))

            # Vale-Transporte
            tarifa = int(ct["vt_tarifa_centavos"] or 430)
            passagens = int(ct["vt_passagens_dia"] or 4)
            vt_bruto = dias_vt * passagens * tarifa if ct["vt_optante"] else 0
            vt_bruto_2d = dias_vt * 2 * tarifa if ct["vt_optante"] else 0
            base_vt = min(sal_prop, _round_cent(Decimal(teto_vt_misto) * Decimal(dias_trab) / Decimal(dias_mes))) if cod == "E2" else sal_prop
            vt_desc = min(_round_cent(Decimal(base_vt) * Decimal("0.06")), vt_bruto) if ct["vt_optante"] else 0
            vt_subs = max(0, vt_bruto - vt_desc)
            vt_subs_2d = max(0, vt_bruto_2d - min(_round_cent(Decimal(base_vt) * Decimal("0.06")), vt_bruto_2d))
            itens.append((
                f"fi:{fc['competencia']}:{cod}:VT-DESC", fc_id, ct_id, 7, "VT-DESC",
                "Desconto Vale-Transporte (6% Salário Básico)", "desconto", f"6% s/ {base_vt/100:.2f}", base_vt, vt_desc,
                f"min(6% * {base_vt/100:.2f}, VT bruto {vt_bruto/100:.2f})", "Lei 7.418/1985 art. 4º; CCT Cl. 6ª",
                False, False, False, "motor_calculo", "pendente_revisao",
            ))
            itens.append((
                f"fi:{fc['competencia']}:{cod}:VT-SUBS", fc_id, ct_id, 8, "VT-SUBS",
                f"Subsídio Vale-Transporte Empresa ({passagens}/dia)", "informativo", f"{dias_vt}d x {passagens}/d",
                vt_bruto, vt_subs, f"{vt_bruto/100:.2f} - {vt_desc/100:.2f}",
                "Lei 7.418/1985", False, False, False, "motor_calculo", "pendente_revisao",
            ))

            # Vale-Refeicao (auxilio-alimentacao nao pago em dinheiro: CLT art. 457, par. 2)
            vr_val = dias_vr * int(ct["vr_valor_dia_centavos"] or 0) if ct["vr_elegivel"] else 0
            if vr_val > 0:
                itens.append((
                    f"fi:{fc['competencia']}:{cod}:VR", fc_id, ct_id, 9, "VR-PAT",
                    "Vale-Refeição (CLT art. 457, § 2º)", "informativo", f"{dias_vr}d x R$ 30,00",
                    vr_val, vr_val, f"{dias_vr} * {int(ct['vr_valor_dia_centavos'])/100:.2f}",
                    "CLT art. 457, § 2º (EC02, p. 3: R$ 30,00/dia trabalhado)", False, False, False, "motor_calculo", "pendente_revisao",
                ))

            # Contribuicao Negocial (Cenario A vs B)
            neg_a = min(_round_cent(Decimal(bruto) * aliq_neg), teto_neg)
            neg_ativo = neg_a if cenario_neg == "A_desconta" else 0
            itens.append((
                f"fi:{fc['competencia']}:{cod}:NEG", fc_id, ct_id, 10, "NEGOCIAL",
                f"Contribuição Negocial CCT (Cenário {'A' if cenario_neg == 'A_desconta' else 'B'})",
                "desconto", "3,33% (teto 148)", bruto, neg_ativo,
                f"Cenário A={neg_a/100:.2f} | Cenário B=0,00", "CCT Adit. 2026/2027 Cl. 11ª; STF Tema 935",
                False, False, False, "motor_calculo", "pendente_revisao",
            ))

            fgts = _round_cent(Decimal(bruto) * aliq_fgts)
            itens.append((
                f"fi:{fc['competencia']}:{cod}:FGTS", fc_id, ct_id, 11, "FGTS-8",
                "FGTS da Folha (8% — FGTS Digital)", "encargo", "8,00%", bruto, fgts,
                f"8% * {bruto/100:.2f}", "Lei nº 8.036/1990", False, False, False, "motor_calculo", "pendente_revisao",
            ))

            liq_a = bruto - inss - irrf - vt_desc - neg_a
            liq_b = bruto - inss - irrf - vt_desc

            # Provisoes (1/12 avo se >= 15 dias trabalhados)
            p13 = pfer = pter = pfgts = ptot = 0
            if dias_trab >= 15:
                p13 = _round_cent(Decimal(sal_base) / Decimal("12"))
                pfer = _round_cent(Decimal(sal_base) / Decimal("12"))
                pter = _round_cent(Decimal(pfer) / Decimal("3"))
                pfgts = _round_cent(Decimal(p13 + pfer + pter) * aliq_fgts)
                ptot = p13 + pfer + pter + pfgts
                for o_p, cp, np, vp, fp in (
                    (12, "PROV-13", "Provisão 13º Salário (1/12 avo)", p13, f"{sal_base/100:.2f} / 12"),
                    (13, "PROV-FER", "Provisão Férias (1/12 avo)", pfer, f"{sal_base/100:.2f} / 12"),
                    (14, "PROV-1/3", "Provisão 1/3 Constitucional de Férias", pter, f"{pfer/100:.2f} / 3"),
                    (15, "PROV-FGTS", "FGTS s/ Provisões (8%)", pfgts, f"8% * {(p13+pfer+pter)/100:.2f}"),
                ):
                    itens.append((
                        f"fi:{fc['competencia']}:{cod}:{cp}", fc_id, ct_id, o_p, cp, np, "provisao",
                        "1/12 avo", sal_base, vp, fp, "Lei 4.090/62; CLT art. 146; NBC TG 33",
                        False, False, False, "motor_calculo", "pendente_revisao",
                    ))

            tot["bruto"] += bruto
            tot["inss"] += inss
            tot["irrf"] += irrf
            tot["fgts"] += fgts
            tot["vt_desc"] += vt_desc
            tot["vt_subs"] += vt_subs
            tot["vt_subs_2d"] += vt_subs_2d
            tot["vr"] += vr_val
            tot["neg_a"] += neg_a
            tot["liq_a"] += liq_a
            tot["liq_b"] += liq_b
            tot["prov_13"] += p13
            tot["prov_ferias"] += pfer
            tot["prov_terco"] += pter
            tot["prov_fgts"] += pfgts
            tot["prov_total"] += ptot
            custo_ind = bruto + fgts + vt_subs + vr_val + ptot
            if ct["departamento"] == "administrativo":
                tot["custo_adm"] += custo_ind
            else:
                tot["custo_com"] += custo_ind
            res_emp[cod] = {
                "sal_prop": sal_prop, "comissao": comissao, "dsr": dsr, "bruto": bruto,
                "inss": inss, "irrf": irrf, "vt_bruto": vt_bruto, "vt_desc": vt_desc,
                "vt_subs": vt_subs, "vr": vr_val, "neg_a": neg_a, "liq_a": liq_a,
                "liq_b": liq_b, "fgts": fgts, "prov_13": p13, "prov_fer": pfer + pter,
                "prov_fgts": pfgts, "prov_total": ptot, "custo": custo_ind,
            }

        custo_total = tot["custo_adm"] + tot["custo_com"]
        neg_ativo_tot = tot["neg_a"] if cenario_neg == "A_desconta" else 0
        liq_ativo_tot = tot["liq_a"] if cenario_neg == "A_desconta" else tot["liq_b"]

        # Persiste itens e totais na competencia
        cur.execute("DELETE FROM erp.folha_item WHERE competencia_id = %s", (fc_id,))
        execute_values(
            cur,
            """
            INSERT INTO erp.folha_item
                (chave, competencia_id, contrato_trabalho_id, ordem, codigo_rubrica, nome_rubrica,
                 tipo_rubrica, referencia_texto, base_centavos, valor_centavos, formula_texto,
                 fonte_normativa, incide_inss, incide_irrf, incide_fgts, origem_registro, status_validacao)
            VALUES %s
            """,
            itens,
        )
        cur.execute(
            """
            UPDATE erp.folha_competencia
            SET status_folha = CASE WHEN status_folha = 'homologada' THEN 'homologada' ELSE 'calculada' END,
                bruto_total_centavos = %s,
                inss_total_centavos = %s,
                fgts_total_centavos = %s,
                liquido_total_centavos = %s,
                provisoes_total_centavos = %s,
                custo_total_centavos = %s
            WHERE id = %s
            """,
            (tot["bruto"], tot["inss"], tot["fgts"], liq_ativo_tot, tot["prov_total"], custo_total, fc_id),
        )

        # Contabilizacao em Partidas Dobradas (L1..L4)
        cc_map = _garantir_contas_folha_d2(cur, emp_id)
        cur.execute("SELECT id FROM erp.lancamento WHERE empresa_id = %s AND origem_registro = 'motor_calculo'", (emp_id,))
        old_lids = [int(r["id"]) for r in cur.fetchall()]
        if old_lids:
            cur.execute("DELETE FROM erp.partida WHERE lancamento_id = ANY(%s)", (old_lids,))
            cur.execute("DELETE FROM erp.lancamento WHERE id = ANY(%s)", (old_lids,))

        e1 = res_emp["E1"]
        e2 = res_emp["E2"]
        lotes = [
            (1, "L1 — Apropriação da Folha de Pagamento 09/2026 (E1 Adm + E2 Com) e Retenções", "folha_l1", [
                ("4.1.1.01", "D", e1["sal_prop"]),
                ("4.2.1.01", "D", e2["sal_prop"]),
                ("4.2.1.02", "D", e2["comissao"] + e2["dsr"]),
                ("2.1.2.01", "C", liq_ativo_tot),
                ("2.1.2.02", "C", tot["inss"]),
                ("2.1.2.05", "C", neg_ativo_tot),
                ("4.1.1.05", "C", e1["vt_desc"]),
                ("4.2.1.05", "C", e2["vt_desc"]),
            ]),
            (2, "L2 — Encargo FGTS 8% s/ Folha 09/2026 (FGTS Digital PIX)", "folha_l2", [
                ("4.1.1.03", "D", e1["fgts"]),
                ("4.2.1.03", "D", e2["fgts"]),
                ("2.1.2.03", "C", tot["fgts"]),
            ]),
            (3, _historico_lote_l3([dict(c) for c in cts], str(fc["competencia"])), "folha_l3", [
                ("4.1.1.05", "D", e1["vt_bruto"]),
                ("4.2.1.05", "D", e2["vt_bruto"]),
                ("4.1.1.06", "D", e1["vr"]),
                ("2.1.2.06", "C", e1["vt_bruto"] + e2["vt_bruto"] + e1["vr"]),
            ]),
            (4, "L4 — Provisões Trabalhistas 09/2026 (1/12 avo E1: 13º, Férias+1/3 e FGTS)", "folha_l4", [
                ("4.1.1.07", "D", tot["prov_13"]),
                ("4.1.1.08", "D", tot["prov_ferias"] + tot["prov_terco"]),
                ("4.1.1.09", "D", tot["prov_fgts"]),
                ("2.1.2.10", "C", tot["prov_13"]),
                ("2.1.2.11", "C", tot["prov_ferias"] + tot["prov_terco"]),
                ("2.1.2.12", "C", tot["prov_fgts"]),
            ]),
        ]
        partidas_total_d = 0
        partidas_total_c = 0
        for num_l, hist, tag, linhas in lotes:
            linhas_nz = [(c, dc, v) for c, dc, v in linhas if v > 0]
            cur.execute(
                """
                INSERT INTO erp.lancamento
                    (chave, empresa_id, ano, numero_lancamento, data_lancamento, historico, tag_ref,
                     origem_registro, status_validacao)
                VALUES (%s, %s, 2026, %s, DATE '2026-09-30', %s, %s, 'motor_calculo', 'pendente_revisao')
                RETURNING id
                """,
                (f"lanc:d2:{fc['competencia']}:L{num_l}", emp_id, 900 + num_l, hist, tag),
            )
            lid = int(cur.fetchone()["id"])
            p_rows = []
            for p_ord, (cc_cod, dc, val) in enumerate(linhas_nz, start=1):
                if dc == "D":
                    partidas_total_d += val
                else:
                    partidas_total_c += val
                p_rows.append((f"part:d2:{fc['competencia']}:L{num_l}:{p_ord}", lid, p_ord, cc_map[cc_cod], dc, val))
            execute_values(
                cur,
                "INSERT INTO erp.partida (chave, lancamento_id, ordem, conta_id, dc, valor_centavos) VALUES %s",
                p_rows,
            )

        itens_dicts = [
            {"tipo_rubrica": r[6], "codigo_rubrica": r[4], "valor_centavos": r[9]}
            for r in itens
        ]
        exclusao_simples_extra = impacto_exclusao_simples(itens_dicts, pars) or 0

    validar_coerencia_dossie2(conn, emp_id)
    return {
        "competencia": fc["competencia"],
        "cenario_negocial": cenario_neg,
        "e1": e1,
        "e2": e2,
        "totais": tot,
        "custo_total_centavos": custo_total,
        "partidas_debito_centavos": partidas_total_d,
        "partidas_credito_centavos": partidas_total_c,
        "diferenca_partidas": partidas_total_d - partidas_total_c,
        "exclusao_simples_extra_centavos": exclusao_simples_extra,
        "custo_fora_simples_centavos": custo_total + exclusao_simples_extra,
    }


def validar_coerencia_dossie2(conn: Any, empresa_id: int) -> list[dict[str, Any]]:
    """Detecta inconsistencias reais do Dossie 2 (Rota Sul) e pontos OP-01..08 em auditoria.alerta_coerencia."""
    alertas: list[dict[str, Any]] = []

    def add(regra: str, sev: str, cat: str, mod: str, tit: str, desc: str, rec: str, ancora: str) -> None:
        alertas.append({
            "chave": f"alerta:d2:{regra.lower()}",
            "codigo_regra": regra,
            "severidade": sev,
            "categoria": cat,
            "modulo_alvo": mod,
            "titulo": tit,
            "descricao": desc,
            "recomendacao": rec,
            "resolvido": False,
            "ancora": ancora,
        })

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM erp.enquadramento_historico WHERE empresa_id = %s ORDER BY id DESC LIMIT 1", (empresa_id,))
        enq = cur.fetchone()
        cnaes = [enq["cnae_principal"]] + list(enq["cnaes_secundarios"] or []) if enq else []
        if "4541-2/01" in cnaes or "4511-1/02" in cnaes:
            add(
                "D2_CNAE_VEDACAO_SIMPLES", "critico", "tributario", "cadastro",
                "Risco de exclusão do Simples Nacional: CNAE 4541-2/01 (motos) sob importação",
                "O Anexo I mantém 4541-2/01, 4541-2/03 e 4511-1/02 sob o título Importação/Exportação (LC 123/2006, art. 17, VIII), expondo a empresa à exclusão do Simples Nacional e perda do recolhimento da CPP no DAS (ver PR-02).",
                "Excluir 4541-2/01, 4541-2/03 e 4511-1/02 na 3ª Alteração Contratual (etapa R-01).",
                "/legalizacao",
            )

        cur.execute("SELECT * FROM erp.contrato_trabalho WHERE empresa_id = %s ORDER BY codigo_empregado", (empresa_id,))
        cts = cur.fetchall()
        sem_aso = [c["codigo_empregado"] for c in cts if c["aso_status"] == "pendente_critico"]
        if sem_aso:
            add(
                "D2_ASO_ADMISSIONAL_PENDENTE", "critico", "trabalhista", "dp",
                f"ASO admissional (NR-7) pendente para {', '.join(sem_aso)}",
                "Os empregados iniciaram atividades sem ASO admissional prévio, bloqueando a transmissão de S-2220 no eSocial.",
                "Coletar ASOs imediatamente e registrar status 'Apto' antes de liberar o S-2220.",
                "/dp#contratos-trabalho",
            )

        for c in cts:
            if c["codigo_empregado"] == "E1" and int(c["intervalo_minutos"] or 0) == 108:
                add(
                    "D2_OP_JORNADA_E1_41H", "alerta", "trabalhista", "dp",
                    "Inconsistência aritmética na jornada de E1 (1h48 = 41h semanais vs. 44h)",
                    "O Estudo de Caso 02 descreve 08h–18h com 1h48 de intervalo (seg–sex = 41h reais), faltando 3h frente às 44h declaradas (PEND-04).",
                    "Esclarecer escala complementar com a Rota Sul sem alterar 1h48 arbitrariamente.",
                    f"/dp#contrato-{c['id']}",
                )
        if any(c["vt_optante"] and int(c["vt_passagens_dia"] or 0) == 4 for c in cts):
            add(
                "D2_OP01_VT_4_VS_2", "info", "trabalhista", "folha",
                "OP-01: Vale-Transporte parametrizado em 4 passagens/dia (o caso informa 2 conduções/dia)",
                "EC02, p. 3 e aula de DP, p. 24: 2 conduções/dia (PR-08). A quantidade muda o subsídio da empresa, não o desconto de 6% do empregado.",
                "Confirmar trajeto real no Termo VT assinado (DOC-12).",
                "/dp#contratos-trabalho",
            )

        cur.execute("SELECT * FROM erp.esocial_evento WHERE empresa_id = %s AND status_envio = 'transmitido' AND (numero_recibo IS NULL OR numero_recibo = '')", (empresa_id,))
        if cur.fetchall():
            add(
                "D2_ESOCIAL_SEM_RECIBO", "critico", "trabalhista", "dp",
                "Evento eSocial marcado como transmitido sem número de recibo",
                "Documento físico não se confunde com evento transmitido.",
                "Informar o recibo oficial ou retornar para 'Aguardando insumo'.",
                "/dp#esocial",
            )

        cur.execute("SELECT COUNT(*) AS qtd FROM erp.diligencia_item WHERE empresa_id = %s AND status_item = 'pendente_critico'", (empresa_id,))
        qtd_crit = int(cur.fetchone()["qtd"])
        if qtd_crit > 0:
            add(
                "D2_ONBOARDING_PEND_CRITICAS", "alerta", "governanca", "onboarding",
                f"{qtd_crit} itens de diligência em status pendente crítico (DOC-04/10/11, PEND-01..03)",
                "Certificados e-CNPJ, ASOs, laudos SST, distrato Sócontas e omissão mar–ago/2026 seguem abertos no onboarding.",
                "Acompanhar prazos por ator responsável na Estação 7 (Onboarding).",
                "/onboarding#diligencia",
            )

        cur.execute(
            """
            SELECT modulo, COUNT(*) AS qtd
            FROM auditoria.vw_pendencias_quarentena
            WHERE empresa_id = %s AND status_validacao IN ('pendente_revisao', 'alerta_inconsistencia')
            GROUP BY modulo ORDER BY modulo
            """,
            (empresa_id,),
        )
        pends = cur.fetchall()
        tot_p = sum(int(r["qtd"]) for r in pends)
        if tot_p > 0:
            add(
                "D2_QUARENTENA_REVISAO", "info", "governanca", "sustentacao",
                f"{tot_p} registros do Dossiê 2 aguardando revisão/homologação da contadora",
                "Os itens importados do pacote revisado permanecem em quarentena até validação nas estações 1–9.",
                "Revisar e homologar com justificativa técnica; acompanhar OP-02..OP-08.",
                "/emissao#quarentena",
            )

        cur.execute("SELECT documento, codigo_secao, conteudo_md FROM erp.documento_secao WHERE empresa_id = %s AND dossie = 'D2'", (empresa_id,))
        secoes_d2 = cur.fetchall()
        cur.execute("SELECT codigo_documento, conteudo_md FROM erp.contrato_servico WHERE empresa_id = %s", (empresa_id,))
        cs_d2 = cur.fetchall()
        residuos = detectar_residuos_texto_d2(secoes_d2, cs_d2)
        if residuos:
            lista_res = "; ".join(f"{r['documento']} ({r['padrao']}: {r['trecho']})" for r in residuos[:5])
            add(
                "D2_TEXTO_RESIDUO", "critico", "governanca", "emissao",
                f"Marcas de rascunho ou norma revogada detectadas em {len(residuos)} trecho(s)",
                f"Resíduos encontrados: {lista_res}.",
                "Remover placeholders ([INSERIR, [cite, XX.XXX, TODO, ???) e substituir Res. CFC 1.555/2018 pela Res. CFC 1.708/2023.",
                "/emissao#secoes",
            )

        cur.execute("SELECT * FROM erp.contrato_servico WHERE empresa_id = %s", (empresa_id,))
        divs_cs = detectar_divergencia_contratos_d2(cur.fetchall())
        if divs_cs:
            det = "; ".join(f"{d['rotulo']}: {d['valores']}" for d in divs_cs)
            add(
                "D2_PROPOSTA_CONTRATO_DIVERGENTE", "alerta", "governanca", "onboarding",
                "Divergência comercial/vigência entre Proposta, Contrato e Termo RT",
                f"Diferenças detectadas — {det}.",
                "Alinhar honorário, 13º, valor-hora (proposta × contrato × termo RT) e vigência inicial (contrato × termo RT) na Estação 7.",
                "/onboarding#contratos",
            )

        cur.execute("SELECT * FROM erp.parametro_legal WHERE empresa_id = %s", (empresa_id,))
        pars_d2 = cur.fetchall()
        pisos_err = detectar_salario_abaixo_piso_d2(cts, pars_d2)
        if pisos_err:
            sev = "critico" if any(x["severidade"] == "critico" for x in pisos_err) else "alerta"
            add(
                "D2_SALARIO_ABAIXO_PISO", sev, "trabalhista", "dp",
                "Salário contratual abaixo do piso CCT ou referência CCT ausente",
                " ".join(x["mensagem"] for x in pisos_err),
                "Conferir salário base, piso CCT e referência normativa na Estação 8 (Departamento Pessoal).",
                "/dp#contratos-trabalho",
            )

        cur.execute("SELECT * FROM erp.folha_competencia WHERE empresa_id = %s ORDER BY competencia DESC LIMIT 1", (empresa_id,))
        fc_d2 = cur.fetchone()
        if fc_d2:
            cur.execute(
                """
                SELECT fi.*, ct.codigo_empregado, ct.nome_empregado
                FROM erp.folha_item fi
                JOIN erp.contrato_trabalho ct ON ct.id = fi.contrato_trabalho_id
                WHERE fi.competencia_id = %s
                ORDER BY ct.codigo_empregado, fi.ordem, fi.id
                """,
                (fc_d2["id"],),
            )
            itens_d2 = cur.fetchall()
            ausentes_rec: list[str] = []
            comp_rec = recalcular_folha_independente_dados(
                dict(fc_d2), [dict(c) for c in cts], [dict(p) for p in pars_d2], [dict(i) for i in itens_d2],
                parametros_ausentes=ausentes_rec,
            )
            if ausentes_rec:
                add(
                    "D2_PARAMETRO_AUSENTE", "critico", "trabalhista", "folha",
                    f"Parâmetro(s) ausente(s) no recálculo da folha ({len(ausentes_rec)})",
                    f"Parâmetros/campos faltantes: {', '.join(ausentes_rec)}.",
                    "Cadastrar os parâmetros legais ou dados contratuais ausentes na Estação 8 e recalcular.",
                    "/dp#parametros",
                )
            divs_rec = detectar_recalculo_divergente_d2(comp_rec)
            if divs_rec:
                resumo_div = "; ".join(f"{d['codigo_empregado']}/{d['codigo_rubrica']} (dif {d['diferenca_centavos']/100:.2f})" for d in divs_rec[:5])
                add(
                    "D2_RECALCULO_DIVERGENTE", "critico", "trabalhista", "folha",
                    f"Divergência entre motor da folha e recálculo independente ({len(divs_rec)} rubrica(s))",
                    f"Diferenças encontradas: {resumo_div}.",
                    "Executar 'Recalcular folha e partidas dobradas' na Estação 9 e conferir parâmetros 2026.",
                    "/folha#rubricas",
                )

        cur.execute("DELETE FROM auditoria.alerta_coerencia WHERE empresa_id = %s AND dossie = 'D2'", (empresa_id,))
        if alertas:
            execute_values(
                cur,
                """
                INSERT INTO auditoria.alerta_coerencia
                    (chave, empresa_id, codigo_regra, severidade, categoria, modulo_alvo,
                     titulo, descricao, recomendacao, resolvido, ancora, dossie)
                VALUES %s
                """,
                [
                    (a["chave"], empresa_id, a["codigo_regra"], a["severidade"], a["categoria"],
                     a["modulo_alvo"], a["titulo"], a["descricao"], a["recomendacao"], a["resolvido"], a["ancora"], "D2")
                    for a in alertas
                ],
            )
    return alertas


if __name__ == "__main__":
    with conectar_pg() as c:
        res = recalcular_folha_d2(c)
        c.commit()
    print("Folha D2 recalculada:", res["totais"], "Dif partidas:", res["diferenca_partidas"])
