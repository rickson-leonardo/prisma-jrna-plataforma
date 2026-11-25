"""Camada 2 (Fase 3) — Extracao dos Livros Diarios, Livros Razao e Balancete PDF."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any

_RE_MOEDA = re.compile(r"^-?\s*(?:R\$\s*)?([\d\.]+,\d{2})$")
_RE_DATA_BR = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_RE_TAG = re.compile(r"\[([^\]]+)\]\s*$")


@dataclass
class LinhaBruta:
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


def parse_moeda_centavos(s: str) -> int | None:
    """Converte 'R$ 1.234,56' ou '1.234,56' em centavos inteiros."""
    txt = s.strip()
    if not txt or txt in ("-", "–", "—"):
        return None
    neg = False
    if txt.startswith("-") or txt.startswith("–"):
        neg = True
        txt = txt[1:].strip()
    txt = txt.replace("R$", "").strip()
    if not re.match(r"^[\d\.]+,\d{2}$", txt):
        return None
    val = int(txt.replace(".", "").replace(",", ""))
    return -val if neg else val


def parse_data_iso(s: str) -> str | None:
    """Converte DD/MM/YYYY em YYYY-MM-DD."""
    m = _RE_DATA_BR.match(s.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{mo}-{d}"


def _split_conta(texto: str) -> tuple[str, str]:
    s = texto.strip()
    for sep in (" – ", " - "):
        if sep in s:
            cod, nome = s.split(sep, 1)
            return cod.strip(), nome.strip()
    return "", s


def _carregar_linhas(conn: sqlite3.Connection, caminho_rel: str) -> tuple[int, int, list[LinhaBruta]]:
    row = conn.execute(
        "SELECT id, paginas_total FROM bru_arquivo WHERE caminho_relativo = ?",
        (caminho_rel,),
    ).fetchone()
    if not row:
        raise FileNotFoundError(f"Arquivo nao encontrado em bru_arquivo: {caminho_rel}")
    arq_id, paginas_total = int(row[0]), int(row[1] or 0)
    rows = conn.execute(
        """
        SELECT id, chave, pagina, n_linha, texto, x0, y0, tam_fonte, fonte, cor_hex, eh_marca_dagua
        FROM bru_linha
        WHERE arquivo_id = ?
        ORDER BY pagina, n_linha
        """,
        (arq_id,),
    ).fetchall()
    linhas = [
        LinhaBruta(
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
    return arq_id, paginas_total, linhas


def _atualizar_destinos(conn: sqlite3.Connection, updates: list[tuple[str, int]]) -> None:
    if updates:
        conn.executemany("UPDATE bru_linha SET destino = ? WHERE id = ?", updates)


def _processar_termos_capa_encerramento(
    conn: sqlite3.Connection,
    arq_id: int,
    prefixo_chave: str,
    tag_termo: str,
    linhas: list[LinhaBruta],
    updates: list[tuple[str, int]],
) -> int:
    notas_lines: list[LinhaBruta] = []
    n_notas = 0
    for ln in linhas:
        if ln.eh_marca_dagua:
            continue
        if ln.cor_hex == "0x5a6477":
            notas_lines.append(ln)
            updates.append((f"ext_nota_didatica:{tag_termo}", ln.id))
        else:
            updates.append((tag_termo, ln.id))
    if notas_lines:
        n_notas += 1
        texto_nota = " ".join(x.texto.strip() for x in notas_lines if x.texto.strip())
        conn.execute(
            """
            INSERT INTO ext_nota_didatica (chave, arquivo_id, texto, linha_bruto_id)
            VALUES (?, ?, ?, ?)
            """,
            (f"nota:{prefixo_chave}:{notas_lines[0].pagina}", arq_id, texto_nota, notas_lines[0].id),
        )
    return n_notas


def extrair_diario(conn: sqlite3.Connection, caminho_rel: str, ano: int) -> dict[str, int]:
    """Extrai lancamentos e partidas do Livro Diario PDF."""
    arq_id, paginas_total, linhas = _carregar_linhas(conn, caminho_rel)
    updates: list[tuple[str, int]] = []
    n_lanc = 0
    n_part = 0
    n_notas = 0

    por_pagina: dict[int, list[LinhaBruta]] = {}
    for ln in linhas:
        por_pagina.setdefault(ln.pagina, []).append(ln)

    cur_num: int | None = None
    cur_data: str | None = None
    cur_hist: list[str] = []
    cur_linha_id: int | None = None
    cur_partidas: list[tuple[int, str, str, str, int, str, int, list[int]]] = []

    def _flush_lancamento() -> None:
        nonlocal n_lanc, n_part, cur_num, cur_data, cur_hist, cur_linha_id, cur_partidas
        if cur_num is None:
            return
        hist = " ".join(cur_hist).strip()
        m_tag = _RE_TAG.search(hist)
        tag_ref = m_tag.group(1).strip() if m_tag else None
        chave_l = f"extlanc:{ano}:{cur_num:04d}"
        cur = conn.execute(
            """
            INSERT INTO ext_diario_lancamento (
                chave, arquivo_id, ano, numero_lancamento, data_lancamento, historico, tag_ref, linha_bruto_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chave_l, arq_id, ano, cur_num, cur_data or "", hist, tag_ref, cur_linha_id),
        )
        lanc_id = int(cur.lastrowid)
        n_lanc += 1
        for ordem, cod, nome, dc, val_c, val_t, p_lid, _ in cur_partidas:
            chave_p = f"extpart:{ano}:{cur_num:04d}:{ordem:03d}"
            conn.execute(
                """
                INSERT INTO ext_diario_partida (
                    chave, lancamento_id, ordem, conta_codigo, conta_nome, dc, valor_centavos, valor_texto, linha_bruto_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (chave_p, lanc_id, ordem, cod, nome, dc, val_c, val_t, p_lid),
            )
            n_part += 1

        cur_num = None
        cur_data = None
        cur_hist = []
        cur_linha_id = None
        cur_partidas = []

    for pag in sorted(por_pagina):
        p_linhas = por_pagina[pag]
        if pag == 1 or pag == paginas_total:
            n_notas += _processar_termos_capa_encerramento(
                conn, arq_id, f"diario:{ano}", f"termo_livro_diario:{ano}", p_linhas, updates
            )
            continue

        # Identifica y0 da linha TOTAIS DO PERIODO se existir na pagina
        totais_y0: float | None = None
        for ln in p_linhas:
            if not ln.eh_marca_dagua and "TOTAIS DO PERÍODO" in ln.texto:
                totais_y0 = ln.y0
                break

        idx = 0
        while idx < len(p_linhas):
            ln = p_linhas[idx]
            if ln.eh_marca_dagua:
                idx += 1
                continue
            txt = ln.texto.strip()
            if (
                ln.cor_hex == "0x5a6477"
                and ln.x0 >= 95.0
                and txt.startswith("[")
                and txt.endswith("]")
                and cur_num is not None
            ):
                cur_hist.append(txt)
                updates.append((f"ext_diario_lancamento:{ano}:{cur_num:04d}", ln.id))
                idx += 1
                continue
            if ln.tam_fonte == 12.0 or ln.cor_hex in ("0x5a6477", "0xffffff"):
                updates.append((f"cabecalho_pagina_diario:{ano}", ln.id))
                idx += 1
                continue
            if totais_y0 is not None and abs(ln.y0 - totais_y0) <= 2.0:
                updates.append((f"total_periodo_diario:{ano}", ln.id))
                idx += 1
                continue

            if "Bold" in ln.fonte:
                txt = ln.texto.strip()
                if ln.x0 < 45 and txt.isdigit():
                    _flush_lancamento()
                    cur_num = int(txt)
                    cur_linha_id = ln.id
                elif 45 <= ln.x0 < 95 and parse_data_iso(txt):
                    cur_data = parse_data_iso(txt)
                else:
                    cur_hist.append(txt)
                dest_num = cur_num if cur_num is not None else 0
                updates.append((f"ext_diario_lancamento:{ano}:{dest_num:04d}", ln.id))
                idx += 1
                continue

            # Linha de partida (nao bold, agrupada por y0)
            y_ref = ln.y0
            grupo: list[LinhaBruta] = [ln]
            j = idx + 1
            while j < len(p_linhas):
                nxt = p_linhas[j]
                if (
                    not nxt.eh_marca_dagua
                    and "Bold" not in nxt.fonte
                    and nxt.cor_hex == "0x1d2433"
                    and abs(nxt.y0 - y_ref) <= 2.0
                    and (totais_y0 is None or abs(nxt.y0 - totais_y0) > 2.0)
                ):
                    grupo.append(nxt)
                    j += 1
                else:
                    break

            conta_parts: list[str] = []
            dc = ""
            val_texto = ""
            val_cent = 0
            p_lid = grupo[0].id
            for g in grupo:
                t = g.texto.strip()
                if g.x0 < 350:
                    conta_parts.append(t)
                    p_lid = g.id
                elif 350 <= g.x0 < 410:
                    dc = t
                elif g.x0 >= 410:
                    val_texto = t
                    val_cent = parse_moeda_centavos(t) or 0

            cod, nome = _split_conta(" ".join(conta_parts))
            ordem = len(cur_partidas) + 1
            cur_partidas.append((ordem, cod, nome, dc, val_cent, val_texto, p_lid, [g.id for g in grupo]))
            dest_num = cur_num if cur_num is not None else 0
            for g in grupo:
                updates.append((f"ext_diario_partida:{ano}:{dest_num:04d}:{ordem:03d}", g.id))
            idx = j

    _flush_lancamento()
    _atualizar_destinos(conn, updates)
    return {"lancamentos": n_lanc, "partidas": n_part, "notas": n_notas}


def extrair_razao(conn: sqlite3.Connection, caminho_rel: str, ano: int) -> dict[str, int]:
    """Extrai os movimentos por conta do Livro Razao PDF."""
    arq_id, paginas_total, linhas = _carregar_linhas(conn, caminho_rel)
    updates: list[tuple[str, int]] = []
    n_linhas_razao = 0
    n_notas = 0

    por_pagina: dict[int, list[LinhaBruta]] = {}
    for ln in linhas:
        por_pagina.setdefault(ln.pagina, []).append(ln)

    conta_cod = ""
    conta_nome = ""
    ordem_conta = 0
    seq_global = 0

    cur_data: str | None = None
    cur_num: int | None = None
    cur_hist: list[str] = []
    cur_deb: int | None = None
    cur_cred: int | None = None
    cur_saldo: int | None = None
    cur_saldo_dc: str | None = None
    cur_lid: int | None = None
    cur_ids: list[int] = []

    def _flush_mov() -> None:
        nonlocal n_linhas_razao, ordem_conta, seq_global
        nonlocal cur_data, cur_num, cur_hist, cur_deb, cur_cred, cur_saldo, cur_saldo_dc, cur_lid, cur_ids
        if cur_lid is None:
            return
        ordem_conta += 1
        seq_global += 1
        hist = " ".join(cur_hist).strip()
        chave_r = f"extraz:{ano}:{conta_cod}:{ordem_conta:04d}:{seq_global}"
        conn.execute(
            """
            INSERT INTO ext_razao_linha (
                chave, arquivo_id, ano, conta_codigo, conta_nome, ordem,
                data_movimento, numero_lancamento, historico,
                debito_centavos, credito_centavos, saldo_centavos, saldo_dc, linha_bruto_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chave_r,
                arq_id,
                ano,
                conta_cod,
                conta_nome,
                ordem_conta,
                cur_data,
                cur_num,
                hist,
                cur_deb,
                cur_cred,
                cur_saldo,
                cur_saldo_dc,
                cur_lid,
            ),
        )
        dest = f"ext_razao_linha:{ano}:{conta_cod}:{ordem_conta:04d}"
        for lid in cur_ids:
            updates.append((dest, lid))
        n_linhas_razao += 1

        cur_data = None
        cur_num = None
        cur_hist = []
        cur_deb = None
        cur_cred = None
        cur_saldo = None
        cur_saldo_dc = None
        cur_lid = None
        cur_ids = []

    for pag in sorted(por_pagina):
        p_linhas = por_pagina[pag]
        if pag == 1 or pag == paginas_total:
            n_notas += _processar_termos_capa_encerramento(
                conn, arq_id, f"razao:{ano}", f"termo_livro_razao:{ano}", p_linhas, updates
            )
            continue

        for ln in p_linhas:
            if ln.eh_marca_dagua:
                continue
            txt = ln.texto.strip()
            if ln.tam_fonte == 12.0 or ln.cor_hex == "0x5a6477":
                updates.append((f"cabecalho_pagina_razao:{ano}", ln.id))
                continue
            if ln.cor_hex == "0xffffff":
                if ln.tam_fonte >= 6.4:
                    _flush_mov()
                    conta_cod, conta_nome = _split_conta(txt)
                    ordem_conta = 0
                    updates.append((f"conta_razao:{ano}:{conta_cod}", ln.id))
                else:
                    updates.append((f"cabecalho_tabela_razao:{ano}", ln.id))
                continue
            if "Bold" in ln.fonte and ln.cor_hex == "0x1d2433":
                _flush_mov()
                updates.append((f"total_conta_razao:{ano}:{conta_cod}", ln.id))
                continue

            # Linha de movimento da conta (0x1d2433 nao Bold)
            if ln.x0 < 50 and parse_data_iso(txt):
                _flush_mov()
                cur_data = parse_data_iso(txt)
                cur_lid = ln.id
                cur_ids = [ln.id]
                continue

            if cur_lid is None:
                # Caso raro de linha residual antes da primeira data da pagina
                updates.append((f"cabecalho_tabela_razao:{ano}", ln.id))
                continue

            cur_ids.append(ln.id)
            if 50 <= ln.x0 < 105 and txt.isdigit():
                cur_num = int(txt)
            elif 105 <= ln.x0 < 350:
                cur_hist.append(txt)
            elif 350 <= ln.x0 < 430:
                cur_deb = parse_moeda_centavos(txt)
            elif 430 <= ln.x0 < 505:
                cur_cred = parse_moeda_centavos(txt)
            elif ln.x0 >= 505:
                if txt.endswith(" D"):
                    cur_saldo_dc = "D"
                    cur_saldo = parse_moeda_centavos(txt[:-2])
                elif txt.endswith(" C"):
                    cur_saldo_dc = "C"
                    cur_saldo = parse_moeda_centavos(txt[:-2])
                else:
                    cur_saldo_dc = None
                    cur_saldo = parse_moeda_centavos(txt)

    _flush_mov()
    _atualizar_destinos(conn, updates)
    return {"linhas_razao": n_linhas_razao, "notas": n_notas}


def _normalizar_periodo_balancete(rotulo: str) -> str:
    s = rotulo.strip()
    if "antes da apura" in s.lower():
        return "2025-12-antes"
    if "pós-apura" in s.lower() or "pos-apura" in s.lower():
        return "2025-12-pos"
    m = re.search(r"(\d{2})/(\d{4})", s)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    return s


def extrair_balancete_pdf(conn: sqlite3.Connection, caminho_rel: str) -> dict[str, int]:
    """Extrai as 21 paginas mensais de Balancetes_Verificacao_Mensais_2025-2026.pdf."""
    arq_id, _, linhas = _carregar_linhas(conn, caminho_rel)
    updates: list[tuple[str, int]] = []
    n_contas = 0

    por_pagina: dict[int, list[LinhaBruta]] = {}
    for ln in linhas:
        por_pagina.setdefault(ln.pagina, []).append(ln)

    for pag in sorted(por_pagina):
        p_linhas = por_pagina[pag]
        periodo = f"pag_{pag:02d}"
        for ln in p_linhas:
            if ln.tam_fonte == 12.0 and "BALANCETE DE VERIFICAÇÃO" in ln.texto:
                periodo = _normalizar_periodo_balancete(ln.texto)
                break

        col_hdr_xs = sorted(
            ln.x0
            for ln in p_linhas
            if not ln.eh_marca_dagua
            and ln.cor_hex == "0xffffff"
            and ln.texto.strip() not in ("Código", "Conta")
        )

        idx = 0
        while idx < len(p_linhas):
            ln = p_linhas[idx]
            if ln.eh_marca_dagua:
                idx += 1
                continue
            if ln.tam_fonte == 12.0 or ln.cor_hex in ("0x5a6477", "0xffffff"):
                updates.append((f"cabecalho_balancete_pdf:{periodo}", ln.id))
                idx += 1
                continue
            if "Bold" in ln.fonte:
                updates.append((f"total_balancete_pdf:{periodo}", ln.id))
                idx += 1
                continue

            # Agrupar linha da conta: inicia em x0 < 60 (codigo da conta) e consome ate o proximo x0 < 60
            grupo: list[LinhaBruta] = [ln]
            j = idx + 1
            while j < len(p_linhas):
                nxt = p_linhas[j]
                if nxt.eh_marca_dagua:
                    j += 1
                    continue
                if (
                    "Bold" in nxt.fonte
                    or nxt.cor_hex in ("0x5a6477", "0xffffff")
                    or nxt.tam_fonte == 12.0
                    or nxt.x0 < 60
                ):
                    break
                grupo.append(nxt)
                j += 1

            cod = ""
            nome_parts: list[str] = []
            vals_col = [0, 0, 0, 0, 0, 0]
            for g in grupo:
                t = g.texto.strip()
                if g.x0 < 60:
                    cod = t
                elif g.x0 < 200 and not t.startswith("R$"):
                    nome_parts.append(t)
                elif len(col_hdr_xs) == 6:
                    c_idx = min(range(6), key=lambda i: abs(g.x0 - (col_hdr_xs[i] - 8.0)))
                    vals_col[c_idx] = parse_moeda_centavos(t) or 0
                elif 200 <= g.x0 < 270:
                    vals_col[0] = parse_moeda_centavos(t) or 0
                elif 270 <= g.x0 < 330:
                    vals_col[1] = parse_moeda_centavos(t) or 0
                elif 330 <= g.x0 < 395:
                    vals_col[2] = parse_moeda_centavos(t) or 0
                elif 395 <= g.x0 < 455:
                    vals_col[3] = parse_moeda_centavos(t) or 0
                elif 455 <= g.x0 < 515:
                    vals_col[4] = parse_moeda_centavos(t) or 0
                else:
                    vals_col[5] = parse_moeda_centavos(t) or 0
            ant_d, ant_c, deb, cred, atu_d, atu_c = vals_col

            nome = " ".join(nome_parts).strip()
            chave_b = f"extbal:pdf:{periodo}:{cod}"
            conn.execute(
                """
                INSERT INTO ext_balancete_linha (
                    chave, arquivo_id, fonte, periodo, conta_codigo, conta_nome,
                    saldo_anterior_centavos, debito_centavos, credito_centavos, saldo_atual_centavos,
                    origem_valor, linha_bruto_id
                ) VALUES (?, ?, 'pdf', ?, ?, ?, ?, ?, ?, ?, 'impresso', ?)
                """,
                (chave_b, arq_id, periodo, cod, nome, ant_d - ant_c, deb, cred, atu_d - atu_c, grupo[0].id),
            )
            dest = f"ext_balancete_linha:pdf:{periodo}:{cod}"
            for g in grupo:
                updates.append((dest, g.id))
            n_contas += 1
            idx = j

    _atualizar_destinos(conn, updates)
    return {"balancete_pdf_linhas": n_contas}


def extrair_livros(conn: sqlite3.Connection) -> dict[str, int]:
    """Extrai todos os livros contabeis (Diarios, Razoes e Balancetes PDF)."""
    r1 = extrair_diario(conn, "D4/Livro_Diario_2025.pdf", 2025)
    r2 = extrair_diario(conn, "D4/Livro_Diario_2026.pdf", 2026)
    r3 = extrair_razao(conn, "D4/Livro_Razao_2025.pdf", 2025)
    r4 = extrair_razao(conn, "D4/Livro_Razao_2026.pdf", 2026)
    r5 = extrair_balancete_pdf(conn, "D4/Balancetes_Verificacao_Mensais_2025-2026.pdf")
    return {
        "diario_lancamentos": r1["lancamentos"] + r2["lancamentos"],
        "diario_partidas": r1["partidas"] + r2["partidas"],
        "razao_linhas": r3["linhas_razao"] + r4["linhas_razao"],
        "balancete_pdf_linhas": r5["balancete_pdf_linhas"],
    }
