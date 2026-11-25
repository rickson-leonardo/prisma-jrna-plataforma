"""Camada de qualidade (Fase 5) — Gates deterministicos de fidelidade e auditoria cruzada."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from sistema.extracao.planilhas import _carregar_celulas


def _upsert_conferencia(
    conn: sqlite3.Connection,
    chave: str,
    regra: str,
    severidade: str,
    registros: Any,
    valores: Any,
    status: str,
    descricao: str,
) -> None:
    conn.execute(
        """
        INSERT INTO conferencia (chave, regra, severidade, registros_json, valores_json, status, descricao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chave) DO UPDATE SET
            regra = excluded.regra,
            severidade = excluded.severidade,
            registros_json = excluded.registros_json,
            valores_json = excluded.valores_json,
            status = excluded.status,
            descricao = excluded.descricao
        """,
        (
            chave,
            regra,
            severidade,
            json.dumps(registros, ensure_ascii=False),
            json.dumps(valores, ensure_ascii=False),
            status,
            descricao,
        ),
    )


def executar_gates_fidelidade(conn: sqlite3.Connection, incluir_camada3: bool = True) -> dict[str, int]:
    """Executa os 8 gates de fidelidade entre fontes e grava os resultados na tabela conferencia."""
    ok = 0
    falhas = 0
    alertas = 0

    def _registrar(chave: str, regra: str, sev: str, regs: Any, vals: Any, st: str, desc: str) -> None:
        nonlocal ok, falhas, alertas
        _upsert_conferencia(conn, chave, regra, sev, regs, vals, st, desc)
        if sev == "gate_ok":
            ok += 1
        elif sev == "gate_falha":
            falhas += 1
        elif sev in ("alerta", "divergencia"):
            alertas += 1

    # Gate 1: Cobertura 100% da camada bruta (bru_linha, bru_celula, bru_paragrafo, bru_sigaa_item)
    cob = conn.execute("SELECT origem, total, com_destino, sem_destino FROM vw_cobertura_bruto").fetchall()
    cob_dict = {
        r[0]: {"total": int(r[1] or 0), "com_destino": int(r[2] or 0), "sem_destino": int(r[3] or 0)}
        for r in cob
    }
    sigaa_nao_map = conn.execute("SELECT COUNT(*) FROM bru_sigaa_item WHERE arquivo_id IS NULL").fetchone()[0]
    sem_dest_total = sum(v["sem_destino"] for v in cob_dict.values()) + int(sigaa_nao_map)
    sev1 = "gate_ok" if sem_dest_total == 0 else "gate_falha"
    _registrar(
        "gate:cobertura_bruto",
        "gate_cobertura_bruto",
        sev1,
        ["bru_linha", "bru_celula", "bru_paragrafo", "bru_sigaa_item"],
        {**cob_dict, "sigaa_nao_mapeados": int(sigaa_nao_map)},
        "ok" if sev1 == "gate_ok" else "aberto",
        f"Cobertura 100% da camada bruta verificada (sem_destino_total={sem_dest_total}).",
    )

    # Gate 2: Partidas dobradas no Livro Diario (D = C em 100% dos lancamentos)
    desb = conn.execute(
        """
        SELECT l.ano, l.numero_lancamento,
               SUM(CASE WHEN p.dc = 'D' THEN p.valor_centavos ELSE 0 END) AS d,
               SUM(CASE WHEN p.dc = 'C' THEN p.valor_centavos ELSE 0 END) AS c
        FROM ext_diario_lancamento l
        JOIN ext_diario_partida p ON p.lancamento_id = l.id
        GROUP BY l.id
        HAVING d != c
        """
    ).fetchall()
    totais_ano = {
        int(r[0]): {"debito": int(r[1]), "credito": int(r[2]), "qtd_lanc": int(r[3])}
        for r in conn.execute(
            """
            SELECT l.ano,
                   SUM(CASE WHEN p.dc = 'D' THEN p.valor_centavos ELSE 0 END),
                   SUM(CASE WHEN p.dc = 'C' THEN p.valor_centavos ELSE 0 END),
                   COUNT(DISTINCT l.id)
            FROM ext_diario_lancamento l
            JOIN ext_diario_partida p ON p.lancamento_id = l.id
            GROUP BY l.ano
            """
        ).fetchall()
    }
    sev2 = "gate_ok" if len(desb) == 0 else "gate_falha"
    _registrar(
        "gate:diario_partidas_dobradas",
        "gate_diario_partidas_dobradas",
        sev2,
        ["ext_diario_lancamento", "ext_diario_partida"],
        {"desbalanceados": len(desb), "totais_por_ano": totais_ano},
        "ok" if sev2 == "gate_ok" else "aberto",
        f"Partidas dobradas do Diario verificadas ({len(desb)} lancamentos desbalanceados).",
    )

    # Gate 3: Diario x Razao (somas de D e C por ano e conta)
    diario_cc = {
        (int(r[0]), str(r[1])): (int(r[2]), int(r[3]))
        for r in conn.execute(
            """
            SELECT l.ano, p.conta_codigo,
                   SUM(CASE WHEN p.dc = 'D' THEN p.valor_centavos ELSE 0 END),
                   SUM(CASE WHEN p.dc = 'C' THEN p.valor_centavos ELSE 0 END)
            FROM ext_diario_partida p
            JOIN ext_diario_lancamento l ON l.id = p.lancamento_id
            GROUP BY l.ano, p.conta_codigo
            """
        ).fetchall()
    }
    razao_cc = {
        (int(r[0]), str(r[1])): (int(r[2]), int(r[3]))
        for r in conn.execute(
            """
            SELECT ano, conta_codigo,
                   SUM(COALESCE(debito_centavos, 0)),
                   SUM(COALESCE(credito_centavos, 0))
            FROM ext_razao_linha
            GROUP BY ano, conta_codigo
            """
        ).fetchall()
    }
    diffs_dr: list[dict[str, Any]] = []
    for key in sorted(set(diario_cc) | set(razao_cc)):
        d_dc = diario_cc.get(key, (0, 0))
        r_dc = razao_cc.get(key, (0, 0))
        if d_dc != r_dc:
            diffs_dr.append({"ano": key[0], "conta": key[1], "diario": d_dc, "razao": r_dc})
    sev3 = "gate_ok" if len(diffs_dr) == 0 else "gate_falha"
    _registrar(
        "gate:diario_vs_razao",
        "gate_diario_vs_razao",
        sev3,
        ["ext_diario_partida", "ext_razao_linha"],
        {"contas_conferidas": len(diario_cc), "divergencias": diffs_dr[:20], "total_divergencias": len(diffs_dr)},
        "ok" if sev3 == "gate_ok" else "aberto",
        f"Cruzamento Diario x Razao executado em {len(diario_cc)} pares (ano, conta) com {len(diffs_dr)} divergencia(s).",
    )

    # Gate 4: Balancete PDF x Balancete XLSX (21 periodos mensais)
    diffs_bal = conn.execute(
        """
        SELECT p.periodo, p.conta_codigo,
               p.saldo_anterior_centavos, x.saldo_anterior_centavos,
               p.debito_centavos, x.debito_centavos,
               p.credito_centavos, x.credito_centavos,
               p.saldo_atual_centavos, x.saldo_atual_centavos
        FROM ext_balancete_linha p
        JOIN ext_balancete_linha x
          ON x.fonte = 'xlsx' AND x.periodo = p.periodo AND x.conta_codigo = p.conta_codigo
        WHERE p.fonte = 'pdf'
          AND (
            p.saldo_anterior_centavos != x.saldo_anterior_centavos
            OR p.debito_centavos != x.debito_centavos
            OR p.credito_centavos != x.credito_centavos
            OR p.saldo_atual_centavos != x.saldo_atual_centavos
          )
        """
    ).fetchall()
    periodos_pdf = conn.execute("SELECT COUNT(DISTINCT periodo) FROM ext_balancete_linha WHERE fonte = 'pdf'").fetchone()[0]
    sev4 = "gate_ok" if len(diffs_bal) == 0 and int(periodos_pdf) == 21 else "gate_falha"
    _registrar(
        "gate:balancete_pdf_vs_xlsx",
        "gate_balancete_pdf_vs_xlsx",
        sev4,
        ["ext_balancete_linha"],
        {"periodos_pdf": int(periodos_pdf), "divergencias": len(diffs_bal)},
        "ok" if sev4 == "gate_ok" else "aberto",
        f"Balancete PDF x XLSX conferido em {periodos_pdf} periodos mensais ({len(diffs_bal)} divergencias).",
    )

    # Gate 5: Consolidado x Individual Goiania (847 paginas espelho)
    cons_rows = conn.execute(
        "SELECT id, caminho_relativo, paginas_total FROM bru_arquivo WHERE papel_acervo = 'consolidado_espelho' ORDER BY caminho_relativo"
    ).fetchall()
    pags_ok = 0
    pags_div = 0
    for cid, crel, _ in cons_rows:
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
            c_txt = [
                r[0]
                for r in conn.execute(
                    "SELECT texto FROM bru_linha WHERE arquivo_id = ? AND pagina = ? AND eh_marca_dagua = 0 ORDER BY n_linha",
                    (cid, pno),
                ).fetchall()
            ]
            i_txt = [
                r[0]
                for r in conn.execute(
                    "SELECT texto FROM bru_linha WHERE arquivo_id = ? AND pagina = 1 AND eh_marca_dagua = 0 ORDER BY n_linha",
                    (iid,),
                ).fetchall()
            ]
            if c_txt == i_txt:
                pags_ok += 1
            else:
                pags_div += 1
    sev5 = "gate_ok" if pags_ok == 847 and pags_div == 0 else "gate_falha"
    _registrar(
        "gate:consolidado_vs_individual_goiania",
        "gate_consolidado_vs_individual_goiania",
        sev5,
        ["bru_arquivo", "bru_linha"],
        {"paginas_identicas": pags_ok, "paginas_divergentes": pags_div},
        "ok" if sev5 == "gate_ok" else "aberto",
        f"Espelhamento Goiania consolidado x individual verificado ({pags_ok}/847 paginas identicas).",
    )

    # Gate 6: Extratos bancarios (equacao de saldo + Resumo por mes de Goiania)
    diffs_saldo_mov: list[dict[str, Any]] = []
    saldos_iniciais = {
        r[0].replace("param:extrato:", "").split(":")[0]: int(r[1].split("|")[1].strip())
        for r in conn.execute(
            "SELECT chave, valor_texto FROM ext_parametro_planilha WHERE rotulo = 'Saldo Inicial'"
        ).fetchall()
        if "| " in str(r[1])
    }
    for conta in ("matriz_2025", "matriz_2026", "filial", "goiania"):
        movs = conn.execute(
            """
            SELECT n_linha, data_movimento, debito_centavos, credito_centavos, saldo_centavos
            FROM ext_extrato_linha
            WHERE conta_codigo = ?
            ORDER BY n_linha
            """,
            (conta,),
        ).fetchall()
        # Saldo imediatamente anterior ao 1o movimento (quando matriz_2025 inicia em 17641250 etc.)
        if movs:
            primeiro_esp = movs[0][4] + (movs[0][2] or 0) - (movs[0][3] or 0)
            saldo_corrente = primeiro_esp
            for nl, dt, deb, cred, sal in movs:
                saldo_corrente = saldo_corrente - (deb or 0) + (cred or 0)
                if saldo_corrente != sal:
                    diffs_saldo_mov.append({"conta": conta, "n_linha": nl, "calc": saldo_corrente, "reg": sal})
                    saldo_corrente = sal

    # Conferir Resumo por mes de Goiania contra agregacao de ext_extrato_linha
    resumo_diffs: list[dict[str, Any]] = []
    resumos = conn.execute(
        "SELECT rotulo, valor_texto FROM ext_parametro_planilha WHERE chave LIKE 'param:goiania_resumo:%'"
    ).fetchall()
    # Verificar via abas ou ordem de mes em goiania
    meses_map = {
        "Janeiro/2026": "2026-01", "Fevereiro/2026": "2026-02", "Março/2026": "2026-03",
        "Abril/2026": "2026-04", "Maio/2026": "2026-05", "Junho/2026": "2026-06",
        "Julho/2026": "2026-07", "Agosto/2026": "2026-08",
    }
    for rot, vtxt in resumos:
        mes_nome = rot.replace("Resumo ", "").strip()
        ym = meses_map.get(mes_nome)
        if not ym:
            continue
        dados = json.loads(vtxt)
        agg = conn.execute(
            """
            SELECT COALESCE(SUM(credito_centavos), 0), COALESCE(SUM(debito_centavos), 0),
                   (SELECT saldo_centavos FROM ext_extrato_linha WHERE conta_codigo='goiania' AND data_movimento LIKE ? ORDER BY n_linha DESC LIMIT 1)
            FROM ext_extrato_linha
            WHERE conta_codigo = 'goiania' AND data_movimento LIKE ?
            """,
            (f"{ym}%", f"{ym}%"),
        ).fetchone()
        if (dados["creditos_centavos"], dados["debitos_centavos"], dados["saldo_final_centavos"]) != (
            int(agg[0]),
            int(agg[1]),
            int(agg[2]),
        ):
            resumo_diffs.append({"mes": ym, "resumo": dados, "agg": agg})

    sev6 = "gate_ok" if not diffs_saldo_mov and not resumo_diffs else "gate_falha"
    _registrar(
        "gate:extratos_saldos_recalculados",
        "gate_extratos_saldos_recalculados",
        sev6,
        ["ext_extrato_linha", "ext_parametro_planilha"],
        {
            "divergencias_linha": len(diffs_saldo_mov),
            "divergencias_resumo_goiania": len(resumo_diffs),
            "saldos_iniciais_amostra": len(saldos_iniciais),
        },
        "ok" if sev6 == "gate_ok" else "aberto",
        f"Saldos dos extratos verificados ({len(diffs_saldo_mov)} diffs linha, {len(resumo_diffs)} diffs resumo Goiania).",
    )

    # Gate 7: Pagina HTML vazia do SIGAA verificada (preservando regra='sigaa_html_vazio' da Camada 1)
    vazia_conf = conn.execute(
        "SELECT chave, registros_json, descricao FROM conferencia WHERE regra = 'sigaa_html_vazio'"
    ).fetchall()
    _registrar(
        "gate:sigaa_html_vazio",
        "gate_sigaa_html_vazio",
        "alerta" if vazia_conf else "gate_falha",
        [r[0] for r in vazia_conf] or ["sigaa_html_vazio"],
        {"qtd_conferencias_html_vazio": len(vazia_conf), "chaves": [r[0] for r in vazia_conf]},
        "registrado" if vazia_conf else "aberto",
        f"Verificada a existencia de {len(vazia_conf)} alerta(s) 'sigaa_html_vazio' preservado(s) da Camada 1.",
    )

    # Gate 8: Integridade referencial e cobertura de evidencia na Camada 3
    if incluir_camada3:
        fk_err = conn.execute("PRAGMA foreign_key_check").fetchall()
        nrm_tabs = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'nrm_%' ORDER BY name"
            ).fetchall()
        ]
        vazias = [t for t in nrm_tabs if conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0]
        sem_ev = [
            t
            for t in nrm_tabs
            if conn.execute("SELECT COUNT(*) FROM evidencia WHERE tabela_destino = ?", (t,)).fetchone()[0] == 0
        ]
        n_lanc_c2 = conn.execute("SELECT COUNT(*) FROM ext_diario_lancamento").fetchone()[0]
        n_lanc_c3 = conn.execute("SELECT COUNT(*) FROM nrm_lancamento").fetchone()[0]
        n_mov_c2 = conn.execute("SELECT COUNT(*) FROM ext_extrato_linha").fetchone()[0]
        n_mov_c3 = conn.execute("SELECT COUNT(*) FROM nrm_movimento_bancario").fetchone()[0]
        paridade_ok = (n_lanc_c2 == n_lanc_c3) and (n_mov_c2 == n_mov_c3)
        sev8 = "gate_ok" if (not fk_err and not vazias and not sem_ev and paridade_ok) else "gate_falha"
        _registrar(
            "gate:integridade_camada3",
            "gate_integridade_camada3",
            sev8,
            ["nrm_*", "evidencia"],
            {
                "fk_erros": len(fk_err),
                "tabelas_nrm_totais": len(nrm_tabs),
                "tabelas_nrm_vazias": vazias,
                "tabelas_sem_evidencia": sem_ev,
                "lancamentos_c2_c3": [n_lanc_c2, n_lanc_c3],
                "movimentos_c2_c3": [n_mov_c2, n_mov_c3],
            },
            "ok" if sev8 == "gate_ok" else "aberto",
            f"Integridade Camada 3: {len(nrm_tabs) - len(vazias)}/{len(nrm_tabs)} tabelas populadas, {len(sem_ev)} sem evidencia, {len(fk_err)} erros de FK.",
        )

    return {"gates_ok": ok, "gates_falha": falhas, "alertas_divergencias": alertas}
