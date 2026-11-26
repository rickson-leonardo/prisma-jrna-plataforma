"""Planilha aberta da Folha de Pagamento Set/2026 (Dossie 2 — Rota Sul) no padrao DMA-PRISMA-2026-v3.

Gera 5 abas (Leia-me + 4 abas de calculo: Parametros, Folha_Set2026, Memoria_Calculo,
Provisoes_e_Integracao) com formulas Excel dinamicas ('=...') referenciando Parametros,
cores padrao DMA (azul=premissa, preto=formula, verde-escuro=conciliacao zerada) e
gravacao em bytes para download direto online (Vercel) ou arquivo local.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from sistema.web.planilha_dossie1 import (
    BRAND_DIR,
    COR_TIPO,
    CR,
    FX,
    G800,
    G900,
    IN,
    L200,
    M500,
    NUM_FMT,
    OK,
    TXT,
    _fonte,
)

XLSX_D2_NOME = "11_Folha_Pagamento_Set2026_Memoria_Calculo.xlsx"


def _r(c: int | None) -> float:
    return round(int(c or 0) / 100.0, 2)


def _p(m: int | None) -> float:
    return int(m or 0) / 1_000_000.0


def _estilizar_cab_aba(ws: Any, titulo: str, subtitulo: str, col_fim: int) -> int:
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = G800
    ws.cell(1, 1, titulo).font = _fonte(size=12, bold=True, color=G900)
    ws.cell(2, 1, subtitulo).font = _fonte(size=8.5, color=M500)
    ws.cell(3, 1, "Legenda: azul = premissa | preto = fórmula dinâmica | verde = conciliação zerada").font = _fonte(
        size=8, color=M500, italic=True
    )
    return 5


def _cell(
    ws: Any,
    row: int,
    col: int,
    val: Any,
    tipo: str = FX,
    fmt: str = "brl",
    bold: bool = False,
) -> Any:
    c = ws.cell(row, col, val)
    cor, fundo = COR_TIPO.get(tipo, COR_TIPO[FX])
    mono = fmt != "txt"
    c.font = _fonte("Adwaita Mono" if mono else "Adwaita Sans", color=cor, bold=bold)
    if fundo:
        c.fill = PatternFill("solid", fgColor=fundo)
    c.number_format = NUM_FMT.get(fmt, NUM_FMT["txt"])
    c.alignment = Alignment(horizontal="right" if mono else "left", vertical="center", wrap_text=not mono)
    c.border = Border(bottom=Side(style="thin", color=L200), top=Side(style="thin", color=L200))
    return c


def _hdr(ws: Any, row: int, cols: list[str], freezes: bool = True) -> None:
    for j, h in enumerate(cols, start=1):
        c = ws.cell(row, j, h)
        c.font = _fonte(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=G800)
        c.alignment = Alignment(horizontal="left" if j <= 2 else "right", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 22
    if freezes:
        ws.freeze_panes = ws.cell(row + 1, 1)
        ws.print_title_rows = f"{row}:{row}"


def _ajustar_impressao(ws: Any, largs: dict[int, int]) -> None:
    for j, w in largs.items():
        ws.column_dimensions[get_column_letter(j)].width = max(w, 12)
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.oddFooter.left.text = "PRISMA JRNA · Rota Sul (Dossiê 2) · &F"
    ws.oddFooter.right.text = "Página &P de &N"


def _montar_workbook_d2(d: dict[str, Any]) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    ws_readme = wb.active
    ws_readme.title = "Leia-me"
    ws_par = wb.create_sheet("Parametros")
    ws_folha = wb.create_sheet("Folha_Set2026")
    ws_mem = wb.create_sheet("Memoria_Calculo")
    ws_prov = wb.create_sheet("Provisoes_e_Integracao")

    fc = d.get("comp") or {}
    cts = {c["codigo_empregado"]: c for c in d.get("contratos", [])}
    e1 = cts.get("E1", {})
    e2 = cts.get("E2", {})
    pars = {p["codigo"]: p for p in d.get("parametros", [])}

    # =========================================================================
    # 1. ABA PARAMETROS (ancora unica para todas as formulas da planilha)
    # =========================================================================
    r = _estilizar_cab_aba(ws_par, "PARÂMETROS OFICIAIS — COMPETÊNCIA 09/2026 (ROTA SUL)", "Portaria MPS/MF 13/2026 · Lei 15.270/2025 · CCT SRT00189/2025 + Aditivo 2026/2027", 5)
    _hdr(ws_par, r, ["Código", "Parâmetro / Premissa", "Valor / Limite", "Alíquota / Extra", "Base Legal / Origem"])
    r += 1
    # Linhas fixas previsiveis (linhas 6..31):
    linhas_par = [
        ("SAL-E1", "Salário contratual mensal — E1 (Mariana)", _r(e1.get("salario_base_centavos", 240000)), None, "brl", None, "Estudo de Caso 02 / Ficha E1"),  # row 6
        ("SAL-E2", "Salário fixo contratual mensal — E2 (Rafael)", _r(e2.get("salario_base_centavos", 190000)), None, "brl", None, "Estudo de Caso 02 / Ficha E2"),  # row 7
        ("DIAS-MES", "Dias padrão do mês comercial (divisor CLT)", int(fc.get("dias_mes_padrao") or 30), None, "int", None, "CLT art. 64"),  # row 8
        ("DIAS-E1", "Dias trabalhados na competência — E1 (16 a 30/09)", int(fc.get("dias_trabalhados_e1") or 15), None, "int", None, "Admissão 16/09/2026"),  # row 9
        ("DIAS-E2", "Dias trabalhados na competência — E2 (21 a 30/09)", int(fc.get("dias_trabalhados_e2") or 10), None, "int", None, "Admissão 21/09/2026"),  # row 10
        ("VENDAS-E2", "Vendas líquidas de E2 em 09/2026 (premissa PR-07)", _r(fc.get("vendas_liquidas_e2_centavos", 6000000)), _p(e2.get("comissao_pct_micro", 15000)), "brl", "pct", "Contrato E2 Cl. 3ª (1,50%)"),  # row 11
        ("DSR-E2", "Dias úteis comissão (9) / Domingos no período (1)", int(fc.get("dias_uteis_comissao_e2") or 9), int(fc.get("domingos_feriados_e2") or 1), "int", "int", "Lei 605/1949; Súmula 27 TST (27/09)"),  # row 12
        ("VT-E1", "VT E1: dias úteis / passagens por dia", int(fc.get("dias_uteis_vt_e1") or 11), int(e1.get("vt_passagens_dia") or 4), "int", "int", "PR-08 (4/dia = 2 ida + 2 volta; sensib. 2/dia)"),  # row 13
        ("VT-E2", "VT E2: dias úteis / passagens por dia", int(fc.get("dias_uteis_vt_e2") or 9), int(e2.get("vt_passagens_dia") or 4), "int", "int", "PR-08 (4/dia = 2 ida + 2 volta; sensib. 2/dia)"),  # row 14
        ("VT-TAR", "Tarifa unitária VT RMTC Goiânia / Pct desconto", _r(e1.get("vt_tarifa_centavos", 430)), 0.06, "brl", "pct", "Lei 7.418/1985 art. 4º"),  # row 15
        ("VT-MISTO", "CCT Cl. 6ª — Teto base salário misto", _r(pars.get("CCT-VT-MISTO", {}).get("limite_centavos", 225750)), None, "brl", None, "CCT SRT00189/2025 Cl. 6ª"),  # row 16
        ("VR-E1", "VR E1: dias úteis / valor diário PAT", int(fc.get("dias_uteis_vr_e1") or 11), _r(e1.get("vr_valor_dia_centavos", 3000)), "int", "brl", "PR-09 (CLT art. 457 § 2º; E2 sem VR)"),  # row 17
        ("INSS-F1", "INSS 2026 Faixa 1 (teto R$ 1.621,00)", _r(pars.get("INSS-F1", {}).get("limite_centavos", 162100)), _p(pars.get("INSS-F1", {}).get("aliquota_micro", 75000)), "brl", "pct", "Portaria MPS/MF nº 13/2026"),  # row 18
        ("INSS-F2", "INSS 2026 Faixa 2 (teto R$ 2.902,84)", _r(pars.get("INSS-F2", {}).get("limite_centavos", 290284)), _p(pars.get("INSS-F2", {}).get("aliquota_micro", 90000)), "brl", "pct", "Portaria MPS/MF nº 13/2026"),  # row 19
        ("INSS-F3", "INSS 2026 Faixa 3 (teto R$ 4.354,27)", _r(pars.get("INSS-F3", {}).get("limite_centavos", 435427)), _p(pars.get("INSS-F3", {}).get("aliquota_micro", 120000)), "brl", "pct", "Portaria MPS/MF nº 13/2026"),  # row 20
        ("INSS-F4", "INSS 2026 Faixa 4 (teto R$ 8.475,55)", _r(pars.get("INSS-F4", {}).get("limite_centavos", 847555)), _p(pars.get("INSS-F4", {}).get("aliquota_micro", 140000)), "brl", "pct", "Portaria MPS/MF nº 13/2026"),  # row 21
        ("SF-2026", "Salário-Família 2026 (teto R$ 1.980,38 / cota)", _r(pars.get("SF-2026", {}).get("limite_centavos", 198038)), _r(pars.get("SF-2026", {}).get("valor_centavos", 6754)), "brl", "brl", "Dec. 3.048/99 art. 82; Port. 13/2026"),  # row 22
        ("SF-DEP", "Dependentes Salário-Família (E1 / E2)", int(e1.get("qtd_dependentes_sf") or 1), int(e2.get("qtd_dependentes_sf") or 0), "int", "int", "E1 possui 1 filho (6 anos)"),  # row 23
        ("IRRF-SIMPL", "IRRF Desconto Simplificado / Isenção Lei 15.270", _r(pars.get("IRRF-SIMPLIF", {}).get("valor_centavos", 60720)), _r(pars.get("RED-ISENTO", {}).get("limite_centavos", 500000)), "brl", "brl", "Lei 14.848/2024 + Lei 15.270/2025"),  # row 24
        ("IRRF-F1", "IRRF Clássico Faixa Isenta / Dependente", _r(pars.get("IRRF-F1", {}).get("limite_centavos", 242880)), _r(pars.get("IRRF-DEP", {}).get("valor_centavos", 18959)), "brl", "brl", "RFB 2026"),  # row 25
        ("FGTS", "FGTS Digital Mensal", 0.0, _p(pars.get("FGTS-8", {}).get("aliquota_micro", 80000)), "brl", "pct", "Lei nº 8.036/1990 (PIX dia 20)"),  # row 26
        ("NEGOCIAL", "Contribuição Negocial CCT (teto / alíquota)", _r(pars.get("CCT-NEGOCIAL", {}).get("limite_centavos", 14800)), _p(pars.get("CCT-NEGOCIAL", {}).get("aliquota_micro", 33300)), "brl", "pct", "CCT Cl. 11ª + STF Tema 935"),  # row 27
        ("CCT-PISOS", "Pisos CCT: Geral / Vendedor", _r(e1.get("piso_cct_centavos", 172225)), _r(e2.get("piso_cct_centavos", 186300)), "brl", "brl", "CCT SECEG × SINDILOJAS-GO Cl. 3ª"),  # row 28
        ("EXCL-SIMP", "Sensibilidade Exclusão Simples (CPP+RAT+Terc)", 0.0, 0.278, "brl", "pct", "PR-17: 20% CPP + 2% RAT + 5,8% FPAS 515"),  # row 29
    ]
    for cod, desc, v1, v2, f1, f2, norm in linhas_par:
        _cell(ws_par, r, 1, cod, TXT, "txt", True)
        _cell(ws_par, r, 2, desc, TXT, "txt")
        _cell(ws_par, r, 3, v1, IN, f1)
        _cell(ws_par, r, 4, "" if v2 is None else v2, IN if v2 is not None else TXT, f2 or "txt")
        _cell(ws_par, r, 5, norm, TXT, "txt")
        r += 1
    _ajustar_impressao(ws_par, {1: 14, 2: 46, 3: 16, 4: 16, 5: 44})

    # =========================================================================
    # 2. ABA FOLHA_SET2026 (100% formulas ligadas a Parametros)
    # =========================================================================
    r = _estilizar_cab_aba(ws_folha, "FOLHA DE PAGAMENTO — COMPETÊNCIA SETEMBRO/2026 (ROTA SUL)", "Regime: Simples Nacional Anexo I (CPP no DAS) · Admissões 16/09 (E1) e 21/09 (E2)", 15)
    cols_f = [
        "Cód.", "Empregado / Cargo", "Sal. Base", "Fixo Prop.", "Comissão", "DSR",
        "Total Bruto", "Sal. Família", "INSS Retido", "IRRF", "Desc. VT (6%)",
        "Negocial (Cen. A)", "Líquido Cen. A", "Líquido Cen. B", "FGTS (8%)",
    ]
    _hdr(ws_folha, r, cols_f)
    # Row 6 = E1, Row 7 = E2, Row 8 = TOTAL
    _cell(ws_folha, 6, 1, "E1", TXT, "txt", True)
    _cell(ws_folha, 6, 2, f"{e1.get('nome_empregado', 'Mariana Alves Costa')} — {e1.get('cargo', 'Auxiliar Administrativo')}", TXT, "txt")
    _cell(ws_folha, 6, 3, "=Parametros!C6", FX, "brl")
    _cell(ws_folha, 6, 4, "=ROUND(C6/Parametros!C8*Parametros!C9,2)", FX, "brl")
    _cell(ws_folha, 6, 5, 0.0, FX, "brl")
    _cell(ws_folha, 6, 6, 0.0, FX, "brl")
    _cell(ws_folha, 6, 7, "=SUM(D6:F6)", FX, "brl", True)
    _cell(ws_folha, 6, 8, "=IF(AND(C6<=Parametros!C22,Parametros!C23>0),Parametros!D22*Parametros!C23,0)", FX, "brl")
    _cell(ws_folha, 6, 9, "=ROUND(MIN(G6,Parametros!C18)*Parametros!D18+MAX(0,MIN(G6,Parametros!C19)-Parametros!C18)*Parametros!D19+MAX(0,MIN(G6,Parametros!C20)-Parametros!C19)*Parametros!D20+MAX(0,MIN(G6,Parametros!C21)-Parametros!C20)*Parametros!D21,2)", FX, "brl")
    _cell(ws_folha, 6, 10, "=IF(G6<=Parametros!D24,0,MAX(0,G6-Parametros!C24-Parametros!C25))", FX, "brl")
    _cell(ws_folha, 6, 11, "=ROUND(D6*Parametros!D15,2)", FX, "brl")
    _cell(ws_folha, 6, 12, "=MIN(ROUND(G6*Parametros!D27,2),Parametros!C27)", FX, "brl")
    _cell(ws_folha, 6, 13, "=G6+H6-I6-J6-K6-L6", FX, "brl", True)
    _cell(ws_folha, 6, 14, "=G6+H6-I6-J6-K6", FX, "brl")
    _cell(ws_folha, 6, 15, "=ROUND(G6*Parametros!D26,2)", FX, "brl")

    _cell(ws_folha, 7, 1, "E2", TXT, "txt", True)
    _cell(ws_folha, 7, 2, f"{e2.get('nome_empregado', 'Rafael Souza Lima')} — {e2.get('cargo', 'Vendedor')}", TXT, "txt")
    _cell(ws_folha, 7, 3, "=Parametros!C7", FX, "brl")
    _cell(ws_folha, 7, 4, "=ROUND(C7/Parametros!C8*Parametros!C10,2)", FX, "brl")
    _cell(ws_folha, 7, 5, "=ROUND(Parametros!C11*Parametros!D11,2)", FX, "brl")
    _cell(ws_folha, 7, 6, "=ROUND(E7/Parametros!C12*Parametros!D12,2)", FX, "brl")
    _cell(ws_folha, 7, 7, "=SUM(D7:F7)", FX, "brl", True)
    _cell(ws_folha, 7, 8, "=IF(AND(C7<=Parametros!C22,Parametros!D23>0),Parametros!D22*Parametros!D23,0)", FX, "brl")
    _cell(ws_folha, 7, 9, "=ROUND(MIN(G7,Parametros!C18)*Parametros!D18+MAX(0,MIN(G7,Parametros!C19)-Parametros!C18)*Parametros!D19+MAX(0,MIN(G7,Parametros!C20)-Parametros!C19)*Parametros!D20+MAX(0,MIN(G7,Parametros!C21)-Parametros!C20)*Parametros!D21,2)", FX, "brl")
    _cell(ws_folha, 7, 10, "=IF(G7<=Parametros!D24,0,MAX(0,G7-Parametros!C24-Parametros!C25))", FX, "brl")
    _cell(ws_folha, 7, 11, "=ROUND(MIN(D7,Parametros!C16/Parametros!C8*Parametros!C10)*Parametros!D15,2)", FX, "brl")
    _cell(ws_folha, 7, 12, "=MIN(ROUND(G7*Parametros!D27,2),Parametros!C27)", FX, "brl")
    _cell(ws_folha, 7, 13, "=G7+H7-I7-J7-K7-L7", FX, "brl", True)
    _cell(ws_folha, 7, 14, "=G7+H7-I7-J7-K7", FX, "brl")
    _cell(ws_folha, 7, 15, "=ROUND(G7*Parametros!D26,2)", FX, "brl")

    _cell(ws_folha, 8, 1, "TOT", TXT, "txt", True)
    _cell(ws_folha, 8, 2, "TOTAL CONSOLIDADO DA FOLHA 09/2026", TXT, "txt", True)
    for col in range(3, 16):
        ltr = get_column_letter(col)
        _cell(ws_folha, 8, col, f"=SUM({ltr}6:{ltr}7)", FX, "brl", True)

    # Quadro de Beneficios VT/VR na aba Folha_Set2026 (rows 11..14)
    _hdr(ws_folha, 10, ["Cód.", "Benefício / Custo Empresa", "VT Bruto (4/dia)", "Desc. VT (6%)", "Subsídio VT (4/dia)", "VR (PAT)", "Sensib. VT (2/dia)", "Obs."], freezes=False)
    _cell(ws_folha, 11, 1, "E1", TXT, "txt", True)
    _cell(ws_folha, 11, 2, "Mariana Alves Costa (11d úteis)", TXT, "txt")
    _cell(ws_folha, 11, 3, "=Parametros!C13*Parametros!D13*Parametros!C15", FX, "brl")
    _cell(ws_folha, 11, 4, "=K6", FX, "brl")
    _cell(ws_folha, 11, 5, "=MAX(0,C11-D11)", FX, "brl")
    _cell(ws_folha, 11, 6, "=Parametros!C17*Parametros!D17", FX, "brl")
    _cell(ws_folha, 11, 7, "=MAX(0,Parametros!C13*2*Parametros!C15-D11)", FX, "brl")
    _cell(ws_folha, 11, 8, "VR 100% empresa; VT 4/dia vs 2/dia", TXT, "txt")

    _cell(ws_folha, 12, 1, "E2", TXT, "txt", True)
    _cell(ws_folha, 12, 2, "Rafael Souza Lima (9d úteis)", TXT, "txt")
    _cell(ws_folha, 12, 3, "=Parametros!C14*Parametros!D14*Parametros!C15", FX, "brl")
    _cell(ws_folha, 12, 4, "=K7", FX, "brl")
    _cell(ws_folha, 12, 5, "=MAX(0,C12-D12)", FX, "brl")
    _cell(ws_folha, 12, 6, 0.0, FX, "brl")
    _cell(ws_folha, 12, 7, "=MAX(0,Parametros!C14*2*Parametros!C15-D12)", FX, "brl")
    _cell(ws_folha, 12, 8, "E2 sem VR em 09/2026 (PR-09)", TXT, "txt")

    _cell(ws_folha, 13, 1, "TOT", TXT, "txt", True)
    _cell(ws_folha, 13, 2, "TOTAL BENEFÍCIOS SETEMBRO/2026", TXT, "txt", True)
    for col in range(3, 8):
        ltr = get_column_letter(col)
        _cell(ws_folha, 13, col, f"=SUM({ltr}11:{ltr}12)", FX, "brl", True)
    _cell(ws_folha, 13, 8, "Líquido dos empregados não muda com 2/dia vs 4/dia", TXT, "txt")
    _ajustar_impressao(ws_folha, {1: 8, 2: 34, 3: 13, 4: 13, 5: 13, 6: 13, 7: 14, 8: 14, 9: 13, 10: 11, 11: 13, 12: 15, 13: 14, 14: 14, 15: 13})

    # =========================================================================
    # 3. ABA MEMORIA_CALCULO (Passo a passo + Sensibilidades)
    # =========================================================================
    r = _estilizar_cab_aba(ws_mem, "MEMÓRIA DE CÁLCULO DETALHADA E SENSIBILIDADES", "Confronto com Pisos CCT, Faixas INSS/IRRF 2026 e Impacto de Exclusão do Simples Nacional", 5)
    _hdr(ws_mem, r, ["Bloco", "Memória Analítica", "Empregado 1", "Empregado 2", "Total / Observação"])
    mem_rows = [
        ("INSS F1", "Parcela tributável na Faixa 1 (7,5%)", "=MIN(Folha_Set2026!G6,Parametros!C18)*Parametros!D18", "=MIN(Folha_Set2026!G7,Parametros!C18)*Parametros!D18", "Portaria MPS/MF 13/2026"),
        ("INSS F2", "Parcela tributável na Faixa 2 (9,0%)", "=MAX(0,MIN(Folha_Set2026!G6,Parametros!C19)-Parametros!C18)*Parametros!D19", "=MAX(0,MIN(Folha_Set2026!G7,Parametros!C19)-Parametros!C18)*Parametros!D19", "E2 excede em R$ 12,33 -> R$ 1,11"),
        ("INSS TOT", "Total INSS Retido (DCTFWeb)", "=ROUND(C6+C7,2)", "=ROUND(D6+D7,2)", "=C8+D8"),
        ("IRRF BASE", "Base ótima IRRF (Bruto − max(INSS+Dep, Simplif.))", "=MAX(0,Folha_Set2026!G6-MAX(Folha_Set2026!I6+Parametros!C23*Parametros!D25,Parametros!C24))", "=MAX(0,Folha_Set2026!G7-Parametros!C24)", "Abaixo de R$ 2.428,80 e R$ 5.000,00"),
        ("CCT PISO", "Margem acima do Piso / Garantia CCT", "=Folha_Set2026!C6-Parametros!C28", "=Folha_Set2026!C7-Parametros!D28", "Ambos acima do mínimo normativo"),
        ("CUSTO SIMP", "Custo Mensal no Simples Nacional (com Provisões E1)", "=Folha_Set2026!G6+Folha_Set2026!O6+Folha_Set2026!E11+Folha_Set2026!F11+Provisoes_e_Integracao!E10", "=Folha_Set2026!G7+Folha_Set2026!O7+Folha_Set2026!E12", "=C11+D11"),
        ("EXCL SIMP", "Adicional Patronal se Excluído do Simples (+27,8%)", "=ROUND((Folha_Set2026!G6+Provisoes_e_Integracao!E9)*Parametros!D29,2)", "=ROUND(Folha_Set2026!G7*Parametros!D29,2)", "=C12+D12"),
        ("CUSTO FORA", "Custo Total Fora do Simples (Lucro Presumido/Real)", "=C11+C12", "=D11+D12", "=C13+D13"),
    ]
    rr = 6
    for blk, desc, fe1, fe2, obs in mem_rows:
        _cell(ws_mem, rr, 1, blk, TXT, "txt", True)
        _cell(ws_mem, rr, 2, desc, TXT, "txt")
        _cell(ws_mem, rr, 3, fe1, FX, "brl", blk in ("INSS TOT", "CUSTO SIMP", "CUSTO FORA"))
        _cell(ws_mem, rr, 4, fe2, FX, "brl", blk in ("INSS TOT", "CUSTO SIMP", "CUSTO FORA"))
        is_f = isinstance(obs, str) and obs.startswith("=")
        _cell(ws_mem, rr, 5, obs, FX if is_f else TXT, "brl" if is_f else "txt", is_f)
        rr += 1
    _ajustar_impressao(ws_mem, {1: 14, 2: 48, 3: 16, 4: 16, 5: 34})

    # =========================================================================
    # 4. ABA PROVISOES_E_INTEGRACAO (Provisoes + L1..L4 + Conciliacao = 0,00)
    # =========================================================================
    r = _estilizar_cab_aba(ws_prov, "PROVISÕES, INTEGRAÇÃO CONTÁBIL (L1–L4) E CONCILIAÇÃO", "Regime de Competência (NBC TG 33) · Segregação DRE (NBC TG 26) · Diferença obrigatória = R$ 0,00", 6)
    _hdr(ws_prov, r, ["Provisão (09/2026)", "Regra (1/12 avo se >= 15d)", "E1 (15d)", "E2 (10d)", "Total", "Observação"])
    # Rows 6..10: 13o (6), Ferias 1/12 (7), 1/3 Ferias (8), Subtotal Brutas (9), Total + FGTS 8% (10)
    _cell(ws_prov, 6, 1, "13º Salário (1/12)", TXT, "txt")
    _cell(ws_prov, 6, 2, "Salário / 12 se >= 15 dias", TXT, "txt")
    _cell(ws_prov, 6, 3, "=IF(Parametros!C9>=15,ROUND(Parametros!C6/12,2),0)", FX, "brl")
    _cell(ws_prov, 6, 4, "=IF(Parametros!C10>=15,ROUND(Parametros!C7/12,2),0)", FX, "brl")
    _cell(ws_prov, 6, 5, "=C6+D6", FX, "brl")
    _cell(ws_prov, 6, 6, "Lei 4.090/1962 art. 1º § 2º", TXT, "txt")

    _cell(ws_prov, 7, 1, "Férias (1/12)", TXT, "txt")
    _cell(ws_prov, 7, 2, "Salário / 12 se >= 15 dias", TXT, "txt")
    _cell(ws_prov, 7, 3, "=IF(Parametros!C9>=15,ROUND(Parametros!C6/12,2),0)", FX, "brl")
    _cell(ws_prov, 7, 4, "=IF(Parametros!C10>=15,ROUND(Parametros!C7/12,2),0)", FX, "brl")
    _cell(ws_prov, 7, 5, "=C7+D7", FX, "brl")
    _cell(ws_prov, 7, 6, "CLT art. 146", TXT, "txt")

    _cell(ws_prov, 8, 1, "1/3 Constitucional s/ Férias", TXT, "txt")
    _cell(ws_prov, 8, 2, "Férias (1/12) / 3 se >= 15 dias", TXT, "txt")
    _cell(ws_prov, 8, 3, "=IF(Parametros!C9>=15,ROUND(C7/3,2),0)", FX, "brl")
    _cell(ws_prov, 8, 4, "=IF(Parametros!C10>=15,ROUND(D7/3,2),0)", FX, "brl")
    _cell(ws_prov, 8, 5, "=C8+D8", FX, "brl")
    _cell(ws_prov, 8, 6, "CF art. 7º XVII", TXT, "txt")

    _cell(ws_prov, 9, 1, "Subtotal Provisões", TXT, "txt", True)
    _cell(ws_prov, 9, 2, "Base para FGTS s/ Provisões", TXT, "txt")
    _cell(ws_prov, 9, 3, "=SUM(C6:C8)", FX, "brl", True)
    _cell(ws_prov, 9, 4, "=SUM(D6:D8)", FX, "brl", True)
    _cell(ws_prov, 9, 5, "=C9+D9", FX, "brl", True)
    _cell(ws_prov, 9, 6, "R$ 466,67 (somente E1)", TXT, "txt")

    _cell(ws_prov, 10, 1, "Total Provisões + FGTS 8%", TXT, "txt", True)
    _cell(ws_prov, 10, 2, "Subtotal + ROUND(8% * Subtotal, 2)", TXT, "txt")
    _cell(ws_prov, 10, 3, "=C9+ROUND(C9*Parametros!D26,2)", FX, "brl", True)
    _cell(ws_prov, 10, 4, "=D9+ROUND(D9*Parametros!D26,2)", FX, "brl", True)
    _cell(ws_prov, 10, 5, "=C10+D10", FX, "brl", True)
    _cell(ws_prov, 10, 6, "R$ 504,00 (466,67 + 37,33 FGTS)", TXT, "txt")

    # Partidas Dobradas L1..L4 (rows 13..33)
    _hdr(ws_prov, 12, ["Lote", "D/C", "Conta Contábil", "Histórico Resumido", "Débito (R$)", "Crédito (R$)"], freezes=False)
    lotes_fx = [
        ("L1", "D", "4.1.1.01", "Desp. Adm. — Salários (E1)", "=Folha_Set2026!D6", 0.0),
        ("L1", "D", "4.2.1.01", "Desp. Com. — Salários (E2)", "=Folha_Set2026!D7", 0.0),
        ("L1", "D", "4.2.1.02", "Desp. Com. — Comissões e DSR (E2)", "=Folha_Set2026!E7+Folha_Set2026!F7", 0.0),
        ("L1", "C", "2.1.2.01", "Salários a Pagar (Cenário A)", 0.0, "=Folha_Set2026!M8"),
        ("L1", "C", "2.1.2.02", "INSS Retido a Recolher (DCTFWeb)", 0.0, "=Folha_Set2026!I8"),
        ("L1", "C", "2.1.2.05", "Contribuição Negocial a Recolher", 0.0, "=Folha_Set2026!L8"),
        ("L1", "C", "4.1.1.05", "Desp. Adm. — VT (recuperação 6% E1)", 0.0, "=Folha_Set2026!K6"),
        ("L1", "C", "4.2.1.05", "Desp. Com. — VT (recuperação 6% E2)", 0.0, "=Folha_Set2026!K7"),
        ("L2", "D", "4.1.1.03", "Desp. Adm. — FGTS 8% (E1)", "=Folha_Set2026!O6", 0.0),
        ("L2", "D", "4.2.1.03", "Desp. Com. — FGTS 8% (E2)", "=Folha_Set2026!O7", 0.0),
        ("L2", "C", "2.1.2.03", "FGTS a Recolher (FGTS Digital)", 0.0, "=Folha_Set2026!O8"),
        ("L3", "D", "4.1.1.05", "Desp. Adm. — Apropriação VT (E1)", "=Folha_Set2026!C11", 0.0),
        ("L3", "D", "4.2.1.05", "Desp. Com. — Apropriação VT (E2)", "=Folha_Set2026!C12", 0.0),
        ("L3", "D", "4.1.1.06", "Desp. Adm. — Vale-Refeição PAT (E1)", "=Folha_Set2026!F11", 0.0),
        ("L3", "C", "1.1.4.01", "Adiantamentos / Fornecedores VT e VR", 0.0, "=Folha_Set2026!C13+Folha_Set2026!F13"),
        ("L4", "D", "4.1.1.07", "Desp. Adm. — Provisão 13º Salário", "=E6", 0.0),
        ("L4", "D", "4.1.1.08", "Desp. Adm. — Provisão Férias + 1/3", "=E7+E8", 0.0),
        ("L4", "D", "4.1.1.09", "Desp. Adm. — FGTS s/ Provisões", "=ROUND(E9*Parametros!D26,2)", 0.0),
        ("L4", "C", "2.1.2.10", "Provisão para 13º Salário", 0.0, "=E6"),
        ("L4", "C", "2.1.2.11", "Provisão para Férias e 1/3", 0.0, "=E7+E8"),
        ("L4", "C", "2.1.2.12", "Provisão de FGTS s/ 13º e Férias", 0.0, "=ROUND(E9*Parametros!D26,2)"),
    ]
    rp = 13
    for lt, dc, cc, hist, deb, cred in lotes_fx:
        _cell(ws_prov, rp, 1, lt, TXT, "txt", True)
        _cell(ws_prov, rp, 2, dc, TXT, "txt", True)
        _cell(ws_prov, rp, 3, cc, TXT, "txt")
        _cell(ws_prov, rp, 4, hist, TXT, "txt")
        _cell(ws_prov, rp, 5, deb, FX, "brl")
        _cell(ws_prov, rp, 6, cred, FX, "brl")
        rp += 1
    _cell(ws_prov, rp, 1, "TOT", TXT, "txt", True)
    _cell(ws_prov, rp, 2, "D=C", TXT, "txt", True)
    _cell(ws_prov, rp, 3, "CHECK", TXT, "txt", True)
    _cell(ws_prov, rp, 4, "VERIFICAÇÃO DE PARTIDAS DOBRADAS (D = C)", TXT, "txt", True)
    _cell(ws_prov, rp, 5, f"=SUM(E13:E{rp-1})", FX, "brl", True)
    _cell(ws_prov, rp, 6, f"=SUM(F13:F{rp-1})", FX, "brl", True)

    # Quadro de Conciliacao (9 linhas = 0,00)
    rc_hdr = rp + 2
    _hdr(ws_prov, rc_hdr, ["#", "Rubrica Conciliada", "Folha (Set/2026)", "Contabilidade (L1–L4)", "Diferença (R$)", "Status"], freezes=False)
    conc_rows = [
        ("1", "Total Proventos Brutos", "=Folha_Set2026!G8", "=E13+E14+E15"),
        ("2", "Líquido a Pagar (Cenário A)", "=Folha_Set2026!M8", "=F16"),
        ("3", "INSS Retido (DCTFWeb)", "=Folha_Set2026!I8", "=F17"),
        ("4", "Contribuição Negocial (CCT)", "=Folha_Set2026!L8", "=F18"),
        ("5", "FGTS da Folha (FGTS Digital)", "=Folha_Set2026!O8", "=F23"),
        ("6", "Desconto VT (6% Empregados)", "=Folha_Set2026!K8", "=F19+F20"),
        ("7", "Subsídio Líquido VT Empresa", "=Folha_Set2026!E13", "=E24+E25-F19-F20"),
        ("8", "Vale-Refeição Empresa (PAT)", "=Folha_Set2026!F13", "=E26"),
        ("9", "Partidas Dobradas (Débitos − Créditos)", f"=E{rp}", f"=F{rp}"),
    ]
    rc = rc_hdr + 1
    for num_c, tit_c, f_fol, f_con in conc_rows:
        _cell(ws_prov, rc, 1, num_c, TXT, "txt", True)
        _cell(ws_prov, rc, 2, tit_c, TXT, "txt")
        _cell(ws_prov, rc, 3, f_fol, FX, "brl")
        _cell(ws_prov, rc, 4, f_con, FX, "brl")
        _cell(ws_prov, rc, 5, f"=ROUND(C{rc}-D{rc},2)", OK, "brl", True)
        _cell(ws_prov, rc, 6, f'=IF(E{rc}=0,"CONCILIADO","DIVERGENTE")', OK, "txt", True)
        rc += 1

    _ajustar_impressao(ws_prov, {1: 22, 2: 36, 3: 16, 4: 38, 5: 15, 6: 22})

    # =========================================================================
    # 5. ABA LEIA-ME (padrao DMA)
    # =========================================================================
    ws_readme.sheet_properties.tabColor = G800
    ws_readme.sheet_view.showGridLines = False
    ws_readme.column_dimensions["A"].width = 3
    ws_readme.column_dimensions["B"].width = 28
    ws_readme.column_dimensions["C"].width = 90
    logo = BRAND_DIR / "logo_prisma_jrna_hd.png"
    if logo.exists():
        img = XLImage(str(logo))
        img.height, img.width = 78, int(78 * 829 / 647)
        ws_readme.add_image(img, "B1")
    linhas_rd = [
        ("t", "LEIA-ME — FOLHA DE PAGAMENTO E MEMÓRIA DE CÁLCULO (DOSSIÊ 2)", ""),
        ("s", "Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. · Competência 09/2026", ""),
        ("", "", ""),
        ("h", "Aba / Item", "Descrição"),
        ("", "Parametros", "Premissas da competência, tabelas oficiais 2026 (Portaria MPS/MF 13/2026, Lei 15.270/2025) e CCT SRT00189/2025."),
        ("", "Folha_Set2026", "Cálculo por fórmulas dinâmicas de E1 e E2 (bruto, INSS 4 faixas, IRRF, VT 4x2, VR, Negocial A/B, FGTS)."),
        ("", "Memoria_Calculo", "Passo a passo de INSS progressivo, IRRF ótimo e sensibilidade de exclusão do Simples (+27,8%)."),
        ("", "Provisoes_e_Integracao", "Provisões 1/12 avo (R$ 504,00), lotes L1–L4 em partidas dobradas (R$ 4.238,00) e 9 linhas de conciliação zeradas."),
        ("", "Governança", f"{d.get('pendencias_total', 0)} registros do Dossiê 2 ainda em quarentena/revisão."),
    ]
    r_rd = 7
    for tp, b, c in linhas_rd:
        cb, cc = ws_readme.cell(r_rd, 2, b), ws_readme.cell(r_rd, 3, c)
        cb.font = _fonte(size=13 if tp == "t" else 9, bold=(tp in ("t", "h")), color="FFFFFF" if tp == "h" else G900)
        cc.font = _fonte(size=9, bold=(tp == "h"), color="FFFFFF" if tp == "h" else M500 if tp == "s" else G900)
        if tp == "h":
            cb.fill = PatternFill("solid", fgColor=G800)
            cc.fill = PatternFill("solid", fgColor=G800)
        r_rd += 1
    ws_readme.page_setup.orientation = "portrait"
    ws_readme.page_setup.fitToWidth = 1
    ws_readme.sheet_properties.pageSetUpPr.fitToPage = True

    return wb


def gravar_xlsx_d2(d: dict[str, Any], caminho: Path) -> Path:
    wb = _montar_workbook_d2(d)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
    return caminho


def gravar_xlsx_bytes_d2(d: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    _montar_workbook_d2(d).save(buf)
    return buf.getvalue()
