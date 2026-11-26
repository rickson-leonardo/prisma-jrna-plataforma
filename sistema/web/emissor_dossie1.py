"""Emissao dos documentos oficiais do Dossie 1 em PDF (padrao DMA-PRISMA-2026-v3).

Fluxo: PostgreSQL -> dados_dossie1 -> templates/pdf/*.html (Jinja) -> Playwright + Edge
(channel="msedge") -> PDF -> verificacao editorial com PyMuPDF (fontes Adwaita, paginas esparsas,
pagina 1 sem rodape). Adaptado de G:\\...\\_planejamento\\ferramentas\\render.py e checkpdf.py.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from sistema.config import PLATAFORMA_DIR
from sistema.web import rotulos, texto
from sistema.web.bpmn import gerar_svg_bpmn
from sistema.web.dados_dossie1 import carregar_dados_dossie1, secao
from sistema.web.fontes_pdf import garantir_fontes_estaticas
from sistema.web.planilha_dossie1 import IN, LK, OK, CR, gravar_xlsx, montar_abas

EXPORT_D1_DIR = PLATAFORMA_DIR / "exportacoes" / "dossie1"
WEB_DIR = Path(__file__).resolve().parent
BRAND_DIR = WEB_DIR / "static" / "brand"
XLSX_NOME = "02_Plano_Financeiro_PRISMA_JRNA.xlsx"
MANIFESTO = "_manifesto.json"

DOCUMENTOS: dict[str, dict[str, Any]] = {
    "indice": {"arquivo": "00_Indice_Geral_Dossie1_PRISMA_JRNA.pdf", "nn": "00", "curto": "Índice Geral do Dossiê 1",
               "titulo": "Índice geral do Dossiê 1 — constituição e organização da PRISMA JRNA", "just": False},
    "pesquisa": {"arquivo": "01_Pesquisa_Registro_Profissional_e_Redesim_DF.pdf", "nn": "01", "curto": "Pesquisa Normativa",
                 "titulo": "Pesquisa orientada — registro profissional, organização contábil e Redesim no DF", "just": False},
    "plano_negocios": {"arquivo": "02_Plano_de_Negocios_PRISMA_JRNA.pdf", "nn": "02", "curto": "Plano de Negócios",
                       "titulo": "Plano de negócios — PRISMA JRNA Auditoria e Contabilidade", "just": False},
    "planilha": {"arquivo": "02_Plano_Financeiro_PRISMA_JRNA_Planilha.pdf", "nn": "02", "curto": "Planilha do Plano Financeiro",
                 "titulo": "Planilha do plano financeiro — 36 meses", "just": False},
    "contrato_social": {"arquivo": "03_Contrato_Social_PRISMA_JRNA.pdf", "nn": "03", "curto": "Contrato Social",
                        "titulo": "Contrato social de constituição de sociedade empresária limitada", "just": True},
    "memorando": {"arquivo": "04_Memorando_de_Entendimentos_MOU_PRISMA_JRNA.pdf", "nn": "04", "curto": "Memorando de Entendimentos",
                  "titulo": "Memorando de entendimentos (MoU) — pré-constituição e acordo de sócias", "just": True},
    "fluxo_abertura": {"arquivo": "05_Fluxo_Abertura_Empresa_DF_Redesim_e_BPMN.pdf", "nn": "05", "curto": "Fluxo de Abertura no DF",
                       "titulo": "Fluxo de abertura de empresa no Distrito Federal — Redesim e BPMN", "just": False},
    "ia": {"arquivo": "06_Declaracao_Uso_Inteligencia_Artificial_Dossie1.pdf", "nn": "06", "curto": "Declaração de Uso de IA",
           "titulo": "Declaração de uso de inteligência artificial — Dossiê 1", "just": False},
}

BLOCOS_FLUXO = {
    "A": "Planejamento prévio e enquadramento",
    "B": "Consulta prévia de viabilidade",
    "C": "Coletor nacional (DBE) e integrador estadual",
    "D": "Registro digital e obtenção do NIRE",
    "E": "CNPJ e cadastro fiscal do Distrito Federal",
    "F": "Licenciamento e classificação de risco",
    "G": "Registros profissionais e obrigações iniciais",
    "H": "Representação gráfica (BPMN) e cadeia de evidências",
}

# ----------------------------------------------------------------------------
# CSS DMA v3 (adaptado do render.py validado)
# ----------------------------------------------------------------------------
CSS = r"""
%(SANS)s
@font-face{font-family:"Adwaita Mono";src:url("%(B)s/fonts/AdwaitaMono-Regular.ttf");font-weight:400}
@font-face{font-family:"Adwaita Mono";src:url("%(B)s/fonts/AdwaitaMono-Bold.ttf");font-weight:700}
@font-face{font-family:"Adwaita Mono";src:url("%(B)s/fonts/AdwaitaMono-Italic.ttf");font-weight:400;font-style:italic}
:root{--g900:#111827;--g800:#1F2937;--c700:#374151;--a600:#4B5563;--m500:#6B7280;--l300:#D1D5DB;--l200:#E5E7EB;--n100:#F3F4F6;--n50:#F9FAFB;
 --mono:"Adwaita Mono";--sans:"Adwaita Sans"}
@page{size:A4 portrait;margin:25mm 20mm 20mm 20mm;
 @top-left{content:"PRISMA JRNA  ·  Auditoria e Contabilidade";font:650 7.5pt "Adwaita Sans";color:#1F2937;letter-spacing:.04em;
   background:url("%(B)s/simbolo_prisma_jrna.png") no-repeat left center/auto 7mm;padding-left:9mm;border-bottom:.6pt solid #D1D5DB;vertical-align:middle;margin-top:9mm;margin-bottom:3mm}
 @top-right{content:"%(HDR)s";font:400 7.5pt "Adwaita Sans";color:#6B7280;border-bottom:.6pt solid #D1D5DB;vertical-align:middle;text-align:right;margin-top:9mm;margin-bottom:3mm;white-space:pre}
 @bottom-left{content:"%(RODAPE)s";font:400 7pt "Adwaita Sans";color:#6B7280;border-top:.6pt solid #D1D5DB;vertical-align:top;padding-top:2mm;margin-bottom:9mm}
 @bottom-right{content:"Página " counter(page) " de " counter(pages);font:400 7pt "Adwaita Mono";color:#1F2937;border-top:.6pt solid #D1D5DB;vertical-align:top;padding-top:2mm;text-align:right;margin-bottom:9mm}}
@page land{size:A4 landscape;margin:22mm 18mm 18mm 18mm}
@page :first{margin-top:0;@top-left{content:none;border:0;background:none}@top-right{content:none;border:0}@bottom-left{content:none;border:0}@bottom-right{content:none;border:0}}
*{box-sizing:border-box}
html,body{margin:0;background:#fff}
body{font-family:var(--sans);color:var(--g900);font-size:9.5pt;line-height:1.47;-webkit-print-color-adjust:exact;print-color-adjust:exact;font-variant-numeric:tabular-nums;hyphens:auto}
.wm{position:fixed;left:50%%;top:50%%;width:85mm;transform:translate(-50%%,-50%%);opacity:.04;z-index:-1}
/* capa: pagina 1 inteira em branco opaco (marca d'agua nao aparece na capa) */
.capa{background:#fff;min-height:262mm;break-after:page;display:flex;flex-direction:column}
.capa .band{height:9mm;background:var(--g800);margin:0 -20mm 10mm}
.capa .logo{height:44mm;margin:0 auto 5mm;display:block}
.capa h1{font-size:20pt;line-height:1.2;font-weight:700;margin:0 auto 3mm;letter-spacing:-.01em;max-width:150mm;text-align:center;border:0;padding:0}
.capa .meta{font-size:9pt;color:var(--m500);text-align:center}
.capa .rule{width:16mm;height:1.2pt;background:var(--g800);margin:5mm auto 5mm}
.capa .ficha{margin:0 0 4mm}
.capa .ficha td:first-child{width:48mm;color:var(--c700);font-weight:650}
.capa h2{margin-top:3mm}
.sumario{columns:2;column-gap:10mm;margin:0;padding-left:5mm;font-size:8.3pt;line-height:1.35}
.sumario li{margin-bottom:.4mm}
.capa p,.capa li,.capa td{text-align:left!important;text-indent:0!important}
h1{font-size:14pt;font-weight:700;margin:6mm 0 2.5mm;line-height:1.25;break-after:avoid}
h2{font-size:11pt;font-weight:650;color:var(--g800);margin:6mm 0 2mm;line-height:1.3;break-after:avoid;padding-bottom:1mm;border-bottom:.6pt solid var(--l200)}
h3{font-size:9.5pt;font-weight:650;color:var(--c700);margin:4mm 0 1.5mm;break-after:avoid}
h4{font-size:9pt;font-weight:650;color:var(--c700);margin:3mm 0 1mm;break-after:avoid}
p{margin:0 0 2.2mm;orphans:3;widows:3}
.just p,.just li{text-align:justify;hyphens:auto}
.just .clausula p{text-indent:1.25cm}
.clausula{break-inside:auto;margin-bottom:3mm}
.clausula h3{color:var(--g900)}
ul,ol{margin:0 0 2.5mm;padding-left:6mm} li{margin-bottom:1.1mm}
code,.mono{font-family:var(--mono);font-size:.92em;white-space:nowrap;color:var(--g900);background:none;padding:0;font-style:normal}
strong{font-weight:650}
a{color:inherit;text-decoration:underline;text-decoration-color:var(--l300)}
hr{border:0;border-top:.6pt solid var(--l200);margin:5mm 0}
blockquote,.caixa{margin:3mm 0;padding:2.5mm 3.5mm;border-left:1.6mm solid var(--a600);background:var(--n50);border-radius:0 1mm 1mm 0;font-size:9pt;break-inside:avoid}
blockquote p:last-child,.caixa p:last-child{margin-bottom:0}
.caixa .rot{font-weight:700;display:block;margin-bottom:1mm}
.caixa.at{border-left-color:#92400E;background:#FFFBEB}
.caixa.at .rot{color:#92400E}
.caixa.in{border-left-color:#1E40AF;background:#EFF6FF}
.caixa.in .rot{color:#1E40AF}
table{width:100%%;border-collapse:collapse;font-size:8.5pt;line-height:1.35;margin:2mm 0 1.5mm;break-inside:auto}
thead{display:table-header-group} tr{break-inside:avoid}
th{background:var(--g800);color:#fff;font-weight:650;text-align:left;padding:1.7mm 2mm;font-size:8pt;vertical-align:bottom}
td{padding:1.5mm 2mm;border-bottom:.5pt solid var(--l200);vertical-align:top}
tbody tr:nth-child(even) td{background:var(--n50)}
td.num{font-family:var(--mono);font-size:8.2pt;white-space:nowrap;text-align:right}
th.num{text-align:right}
tr.total td{font-weight:700;border-top:1.2pt solid var(--g800);border-bottom:1.2pt solid var(--g800);background:#fff!important}
.tt{font-size:8.5pt;font-weight:650;margin:4mm 0 0;break-after:avoid;color:var(--g900)}
.fonte{font-size:7.5pt;color:var(--m500);margin:0 0 4mm}
.badge{display:inline-block;font-size:7.2pt;font-weight:700;padding:.3mm 1.6mm;border-radius:.8mm;white-space:nowrap;text-indent:0}
.b-ok{color:#166534;background:#F0FDF4;border:.5pt solid #BBF7D0}.b-at{color:#92400E;background:#FFFBEB;border:.5pt solid #FDE68A}
.b-cr{color:#991B1B;background:#FEF2F2;border:.5pt solid #FECACA}.b-in{color:#1E40AF;background:#EFF6FF;border:.5pt solid #BFDBFE}
.b-neutro{color:#374151;background:#F3F4F6;border:.5pt solid #D1D5DB}
.land{page:land}
.land table{font-size:8pt}
.quebra{break-before:page}
.manter{break-inside:avoid}
.figura{break-before:page;break-inside:avoid;text-align:center}
.figura svg{width:170mm;height:auto;max-height:225mm}
.legenda{font-size:7.5pt;color:var(--m500);margin:1.5mm 0 4mm}
.ass{display:grid;grid-template-columns:1fr 1fr;gap:12mm;margin:14mm 0 6mm;break-inside:avoid}
.ass div{border-top:.8pt solid var(--g900);padding-top:1.5mm;font-size:8.5pt;text-align:center}
.ass strong{display:block}
.xl td,.xl th{border:.4pt solid #E5E7EB;padding:1.1mm 1.6mm;font-size:7.6pt}
.xl tbody tr:nth-child(even) td{background:transparent}
.xl td.in{color:#1D4ED8;background:#EFF6FF!important}
.xl td.lk{color:#15803D}
.xl td.ok{color:#166534;background:#F0FDF4!important;font-weight:700}
.xl td.cr{color:#991B1B;background:#FEF2F2!important;font-weight:700}
.sheet-leg{font-size:7.5pt;color:var(--m500);font-style:italic;margin:0 0 2mm}
.etapa{border:.5pt solid var(--l200);border-radius:1mm;padding:2.5mm 3mm;margin:0 0 3mm;break-inside:avoid}
.etapa h3{margin-top:0}
.etapa dl{display:grid;grid-template-columns:34mm 1fr;gap:.8mm 3mm;margin:0;font-size:8.5pt}
.etapa dt{color:var(--c700);font-weight:650}
.etapa dd{margin:0}
"""

# JS do render.py: tabela larga (soma das larguras minimas) vai para pagina paisagem com seu titulo
JS_ORIENTACAO = r"""
() => {
  const mm = v => v * 96 / 25.4;
  document.querySelectorAll('td.num').forEach(td => { if (td.textContent.trim().length > 22) { td.style.whiteSpace = 'normal'; td.style.fontFamily = 'Adwaita Sans'; td.style.textAlign = 'left'; } });
  const wide = [...document.querySelectorAll('main table:not(.keep)')].filter(t => {
    if (t.closest('.land') || t.closest('.retrato')) return false;
    const cols = t.rows[0] ? t.rows[0].cells.length : 0;
    const w0 = t.style.width; t.style.width = '1px'; const minW = t.offsetWidth; t.style.width = w0;
    const tds = [...t.querySelectorAll('td')];
    const avg = tds.reduce((s, c) => s + c.textContent.trim().length, 0) / Math.max(1, tds.length);
    return minW > mm(170) || cols >= 7 || (cols >= 5 && avg > 45);
  });
  const isHead = e => /^H[1-4]$/.test(e.tagName);
  wide.forEach(t => {
    let lead = [], p = t.previousElementSibling, chars = 0;
    while (p && lead.length < 3 && !['TABLE', 'SECTION'].includes(p.tagName)) {
      chars += p.textContent.length; if (chars > 700) break;
      lead.unshift(p); if (/^H[1-3]$/.test(p.tagName)) break;
      p = p.previousElementSibling;
    }
    const k = lead.findIndex(isHead); lead = k >= 0 ? lead.slice(k) : [];
    const box = document.createElement('section'); box.className = 'land';
    t.parentNode.insertBefore(box, lead[0] || t);
    lead.forEach(e => box.appendChild(e)); box.appendChild(t);
    let nx = box.nextElementSibling;
    while (nx && (nx.classList.contains('fonte') || nx.classList.contains('legenda'))) { const n2 = nx.nextElementSibling; box.appendChild(nx); nx = n2; }
  });
  return document.querySelectorAll('.land').length;
}
"""


# ----------------------------------------------------------------------------
# Contexto e marcadores vivos
# ----------------------------------------------------------------------------
def _marcadores(d: dict[str, Any]) -> dict[str, str]:
    a, ind = d["anos"], d["indicadores"]
    mk: dict[str, str] = {
        "VPL": texto.brl(ind.get("vpl_centavos")),
        "TIR": texto.tir_br(ind.get("tir_pct"), ind.get("vpl_centavos")),
        "CAPITAL_SOCIAL": texto.brl(d["capital_qsa_centavos"]),
        "LTV_CAC": texto.num_br(ind.get("ltv_cac")) + "×",
        "PAYBACK_DESCONTADO": texto.num_br(ind.get("payback_descontado_meses"), 1) + " meses",
    }
    for y in (1, 2, 3):
        if y in a:
            mk[f"RECEITA_A{y}"] = texto.brl(a[y]["receita_bruta_centavos"])
            mk[f"LUCRO_A{y}"] = texto.brl(a[y]["lucro_liquido_centavos"])
    return mk


def _md_vivo(d: dict[str, Any]):
    mk = _marcadores(d)

    def conv(txt: str | None) -> Markup:
        s = re.sub(r"\{\{\s*([A-Z0-9_]+)\s*\}\}", lambda m: mk.get(m.group(1), m.group(0)), txt or "")
        return texto.md_html(s)

    return conv


def _pendentes(itens: list[dict[str, Any]]) -> int:
    return sum(1 for i in itens if i and i.get("status_validacao") not in ("homologado_contadora", "acervo_referencia"))


def _pendencias_documento(doc: str, d: dict[str, Any]) -> int:
    sec = lambda k: d["secoes"].get(k, [])  # noqa: E731
    cad = [d["empresa"], d["enquadramento"]] + list(d["socios"]) + list(d["estabelecimentos"])
    mapa = {
        "indice": d["pendencias_total"],
        "pesquisa": _pendentes(d["consultas"]) + _pendentes(d["decisoes"]) + _pendentes(sec("pesquisa")),
        "plano_negocios": _pendentes([d["cenario"]]) + _pendentes(sec("plano_negocios")),
        "planilha": _pendentes([d["cenario"]]),
        "contrato_social": _pendentes(d["clausulas_contrato"]) + _pendentes(cad) + _pendentes(sec("contrato_social")),
        "memorando": _pendentes(d["clausulas_mou"]) + _pendentes(d["socios"]) + _pendentes(sec("memorando")),
        "fluxo_abertura": _pendentes(d["etapas"]) + _pendentes(sec("fluxo_abertura")),
        "ia": _pendentes(d["diario_ia"]),
    }
    return int(mapa.get(doc, 0))


def _coerencia_cruzada(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Quadro MoU x Contrato x Plano montado do banco (nada digitado)."""
    cs, mou, cen = d["clausulas_contrato"], d["clausulas_mou"], d["cenario"] or {}
    enq = d["enquadramento"] or {}

    def metodos(cl: list[dict[str, Any]]) -> set[str]:
        return {c["metodo_haveres"] for c in cl if c["metodo_haveres"] != "nao_aplicavel"}

    def alcadas(cl: list[dict[str, Any]]) -> set[int]:
        return {int(c["alcada_centavos"]) for c in cl if c["alcada_centavos"]}

    def ref(cl: list[dict[str, Any]], pred) -> str:
        achados = [c["numero_clausula"] for c in cl if pred(c)]
        return ", ".join(achados) if achados else "—"

    def fmt_met(s: set[str]) -> str:
        return " / ".join(rotulos.rotulo(x, "haveres") for x in sorted(s)) or "Não parametrizado"

    def fmt_alc(s: set[int]) -> str:
        return " / ".join(texto.brl(x) for x in sorted(s)) or "Não parametrizada"

    cnaes = [enq.get("cnae_principal")] + list(enq.get("cnaes_secundarios") or [])
    cs_txt = " ".join((c["regra_texto"] or "") for c in cs)
    mou_txt = " ".join((c["regra_texto"] or "") for c in mou)
    linhas = [
        {
            "eixo": "Apuração de haveres",
            "mou": f"{fmt_met(metodos(mou))} ({ref(mou, lambda c: c['metodo_haveres'] != 'nao_aplicavel')})",
            "contrato": f"{fmt_met(metodos(cs))} ({ref(cs, lambda c: c['metodo_haveres'] != 'nao_aplicavel')})",
            "plano": "—",
            "ok": metodos(mou) == metodos(cs) and bool(metodos(cs)),
        },
        {
            "eixo": "Alçada isolada da administradora",
            "mou": fmt_alc(alcadas(mou)), "contrato": fmt_alc(alcadas(cs)), "plano": "—",
            "ok": alcadas(mou) == alcadas(cs) and bool(alcadas(cs)),
        },
        {
            "eixo": "Capital social",
            "mou": "Ver cláusula de capital", "contrato": f"QSA {texto.brl(d['capital_qsa_centavos'])} ({d['quotas_total']:,} quotas)".replace(",", "."),
            "plano": texto.brl(cen.get("capital_social_centavos")),
            "ok": int(cen.get("capital_social_centavos") or -1) == d["capital_qsa_centavos"],
        },
        {
            "eixo": "CNAEs (contabilidade + auditoria)",
            "mou": "6920-6/02 citado" if "6920-6/02" in mou_txt else "6920-6/02 não citado",
            "contrato": "6920-6/02 citado" if "6920-6/02" in cs_txt else "6920-6/02 não citado",
            "plano": ", ".join(c for c in cnaes if c),
            "ok": "6920-6/02" in cnaes and "6920-6/02" in cs_txt,
        },
        {
            "eixo": "Pró-labore M1–M3 / M4–M12",
            "mou": "Ver cláusula de pró-labore", "contrato": "Remissão ao Acordo/MoU",
            "plano": f"{texto.brl(cen.get('prolabore_m1_3_mensal_centavos'))} / {texto.brl(cen.get('prolabore_m4_12_mensal_centavos'))} por mês",
            "ok": None,
        },
    ]
    return linhas


def contexto_documento(doc: str, d: dict[str, Any], para_web: bool = False) -> dict[str, Any]:
    info = DOCUMENTOS[doc]
    brand = "/static/brand" if para_web else BRAND_DIR.as_uri()
    rt = d["rt"]
    rodape = f"{d['empresa']['razao_social']}  ·  RT {rt['nome'] or 'não definida'}, {rt['crc'] or 'CRC não cadastrado'}"
    hdr = f"DOC. {info['nn']}  ·  {info['curto']}\\A DMA-PRISMA-2026-v3"
    # Adwaita Sans em instancias estaticas nomeadas (a variavel vira Type3 sem nome no PDF)
    faces = "".join(
        f'@font-face{{font-family:"Adwaita Sans";src:url("{brand}/fonts/estaticas/{arq.name}");font-weight:{peso};font-style:{estilo}}}'
        for arq, peso, estilo in garantir_fontes_estaticas()
    )
    css = CSS % {"B": brand, "SANS": faces, "HDR": hdr.replace('"', "'"), "RODAPE": rodape.replace('"', "'")}
    sede = d["sede"] or {}
    ctx = dict(d)
    ctx.update(
        doc=doc, info=info, css=Markup(css), brand=brand, documentos=DOCUMENTOS,
        para_web=para_web, js_orientacao=Markup(JS_ORIENTACAO),
        pend_doc=_pendencias_documento(doc, d), doc_pend=lambda k: _pendencias_documento(k, d), md=_md_vivo(d), rot=rotulos.rotulo,
        brl=texto.brl, brl_tab=texto.brl_tab, pct=texto.pct_micro, num=texto.num_br, tir=texto.tir_br,
        sede_txt=f"{sede.get('endereco') or '—'} — {sede.get('municipio') or ''}/{sede.get('uf') or ''}",
        coerencia=_coerencia_cruzada(d), blocos_fluxo=BLOCOS_FLUXO,
        secao=lambda documento, codigo: secao(d, documento, codigo),
    )
    if doc == "fluxo_abertura":
        ctx["bpmn_svg"] = Markup(gerar_svg_bpmn(list(d["etapas"])))
        grupos: dict[str, list[dict[str, Any]]] = {k: [] for k in BLOCOS_FLUXO}
        for e in d["etapas"]:
            grupos.setdefault(str(e["bloco"]).split(",")[0].strip()[:1].upper() or "A", []).append(e)
        ctx["etapas_por_bloco"] = grupos
    if doc in ("planilha", "plano_negocios"):
        ctx["abas"] = montar_abas(d)
        ctx["tipos"] = {"in": IN, "lk": LK, "ok": OK, "cr": CR}
    return ctx


_env: Environment | None = None


def _jinja() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(str(WEB_DIR / "templates" / "pdf")), autoescape=select_autoescape(["html"]))
        _env.filters.update(md_inline=texto.md_inline, rotulo=rotulos.rotulo)
    return _env


def html_documento(doc: str, para_web: bool = False, dados: dict[str, Any] | None = None) -> str:
    d = dados or carregar_dados_dossie1()
    return _jinja().get_template(f"{doc}.html").render(**contexto_documento(doc, d, para_web))


# ----------------------------------------------------------------------------
# Verificacao editorial (checkpdf.py)
# ----------------------------------------------------------------------------
def verificar_pdf(caminho: Path) -> dict[str, Any]:
    import pymupdf

    with pymupdf.open(caminho) as pdf:
        brutas = {(f[2], f[3].split("+")[-1]) for p in pdf for f in p.get_fonts()}
        # Fonte sem nome (ex.: Type3 gerada de fonte variavel) nao pode ser conferida -> reprova
        fontes = sorted({nome or f"[{tipo} sem nome]" for tipo, nome in brutas})
        esparsas = []
        for p in pdf:
            h = p.rect.height
            topo, base = h * 0.09, h * 0.92
            blocos = [b for b in p.get_text("blocks") if b[1] > topo and b[3] < base]
            t = "".join(b[4] for b in blocos)
            desenhos = [d["rect"] for d in p.get_drawings() if d["rect"].y0 > topo and d["rect"].y1 < base]
            fundo = max([b[3] for b in blocos] + [r.y1 for r in desenhos] + [topo])
            ocupacao = (fundo - topo) / (base - topo)
            # DMA v3 §05: nenhuma pagina com menos de 1/4 ocupado (salvo a ultima / fim natural)
            if (len(t.strip()) < 250 or ocupacao < 0.25) and p.number != pdf.page_count - 1:
                esparsas.append(p.number + 1)
        orient = "".join("P" if p.rect.width > p.rect.height else "R" for p in pdf)
        p1 = pdf[0].get_text()
        primeira_sem_rodape = "Página" not in p1
        paginas = pdf.page_count
    so_adwaita = bool(fontes) and all(f.startswith("Adwaita") for f in fontes)
    return {
        "arquivo": caminho.name, "paginas": paginas, "orientacao": orient, "fontes": fontes,
        "so_adwaita": so_adwaita, "paginas_esparsas": esparsas, "primeira_sem_rodape": primeira_sem_rodape,
        "ok": so_adwaita and not esparsas and primeira_sem_rodape,
    }


# ----------------------------------------------------------------------------
# Emissao
# ----------------------------------------------------------------------------
def emitir_pacote(somente: list[str] | None = None, destino: Path = EXPORT_D1_DIR) -> dict[str, Any]:
    """Gera PDFs (+ XLSX) a partir do banco e grava manifesto com a verificacao editorial."""
    from playwright.sync_api import sync_playwright

    destino.mkdir(parents=True, exist_ok=True)
    tmp = destino / "_html"
    tmp.mkdir(exist_ok=True)
    d = carregar_dados_dossie1()
    docs = [k for k in DOCUMENTOS if not somente or k in somente]
    arquivos: list[str] = []
    verificacoes: list[dict[str, Any]] = []
    if not somente or "planilha" in somente or "plano_negocios" in somente:
        if d["cenario"]:
            arquivos.append(str(gravar_xlsx(d, destino / XLSX_NOME)))
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(channel="msedge")
        pagina = navegador.new_page()
        for doc in docs:
            html = html_documento(doc, dados=d)
            hp = tmp / f"{doc}.html"
            hp.write_text(html, encoding="utf-8")
            pagina.goto(hp.as_uri(), wait_until="networkidle")
            pagina.evaluate("document.fonts.ready")
            pagina.evaluate(JS_ORIENTACAO)
            saida = destino / DOCUMENTOS[doc]["arquivo"]
            pagina.pdf(path=str(saida), prefer_css_page_size=True, print_background=True)
            arquivos.append(str(saida))
            verificacoes.append(verificar_pdf(saida))
        navegador.close()

    man_path = destino / MANIFESTO
    manifesto = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    agora = datetime.now().isoformat(timespec="seconds")
    for v in verificacoes:
        manifesto[v["arquivo"]] = dict(v, emitido_em=agora, pendencias=d["pendencias_total"])
    if any(Path(a).name == XLSX_NOME for a in arquivos):
        manifesto[XLSX_NOME] = {"arquivo": XLSX_NOME, "emitido_em": agora, "ok": True, "pendencias": d["pendencias_total"]}
    man_path.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"diretorio": str(destino), "arquivos": arquivos, "verificacoes": verificacoes, "pendencias_quarentena": d["pendencias_total"]}


def _nomes_permitidos() -> list[str]:
    return [v["arquivo"] for v in DOCUMENTOS.values()] + [XLSX_NOME]


def situacao_pacote(destino: Path = EXPORT_D1_DIR) -> list[dict[str, Any]]:
    man_path = destino / MANIFESTO
    manifesto = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    out = []
    for doc, info in list(DOCUMENTOS.items()) + [("xlsx", {"arquivo": XLSX_NOME, "curto": "Planilha editável (XLSX)", "nn": "02"})]:
        p = destino / info["arquivo"]
        m = manifesto.get(info["arquivo"], {})
        out.append({
            "doc": doc, "arquivo": info["arquivo"], "curto": info["curto"], "nn": info["nn"], "existe": p.exists(),
            "emitido_em": m.get("emitido_em"), "paginas": m.get("paginas"), "orientacao": m.get("orientacao"),
            "ok": m.get("ok"), "fontes": m.get("fontes"), "esparsas": m.get("paginas_esparsas"), "pendencias": m.get("pendencias"),
        })
    return out


def caminho_arquivo(nome: str, destino: Path = EXPORT_D1_DIR) -> Path | None:
    if nome not in _nomes_permitidos():
        return None
    p = destino / nome
    return p if p.exists() else None


def compactar_pacote(destino: Path = EXPORT_D1_DIR) -> Path | None:
    existentes = [destino / n for n in _nomes_permitidos() if (destino / n).exists()]
    if not existentes:
        return None
    zp = destino / "_Dossie1_PRISMA_JRNA.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in existentes:
            z.write(p, p.name)
    return zp
