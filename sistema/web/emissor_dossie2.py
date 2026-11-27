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
from sistema.erp.motor_folha import impacto_exclusao_simples, recalcular_folha_independente_dados
from sistema.pg.db import conectar_pg
from sistema.web import rotulos, texto
from sistema.web.emissor_dossie1 import BRAND_DIR, CSS, JS_ORIENTACAO, WEB_DIR, verificar_pdf
from sistema.web.fontes_pdf import garantir_fontes_estaticas
from sistema.web.planilha_dossie2 import XLSX_D2_NOME, gravar_xlsx_d2
from sistema.web.repo_d2 import obter_dados_escritorio_d1

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
            SELECT * FROM erp.requisito
            WHERE dossie_id = (SELECT id FROM erp.dossie WHERE codigo = 'D2')
              AND documentos_json IS NOT NULL
            ORDER BY ordem, id
            """
        )
        requisitos = cur.fetchall()

        cur.execute("SELECT * FROM erp.diligencia_item WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
        diligencias = cur.fetchall()

        cur.execute(
            """
            SELECT ev.*, ct.codigo_empregado, ct.nome_empregado
            FROM erp.esocial_evento ev
            LEFT JOIN erp.contrato_trabalho ct ON ct.id = ev.contrato_trabalho_id
            WHERE ev.empresa_id = %s
            ORDER BY ev.ordem, ev.id
            """,
            (emp_id,),
        )
        esocial = cur.fetchall()

        cur.execute("SELECT * FROM erp.consulta_normativa WHERE empresa_id = %s AND dossie = 'D2' ORDER BY numero_questao, id", (emp_id,))
        consultas = cur.fetchall()

        cur.execute("SELECT * FROM auditoria.diario_ia WHERE empresa_id = %s AND dossie = 'D2' ORDER BY id", (emp_id,))
        diario_ia = cur.fetchall()

        escritorio = obter_dados_escritorio_d1(cur)

        cur.execute(
            """
            SELECT ps.*, p.nome_canonico, p.id AS pessoa_id
            FROM erp.participacao_societaria ps
            JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id
            WHERE ps.empresa_id = %s AND ps.vigente_ate IS NULL
            ORDER BY ps.id
            """,
            (emp_id,),
        )
        socios = cur.fetchall()

        pessoa_ids = [int(emp["pessoa_id"])] + [int(s["pessoa_id"]) for s in socios]
        cur.execute(
            """
            SELECT pi.*, p.nome_canonico
            FROM erp.pessoa_identificador pi
            JOIN erp.pessoa p ON p.id = pi.pessoa_id
            WHERE pi.pessoa_id = ANY(%s)
            ORDER BY pi.pessoa_id, pi.tipo_id, pi.id
            """,
            (pessoa_ids,),
        )
        identificadores = cur.fetchall()

        cur.execute(
            "SELECT * FROM erp.enquadramento_historico WHERE empresa_id = %s ORDER BY vigente_de DESC, id DESC LIMIT 1",
            (emp_id,),
        )
        enquadramento = cur.fetchone()

        cur.execute(
            "SELECT * FROM erp.fato WHERE sujeito_chave = %s AND atributo IN ('capital_social', 'capital_integralizado') ORDER BY vigente_de, id",
            (EMPRESA_CHAVE_D2,),
        )
        fatos_capital = cur.fetchall()

        cur.execute("SELECT * FROM erp.instrumento_societario_clausula WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
        clausulas_d2 = cur.fetchall()

        cur.execute("SELECT * FROM erp.contrato_servico WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
        contratos_servico = cur.fetchall()

        cur.execute("SELECT * FROM erp.auditoria_folha WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
        auditoria = cur.fetchall()

        rt_nome = (escritorio or {}).get("rt_nome") or "—"
        rt_crc = (escritorio or {}).get("rt_crc") or "—"

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
        "requisitos": requisitos,
        "diligencias": diligencias,
        "esocial": esocial,
        "consultas": consultas,
        "diario_ia": diario_ia,
        "escritorio": escritorio,
        "socios": socios,
        "identificadores": identificadores,
        "enquadramento": enquadramento,
        "fatos_capital": fatos_capital,
        "clausulas_d2": clausulas_d2,
        "contratos_servico": contratos_servico,
        "auditoria": auditoria,
        "rt": {"nome": rt_nome, "crc": rt_crc},
    }


def _fmt_brl_ou_traco(centavos: int | None) -> str:
    return "—" if centavos is None else texto.brl(centavos)


def _soma_rubrica(itens: list[dict[str, Any]], codigo: str) -> int | None:
    vals = [int(it["valor_centavos"]) for it in itens if it.get("codigo_rubrica") == codigo and it.get("valor_centavos") is not None]
    return sum(vals) if vals else None


def _calcular_liquido_b(comp: dict[str, Any], itens: list[dict[str, Any]]) -> int | None:
    liq_a = comp.get("liquido_total_centavos")
    if liq_a is None:
        return None
    if comp.get("cenario_negocial") == "B_patronal":
        return int(liq_a)
    neg = _soma_rubrica(itens, "NEGOCIAL")
    if neg is None:
        return None
    return int(liq_a) + neg


def _marcadores_honorarios(contratos_servico: list[dict[str, Any]]) -> dict[str, str]:
    """Marcadores dos honorários (Docs 02–04) a partir do contrato (ou da proposta): nenhum valor digitado no texto.

    VALOR_<COD> = horas da frente `codigo` em memoria_horas_json × valor_hora_centavos do registro.
    """
    por_doc = {str(c.get("codigo_documento")): c for c in (contratos_servico or [])}
    cs = por_doc.get("contrato") or por_doc.get("proposta")
    if not cs:
        return {}
    vh = cs.get("valor_hora_centavos")
    mk = {
        "VALOR_HORA": _fmt_brl_ou_traco(vh),
        "HORAS_MES": "—" if cs.get("horas_mes_estimadas") is None else str(cs["horas_mes_estimadas"]),
        "HONORARIO_MENSAL": _fmt_brl_ou_traco(cs.get("honorario_mensal_centavos")),
        "DECIMO_TERCEIRO": _fmt_brl_ou_traco(cs.get("honorario_mensal_centavos") if cs.get("tem_decimo_terceiro") else None),
    }
    # memória de horas: do contrato se houver; senão da proposta (a regra D2_PROPOSTA_CONTRATO_DIVERGENTE garante o mesmo valor-hora)
    mem = next((c for c in (por_doc.get("contrato"), por_doc.get("proposta")) if c and c.get("memoria_horas_json")), None)
    vh_mem = (mem or {}).get("valor_hora_centavos")
    for item in (mem or {}).get("memoria_horas_json") or []:
        if isinstance(item, dict) and item.get("codigo") and item.get("horas") is not None:
            cod, horas = str(item["codigo"]).upper(), int(item["horas"])
            mk[f"HORAS_{cod}"] = str(horas)
            mk[f"VALOR_{cod}"] = _fmt_brl_ou_traco(horas * int(vh_mem) if vh_mem is not None else None)
    return mk


def _marcadores_d2(d: dict[str, Any]) -> dict[str, str]:
    comp = d.get("comp") or {}
    itens = d.get("itens") or []
    partidas = d.get("partidas") or []
    part_d = sum(int(p["valor_centavos"]) for p in partidas if p.get("dc") == "D") if partidas else None
    liq_b = _calcular_liquido_b(comp, itens)
    vt_subs = _soma_rubrica(itens, "VT-SUBS")
    vr_tot = _soma_rubrica(itens, "VR-PAT")
    imp_excl = impacto_exclusao_simples(itens, d.get("parametros") or [])
    return {
        "BRUTO_TOTAL": _fmt_brl_ou_traco(comp.get("bruto_total_centavos")),
        "INSS_TOTAL": _fmt_brl_ou_traco(comp.get("inss_total_centavos")),
        "FGTS_TOTAL": _fmt_brl_ou_traco(comp.get("fgts_total_centavos")),
        "LIQUIDO_A": _fmt_brl_ou_traco(comp.get("liquido_total_centavos")),
        "LIQUIDO_B": _fmt_brl_ou_traco(liq_b),
        "PROVISOES_TOTAL": _fmt_brl_ou_traco(comp.get("provisoes_total_centavos")),
        "CUSTO_SIMPLES": _fmt_brl_ou_traco(comp.get("custo_total_centavos")),
        "SUBSIDIO_VT": _fmt_brl_ou_traco(vt_subs),
        "VR_TOTAL": _fmt_brl_ou_traco(vr_tot),
        "IMPACTO_EXCLUSAO_SIMPLES": _fmt_brl_ou_traco(imp_excl),
        "PARTIDAS_DOBRADAS": _fmt_brl_ou_traco(part_d),
        **_marcadores_honorarios(d.get("contratos_servico") or []),
    }


def _md_vivo_d2(d: dict[str, Any]):
    mk = _marcadores_d2(d)

    def conv(txt: str | None) -> Markup:
        s = re.sub(r"\{\{\s*([A-Z0-9_]+)\s*\}\}", lambda m: mk.get(m.group(1), m.group(0)), txt or "")
        return texto.md_html(s)

    return conv


_env: Environment | None = None


def _fmt_hhmm(minutos: int | None) -> str:
    if minutos is None:
        return "—"
    m = int(minutos)
    return f"{m // 60}h{m % 60:02d}"


def _fmt_data(val: Any) -> str:
    if not val:
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s[:10])
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else s


def _normalizar_docs_admissao(ct: dict[str, Any]) -> list[dict[str, str]]:
    pecas: list[dict[str, str]] = []
    tem_aso = False
    for raw in ct.get("docs_admissionais_json") or []:
        if isinstance(raw, dict):
            nome = str(raw.get("documento") or raw.get("nome") or raw.get("peca") or "Documento")
            if "aso" in nome.lower():
                tem_aso = True
                continue
            st_raw = str(raw.get("status") or "").strip()
            if st_raw:
                st = st_raw
                obs = str(raw.get("observacao") or "—")
            else:
                st = "Não informado"
                obs = str(raw.get("observacao") or "Status não registrado no banco")
            pecas.append({"peca": nome, "status": st, "observacao": obs})
        else:
            nome = str(raw)
            if "aso" in nome.lower():
                tem_aso = True
                continue
            pecas.append({"peca": nome, "status": "Não informado", "observacao": "Status não registrado no banco"})
    aso_st = str(ct.get("aso_status") or "pendente_critico")
    pecas.append({
        "peca": "ASO Admissional (NR-7 / eSocial S-2220)",
        "status": rotulos.rotulo(aso_st, "aso_status"),
        "observacao": str(ct.get("aso_observacao") or "—") if (tem_aso or aso_st != "apto" or ct.get("aso_observacao")) else "—",
    })
    return pecas


def _registros_por_doc(doc: str, d: dict[str, Any]) -> list[dict[str, Any]]:
    regs: list[dict[str, Any]] = list(d.get("secoes", {}).get(doc, []))
    if doc == "d2_01_diagnostico":
        regs.extend(d.get("clausulas_d2") or [])
    elif doc == "d2_02_proposta":
        regs.extend(c for c in (d.get("contratos_servico") or []) if c.get("codigo_documento") == "proposta")
    elif doc == "d2_03_contrato":
        regs.extend(c for c in (d.get("contratos_servico") or []) if c.get("codigo_documento") in ("contrato", "procuracao"))
    elif doc == "d2_04_termo_rt":
        regs.extend(c for c in (d.get("contratos_servico") or []) if c.get("codigo_documento") == "termo_rt")
    elif doc == "d2_05_onboarding":
        regs.extend(d.get("diligencias") or [])
    elif doc == "d2_06_prontuario":
        regs.extend(d.get("contratos") or [])
        regs.extend(d.get("esocial") or [])
    elif doc in ("d2_07_ficha_e1", "d2_08_exp_e1"):
        regs.extend(c for c in (d.get("contratos") or []) if c.get("codigo_empregado") == "E1")
    elif doc in ("d2_09_ficha_e2", "d2_10_exp_e2"):
        regs.extend(c for c in (d.get("contratos") or []) if c.get("codigo_empregado") == "E2")
    elif doc == "d2_11_folha":
        if d.get("comp"):
            regs.append(d["comp"])
        regs.extend(d.get("itens") or [])
    elif doc == "d2_12_resumo_contab":
        if d.get("comp"):
            regs.append(d["comp"])
    elif doc == "d2_13_auditoria":
        regs.extend(d.get("auditoria") or [])
    elif doc == "d2_14_premissas":
        regs.extend(d.get("consultas") or [])
        regs.extend(d.get("parametros") or [])
    elif doc == "d2_15_ia":
        regs.extend(d.get("diario_ia") or [])
    return regs


def _contagem_doc(doc: str, d: dict[str, Any]) -> tuple[int, int, int]:
    regs = _registros_por_doc(doc, d)
    homol = sum(1 for r in regs if r.get("status_validacao") == "homologado_contadora")
    pend = sum(1 for r in regs if r.get("status_validacao") not in ("homologado_contadora", "acervo_referencia"))
    return homol, len(regs), pend


def _produtos_doc00(d: dict[str, Any]) -> list[dict[str, Any]]:
    saida: list[dict[str, Any]] = []
    for req in d.get("requisitos") or []:
        docs_lista = []
        homol_p = 0
        total_p = 0
        for dk in req.get("documentos_json") or []:
            info = DOCUMENTOS.get(dk)
            if not info:
                continue
            h, t, _ = _contagem_doc(dk, d)
            homol_p += h
            total_p += t
            docs_lista.append({"doc": dk, "nn": info["nn"], "curto": info["curto"], "homologados": h, "total": t})
        saida.append({
            "codigo": req.get("codigo") or "—",
            "descricao": req.get("descricao") or "—",
            "docs": docs_lista,
            "homologados_total": homol_p,
            "total_registros": total_p,
        })
    return saida


def _parametros_por_categoria(parametros: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    ordem_cats = ("inss", "irrf", "reducao_irrf_2026", "salario_familia", "fgts", "cct_clausula")
    grupos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in parametros:
        grupos[str(p.get("categoria") or "outros")].append(p)
    cats = [c for c in ordem_cats if c in grupos] + [c for c in grupos if c not in ordem_cats]
    return [(c, grupos[c]) for c in cats]


def _fmt_pct_socio(micro: int | None) -> str:
    if micro is None:
        return "—"
    v = int(micro)
    if abs(v) > 1_000_000:
        return texto.num_br(v / 1_000_000.0, 2) + "%"
    return texto.pct_micro(v)


def _capital_doc01(d: dict[str, Any]) -> dict[str, int | None]:
    subscrito = sum(int(s.get("valor_centavos") or 0) for s in (d.get("socios") or []))
    fatos = d.get("fatos_capital") or []
    cap_vigente = next(
        (
            f for f in fatos
            if f.get("atributo", "capital_social") == "capital_social"
            and f.get("vigente_ate") is None
            and f.get("valor_centavos") is not None
        ),
        None,
    )
    if subscrito <= 0 and cap_vigente:
        subscrito = int(cap_vigente["valor_centavos"])
    fato_int = next(
        (
            f for f in fatos
            if f.get("atributo") == "capital_integralizado"
            and f.get("vigente_ate") is None
            and f.get("valor_centavos") is not None
        ),
        None,
    )
    if fato_int is None:
        return {"subscrito": subscrito, "integralizado": None, "a_integralizar": None}
    integralizado = int(fato_int["valor_centavos"])
    a_integralizar = max(0, subscrito - integralizado)
    return {"subscrito": subscrito, "integralizado": integralizado, "a_integralizar": a_integralizar}


def _memoria_custo_doc02(cs: dict[str, Any] | None) -> tuple[list[dict[str, Any]], int]:
    if not cs:
        return [], 0
    vh = int(cs.get("valor_hora_centavos") or 0)
    linhas: list[dict[str, Any]] = []
    for raw in cs.get("memoria_horas_json") or []:
        if not isinstance(raw, dict):
            continue
        horas = int(raw.get("horas") or 0)
        linhas.append({
            "frente": str(raw.get("frente") or raw.get("atividade") or "—"),
            "horas": horas,
            "valor_hora_centavos": vh,
            "total_centavos": horas * vh,
        })
    return linhas, sum(int(ln["total_centavos"]) for ln in linhas)


def _conciliacao_doc12(d: dict[str, Any]) -> list[dict[str, Any]]:
    comp = d.get("comp") or {}
    itens = d.get("itens") or []
    partidas = d.get("partidas") or []
    if not comp and not itens and not partidas:
        return []

    def soma_it(cod: str) -> int:
        return sum(int(it.get("valor_centavos") or 0) for it in itens if it.get("codigo_rubrica") == cod)

    def soma_pt(dc: str, contas: tuple[str, ...] | None = None, tag: str | None = None) -> int:
        return sum(
            int(p.get("valor_centavos") or 0)
            for p in partidas
            if p.get("dc") == dc
            and (contas is None or p.get("conta_codigo") in contas)
            and (tag is None or p.get("tag_ref") == tag)
        )

    bruto_folha = sum(int(it.get("valor_centavos") or 0) for it in itens if it.get("tipo_rubrica") == "provento") if itens else int(comp.get("bruto_total_centavos") or 0)
    liq_folha = int(comp.get("liquido_total_centavos") or 0)
    inss_folha = soma_it("INSS-RET") if itens else int(comp.get("inss_total_centavos") or 0)
    neg_folha = soma_it("NEGOCIAL")
    fgts_folha = soma_it("FGTS-8") if itens else int(comp.get("fgts_total_centavos") or 0)
    vt_desc_folha = soma_it("VT-DESC")
    prov_folha = sum(int(it.get("valor_centavos") or 0) for it in itens if it.get("tipo_rubrica") == "provisao") if itens else int(comp.get("provisoes_total_centavos") or 0)
    tot_d = soma_pt("D")
    tot_c = soma_pt("C")

    linhas = [
        ("1", "Total de Proventos Brutos", bruto_folha, soma_pt("D", ("4.1.1.01", "4.2.1.01", "4.2.1.02"), "folha_l1")),
        ("2", "Salários Líquidos a Pagar", liq_folha, soma_pt("C", ("2.1.2.01",), "folha_l1")),
        ("3", "INSS Retido (DCTFWeb)", inss_folha, soma_pt("C", ("2.1.2.02",), "folha_l1")),
        ("4", "Contribuição Negocial (CCT)", neg_folha, soma_pt("C", ("2.1.2.05",), "folha_l1")),
        ("5", "FGTS da Folha (FGTS Digital 8%)", fgts_folha, soma_pt("C", ("2.1.2.03",), "folha_l2")),
        ("6", "Desconto Vale-Transporte (6%)", vt_desc_folha, soma_pt("C", ("4.1.1.05", "4.2.1.05"), "folha_l1")),
        ("7", "Provisões Trabalhistas + FGTS (L4)", prov_folha, soma_pt("D", None, "folha_l4")),
        ("8", "Partidas Dobradas (Débitos × Créditos)", tot_d, tot_c),
    ]
    return [
        {"num": num, "rubrica": rub, "folha": v_fol, "contab": v_con, "diferenca": v_fol - v_con}
        for num, rub, v_fol, v_con in linhas
    ]


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
    mk = _marcadores_d2(d)
    resumo_exec = None
    if doc in ("d2_00_indice", "d2_11_folha", "d2_12_resumo_contab"):
        resumo_exec = {
            "competencia": comp.get("competencia") or "—",
            "bruto": mk["BRUTO_TOTAL"],
            "inss": mk["INSS_TOTAL"],
            "fgts": mk["FGTS_TOTAL"],
            "liq_a": mk["LIQUIDO_A"],
            "liq_b": mk["LIQUIDO_B"],
            "provisoes": mk["PROVISOES_TOTAL"],
            "custo": mk["CUSTO_SIMPLES"],
            "partidas": mk["PARTIDAS_DOBRADAS"],
        }

    _, _, pend_doc_calc = _contagem_doc(doc, d)
    pend_doc = d["pendencias_total"] if doc == "d2_00_indice" else pend_doc_calc
    cnpj_info = {"valor": sede["cnpj"], "eh_ficticio": True} if sede.get("cnpj") else None

    ctx_extra: dict[str, Any] = {}
    if doc == "d2_00_indice":
        ctx_extra["produtos_d2"] = _produtos_doc00(d)
        ctx_extra["quarentena"] = d.get("quarentena") or []
    elif doc == "d2_05_onboarding":
        dils = d.get("diligencias") or []
        ctx_extra["dil_docs"] = [x for x in dils if x.get("tipo") == "documento"]
        ctx_extra["dil_pergs"] = [x for x in dils if x.get("tipo") == "pergunta"]
        ctx_extra["dil_pends"] = [x for x in dils if x.get("tipo") == "pendencia"]
    elif doc == "d2_06_prontuario":
        cts = d.get("contratos") or []
        ctx_extra["prontuarios"] = [{"ct": ct, "pecas": _normalizar_docs_admissao(ct)} for ct in cts]
        ctx_extra["esocial"] = d.get("esocial") or []
        ctx_extra["contratos_dp"] = cts
    elif doc in ("d2_07_ficha_e1", "d2_09_ficha_e2"):
        alvo = "E1" if doc == "d2_07_ficha_e1" else "E2"
        ct = next((c for c in (d.get("contratos") or []) if c.get("codigo_empregado") == alvo), None)
        est = None
        if ct and ct.get("estabelecimento_id"):
            est = next((e for e in (d.get("estabelecimentos") or []) if e.get("id") == ct.get("estabelecimento_id")), None)
        ctx_extra["ficha_ct"] = ct
        ctx_extra["ficha_estab"] = est or sede
    elif doc == "d2_14_premissas":
        ctx_extra["premissas"] = d.get("consultas") or []
        ctx_extra["parametros_grupos"] = _parametros_por_categoria(d.get("parametros") or [])
    elif doc == "d2_15_ia":
        ctx_extra["diario_ia"] = d.get("diario_ia") or []
    elif doc == "d2_01_diagnostico":
        emp_pid = int(d["empresa"].get("pessoa_id") or 0)
        nire_matriz = next(
            (pi.get("valor") for pi in (d.get("identificadores") or []) if int(pi.get("pessoa_id") or 0) == emp_pid and pi.get("tipo_id") == "NIRE"),
            None,
        )
        ctx_extra["estabelecimentos_d2"] = d.get("estabelecimentos") or []
        ctx_extra["socios_d2"] = d.get("socios") or []
        ctx_extra["enquadramento_d2"] = d.get("enquadramento")
        ctx_extra["nire_matriz"] = nire_matriz
        ctx_extra["capital_d2"] = _capital_doc01(d)
        ctx_extra["clausulas_d2"] = d.get("clausulas_d2") or []
    elif doc in ("d2_02_proposta", "d2_03_contrato", "d2_04_termo_rt"):
        cod_srv = {"d2_02_proposta": "proposta", "d2_03_contrato": "contrato", "d2_04_termo_rt": "termo_rt"}[doc]
        cs = next((c for c in (d.get("contratos_servico") or []) if c.get("codigo_documento") == cod_srv), None)
        mem_linhas, mem_total = _memoria_custo_doc02(cs)
        ctx_extra["escritorio_d1"] = d.get("escritorio")
        ctx_extra["estabelecimentos_d2"] = d.get("estabelecimentos") or []
        ctx_extra["contrato_srv"] = cs
        ctx_extra["memoria_custo"] = mem_linhas
        ctx_extra["memoria_total"] = mem_total
        if doc == "d2_04_termo_rt":
            ctx_extra["pends_termo_rt"] = [
                x for x in (d.get("diligencias") or [])
                if x.get("tipo") == "pendencia" and x.get("status_item") != "concluido"
            ]
    elif doc in ("d2_08_exp_e1", "d2_10_exp_e2"):
        alvo = "E1" if doc == "d2_08_exp_e1" else "E2"
        ctx_extra["exp_ct"] = next((c for c in (d.get("contratos") or []) if c.get("codigo_empregado") == alvo), None)
    elif doc == "d2_12_resumo_contab":
        ctx_extra["conciliacao_d2"] = _conciliacao_doc12(d)
    elif doc == "d2_13_auditoria":
        aud = d.get("auditoria") or []
        ctx_extra["aud_pts"] = [a for a in aud if a.get("tipo_registro") == "papel_trabalho"]
        ctx_extra["aud_achados"] = [a for a in aud if a.get("tipo_registro") == "achado"]
        ctx_extra["recalculo_ind"] = (
            recalcular_folha_independente_dados(comp, d.get("contratos") or [], d.get("parametros") or [], d.get("itens") or [])
            if comp else []
        )

    return _jinja().get_template("d2_doc.html").render(
        doc=doc, info=info, css=Markup(css), brand=brand, para_web=para_web,
        js_orientacao=Markup(JS_ORIENTACAO), empresa=d["empresa"], rt=d["rt"], cnpj=cnpj_info,
        pend_doc=pend_doc, pendencias_total=d["pendencias_total"],
        emitido_em=d["emitido_em"], socios=[],
        sede_txt=f"{sede.get('endereco') or '—'} — {sede.get('municipio') or '—'}/{sede.get('uf') or '—'}",
        secoes=d["secoes"].get(doc, []), md=_md_vivo_d2(d), rot=rotulos.rotulo,
        brl=texto.brl, brl_tab=texto.brl_tab, pct=texto.pct_micro, num=texto.num_br,
        fmt_hhmm=_fmt_hhmm, fmt_data=_fmt_data, fmt_pct_socio=_fmt_pct_socio,
        resumo_executivo=resumo_exec,
        extra_rubricas=d["itens"] if doc == "d2_11_folha" else None,
        extra_partidas=d["partidas"] if doc == "d2_12_resumo_contab" else None,
        **ctx_extra,
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
