"""Exportador limpo dos papeis de trabalho e entregaveis do Dossie 1 a partir do PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sistema.config import PLATAFORMA_DIR
from sistema.pg.db import conectar_pg
from sistema.web.repo import EMPRESA_CHAVE_D1

EXPORT_D1_DIR = PLATAFORMA_DIR / "exportacoes" / "dossie1"


def _fmt_brl(centavos: int) -> str:
    val = centavos / 100.0
    neg = val < 0
    s = f"{abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"(R$ {s})" if neg else f"R$ {s}"


def _tag_homolog(status: str) -> str:
    return "" if status == "homologado_contadora" else f" *(Quarentena: {status})*"


def _esc_md(val: Any) -> str:
    return str(val or "").replace("\r\n", "<br>").replace("\n", "<br>").replace("|", "\\|").strip()


def _safe_xlsx(val: Any) -> Any:
    if isinstance(val, str) and val and val[0] in ("=", "+", "-", "@"):
        return "'" + val
    return val


def exportar_dossie1(destino_dir: Path = EXPORT_D1_DIR) -> dict[str, Any]:
    """Compila .md e .xlsx diretamente do estado vigente no PostgreSQL (lab_contabil)."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM erp.empresa WHERE chave = %s", (EMPRESA_CHAVE_D1,))
            emp = cur.fetchone()
            emp_id = int(emp["id"])
            cur.execute("SELECT * FROM erp.estabelecimento WHERE empresa_id = %s ORDER BY id", (emp_id,))
            estabs = cur.fetchall()
            cur.execute(
                """
                SELECT ps.*, p.nome_canonico
                FROM erp.participacao_societaria ps
                JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id
                WHERE ps.empresa_id = %s AND ps.vigente_ate IS NULL ORDER BY ps.id
                """,
                (emp_id,),
            )
            socios = cur.fetchall()
            cur.execute(
                """
                SELECT enq.*, p.nome_canonico AS rt_nome
                FROM erp.enquadramento_historico enq
                LEFT JOIN erp.pessoa p ON p.id = enq.responsavel_tecnico_pessoa_id
                WHERE enq.empresa_id = %s ORDER BY enq.vigente_de DESC LIMIT 1
                """,
                (emp_id,),
            )
            enq = cur.fetchone()
            cur.execute("SELECT * FROM erp.instrumento_societario_clausula WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
            clausulas = cur.fetchall()
            cur.execute("SELECT * FROM erp.processo_legalizacao_etapa WHERE empresa_id = %s ORDER BY ordem", (emp_id,))
            etapas = cur.fetchall()
            cur.execute("SELECT * FROM erp.consulta_normativa WHERE empresa_id = %s ORDER BY numero_questao", (emp_id,))
            consultas = cur.fetchall()
            cur.execute("SELECT * FROM erp.empresa_decisao_preliminar WHERE empresa_id = %s ORDER BY ordem", (emp_id,))
            decisoes = cur.fetchall()
            cur.execute("SELECT * FROM erp.orcamento_cenario WHERE empresa_id = %s AND eh_oficial = true ORDER BY id DESC LIMIT 1", (emp_id,))
            cen = cur.fetchone()
            dems = []
            mens = []
            if cen:
                cur.execute("SELECT * FROM erp.orcamento_demonstrativo_anual WHERE cenario_id = %s ORDER BY ano_ordem", (cen["id"],))
                dems = cur.fetchall()
                cur.execute("SELECT * FROM erp.orcamento_projecao_mensal WHERE cenario_id = %s ORDER BY mes_ordem", (cen["id"],))
                mens = cur.fetchall()
            cur.execute("SELECT * FROM auditoria.diario_ia WHERE empresa_id = %s AND dossie = 'D1' ORDER BY id", (emp_id,))
            ia_rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS pendentes FROM auditoria.vw_pendencias_quarentena WHERE status_validacao <> 'homologado_contadora'")
            pend_total = int(cur.fetchone()["pendentes"])

    aviso_topo = (
        f"> **Status de Governança na Exportação ({datetime.now().strftime('%d/%m/%Y %H:%M')}):** "
        + ("Todos os registros homologados pela contadora." if pend_total == 0 else f"Existem **{pend_total} itens** ainda marcados em quarentena/revisão no sistema.")
        + "\n\n"
    )

    arquivos: list[str] = []

    # 1. Pesquisa Normativa
    p1 = destino_dir / "01_Pesquisa_Registro_Profissional_e_Redesim_DF.md"
    lines_p1 = [f"# PESQUISA ORIENTADA — {emp['nome_curto']}", "", aviso_topo]
    for q in consultas:
        lines_p1 += [
            f"### Q{q['numero_questao']} — {q['enunciado']}{_tag_homolog(q['status_validacao'])}",
            q["resposta_autoral"],
            f"- **Norma / Fonte:** {q['norma_citada']}",
            f"- **Link:** {q['link_oficial']} | **Data de acesso:** {q['data_acesso']}",
            "",
        ]
    lines_p1 += ["## Decisões Preliminares", "| Elemento | Opção Adotada | Alternativas | Justificativa |", "|---|---|---|---|"]
    for d in decisoes:
        lines_p1.append(
            f"| {_esc_md(d['elemento'])} | {_esc_md(d['opcao_adotada'])} | {_esc_md(d['alternativas_consideradas'] or '')} | {_esc_md(d['justificativa_documental'])} |"
        )
    p1.write_text("\n".join(lines_p1), encoding="utf-8")
    arquivos.append(str(p1))

    # 2. Contrato Social e MoU
    for nome_arq, tit_doc, flag_col in (
        ("03_Contrato_Social_ERP.md", "CONTRATO SOCIAL", "aplica_contrato"),
        ("04_Memorando_Entendimentos_MOU_ERP.md", "MEMORANDO DE ENTENDIMENTOS (MOU)", "aplica_mou"),
    ):
        pa = destino_dir / nome_arq
        lns = [
            f"# {tit_doc} — {emp['nome_curto']}",
            "",
            aviso_topo,
            f"**Sede:** {estabs[0]['endereco'] if estabs else 'Nao informada'} | **CNPJ:** {estabs[0]['cnpj'] if estabs else '-'}",
            f"**CNAEs:** {enq['cnae_principal'] if enq else '-'} / {enq['cnaes_secundarios'] if enq else []} | **RT:** {enq['rt_nome'] if enq else '-'}",
            "",
            "## Quadro Societário",
            "| Sócia | Quotas | Capital | Participação | Papel |",
            "|---|---:|---:|---:|---|",
        ]
        for s in socios:
            lns.append(f"| {s['nome_canonico']} | {s['quotas']} | {_fmt_brl(int(s['valor_centavos'] or 0))} | {(int(s['percentual_micro'] or 0)/10000):.2f}% | {s['papel']} |")
        lns.append("")
        for cl in clausulas:
            if not cl[flag_col]:
                continue
            lns += [f"### {cl['numero_clausula']} — {cl['titulo']}{_tag_homolog(cl['status_validacao'])}", cl["regra_texto"], ""]
        pa.write_text("\n".join(lns), encoding="utf-8")
        arquivos.append(str(pa))

    # 3. Fluxo de Abertura DF
    p5 = destino_dir / "05_Fluxo_Abertura_DF_ERP.md"
    lns5 = [
        f"# FLUXO DE ABERTURA NO DISTRITO FEDERAL — {emp['nome_curto']}",
        "",
        aviso_topo,
        "| Ordem | Código | Raia | Etapa | Órgão | Saída / Evidência | Status |",
        "|---:|---|---|---|---|---|---|",
    ]
    for e in etapas:
        lns5.append(
            f"| {e['ordem']} | {_esc_md(e['codigo'])} | {_esc_md(e['raia_responsavel'])} | {_esc_md(e['nome_etapa'])} | {_esc_md(e['orgao'])} | {_esc_md(e['saida_doc'])} | {e['status_validacao']} |"
        )
    p5.write_text("\n".join(lns5), encoding="utf-8")
    arquivos.append(str(p5))

    # 4. Planilha financeira DMA v3 (mesmo modelo do pacote PDF: Leia-me, Premissas, Fluxo, DRE/BP, Viabilidade, Cenarios)
    if cen and dems:
        from sistema.web.dados_dossie1 import carregar_dados_dossie1
        from sistema.web.planilha_dossie1 import gravar_xlsx

        px = gravar_xlsx(carregar_dados_dossie1(), destino_dir / "02_Plano_Financeiro_ERP.xlsx")
        arquivos.append(str(px))

    # 5. Diario de IA
    p6 = destino_dir / "06_Declaracao_Uso_IA_ERP.md"
    lns6 = ["# DECLARAÇÃO DE USO DE IA — REGISTRO NO SISTEMA", "", aviso_topo, "| Entregável | Ferramenta | Finalidade | Fonte Oficial | Revisão Humana | Status |", "|---|---|---|---|---|---|"]
    for row in ia_rows:
        lns6.append(
            f"| {_esc_md(row['entregavel'] or '-')} | {_esc_md(row['ferramenta'] or '-')} | {_esc_md(row['finalidade'])} | {_esc_md(row['fonte_oficial'])} | {_esc_md(row['revisao_humana'])} | {row['status_validacao']} |"
        )
    p6.write_text("\n".join(lns6), encoding="utf-8")
    arquivos.append(str(p6))

    return {"diretorio": str(destino_dir), "arquivos": arquivos, "pendencias_quarentena": pend_total}
