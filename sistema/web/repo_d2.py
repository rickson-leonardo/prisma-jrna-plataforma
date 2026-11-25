"""Repositorio PostgreSQL das Estacoes 7, 8 e 9 do Dossie 2 (Rota Sul Importadora)."""

from __future__ import annotations

from typing import Any

from sistema.erp.motor_folha import recalcular_folha_d2, validar_coerencia_dossie2
from sistema.pg.db import conectar_pg
from sistema.web.repo import (
    EMPRESA_CHAVE_D1,
    EMPRESA_CHAVE_D2,
    _slug,
    parse_int_br,
    parse_reais_centavos,
)


def _emp_d2(cur: Any) -> dict[str, Any]:
    cur.execute(
        """
        SELECT e.*, p.nome_canonico AS razao_social_pessoa
        FROM erp.empresa e JOIN erp.pessoa p ON p.id = e.pessoa_id
        WHERE e.chave = %s
        """,
        (EMPRESA_CHAVE_D2,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Empresa {EMPRESA_CHAVE_D2} nao encontrada.")
    d = dict(row)
    d["dossie"] = "D2"
    return d


# =============================================================================
# ESTACAO 7: ONBOARDING, CONTRATOS (P2) E DILIGENCIA (P3)
# =============================================================================
def carregar_onboarding(tipo_filtro: str = "todos") -> dict[str, Any]:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            cur.execute(
                "SELECT * FROM erp.contrato_servico WHERE empresa_id = %s ORDER BY ordem, id",
                (emp_id,),
            )
            contratos = cur.fetchall()
            where = "WHERE empresa_id = %s"
            params: list[Any] = [emp_id]
            if tipo_filtro in ("documento", "pergunta", "pendencia"):
                where += " AND tipo = %s"
                params.append(tipo_filtro)
            cur.execute(f"SELECT * FROM erp.diligencia_item {where} ORDER BY ordem, id", params)
            diligencias = cur.fetchall()

            # Dados oficiais da contratada (PRISMA JRNA) em leitura do Dossie 1 (zero redigitacao)
            cur.execute(
                """
                SELECT e.nome_curto, p.nome_canonico, enq.registro_crc,
                       (SELECT pi.valor FROM erp.pessoa_identificador pi WHERE pi.pessoa_id = e.pessoa_id AND pi.tipo_id = 'CNPJ' LIMIT 1) AS cnpj,
                       (SELECT pi.valor FROM erp.pessoa_identificador pi WHERE pi.pessoa_id = enq.responsavel_tecnico_pessoa_id AND pi.tipo_id = 'CRC' LIMIT 1) AS rt_crc,
                       rt.nome_canonico AS rt_nome,
                       est.endereco AS sede
                FROM erp.empresa e
                JOIN erp.pessoa p ON p.id = e.pessoa_id
                LEFT JOIN erp.estabelecimento est ON est.empresa_id = e.id
                LEFT JOIN erp.enquadramento_historico enq ON enq.empresa_id = e.id
                LEFT JOIN erp.pessoa rt ON rt.id = enq.responsavel_tecnico_pessoa_id
                WHERE e.chave = %s LIMIT 1
                """,
                (EMPRESA_CHAVE_D1,),
            )
            escritorio = cur.fetchone()
        return {
            "empresa": emp,
            "contratos": contratos,
            "diligencias": diligencias,
            "escritorio": escritorio,
            "tipo_filtro": tipo_filtro,
        }


def salvar_contrato_servico(cs_id: int | None, form: dict[str, str]) -> int:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            hon = parse_reais_centavos(form.get("honorario_mensal_reais"), 0)
            vh = parse_reais_centavos(form.get("valor_hora_reais"), 12500)
            hm = parse_int_br(form.get("horas_mes_estimadas"), 0)
            dec13 = form.get("tem_decimo_terceiro") == "on"
            vig = (form.get("vigencia_inicio") or "").strip() or None
            if cs_id is None:
                cod = form.get("codigo_documento", "proposta")
                cur.execute("SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM erp.contrato_servico WHERE empresa_id = %s", (emp_id,))
                ord_ = parse_int_br(form.get("ordem"), int(cur.fetchone()["prox"]))
                cur.execute(
                    """
                    INSERT INTO erp.contrato_servico
                        (chave, empresa_id, codigo_documento, ordem, titulo, honorario_mensal_centavos,
                         tem_decimo_terceiro, valor_hora_centavos, horas_mes_estimadas, vigencia_inicio,
                         foro, escopo_resumo, conteudo_md, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s)
                    RETURNING id
                    """,
                    (
                        f"cs:d2:usr:{cod}:{_slug(form['titulo'])[:20]}", emp_id, cod, ord_,
                        form["titulo"].strip(), hon, dec13, vh, hm, vig,
                        (form.get("foro") or "Goiânia-GO").strip(), (form.get("escopo_resumo") or "").strip(),
                        (form.get("conteudo_md") or "").strip(), form["status_validacao"],
                        (form.get("justificativa_contadora") or "").strip() or None,
                    ),
                )
                cs_id = int(cur.fetchone()["id"])
            else:
                cur.execute(
                    """
                    UPDATE erp.contrato_servico
                    SET titulo = %s, honorario_mensal_centavos = %s, tem_decimo_terceiro = %s,
                        valor_hora_centavos = %s, horas_mes_estimadas = %s, vigencia_inicio = %s,
                        foro = %s, escopo_resumo = %s, conteudo_md = %s,
                        origem_registro = 'usuario', status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        form["titulo"].strip(), hon, dec13, vh, hm, vig,
                        (form.get("foro") or "Goiânia-GO").strip(), (form.get("escopo_resumo") or "").strip(),
                        (form.get("conteudo_md") or "").strip(), form["status_validacao"],
                        (form.get("justificativa_contadora") or "").strip() or None, cs_id, emp_id,
                    ),
                )
        validar_coerencia_dossie2(conn, emp_id)
        conn.commit()
    return cs_id


def salvar_diligencia(dil_id: int | None, form: dict[str, str]) -> int:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            dt = (form.get("data_interacao") or "").strip() or None
            if dil_id is None:
                cod = form["codigo"].strip().upper()
                cur.execute("SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM erp.diligencia_item WHERE empresa_id = %s", (emp_id,))
                ord_ = parse_int_br(form.get("ordem"), int(cur.fetchone()["prox"]))
                cur.execute(
                    """
                    INSERT INTO erp.diligencia_item
                        (chave, empresa_id, tipo, codigo, ordem, ator, tema, enunciado, resposta_literal,
                         fonte_evidencia, data_interacao, responsavel, prazo_texto, risco, status_item,
                         origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s)
                    RETURNING id
                    """,
                    (
                        f"dil:d2:usr:{_slug(cod)}_{ord_}", emp_id, form["tipo"], cod, ord_, form["ator"],
                        form.get("tema", "").strip(), form["enunciado"].strip(),
                        (form.get("resposta_literal") or "").strip() or None,
                        (form.get("fonte_evidencia") or "").strip() or None, dt,
                        (form.get("responsavel") or "").strip() or None,
                        (form.get("prazo_texto") or "").strip() or None,
                        (form.get("risco") or "medio").strip(), form["status_item"],
                        form["status_validacao"], (form.get("justificativa_contadora") or "").strip() or None,
                    ),
                )
                dil_id = int(cur.fetchone()["id"])
            else:
                cur.execute(
                    """
                    UPDATE erp.diligencia_item
                    SET ator = %s, tema = %s, enunciado = %s, resposta_literal = %s, fonte_evidencia = %s,
                        data_interacao = %s, responsavel = %s, prazo_texto = %s, risco = %s, status_item = %s,
                        origem_registro = 'usuario', status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        form["ator"], form.get("tema", "").strip(), form["enunciado"].strip(),
                        (form.get("resposta_literal") or "").strip() or None,
                        (form.get("fonte_evidencia") or "").strip() or None, dt,
                        (form.get("responsavel") or "").strip() or None,
                        (form.get("prazo_texto") or "").strip() or None,
                        (form.get("risco") or "medio").strip(), form["status_item"],
                        form["status_validacao"], (form.get("justificativa_contadora") or "").strip() or None,
                        dil_id, emp_id,
                    ),
                )
        validar_coerencia_dossie2(conn, emp_id)
        conn.commit()
    return dil_id


def excluir_diligencia(dil_id: int) -> None:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            cur.execute("DELETE FROM erp.diligencia_item WHERE id = %s AND empresa_id = %s", (dil_id, emp_id))
        validar_coerencia_dossie2(conn, emp_id)
        conn.commit()


# =============================================================================
# ESTACAO 8: DEPARTAMENTO PESSOAL, TABELAS 2026 E ESOCIAL (P4)
# =============================================================================
def carregar_dp() -> dict[str, Any]:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            cur.execute("SELECT * FROM erp.contrato_trabalho WHERE empresa_id = %s ORDER BY codigo_empregado, id", (emp_id,))
            contratos = cur.fetchall()
            cur.execute("SELECT * FROM erp.parametro_legal WHERE empresa_id = %s ORDER BY categoria, ordem, id", (emp_id,))
            parametros = cur.fetchall()
            cur.execute("SELECT * FROM erp.esocial_evento WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
            esocial = cur.fetchall()
        return {"empresa": emp, "contratos": contratos, "parametros": parametros, "esocial": esocial}


def salvar_contrato_trabalho(ct_id: int, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            sal = parse_reais_centavos(form.get("salario_base_reais"), 0)
            piso = parse_reais_centavos(form.get("piso_cct_reais"), 0)
            com_pct = round(float((form.get("comissao_pct") or "0").replace(",", ".")) * 10_000)
            vt_tar = parse_reais_centavos(form.get("vt_tarifa_reais"), 430)
            vr_dia = parse_reais_centavos(form.get("vr_valor_dia_reais"), 0)
            cur.execute(
                """
                UPDATE erp.contrato_trabalho
                SET nome_empregado = %s, cpf_ficticio = %s, cargo = %s, departamento = %s, cbo = %s,
                    data_admissao = %s, experiencia_dias_1 = %s, experiencia_dias_2 = %s,
                    salario_base_centavos = %s, piso_cct_centavos = %s, comissao_pct_micro = %s,
                    intervalo_minutos = %s, jornada_descricao = %s,
                    vt_optante = %s, vt_passagens_dia = %s, vt_tarifa_centavos = %s,
                    vr_elegivel = %s, vr_valor_dia_centavos = %s,
                    aso_status = %s, aso_observacao = %s,
                    qtd_dependentes_ir = %s, qtd_dependentes_sf = %s,
                    origem_registro = 'usuario', status_validacao = %s, justificativa_contadora = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    form["nome_empregado"].strip(), (form.get("cpf_ficticio") or "").strip(),
                    form["cargo"].strip(), form["departamento"], form["cbo"].strip(), form["data_admissao"],
                    parse_int_br(form.get("experiencia_dias_1"), 45), parse_int_br(form.get("experiencia_dias_2"), 45),
                    sal, piso, com_pct, parse_int_br(form.get("intervalo_minutos"), 60),
                    form.get("jornada_descricao", "").strip(), form.get("vt_optante") == "on",
                    parse_int_br(form.get("vt_passagens_dia"), 4), vt_tar,
                    form.get("vr_elegivel") == "on", vr_dia, form["aso_status"],
                    form.get("aso_observacao", "").strip(), parse_int_br(form.get("qtd_dependentes_ir"), 0),
                    parse_int_br(form.get("qtd_dependentes_sf"), 0), form["status_validacao"],
                    (form.get("justificativa_contadora") or "").strip() or None, ct_id, emp_id,
                ),
            )
        validar_coerencia_dossie2(conn, emp_id)
        conn.commit()


def salvar_parametro_legal(par_id: int, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            lim = parse_reais_centavos(form.get("limite_reais"), -1)
            lim_val = None if (form.get("limite_reais") or "").strip() == "" else lim
            ded = parse_reais_centavos(form.get("deducao_reais"), -1)
            ded_val = None if (form.get("deducao_reais") or "").strip() == "" else ded
            val = parse_reais_centavos(form.get("valor_reais"), -1)
            val_val = None if (form.get("valor_reais") or "").strip() == "" else val
            aliq_str = (form.get("aliquota_pct") or "").strip().replace(",", ".")
            aliq_val = None if not aliq_str else round(float(aliq_str) * 10_000)
            cur.execute(
                """
                UPDATE erp.parametro_legal
                SET descricao = %s, limite_centavos = %s, aliquota_micro = %s, deducao_centavos = %s,
                    valor_centavos = %s, norma_citada = %s, link_oficial = %s, regra_texto = %s,
                    origem_registro = 'usuario', status_validacao = %s, justificativa_contadora = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    form["descricao"].strip(), lim_val, aliq_val, ded_val, val_val,
                    form.get("norma_citada", "").strip(), (form.get("link_oficial") or "").strip() or None,
                    form.get("regra_texto", "").strip(), form["status_validacao"],
                    (form.get("justificativa_contadora") or "").strip() or None, par_id, emp_id,
                ),
            )
        recalcular_folha_d2(conn)
        conn.commit()


def salvar_esocial_evento(ev_id: int, form: dict[str, str]) -> None:
    status_envio = form["status_envio"]
    recibo = (form.get("numero_recibo") or "").strip() or None
    if recibo and status_envio != "transmitido":
        raise ValueError("Número de recibo só pode ser preenchido quando o status do evento for 'Transmitido'.")
    if status_envio == "transmitido" and not recibo:
        raise ValueError("Documento != evento: para marcar como 'Transmitido', informe o número de recibo real.")
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            cur.execute(
                """
                UPDATE erp.esocial_evento
                SET prazo_legal = %s, status_envio = %s, numero_recibo = %s, observacao = %s,
                    origem_registro = 'usuario', status_validacao = %s, justificativa_contadora = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    form.get("prazo_legal", "").strip(), status_envio, recibo,
                    form.get("observacao", "").strip(), form["status_validacao"],
                    (form.get("justificativa_contadora") or "").strip() or None, ev_id, emp_id,
                ),
            )
        validar_coerencia_dossie2(conn, emp_id)
        conn.commit()


# =============================================================================
# ESTACAO 9: FOLHA 09/2026, PARTIDAS DOBRADAS E AUDITORIA (P5-P7)
# =============================================================================
def carregar_folha() -> dict[str, Any]:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            cur.execute("SELECT * FROM erp.folha_competencia WHERE empresa_id = %s ORDER BY competencia DESC LIMIT 1", (emp_id,))
            comp = cur.fetchone()
            itens = []
            if comp:
                cur.execute(
                    """
                    SELECT fi.*, ct.codigo_empregado, ct.nome_empregado
                    FROM erp.folha_item fi
                    JOIN erp.contrato_trabalho ct ON ct.id = fi.contrato_trabalho_id
                    WHERE fi.competencia_id = %s
                    ORDER BY ct.codigo_empregado, fi.ordem, fi.id
                    """,
                    (comp["id"],),
                )
                itens = cur.fetchall()
            cur.execute(
                """
                SELECT l.id AS lancamento_id, l.numero_lancamento, l.data_lancamento, l.historico, l.tag_ref,
                       p.ordem, cc.codigo AS conta_codigo, cc.nome AS conta_nome, p.dc, p.valor_centavos
                FROM erp.lancamento l
                JOIN erp.partida p ON p.lancamento_id = l.id
                JOIN erp.conta_contabil cc ON cc.id = p.conta_id
                WHERE l.empresa_id = %s AND l.origem_registro = 'motor_calculo'
                ORDER BY l.numero_lancamento, p.ordem
                """,
                (emp_id,),
            )
            partidas = cur.fetchall()
            cur.execute("SELECT * FROM erp.auditoria_folha WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
            auditoria = cur.fetchall()
            cur.execute("SELECT * FROM auditoria.alerta_coerencia WHERE empresa_id = %s AND dossie = 'D2' ORDER BY id", (emp_id,))
            alertas = cur.fetchall()
        tot_d = sum(int(p["valor_centavos"]) for p in partidas if p["dc"] == "D")
        tot_c = sum(int(p["valor_centavos"]) for p in partidas if p["dc"] == "C")
        return {
            "empresa": emp,
            "comp": comp,
            "itens": itens,
            "partidas": partidas,
            "tot_debito": tot_d,
            "tot_credito": tot_c,
            "auditoria": auditoria,
            "alertas": alertas,
        }


def salvar_competencia_e_recalcular(comp_id: int, form: dict[str, str]) -> dict[str, Any]:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            vendas = parse_reais_centavos(form.get("vendas_liquidas_e2_reais"), 6000000)
            dp = (form.get("data_pagamento") or "").strip() or None
            cur.execute(
                """
                UPDATE erp.folha_competencia
                SET vendas_liquidas_e2_centavos = %s, dias_trabalhados_e1 = %s, dias_trabalhados_e2 = %s,
                    dias_uteis_comissao_e2 = %s, domingos_feriados_e2 = %s, dias_uteis_vt_e1 = %s,
                    dias_uteis_vt_e2 = %s, dias_uteis_vr_e1 = %s, cenario_negocial = %s,
                    data_pagamento = %s, origem_registro = 'usuario',
                    status_validacao = %s, justificativa_contadora = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    vendas, parse_int_br(form.get("dias_trabalhados_e1"), 15),
                    parse_int_br(form.get("dias_trabalhados_e2"), 10),
                    parse_int_br(form.get("dias_uteis_comissao_e2"), 9),
                    parse_int_br(form.get("domingos_feriados_e2"), 1),
                    parse_int_br(form.get("dias_uteis_vt_e1"), 11),
                    parse_int_br(form.get("dias_uteis_vt_e2"), 9),
                    parse_int_br(form.get("dias_uteis_vr_e1"), 11),
                    form.get("cenario_negocial", "A_desconta"), dp,
                    form["status_validacao"], (form.get("justificativa_contadora") or "").strip() or None,
                    comp_id, emp_id,
                ),
            )
        res = recalcular_folha_d2(conn, comp_id)
        conn.commit()
    return res


def executar_recalculo_folha_d2() -> dict[str, Any]:
    with conectar_pg() as conn:
        res = recalcular_folha_d2(conn)
        conn.commit()
    return res


def salvar_auditoria_item(aud_id: int | None, form: dict[str, str]) -> int:
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            emp = _emp_d2(cur)
            emp_id = int(emp["id"])
            if aud_id is None:
                cod = form["codigo"].strip().upper()
                cur.execute("SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM erp.auditoria_folha WHERE empresa_id = %s", (emp_id,))
                ord_ = parse_int_br(form.get("ordem"), int(cur.fetchone()["prox"]))
                cur.execute(
                    """
                    INSERT INTO erp.auditoria_folha
                        (chave, empresa_id, tipo_registro, codigo, ordem, titulo, norma_referencia,
                         objetivo_ou_evidencia, procedimento_ou_risco, conclusao_ou_correcao,
                         responsavel, prazo_texto, situacao_achado, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s)
                    RETURNING id
                    """,
                    (
                        f"aud:d2:usr:{_slug(cod)}_{ord_}", emp_id, form.get("tipo_registro", "achado"),
                        cod, ord_, form["titulo"].strip(), form.get("norma_referencia", "").strip(),
                        form.get("objetivo_ou_evidencia", "").strip(), form.get("procedimento_ou_risco", "").strip(),
                        form.get("conclusao_ou_correcao", "").strip(),
                        (form.get("responsavel") or "").strip() or None,
                        (form.get("prazo_texto") or "").strip() or None,
                        form.get("situacao_achado", "aberto_cliente"), form["status_validacao"],
                        (form.get("justificativa_contadora") or "").strip() or None,
                    ),
                )
                aud_id = int(cur.fetchone()["id"])
            else:
                cur.execute(
                    """
                    UPDATE erp.auditoria_folha
                    SET titulo = %s, norma_referencia = %s, objetivo_ou_evidencia = %s,
                        procedimento_ou_risco = %s, conclusao_ou_correcao = %s,
                        responsavel = %s, prazo_texto = %s, situacao_achado = %s,
                        origem_registro = 'usuario', status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        form["titulo"].strip(), form.get("norma_referencia", "").strip(),
                        form.get("objetivo_ou_evidencia", "").strip(), form.get("procedimento_ou_risco", "").strip(),
                        form.get("conclusao_ou_correcao", "").strip(),
                        (form.get("responsavel") or "").strip() or None,
                        (form.get("prazo_texto") or "").strip() or None,
                        form.get("situacao_achado", "aberto_cliente"), form["status_validacao"],
                        (form.get("justificativa_contadora") or "").strip() or None, aud_id, emp_id,
                    ),
                )
        validar_coerencia_dossie2(conn, emp_id)
        conn.commit()
    return aud_id
