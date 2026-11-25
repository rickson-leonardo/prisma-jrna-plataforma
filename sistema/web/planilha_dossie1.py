"""Planilha financeira do Dossie 1 no padrao DMA-PRISMA-2026-v3 (secao 07).

Um unico modelo (abas -> blocos -> linhas de celulas tipadas) alimenta:
- o .xlsx editavel (openpyxl): azul = premissa digitada, preto = calculado pelo motor,
  verde = vinculo com outro modulo; aba Leia-me; cabecalho congelado; impressao paisagem;
- o PDF paisagem 02_Plano_Financeiro_PRISMA_JRNA_Planilha.pdf (via emissor_dossie1).
Todos os valores vem do cenario oficial calculado por motor_contabil.py.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BRAND_DIR = Path(__file__).resolve().parent / "static" / "brand"

# tipo da celula -> papel no papel de trabalho
IN, FX, LK, TXT, OK, CR = "in", "fx", "lk", "txt", "ok", "cr"


@dataclass
class Celula:
    v: Any
    tipo: str = FX       # in | fx | lk | txt | ok | cr
    fmt: str = "brl"     # brl | pct | int | num | txt
    negrito: bool = False


@dataclass
class Bloco:
    titulo: str
    cabecalho: list[str]
    linhas: list[list[Celula]]
    fonte: str = ""
    totais: set[int] = field(default_factory=set)   # indices de linhas de total


@dataclass
class Aba:
    nome: str
    titulo: str
    subtitulo: str
    blocos: list[Bloco]


def _r(c: int | None) -> float:
    return round(int(c or 0) / 100.0, 2)


def _p(m: int | None) -> float:
    return int(m or 0) / 1_000_000.0


def _t(txt: Any, negrito: bool = False) -> Celula:
    return Celula("" if txt is None else str(txt), TXT, "txt", negrito)


def montar_abas(d: dict[str, Any]) -> list[Aba]:
    cen = d["cenario"]
    if not cen:
        return []
    ind = d["indicadores"]
    anos = d["anos"]
    rot = f"Cenário oficial: {cen['nome']} ({cen['codigo_cenario']})"

    # ---------------- Premissas ----------------
    def pin(cod: str, nome: str, val: Any, fmt: str, unid: str, obs: str, tipo: str = IN) -> list[Celula]:
        return [_t(cod), _t(nome), Celula(val, tipo, fmt), _t(unid), _t(obs)]

    prem = [
        pin("PR-01", "Capital social integralizado (cenário)", _r(cen["capital_social_centavos"]), "brl", "R$", "Integralização em M0."),
        pin("PR-02", "Capital social no QSA (Estação 1)", _r(d["capital_qsa_centavos"]), "brl", "R$", "Vínculo: erp.participacao_societaria.", LK),
        pin("PR-03", "Ticket médio mensal por cliente", _r(cen["ticket_medio_centavos"]), "brl", "R$/mês", "Honorário médio."),
        pin("PR-04", "Novos clientes por mês", int(cen["novos_clientes_mes"]), "int", "clientes", "Rampa de 36 meses."),
        pin("PR-05", "Inadimplência / PDD", _p(cen["inadimplencia_micro"]), "pct", "% receita", "Perda esperada."),
        pin("PR-06", "Custo variável operacional", _p(cen["custo_variavel_micro"]), "pct", "% receita", "Sistemas e insumos por cliente."),
        pin("PR-07", "CAC unitário", _r(cen["cac_centavos"]), "brl", "R$", "Aquisição de cliente."),
        pin("PR-08", "Retenção média do cliente", int(cen["retencao_meses"]), "int", "meses", "Base do LTV."),
        pin("PR-09", "Receita no CNAE 6920-6/01 (Anexo III)", _p(cen["pct_cnae_principal_micro"]), "pct", "% receita", "Restante: 6920-6/02 sujeito ao Fator R."),
        pin("PR-10", "Tese tributária", cen["regime_simulacao"], "txt", "—", "Código técnico da tese de apuração."),
        pin("PR-11", "Pró-labore M1–M3", _r(cen["prolabore_m1_3_mensal_centavos"]), "brl", "R$/mês", "Trava de 90 dias."),
        pin("PR-12", "Pró-labore M4–M12", _r(cen["prolabore_m4_12_mensal_centavos"]), "brl", "R$/mês", "Entra no FS12 do Fator R."),
        pin("PR-13", "Pró-labore ano 2", _r(cen["prolabore_ano2_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-14", "Pró-labore ano 3", _r(cen["prolabore_ano3_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-15", "Folha CLT bruta ano 2", _r(cen["folha_clt_ano2_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-16", "Folha CLT bruta ano 3", _r(cen["folha_clt_ano3_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-17", "Encargos e provisões sobre folha CLT", _p(cen["encargos_clt_micro"]), "pct", "% folha", "CPP já incluída no DAS (Anexo III)."),
        pin("PR-18", "OPEX fixo ano 1", _r(cen["opex_fixo_ano1_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-19", "OPEX fixo ano 2", _r(cen["opex_fixo_ano2_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-20", "OPEX fixo ano 3", _r(cen["opex_fixo_ano3_mensal_centavos"]), "brl", "R$/mês", ""),
        pin("PR-21", "CAPEX M0", _r(cen["capex_m0_centavos"]), "brl", "R$", "Imobilizado inicial."),
        pin("PR-22", "CAPEX ano 2", _r(cen["capex_ano2_centavos"]), "brl", "R$", ""),
        pin("PR-23", "CAPEX ano 3", _r(cen["capex_ano3_centavos"]), "brl", "R$", ""),
        pin("PR-24", "Depreciação anual do imobilizado", _p(cen["taxa_depreciacao_anual_micro"]), "pct", "% a.a.", ""),
        pin("PR-25", "TMA (taxa mínima de atratividade)", _p(cen["tma_anual_micro"]), "pct", "% a.a.", "Desconto do VPL e payback."),
        pin("PR-26", "Reserva de lucros", _p(cen["taxa_reserva_lucros_micro"]), "pct", "% lucro", "Restante distribuído."),
    ]
    aba_prem = Aba("Premissas", "Premissas do cenário oficial", rot, [
        Bloco("", ["Código", "Premissa", "Valor", "Unidade", "Observação"], prem, "Fonte: erp.orcamento_cenario · erp.participacao_societaria.")
    ])

    # ---------------- Fluxo mensal ----------------
    lm = []
    for m in d["mensal"]:
        lm.append([
            Celula(int(m["mes_ordem"]), FX, "int"), _t(m["competencia_ym"]), Celula(int(m["clientes_ativos"]), FX, "int"),
            Celula(_r(m["receita_bruta_centavos"])), Celula(_r(m["rbt12_proporcional_centavos"])), Celula(_r(m["fs12_proporcional_centavos"])),
            Celula(_p(m["fator_r_micro"]), FX, "pct"), _t(str(m["anexo_cnae_secundario"]).replace("_", " ")),
            Celula(_p(m["aliquota_efetiva_micro"]), FX, "pct"), Celula(_r(m["das_apurado_centavos"])),
            Celula(_r(m["prolabore_centavos"])), Celula(_r(m["lucro_liquido_centavos"])), Celula(_r(m["saldo_caixa_centavos"]), FX, "brl", True),
        ])
    aba_fluxo = Aba("Projecao_Mensal_M0_M36", "Fluxo de caixa e apuração mensal do Simples (M0–M36)", rot, [
        Bloco("", ["Mês", "Competência", "Clientes", "Receita bruta", "RBT12", "Folha 12m (FS12)", "Fator R", "Anexo 6920-6/02",
                   "Alíq. efetiva", "DAS apurado", "Pró-labore", "Lucro líquido", "Saldo de caixa"], lm,
              "Fonte: erp.orcamento_projecao_mensal (motor_contabil.simular_cenario).")
    ])

    # ---------------- DRE e BP ----------------
    a = [anos[k] for k in (1, 2, 3) if k in anos]

    def lin(rotulo: str, campo: str, sinal: int = 1, negrito: bool = False) -> list[Celula]:
        return [_t(rotulo, negrito)] + [Celula(_r(sinal * int(x[campo] or 0)), FX, "brl", negrito) for x in a]

    dre = [
        [_t("Clientes no fim do ano")] + [Celula(int(x["clientes_fim"]), FX, "int") for x in a],
        lin("Receita bruta", "receita_bruta_centavos", 1, True),
        lin("(−) Simples Nacional (DAS)", "das_centavos", -1),
        lin("(−) Inadimplência / PDD", "inadimplencia_centavos", -1),
        lin("(=) Receita líquida", "receita_liquida_centavos"),
        lin("(−) Custos variáveis", "custos_variaveis_centavos", -1),
        lin("(=) Margem de contribuição", "margem_contribuicao_centavos"),
        lin("(−) Despesas comerciais (CAC)", "cac_centavos", -1),
        lin("(−) Pró-labore das sócias", "prolabore_centavos", -1),
        lin("(−) Folha CLT + encargos", "folha_clt_centavos", -1),
        lin("(−) OPEX fixo", "opex_fixo_centavos", -1),
        lin("(=) EBITDA", "ebitda_centavos"),
        lin("(−) Depreciação", "depreciacao_centavos", -1),
        lin("(=) Lucro líquido", "lucro_liquido_centavos", 1, True),
        [_t("Fator R anual")] + [Celula(_p(x["fator_r_anual_micro"]), FX, "pct") for x in a],
        [_t("Alíquota efetiva média do DAS")] + [Celula(_p(x["aliquota_efetiva_anual_micro"]), FX, "pct") for x in a],
    ]
    b = [anos[k] for k in sorted(anos)]

    def linb(rotulo: str, valores: list[int], negrito: bool = False, tipo: str = FX) -> list[Celula]:
        return [_t(rotulo, negrito)] + [Celula(_r(v), tipo, "brl", negrito) for v in valores]

    bp = [
        linb("Caixa e equivalentes", [x["bp_caixa_centavos"] for x in b]),
        linb("Imobilizado líquido", [int(x["bp_imobilizado_bruto_centavos"]) + int(x["bp_depreciacao_acumulada_centavos"]) for x in b]),
        linb("Ativo total", [x["bp_ativo_total_centavos"] for x in b], True),
        linb("DAS a recolher", [x["bp_das_a_recolher_centavos"] for x in b]),
        linb("Obrigações trabalhistas", [x["bp_obrigacoes_trabalhistas_centavos"] for x in b]),
        linb("Passivo total", [x["bp_passivo_total_centavos"] for x in b]),
        linb("Capital social (vínculo QSA)", [x["bp_capital_social_centavos"] for x in b], tipo=LK),
        linb("Reservas de lucros", [x["bp_reservas_lucros_centavos"] for x in b]),
        linb("Passivo + PL", [int(x["bp_passivo_total_centavos"]) + int(x["bp_pl_total_centavos"]) for x in b], True),
        [_t("Check: Ativo − Passivo − PL", True)] + [Celula("Conforme 0,00" if int(x["bp_diferenca_centavos"]) == 0 else f"Crítico {_r(x['bp_diferenca_centavos'])}",
                                                        OK if int(x["bp_diferenca_centavos"]) == 0 else CR, "txt", True) for x in b],
    ]
    aba_dre = Aba("DRE_e_BP_3_Anos", "DRE e balanço patrimonial projetados (3 anos)", rot, [
        Bloco("DRE projetada", ["Linha (R$)"] + [x["rotulo_periodo"] for x in a], dre, "Fonte: erp.orcamento_demonstrativo_anual.", {13}),
        Bloco("Balanço patrimonial", ["Conta (R$)"] + [x["rotulo_periodo"] for x in b], bp, "Fonte: erp.orcamento_demonstrativo_anual (check exigido = 0 pelo banco).", {2, 8}),
    ])

    # ---------------- Viabilidade ----------------
    def vi(nome: str, val: Any, fmt: str, unid: str, formula: str) -> list[Celula]:
        return [_t(nome), Celula(val, FX, fmt), _t(unid), _t(formula)]

    def ou0(x: Any) -> float:
        return float(x) if x is not None else 0.0

    viab = [
        vi("VPL dos fluxos livres (3 anos)", _r(ind.get("vpl_centavos")), "brl", "R$", "Σ FCt / (1 + TMA)^t; viável se > 0"),
        vi("TIR", ou0(ind.get("tir_pct")) / 100.0, "pct", "% a.a.", "Taxa que zera o VPL; viável se > TMA"),
        vi("Payback simples", ou0(ind.get("payback_simples_meses")), "num", "meses", "Fluxo acumulado ≥ 0"),
        vi("Payback descontado", ou0(ind.get("payback_descontado_meses")), "num", "meses", "Fluxo descontado acumulado ≥ 0"),
        vi("Ponto de equilíbrio — fase 1 (M1–M3)", ou0(ind.get("break_even_fase1_clientes")), "num", "clientes", "Custos fixos ÷ margem de contribuição unitária"),
        vi("Receita de equilíbrio — fase 1", _r(ind.get("break_even_fase1_receita_centavos")), "brl", "R$/mês", "Clientes de equilíbrio × ticket"),
        vi("Ponto de equilíbrio — fase 2 (M4–M12)", ou0(ind.get("break_even_fase2_clientes")), "num", "clientes", "Inclui pró-labore nos custos fixos"),
        vi("Receita de equilíbrio — fase 2", _r(ind.get("break_even_fase2_receita_centavos")), "brl", "R$/mês", "Clientes de equilíbrio × ticket"),
        vi("Margem de contribuição unitária (ano 1)", _r(ind.get("mc_unitaria_ano1_centavos")), "brl", "R$/mês", "Ticket × (1 − DAS% − PDD% − CV%)"),
        vi("LTV pela margem de contribuição", _r(ind.get("ltv_centavos")), "brl", "R$", "MC unitária × retenção"),
        vi("CAC", _r(ind.get("cac_centavos")), "brl", "R$", "Premissa PR-07"),
        vi("LTV / CAC", ou0(ind.get("ltv_cac")), "num", "×", "Saudável acima de 3×"),
        vi("Payback do CAC", ou0(ind.get("payback_cac_meses")), "num", "meses", "CAC ÷ MC unitária"),
        vi("Receita acumulada 3 anos", _r(ind.get("receita_3_anos_centavos")), "brl", "R$", "Σ receita bruta A1–A3"),
        vi("DAS acumulado 3 anos", _r(ind.get("das_3_anos_centavos")), "brl", "R$", "Σ DAS A1–A3"),
        vi("Alíquota média do DAS em 3 anos", ou0(ind.get("das_medio_3_anos_pct")) / 100.0, "pct", "%", "DAS ÷ receita"),
        vi("Mês de transição ME → EPP", int(ind.get("mes_transicao_epp") or 0), "int", "mês", "Receita acumulada > R$ 360 mil (0 = não ocorre)"),
    ]
    aba_viab = Aba("Viabilidade", "Viabilidade, ponto de equilíbrio e unit economics", rot, [
        Bloco("", ["Indicador", "Valor", "Unidade", "Fórmula / critério"], viab, "Fonte: indicadores_json do cenário oficial (motor_contabil.simular_cenario).")
    ])

    # ---------------- Cenários e sensibilidade ----------------
    estr = [[_t(s["nome"]), Celula(_r(s["receita_3_anos_centavos"])), Celula(ou0(s["das_medio_pct"]) / 100.0, FX, "pct"),
             Celula(_r(s["lucro_3_anos_centavos"])), Celula(_r(s["vpl_centavos"])), Celula(ou0(s["tir_pct"]) / 100.0, FX, "pct")]
            for s in ind.get("cenarios_estrategicos", [])]
    sens = ind.get("matriz_sensibilidade", {})
    cab_s = ["Ticket \\ Inadimplência"] + [f"{x:.1f}%".replace(".", ",") for x in sens.get("inadimplencias_pct", [])]
    lin_s = [[Celula(_r(ln["ticket_centavos"]), IN, "brl", True)] + [Celula(_r(v)) for v in ln["valores_vpl_centavos"]] for ln in sens.get("linhas", [])]
    teses = [[_t(c["nome"]), _t(c["regime_simulacao"]), Celula(_r(c["a1_das"])), Celula(_p(c["a1_fator_r"]), FX, "pct"),
              Celula(_r(c["a1_lucro"])), Celula(_r((c["indicadores_json"] or {}).get("vpl_centavos"))), _t(c["status_validacao"])]
             for c in d["cenarios"]]
    aba_cen = Aba("Cenarios_Sensibilidade", "Cenários estratégicos e sensibilidade do VPL", rot, [
        Bloco("Cenários estratégicos (3 anos)", ["Cenário", "Receita 3 anos", "DAS médio", "Lucro 3 anos", "VPL", "TIR"], estr,
              "Fonte: motor_contabil — variação de clientes e inadimplência sobre o cenário oficial."),
        Bloco("Matriz 5×5 de sensibilidade do VPL (R$)", cab_s, lin_s, "Linhas: ticket médio (R$); colunas: inadimplência."),
        Bloco("Teses tributárias cadastradas (comparativo)", ["Cenário", "Tese (código)", "DAS ano 1", "Fator R A1", "Lucro A1", "VPL", "Situação (código)"], teses,
              "Fonte: erp.orcamento_cenario."),
    ])
    return [aba_prem, aba_fluxo, aba_dre, aba_viab, aba_cen]


# =============================================================================
# XLSX
# =============================================================================
G800, G900, M500, L200 = "1F2937", "111827", "6B7280", "E5E7EB"
COR_TIPO = {IN: ("1D4ED8", "EFF6FF"), FX: (G900, None), LK: ("15803D", None), TXT: (G900, None), OK: ("166534", "F0FDF4"), CR: ("991B1B", "FEF2F2")}
NUM_FMT = {"brl": '#,##0.00;(#,##0.00);"–"', "pct": "0.0%", "int": "#,##0", "num": "#,##0.00", "txt": "@"}


def _fonte(nome: str = "Adwaita Sans", **kw: Any) -> Font:
    return Font(name=nome, size=kw.pop("size", 9), **kw)


def _montar_workbook(d: dict[str, Any]) -> openpyxl.Workbook:
    abas = montar_abas(d)
    wb = openpyxl.Workbook()
    leia = wb.active
    leia.title = "Leia-me"
    _leia_me(leia, d, abas)
    linha_fina = Border(bottom=Side(style="thin", color=L200))
    for aba in abas:
        ws = wb.create_sheet(aba.nome)
        ws.sheet_properties.tabColor = G800
        ws.sheet_view.showGridLines = False
        ws["A1"] = aba.titulo
        ws["A1"].font = _fonte(size=13, bold=True, color=G900)
        ws["A2"] = aba.subtitulo
        ws["A2"].font = _fonte(size=8.5, color=M500)
        ws["A3"] = "Valores em R$ · azul = premissa digitada · preto = calculado pelo motor · verde = vínculo com outro módulo · ( ) = negativo · – = zero"
        ws["A3"].font = _fonte(size=8, italic=True, color=M500)
        r = 4
        larg: dict[int, int] = {}
        for bl in aba.blocos:
            if bl.titulo:
                ws.cell(r, 1, bl.titulo).font = _fonte(size=10, bold=True, color=G800)
                r += 1
            for j, h in enumerate(bl.cabecalho, start=1):
                c = ws.cell(r, j, h)
                c.font = _fonte(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor=G800)
                c.alignment = Alignment(horizontal="left" if j == 1 else "right", vertical="center", wrap_text=True)
                larg[j] = max(larg.get(j, 8), min(len(str(h)) + 2, 40))
            ws.row_dimensions[r].height = 22
            if aba.blocos.index(bl) == 0:
                ws.freeze_panes = ws.cell(r + 1, 1)
                ws.print_title_rows = f"{r}:{r}"
            r += 1
            for i, ln in enumerate(bl.linhas):
                for j, cel in enumerate(ln, start=1):
                    v = cel.v
                    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
                        v = "'" + v  # texto do banco nunca vira formula
                    c = ws.cell(r, j, v)
                    cor, fundo = COR_TIPO[cel.tipo]
                    mono = cel.fmt != "txt"
                    c.font = _fonte("Adwaita Mono" if mono else "Adwaita Sans", color=cor, bold=cel.negrito or i in bl.totais)
                    if fundo:
                        c.fill = PatternFill("solid", fgColor=fundo)
                    c.number_format = NUM_FMT[cel.fmt]
                    c.alignment = Alignment(horizontal="right" if mono else "left", vertical="top", wrap_text=not mono)
                    c.border = linha_fina
                    larg[j] = max(larg.get(j, 8), min(len(str(cel.v)) + 3, 60))
                r += 1
            if bl.fonte:
                ws.cell(r, 1, bl.fonte).font = _fonte(size=7.5, color=M500, italic=True)
                r += 1
            r += 1
        for j, w in larg.items():
            ws.column_dimensions[get_column_letter(j)].width = max(w, 11)
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.oddFooter.left.text = "PRISMA JRNA · &F"
        ws.oddFooter.right.text = "Página &P de &N"
    return wb


def gravar_xlsx(d: dict[str, Any], caminho: Path) -> Path:
    wb = _montar_workbook(d)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
    return caminho


def gravar_xlsx_bytes(d: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    _montar_workbook(d).save(buf)
    return buf.getvalue()


def _leia_me(ws: Any, d: dict[str, Any], abas: list[Aba]) -> None:
    ws.sheet_properties.tabColor = G800
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 95
    logo = BRAND_DIR / "logo_prisma_jrna_hd.png"
    if logo.exists():
        img = XLImage(str(logo))
        img.height, img.width = 78, int(78 * 829 / 647)
        ws.add_image(img, "B1")
    cen = d["cenario"]
    rt = d["rt"]
    linhas = [
        ("t", "LEIA-ME — PLANO FINANCEIRO DO DOSSIÊ 1", ""),
        ("s", f"{d['empresa']['razao_social']} · padrão DMA-PRISMA-2026-v3", ""),
        ("", "", ""),
        ("h", "Item", "Descrição"),
        ("", "Objetivo", "Projeção de 36 meses com Simples Nacional progressivo e Fator R, DRE, balanço fechado, viabilidade (VPL/TIR/payback), unit economics e sensibilidade."),
        ("", "Cenário", f"{cen['nome']} — código {cen['codigo_cenario']} — situação: {cen['status_validacao']}." if cen else "Nenhum cenário oficial definido."),
        ("", "Origem dos números", "Calculados pelo motor contábil (sistema/erp/motor_contabil.py) e gravados no PostgreSQL. Nenhum número é digitado nesta planilha exceto as premissas (azul)."),
    ]
    linhas += [("", f"Aba {a.nome}", a.titulo) for a in abas]
    linhas += [
        ("", "Governança", f"{d['pendencias_total']} registros do Dossiê 1 ainda não homologados pela contadora na data da emissão." if d["pendencias_total"] else "Todos os registros do Dossiê 1 homologados pela contadora."),
        ("", "", ""),
        ("h", "Legenda de células", "Significado"),
        ("in", "1.234,56", "Premissa digitada — azul sobre fundo azul-claro"),
        ("fx", "1.234,56", "Calculado pelo motor contábil — preto"),
        ("lk", "1.234,56", "Vínculo com outro módulo (ex.: capital do QSA) — verde"),
        ("ok", "Conforme 0,00", "Checagem conforme — verde-escuro"),
        ("", "(1.234,56)  /  –", "Negativo entre parênteses / zero exibido como traço"),
        ("", "", ""),
        ("", "Última emissão", f"{d['emitido_em']:%d/%m/%Y %H:%M} — RT {rt['nome'] or '—'} ({rt['crc'] or 'CRC não cadastrado'})"),
    ]
    r = 7
    for tipo, b, c in linhas:
        cb, cc = ws.cell(r, 2, b), ws.cell(r, 3, c)
        for z in (cb, cc):
            z.font = _fonte(color=G900)
            z.alignment = Alignment(wrap_text=True, vertical="top")
        if tipo == "t":
            cb.font = _fonte(size=13, bold=True, color=G900)
            cb.alignment = Alignment(wrap_text=False)
        elif tipo == "s":
            cb.font = _fonte(size=8.5, color=M500)
            cb.alignment = Alignment(wrap_text=False)
        elif tipo == "h":
            for z in (cb, cc):
                z.font = _fonte(bold=True, color="FFFFFF")
                z.fill = PatternFill("solid", fgColor=G800)
        elif tipo in COR_TIPO:
            cor, fundo = COR_TIPO[tipo]
            cb.font = _fonte("Adwaita Mono", color=cor, bold=tipo == OK)
            if fundo:
                cb.fill = PatternFill("solid", fgColor=fundo)
            cb.alignment = Alignment(horizontal="right")
        r += 1
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
