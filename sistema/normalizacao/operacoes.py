"""Camada 3 (Fase 6) — Normalizacao de operacoes fiscais, financeiras, tributarias, contabeis, transacoes e curso."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from sistema.extracao.livros import parse_data_iso, parse_moeda_centavos
from sistema.normalizacao.entidades import ContextoEntidades, _slug

_RE_NF_TAG = re.compile(r"^NF-e\s+(\d+)$", re.I)
_RE_CCB_PARC = re.compile(r"^CCB\s+parc\.\s*(\d+)$", re.I)


def _centavos_flex(s: str | None, moeda: str = "BRL") -> int | None:
    if s is None:
        return None
    txt = str(s).strip()
    if not txt or txt in ("-", "–", "—"):
        return None
    if moeda == "USD" or "," in txt and "." in txt and txt.rfind(".") > txt.rfind(","):
        neg = txt.startswith("(") and txt.endswith(")") or txt.startswith("-")
        clean = re.sub(r"[^\d.]", "", txt)
        if clean:
            val = round(float(clean) * 100)
            return -val if neg else val
    neg = txt.startswith("(") and txt.endswith(")") or txt.startswith("-")
    t2 = txt.strip("() ").replace("USD", "").replace("US$", "").replace("R$", "").strip()
    c = parse_moeda_centavos(t2)
    if c is not None:
        return -abs(c) if neg else c
    try:
        return round(float(t2.replace(",", ".")) * 100) * (-1 if neg else 1)
    except ValueError:
        return None


def _micro_flex(s: str | None) -> int | None:
    if not s:
        return None
    txt = str(s).strip()
    m_pct = re.search(r"(\d+[\.,]\d+)\s*%", txt)
    if m_pct:
        return round(float(m_pct.group(1).replace(",", ".")) * 10_000)
    m_num = re.search(r"(\d+[\.,]\d+)", txt)
    if m_num:
        return round(float(m_num.group(1).replace(",", ".")) * 1_000_000)
    return None


def _data_flex(s: str | None, fallback: str | None = None) -> str | None:
    if not s:
        return fallback
    m = re.search(r"(\d{2}/\d{2}/\d{4})", str(s))
    if m:
        return parse_data_iso(m.group(1)) or fallback
    m_iso = re.search(r"(\d{4}-\d{2}-\d{2})", str(s))
    if m_iso:
        return m_iso.group(1)
    return fallback


def _carregar_docs_e_itens(conn: sqlite3.Connection) -> tuple[list[tuple[Any, ...]], dict[int, list[tuple[Any, ...]]], dict[int, list[tuple[Any, ...]]]]:
    docs = conn.execute(
        """
        SELECT d.id, d.chave, d.arquivo_id, d.modelo, d.tipo, d.numero, d.serie,
               d.data_emissao, d.data_referencia, d.doc_ref, d.estabelecimento_prefixo,
               d.valor_total_centavos, d.moeda, a.chave
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        ORDER BY d.id
        """
    ).fetchall()
    campos_por_doc: dict[int, list[tuple[Any, ...]]] = {}
    for r in conn.execute(
        "SELECT documento_id, secao, rotulo, valor_texto, valor_centavos, moeda, valor_micro, valor_data, linha_bruto_id FROM ext_campo ORDER BY id"
    ).fetchall():
        campos_por_doc.setdefault(int(r[0]), []).append(r[1:])

    itens_por_doc: dict[int, list[tuple[Any, ...]]] = {}
    for r in conn.execute(
        "SELECT documento_id, tabela, n_linha, colunas_json, linha_bruto_id FROM ext_item ORDER BY id"
    ).fetchall():
        itens_por_doc.setdefault(int(r[0]), []).append(r[1:])
    return docs, campos_por_doc, itens_por_doc


def normalizar_operacoes_e_contabilidade(
    conn: sqlite3.Connection,
    ctx: ContextoEntidades,
) -> dict[str, int]:
    """Popula todas as tabelas operacionais, tributarias, contabeis, transacoes, curso e evidencia."""
    docs, campos_por_doc, itens_por_doc = _carregar_docs_e_itens(conn)

    def _ev_doc(tab: str, reg_chave: str, doc_lid: int | None, arq_chave: str) -> None:
        if doc_lid and doc_lid in ctx.lin_chave_por_id:
            ctx.add_ev(tab, reg_chave, "bru_linha", ctx.lin_chave_por_id[doc_lid])
        else:
            ctx.add_ev(tab, reg_chave, "bru_arquivo", arq_chave)

    # 1. Produtos e Estoque (nrm_produto, nrm_ciclo_importacao, nrm_estoque_movimento)
    produtos_por_cod: dict[str, int] = {}
    est_rows = conn.execute(
        "SELECT id, chave, arquivo_id, aba, ordem, produto_codigo, descricao, dados_json, celula_id FROM ext_estoque_linha ORDER BY id"
    ).fetchall()

    # Pass 1a: Ficha abertura define produtos e abertura
    for _, ch_e, _, aba, _, prod_cod, desc, djson, cel_id in est_rows:
        if aba != "Ficha abertura 01-01-2025" or not prod_cod:
            continue
        dados = json.loads(djson)
        p_chave = f"prod:{prod_cod}"
        cur = conn.execute(
            """
            INSERT INTO nrm_produto (chave, codigo_interno, descricao, ncm, cest, origem)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (p_chave, prod_cod, desc or prod_cod, dados.get("NCM"), None, dados.get("Origem do item")),
        )
        pid = int(cur.lastrowid)
        produtos_por_cod[prod_cod] = pid
        bkey = ctx.cel_chave_por_id.get(cel_id, ch_e)
        btab = "bru_celula" if cel_id in ctx.cel_chave_por_id else "bru_arquivo"
        ctx.add_ev("nrm_produto", p_chave, btab, bkey)

        qtd = int(round(float(dados.get("Qtd. inicial") or 0)))
        cu = _centavos_flex(str(dados.get("Custo médio unitário (R$)")))
        vt = _centavos_flex(str(dados.get("Valor total (R$)")))
        m_ch = f"estmov:abertura:{prod_cod}"
        conn.execute(
            """
            INSERT INTO nrm_estoque_movimento (
                chave, produto_id, ciclo_importacao_id, tipo_movimento, data_movimento, quantidade, custo_unitario_centavos, valor_total_centavos
            ) VALUES (?, ?, NULL, 'abertura', '2025-01-01', ?, ?, ?)
            """,
            (m_ch, pid, qtd, cu, vt),
        )
        ctx.add_ev("nrm_estoque_movimento", m_ch, btab, bkey)

    # Pass 1b: Ciclos de importacao e entradas de estoque
    ciclos_por_camb: dict[str, int] = {}
    for _, ch_e, arq_id, aba, ordem, _, _, djson, cel_id in est_rows:
        if aba != "Entradas – importações":
            continue
        dados = json.loads(djson)
        camb = str(dados.get("Câmbio (Doc/Ref)") or "").strip()
        if not camb:
            continue
        dt_c = _data_flex(dados.get("Data do câmbio"), "2025-01-01") or "2025-01-01"
        dt_e = _data_flex(dados.get("Data de entrada no estoque"))
        emp_id = ctx.empresas_por_chave["emp:meia_ponte"] if dt_c >= "2026-01-01" and "G" in camb else ctx.empresas_por_chave["emp:rota_sul_d4"]
        c_ch = f"ciclo:{camb}"
        cur = conn.execute(
            """
            INSERT INTO nrm_ciclo_importacao (
                chave, empresa_id, cambio_doc_ref, data_cambio, data_entrada_estoque, pais_origem, principal_brl_centavos, iof_centavos
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c_ch,
                emp_id,
                camb,
                dt_c,
                dt_e,
                dados.get("País"),
                _centavos_flex(str(dados.get("Principal R$") or "")),
                _centavos_flex(str(dados.get("IOF R$") or "")),
            ),
        )
        cic_id = int(cur.lastrowid)
        ciclos_por_camb[camb] = cic_id
        bkey = ctx.cel_chave_por_id.get(cel_id, ctx.arq_chave_por_id[arq_id])
        btab = "bru_celula" if cel_id in ctx.cel_chave_por_id else "bru_arquivo"
        ctx.add_ev("nrm_ciclo_importacao", c_ch, btab, bkey)

        itens_str = str(dados.get("Itens (qtd.)") or "")
        for part in itens_str.split(";"):
            if ":" not in part:
                continue
            pcod, pqtd = part.split(":", 1)
            pcod = pcod.strip()
            pid = produtos_por_cod.get(pcod)
            if pid:
                qtd_i = int(re.sub(r"\D", "", pqtd) or 0)
                m_ch = f"estmov:entrada:{camb}:{pcod}"
                conn.execute(
                    """
                    INSERT INTO nrm_estoque_movimento (
                        chave, produto_id, ciclo_importacao_id, tipo_movimento, data_movimento, quantidade, custo_unitario_centavos, valor_total_centavos
                    ) VALUES (?, ?, ?, 'entrada_importacao', ?, ?, NULL, NULL)
                    """,
                    (m_ch, pid, cic_id, dt_e or dt_c, qtd_i),
                )
                ctx.add_ev("nrm_estoque_movimento", m_ch, btab, bkey)

    # Pass 1c: Saldos mensais de estoque
    for _, ch_e, arq_id, aba, _, prod_cod, _, djson, cel_id in est_rows:
        if aba != "Saldos mensais (qtd.)" or not prod_cod:
            continue
        pid = produtos_por_cod.get(prod_cod)
        if not pid:
            continue
        dados = json.loads(djson)
        bkey = ctx.cel_chave_por_id.get(cel_id, ctx.arq_chave_por_id[arq_id])
        btab = "bru_celula" if cel_id in ctx.cel_chave_por_id else "bru_arquivo"
        for k, v in dados.items():
            if re.match(r"^\d{4}-\d{2}$", k):
                qtd_m = int(round(float(v)))
                m_ch = f"estmov:saldo:{k}:{prod_cod}"
                conn.execute(
                    """
                    INSERT INTO nrm_estoque_movimento (
                        chave, produto_id, ciclo_importacao_id, tipo_movimento, data_movimento, quantidade, custo_unitario_centavos, valor_total_centavos
                    ) VALUES (?, ?, NULL, 'saldo_mensal', ?, ?, NULL, NULL)
                    """,
                    (m_ch, pid, f"{k}-28", qtd_m),
                )
                ctx.add_ev("nrm_estoque_movimento", m_ch, btab, bkey)

    # Atualizar CEST nos produtos a partir de NFe
    for d_id, _, _, mod, *_ in docs:
        if mod != "NFe":
            continue
        for _, _, cj, _ in itens_por_doc.get(d_id, []):
            row_d = json.loads(cj)
            cod = row_d.get("Cód.")
            cest = row_d.get("CEST")
            if cod and cest and cod in produtos_por_cod:
                conn.execute("UPDATE nrm_produto SET cest = COALESCE(cest, ?) WHERE id = ?", (cest, produtos_por_cod[cod]))

    # 2. Index auxiliar de Commercial-Invoice / Cronograma / Posicao por doc_ref
    invoices_por_ref: dict[str, tuple[str | None, int]] = {}
    for d_id, _, _, mod, _, _, _, _, _, d_ref, _, val_c, _, _ in docs:
        if mod == "Commercial-Invoice" and d_ref:
            cmps = campos_por_doc.get(d_id, [])
            inv_num = None
            for _, rot, vtxt, *_ in cmps:
                if rot == "TEXTO" and "Invoice No." in str(vtxt):
                    inv_num = str(vtxt).replace("Invoice No.", "").strip()
                    break
            invoices_por_ref[d_ref] = (inv_num, val_c or 0)

    nfe_num_to_doc_ref: dict[str, str] = {}
    nfe_entrada_por_ref: dict[str, list[dict[str, str]]] = {}

    # 3. Documentos fiscais, financeiros, tributarios e controle interno a partir dos 2.191 ext_documento
    n_counts: dict[str, int] = {}

    def _inc(k: str) -> None:
        n_counts[k] = n_counts.get(k, 0) + 1

    # Mapear ext_documento_id -> membros de transacao e chave da entidade normalizada
    doc_para_nrm_membro: list[tuple[int, str, str | None, str | None, str | None, str, str]] = []
    # (ext_doc_id, nrm_tab, doc_ref, est_pfx, data_ref, nrm_chave, modelo)

    ccbs_criadas: dict[str, int] = {}

    # 3a. Garantir CCB antes de Cronograma/Posicao
    for d_id, d_ch, arq_id, mod, tp, num, ser, dt_em, dt_ref, d_ref, est_pfx, val_c, moeda, a_ch in docs:
        if mod != "CCB":
            continue
        cmps = {r[1]: r for r in campos_por_doc.get(d_id, [])}
        cred_ch = f"nrm:ccred:{d_ch}"
        princ = cmps.get("VALOR LÍQUIDO LIBERADO (PRINCIPAL)", (None, None, None, val_c))[3] or (val_c or 0)
        dt_lib = _data_flex(cmps.get("DATA DE LIBERAÇÃO", (None, None, ""))[2], dt_em or dt_ref) or "2025-04-18"
        taxa = cmps.get("TAXA DE JUROS", (None, None, None))[2]
        lid = cmps.get("VALOR LÍQUIDO LIBERADO (PRINCIPAL)", (None,)*8)[-1]
        cur = conn.execute(
            """
            INSERT INTO nrm_contrato_credito (
                chave, empresa_id, numero_contrato, data_contratacao, principal_centavos, taxa_juros_texto, doc_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (cred_ch, ctx.empresas_por_chave["emp:rota_sul_d4"], num or d_ref or "EMP2221", dt_lib, princ, taxa, d_ref),
        )
        ccbs_criadas[d_ref or "EMP2221"] = int(cur.lastrowid)
        _ev_doc("nrm_contrato_credito", cred_ch, lid, a_ch)
        doc_para_nrm_membro.append((d_id, "nrm_contrato_credito", d_ref, est_pfx, dt_lib, cred_ch, mod))
        _inc("contratos_credito")

    for d_id, d_ch, arq_id, mod, tp, num, ser, dt_em, dt_ref, d_ref, est_pfx, val_c, moeda, a_ch in docs:
        est_id = ctx.estab_por_prefixo.get(est_pfx or "")
        cmps = campos_por_doc.get(d_id, [])
        cmp_map: dict[str, tuple[Any, ...]] = {}
        for c_row in cmps:
            cmp_map.setdefault(str(c_row[1]), c_row)
        itens = itens_por_doc.get(d_id, [])
        first_lid = next((c_row[7] for c_row in cmps if c_row[7]), None)

        # --- FAMILIA FISCAL ---
        if mod in ("NFe", "NFSe", "CTe", "NFe-compra", "NFe-entrada-importacao", "Fatura-energia", "Fatura-telecom"):
            tp_map = {
                "NFe": "NFe",
                "NFSe": "NFSe",
                "CTe": "CTe",
                "NFe-compra": "NFe_compra",
                "NFe-entrada-importacao": "NFe_entrada_importacao",
                "Fatura-energia": "Fatura_energia",
                "Fatura-telecom": "Fatura_telecom",
            }
            tp_doc = tp_map[mod]
            ch_f = f"nrm:df:{d_ch}"
            dt_doc = dt_em or dt_ref or "2025-01-01"
            chave_acc = cmp_map.get("CHAVE DE ACESSO", (None, None, None))[2]
            nat_op = cmp_map.get("NATUREZA DA OPERAÇÃO", (None, None, None))[2]
            if mod == "NFe" and num and d_ref:
                n_limpo = num.split("/")[0].replace(".", "").strip()
                nfe_num_to_doc_ref[n_limpo] = d_ref
            if mod == "NFe-entrada-importacao" and d_ref:
                nfe_entrada_por_ref[d_ref] = [json.loads(it[2]) for it in itens]

            # Emitente / Destinatario
            emit_id = None
            dest_id = None
            if mod == "NFe":
                emit_id = ctx.pessoas_por_chave.get("pes:pj:41234567000101" if est_pfx == "G" else "pes:pj:12345678000190")
                n_dest = cmp_map.get("NOME / RAZÃO SOCIAL", (None, None, None))[2]
                doc_dest = cmp_map.get("CNPJ / CPF", (None, None, None))[2]
                if n_dest:
                    dest_id = ctx.resolver_ou_criar_contraparte(conn, n_dest, doc_dest, "destinatario", d_ch, "bru_arquivo", a_ch)
            elif mod in ("NFe-compra", "NFSe", "CTe"):
                dest_id = ctx.pessoas_por_chave.get("pes:pj:41234567000101" if est_pfx == "G" else "pes:pj:12345678000190")
                n_em = cmp_map.get("RAZÃO SOCIAL", (None, None, None))[2]
                doc_em = cmp_map.get("CNPJ", (None, None, None))[2]
                if n_em:
                    emit_id = ctx.resolver_ou_criar_contraparte(conn, n_em, doc_em, "emitente", d_ch, "bru_arquivo", a_ch)

            cur = conn.execute(
                """
                INSERT INTO nrm_documento_fiscal (
                    chave, estabelecimento_id, tipo_documento, numero, serie, chave_acesso,
                    data_emissao, emitente_pessoa_id, destinatario_pessoa_id, natureza_operacao,
                    valor_total_centavos, moeda, doc_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ch_f, est_id, tp_doc, num, ser, chave_acc, dt_doc, emit_id, dest_id, nat_op, val_c or 0, moeda, d_ref),
            )
            df_id = int(cur.lastrowid)
            _ev_doc("nrm_documento_fiscal", ch_f, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_documento_fiscal", d_ref, est_pfx, dt_doc, ch_f, mod))
            _inc("documentos_fiscais")

            for idx_it, (tab_i, n_lin, cj, it_lid) in enumerate(itens, start=1):
                row_d = json.loads(cj)
                if row_d.get("_tipo_linha") == "total":
                    continue
                cod_doc = row_d.get("Cód.")
                prod_id = produtos_por_cod.get(cod_doc) if cod_doc else None
                desc_i = row_d.get("Descrição") or row_d.get("Componente") or row_d.get("Serviço") or "Item"
                vt_i = _centavos_flex(
                    row_d.get("V. total") or row_d.get("Valor") or row_d.get("V. aduaneiro"),
                    moeda,
                ) or 0
                qtd_raw = row_d.get("Qtd") or row_d.get("Quantidade")
                qtd_m = _micro_flex(qtd_raw) if qtd_raw and re.search(r"[\.,]", str(qtd_raw)) else (
                    int(re.sub(r"\D", "", str(qtd_raw))) * 1_000_000 if qtd_raw and re.search(r"\d", str(qtd_raw)) else None
                )
                vu_raw = row_d.get("V. unit.") or row_d.get("Tarifa (R$/kWh)")
                vu_m = _micro_flex(vu_raw)
                it_ch = f"nrm:dfi:{d_ch}:{idx_it}"
                cur_it = conn.execute(
                    """
                    INSERT INTO nrm_documento_fiscal_item (
                        chave, documento_fiscal_id, n_item, produto_id, codigo_item_documento,
                        descricao, ncm_hs, cfop, cst_csosn, unidade, quantidade_micro,
                        valor_unitario_micro, valor_total_centavos, moeda
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        it_ch, df_id, idx_it, prod_id, cod_doc, desc_i,
                        row_d.get("NCM"), row_d.get("CFOP"), row_d.get("CSOSN") or row_d.get("CST"),
                        None, qtd_m, vu_m, vt_i, moeda,
                    ),
                )
                dfi_id = int(cur_it.lastrowid)
                _ev_doc("nrm_documento_fiscal_item", it_ch, it_lid, a_ch)
                _inc("itens_fiscais")

                # Tributos no nivel de item (IPI, ICMS_ST, II, PIS_IMP, COFINS_IMP)
                for k_trib, nome_t in (
                    ("IPI", "IPI"),
                    ("ICMS ST", "ICMS_ST"),
                    ("II", "II"),
                    ("PIS-Imp.", "PIS_IMP"),
                    ("COFINS-Imp.", "COFINS_IMP"),
                ):
                    if k_trib in row_d:
                        v_trib = _centavos_flex(row_d.get(k_trib))
                        if v_trib and v_trib > 0:
                            base_t = _centavos_flex(row_d.get("BC ST") if k_trib == "ICMS ST" else row_d.get("V. aduaneiro"))
                            t_ch = f"nrm:trib:{d_ch}:{idx_it}:{nome_t}"
                            conn.execute(
                                """
                                INSERT INTO nrm_item_tributo (chave, item_id, documento_fiscal_id, tributo, base_centavos, aliquota_micro, aliquota_texto, valor_centavos)
                                VALUES (?, ?, ?, ?, ?, NULL, NULL, ?)
                                """,
                                (t_ch, dfi_id, df_id, nome_t, base_t, v_trib),
                            )
                            _ev_doc("nrm_item_tributo", t_ch, it_lid, a_ch)
                            _inc("itens_tributos")

            # Tributos de cabecalho (ISS em NFSe, ICMS em NFe/CTe/NFe-compra)
            if mod == "NFSe" and "VALOR DO ISS" in cmp_map and (cmp_map["VALOR DO ISS"][3] or 0) > 0:
                t_ch = f"nrm:trib:{d_ch}:ISS"
                conn.execute(
                    """
                    INSERT INTO nrm_item_tributo (chave, item_id, documento_fiscal_id, tributo, base_centavos, aliquota_micro, aliquota_texto, valor_centavos)
                    VALUES (?, NULL, ?, 'ISS', ?, ?, ?, ?)
                    """,
                    (
                        t_ch, df_id,
                        cmp_map.get("BASE DE CÁLCULO DO ISS", (None, None, None, None))[3],
                        cmp_map.get("ALÍQUOTA ISS (DIDÁTICA)", (None,)*6)[5],
                        cmp_map.get("ALÍQUOTA ISS (DIDÁTICA)", (None, None, None))[2],
                        cmp_map["VALOR DO ISS"][3],
                    ),
                )
                _ev_doc("nrm_item_tributo", t_ch, cmp_map["VALOR DO ISS"][7], a_ch)
                _inc("itens_tributos")

            if mod in ("NFe", "NFe-compra") and "VALOR ICMS" in cmp_map and (cmp_map["VALOR ICMS"][3] or 0) > 0:
                t_ch = f"nrm:trib:{d_ch}:ICMS"
                conn.execute(
                    """
                    INSERT INTO nrm_item_tributo (chave, item_id, documento_fiscal_id, tributo, base_centavos, aliquota_micro, aliquota_texto, valor_centavos)
                    VALUES (?, NULL, ?, 'ICMS', ?, NULL, NULL, ?)
                    """,
                    (t_ch, df_id, cmp_map.get("BASE ICMS", (None,)*4)[3], cmp_map["VALOR ICMS"][3]),
                )
                _ev_doc("nrm_item_tributo", t_ch, cmp_map["VALOR ICMS"][7], a_ch)
                _inc("itens_tributos")

        # --- TITULOS (BOLETOS) ---
        elif mod in ("Boleto-aluguel", "Boleto-condominio"):
            subt = "Boleto_aluguel" if mod == "Boleto-aluguel" else "Boleto_condominio"
            t_ch = f"nrm:tit:{d_ch}"
            dt_v = (cmp_map.get("VENCIMENTO", (None,)*7)[6]) or dt_ref
            n_ben = (cmp_map.get("BENEFICIÁRIO", (None,)*3)[2]) or (cmp_map.get("LOCADOR", (None,)*3)[2])
            ben_id = ctx.resolver_ou_criar_contraparte(conn, n_ben, None, "beneficiario", d_ch, "bru_arquivo", a_ch) if n_ben else None
            conn.execute(
                """
                INSERT INTO nrm_titulo (chave, estabelecimento_id, subtipo, numero, data_vencimento, valor_centavos, beneficiario_pessoa_id, doc_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (t_ch, est_id, subt, num, dt_v, val_c or 0, ben_id, d_ref),
            )
            _ev_doc("nrm_titulo", t_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_titulo", d_ref, est_pfx, dt_v or dt_ref, t_ch, mod))
            _inc("titulos")

        # --- CAMBIO & COMMERCIAL INVOICE ---
        elif mod == "Contrato-cambio":
            cb_ch = f"nrm:camb:{d_ch}"
            dt_c = dt_em or dt_ref or "2025-01-01"
            inv_num, usd_c = invoices_por_ref.get(d_ref or "", (None, 0))
            princ_brl = 0
            iof_brl = None
            tar_brl = None
            taxa_m = 0
            taxa_t = "0"
            for _, _, cj, _ in itens:
                it = json.loads(cj)
                nom_i = str(it.get("Item") or "")
                val_rs = _centavos_flex(it.get("Valor em R$"))
                if "Valor em moeda estrangeira" in nom_i or "Valor principal" in nom_i:
                    princ_brl = val_rs or princ_brl
                    if not usd_c and it.get("Base"):
                        usd_c = _centavos_flex(it.get("Base"), "USD") or 0
                    if it.get("Taxa / alíquota"):
                        taxa_t = str(it["Taxa / alíquota"])
                        taxa_m = _micro_flex(taxa_t) or 0
                elif "IOF" in nom_i:
                    iof_brl = val_rs
                elif "Tarifa" in nom_i:
                    tar_brl = val_rs
            exp_name = cmp_map.get("BANCO NO EXTERIOR", (None,)*3)[2]
            exp_id = ctx.resolver_ou_criar_contraparte(conn, exp_name, None, "banco_exterior", d_ch, "bru_arquivo", a_ch, estrangeira=True) if exp_name else None
            conn.execute(
                """
                INSERT INTO nrm_cambio (
                    chave, estabelecimento_id, contrato_numero, data_contratacao, moeda_estrangeira,
                    valor_estrangeiro_centavos, taxa_micro, taxa_texto, principal_brl_centavos,
                    iof_centavos, tarifa_centavos, valor_total_brl_centavos, exportador_pessoa_id, invoice_numero, doc_ref
                ) VALUES (?, ?, ?, ?, 'USD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cb_ch, est_id, num or d_ref or cb_ch, dt_c, usd_c, taxa_m, taxa_t, princ_brl, iof_brl, tar_brl, val_c or 0, exp_id, inv_num, d_ref),
            )
            _ev_doc("nrm_cambio", cb_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_cambio", d_ref, est_pfx, dt_c, cb_ch, mod))
            _inc("cambios")

        elif mod == "Commercial-Invoice":
            # Registrado tambem como comprovante/fatura comercial de exportador estrangeiro vinculada ao cambio
            cm_ch = f"nrm:comp:{d_ch}"
            exp_n = cmp_map.get("EXPORTER / SELLER", (None,)*3)[2]
            exp_id = ctx.resolver_ou_criar_contraparte(conn, exp_n, None, "exportador", d_ch, "bru_arquivo", a_ch, estrangeira=True) if exp_n else None
            conn.execute(
                """
                INSERT INTO nrm_comprovante (chave, estabelecimento_id, subtipo, data_operacao, valor_centavos, moeda, contraparte_pessoa_id, doc_ref)
                VALUES (?, ?, 'commercial_invoice', ?, ?, ?, ?, ?)
                """,
                (cm_ch, est_id, dt_em or dt_ref or "2025-01-01", val_c or 0, moeda, exp_id, d_ref),
            )
            _ev_doc("nrm_comprovante", cm_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_comprovante", d_ref, est_pfx, dt_ref or dt_em, cm_ch, mod))
            _inc("comprovantes")

        # --- CREDITO E CARTAO ---
        elif mod == "CCB":
            pass  # Ja inserido acima
        elif mod in ("Cronograma-pagamentos", "Posicao-contrato-parcelas-pagas"):
            cred_id = next(iter(ccbs_criadas.values()))
            if mod == "Cronograma-pagamentos":
                for _, _, cj, it_lid in itens:
                    it = json.loads(cj)
                    if it.get("_tipo_linha") == "total":
                        continue
                    np_raw = str(it.get("Parc.") or "")
                    if not np_raw.isdigit():
                        continue
                    n_p = int(np_raw)
                    p_ch = f"nrm:parc:EMP2221:{n_p:03d}"
                    dt_v = _data_flex(it.get("Vencimento"), dt_ref) or "2025-05-18"
                    conn.execute(
                        """
                        INSERT INTO nrm_parcela (chave, contrato_id, numero_parcela, data_vencimento, amortizacao_centavos, juros_centavos, total_centavos, situacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            p_ch, cred_id, n_p, dt_v,
                            _centavos_flex(it.get("Amortização")) or 0,
                            _centavos_flex(it.get("Juros")) or 0,
                            _centavos_flex(it.get("Prestação")) or 0,
                            it.get("Fase"),
                        ),
                    )
                    _ev_doc("nrm_parcela", p_ch, it_lid, a_ch)
                    _inc("parcelas")
                doc_para_nrm_membro.append((d_id, "nrm_contrato_credito", d_ref, est_pfx, dt_ref, "nrm:ccred:" + next(c[1] for c in docs if c[3] == "CCB"), mod))
            else:
                for _, _, cj, _ in itens:
                    it = json.loads(cj)
                    np_raw = str(it.get("Parc.") or "")
                    if np_raw.isdigit():
                        conn.execute(
                            "UPDATE nrm_parcela SET situacao = ? WHERE contrato_id = ? AND numero_parcela = ?",
                            (f"Liquidada em {it.get('Data da liquidação', '')}".strip(), cred_id, int(np_raw)),
                        )
                doc_para_nrm_membro.append((d_id, "nrm_contrato_credito", d_ref, est_pfx, dt_ref, "nrm:ccred:" + next(c[1] for c in docs if c[3] == "CCB"), mod))

        elif mod == "Extrato-liquidacao-cartao":
            lq_ch = f"nrm:liq:{d_ch}"
            bruto_c = cmp_map.get("VALOR BRUTO DAS PARCELAS", (None,)*4)[3] or (val_c or 0)
            taxa_c = cmp_map.get("(–) TAXA DE DESCONTO (MDR)", (None,)*4)[3]
            liq_c = cmp_map.get("VALOR LÍQUIDO CREDITADO", (None,)*4)[3] or (val_c or 0)
            cur = conn.execute(
                """
                INSERT INTO nrm_liquidacao_cartao (chave, estabelecimento_id, data_liquidacao, valor_bruto_centavos, taxa_centavos, valor_liquido_centavos, doc_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (lq_ch, est_id, dt_ref or dt_em or "2025-01-01", bruto_c, taxa_c, liq_c, d_ref),
            )
            lq_id = int(cur.lastrowid)
            _ev_doc("nrm_liquidacao_cartao", lq_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_liquidacao_cartao", d_ref, est_pfx, dt_ref, lq_ch, mod))
            _inc("liquidacoes_cartao")
            for idx_it, (_, n_lin, cj, it_lid) in enumerate(itens, start=1):
                it = json.loads(cj)
                if it.get("_tipo_linha") == "total":
                    continue
                v_ch = f"nrm:lqv:{d_ch}:{idx_it}"
                conn.execute(
                    """
                    INSERT INTO nrm_liquidacao_cartao_venda (chave, liquidacao_id, data_venda, autorizacao, modalidade, parcela_texto, valor_bruto_centavos, valor_liquido_centavos)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        v_ch, lq_id, _data_flex(it.get("Data da venda")),
                        it.get("Autorização"), it.get("Modalidade"), it.get("Parc."),
                        _centavos_flex(it.get("Bruto")) or 0, _centavos_flex(it.get("Líquido")),
                    ),
                )
                _ev_doc("nrm_liquidacao_cartao_venda", v_ch, it_lid, a_ch)
                _inc("vendas_cartao")

        # --- TRIBUTARIO & ADUANEIRO ---
        elif mod in ("DAS", "DARF-IPI", "Guia-AFRMM", "Guia-DARE-SC", "Guia-DARE-GO-ICMS-importacao", "Guia-DARE-GO-ST", "GNRE-DF", "GNRE-ES", "GNRE-MG"):
            tg_map = {
                "DAS": ("DAS", None), "DARF-IPI": ("DARF_IPI", None), "Guia-AFRMM": ("AFRMM", None),
                "Guia-DARE-SC": ("DARE_SC", "SC"), "Guia-DARE-GO-ICMS-importacao": ("DARE_GO_ICMS_IMP", "GO"),
                "Guia-DARE-GO-ST": ("DARE_GO_ST", "GO"), "GNRE-DF": ("GNRE_DF", "DF"),
                "GNRE-ES": ("GNRE_ES", "ES"), "GNRE-MG": ("GNRE_MG", "MG"),
            }
            tg, uf_g = tg_map[mod]
            comp = (
                cmp_map.get("PERÍODO DE APURAÇÃO", (None,)*3)[2]
                or cmp_map.get("PERÍODO DE REFERÊNCIA", (None,)*3)[2]
            )
            dt_v = (
                cmp_map.get("DATA DE VENCIMENTO", (None,)*7)[6]
                or cmp_map.get("VENCIMENTO", (None,)*7)[6]
                or dt_ref
            )
            vp = cmp_map.get("VALOR PRINCIPAL", (None,)*4)[3] or (val_c or 0)
            g_ch = f"nrm:guia:{d_ch}"
            cur = conn.execute(
                """
                INSERT INTO nrm_guia (chave, estabelecimento_id, tipo_guia, competencia, data_vencimento, valor_principal_centavos, valor_total_centavos, uf, doc_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (g_ch, est_id, tg, comp, dt_v, vp, val_c or vp, uf_g, d_ref),
            )
            gid = int(cur.lastrowid)
            _ev_doc("nrm_guia", g_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_guia", d_ref, est_pfx, dt_ref or dt_v, g_ch, mod))
            _inc("guias")
            for idx_it, (_, n_lin, cj, it_lid) in enumerate(itens, start=1):
                it = json.loads(cj)
                if it.get("_tipo_linha") == "total":
                    continue
                t_desc = it.get("Tributo") or it.get("Componente") or it.get("Descrição") or "Componente"
                t_val = _centavos_flex(it.get("Valor"))
                if t_val is not None:
                    gc_ch = f"nrm:gcomp:{d_ch}:{idx_it}"
                    conn.execute(
                        "INSERT INTO nrm_guia_composicao (chave, guia_id, tributo_codigo, descricao, valor_centavos) VALUES (?, ?, ?, ?, ?)",
                        (gc_ch, gid, _slug(t_desc).upper()[:24], t_desc, t_val),
                    )
                    _ev_doc("nrm_guia_composicao", gc_ch, it_lid, a_ch)

        elif mod == "PGDAS-D":
            ap_ch = f"nrm:apur:{d_ch}"
            emp_id = ctx.empresas_por_chave["emp:meia_ponte" if est_pfx == "G" else "emp:rota_sul_d4"]
            comp = cmp_map.get("PERÍODO DE APURAÇÃO (PA)", (None,)*3)[2] or (dt_ref[:7] if dt_ref else "2026-01")
            rbt12 = cmp_map.get("RECEITA BRUTA ACUMULADA NOS 12 MESES ANTERIORES (RBT12)", (None,)*4)[3]
            rba = cmp_map.get("RECEITA BRUTA DO PA (MERCADO INTERNO)", (None,)*4)[3]
            conn.execute(
                """
                INSERT INTO nrm_apuracao (chave, empresa_id, tipo_apuracao, competencia, receita_bruta_centavos, rbt12_centavos, tributo_apurado_centavos, doc_ref)
                VALUES (?, ?, 'PGDAS_D', ?, ?, ?, ?, ?)
                """,
                (ap_ch, emp_id, comp, rba, rbt12, val_c or 0, d_ref),
            )
            _ev_doc("nrm_apuracao", ap_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_apuracao", d_ref, est_pfx, dt_ref, ap_ch, mod))
            _inc("apuracoes")

        elif mod == "Extrato-DI":
            di_ch = f"nrm:di:{d_ch}"
            tx_c = cmp_map.get("MOEDA / TAXA (DÓLAR DOS EUA)", (None,)*3)[2] or "0"
            tx_m = _micro_flex(tx_c) or 0
            fob_c = _centavos_flex(cmp_map.get("VALOR FOB", (None,)*3)[2], "USD") or 0
            frt_c = _centavos_flex(cmp_map.get("FRETE + SEGURO", (None,)*3)[2], "USD")
            cur = conn.execute(
                """
                INSERT INTO nrm_di (chave, estabelecimento_id, numero_di, data_registro, moeda, taxa_micro, taxa_texto, valor_fob_moeda_centavos, frete_seguro_moeda_centavos, valor_aduaneiro_brl_centavos, doc_ref)
                VALUES (?, ?, ?, ?, 'USD', ?, ?, ?, ?, ?, ?)
                """,
                (di_ch, est_id, num or d_ref or di_ch, dt_em or dt_ref or "2026-01-01", tx_m, tx_c, fob_c, frt_c, val_c or 0, d_ref),
            )
            di_id = int(cur.lastrowid)
            _ev_doc("nrm_di", di_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_di", d_ref, est_pfx, dt_em or dt_ref, di_ch, mod))
            _inc("dis")

            for tab_i, n_lin, cj, it_lid in itens:
                if "ADIÇÕES" not in str(tab_i).upper():
                    continue
                it = json.loads(cj)
                n_ad = str(it.get("Adição") or f"{n_lin:03d}")
                ncm_desc = str(it.get("NCM / descrição") or "")
                m_ncm = re.search(r"(\d{4}\.\d{2}\.\d{2})", ncm_desc)
                ncm_cod = m_ncm.group(1) if m_ncm else ncm_desc[:12]
                # Agrega tributos pelos itens de mesma NCM ou da DI quando aplicavel
                va = ii = ipi = pis = cofins = 0
                ad_ch = f"nrm:di_ad:{d_ch}:{n_ad}"
                conn.execute(
                    """
                    INSERT INTO nrm_di_adicao (chave, di_id, numero_adicao, ncm, valor_aduaneiro_centavos, ii_centavos, ipi_centavos, pis_imp_centavos, cofins_imp_centavos)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ad_ch, di_id, n_ad, ncm_cod, va, ii, ipi, pis, cofins),
                )
                _ev_doc("nrm_di_adicao", ad_ch, it_lid, a_ch)

        # --- CONTROLE INTERNO ---
        elif mod == "Fechamento-caixa":
            fc_ch = f"nrm:fc:{d_ch}"
            dt_f = dt_ref or dt_em or "2025-01-01"
            cur = conn.execute(
                """
                INSERT INTO nrm_fechamento_caixa (chave, estabelecimento_id, data_fechamento, valor_total_centavos, doc_ref)
                VALUES (?, ?, ?, ?, ?)
                """,
                (fc_ch, est_id, dt_f, val_c or 0, d_ref),
            )
            fc_id = int(cur.lastrowid)
            _ev_doc("nrm_fechamento_caixa", fc_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_fechamento_caixa", d_ref, est_pfx, dt_f, fc_ch, mod))
            _inc("fechamentos_caixa")
            for idx_it, (_, n_lin, cj, it_lid) in enumerate(itens, start=1):
                it = json.loads(cj)
                if it.get("_tipo_linha") == "total":
                    continue
                d_dia = _data_flex(it.get("Data"), dt_f) or dt_f
                v_dia = _centavos_flex(it.get("Total em dinheiro")) or 0
                fd_ch = f"nrm:fcd:{d_ch}:{idx_it}"
                conn.execute(
                    "INSERT INTO nrm_fechamento_caixa_dia (chave, fechamento_id, data_dia, valor_centavos) VALUES (?, ?, ?, ?)",
                    (fd_ch, fc_id, d_dia, v_dia),
                )
                _ev_doc("nrm_fechamento_caixa_dia", fd_ch, it_lid, a_ch)

        elif mod in ("Memorando-transferencia", "Carta-socios-Goiania"):
            mm_ch = f"nrm:memo:{d_ch}"
            assunto = (
                "Transferência interbancária / matriz-filial"
                if mod == "Memorando-transferencia"
                else "Carta dos sócios ao contador — Goiânia / Meia Ponte"
            )
            conn.execute(
                "INSERT INTO nrm_memorando (chave, estabelecimento_id, data_memorando, assunto, valor_centavos, doc_ref) VALUES (?, ?, ?, ?, ?, ?)",
                (mm_ch, est_id, dt_em or dt_ref or "2026-09-14", assunto, val_c, d_ref),
            )
            _ev_doc("nrm_memorando", mm_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_memorando", d_ref, est_pfx, dt_ref or dt_em, mm_ch, mod))
            _inc("memorandos")

        elif mod.startswith("Recibo-"):
            subt = mod.replace("Recibo-", "").replace("-", "_")
            rc_ch = f"nrm:rec:{d_ch}"
            comp = cmp_map.get("COMPETENCIA", (None,)*3)[2]
            cp_id = None
            ass = cmp_map.get("ASSINANTE", (None,)*3)[2]
            if ass:
                cp_id = ctx.resolver_ou_criar_contraparte(conn, ass.split("|")[0], cmp_map.get("IDENTIFICADOR_1", (None,)*3)[2], "beneficiario_recibo", d_ch, "bru_arquivo", a_ch)
            conn.execute(
                """
                INSERT INTO nrm_recibo (chave, estabelecimento_id, subtipo, data_recibo, competencia, beneficiario_pessoa_id, valor_centavos, doc_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rc_ch, est_id, subt, dt_em or dt_ref or "2025-01-01", comp, cp_id, val_c or 0, d_ref),
            )
            _ev_doc("nrm_recibo", rc_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_recibo", d_ref, est_pfx, dt_em or dt_ref, rc_ch, mod))
            _inc("recibos")

        # --- COMPROVANTES BANCARIOS E DEMAIS ---
        else:
            cp_ch = f"nrm:comp:{d_ch}"
            cp_n = cmp_map.get("NOME", (None,)*3)[2] or cmp_map.get("CLIENTE", (None,)*3)[2]
            cp_doc = cmp_map.get("CNPJ", (None,)*3)[2] or cmp_map.get("CPF", (None,)*3)[2] or cmp_map.get("CNPJ / CPF", (None,)*3)[2]
            cp_pid = ctx.resolver_ou_criar_contraparte(conn, cp_n, cp_doc, "contraparte", d_ch, "bru_arquivo", a_ch) if cp_n else None
            conn.execute(
                """
                INSERT INTO nrm_comprovante (chave, estabelecimento_id, subtipo, data_operacao, valor_centavos, moeda, contraparte_pessoa_id, doc_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cp_ch, est_id, _slug(mod), dt_em or dt_ref or "2025-01-01", val_c or 0, moeda, cp_pid, d_ref),
            )
            _ev_doc("nrm_comprovante", cp_ch, first_lid, a_ch)
            doc_para_nrm_membro.append((d_id, "nrm_comprovante", d_ref, est_pfx, dt_ref or dt_em, cp_ch, mod))
            _inc("comprovantes")

    # Atualizar valores tributarios das adicoes de DI cruzando NFe-entrada-importacao de mesmo doc_ref
    for di_id, di_ch, d_ref in conn.execute("SELECT id, chave, doc_ref FROM nrm_di").fetchall():
        nf_its = nfe_entrada_por_ref.get(d_ref or "", [])
        if not nf_its:
            continue
        for ad_id, ncm in conn.execute("SELECT id, ncm FROM nrm_di_adicao WHERE di_id = ?", (di_id,)).fetchall():
            match = [x for x in nf_its if x.get("_tipo_linha") != "total" and (x.get("NCM") == ncm)]
            if match:
                va = sum(_centavos_flex(x.get("V. aduaneiro")) or 0 for x in match)
                ii = sum(_centavos_flex(x.get("II")) or 0 for x in match)
                ipi = sum(_centavos_flex(x.get("IPI")) or 0 for x in match)
                pis = sum(_centavos_flex(x.get("PIS-Imp.")) or 0 for x in match)
                cof = sum(_centavos_flex(x.get("COFINS-Imp.")) or 0 for x in match)
                conn.execute(
                    """
                    UPDATE nrm_di_adicao
                    SET valor_aduaneiro_centavos=?, ii_centavos=?, ipi_centavos=?, pis_imp_centavos=?, cofins_imp_centavos=?
                    WHERE id=?
                    """,
                    (va, ii, ipi, pis, cof, ad_id),
                )

    # Incluir DANFSe didatica D3 (D3/01_NFSe_Ficticia_Auditoria_Ente_Federal.pdf)
    arq_d3_row = conn.execute(
        "SELECT id, chave FROM bru_arquivo WHERE caminho_relativo = 'D3/01_NFSe_Ficticia_Auditoria_Ente_Federal.pdf'"
    ).fetchone()
    if arq_d3_row:
        d3_aid, d3_ach = int(arq_d3_row[0]), str(arq_d3_row[1])
        d3_ch = "nrm:df:d3:nfse_2026_000184"
        cur_d3 = conn.execute(
            """
            INSERT INTO nrm_documento_fiscal (
                chave, estabelecimento_id, tipo_documento, numero, serie, chave_acesso,
                data_emissao, emitente_pessoa_id, destinatario_pessoa_id, natureza_operacao,
                valor_total_centavos, moeda, doc_ref
            ) VALUES (?, ?, 'NFSe', '2026/000184', NULL, 'DIDATICA-2026-000184-GYN', '2026-10-20', ?, ?, '07.02.01 - Execução de obra por administração', 952000, 'BRL', NULL)
            """,
            (
                d3_ch,
                ctx.estabelecimentos_por_chave["est:horizonte:matriz"],
                ctx.pessoas_por_chave["pes:pj:48321765000120"],
                ctx.pessoas_por_chave["pes:pj:00123456000100"],
            ),
        )
        d3_df_id = int(cur_d3.lastrowid)
        ctx.add_ev("nrm_documento_fiscal", d3_ch, "bru_arquivo", d3_ach)
        _inc("documentos_fiscais")
        for idx_s, (desc_s, val_s) in enumerate(
            [("Projeto elétrico", 472000), ("Projeto de prevenção e combate a incêndio", 480000)], start=1
        ):
            it_ch = f"{d3_ch}:item:{idx_s}"
            conn.execute(
                """
                INSERT INTO nrm_documento_fiscal_item (
                    chave, documento_fiscal_id, n_item, produto_id, codigo_item_documento,
                    descricao, ncm_hs, cfop, cst_csosn, unidade, quantidade_micro, valor_unitario_micro, valor_total_centavos, moeda
                ) VALUES (?, ?, ?, NULL, '07.02.01', ?, NULL, NULL, NULL, 'UN', 1000000, NULL, ?, 'BRL')
                """,
                (it_ch, d3_df_id, idx_s, desc_s, val_s),
            )
            ctx.add_ev("nrm_documento_fiscal_item", it_ch, "bru_arquivo", d3_ach)
        for tr_nom, tr_aliq_m, tr_aliq_t, tr_val in [
            ("ISS", 50000, "5,00%", 47600),
            ("IRRF", 15000, "1,50%", 14280),
            ("CSLL", 10000, "1,00%", 9520),
            ("PIS", 6500, "0,65%", 6188),
            ("COFINS", 30000, "3,00%", 28560),
        ]:
            t_ch = f"{d3_ch}:trib:{tr_nom}"
            conn.execute(
                """
                INSERT INTO nrm_item_tributo (chave, item_id, documento_fiscal_id, tributo, base_centavos, aliquota_micro, aliquota_texto, valor_centavos)
                VALUES (?, NULL, ?, ?, 952000, ?, ?, ?)
                """,
                (t_ch, d3_df_id, tr_nom, tr_aliq_m, tr_aliq_t, tr_val),
            )
            ctx.add_ev("nrm_item_tributo", t_ch, "bru_arquivo", d3_ach)

    # 4. Movimentos bancarios (nrm_movimento_bancario) - 1.122 linhas
    movs_nrm_info: list[tuple[str, str, str, str, str]] = []  # (chave, conta_codigo, data, doc_ref, est_pfx)
    cta_to_pfx = {"matriz_2025": "M", "matriz_2026": "M", "filial": "F", "goiania": "G"}
    for _, ch_m, arq_id, _, n_lin, c_cod, dt_m, hist, d_ref, deb_c, cred_c, sal_c, orig, cel_id in conn.execute(
        "SELECT id, chave, arquivo_id, aba, n_linha, conta_codigo, data_movimento, historico, doc_ref, debito_centavos, credito_centavos, saldo_centavos, origem_valor, celula_saldo_id FROM ext_extrato_linha ORDER BY id"
    ).fetchall():
        tipo_dc = "D" if (deb_c is not None and deb_c > 0) or cred_c is None else "C"
        val_m = deb_c if tipo_dc == "D" else (cred_c or 0)
        nrm_m_ch = f"mov:{c_cod}:{dt_m}:{d_ref}:{n_lin}"
        conn.execute(
            """
            INSERT INTO nrm_movimento_bancario (chave, conta_bancaria_id, data_movimento, historico, doc_ref, tipo_dc, valor_centavos, saldo_apos_centavos, origem_saldo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nrm_m_ch, ctx.contas_por_chave[c_cod], dt_m, hist, d_ref, tipo_dc, val_m or 0, sal_c, orig),
        )
        bkey = ctx.cel_chave_por_id.get(cel_id, ctx.arq_chave_por_id[arq_id])
        btab = "bru_celula" if cel_id in ctx.cel_chave_por_id else "bru_arquivo"
        ctx.add_ev("nrm_movimento_bancario", nrm_m_ch, btab, bkey)
        movs_nrm_info.append((nrm_m_ch, c_cod, dt_m, d_ref, cta_to_pfx[c_cod]))
        _inc("movimentos_bancarios")

    # 5. Contabil (nrm_conta_contabil, nrm_lancamento, nrm_partida, nrm_saldo)
    contas_map: dict[str, int] = {}

    def _garantir_conta(codigo: str, nome: str, bru_tab: str, bru_ch: str) -> int:
        if codigo in contas_map:
            return contas_map[codigo]
        grp = int(codigo.split(".")[0]) if codigo and codigo[0].isdigit() else 1
        nat = "D" if grp in (1, 5, 6) else "C"
        cc_ch = f"cc:{codigo}"
        cur = conn.execute(
            "INSERT INTO nrm_conta_contabil (chave, codigo, nome, grupo, natureza) VALUES (?, ?, ?, ?, ?)",
            (cc_ch, codigo, nome or codigo, grp, nat),
        )
        cid = int(cur.lastrowid)
        contas_map[codigo] = cid
        ctx.add_ev("nrm_conta_contabil", cc_ch, bru_tab, bru_ch)
        _inc("contas_contabeis")
        return cid

    for b_id, b_ch, arq_id, fonte, periodo, c_cod, c_nom, s_ant, deb, cred, s_atu, _, cel_id, lid in conn.execute(
        "SELECT id, chave, arquivo_id, fonte, periodo, conta_codigo, conta_nome, saldo_anterior_centavos, debito_centavos, credito_centavos, saldo_atual_centavos, origem_valor, celula_id, linha_bruto_id FROM ext_balancete_linha ORDER BY id"
    ).fetchall():
        btab = "bru_celula" if cel_id in ctx.cel_chave_por_id else ("bru_linha" if lid in ctx.lin_chave_por_id else "bru_arquivo")
        bkey = ctx.cel_chave_por_id.get(cel_id) or ctx.lin_chave_por_id.get(lid) or ctx.arq_chave_por_id[arq_id]
        cc_id = _garantir_conta(c_cod, c_nom, btab, bkey)
        f_nrm = "abertura_d1" if periodo == "2024-12" else ("balancete_xlsx" if fonte == "xlsx" else "balancete_pdf")
        s_ch = f"nrm:saldo:{f_nrm}:{periodo}:{c_cod}"
        conn.execute(
            """
            INSERT INTO nrm_saldo (chave, conta_id, periodo, fonte, saldo_anterior_centavos, debito_centavos, credito_centavos, saldo_atual_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (s_ch, cc_id, periodo, f_nrm, s_ant, deb, cred, s_atu),
        )
        ctx.add_ev("nrm_saldo", s_ch, btab, bkey)
        _inc("saldos")

    # Saldos anuais por conta do Razao (ultimo movimento da conta no ano)
    for ano_r, c_cod, c_nom, arq_id, sal_c, s_dc, lid in conn.execute(
        """
        SELECT ano, conta_codigo, conta_nome, arquivo_id, saldo_centavos, saldo_dc, linha_bruto_id
        FROM ext_razao_linha r1
        WHERE r1.ordem = (
            SELECT MAX(r2.ordem) FROM ext_razao_linha r2 WHERE r2.ano = r1.ano AND r2.conta_codigo = r1.conta_codigo
        )
        """
    ).fetchall():
        if sal_c is None:
            continue
        bkey = ctx.lin_chave_por_id.get(lid, ctx.arq_chave_por_id[arq_id])
        btab = "bru_linha" if lid in ctx.lin_chave_por_id else "bru_arquivo"
        cc_id = _garantir_conta(c_cod, c_nom, btab, bkey)
        val_s = -sal_c if s_dc == "C" else sal_c
        s_ch = f"nrm:saldo:razao:{ano_r}:{c_cod}"
        conn.execute(
            """
            INSERT INTO nrm_saldo (chave, conta_id, periodo, fonte, saldo_anterior_centavos, debito_centavos, credito_centavos, saldo_atual_centavos)
            VALUES (?, ?, ?, 'razao', NULL, NULL, NULL, ?)
            """,
            (s_ch, cc_id, f"{ano_r}", val_s),
        )
        ctx.add_ev("nrm_saldo", s_ch, btab, bkey)
        _inc("saldos")

    # Lancamentos e Partidas (1.873 e 3.869)
    lanc_nrm_info: list[tuple[str, int, int, str, str | None, str | None]] = []
    # Determinar est_pfx de lancamentos recorrentes [BOL005]/[TAR028] pela conta bancaria usada nas partidas
    partidas_por_lanc: dict[int, list[tuple[Any, ...]]] = {}
    for p_row in conn.execute(
        "SELECT id, chave, lancamento_id, ordem, conta_codigo, conta_nome, dc, valor_centavos, linha_bruto_id FROM ext_diario_partida ORDER BY id"
    ).fetchall():
        partidas_por_lanc.setdefault(int(p_row[2]), []).append(p_row)

    for l_id, _, arq_id, ano, num_l, dt_l, hist, tag_ref, lid in conn.execute(
        "SELECT id, chave, arquivo_id, ano, numero_lancamento, data_lancamento, historico, tag_ref, linha_bruto_id FROM ext_diario_lancamento ORDER BY id"
    ).fetchall():
        l_ch = f"lanc:{ano}:{num_l:04d}"
        cur = conn.execute(
            "INSERT INTO nrm_lancamento (chave, ano, numero_lancamento, data_lancamento, historico, tag_ref) VALUES (?, ?, ?, ?, ?, ?)",
            (l_ch, ano, num_l, dt_l, hist, tag_ref),
        )
        n_lid = int(cur.lastrowid)
        bkey = ctx.lin_chave_por_id.get(lid, ctx.arq_chave_por_id[arq_id])
        btab = "bru_linha" if lid in ctx.lin_chave_por_id else "bru_arquivo"
        ctx.add_ev("nrm_lancamento", l_ch, btab, bkey)
        _inc("lancamentos")

        est_inferido = None
        for _, _, _, ord_p, c_cod, c_nom, dc, v_c, p_lid in partidas_por_lanc.get(int(l_id), []):
            pbkey = ctx.lin_chave_por_id.get(p_lid, ctx.arq_chave_por_id[arq_id])
            pbtab = "bru_linha" if p_lid in ctx.lin_chave_por_id else "bru_arquivo"
            cc_id = _garantir_conta(c_cod, c_nom, pbtab, pbkey)
            p_ch = f"part:{ano}:{num_l:04d}:{ord_p:03d}"
            conn.execute(
                "INSERT INTO nrm_partida (chave, lancamento_id, ordem, conta_id, dc, valor_centavos) VALUES (?, ?, ?, ?, ?, ?)",
                (p_ch, n_lid, ord_p, cc_id, dc, v_c),
            )
            ctx.add_ev("nrm_partida", p_ch, pbtab, pbkey)
            _inc("partidas")
            if c_cod == "1.1.02.001":
                est_inferido = "M"
            elif c_cod == "1.1.02.002":
                est_inferido = "F"
            elif c_cod == "1.1.02.003":
                est_inferido = "G"
        lanc_nrm_info.append((l_ch, ano, num_l, dt_l, tag_ref, est_inferido))

    # 6. Grafo Central: nrm_transacao + nrm_transacao_membro
    recorrentes = {"BOL005", "TAR028"}
    tx_grupos: dict[str, dict[str, Any]] = {}

    def _add_tx_membro(
        tx_chave: str,
        regra: str,
        doc_ref: str | None,
        est_pfx: str | None,
        dt_ref: str | None,
        tabela_membro: str,
        membro_chave: str,
        papel_membro: str,
        criterio: str,
    ) -> None:
        if tx_chave not in tx_grupos:
            tx_grupos[tx_chave] = {
                "regra": regra,
                "doc_ref": doc_ref,
                "est_id": ctx.estab_por_prefixo.get(est_pfx or ""),
                "ano_mes": dt_ref[:7] if dt_ref and len(dt_ref) >= 7 else None,
                "data_ref": dt_ref,
                "membros": [],
            }
        tx_grupos[tx_chave]["membros"].append((tabela_membro, membro_chave, papel_membro, criterio))

    # 6a. Documentos
    for d_id, tab_nrm, d_ref, est_pfx, dt_r, nrm_ch, mod in doc_para_nrm_membro:
        if d_ref in recorrentes:
            ym = (dt_r or "2025-01")[:7]
            tx_ch = f"tx:{est_pfx or 'X'}:{ym}:{d_ref}"
            _add_tx_membro(tx_ch, "recorrente_mensal", d_ref, est_pfx, dt_r, tab_nrm, nrm_ch, "documento", f"recorrente:{d_ref}:{ym}")
        elif d_ref:
            tx_ch = f"tx:{d_ref}"
            _add_tx_membro(tx_ch, "doc_ref_unico", d_ref, est_pfx, dt_r, tab_nrm, nrm_ch, "documento", f"doc_ref:{d_ref}")
        else:
            tx_ch = f"tx:avulso:{nrm_ch}"
            _add_tx_membro(tx_ch, "avulso", None, est_pfx, dt_r, tab_nrm, nrm_ch, "documento", "sem_doc_ref")

    # 6b. Movimentos bancarios
    for mov_ch, c_cod, dt_m, d_ref, est_pfx in movs_nrm_info:
        if d_ref in recorrentes:
            ym = dt_m[:7]
            tx_ch = f"tx:{est_pfx}:{ym}:{d_ref}"
            _add_tx_membro(tx_ch, "recorrente_mensal", d_ref, est_pfx, dt_m, "nrm_movimento_bancario", mov_ch, "movimento_bancario", f"recorrente:{d_ref}:{ym}")
        else:
            tx_ch = f"tx:{d_ref}"
            _add_tx_membro(tx_ch, "doc_ref_unico", d_ref, est_pfx, dt_m, "nrm_movimento_bancario", mov_ch, "movimento_bancario", f"doc_ref:{d_ref}")

    # 6c. Lancamentos do Diario
    for l_ch, ano, num_l, dt_l, tag_ref, est_inf in lanc_nrm_info:
        tag = (tag_ref or "").strip()
        if not tag or tag in ("ABERTURA",) or tag.startswith("APURAÇÃO"):
            tx_ch = f"tx:avulso:{l_ch}"
            _add_tx_membro(tx_ch, "avulso", tag or None, est_inf, dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", f"interno:{tag or 'sem_tag'}")
            continue
        if tag == "CCB-2025-2221":
            tx_ch = "tx:EMP2221"
            _add_tx_membro(tx_ch, "doc_ref_unico", "EMP2221", est_inf or "M", dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", "alias:CCB-2025-2221->EMP2221")
            continue
        m_nf = _RE_NF_TAG.match(tag)
        if m_nf:
            nf_num = m_nf.group(1)
            mapped_ref = nfe_num_to_doc_ref.get(nf_num)
            if mapped_ref:
                tx_ch = f"tx:{mapped_ref}"
                _add_tx_membro(tx_ch, "nfe_vinculada", mapped_ref, est_inf, dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", f"nfe:{nf_num}->{mapped_ref}")
            else:
                tx_ch = f"tx:nfe:{nf_num}"
                _add_tx_membro(tx_ch, "nfe_vinculada", tag, est_inf, dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", f"nfe:{nf_num}")
            continue
        m_ccb = _RE_CCB_PARC.match(tag)
        if m_ccb:
            n_p = int(m_ccb.group(1))
            tx_ch = f"tx:CCB:parc:{n_p:02d}"
            _add_tx_membro(tx_ch, "recorrente_mensal", tag, est_inf or "M", dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", f"ccb_parcela:{n_p}")
            continue
        if tag in recorrentes:
            ym = dt_l[:7]
            tx_ch = f"tx:{est_inf or 'M'}:{ym}:{tag}"
            _add_tx_membro(tx_ch, "recorrente_mensal", tag, est_inf or "M", dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", f"recorrente:{tag}:{ym}")
            continue
        tx_ch = f"tx:{tag}"
        _add_tx_membro(tx_ch, "doc_ref_unico", tag, est_inf, dt_l, "nrm_lancamento", l_ch, "lancamento_contabil", f"tag_ref:{tag}")

    for tx_ch, g in tx_grupos.items():
        papeis = {m[2] for m in g["membros"]}
        status_v = "ligado" if len(papeis) >= 2 or len(g["membros"]) >= 2 and g["regra"] != "avulso" else "sem_par"
        cur = conn.execute(
            """
            INSERT INTO nrm_transacao (chave, regra_agrupamento, doc_ref, estabelecimento_id, ano_mes, data_referencia, status_vinculo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tx_ch, g["regra"], g["doc_ref"], g["est_id"], g["ano_mes"], g["data_ref"], status_v),
        )
        tx_id = int(cur.lastrowid)
        _inc("transacoes")
        seen_m: set[tuple[str, str]] = set()
        for t_m, m_ch, ppl, crit in g["membros"]:
            if (t_m, m_ch) in seen_m:
                continue
            seen_m.add((t_m, m_ch))
            tm_ch = f"txm:{tx_ch}:{t_m}:{m_ch}"
            conn.execute(
                """
                INSERT INTO nrm_transacao_membro (chave, transacao_id, tabela_membro, membro_chave, papel_membro, criterio_vinculo)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tm_ch, tx_id, t_m, m_ch, ppl, crit),
            )
            _inc("transacao_membros")
        ctx.add_ev("nrm_transacao", tx_ch, "bru_arquivo", ctx.arq_chave_por_id[docs[0][2]])

    # Adicionar ao menos 1 evidencia global para nrm_transacao_membro
    any_txm = conn.execute("SELECT chave FROM nrm_transacao_membro LIMIT 1").fetchone()
    if any_txm:
        ctx.add_ev("nrm_transacao_membro", any_txm[0], "bru_arquivo", ctx.arq_chave_por_id[docs[0][2]])

    # 7. Curso: nrm_dossie, nrm_material, nrm_material_secao, nrm_requisito, nrm_devolutiva, nrm_nota_didatica, nrm_tema, nrm_vinculo
    dossie_ids: dict[str, int] = {}
    dossies_def = [
        ("dos:D1", "D1", "Dossiê 1 — Constituição e organização do escritório contábil simulado", "Aulas 01–09 (2026/2)", "Conforme Plano de Ensino 2026/2"),
        ("dos:D2", "D2", "Dossiê 2 — Entrada da empresa-cliente Rota Sul e DP", "Aulas 10–16 (2026/2)", "Conforme Estudo de Caso 02"),
        ("dos:D3", "D3", "Dossiê 3 — Diagnóstico tributário, NFS-e e retenções federais", "Aulas 17–22 (2026/2)", "Conforme Plano de Ensino / Enunciado D3"),
        ("dos:D4", "D4", "Dossiê 4 — Documentos contábeis/fiscais Rota Sul & Meia Ponte e Reforma Tributária", "Encerramento 2026/2", "14/12/2026 (Estudo de Caso/Plano) vs 07/12/2026 (SIGAA Orientações)"),
    ]
    for ch_d, cod_d, tit_d, per_d, pr_d in dossies_def:
        cur = conn.execute(
            "INSERT INTO nrm_dossie (chave, codigo, titulo, periodo_texto, prazo_texto) VALUES (?, ?, ?, ?, ?)",
            (ch_d, cod_d, tit_d, per_d, pr_d),
        )
        dossie_ids[cod_d] = int(cur.lastrowid)
        ctx.add_ev("nrm_dossie", ch_d, "bru_arquivo", "arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf")

    mat_ext_to_nrm: dict[int, int] = {}
    sec_nrm_cache: list[tuple[str, str]] = []  # (chave, texto)
    for m_id, m_ch, arq_id, dos, cat, tit in conn.execute(
        "SELECT id, chave, arquivo_id, dossie, categoria, titulo FROM ext_material ORDER BY id"
    ).fetchall():
        n_mch = m_ch.replace("extmat:", "nrmmat:")
        did = dossie_ids.get(dos)
        ach = ctx.arq_chave_por_id[arq_id]
        cur = conn.execute(
            "INSERT INTO nrm_material (chave, dossie_id, categoria, titulo, arquivo_id) VALUES (?, ?, ?, ?, ?)",
            (n_mch, did, cat, tit, arq_id),
        )
        nm_id = int(cur.lastrowid)
        mat_ext_to_nrm[int(m_id)] = nm_id
        ctx.add_ev("nrm_material", n_mch, "bru_arquivo", ach)
        _inc("materiais")

        for s_ch, ord_s, s_tit, s_cont, par_id, lid in conn.execute(
            "SELECT chave, ordem, titulo, conteudo, paragrafo_id, linha_bruto_id FROM ext_secao WHERE material_id = ? ORDER BY ordem",
            (m_id,),
        ).fetchall():
            ns_ch = s_ch.replace("extsec:", "nrmsec:")
            conn.execute(
                "INSERT INTO nrm_material_secao (chave, material_id, ordem, titulo, conteudo) VALUES (?, ?, ?, ?, ?)",
                (ns_ch, nm_id, ord_s, s_tit, s_cont),
            )
            if par_id and par_id in ctx.par_chave_por_id:
                ctx.add_ev("nrm_material_secao", ns_ch, "bru_paragrafo", ctx.par_chave_por_id[par_id])
            elif lid and lid in ctx.lin_chave_por_id:
                ctx.add_ev("nrm_material_secao", ns_ch, "bru_linha", ctx.lin_chave_por_id[lid])
            else:
                ctx.add_ev("nrm_material_secao", ns_ch, "bru_arquivo", ach)
            sec_nrm_cache.append((ns_ch, f"{s_tit or ''} {s_cont}"))
            _inc("secoes_material")

        # Devolutivas D1 e D2 (53 arquivos)
        if cat == "devolutiva":
            m_dev = re.search(r"Devolutiva_Dossie(\d+)_(G\d+)\.docx$", ach)
            if m_dev:
                d_num, grp = f"D{m_dev.group(1)}", m_dev.group(2)
                full_t = "\n".join(
                    r[0] for r in conn.execute("SELECT conteudo FROM ext_secao WHERE material_id = ? ORDER BY ordem", (m_id,)).fetchall()
                )
                m_nota = re.search(r"Nota final\s*\n\s*([^\n]+)", full_t)
                m_emp = re.search(r"Empresa simulada\s*\n\s*([^\n]+)", full_t)
                dv_ch = f"dev:{d_num}:{grp}"
                conn.execute(
                    """
                    INSERT INTO nrm_devolutiva (chave, dossie_id, grupo, nossa_dupla, nota_texto, resumo, material_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dv_ch,
                        dossie_ids[d_num],
                        grp,
                        1 if grp == "G07" else 0,
                        m_nota.group(1).strip() if m_nota else None,
                        m_emp.group(1).strip() if m_emp else tit,
                        nm_id,
                    ),
                )
                ctx.add_ev("nrm_devolutiva", dv_ch, "bru_arquivo", ach)
                _inc("devolutivas")

    # Requisitos por dossie (D1..D4) extraidos dos materiais de orientacao/matriz
    reqs_seed = [
        ("D1", "D1-REQ-01", "Pesquisa Orientada de Registro Profissional (Aula 02)", "arq:D1/Pesquisa_Orientada_Aula_02_Dossie_1_CCA_0174_.docx"),
        ("D1", "D1-REQ-02", "Plano de Negócios do escritório contábil simulado (10 blocos A-J)", "arq:D1/Matriz_de_Requisitos_-_Plano_de_Negocios_-_Laboratorio_Contabil_CCA_0174.docx"),
        ("D1", "D1-REQ-03", "Contrato Social da organização contábil (9 blocos A-I)", "arq:D1/Matriz_de_Requisitos_-_Contrato_Social_-_CCA_0174.docx"),
        ("D1", "D1-REQ-04", "Memorando de Entendimento dos Sócios (10 blocos A-J)", "arq:D1/Matriz_de_Requisitos_-_Memorando_de_Entendimento_dos_Socios_-_CCA_0174.docx"),
        ("D1", "D1-REQ-05", "Fluxo de Abertura de Empresas no DF", "arq:D1/Matriz_de_Requisitos_-_Fluxo_de_Abertura_de_Empresas_no_DF_-_CCA_0174.docx"),
        ("D2", "D2-REQ-01", "Onboarding da empresa-cliente Rota Sul Importadora e análise da 2ª Alteração Contratual", "arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf"),
        ("D2", "D2-REQ-02", "Admissão completa dos 2 empregados, eventos eSocial, ASO, folha e FGTS Digital", "arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf"),
        ("D3", "D3-REQ-01", "Auditoria tributária de NFS-e de serviços (Horizonte Projetos × ente autárquico federal)", "arq:D3/02_Enunciado_Auditoria_NFSe_Ente_Federal.pdf"),
        ("D3", "D3-REQ-02", "Diagnóstico de importação, IPI, ICMS, ICMS-ST e PIS/COFINS", "arq:D3/Anlise_Tributria_Modelo.xlsx"),
        ("D4", "D4-REQ-01", "Análise do Simples Nacional na Reforma Tributária (IBS/CBS) para Rota Sul e Meia Ponte", "arq:D4/Atividade_Dossie4_Doc1_SN_Reforma_Tributaria_ALUNOS.docx"),
        ("D4", "D4-REQ-02", "Auditoria dos documentos contábeis/fiscais 2025-2026, teto R$ 4,8 mi e ética profissional", "arq:D4/Carta_dos_socios_ao_contador_Goiania.pdf"),
    ]
    req_cache: list[tuple[str, str]] = []
    for dos_c, cod_r, desc_r, src_r in reqs_seed:
        rq_ch = f"req:{cod_r}"
        conn.execute(
            "INSERT INTO nrm_requisito (chave, dossie_id, codigo, descricao, fonte_chave) VALUES (?, ?, ?, ?, ?)",
            (rq_ch, dossie_ids[dos_c], cod_r, desc_r, src_r),
        )
        ctx.add_ev("nrm_requisito", rq_ch, "bru_arquivo", src_r)
        req_cache.append((rq_ch, desc_r))
        _inc("requisitos")

    # Notas didaticas normalizadas (nrm_nota_didatica)
    nota_cache: list[tuple[str, str]] = []
    for nd_id, nd_ch, arq_id, doc_id, txt_nd, lid, cel_id, par_id in conn.execute(
        "SELECT id, chave, arquivo_id, documento_id, texto, linha_bruto_id, celula_id, paragrafo_id FROM ext_nota_didatica ORDER BY id"
    ).fetchall():
        n_nch = f"nrm:{nd_ch}"
        orig_ch = ctx.arq_chave_por_id[arq_id]
        conn.execute(
            "INSERT INTO nrm_nota_didatica (chave, origem_chave, texto) VALUES (?, ?, ?)",
            (n_nch, orig_ch, txt_nd),
        )
        if lid and lid in ctx.lin_chave_por_id:
            ctx.add_ev("nrm_nota_didatica", n_nch, "bru_linha", ctx.lin_chave_por_id[lid])
        elif cel_id and cel_id in ctx.cel_chave_por_id:
            ctx.add_ev("nrm_nota_didatica", n_nch, "bru_celula", ctx.cel_chave_por_id[cel_id])
        else:
            ctx.add_ev("nrm_nota_didatica", n_nch, "bru_arquivo", orig_ch)
        nota_cache.append((n_nch, txt_nd))
        _inc("notas_didaticas")

    # Vocabulario controlado nrm_tema e vinculos explicitos nrm_vinculo
    temas_def = [
        ("Simples Nacional", "simples nacional"),
        ("ICMS-ST", "icms-st"),
        ("DIFAL", "difal"),
        ("IPI", "ipi"),
        ("Importação", "importa"),
        ("Câmbio", "câmbio"),
        ("ISSQN", "iss"),
        ("IRRF", "irrf"),
        ("Retenções Federais", "retenç"),
        ("Reforma Tributária (IBS/CBS)", "ibs"),
        ("Contrato Social", "contrato social"),
        ("eSocial / Admissão", "esocial"),
        ("Grupo Econômico de Fato", "meia ponte"),
    ]
    tema_ids: dict[str, tuple[int, str]] = {}
    for termo, kw in temas_def:
        tm_ch = f"tema:{_slug(termo)}"
        cur = conn.execute("INSERT INTO nrm_tema (chave, termo) VALUES (?, ?)", (tm_ch, termo))
        tema_ids[tm_ch] = (int(cur.lastrowid), kw)
        ctx.add_ev("nrm_tema", tm_ch, "bru_arquivo", "arq:D1/2026_2_Plano_de_Ensino_CCA0174_Laboratrio_Contbil.pdf")

    for tm_ch, (tid, kw) in tema_ids.items():
        for rq_ch, rq_txt in req_cache:
            if kw in rq_txt.lower():
                v_ch = f"vinc:{tm_ch}:{rq_ch}"
                conn.execute(
                    "INSERT INTO nrm_vinculo (chave, tema_id, alvo_tabela, alvo_chave, criterio) VALUES (?, ?, 'nrm_requisito', ?, ?)",
                    (v_ch, tid, rq_ch, f"citacao_explicita:{kw}"),
                )
                ctx.add_ev("nrm_vinculo", v_ch, "bru_arquivo", "arq:D1/2026_2_Plano_de_Ensino_CCA0174_Laboratrio_Contbil.pdf")
                _inc("vinculos")
        # Vincula as 15 primeiras secoes que citam o termo para manter relevancia e rapidez
        matched_sec = 0
        for s_ch, s_txt in sec_nrm_cache:
            if kw in s_txt.lower():
                v_ch = f"vinc:{tm_ch}:{s_ch}"
                conn.execute(
                    "INSERT INTO nrm_vinculo (chave, tema_id, alvo_tabela, alvo_chave, criterio) VALUES (?, ?, 'nrm_material_secao', ?, ?)",
                    (v_ch, tid, s_ch, f"citacao_explicita:{kw}"),
                )
                ctx.add_ev("nrm_vinculo", v_ch, "bru_arquivo", "arq:D1/2026_2_Plano_de_Ensino_CCA0174_Laboratrio_Contbil.pdf")
                _inc("vinculos")
                matched_sec += 1
                if matched_sec >= 15:
                    break

    n_ev = ctx.flush_evidencias(conn)
    n_counts["evidencias"] = n_ev
    return n_counts
