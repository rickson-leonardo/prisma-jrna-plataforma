"""Camada 2 (Fase 2) — Motor declarativo de extracao dos 51 modelos de PDF do D4."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from sistema.extracao.livros import parse_data_iso, parse_moeda_centavos
from sistema.extracao.modelos import CATALOGO_MODELOS
from sistema.extracao.modelos.base import SpecModelo

_MESES_EN = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}
_MESES_PT = {
    "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03", "abril": "04",
    "maio": "05", "junho": "06", "julho": "07", "agosto": "08", "setembro": "09",
    "outubro": "10", "novembro": "11", "dezembro": "12",
}

_RE_ARQUIVO_D4 = re.compile(r"^([MFG]|NF)\d+_(\d{4}-\d{2}-\d{2})_([A-Z0-9]+)_(\d+)_(.+?)\.pdf$")
_RE_DATA_INICIO = re.compile(r"(\d{2}/\d{2}/\d{4})")
_RE_DATA_EN = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$")
_RE_USD = re.compile(r"(?:USD|US\$)\s*([\d,]+\.\d{2})")
_RE_BRL = re.compile(r"R\$\s*([\d\.]+,\d{2})")
_RE_PCT = re.compile(r"(\d+[\.,]\d+)\s*%")


@dataclass
class _LinhaPDF:
    id: int
    chave: str
    pagina: int
    n_linha: int
    texto: str
    x0: float
    y0: float
    tam_fonte: float
    fonte: str
    cor_hex: str
    eh_marca_dagua: int


def parse_nome_arquivo_d4(nome: str) -> tuple[str, str | None, str | None, str | None]:
    """Retorna (modelo, est_prefixo, data_ref, doc_ref) a partir do nome do arquivo D4."""
    if nome == "Carta_dos_socios_ao_contador_Goiania.pdf":
        return "Carta-socios-Goiania", None, "2026-09-14", None
    m = _RE_ARQUIVO_D4.match(nome)
    if not m:
        raise ValueError(f"Nome de arquivo D4 fora do padrao esperado: {nome}")
    est_prefixo, data_ref, doc_ref, _, tail = m.groups()
    modelo = re.sub(r"-(?:\d[\d\-A-Za-z]*|202\d.*)$", "", tail)
    return modelo, est_prefixo, data_ref, doc_ref


def _parse_valor_campo(texto: str, moeda_padrao: str = "BRL") -> tuple[int | None, str | None, int | None, str | None]:
    """Extrai (valor_centavos, moeda, valor_micro, valor_data) de um texto de campo."""
    s = texto.strip()
    valor_data: str | None = None
    m_dt = _RE_DATA_INICIO.search(s)
    if m_dt:
        valor_data = parse_data_iso(m_dt.group(1))
    else:
        m_en = _RE_DATA_EN.match(s)
        if m_en:
            mes = _MESES_EN.get(m_en.group(2).lower())
            if mes:
                valor_data = f"{m_en.group(3)}-{mes}-{int(m_en.group(1)):02d}"

    valor_centavos: int | None = None
    moeda: str | None = None
    m_brl = _RE_BRL.search(s)
    m_usd = _RE_USD.search(s)
    if m_brl:
        valor_centavos = parse_moeda_centavos(m_brl.group(1))
        moeda = "BRL"
    elif m_usd:
        valor_centavos = round(float(m_usd.group(1).replace(",", "")) * 100)
        moeda = "USD"
    elif moeda_padrao == "USD" and re.match(r"^[\d,]+\.\d{2}$", s):
        valor_centavos = round(float(s.replace(",", "")) * 100)
        moeda = "USD"
    else:
        c = parse_moeda_centavos(s)
        if c is not None:
            valor_centavos = c
            moeda = moeda_padrao

    valor_micro: int | None = None
    m_pct = _RE_PCT.search(s)
    if m_pct:
        valor_micro = round(float(m_pct.group(1).replace(",", ".")) * 10_000)
    elif re.match(r"^\d+\.\d{4}$", s):
        valor_micro = round(float(s) * 1_000_000)

    return valor_centavos, moeda, valor_micro, valor_data


def _extrair_campos_prosa(
    modelo: str, texto_completo: str
) -> list[tuple[str, str, int | None, str | None, int | None, str | None]]:
    """Extrai campos estruturados dos documentos em prosa (recibos e carta)."""
    campos: list[tuple[str, str, int | None, str | None, int | None, str | None]] = []

    m_val = _RE_BRL.search(texto_completo)
    if m_val:
        vc = parse_moeda_centavos(m_val.group(1))
        campos.append(("VALOR", f"R$ {m_val.group(1)}", vc, "BRL", None, None))

    m_num = re.search(r"Nº\s*([0-9/.\-]+)", texto_completo)
    if m_num:
        campos.append(("NUMERO", m_num.group(1), None, None, None, None))

    m_ref = re.search(r"(?:Doc/Ref|boleto)\s+([A-Z0-9]+)", texto_completo)
    if m_ref:
        campos.append(("DOC_REF", m_ref.group(1), None, None, None, None))

    m_comp = re.search(r"competência\s+([a-zç]+/\d{4}|\d{2}/\d{4})|mês\s+(\d{2}/\d{4})", texto_completo, re.I)
    if m_comp:
        comp = m_comp.group(1) or m_comp.group(2)
        campos.append(("COMPETENCIA", comp, None, None, None, None))

    # Data por extenso (ex.: 14 de setembro de 2026) ou DD/MM/YYYY
    m_ext = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", texto_completo, re.I)
    if m_ext:
        mes_n = _MESES_PT.get(m_ext.group(2).lower())
        if mes_n:
            dt_iso = f"{m_ext.group(3)}-{mes_n}-{int(m_ext.group(1)):02d}"
            campos.append(("DATA_EMISSAO", m_ext.group(0), None, None, None, dt_iso))
    else:
        datas = _RE_DATA_INICIO.findall(texto_completo)
        if datas:
            dt_iso = parse_data_iso(datas[-1])
            campos.append(("DATA_EMISSAO", datas[-1], None, None, None, dt_iso))

    for i, doc_id in enumerate(re.findall(r"(?:CNPJ|CPF)\s+([\d.\-/]+)", texto_completo), start=1):
        campos.append((f"IDENTIFICADOR_{i}", doc_id, None, None, None, None))

    return campos


def _carregar_linhas_pdf(conn: sqlite3.Connection, arq_id: int) -> list[_LinhaPDF]:
    rows = conn.execute(
        """
        SELECT id, chave, pagina, n_linha, texto, x0, y0, tam_fonte, fonte, cor_hex, eh_marca_dagua
        FROM bru_linha
        WHERE arquivo_id = ?
        ORDER BY pagina, n_linha
        """,
        (arq_id,),
    ).fetchall()
    return [
        _LinhaPDF(
            id=int(r[0]),
            chave=str(r[1]),
            pagina=int(r[2]),
            n_linha=int(r[3]),
            texto=str(r[4]),
            x0=float(r[5]),
            y0=float(r[6]),
            tam_fonte=float(r[7]),
            fonte=str(r[8] or ""),
            cor_hex=str(r[9] or ""),
            eh_marca_dagua=int(r[10]),
        )
        for r in rows
    ]


def _eh_cabecalho_tabela(ln: _LinhaPDF) -> bool:
    return ln.cor_hex == "0x1d2433" and ln.tam_fonte == 7.0 and "Bold" in ln.fonte


def _eh_rotulo(ln: _LinhaPDF) -> bool:
    return ln.cor_hex == "0x5a6477" and ln.tam_fonte == 6.3


def _eh_nota_didatica(ln: _LinhaPDF) -> bool:
    return ln.cor_hex == "0x5a6477" and ln.tam_fonte == 6.9


def _eh_secao(ln: _LinhaPDF) -> bool:
    return ln.cor_hex == "0xffffff" and ln.tam_fonte == 6.5 and ln.y0 >= 75.0


def _eh_valor(ln: _LinhaPDF) -> bool:
    return ln.cor_hex in ("0x1d2433", "0x12355b")


def _processar_documento(
    conn: sqlite3.Connection,
    arq_id: int,
    rel: str,
    nome: str,
    spec: SpecModelo,
    est_prefixo: str | None,
    data_ref: str | None,
    doc_ref: str | None,
) -> tuple[int, int, int]:
    linhas = _carregar_linhas_pdf(conn, arq_id)
    chave_doc = f"extdoc:{rel}:1"
    cur_doc = conn.execute(
        """
        INSERT INTO ext_documento (
            chave, arquivo_id, modelo, tipo, data_referencia, doc_ref, estabelecimento_prefixo, moeda
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (chave_doc, arq_id, spec.nome, spec.tipo, data_ref, doc_ref, est_prefixo, spec.moeda_padrao),
    )
    doc_id = int(cur_doc.lastrowid)

    updates: list[tuple[str, int]] = []
    campos_extraidos: list[tuple[str, str, int | None, str | None, int | None, str | None]] = []
    itens_extraidos: list[dict[str, str]] = []
    n_campos = 0
    n_itens = 0
    n_notas = 0
    campo_seq = 0
    nota_seq = 0
    tabelas_usadas: dict[str, int] = {}

    def _add_campo(
        secao: str,
        rotulo: str,
        valor_texto: str,
        linha_id: int,
        moeda_hint: str | None = None,
    ) -> None:
        nonlocal n_campos, campo_seq
        campo_seq += 1
        vc, md, vm, vd = _parse_valor_campo(valor_texto, moeda_hint or spec.moeda_padrao)
        campos_extraidos.append((rotulo, valor_texto, vc, md, vm, vd))
        conn.execute(
            """
            INSERT INTO ext_campo (
                chave, documento_id, secao, rotulo, valor_texto,
                valor_centavos, moeda, valor_micro, valor_data, linha_bruto_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"extcmp:{rel}:{campo_seq}",
                doc_id,
                secao,
                rotulo,
                valor_texto,
                vc,
                md,
                vm,
                vd,
                linha_id,
            ),
        )
        n_campos += 1

    por_pagina: dict[int, list[_LinhaPDF]] = {}
    for ln in linhas:
        por_pagina.setdefault(ln.pagina, []).append(ln)

    secao_atual = "GERAL"
    tabela_ativa: tuple[str, list[tuple[str, float]]] | None = None
    n_linha_tabela = 0
    corpo_prosa_linhas: list[tuple[str, int]] = []
    rodape_prosa_atingido = False

    for pag in sorted(por_pagina):
        p_linhas = por_pagina[pag]
        idx = 0
        while idx < len(p_linhas):
            ln = p_linhas[idx]
            if ln.eh_marca_dagua:
                idx += 1
                continue
            txt = ln.texto.strip()

            # 1. Nota didatica (0x5a6477, 6.9pt)
            if _eh_nota_didatica(ln):
                tabela_ativa = None
                grupo_nota = [ln]
                j = idx + 1
                while j < len(p_linhas) and not p_linhas[j].eh_marca_dagua and _eh_nota_didatica(p_linhas[j]):
                    grupo_nota.append(p_linhas[j])
                    j += 1
                nota_seq += 1
                texto_nota = " ".join(x.texto.strip() for x in grupo_nota if x.texto.strip())
                conn.execute(
                    """
                    INSERT INTO ext_nota_didatica (chave, arquivo_id, documento_id, texto, linha_bruto_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (f"nota:{rel}:{nota_seq}", arq_id, doc_id, texto_nota, grupo_nota[0].id),
                )
                for x in grupo_nota:
                    updates.append((f"ext_nota_didatica:{spec.nome}", x.id))
                n_notas += 1
                idx = j
                continue

            # 2. Secao de documento (0xffffff, 6.5pt)
            if _eh_secao(ln):
                tabela_ativa = None
                secao_atual = txt
                updates.append((f"secao_doc:{spec.nome}:{secao_atual}", ln.id))
                idx += 1
                continue

            # 3. Cabecalho de tabela (0x1d2433, 7.0pt Bold)
            if _eh_cabecalho_tabela(ln):
                y_base = ln.y0
                hdr_lines = [ln]
                j = idx + 1
                while j < len(p_linhas):
                    nxt = p_linhas[j]
                    if nxt.eh_marca_dagua:
                        j += 1
                        continue
                    if _eh_cabecalho_tabela(nxt) and abs(nxt.y0 - y_base) <= 18.0:
                        hdr_lines.append(nxt)
                        j += 1
                    else:
                        break
                # Agrupar headers multi-linha por x0 proximo (<= 12pt)
                colunas: list[tuple[str, float]] = []
                for h in hdr_lines:
                    ht = h.texto.strip()
                    merged = False
                    for c_i, (c_nome, c_x0) in enumerate(colunas):
                        if abs(h.x0 - c_x0) <= 12.0 and h.y0 > y_base + 2.0:
                            colunas[c_i] = (f"{c_nome} {ht}".strip(), c_x0)
                            merged = True
                            break
                    if not merged:
                        colunas.append((ht, h.x0))

                base_tbl = secao_atual or "TABELA"
                tabelas_usadas[base_tbl] = tabelas_usadas.get(base_tbl, 0) + 1
                nome_tbl = base_tbl if tabelas_usadas[base_tbl] == 1 else f"{base_tbl}_{tabelas_usadas[base_tbl]}"
                tabela_ativa = (nome_tbl, colunas)
                n_linha_tabela = 0
                for h in hdr_lines:
                    if not h.eh_marca_dagua:
                        updates.append((f"cabecalho_tabela:{spec.nome}:{nome_tbl}", h.id))
                idx = j
                continue

            # 4. Rotulo de campo (0x5a6477, 6.3pt)
            if _eh_rotulo(ln):
                tabela_ativa = None
                rot_lines = [ln]
                j = idx + 1
                while j < len(p_linhas):
                    nxt = p_linhas[j]
                    if nxt.eh_marca_dagua:
                        j += 1
                        continue
                    if _eh_rotulo(nxt) and abs(nxt.x0 - ln.x0) <= 4.0 and 0.0 < nxt.y0 - rot_lines[-1].y0 <= 12.0:
                        rot_lines.append(nxt)
                        j += 1
                    else:
                        break
                rotulo = " ".join(r.texto.strip() for r in rot_lines)

                # Coletar linhas de valor associadas (antes do proximo rotulo/secao/tabela/nota/assinatura)
                val_lines: list[_LinhaPDF] = []
                while j < len(p_linhas):
                    nxt = p_linhas[j]
                    if nxt.eh_marca_dagua:
                        j += 1
                        continue
                    if (
                        _eh_rotulo(nxt)
                        or _eh_secao(nxt)
                        or _eh_cabecalho_tabela(nxt)
                        or _eh_nota_didatica(nxt)
                        or nxt.texto.strip().startswith("_____")
                    ):
                        break
                    # Em tabelas de calculo (ex.: Contrato-cambio / DARE), a secao pode ter headers logo apos um rotulo? Nao, aqui sao valores do rotulo
                    if not _eh_valor(nxt):
                        break
                    # Se mudou muito a coordenada x0 para outro bloco antes de outro rotulo? No layout, valores vem logo apos o rotulo em ordem
                    val_lines.append(nxt)
                    j += 1

                val_texto = " ".join(v.texto.strip() for v in val_lines).strip()
                if val_texto:
                    _add_campo(secao_atual, rotulo, val_texto, val_lines[0].id)
                dest_cmp = f"ext_campo:{spec.nome}:{rotulo}"
                for r_ln in rot_lines:
                    updates.append((dest_cmp, r_ln.id))
                for v_ln in val_lines:
                    updates.append((dest_cmp, v_ln.id))
                idx = j
                continue

            # 5. Bloco de assinatura
            if txt.startswith("_____"):
                tabela_ativa = None
                rodape_prosa_atingido = True
                sig_lines = [ln]
                j = idx + 1
                while j < len(p_linhas):
                    nxt = p_linhas[j]
                    if nxt.eh_marca_dagua:
                        j += 1
                        continue
                    if _eh_nota_didatica(nxt) or _eh_secao(nxt) or _eh_rotulo(nxt):
                        break
                    if nxt.texto.strip().startswith("_____"):
                        sig_lines.append(nxt)
                        j += 1
                        continue
                    # Linhas curtas logo abaixo da linha de assinatura
                    if abs(nxt.x0 - ln.x0) <= 60.0 or nxt.y0 - sig_lines[-1].y0 <= 20.0:
                        sig_lines.append(nxt)
                        j += 1
                    else:
                        break
                assinante = " | ".join(s.texto.strip() for s in sig_lines if not s.texto.strip().startswith("_____"))
                if assinante:
                    _add_campo("ASSINATURA", "ASSINANTE", assinante, sig_lines[0].id)
                for s_ln in sig_lines:
                    updates.append((f"assinatura:{spec.nome}", s_ln.id))
                idx = j
                continue

            # 6. Dentro de uma tabela ativa
            if tabela_ativa is not None and _eh_valor(ln):
                nome_tbl, colunas = tabela_ativa
                # Se encontrou linha de total/desconto, agrupar pelo y0 e encerrar tabela (exceto se for Subtotal seguido de outro item/total na mesma tabela)
                y_row = ln.y0
                row_cells = [ln]
                j = idx + 1
                while j < len(p_linhas):
                    nxt = p_linhas[j]
                    if nxt.eh_marca_dagua:
                        j += 1
                        continue
                    if _eh_valor(nxt) and abs(nxt.y0 - y_row) <= 2.5:
                        row_cells.append(nxt)
                        j += 1
                    else:
                        break

                row_text_full = " ".join(c.texto.strip() for c in row_cells)
                # Verifica se e uma linha fora da tabela (ex.: paragrafo longo explicativo abaixo da tabela, x0 <= 32 e nao e linha de total)
                eh_linha_total = any(
                    kw in row_text_full.upper()
                    for kw in ("TOTAL", "TOTAIS", "SUBTOTAL", "LESS:", "(=)", "(+)")
                )
                eh_paragrafo_pos_tabela = (
                    len(row_cells) == 1
                    and ln.x0 <= 32.0
                    and len(row_text_full) > 55
                    and not eh_linha_total
                    and not (len(colunas) >= 2 and abs(ln.x0 - colunas[0][1]) <= 4.0 and len(row_text_full) <= 30)
                )
                if eh_paragrafo_pos_tabela:
                    tabela_ativa = None
                    # Cai para o tratamento de corpo abaixo
                else:
                    # Verifica continuacao de celula na linha seguinte (ex.: 'kg' em CTe ou descricao quebrada)
                    if not eh_linha_total and len(row_cells) < len(colunas):
                        while j < len(p_linhas):
                            nxt = p_linhas[j]
                            if nxt.eh_marca_dagua:
                                j += 1
                                continue
                            if (
                                _eh_valor(nxt)
                                and 0.0 < nxt.y0 - y_row <= 11.0
                                and nxt.x0 > colunas[0][1] + 5.0
                                and "TOTAL" not in nxt.texto.upper()
                            ):
                                row_cells.append(nxt)
                                j += 1
                            else:
                                break

                    n_linha_tabela += 1
                    row_dict: dict[str, str] = {}
                    if len(row_cells) == len(colunas):
                        for (c_nome, _), cell in zip(colunas, row_cells):
                            row_dict[c_nome] = cell.texto.strip()
                    else:
                        for cell in row_cells:
                            c_nome = min(colunas, key=lambda c: abs(c[1] - cell.x0))[0]
                            if c_nome in row_dict:
                                row_dict[c_nome] = f"{row_dict[c_nome]} {cell.texto.strip()}"
                            else:
                                row_dict[c_nome] = cell.texto.strip()

                    if eh_linha_total:
                        row_dict["_tipo_linha"] = "total"
                        dest_item = f"total_tabela:{spec.nome}:{nome_tbl}"
                    else:
                        dest_item = f"ext_item:{spec.nome}:{nome_tbl}:{n_linha_tabela}"
                    itens_extraidos.append(row_dict)

                    conn.execute(
                        """
                        INSERT INTO ext_item (chave, documento_id, tabela, n_linha, colunas_json, linha_bruto_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"extitm:{rel}:{nome_tbl}:{n_linha_tabela}",
                            doc_id,
                            nome_tbl,
                            n_linha_tabela,
                            json.dumps(row_dict, ensure_ascii=False),
                            row_cells[0].id,
                        ),
                    )
                    n_itens += 1
                    for cell in row_cells:
                        updates.append((dest_item, cell.id))
                    # Em NFe / NFe-compra / Extrato-liquidacao-cartao / Posicao-contrato / Cronograma, TOTAIS encerra a tabela
                    if any(row_text_full.upper().startswith(p) for p in ("TOTAIS", "TOTAL ", "TOTAL DA", "TOTAL DO", "TOTAL DEPOSITADO", "TOTAL LIQUIDADO", "TOTAL INVOICE")):
                        tabela_ativa = None
                    idx = j
                    continue

            # 7. Cabecalho do documento (y0 < 80 antes do corpo) ou corpo/prosa
            if ln.y0 < 85.0 and not rodape_prosa_atingido and secao_atual == "GERAL" and n_campos == 0:
                updates.append((f"cabecalho_doc:{spec.nome}", ln.id))
                _add_campo("CABECALHO", "CABECALHO", txt, ln.id)
                idx += 1
                continue

            updates.append((f"corpo_texto:{spec.nome}", ln.id))
            _add_campo(secao_atual, "TEXTO", txt, ln.id)
            if spec.eh_prosa:
                corpo_prosa_linhas.append((txt, ln.id))
            idx += 1

    if spec.eh_prosa and corpo_prosa_linhas:
        texto_prosa = " ".join(t for t, _ in corpo_prosa_linhas)
        lid_prosa = corpo_prosa_linhas[0][1]
        for rot, vtxt, vc, md, vm, vd in _extrair_campos_prosa(spec.nome, texto_prosa):
            campo_seq += 1
            campos_extraidos.append((rot, vtxt, vc, md, vm, vd))
            conn.execute(
                """
                INSERT INTO ext_campo (
                    chave, documento_id, secao, rotulo, valor_texto,
                    valor_centavos, moeda, valor_micro, valor_data, linha_bruto_id
                ) VALUES (?, ?, 'PROSA', ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"extcmp:{rel}:{campo_seq}", doc_id, rot, vtxt, vc, md, vm, vd, lid_prosa),
            )
            n_campos += 1

    # Preencher resumo em ext_documento
    numero_doc: str | None = None
    data_emissao: str | None = None
    val_total: int | None = None
    val_texto: str | None = None
    moeda_doc = spec.moeda_padrao

    for rot, vtxt, vc, md, _, vd in campos_extraidos:
        if numero_doc is None:
            for r_alvo in spec.rotulos_numero + (("NUMERO",) if spec.eh_prosa else ()):
                if rot == r_alvo or rot.startswith(r_alvo):
                    numero_doc = vtxt
                    break
        if data_emissao is None and vd is not None:
            for r_alvo in spec.rotulos_data + (("DATA_EMISSAO",) if spec.eh_prosa else ()):
                if rot == r_alvo or rot.startswith(r_alvo):
                    data_emissao = vd
                    break
        if val_total is None and vc is not None:
            for r_alvo in spec.rotulos_valor + (("VALOR",) if spec.eh_prosa else ()):
                if rot == r_alvo or rot.startswith(r_alvo):
                    val_total = vc
                    val_texto = vtxt
                    if md:
                        moeda_doc = md
                    break

    if val_total is None and spec.rotulos_valor:
        for row_dict in itens_extraidos:
            vals_str = [str(v) for k, v in row_dict.items() if k != "_tipo_linha"]
            if any(v == r_alvo or v.startswith(r_alvo) for r_alvo in spec.rotulos_valor for v in vals_str):
                # Procurar valor monetario na linha (preferencialmente na ultima coluna)
                for cand in reversed(vals_str):
                    vc, md, _, _ = _parse_valor_campo(cand, moeda_doc)
                    if vc is not None:
                        val_total = vc
                        val_texto = cand
                        if md:
                            moeda_doc = md
                        break
                if val_total is not None:
                    break

    conn.execute(
        """
        UPDATE ext_documento
        SET numero = ?, data_emissao = ?, valor_total_centavos = ?, moeda = ?, valor_total_texto = ?
        WHERE id = ?
        """,
        (numero_doc, data_emissao or data_ref, val_total, moeda_doc, val_texto, doc_id),
    )

    if updates:
        conn.executemany("UPDATE bru_linha SET destino = ? WHERE id = ?", updates)
    return n_campos, n_itens, n_notas


def _propagar_destinos_consolidados(conn: sqlite3.Connection) -> int:
    """Propaga destinos dos 847 PDFs individuais de Goiania para as 847 paginas consolidadas."""
    cons = conn.execute(
        """
        SELECT id, caminho_relativo, paginas_total
        FROM bru_arquivo
        WHERE papel_acervo = 'consolidado_espelho'
        ORDER BY caminho_relativo
        """
    ).fetchall()
    total_prop = 0
    updates: list[tuple[str, int]] = []
    for cid, crel, cpags in cons:
        parts = str(crel).replace("D4/Goiania_", "").replace("_consolidado.pdf", "").split("_", 1)
        ym, pasta = parts[0], parts[1]
        inds = conn.execute(
            """
            SELECT id FROM bru_arquivo
            WHERE caminho_relativo LIKE ? AND papel_acervo = 'primario'
            ORDER BY caminho_relativo
            """,
            (f"D4/Goiania_PDFs_individuais/{ym}/{pasta}/%",),
        ).fetchall()
        for pno, (iid,) in enumerate(inds, start=1):
            c_rows = conn.execute(
                "SELECT id, eh_marca_dagua FROM bru_linha WHERE arquivo_id = ? AND pagina = ? ORDER BY n_linha",
                (cid, pno),
            ).fetchall()
            i_rows = conn.execute(
                "SELECT destino FROM bru_linha WHERE arquivo_id = ? AND pagina = 1 ORDER BY n_linha",
                (iid,),
            ).fetchall()
            for (c_lid, eh_md), (i_dest,) in zip(c_rows, i_rows):
                if eh_md:
                    continue
                if i_dest:
                    updates.append((f"espelho:{i_dest}", c_lid))
                    total_prop += 1
    if updates:
        conn.executemany("UPDATE bru_linha SET destino = ? WHERE id = ?", updates)
    return total_prop


def extrair_documentos_pdf(
    conn: sqlite3.Connection,
    filtro_modelo: str | None = None,
) -> dict[str, int]:
    """Extrai os documentos PDF do D4 usando o catalogo declarativo dos 51 modelos."""
    rows = conn.execute(
        """
        SELECT id, caminho_relativo, nome
        FROM bru_arquivo
        WHERE dossie = 'D4'
          AND extensao = '.pdf'
          AND papel_acervo = 'primario'
          AND nome NOT LIKE 'Livro_%'
        ORDER BY caminho_relativo
        """
    ).fetchall()

    n_docs = 0
    n_campos = 0
    n_itens = 0
    n_notas = 0

    for arq_id, rel, nome in rows:
        modelo, est_prefixo, data_ref, doc_ref = parse_nome_arquivo_d4(str(nome))
        if filtro_modelo is not None and modelo != filtro_modelo:
            continue
        if modelo not in CATALOGO_MODELOS:
            raise KeyError(f"Modelo nao registrado no CATALOGO_MODELOS: {modelo} ({rel})")
        spec = CATALOGO_MODELOS[modelo]
        c, it, nt = _processar_documento(
            conn, int(arq_id), str(rel), str(nome), spec, est_prefixo, data_ref, doc_ref
        )
        n_docs += 1
        n_campos += c
        n_itens += it
        n_notas += nt

    n_prop = 0
    if filtro_modelo is None:
        n_prop = _propagar_destinos_consolidados(conn)

    return {
        "documentos": n_docs,
        "campos": n_campos,
        "itens": n_itens,
        "notas": n_notas,
        "linhas_consolidadas_propagadas": n_prop,
    }
