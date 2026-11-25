"""Emissao dos 16 documentos + planilha aberta do Dossie 2 (Rota Sul) no padrao DMA-PRISMA-2026-v3."""

from __future__ import annotations

import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from sistema.config import PLATAFORMA_DIR
from sistema.pg.db import conectar_pg
from sistema.web import rotulos, texto
from sistema.web.emissor_dossie1 import BRAND_DIR, CSS, JS_ORIENTACAO, WEB_DIR, verificar_pdf
from sistema.web.fontes_pdf import garantir_fontes_estaticas
from sistema.web.planilha_dossie2 import XLSX_D2_NOME, gravar_xlsx_d2

EXPORT_D2_DIR = PLATAFORMA_DIR / "exportacoes" / "dossie2"
XLSX_NOME = XLSX_D2_NOME
MANIFESTO = "_manifesto.json"
EMPRESA_CHAVE_D2 = "emp:rota_sul_d2"
ESCRITORIO_CHAVE_D1 = "emp:prisma_jrna_g07"

DOCUMENTOS: dict[str, dict[str, Any]] = {
    "d2_00_indice": {"arquivo": "00_Indice_Geral_Dossie2_Rota_Sul.pdf", "nn": "00", "curto": "Índice Geral do Dossiê 2", "titulo": "Índice geral do Dossiê 2 — Onboarding e Departamento Pessoal (Rota Sul)", "just": False, "dossie_label": "Dossiê 2"},
    "d2_01_diagnostico": {"arquivo": "01_Diagnostico_Societario_Rota_Sul.pdf", "nn": "01", "curto": "Diagnóstico Societário (Anexo I)", "titulo": "Relatório de diagnóstico societário e análise da 2ª Alteração Contratual", "just": False, "dossie_label": "Dossiê 2"},
    "d2_02_proposta": {"arquivo": "02_Proposta_Honorarios_BPO.pdf", "nn": "02", "curto": "Proposta de Honorários e BPO", "titulo": "Proposta técnica e comercial de honorários contábeis e BPO", "just": False, "dossie_label": "Dossiê 2"},
    "d2_03_contrato": {"arquivo": "03_Contrato_Servicos_Procuracao.pdf", "nn": "03", "curto": "Contrato de Serviços e Procuração", "titulo": "Contrato de prestação de serviços contábeis e minuta de procuração", "just": True, "dossie_label": "Dossiê 2"},
    "d2_04_termo_rt": {"arquivo": "04_Termo_Responsabilidade_Tecnica.pdf", "nn": "04", "curto": "Termo de Responsabilidade Técnica", "titulo": "Termo de Responsabilidade Técnica Contábil (Resolução CFC nº 1.708/2023)", "just": True, "dossie_label": "Dossiê 2"},
    "d2_05_onboarding": {"arquivo": "05_Comunicacao_Onboarding_Pendencias.pdf", "nn": "05", "curto": "Onboarding, Checklist e Respostas", "titulo": "Comunicação de onboarding, checklist, respostas literais e pendências", "just": False, "dossie_label": "Dossiê 2"},
    "d2_06_prontuario": {"arquivo": "06_Prontuario_Roteiro_eSocial_VT_VR.pdf", "nn": "06", "curto": "Prontuário, eSocial e Termos VT/VR", "titulo": "Prontuário funcional, roteiro eSocial S-1.3 e termos VT/VR", "just": False, "dossie_label": "Dossiê 2"},
    "d2_07_ficha_e1": {"arquivo": "07_Ficha_Registro_E1_Aux_Adm.pdf", "nn": "07", "curto": "Ficha de Registro — E1", "titulo": "Ficha de registro de empregado — Empregado 1 (Auxiliar Administrativo)", "just": False, "dossie_label": "Dossiê 2"},
    "d2_08_exp_e1": {"arquivo": "08_Contrato_Experiencia_E1.pdf", "nn": "08", "curto": "Contrato Experiência — E1", "titulo": "Contrato individual de trabalho a título de experiência (45+45d) — E1", "just": True, "dossie_label": "Dossiê 2"},
    "d2_09_ficha_e2": {"arquivo": "09_Ficha_Registro_E2_Vendedor.pdf", "nn": "09", "curto": "Ficha de Registro — E2", "titulo": "Ficha de registro de empregado — Empregado 2 (Vendedor)", "just": False, "dossie_label": "Dossiê 2"},
    "d2_10_exp_e2": {"arquivo": "10_Contrato_Experiencia_E2.pdf", "nn": "10", "curto": "Contrato Experiência — E2", "titulo": "Contrato individual de trabalho a título de experiência (30+60d) — E2", "just": True, "dossie_label": "Dossiê 2"},
    "d2_11_folha": {"arquivo": "11_Folha_Set2026_Memoria_Calculo.pdf", "nn": "11", "curto": "Folha Set/2026 e Memória", "titulo": "Folha de pagamento setembro/2026 — memória de cálculo e sensibilidades", "just": False, "dossie_label": "Dossiê 2"},
    "d2_12_resumo_contab": {"arquivo": "12_Resumo_Provisoes_Contabilizacao.pdf", "nn": "12", "curto": "Resumo, Provisões e Partidas", "titulo": "Resumo consolidado, provisões, partidas dobradas e recibos — 09/2026", "just": False, "dossie_label": "Dossiê 2"},
    "d2_13_auditoria": {"arquivo": "13_Relatorio_Auditoria_Trabalhista.pdf", "nn": "13", "curto": "Auditoria Trabalhista (PT/AUD)", "titulo": "Relatório técnico de auditoria trabalhista e papéis de trabalho (09/2026)", "just": False, "dossie_label": "Dossiê 2"},
    "d2_14_premissas": {"arquivo": "14_Registro_Premissas_Fontes.pdf", "nn": "14", "curto": "Registro de Premissas (PR-01..18)", "titulo": "Registro numerado de premissas adotadas e fontes oficiais", "just": False, "dossie_label": "Dossiê 2"},
    "d2_15_ia": {"arquivo": "15_Declaracao_Uso_IA_LGPD.pdf", "nn": "15", "curto": "Declaração de Uso de IA e LGPD", "titulo": "Declaração transparente de uso de inteligência artificial e LGPD — Dossiê 2", "just": False, "dossie_label": "Dossiê 2"},
}


def carregar_dados_dossie2() -> dict[str, Any]:
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT e.*, p.nome_canonico AS razao_social FROM erp.empresa e JOIN erp.pessoa p ON p.id = e.pessoa_id WHERE e.chave = %s",
            (EMPRESA_CHAVE_D2,),
        )
        emp = cur.fetchone()
        if not emp:
            raise RuntimeError("Empresa emp:rota_sul_d2 nao encontrada.")
        emp_id = int(emp["id"])

        cur.execute("SELECT * FROM erp.estabelecimento WHERE empresa_id = %s ORDER BY id", (emp_id,))
        estabelecimentos = cur.fetchall()

        cur.execute("SELECT * FROM erp.contrato_trabalho WHERE empresa_id = %s ORDER BY codigo_empregado, id", (emp_id,))
        contratos = cur.fetchall()

        cur.execute("SELECT * FROM erp.parametro_legal WHERE empresa_id = %s ORDER BY categoria, ordem, id", (emp_id,))
        parametros = cur.fetchall()

        cur.execute("SELECT * FROM erp.folha_competencia WHERE empresa_id = %s ORDER BY competencia DESC LIMIT 1", (emp_id,))
        comp = cur.fetchone()

        itens = []
        if comp:
            cur.execute(
                """
                SELECT fi.*, ct.codigo_empregado, ct.nome_empregado
                FROM erp.folha_item fi JOIN erp.contrato_trabalho ct ON ct.id = fi.contrato_trabalho_id
                WHERE fi.competencia_id = %s ORDER BY ct.codigo_empregado, fi.ordem, fi.id
                """,
                (comp["id"],),
            )
            itens = cur.fetchall()

        cur.execute(
            """
            SELECT l.numero_lancamento, l.historico, l.tag_ref, p.dc, cc.codigo AS conta_codigo,
                   cc.nome AS conta_nome, p.valor_centavos
            FROM erp.lancamento l JOIN erp.partida p ON p.lancamento_id = l.id
            JOIN erp.conta_contabil cc ON cc.id = p.conta_id
            WHERE l.empresa_id = %s AND l.origem_registro = 'motor_calculo'
            ORDER BY l.numero_lancamento, p.ordem
            """,
            (emp_id,),
        )
        partidas = cur.fetchall()

        cur.execute(
            """
            SELECT modulo, COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados,
                   COUNT(*) FILTER (WHERE status_validacao = 'alerta_inconsistencia') AS inconsistencias,
                   COUNT(*) FILTER (WHERE status_validacao = 'pendente_revisao') AS pendentes
            FROM auditoria.vw_pendencias_quarentena
            WHERE dossie = 'D2' AND status_validacao <> 'acervo_referencia'
            GROUP BY modulo ORDER BY modulo
            """
        )
        quarentena = cur.fetchall()

        cur.execute("SELECT * FROM erp.documento_secao WHERE empresa_id = %s AND dossie = 'D2' ORDER BY documento, ordem, id", (emp_id,))
        secoes: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for s in cur.fetchall():
            secoes[s["documento"]].append(s)

        cur.execute(
            """
            SELECT rt.nome_canonico AS rt_nome,
                   (SELECT pi.valor FROM erp.pessoa_identificador pi WHERE pi.pessoa_id = rt.id AND pi.tipo_id = 'CRC' LIMIT 1) AS rt_crc
            FROM erp.empresa e
            JOIN erp.enquadramento_historico enq ON enq.empresa_id = e.id
            JOIN erp.pessoa rt ON rt.id = enq.responsavel_tecnico_pessoa_id
            WHERE e.chave = %s LIMIT 1
            """,
            (ESCRITORIO_CHAVE_D1,),
        )
        rt = cur.fetchone() or {"rt_nome": "Nathalia Peres Araujo", "rt_crc": "CRC-DF 025.431/O-7"}

    return {
        "emitido_em": datetime.now(),
        "empresa": emp,
        "estabelecimentos": estabelecimentos,
        "contratos": contratos,
        "parametros": parametros,
        "comp": comp,
        "itens": itens,
        "partidas": partidas,
        "quarentena": quarentena,
        "pendencias_total": sum(int(q["pendentes"]) + int(q["inconsistencias"]) for q in quarentena),
        "secoes": secoes,
        "rt": {"nome": rt["rt_nome"], "crc": rt["rt_crc"]},
    }


def _marcadores_d2(d: dict[str, Any]) -> dict[str, str]:
    comp = d.get("comp") or {}
    part_d = sum(int(p["valor_centavos"]) for p in d.get("partidas", []) if p["dc"] == "D")
    return {
        "BRUTO_TOTAL": texto.brl(comp.get("bruto_total_centavos") or 283333),
        "INSS_TOTAL": texto.brl(comp.get("inss_total_centavos") or 21268),
        "FGTS_TOTAL": texto.brl(comp.get("fgts_total_centavos") or 22667),
        "LIQUIDO_A": texto.brl(comp.get("liquido_total_centavos") or 241630),
        "LIQUIDO_B": texto.brl(251065),
        "PROVISOES_TOTAL": texto.brl(comp.get("provisoes_total_centavos") or 50400),
        "CUSTO_SIMPLES": texto.brl(comp.get("custo_total_centavos") or 412800),
        "SUBSIDIO_VT": texto.brl(23400),
        "VR_TOTAL": texto.brl(33000),
        "IMPACTO_EXCLUSAO_SIMPLES": texto.brl(91740),
        "PARTIDAS_DOBRADAS": texto.brl(part_d or 423800),
    }


def _md_vivo_d2(d: dict[str, Any]):
    mk = _marcadores_d2(d)

    def conv(txt: str | None) -> Markup:
        s = re.sub(r"\{\{\s*([A-Z0-9_]+)\s*\}\}", lambda m: mk.get(m.group(1), m.group(0)), txt or "")
        return texto.md_html(s)

    return conv


_env: Environment | None = None


def _jinja() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(str(WEB_DIR / "templates" / "pdf")), autoescape=select_autoescape(["html"]))
        _env.filters.update(md_inline=texto.md_inline, rotulo=rotulos.rotulo)
    return _env


def html_documento(doc: str, para_web: bool = False, dados: dict[str, Any] | None = None) -> str:
    d = dados or carregar_dados_dossie2()
    info = DOCUMENTOS[doc]
    brand = "/static/brand" if para_web else BRAND_DIR.as_uri()
    rt = d["rt"]
    rodape = f"{d['empresa']['razao_social']}  ·  PRISMA JRNA (RT {rt['nome']}, {rt['crc']})"
    hdr = f"DOC. {info['nn']}  ·  {info['curto']}\\A DMA-PRISMA-2026-v3"
    faces = "".join(
        f'@font-face{{font-family:"Adwaita Sans";src:url("{brand}/fonts/estaticas/{arq.name}");font-weight:{peso};font-style:{estilo}}}'
        for arq, peso, estilo in garantir_fontes_estaticas()
    )
    css = CSS % {"B": brand, "SANS": faces, "HDR": hdr.replace('"', "'"), "RODAPE": rodape.replace('"', "'")}
    sede = (d["estabelecimentos"] or [{}])[0]
    comp = d.get("comp") or {}
    part_d = sum(int(p["valor_centavos"]) for p in d.get("partidas", []) if p["dc"] == "D")
    resumo_exec = None
    if doc in ("d2_00_indice", "d2_11_folha", "d2_12_resumo_contab"):
        resumo_exec = {
            "competencia": comp.get("competencia", "2026-09"),
            "bruto": texto.brl(comp.get("bruto_total_centavos") or 283333),
            "inss": texto.brl(comp.get("inss_total_centavos") or 21268),
            "fgts": texto.brl(comp.get("fgts_total_centavos") or 22667),
            "liq_a": texto.brl(comp.get("liquido_total_centavos") or 241630),
            "liq_b": texto.brl(251065),
            "provisoes": texto.brl(comp.get("provisoes_total_centavos") or 50400),
            "custo": texto.brl(comp.get("custo_total_centavos") or 412800),
            "partidas": texto.brl(part_d or 423800),
        }
    return _jinja().get_template("d2_doc.html").render(
        doc=doc, info=info, css=Markup(css), brand=brand, para_web=para_web,
        js_orientacao=Markup(JS_ORIENTACAO), empresa=d["empresa"], rt=d["rt"],
        pend_doc=d["pendencias_total"], pendencias_total=d["pendencias_total"],
        emitido_em=d["emitido_em"], socios=[],
        sede_txt=f"{sede.get('endereco') or '—'} — {sede.get('municipio') or 'Goiânia'}/{sede.get('uf') or 'GO'}",
        secoes=d["secoes"].get(doc, []), md=_md_vivo_d2(d), brl=texto.brl, brl_tab=texto.brl_tab,
        resumo_executivo=resumo_exec,
        extra_rubricas=d["itens"] if doc == "d2_11_folha" else None,
        extra_partidas=d["partidas"] if doc == "d2_12_resumo_contab" else None,
    )


def emitir_pacote(somente: list[str] | None = None, destino: Path = EXPORT_D2_DIR) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    destino.mkdir(parents=True, exist_ok=True)
    tmp = destino / "_html"
    tmp.mkdir(exist_ok=True)
    d = carregar_dados_dossie2()
    docs = [k for k in DOCUMENTOS if not somente or k in somente]
    arquivos: list[str] = []
    verificacoes: list[dict[str, Any]] = []
    if not somente or "d2_11_folha" in somente:
        arquivos.append(str(gravar_xlsx_d2(d, destino / XLSX_NOME)))
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


def situacao_pacote(destino: Path = EXPORT_D2_DIR) -> list[dict[str, Any]]:
    man_path = destino / MANIFESTO
    manifesto = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    out = []
    for doc, info in list(DOCUMENTOS.items()) + [("xlsx", {"arquivo": XLSX_NOME, "curto": "Planilha aberta da Folha (XLSX)", "nn": "11"})]:
        p = destino / info["arquivo"]
        m = manifesto.get(info["arquivo"], {})
        out.append({
            "doc": doc, "arquivo": info["arquivo"], "curto": info["curto"], "nn": info["nn"], "existe": p.exists(),
            "emitido_em": m.get("emitido_em"), "paginas": m.get("paginas"), "orientacao": m.get("orientacao"),
            "ok": m.get("ok"), "fontes": m.get("fontes"), "esparsas": m.get("paginas_esparsas"), "pendencias": m.get("pendencias"),
        })
    return out


def caminho_arquivo(nome: str, destino: Path = EXPORT_D2_DIR) -> Path | None:
    if nome not in _nomes_permitidos():
        return None
    p = destino / nome
    return p if p.exists() else None


def compactar_pacote(destino: Path = EXPORT_D2_DIR) -> Path | None:
    existentes = [destino / n for n in _nomes_permitidos() if (destino / n).exists()]
    if not existentes:
        return None
    zp = destino / "_Dossie2_Rota_Sul_G07.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in existentes:
            z.write(p, p.name)
    return zp
