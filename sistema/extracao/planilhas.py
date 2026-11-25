"""Camada 2 (Fase 3) — Extracao das 6 planilhas XLSX com avaliacao de formulas sem cache."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

_RE_CONTA = re.compile(r"^\d\.\d\.\d{2}\.\d{3}$")


@dataclass
class CelulaBruta:
    id: int
    chave: str
    aba: str
    ordem_aba: int
    linha: int
    coluna: int
    endereco: str
    tipo_dado: str
    valor_texto: str | None
    valor_cacheado: str | None
    formula: str | None


def _carregar_celulas(conn: sqlite3.Connection, caminho_rel: str) -> tuple[int, dict[str, dict[int, dict[int, CelulaBruta]]]]:
    row = conn.execute(
        "SELECT id FROM bru_arquivo WHERE caminho_relativo = ?", (caminho_rel,)
    ).fetchone()
    if not row:
        raise FileNotFoundError(f"Planilha nao encontrada em bru_arquivo: {caminho_rel}")
    arq_id = int(row[0])
    rows = conn.execute(
        """
        SELECT id, chave, aba, ordem_aba, linha, coluna, endereco, tipo_dado, valor_texto, valor_cacheado, formula
        FROM bru_celula
        WHERE arquivo_id = ?
        ORDER BY ordem_aba, linha, coluna
        """,
        (arq_id,),
    ).fetchall()
    abas: dict[str, dict[int, dict[int, CelulaBruta]]] = {}
    for r in rows:
        cb = CelulaBruta(
            id=int(r[0]),
            chave=str(r[1]),
            aba=str(r[2]),
            ordem_aba=int(r[3]),
            linha=int(r[4]),
            coluna=int(r[5]),
            endereco=str(r[6]),
            tipo_dado=str(r[7]),
            valor_texto=r[8],
            valor_cacheado=r[9],
            formula=r[10],
        )
        abas.setdefault(cb.aba, {}).setdefault(cb.linha, {})[cb.coluna] = cb
    return arq_id, abas


def _centavos_de_celula(cb: CelulaBruta | None) -> int | None:
    if cb is None:
        return None
    bruto = cb.valor_cacheado if cb.valor_cacheado is not None else cb.valor_texto
    if bruto is None:
        return None
    try:
        return round(float(bruto) * 100)
    except ValueError:
        return None


def _atualizar_destinos(conn: sqlite3.Connection, updates: list[tuple[str, int]]) -> None:
    if updates:
        conn.executemany("UPDATE bru_celula SET destino = ? WHERE id = ?", updates)


def _marcar_linha(updates: list[tuple[str, int]], cols: dict[int, CelulaBruta], destino: str) -> None:
    for cb in cols.values():
        updates.append((destino, cb.id))


def _gravar_parametros_genericos(
    conn: sqlite3.Connection,
    arq_id: int,
    prefixo: str,
    aba: str,
    linhas: dict[int, dict[int, CelulaBruta]],
    updates: list[tuple[str, int]],
    destino: str,
) -> int:
    count = 0
    for r_idx in sorted(linhas):
        cols = linhas[r_idx]
        c_ord = sorted(cols)
        rot = str(cols[c_ord[0]].valor_texto or cols[c_ord[0]].formula or "").strip()
        vals = [
            str(cols[c].valor_cacheado or cols[c].valor_texto or cols[c].formula or "").strip()
            for c in c_ord[1:]
        ]
        val_str = " | ".join(v for v in vals if v)
        if not val_str and rot:
            val_str = rot
            rot = f"{aba}_L{r_idx}"
        conn.execute(
            """
            INSERT INTO ext_parametro_planilha (chave, arquivo_id, aba, rotulo, valor_texto, celula_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"param:{prefixo}:{aba}:L{r_idx}", arq_id, aba, rot or f"L{r_idx}", val_str, cols[c_ord[0]].id),
        )
        _marcar_linha(updates, cols, destino)
        count += 1
    return count


def _extrair_extrato_xlsx(
    conn: sqlite3.Connection,
    caminho_rel: str,
    mapa_abas: dict[str, str],
) -> dict[str, int]:
    arq_id, abas = _carregar_celulas(conn, caminho_rel)
    updates: list[tuple[str, int]] = []
    n_movs = 0
    n_params = 0

    saldos_finais_por_aba: dict[str, dict[int, int]] = {}
    debitos_por_aba: dict[str, dict[int, int]] = {}
    creditos_por_aba: dict[str, dict[int, int]] = {}

    for aba, conta_codigo in mapa_abas.items():
        if aba not in abas:
            continue
        linhas = abas[aba]
        saldo_corrente = 0
        saldos_finais_por_aba[aba] = {}
        debitos_por_aba[aba] = {}
        creditos_por_aba[aba] = {}

        for r_idx in sorted(linhas):
            cols = linhas[r_idx]
            c1 = cols.get(1)
            c2 = cols.get(2)
            c3 = cols.get(3)
            c4 = cols.get(4)
            c5 = cols.get(5)
            c6 = cols.get(6)

            if c1 is not None and c1.tipo_dado == "data" and c3 is not None and str(c3.valor_texto or "").strip() == "-":
                # Saldo Inicial / Saldo Anterior
                saldo_ini = _centavos_de_celula(c6)
                if saldo_ini is None and c6 is not None and c6.formula:
                    # Ex.: ='2025 - Conta Matriz'!F342 ou =F43
                    f_str = c6.formula.strip()
                    m_ref = re.match(r"^='([^']+)'!F(\d+)$", f_str)
                    m_local = re.match(r"^=F(\d+)$", f_str)
                    if m_ref:
                        aba_ref, row_ref = m_ref.group(1), int(m_ref.group(2))
                        saldo_ini = saldos_finais_por_aba.get(aba_ref, {}).get(row_ref, 0)
                    elif m_local:
                        saldo_ini = saldos_finais_por_aba.get(aba, {}).get(int(m_local.group(1)), 0)
                saldo_corrente = saldo_ini or 0
                saldos_finais_por_aba[aba][r_idx] = saldo_corrente
                conn.execute(
                    """
                    INSERT INTO ext_parametro_planilha (chave, arquivo_id, aba, rotulo, valor_texto, celula_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"param:extrato:{conta_codigo}:L{r_idx}",
                        arq_id,
                        aba,
                        "Saldo Inicial",
                        f"{c1.valor_texto} | {saldo_corrente}",
                        c6.id if c6 else c1.id,
                    ),
                )
                _marcar_linha(updates, cols, f"saldo_inicial_extrato:{conta_codigo}")
                n_params += 1
                continue

            if c1 is not None and c1.tipo_dado == "data" and c3 is not None:
                data_iso = str(c1.valor_texto or "")
                hist = str(c2.valor_texto or "") if c2 else ""
                doc_ref = str(c3.valor_texto or "").strip()
                deb = _centavos_de_celula(c4)
                cred = _centavos_de_celula(c5)
                debitos_por_aba[aba][r_idx] = deb or 0
                creditos_por_aba[aba][r_idx] = cred or 0
                saldo_corrente = saldo_corrente - (deb or 0) + (cred or 0)

                saldo_cache = _centavos_de_celula(c6)
                if saldo_cache is not None:
                    saldo_final = saldo_cache
                    origem = "impresso"
                    saldo_corrente = saldo_final
                else:
                    saldo_final = saldo_corrente
                    origem = "calculado_formula"

                saldos_finais_por_aba[aba][r_idx] = saldo_final
                chave_m = f"extmov:{conta_codigo}:{r_idx:04d}"
                conn.execute(
                    """
                    INSERT INTO ext_extrato_linha (
                        chave, arquivo_id, aba, n_linha, conta_codigo, data_movimento,
                        historico, doc_ref, debito_centavos, credito_centavos,
                        saldo_centavos, origem_valor, celula_saldo_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chave_m,
                        arq_id,
                        aba,
                        r_idx,
                        conta_codigo,
                        data_iso,
                        hist,
                        doc_ref,
                        deb,
                        cred,
                        saldo_final,
                        origem,
                        c6.id if c6 else None,
                    ),
                )
                _marcar_linha(updates, cols, f"ext_extrato_linha:{chave_m}")
                n_movs += 1
                continue

            # Linhas de totais (=SUM(...)) ou cabecalhos
            has_formula = any(cb.tipo_dado == "formula" for cb in cols.values())
            if has_formula:
                tot_deb = sum(debitos_por_aba[aba].values())
                tot_cred = sum(creditos_por_aba[aba].values())
                conn.execute(
                    """
                    INSERT INTO ext_parametro_planilha (chave, arquivo_id, aba, rotulo, valor_texto, celula_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"param:extrato:{conta_codigo}:totais:L{r_idx}",
                        arq_id,
                        aba,
                        "Totais calculados",
                        json.dumps({"debito_centavos": tot_deb, "credito_centavos": tot_cred}),
                        next(iter(cols.values())).id,
                    ),
                )
                _marcar_linha(updates, cols, f"total_extrato:{conta_codigo}")
                n_params += 1
            else:
                _marcar_linha(updates, cols, f"cabecalho_extrato:{conta_codigo}")

    # Demais abas (Parametros e Notas, Resumo por mes)
    for aba, linhas in abas.items():
        if aba in mapa_abas:
            continue
        if aba == "Resumo por mês":
            for r_idx in sorted(linhas):
                cols = linhas[r_idx]
                if r_idx == 1:
                    _marcar_linha(updates, cols, "cabecalho_resumo_goiania")
                    continue
                mes = str(cols[1].valor_texto or "")
                cred_f = cols[2].formula or ""
                deb_f = cols[3].formula or ""
                sal_f = cols[4].formula or ""
                # Avaliar =SUM('2026 - Conta Goiânia'!E6:E43) etc.
                m_c = re.search(r"'([^']+)'!E(\d+):E(\d+)", cred_f)
                m_d = re.search(r"'([^']+)'!D(\d+):D(\d+)", deb_f)
                m_s = re.search(r"'([^']+)'!F(\d+)", sal_f)
                c_tot = (
                    sum(creditos_por_aba.get(m_c.group(1), {}).get(i, 0) for i in range(int(m_c.group(2)), int(m_c.group(3)) + 1))
                    if m_c
                    else 0
                )
                d_tot = (
                    sum(debitos_por_aba.get(m_d.group(1), {}).get(i, 0) for i in range(int(m_d.group(2)), int(m_d.group(3)) + 1))
                    if m_d
                    else 0
                )
                s_fin = saldos_finais_por_aba.get(m_s.group(1), {}).get(int(m_s.group(2)), 0) if m_s else 0
                conn.execute(
                    """
                    INSERT INTO ext_parametro_planilha (chave, arquivo_id, aba, rotulo, valor_texto, celula_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"param:goiania_resumo:{mes}",
                        arq_id,
                        aba,
                        f"Resumo {mes}",
                        json.dumps({"creditos_centavos": c_tot, "debitos_centavos": d_tot, "saldo_final_centavos": s_fin}),
                        cols[1].id,
                    ),
                )
                _marcar_linha(updates, cols, f"resumo_mes_goiania:{mes}")
                n_params += 1
        else:
            n_params += _gravar_parametros_genericos(
                conn, arq_id, f"extrato:{caminho_rel}", aba, linhas, updates, f"ext_parametro_planilha:{aba}"
            )

    _atualizar_destinos(conn, updates)
    return {"extrato_linhas": n_movs, "parametros": n_params}


def _normalizar_aba_balancete(aba: str) -> str:
    if "antes" in aba:
        return "2025-12-antes"
    if "pós" in aba or "pos" in aba:
        return "2025-12-pos"
    m = re.match(r"^(\d{2})-(\d{4})$", aba)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    return aba


def _extrair_balancetes_xlsx(conn: sqlite3.Connection) -> dict[str, int]:
    updates: list[tuple[str, int]] = []
    n_linhas = 0
    n_params = 0

    # 1. Balancetes_Verificacao_Mensais_2025-2026.xlsx
    arq_id, abas = _carregar_celulas(conn, "D4/Balancetes_Verificacao_Mensais_2025-2026.xlsx")
    for aba, linhas in abas.items():
        if aba == "Resumo":
            n_params += _gravar_parametros_genericos(
                conn, arq_id, "balancetes_xlsx", aba, linhas, updates, "resumo_balancete_xlsx"
            )
            continue
        if aba == "Notas":
            for r_idx in sorted(linhas):
                cols = linhas[r_idx]
                txt = " | ".join(
                    str(c.valor_texto or "").strip() for c in cols.values() if str(c.valor_texto or "").strip()
                )
                if txt:
                    c0 = next(iter(cols.values()))
                    conn.execute(
                        "INSERT INTO ext_nota_didatica (chave, arquivo_id, texto, celula_id) VALUES (?, ?, ?, ?)",
                        (f"nota:balancete_xlsx:L{r_idx}", arq_id, txt, c0.id),
                    )
                _marcar_linha(updates, cols, "ext_nota_didatica:balancete_xlsx")
            continue

        periodo = _normalizar_aba_balancete(aba)
        somas = [0, 0, 0, 0, 0, 0]
        for r_idx in sorted(linhas):
            cols = linhas[r_idx]
            c1 = cols.get(1)
            if c1 and _RE_CONTA.match(str(c1.valor_texto or "").strip()):
                cod = str(c1.valor_texto).strip()
                nome = str(cols[2].valor_texto or "").strip() if 2 in cols else ""
                ant_d = _centavos_de_celula(cols.get(3)) or 0
                ant_c = _centavos_de_celula(cols.get(4)) or 0
                deb = _centavos_de_celula(cols.get(5)) or 0
                cred = _centavos_de_celula(cols.get(6)) or 0
                atu_d = _centavos_de_celula(cols.get(7)) or 0
                atu_c = _centavos_de_celula(cols.get(8)) or 0
                for idx_s, v in enumerate((ant_d, ant_c, deb, cred, atu_d, atu_c)):
                    somas[idx_s] += v

                chave_b = f"extbal:xlsx:{periodo}:{cod}"
                conn.execute(
                    """
                    INSERT INTO ext_balancete_linha (
                        chave, arquivo_id, fonte, periodo, conta_codigo, conta_nome,
                        saldo_anterior_centavos, debito_centavos, credito_centavos, saldo_atual_centavos,
                        origem_valor, celula_id
                    ) VALUES (?, ?, 'xlsx', ?, ?, ?, ?, ?, ?, ?, 'impresso', ?)
                    """,
                    (chave_b, arq_id, periodo, cod, nome, ant_d - ant_c, deb, cred, atu_d - atu_c, c1.id),
                )
                _marcar_linha(updates, cols, f"ext_balancete_linha:xlsx:{periodo}:{cod}")
                n_linhas += 1
            elif any(cb.tipo_dado == "formula" for cb in cols.values()):
                rot = str(cols[2].valor_texto or f"L{r_idx}") if 2 in cols else f"L{r_idx}"
                conn.execute(
                    """
                    INSERT INTO ext_parametro_planilha (chave, arquivo_id, aba, rotulo, valor_texto, celula_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"param:balancete_xlsx:{periodo}:L{r_idx}",
                        arq_id,
                        aba,
                        rot,
                        json.dumps(
                            {
                                "ant_d": somas[0],
                                "ant_c": somas[1],
                                "deb": somas[2],
                                "cred": somas[3],
                                "atu_d": somas[4],
                                "atu_c": somas[5],
                                "origem_valor": "calculado_formula",
                            }
                        ),
                        next(iter(cols.values())).id,
                    ),
                )
                _marcar_linha(updates, cols, f"total_balancete_xlsx:{periodo}")
                n_params += 1
            else:
                _marcar_linha(updates, cols, f"cabecalho_balancete_xlsx:{periodo}")

    _atualizar_destinos(conn, updates)
    updates.clear()

    # 2. D1/Balancete_Abertura_31-12-2024.xlsx
    arq_id_d1, abas_d1 = _carregar_celulas(conn, "D1/Balancete_Abertura_31-12-2024.xlsx")
    for aba, linhas in abas_d1.items():
        for r_idx in sorted(linhas):
            cols = linhas[r_idx]
            c1 = cols.get(1)
            c1_txt = str(c1.valor_texto or "").strip() if c1 else ""
            if _RE_CONTA.match(c1_txt):
                nome = str(cols[2].valor_texto or "").strip() if 2 in cols else ""
                deb = _centavos_de_celula(cols.get(3)) or 0
                cred = _centavos_de_celula(cols.get(4)) or 0
                c5 = cols.get(5)
                if c5 and c5.valor_texto:
                    conn.execute(
                        "INSERT INTO ext_nota_didatica (chave, arquivo_id, texto, celula_id) VALUES (?, ?, ?, ?)",
                        (f"nota:bal_abertura:{c1_txt}", arq_id_d1, str(c5.valor_texto), c5.id),
                    )
                chave_b = f"extbal:xlsx:2024-12:{c1_txt}"
                conn.execute(
                    """
                    INSERT INTO ext_balancete_linha (
                        chave, arquivo_id, fonte, periodo, conta_codigo, conta_nome,
                        saldo_anterior_centavos, debito_centavos, credito_centavos, saldo_atual_centavos,
                        origem_valor, celula_id
                    ) VALUES (?, ?, 'xlsx', '2024-12', ?, ?, 0, ?, ?, ?, 'impresso', ?)
                    """,
                    (chave_b, arq_id_d1, c1_txt, nome, deb, cred, deb - cred, c1.id),
                )
                _marcar_linha(updates, cols, f"ext_balancete_linha:xlsx:2024-12:{c1_txt}")
                n_linhas += 1
            else:
                rot = c1_txt or (str(cols[2].valor_texto or "").strip() if 2 in cols else f"L{r_idx}")
                vals = " | ".join(
                    str(cb.valor_cacheado or cb.valor_texto or cb.formula or "").strip()
                    for col_i, cb in sorted(cols.items())
                    if col_i > 1
                )
                conn.execute(
                    """
                    INSERT INTO ext_parametro_planilha (chave, arquivo_id, aba, rotulo, valor_texto, celula_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f"param:bal_abertura:L{r_idx}", arq_id_d1, aba, rot, vals, next(iter(cols.values())).id),
                )
                _marcar_linha(updates, cols, "param_balancete_abertura")
                n_params += 1
    _atualizar_destinos(conn, updates)
    return {"balancete_xlsx_linhas": n_linhas, "parametros": n_params}


def _extrair_estoque_e_tributaria(conn: sqlite3.Connection) -> dict[str, int]:
    updates: list[tuple[str, int]] = []
    n_est = 0
    n_params = 0

    # 1. Ficha_Estoques_Abertura_01-01-2025.xlsx
    arq_id, abas = _carregar_celulas(conn, "D4/Ficha_Estoques_Abertura_01-01-2025.xlsx")
    for aba, linhas in abas.items():
        if aba == "Premissas":
            for r_idx in sorted(linhas):
                cols = linhas[r_idx]
                txt = " — ".join(str(c.valor_texto or "").strip() for c in cols.values() if str(c.valor_texto or "").strip())
                if r_idx > 1 and txt:
                    c0 = next(iter(cols.values()))
                    conn.execute(
                        "INSERT INTO ext_nota_didatica (chave, arquivo_id, texto, celula_id) VALUES (?, ?, ?, ?)",
                        (f"nota:estoque_premissas:L{r_idx}", arq_id, txt, c0.id),
                    )
                _marcar_linha(updates, cols, "ext_nota_didatica:estoque_premissas")
            continue

        # Determinar linha de cabecalho da tabela
        header_row = 1
        for r_idx in sorted(linhas):
            c1 = linhas[r_idx].get(1)
            if c1 and str(c1.valor_texto or "").strip() in ("Cód.", "Código", "Nº"):
                header_row = r_idx
                break

        headers: dict[int, str] = {}
        if header_row in linhas:
            headers = {col: str(cb.valor_texto or f"col_{col}").strip() for col, cb in linhas[header_row].items()}

        for r_idx in sorted(linhas):
            cols = linhas[r_idx]
            if r_idx <= header_row:
                _marcar_linha(updates, cols, f"cabecalho_estoque:{aba}")
                continue
            c1 = cols.get(1)
            c2 = cols.get(2)
            c1_txt = str(c1.valor_texto or "").strip() if c1 else ""
            c2_txt = str(c2.valor_texto or "").strip() if c2 else ""
            if c1 is None or c2_txt == "TOTAL" or not c1_txt:
                n_params += _gravar_parametros_genericos(
                    conn, arq_id, "estoque", aba, {r_idx: cols}, updates, f"param_estoque:{aba}"
                )
                continue

            dados: dict[str, Any] = {}
            for col_i, cb in sorted(cols.items()):
                h_nome = headers.get(col_i, f"col_{col_i}")
                val: Any = cb.valor_cacheado if cb.valor_cacheado is not None else cb.valor_texto
                if cb.tipo_dado == "formula" and cb.valor_cacheado is None:
                    val = cb.formula
                dados[h_nome] = val

            prod_cod = c1_txt if not c1_txt.isdigit() else None
            desc = c2_txt if not c1_txt.isdigit() else c1_txt
            chave_e = f"extest:{aba}:{r_idx}"
            conn.execute(
                """
                INSERT INTO ext_estoque_linha (chave, arquivo_id, aba, ordem, produto_codigo, descricao, dados_json, celula_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (chave_e, arq_id, aba, r_idx, prod_cod, desc, json.dumps(dados, ensure_ascii=False), c1.id),
            )
            _marcar_linha(updates, cols, f"ext_estoque_linha:{chave_e}")
            n_est += 1

    _atualizar_destinos(conn, updates)
    updates.clear()

    # 2. D3/Anlise_Tributria_Modelo.xlsx
    arq_id_d3, abas_d3 = _carregar_celulas(conn, "D3/Anlise_Tributria_Modelo.xlsx")
    for aba, linhas in abas_d3.items():
        n_params += _gravar_parametros_genericos(
            conn, arq_id_d3, "d3_analise", aba, linhas, updates, f"ext_parametro_planilha:d3:{aba}"
        )
    _atualizar_destinos(conn, updates)
    return {"estoque_linhas": n_est, "parametros": n_params}


def extrair_planilhas(conn: sqlite3.Connection) -> dict[str, int]:
    """Extrai todas as 6 planilhas XLSX do acervo e marca 100% das celulas em bru_celula."""
    r1 = _extrair_extrato_xlsx(
        conn,
        "D4/ExtratosBancariosRotaSul.xlsx",
        {
            "2025 - Conta Matriz": "matriz_2025",
            "2026 - Conta Matriz": "matriz_2026",
            "Conta Filial (Itajai-SC)": "filial",
        },
    )
    r2 = _extrair_extrato_xlsx(
        conn,
        "D4/ExtratoBancario_MeiaPonte_Goiania_jan-ago2026.xlsx",
        {"2026 - Conta Goiânia": "goiania"},
    )
    r3 = _extrair_balancetes_xlsx(conn)
    r4 = _extrair_estoque_e_tributaria(conn)
    return {
        "extrato_linhas": r1["extrato_linhas"] + r2["extrato_linhas"],
        "balancete_xlsx_linhas": r3["balancete_xlsx_linhas"],
        "estoque_linhas": r4["estoque_linhas"],
        "parametros_planilha": r1["parametros"] + r2["parametros"] + r3["parametros"] + r4["parametros"],
    }
