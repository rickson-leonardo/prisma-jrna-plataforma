"""Repositorio PostgreSQL para operacao CRUD e investigacao do Dossie 1 (Prisma JRNA)."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sistema.erp.motor_contabil import recalcular_cenario_no_banco, recalcular_cenarios_empresa, validar_coerencia_dossie1
from sistema.pg.db import conectar_pg

EMPRESA_CHAVE_D1 = "emp:prisma_jrna_g07"
EMPRESA_CHAVE_D2 = "emp:rota_sul_d2"
DOSSIES_VALIDOS = ("D1", "D2")
EMPRESAS_POR_DOSSIE = {"D1": EMPRESA_CHAVE_D1, "D2": EMPRESA_CHAVE_D2}


def dossie_em_foco(dossie: str | None = None) -> str:
    if dossie and str(dossie).strip().upper() in DOSSIES_VALIDOS:
        return str(dossie).strip().upper()
    try:
        from flask import has_request_context, request, session

        if has_request_context():
            q = (request.args.get("dossie") or "").strip().upper()
            if q in DOSSIES_VALIDOS:
                return q
            s = (session.get("dossie_ativo") or "").strip().upper()
            if s in DOSSIES_VALIDOS:
                return s
    except Exception:  # noqa: BLE001
        pass
    return "D1"


def _validar_coerencia(conn: Any, emp_id: int) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute("SELECT chave FROM erp.empresa WHERE id = %s", (emp_id,))
        r = cur.fetchone()
        chave = r["chave"] if r else EMPRESA_CHAVE_D1
    if chave == EMPRESA_CHAVE_D2:
        try:
            from sistema.erp.motor_folha import validar_coerencia_dossie2

            return validar_coerencia_dossie2(conn, emp_id)
        except ImportError:
            return []
    return validar_coerencia_dossie1(conn, emp_id)


def _slug(txt: str) -> str:
    s = txt.lower().strip()
    trocas = {
        "á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e",
        "í": "i", "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    for k, v in trocas.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "item"


def parse_reais_centavos(val: str | None, default: int = 0) -> int:
    """Converte string monetaria pt-BR ou US ('1.500,00', '1.500' ou '1500.00') em centavos inteiros."""
    if val is None:
        return default
    s = str(val).strip().replace("R$", "").replace(" ", "")
    if not s:
        return default
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        dec = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetario invalido: {val!r}") from exc
    return int((dec * 100).quantize(Decimal("1")))


def parse_pct_micro(val: str | None, default: int = 0) -> int:
    """Converte percentual ('15,0' ou '15.0') em micro-unidade (15% -> 150000)."""
    if val is None:
        return default
    s = str(val).strip().replace("%", "").replace(" ", "").replace(",", ".")
    if not s:
        return default
    try:
        dec = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"Percentual invalido: {val!r}") from exc
    return int((dec * 10_000).quantize(Decimal("1")))


def parse_int_br(val: str | None, default: int = 0) -> int:
    """Converte inteiro com separador de milhar ('20.000' -> 20000) sem truncar decimal."""
    if val is None:
        return default
    s = str(val).strip().replace(" ", "")
    if not s:
        return default
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", s):
        s = s.replace(".", "")
    if "," in s:
        s = s.split(",", 1)[0].replace(".", "")
    try:
        return int(s)
    except ValueError as exc:
        raise ValueError(f"Numero inteiro invalido: {val!r}") from exc


def _pessoas_ids(cur: Any, emp: dict[str, Any]) -> list[int]:
    emp_id = int(emp["id"])
    cur.execute("SELECT socio_pessoa_id FROM erp.participacao_societaria WHERE empresa_id = %s", (emp_id,))
    ids = {int(emp["pessoa_id"])}
    ids.update(int(r["socio_pessoa_id"]) for r in cur.fetchall())
    return sorted(ids)


_pessoas_ids_d1 = _pessoas_ids


def empresa_em_foco(conn: Any, dossie: str | None = None) -> dict[str, Any]:
    cod = dossie_em_foco(dossie)
    chave = EMPRESAS_POR_DOSSIE[cod]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.*, p.nome_canonico AS razao_social_pessoa
            FROM erp.empresa e
            JOIN erp.pessoa p ON p.id = e.pessoa_id
            WHERE e.chave = %s
            """,
            (chave,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Empresa {chave} nao encontrada no banco.")
        d = dict(row)
        d["dossie"] = cod
        return d


def obter_empresa_d1(conn: Any) -> dict[str, Any]:
    return empresa_em_foco(conn)


def carregar_painel_geral() -> dict[str, Any]:
    """Carrega visao executiva, placar de conformidade, backlog quarentena e alertas de coerencia."""
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        cod = emp["dossie"]
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM auditoria.alerta_coerencia WHERE empresa_id = %s ORDER BY CASE severidade WHEN 'critico' THEN 1 WHEN 'alerta' THEN 2 ELSE 3 END, id", (emp_id,))
            alertas = cur.fetchall()

            cur.execute("SELECT * FROM auditoria.vw_placar_conformidade WHERE empresa_id = %s ORDER BY matriz", (emp_id,))
            placar_matrizes = cur.fetchall()

            cur.execute(
                """
                SELECT modulo,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados,
                       COUNT(*) FILTER (WHERE status_validacao = 'alerta_inconsistencia') AS inconsistencias,
                       COUNT(*) FILTER (WHERE status_validacao = 'pendente_revisao') AS pendentes
                FROM auditoria.vw_pendencias_quarentena
                WHERE dossie = %s
                GROUP BY modulo
                ORDER BY modulo
                """,
                (cod,),
            )
            quarentena_resumo = cur.fetchall()

            cur.execute(
                """
                SELECT c.*, d.receita_bruta_centavos, d.das_centavos, d.lucro_liquido_centavos,
                       d.fator_r_anual_micro, d.bp_ativo_total_centavos, d.bp_diferenca_centavos,
                       d0.indicadores_json
                FROM erp.orcamento_cenario c
                LEFT JOIN erp.orcamento_demonstrativo_anual d ON d.cenario_id = c.id AND d.ano_ordem = 1
                LEFT JOIN erp.orcamento_demonstrativo_anual d0 ON d0.cenario_id = c.id AND d0.ano_ordem = 0
                WHERE c.empresa_id = %s AND c.eh_oficial = true
                ORDER BY c.id DESC LIMIT 1
                """,
                (emp_id,),
            )
            cen_oficial = cur.fetchone()

            folha_resumo = None
            if cod == "D2":
                cur.execute(
                    "SELECT * FROM erp.folha_competencia WHERE empresa_id = %s ORDER BY competencia DESC LIMIT 1",
                    (emp_id,),
                )
                folha_resumo = cur.fetchone()

        return {
            "empresa": emp,
            "alertas": alertas,
            "placar_matrizes": placar_matrizes,
            "quarentena_resumo": quarentena_resumo,
            "cenario_oficial": cen_oficial,
            "folha_resumo": folha_resumo,
        }


def revalidar_coerencia() -> list[dict[str, Any]]:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        if emp.get("chave") != EMPRESA_CHAVE_D2:
            # D1: o M1 dos cenarios vem do enquadramento (Cadastro); recalcula antes de auditar
            recalcular_cenarios_empresa(conn, int(emp["id"]))
        alertas = _validar_coerencia(conn, int(emp["id"]))
        conn.commit()
    return alertas


# =============================================================================
# ESTACAO 1: CADASTRO SOCIETARIO, QSA, IDENTIFICADORES E ENQUADRAMENTO
# =============================================================================
def carregar_cadastro() -> dict[str, Any]:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM erp.estabelecimento WHERE empresa_id = %s ORDER BY id", (emp_id,))
            estabelecimentos = cur.fetchall()

            cur.execute(
                """
                SELECT ps.*, p.nome_canonico, p.chave AS pessoa_chave, p.status_validacao AS pessoa_status
                FROM erp.participacao_societaria ps
                JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id
                WHERE ps.empresa_id = %s
                ORDER BY ps.id
                """,
                (emp_id,),
            )
            socios = cur.fetchall()

            pessoa_ids = [int(emp["pessoa_id"])] + [int(s["socio_pessoa_id"]) for s in socios]
            cur.execute(
                """
                SELECT pi.*, p.nome_canonico
                FROM erp.pessoa_identificador pi
                JOIN erp.pessoa p ON p.id = pi.pessoa_id
                WHERE pi.pessoa_id = ANY(%s)
                ORDER BY pi.pessoa_id, pi.id
                """,
                (pessoa_ids,),
            )
            identificadores = cur.fetchall()

            cur.execute(
                """
                SELECT p.id, p.chave, p.tipo_pessoa, p.nome_canonico, p.status_validacao, p.apontamento_auditoria
                FROM erp.pessoa p
                WHERE p.id = ANY(%s)
                ORDER BY p.tipo_pessoa DESC, p.nome_canonico
                """,
                (pessoa_ids,),
            )
            pessoas = cur.fetchall()

            cur.execute(
                """
                SELECT enq.*, p.nome_canonico AS rt_nome
                FROM erp.enquadramento_historico enq
                LEFT JOIN erp.pessoa p ON p.id = enq.responsavel_tecnico_pessoa_id
                WHERE enq.empresa_id = %s
                ORDER BY enq.vigente_de DESC, enq.id DESC
                """,
                (emp_id,),
            )
            enquadramentos = cur.fetchall()

        return {
            "empresa": emp,
            "estabelecimentos": estabelecimentos,
            "socios": socios,
            "identificadores": identificadores,
            "pessoas": pessoas,
            "enquadramentos": enquadramentos,
            "soma_quotas_pct": sum(int(s["percentual_micro"] or 0) for s in socios if s["vigente_ate"] is None) / 10_000.0,
            "soma_capital_centavos": sum(int(s["valor_centavos"] or 0) for s in socios if s["vigente_ate"] is None),
        }


def salvar_empresa(form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        nome_curto = form["nome_curto"].strip()
        if not nome_curto:
            raise ValueError("Nome da sociedade nao pode ficar vazio.")
        razao = (form.get("razao_social_pessoa") or "").strip()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE erp.empresa
                SET nome_curto = %s,
                    status_validacao = %s,
                    justificativa_contadora = %s
                WHERE id = %s
                """,
                (nome_curto, form["status_validacao"], form.get("justificativa_contadora", "").strip() or None, emp_id),
            )
            if razao:
                cur.execute(
                    "UPDATE erp.pessoa SET nome_canonico = %s, status_validacao = %s WHERE id = %s",
                    (razao, form["status_validacao"], int(emp["pessoa_id"])),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def criar_ou_salvar_estabelecimento(est_id: int | None, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            if est_id is None:
                chave = f"est:g07:{_slug(form['tipo'])}_{_slug(form['cnpj'])}"
                cur.execute(
                    """
                    INSERT INTO erp.estabelecimento
                        (chave, empresa_id, tipo, cnpj, uf, municipio, endereco, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s)
                    """,
                    (
                        chave, emp_id, form["tipo"], form["cnpj"].strip(),
                        form.get("uf", "DF").strip()[:2].upper(), form.get("municipio", "Brasilia").strip(),
                        form["endereco"].strip(), form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE erp.estabelecimento
                    SET tipo = %s, cnpj = %s, uf = %s, municipio = %s, endereco = %s,
                        status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        form["tipo"], form["cnpj"].strip(), form.get("uf", "DF").strip()[:2].upper(),
                        form.get("municipio", "Brasilia").strip(), form["endereco"].strip(),
                        form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                        est_id, emp_id,
                    ),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_estabelecimento(est_id: int) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erp.estabelecimento WHERE id = %s AND empresa_id = %s", (est_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()


def salvar_identificador(pid_id: int | None, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        eh_ficticio = form.get("eh_ficticio") == "on"
        with conn.cursor() as cur:
            permitidos = set(_pessoas_ids_d1(cur, emp))
            if pid_id is None:
                pessoa_id = int(form["pessoa_id"])
                if pessoa_id not in permitidos:
                    raise PermissionError("Pessoa fora do escopo do Dossie 1.")
                chave = f"pid:usr:{pessoa_id}:{form['tipo_id']}:{_slug(form['valor'])[:24]}"
                cur.execute(
                    """
                    INSERT INTO erp.pessoa_identificador
                        (chave, pessoa_id, tipo_id, valor, eh_ficticio, fonte_chave, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, 'cadastro_usuario', 'usuario', %s, %s)
                    """,
                    (chave, pessoa_id, form["tipo_id"], form["valor"].strip(), eh_ficticio, form["status_validacao"], form.get("justificativa_contadora", "").strip() or None),
                )
            else:
                cur.execute(
                    """
                    UPDATE erp.pessoa_identificador
                    SET tipo_id = %s, valor = %s, eh_ficticio = %s,
                        status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND pessoa_id = ANY(%s)
                    """,
                    (form["tipo_id"], form["valor"].strip(), eh_ficticio, form["status_validacao"], form.get("justificativa_contadora", "").strip() or None, pid_id, list(permitidos)),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_identificador(pid_id: int) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        with conn.cursor() as cur:
            permitidos = _pessoas_ids_d1(cur, emp)
            cur.execute("DELETE FROM erp.pessoa_identificador WHERE id = %s AND pessoa_id = ANY(%s)", (pid_id, permitidos))
        _validar_coerencia(conn, int(emp["id"]))
        conn.commit()


def salvar_socio(ps_id: int | None, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        quotas = parse_int_br(form.get("quotas"), 0)
        valor_cent = parse_reais_centavos(form.get("valor_reais"), 0)
        pct_micro = parse_pct_micro(form.get("percentual"), 0)
        with conn.cursor() as cur:
            if ps_id is None:
                nome = form["nome_canonico"].strip()
                base_slug = _slug(nome)
                chave_pes = f"pes:pf:{base_slug}"
                cur.execute("SELECT id, nome_canonico FROM erp.pessoa WHERE chave = %s", (chave_pes,))
                existente = cur.fetchone()
                if existente and existente["nome_canonico"].strip().lower() == nome.lower():
                    pessoa_id = int(existente["id"])
                else:
                    if existente:
                        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS nxt FROM erp.pessoa")
                        chave_pes = f"pes:pf:{base_slug}_{cur.fetchone()['nxt']}"
                    cur.execute(
                        """
                        INSERT INTO erp.pessoa (chave, tipo_pessoa, nome_canonico, origem_registro, status_validacao)
                        VALUES (%s, 'PF', %s, 'usuario', %s)
                        RETURNING id
                        """,
                        (chave_pes, nome, form["status_validacao"]),
                    )
                    pessoa_id = int(cur.fetchone()["id"])
                chave_ps = f"part:usr:{base_slug}:{pessoa_id}"
                cur.execute(
                    """
                    INSERT INTO erp.participacao_societaria
                        (chave, empresa_id, socio_pessoa_id, quotas, valor_centavos, percentual_micro, papel, vigente_de, fonte_chave, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'cadastro_usuario', 'usuario', %s, %s)
                    """,
                    (chave_ps, emp_id, pessoa_id, quotas, valor_cent, pct_micro, form["papel"].strip(), form.get("vigente_de") or "2026-09-15", form["status_validacao"], form.get("justificativa_contadora", "").strip() or None),
                )
            else:
                cur.execute(
                    """
                    UPDATE erp.participacao_societaria
                    SET quotas = %s, valor_centavos = %s, percentual_micro = %s, papel = %s,
                        status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (quotas, valor_cent, pct_micro, form["papel"].strip(), form["status_validacao"], form.get("justificativa_contadora", "").strip() or None, ps_id, emp_id),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_socio(ps_id: int) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erp.participacao_societaria WHERE id = %s AND empresa_id = %s", (ps_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()


def salvar_enquadramento(enq_id: int, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        sec_raw = [x.strip() for x in (form.get("cnaes_secundarios") or "").split(",") if x.strip()]
        rt_id = int(form["responsavel_tecnico_pessoa_id"]) if form.get("responsavel_tecnico_pessoa_id") else None
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE erp.enquadramento_historico
                SET porte = %s,
                    regime_tributario = %s,
                    cnae_principal = %s,
                    cnaes_secundarios = %s::jsonb,
                    registro_crc = %s,
                    responsavel_tecnico_pessoa_id = %s,
                    status_validacao = %s,
                    justificativa_contadora = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    form["porte"], form["regime_tributario"], form["cnae_principal"].strip(),
                    json.dumps(sec_raw, ensure_ascii=False), form.get("registro_crc", "").strip() or None,
                    rt_id, form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                    enq_id, emp_id,
                ),
            )
        _validar_coerencia(conn, emp_id)
        conn.commit()


# =============================================================================
# ESTACAO 2: INSTRUMENTOS SOCIETARIOS (CONTRATO SOCIAL <-> MOU)
# =============================================================================
def carregar_instrumentos(filtro: str = "todos") -> dict[str, Any]:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            where = "WHERE empresa_id = %s"
            if filtro == "contrato":
                where += " AND aplica_contrato = true"
            elif filtro == "mou":
                where += " AND aplica_mou = true"
            elif filtro == "pendentes":
                where += " AND status_validacao <> 'homologado_contadora'"
            cur.execute(f"SELECT * FROM erp.instrumento_societario_clausula {where} ORDER BY ordem, id", (emp_id,))
            clausulas = cur.fetchall()
            cur.execute(
                """
                SELECT COUNT(*) FILTER (WHERE aplica_contrato) AS cs_total,
                       COUNT(*) FILTER (WHERE aplica_contrato AND status_validacao = 'homologado_contadora') AS cs_homol,
                       COUNT(*) FILTER (WHERE aplica_mou) AS mou_total,
                       COUNT(*) FILTER (WHERE aplica_mou AND status_validacao = 'homologado_contadora') AS mou_homol,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homol
                FROM erp.instrumento_societario_clausula WHERE empresa_id = %s
                """,
                (emp_id,),
            )
            totais = dict(cur.fetchone())
            cur.execute("SELECT * FROM auditoria.alerta_coerencia WHERE empresa_id = %s AND modulo_alvo = 'instrumentos' ORDER BY id", (emp_id,))
            alertas = cur.fetchall()
        return {"empresa": emp, "clausulas": clausulas, "alertas": alertas, "filtro": filtro, "totais": totais}


def criar_clausula(form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM erp.instrumento_societario_clausula WHERE empresa_id = %s", (emp_id,))
            prox = int(cur.fetchone()["prox"])
            ordem = int(form.get("ordem") or prox)
            num_cl = form["numero_clausula"].strip()
            chave = f"inst:usr:{ordem}:{_slug(num_cl)}_{_slug(form['titulo'])[:20]}"
            aplica_cs = form.get("aplica_contrato") == "on"
            aplica_mou = form.get("aplica_mou") == "on"
            txt = form["regra_texto"].strip()
            alc = parse_reais_centavos(form.get("alcada_reais"), 0) or None
            if emp["dossie"] == "D2":
                cur.execute(
                    """
                    INSERT INTO erp.instrumento_societario_clausula
                        (chave, empresa_id, ordem, bloco, codigo_criterio, numero_clausula, titulo, regra_texto,
                         aplica_mou, aplica_contrato, redacao_mou, redacao_contrato, metodo_haveres, quorum_tipo,
                         alcada_centavos, tipo_instrumento, risco_tipo, risco_nivel, providencia, fundamento_legal,
                         responsavel, prazo_texto, versao, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '2a_alteracao', %s, %s, %s, %s, %s, %s, 1, 'usuario', %s, %s)
                    """,
                    (
                        chave, emp_id, ordem, form.get("bloco", "GERAL").strip(), form.get("codigo_criterio", "C-01").strip(),
                        num_cl, form["titulo"].strip(), txt, aplica_mou, aplica_cs,
                        txt if aplica_mou else None, txt if aplica_cs else None,
                        form.get("metodo_haveres", "nao_aplicavel"), form.get("quorum_tipo", "nao_aplicavel"),
                        alc, (form.get("risco_tipo") or "").strip() or None,
                        (form.get("risco_nivel") or "").strip() or None,
                        (form.get("providencia") or "").strip() or None,
                        (form.get("fundamento_legal") or "").strip() or None,
                        (form.get("responsavel") or "").strip() or None,
                        (form.get("prazo_texto") or "").strip() or None,
                        form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO erp.instrumento_societario_clausula
                        (chave, empresa_id, ordem, bloco, codigo_criterio, numero_clausula, titulo, regra_texto,
                         aplica_mou, aplica_contrato, redacao_mou, redacao_contrato, metodo_haveres, quorum_tipo,
                         alcada_centavos, versao, origem_registro, status_validacao, justificativa_contadora)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'usuario', %s, %s)
                    """,
                    (
                        chave, emp_id, ordem, form.get("bloco", "GERAL").strip(), form.get("codigo_criterio", "USR").strip(),
                        num_cl, form["titulo"].strip(), txt, aplica_mou, aplica_cs,
                        txt if aplica_mou else None, txt if aplica_cs else None,
                        form.get("metodo_haveres", "nao_aplicavel"), form.get("quorum_tipo", "nao_aplicavel"),
                        alc, form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                    ),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def salvar_clausula(cl_id: int, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        aplica_cs = form.get("aplica_contrato") == "on"
        aplica_mou = form.get("aplica_mou") == "on"
        txt = form["regra_texto"].strip()
        alc = parse_reais_centavos(form.get("alcada_reais"), 0) or None
        with conn.cursor() as cur:
            if emp["dossie"] == "D2":
                cur.execute(
                    """
                    UPDATE erp.instrumento_societario_clausula
                    SET ordem = %s,
                        bloco = %s,
                        codigo_criterio = %s,
                        numero_clausula = %s,
                        titulo = %s,
                        regra_texto = %s,
                        aplica_contrato = %s,
                        aplica_mou = %s,
                        redacao_contrato = CASE WHEN %s THEN %s ELSE NULL END,
                        redacao_mou = CASE WHEN %s THEN %s ELSE NULL END,
                        metodo_haveres = %s,
                        quorum_tipo = %s,
                        alcada_centavos = %s,
                        risco_tipo = %s,
                        risco_nivel = %s,
                        providencia = %s,
                        fundamento_legal = %s,
                        responsavel = %s,
                        prazo_texto = %s,
                        versao = versao + 1,
                        status_validacao = %s,
                        justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        int(form.get("ordem") or 1), form.get("bloco", "GERAL").strip(), form.get("codigo_criterio", "USR").strip(),
                        form["numero_clausula"].strip(), form["titulo"].strip(), txt,
                        aplica_cs, aplica_mou, aplica_cs, txt, aplica_mou, txt,
                        form.get("metodo_haveres", "nao_aplicavel"), form.get("quorum_tipo", "nao_aplicavel"),
                        alc,
                        (form.get("risco_tipo") or "").strip() or None,
                        (form.get("risco_nivel") or "").strip() or None,
                        (form.get("providencia") or "").strip() or None,
                        (form.get("fundamento_legal") or "").strip() or None,
                        (form.get("responsavel") or "").strip() or None,
                        (form.get("prazo_texto") or "").strip() or None,
                        form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                        cl_id, emp_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE erp.instrumento_societario_clausula
                    SET ordem = %s,
                        bloco = %s,
                        codigo_criterio = %s,
                        numero_clausula = %s,
                        titulo = %s,
                        regra_texto = %s,
                        aplica_contrato = %s,
                        aplica_mou = %s,
                        redacao_contrato = CASE WHEN %s THEN %s ELSE NULL END,
                        redacao_mou = CASE WHEN %s THEN %s ELSE NULL END,
                        metodo_haveres = %s,
                        quorum_tipo = %s,
                        alcada_centavos = %s,
                        versao = versao + 1,
                        status_validacao = %s,
                        justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        int(form.get("ordem") or 1), form.get("bloco", "GERAL").strip(), form.get("codigo_criterio", "USR").strip(),
                        form["numero_clausula"].strip(), form["titulo"].strip(), txt,
                        aplica_cs, aplica_mou, aplica_cs, txt, aplica_mou, txt,
                        form.get("metodo_haveres", "nao_aplicavel"), form.get("quorum_tipo", "nao_aplicavel"),
                        alc, form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                        cl_id, emp_id,
                    ),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_clausula(cl_id: int) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erp.instrumento_societario_clausula WHERE id = %s AND empresa_id = %s", (cl_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()


# =============================================================================
# ESTACAO 3: PARALEGAL DF (WORKFLOW REDESIM / JUCIS-DF / CRC-DF)
# =============================================================================
def carregar_legalizacao() -> dict[str, Any]:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM erp.processo_legalizacao_etapa WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
            etapas = cur.fetchall()
        raias = {
            "socias": [e for e in etapas if e["raia_responsavel"] == "socias"],
            "escritorio_contabil": [e for e in etapas if e["raia_responsavel"] == "escritorio_contabil"],
            "orgaos_publicos": [e for e in etapas if e["raia_responsavel"] == "orgaos_publicos"],
        }
        from sistema.web.bpmn import gerar_svg_bpmn

        return {"empresa": emp, "etapas": etapas, "raias": raias, "bpmn_svg": gerar_svg_bpmn(list(etapas))}


def criar_etapa_legalizacao(form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM erp.processo_legalizacao_etapa WHERE empresa_id = %s", (emp_id,))
            prox = int(cur.fetchone()["prox"])
            ordem = int(form.get("ordem") or prox)
            chave = f"leg:usr:{ordem}:{_slug(form['codigo'])}_{_slug(form['nome_etapa'])[:20]}"
            cur.execute(
                """
                INSERT INTO erp.processo_legalizacao_etapa
                    (chave, empresa_id, ordem, bloco, codigo, nome_etapa, raia_responsavel, orgao, portal_url,
                     data_consulta, entrada_docs, saida_doc, prazo_legal, regra_retorno_exigencia, classificacao_risco,
                     status, protocolo_simulado, origem_registro, status_validacao, justificativa_contadora)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s)
                """,
                (
                    chave, emp_id, ordem, form.get("bloco", "G").strip(), form.get("codigo", "USR").strip(),
                    form["nome_etapa"].strip(), form["raia_responsavel"], form["orgao"].strip(),
                    form.get("portal_url", "").strip() or None, form.get("data_consulta") or None,
                    form["entrada_docs"].strip(), form["saida_doc"].strip(), form.get("prazo_legal", "").strip() or None,
                    form["regra_retorno_exigencia"].strip(), form["classificacao_risco"],
                    form["status"], form.get("protocolo_simulado", "").strip() or None,
                    form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                ),
            )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def salvar_etapa_legalizacao(etapa_id: int, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE erp.processo_legalizacao_etapa
                SET ordem = %s, bloco = %s, codigo = %s, nome_etapa = %s, raia_responsavel = %s,
                    orgao = %s, portal_url = %s, data_consulta = %s, entrada_docs = %s, saida_doc = %s,
                    prazo_legal = %s, regra_retorno_exigencia = %s, classificacao_risco = %s,
                    status = %s, protocolo_simulado = %s,
                    status_validacao = %s, justificativa_contadora = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    int(form.get("ordem") or 1), form.get("bloco", "G").strip(), form.get("codigo", "USR").strip(),
                    form["nome_etapa"].strip(), form["raia_responsavel"], form["orgao"].strip(),
                    form.get("portal_url", "").strip() or None, form.get("data_consulta") or None,
                    form["entrada_docs"].strip(), form["saida_doc"].strip(), form.get("prazo_legal", "").strip() or None,
                    form["regra_retorno_exigencia"].strip(), form["classificacao_risco"],
                    form["status"], form.get("protocolo_simulado", "").strip() or None,
                    form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                    etapa_id, emp_id,
                ),
            )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_etapa_legalizacao(etapa_id: int) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erp.processo_legalizacao_etapa WHERE id = %s AND empresa_id = %s", (etapa_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()


# =============================================================================
# ESTACAO 4: PLANEJAMENTO FINANCEIRO, TRIBUTARIO & VIABILIDADE 36 MESES
# =============================================================================
def carregar_planejamento(cenario_id: int | None = None, ano_mensal: int = 1) -> dict[str, Any]:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.*,
                       d1.receita_bruta_centavos AS a1_receita, d1.das_centavos AS a1_das,
                       d1.lucro_liquido_centavos AS a1_lucro, d1.fator_r_anual_micro AS a1_fator_r,
                       d0.indicadores_json
                FROM erp.orcamento_cenario c
                LEFT JOIN erp.orcamento_demonstrativo_anual d1 ON d1.cenario_id = c.id AND d1.ano_ordem = 1
                LEFT JOIN erp.orcamento_demonstrativo_anual d0 ON d0.cenario_id = c.id AND d0.ano_ordem = 0
                WHERE c.empresa_id = %s
                ORDER BY c.eh_oficial DESC, c.id
                """,
                (emp_id,),
            )
            todos_cenarios = cur.fetchall()
            selecionado = None
            if cenario_id is not None:
                selecionado = next((c for c in todos_cenarios if int(c["id"]) == cenario_id), None)
            if selecionado is None and todos_cenarios:
                selecionado = todos_cenarios[0]

            demonstrativos: list[dict[str, Any]] = []
            mensais: list[dict[str, Any]] = []
            indicadores: dict[str, Any] = {}
            if selecionado is not None:
                sel_id = int(selecionado["id"])
                cur.execute("SELECT * FROM erp.orcamento_demonstrativo_anual WHERE cenario_id = %s ORDER BY ano_ordem", (sel_id,))
                demonstrativos = cur.fetchall()
                if demonstrativos and demonstrativos[0].get("indicadores_json"):
                    indicadores = dict(demonstrativos[0]["indicadores_json"])

                cur.execute(
                    """
                    SELECT * FROM erp.orcamento_projecao_mensal
                    WHERE cenario_id = %s AND (ano_num = %s OR (%s = 1 AND mes_ordem = 0))
                    ORDER BY mes_ordem
                    """,
                    (sel_id, ano_mensal, ano_mensal),
                )
                mensais = cur.fetchall()

            cur.execute("SELECT * FROM auditoria.alerta_coerencia WHERE empresa_id = %s AND modulo_alvo = 'planejamento' ORDER BY id", (emp_id,))
            alertas = cur.fetchall()

            cur.execute(
                "SELECT COALESCE(SUM(valor_centavos), 0) AS cap FROM erp.participacao_societaria WHERE empresa_id = %s AND vigente_ate IS NULL",
                (emp_id,),
            )
            capital_qsa = int(cur.fetchone()["cap"])

        return {
            "empresa": emp,
            "capital_qsa_centavos": capital_qsa,
            "cenarios": todos_cenarios,
            "selecionado": selecionado,
            "demonstrativos": demonstrativos,
            "mensais": mensais,
            "indicadores": indicadores,
            "ano_mensal": ano_mensal,
            "alertas": alertas,
        }


def salvar_cenario(cenario_id: int | None, form: dict[str, str]) -> int:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        campos = {
            "nome": form["nome"].strip(),
            "regime_simulacao": form["regime_simulacao"],
            "capital_social_centavos": parse_reais_centavos(form.get("capital_social_reais"), 4_000_000),
            "capex_m0_centavos": parse_reais_centavos(form.get("capex_m0_reais"), 1_000_000),
            "capex_ano2_centavos": parse_reais_centavos(form.get("capex_ano2_reais"), 1_200_000),
            "capex_ano3_centavos": parse_reais_centavos(form.get("capex_ano3_reais"), 1_500_000),
            "ticket_medio_centavos": parse_reais_centavos(form.get("ticket_medio_reais"), 150_000),
            "novos_clientes_mes": int(form.get("novos_clientes_mes") or 2),
            "inadimplencia_micro": parse_pct_micro(form.get("inadimplencia_pct"), 50_000),
            "custo_variavel_micro": parse_pct_micro(form.get("custo_variavel_pct"), 30_000),
            "cac_centavos": parse_reais_centavos(form.get("cac_reais"), 50_000),
            "retencao_meses": int(form.get("retencao_meses") or 24),
            "tma_anual_micro": parse_pct_micro(form.get("tma_pct"), 150_000),
            "taxa_reserva_lucros_micro": parse_pct_micro(form.get("taxa_reserva_pct"), 200_000),
            "pct_cnae_principal_micro": parse_pct_micro(form.get("pct_cnae_principal"), 850_000),
            "opex_fixo_ano1_mensal_centavos": parse_reais_centavos(form.get("opex_ano1_reais"), 300_000),
            "opex_fixo_ano2_mensal_centavos": parse_reais_centavos(form.get("opex_ano2_reais"), 650_000),
            "opex_fixo_ano3_mensal_centavos": parse_reais_centavos(form.get("opex_ano3_reais"), 950_000),
            "prolabore_m1_3_mensal_centavos": parse_reais_centavos(form.get("prolabore_m1_3_reais"), 0),
            "prolabore_m4_12_mensal_centavos": parse_reais_centavos(form.get("prolabore_m4_12_reais"), 450_000),
            "prolabore_ano2_mensal_centavos": parse_reais_centavos(form.get("prolabore_ano2_reais"), 700_000),
            "prolabore_ano3_mensal_centavos": parse_reais_centavos(form.get("prolabore_ano3_reais"), 1_000_000),
            "folha_clt_ano2_mensal_centavos": parse_reais_centavos(form.get("folha_clt_ano2_reais"), 1_000_000),
            "folha_clt_ano3_mensal_centavos": parse_reais_centavos(form.get("folha_clt_ano3_reais"), 2_520_000),
            "encargos_clt_micro": parse_pct_micro(form.get("encargos_clt_pct"), 296_400),
            "status_validacao": form.get("status_validacao", "pendente_revisao"),
            "justificativa_contadora": form.get("justificativa_contadora", "").strip() or None,
        }
        with conn.cursor() as cur:
            if cenario_id is None:
                codigo = _slug(form.get("codigo_cenario") or form["nome"])[:32]
                cur.execute("SELECT COUNT(*) AS c FROM erp.orcamento_cenario WHERE empresa_id = %s AND codigo_cenario = %s", (emp_id, codigo))
                if int(cur.fetchone()["c"]) > 0:
                    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS nxt FROM erp.orcamento_cenario")
                    codigo = f"{codigo}_{cur.fetchone()['nxt']}"
                chave = f"orc:{codigo}"
                cur.execute(
                    """
                    INSERT INTO erp.orcamento_cenario (
                        chave, empresa_id, codigo_cenario, nome, regime_simulacao, eh_oficial,
                        capital_social_centavos, capex_m0_centavos, capex_ano2_centavos, capex_ano3_centavos,
                        ticket_medio_centavos, novos_clientes_mes, inadimplencia_micro, custo_variavel_micro,
                        cac_centavos, retencao_meses, tma_anual_micro, taxa_reserva_lucros_micro,
                        pct_cnae_principal_micro, opex_fixo_ano1_mensal_centavos, opex_fixo_ano2_mensal_centavos,
                        opex_fixo_ano3_mensal_centavos, prolabore_m1_3_mensal_centavos, prolabore_m4_12_mensal_centavos,
                        prolabore_ano2_mensal_centavos, prolabore_ano3_mensal_centavos,
                        folha_clt_ano2_mensal_centavos, folha_clt_ano3_mensal_centavos, encargos_clt_micro,
                        origem_registro, status_validacao, justificativa_contadora
                    ) VALUES (
                        %s, %s, %s, %s, %s, false, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s
                    ) RETURNING id
                    """,
                    (
                        chave, emp_id, codigo, campos["nome"], campos["regime_simulacao"],
                        campos["capital_social_centavos"], campos["capex_m0_centavos"], campos["capex_ano2_centavos"], campos["capex_ano3_centavos"],
                        campos["ticket_medio_centavos"], campos["novos_clientes_mes"], campos["inadimplencia_micro"], campos["custo_variavel_micro"],
                        campos["cac_centavos"], campos["retencao_meses"], campos["tma_anual_micro"], campos["taxa_reserva_lucros_micro"],
                        campos["pct_cnae_principal_micro"], campos["opex_fixo_ano1_mensal_centavos"], campos["opex_fixo_ano2_mensal_centavos"],
                        campos["opex_fixo_ano3_mensal_centavos"], campos["prolabore_m1_3_mensal_centavos"], campos["prolabore_m4_12_mensal_centavos"],
                        campos["prolabore_ano2_mensal_centavos"], campos["prolabore_ano3_mensal_centavos"],
                        campos["folha_clt_ano2_mensal_centavos"], campos["folha_clt_ano3_mensal_centavos"], campos["encargos_clt_micro"],
                        campos["status_validacao"], campos["justificativa_contadora"],
                    ),
                )
                cenario_id = int(cur.fetchone()["id"])
            else:
                cur.execute(
                    """
                    UPDATE erp.orcamento_cenario
                    SET nome = %s, regime_simulacao = %s,
                        capital_social_centavos = %s, capex_m0_centavos = %s, capex_ano2_centavos = %s, capex_ano3_centavos = %s,
                        ticket_medio_centavos = %s, novos_clientes_mes = %s, inadimplencia_micro = %s, custo_variavel_micro = %s,
                        cac_centavos = %s, retencao_meses = %s, tma_anual_micro = %s, taxa_reserva_lucros_micro = %s,
                        pct_cnae_principal_micro = %s, opex_fixo_ano1_mensal_centavos = %s, opex_fixo_ano2_mensal_centavos = %s,
                        opex_fixo_ano3_mensal_centavos = %s, prolabore_m1_3_mensal_centavos = %s, prolabore_m4_12_mensal_centavos = %s,
                        prolabore_ano2_mensal_centavos = %s, prolabore_ano3_mensal_centavos = %s,
                        folha_clt_ano2_mensal_centavos = %s, folha_clt_ano3_mensal_centavos = %s, encargos_clt_micro = %s,
                        status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        campos["nome"], campos["regime_simulacao"],
                        campos["capital_social_centavos"], campos["capex_m0_centavos"], campos["capex_ano2_centavos"], campos["capex_ano3_centavos"],
                        campos["ticket_medio_centavos"], campos["novos_clientes_mes"], campos["inadimplencia_micro"], campos["custo_variavel_micro"],
                        campos["cac_centavos"], campos["retencao_meses"], campos["tma_anual_micro"], campos["taxa_reserva_lucros_micro"],
                        campos["pct_cnae_principal_micro"], campos["opex_fixo_ano1_mensal_centavos"], campos["opex_fixo_ano2_mensal_centavos"],
                        campos["opex_fixo_ano3_mensal_centavos"], campos["prolabore_m1_3_mensal_centavos"], campos["prolabore_m4_12_mensal_centavos"],
                        campos["prolabore_ano2_mensal_centavos"], campos["prolabore_ano3_mensal_centavos"],
                        campos["folha_clt_ano2_mensal_centavos"], campos["folha_clt_ano3_mensal_centavos"], campos["encargos_clt_micro"],
                        campos["status_validacao"], campos["justificativa_contadora"], cenario_id, emp_id,
                    ),
                )
        recalcular_cenario_no_banco(conn, cenario_id)
        _validar_coerencia(conn, emp_id)
        conn.commit()
    return cenario_id


def clonar_cenario(cenario_id: int) -> int:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM erp.orcamento_cenario WHERE id = %s AND empresa_id = %s", (cenario_id, emp_id))
            src = cur.fetchone()
            if not src:
                raise KeyError("Cenario nao encontrado.")
            cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS nxt FROM erp.orcamento_cenario")
            nxt = int(cur.fetchone()["nxt"])
            cod = f"{src['codigo_cenario'][:20]}_copia_{nxt}"
            cur.execute(
                """
                INSERT INTO erp.orcamento_cenario (
                    chave, empresa_id, codigo_cenario, nome, regime_simulacao, eh_oficial, horizonte_meses,
                    capital_social_centavos, capex_m0_centavos, capex_ano2_centavos, capex_ano3_centavos,
                    taxa_depreciacao_anual_micro, ticket_medio_centavos, novos_clientes_mes, inadimplencia_micro,
                    custo_variavel_micro, cac_centavos, retencao_meses, tma_anual_micro, taxa_reserva_lucros_micro,
                    pct_cnae_principal_micro, opex_fixo_ano1_mensal_centavos, opex_fixo_ano2_mensal_centavos,
                    opex_fixo_ano3_mensal_centavos, prolabore_m1_3_mensal_centavos, prolabore_m4_12_mensal_centavos,
                    prolabore_ano2_mensal_centavos, prolabore_ano3_mensal_centavos, folha_clt_ano2_mensal_centavos,
                    folha_clt_ano3_mensal_centavos, encargos_clt_micro, premissas_json, origem_registro,
                    status_validacao, referencia_v1_original, apontamento_auditoria
                )
                SELECT
                    %s, empresa_id, %s, %s, regime_simulacao, false, horizonte_meses,
                    capital_social_centavos, capex_m0_centavos, capex_ano2_centavos, capex_ano3_centavos,
                    taxa_depreciacao_anual_micro, ticket_medio_centavos, novos_clientes_mes, inadimplencia_micro,
                    custo_variavel_micro, cac_centavos, retencao_meses, tma_anual_micro, taxa_reserva_lucros_micro,
                    pct_cnae_principal_micro, opex_fixo_ano1_mensal_centavos, opex_fixo_ano2_mensal_centavos,
                    opex_fixo_ano3_mensal_centavos, prolabore_m1_3_mensal_centavos, prolabore_m4_12_mensal_centavos,
                    prolabore_ano2_mensal_centavos, prolabore_ano3_mensal_centavos, folha_clt_ano2_mensal_centavos,
                    folha_clt_ano3_mensal_centavos, encargos_clt_micro, premissas_json, 'usuario',
                    'pendente_revisao', referencia_v1_original, 'Simulacao clonada pela contadora para teste de premissas.'
                FROM erp.orcamento_cenario WHERE id = %s
                RETURNING id
                """,
                (f"orc:{cod}", cod, f"{src['nome']} (Simulacao #{nxt})", cenario_id),
            )
            novo_id = int(cur.fetchone()["id"])
        recalcular_cenario_no_banco(conn, novo_id)
        _validar_coerencia(conn, emp_id)
        conn.commit()
    return novo_id


def definir_cenario_oficial(cenario_id: int) -> None:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM erp.orcamento_cenario WHERE id = %s AND empresa_id = %s", (cenario_id, emp_id))
            if cur.fetchone() is None:
                raise ValueError(f"Cenario id={cenario_id} nao encontrado para esta empresa.")
            cur.execute("UPDATE erp.orcamento_cenario SET eh_oficial = false WHERE empresa_id = %s", (emp_id,))
            cur.execute("UPDATE erp.orcamento_cenario SET eh_oficial = true WHERE id = %s AND empresa_id = %s", (cenario_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_cenario(cenario_id: int) -> bool:
    with conectar_pg() as conn:
        emp = obter_empresa_d1(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("SELECT eh_oficial FROM erp.orcamento_cenario WHERE id = %s AND empresa_id = %s", (cenario_id, emp_id))
            row = cur.fetchone()
            if not row or row["eh_oficial"]:
                return False
            cur.execute("DELETE FROM erp.orcamento_cenario WHERE id = %s AND empresa_id = %s", (cenario_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()
    return True


# =============================================================================
# ESTACAO 5: CONSULTAS NORMATIVAS, CONFORMIDADE (200) & DIARIO DE IA
# =============================================================================
MATRIZES_D1 = ("plano_negocios", "contrato_social", "memorando", "fluxo_abertura")
MATRIZES_D2 = ("d2_p1", "d2_p2", "d2_p3", "d2_p4", "d2_p5", "d2_p6", "d2_p7", "d2_p8", "d2_p9")


def carregar_sustentacao(matriz: str | None = None, apenas_pendentes: bool = False) -> dict[str, Any]:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        cod = emp["dossie"]
        validas = MATRIZES_D2 if cod == "D2" else MATRIZES_D1
        if not matriz or matriz not in validas:
            matriz = validas[0]
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM erp.consulta_normativa WHERE empresa_id = %s AND dossie = %s ORDER BY numero_questao", (emp_id, cod))
            consultas = cur.fetchall()

            cur.execute("SELECT * FROM erp.empresa_decisao_preliminar WHERE empresa_id = %s AND dossie = %s ORDER BY ordem", (emp_id, cod))
            decisoes = cur.fetchall()

            cur.execute("SELECT * FROM auditoria.vw_placar_conformidade WHERE empresa_id = %s AND dossie = %s ORDER BY matriz", (emp_id, cod))
            placar = cur.fetchall()

            where_pend = " AND av.status_validacao <> 'homologado_contadora'" if apenas_pendentes else ""
            cur.execute(
                f"""
                SELECT av.*, c.matriz, c.bloco, c.bloco_titulo, c.bloco_peso, c.codigo, c.descricao, c.referencia_fonte
                FROM auditoria.avaliacao_conformidade av
                JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id
                WHERE av.empresa_id = %s AND c.dossie = %s AND c.matriz = %s {where_pend}
                ORDER BY c.bloco, c.id
                """,
                (emp_id, cod, matriz),
            )
            criterios = cur.fetchall()

            cur.execute("SELECT id, documento, codigo_secao FROM erp.documento_secao WHERE empresa_id = %s AND dossie = %s", (emp_id, cod))
            sec_ids = {(r["documento"], r["codigo_secao"]): int(r["id"]) for r in cur.fetchall()}

            cur.execute("SELECT id, codigo_criterio FROM erp.instrumento_societario_clausula WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
            cl_ids: dict[str, int] = {}
            for r in cur.fetchall():
                cl_ids.setdefault(str(r["codigo_criterio"]).strip().upper(), int(r["id"]))

            cur.execute("SELECT id, codigo FROM erp.processo_legalizacao_etapa WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
            etapas_rows = cur.fetchall()

            def _destino_criterio(cr: dict[str, Any]) -> tuple[str, str]:
                mat, blk, cr_cod = cr["matriz"], cr["bloco"], str(cr["codigo"]).strip().upper()
                if mat.startswith("d2_p"):
                    mapa_d2 = {
                        "d2_p1": ("/instrumentos", "Abrir Análise da 2ª Alteração (Estação 2)"),
                        "d2_p2": ("/onboarding#contratos", "Abrir Contratos e Termo RT (Estação 7)"),
                        "d2_p3": ("/onboarding#diligencia", "Abrir Checklist, Q1–Q9 e Pendências (Estação 7)"),
                        "d2_p4": ("/dp#contratos-trabalho", "Abrir Departamento Pessoal e eSocial (Estação 8)"),
                        "d2_p5": ("/folha#rubricas", "Abrir Cálculo da Folha 09/2026 (Estação 9)"),
                        "d2_p6": ("/folha#partidas", "Abrir Provisões e Partidas Dobradas (Estação 9)"),
                        "d2_p7": ("/folha#auditoria", "Abrir Auditoria Trabalhista (Estação 9)"),
                        "d2_p8": ("/sustentacao#consultas", "Abrir Registro de Premissas PR-01..18 (abaixo)"),
                        "d2_p9": ("/sustentacao#diario-ia", "Abrir Diário de Uso de IA (abaixo)"),
                    }
                    return mapa_d2.get(mat, ("/emissao", "Abrir Emissão Dossiê 2 (Estação 6)"))
                if mat == "plano_negocios":
                    mapa_pn = {
                        "A": ("S01", "Abrir Sumário Executivo (S01)"),
                        "B": ("S03", "Abrir Proposta de Valor / Canvas (S03)"),
                        "C": ("S04", "Abrir Mercado e Competição (S04)"),
                        "D": ("S07", "Abrir Validação e Equipe (S07)"),
                        "E": ("S05", "Abrir Marketing e Unit Economics (S05)"),
                        "F": ("S06", "Abrir Operações e Tecnologia (S06)"),
                        "I": ("S09", "Abrir Riscos e Legal (S09)"),
                        "J": ("S10", "Abrir OKRs e Longo Prazo (S10)"),
                    }
                    if blk == "G":
                        return ("/cadastro#socios", "Abrir QSA e Equipe (Estação 1)")
                    if blk == "H":
                        return ("/planejamento#premissas", "Abrir Planejamento Financeiro (Estação 4)")
                    sec_cod, rotulo = mapa_pn.get(blk, ("S01", "Abrir seções do Plano (Estação 6)"))
                    sid = sec_ids.get(("plano_negocios", sec_cod))
                    return (f"/emissao#secao-{sid}" if sid else "/emissao#secoes", rotulo)
                if mat in ("contrato_social", "memorando"):
                    cid = cl_ids.get(cr_cod)
                    filtro = "contrato" if mat == "contrato_social" else "mou"
                    if cid:
                        return (f"/instrumentos?filtro={filtro}#clausula-{cid}", f"Abrir cláusula ({cr_cod}) na Estação 2")
                    return (f"/instrumentos?filtro={filtro}", "Abrir Instrumentos (Estação 2)")
                for e in etapas_rows:
                    tokens = [t.strip().upper() for t in str(e["codigo"]).replace(",", " ").split()]
                    if cr_cod in tokens:
                        return (f"/legalizacao#etapa-{e['id']}", f"Abrir etapa {e['codigo']} na Estação 3")
                return ("/legalizacao#lista-etapas", "Abrir Legalização DF (Estação 3)")

            criterios = [dict(cr, destino_url=_destino_criterio(cr)[0], destino_rotulo=_destino_criterio(cr)[1]) for cr in criterios]

            cur.execute("SELECT * FROM auditoria.diario_ia WHERE empresa_id = %s AND dossie = %s ORDER BY id", (emp_id, cod))
            diario_ia = cur.fetchall()

        return {
            "empresa": emp,
            "consultas": consultas,
            "decisoes": decisoes,
            "placar": placar,
            "criterios": criterios,
            "diario_ia": diario_ia,
            "matriz_ativa": matriz,
            "apenas_pendentes": apenas_pendentes,
            "matrizes_disponiveis": validas,
        }


def salvar_consulta(cons_id: int | None, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        cod = emp["dossie"]
        with conn.cursor() as cur:
            if cons_id is None:
                cur.execute("SELECT COALESCE(MAX(numero_questao), 0) + 1 AS prox FROM erp.consulta_normativa WHERE empresa_id = %s", (emp_id,))
                num = int(form.get("numero_questao") or cur.fetchone()["prox"])
                if cod == "D2":
                    cur.execute(
                        """
                        INSERT INTO erp.consulta_normativa
                            (chave, empresa_id, numero_questao, enunciado, resposta_autoral, norma_citada, link_oficial,
                             data_acesso, decisao_impactada, responsavel_decisao, prazo_decisao, impacto_se_alterada,
                             origem_registro, status_validacao, justificativa_contadora, dossie)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s, %s)
                        """,
                        (
                            f"cons:usr:{cod.lower()}:q{num:02d}", emp_id, num, form["enunciado"].strip(), form["resposta_autoral"].strip(),
                            form["norma_citada"].strip(), form["link_oficial"].strip(), form["data_acesso"],
                            form.get("decisao_impactada", "").strip() or None,
                            (form.get("responsavel_decisao") or "").strip() or None,
                            (form.get("prazo_decisao") or "").strip() or None,
                            (form.get("impacto_se_alterada") or "").strip() or None,
                            form["status_validacao"],
                            form.get("justificativa_contadora", "").strip() or None, cod,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO erp.consulta_normativa
                            (chave, empresa_id, numero_questao, enunciado, resposta_autoral, norma_citada, link_oficial,
                             data_acesso, decisao_impactada, origem_registro, status_validacao, justificativa_contadora, dossie)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s, %s)
                        """,
                        (
                            f"cons:usr:{cod.lower()}:q{num:02d}", emp_id, num, form["enunciado"].strip(), form["resposta_autoral"].strip(),
                            form["norma_citada"].strip(), form["link_oficial"].strip(), form["data_acesso"],
                            form.get("decisao_impactada", "").strip() or None, form["status_validacao"],
                            form.get("justificativa_contadora", "").strip() or None, cod,
                        ),
                    )
            else:
                if cod == "D2":
                    cur.execute(
                        """
                        UPDATE erp.consulta_normativa
                        SET enunciado = %s, resposta_autoral = %s, norma_citada = %s, link_oficial = %s,
                            data_acesso = %s, decisao_impactada = %s,
                            responsavel_decisao = %s, prazo_decisao = %s, impacto_se_alterada = %s,
                            status_validacao = %s, justificativa_contadora = %s
                        WHERE id = %s AND empresa_id = %s
                        """,
                        (
                            form["enunciado"].strip(), form["resposta_autoral"].strip(), form["norma_citada"].strip(),
                            form["link_oficial"].strip(), form["data_acesso"], form.get("decisao_impactada", "").strip() or None,
                            (form.get("responsavel_decisao") or "").strip() or None,
                            (form.get("prazo_decisao") or "").strip() or None,
                            (form.get("impacto_se_alterada") or "").strip() or None,
                            form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                            cons_id, emp_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE erp.consulta_normativa
                        SET enunciado = %s, resposta_autoral = %s, norma_citada = %s, link_oficial = %s,
                            data_acesso = %s, decisao_impactada = %s,
                            status_validacao = %s, justificativa_contadora = %s
                        WHERE id = %s AND empresa_id = %s
                        """,
                        (
                            form["enunciado"].strip(), form["resposta_autoral"].strip(), form["norma_citada"].strip(),
                            form["link_oficial"].strip(), form["data_acesso"], form.get("decisao_impactada", "").strip() or None,
                            form["status_validacao"], form.get("justificativa_contadora", "").strip() or None,
                            cons_id, emp_id,
                        ),
                    )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def excluir_consulta(cons_id: int) -> None:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erp.consulta_normativa WHERE id = %s AND empresa_id = %s", (cons_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()


def salvar_avaliacao_criterio(av_id: int, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        na = form.get("nao_aplicavel") == "on"
        nota_str = (form.get("nota") or "").strip()
        nota = None if (na or nota_str == "") else int(nota_str)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE auditoria.avaliacao_conformidade
                SET nota = %s,
                    nao_aplicavel = %s,
                    referencia_localizacao = %s,
                    justificativa_sustentacao = %s,
                    status_validacao = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (
                    nota, na, form.get("referencia_localizacao", "").strip() or None,
                    form.get("justificativa_sustentacao", "").strip() or None,
                    form["status_validacao"], av_id, emp_id,
                ),
            )
        _validar_coerencia(conn, emp_id)
        conn.commit()


def salvar_diario_ia(ia_id: int | None, form: dict[str, str]) -> None:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        cod = emp["dossie"]
        with conn.cursor() as cur:
            if ia_id is None:
                cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS nxt FROM auditoria.diario_ia")
                nxt = int(cur.fetchone()["nxt"])
                cur.execute(
                    """
                    INSERT INTO auditoria.diario_ia
                        (chave, dossie, empresa_id, entregavel, ferramenta, finalidade, prompt_resumo,
                         fonte_oficial, revisao_humana, autor, origem_registro, status_validacao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'usuario', %s)
                    """,
                    (
                        f"ia:{cod.lower()}:usr:{nxt}", cod, emp_id, form["entregavel"].strip(), form.get("ferramenta", "Assistente IA").strip(),
                        form["finalidade"].strip(), form.get("prompt_resumo", form["finalidade"]).strip(),
                        form["fonte_oficial"].strip(), form["revisao_humana"].strip(),
                        form.get("autor", "Nathalia Peres").strip(), form["status_validacao"],
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE auditoria.diario_ia
                    SET entregavel = %s, ferramenta = %s, finalidade = %s, fonte_oficial = %s,
                        revisao_humana = %s, status_validacao = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        form["entregavel"].strip(), form.get("ferramenta", "Assistente IA").strip(),
                        form["finalidade"].strip(), form["fonte_oficial"].strip(), form["revisao_humana"].strip(),
                        form["status_validacao"], ia_id, emp_id,
                    ),
                )
        conn.commit()


def excluir_diario_ia(ia_id: int) -> None:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auditoria.diario_ia WHERE id = %s AND empresa_id = %s", (ia_id, emp_id))
        conn.commit()


# =============================================================================
# NAVEGACAO: PROGRESSO DE HOMOLOGACAO POR ESTACAO
# =============================================================================
def progresso_por_estacao(dossie: str | None = None) -> dict[str, dict[str, int]]:
    """Homologados/total por estacao a partir de auditoria.vw_pendencias_quarentena."""
    from sistema.web.rotulos import MODULO_ESTACAO

    cod = dossie_em_foco(dossie)
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT modulo, COUNT(*) AS t,
                       COUNT(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS h
                FROM auditoria.vw_pendencias_quarentena
                WHERE dossie = %s AND status_validacao <> 'acervo_referencia'
                GROUP BY modulo
                """,
                (cod,),
            )
            linhas = cur.fetchall()
    out: dict[str, dict[str, int]] = {}
    for r in linhas:
        est = MODULO_ESTACAO.get(r["modulo"])
        if not est:
            continue
        acc = out.setdefault(est, {"h": 0, "t": 0})
        acc["h"] += int(r["h"])
        acc["t"] += int(r["t"])
    return out


# =============================================================================
# ESTACAO 6: EMISSAO — SECOES NARRATIVAS DOS DOCUMENTOS (erp.documento_secao)
# =============================================================================
DOCUMENTOS_SECAO_D1 = ("indice", "pesquisa", "plano_negocios", "contrato_social", "memorando", "fluxo_abertura")
DOCUMENTOS_SECAO_D2 = (
    "d2_00_indice", "d2_01_diagnostico", "d2_02_proposta", "d2_03_contrato",
    "d2_04_termo_rt", "d2_05_onboarding", "d2_06_prontuario", "d2_07_ficha_e1",
    "d2_08_exp_e1", "d2_09_ficha_e2", "d2_10_exp_e2", "d2_11_folha",
    "d2_12_resumo_contab", "d2_13_auditoria", "d2_14_premissas", "d2_15_ia",
)
DOCUMENTOS_SECAO = DOCUMENTOS_SECAO_D1 + DOCUMENTOS_SECAO_D2


def carregar_emissao() -> dict[str, Any]:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        cod = emp["dossie"]
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM erp.documento_secao WHERE empresa_id = %s AND dossie = %s ORDER BY documento, ordem, id", (emp_id, cod))
            secoes = cur.fetchall()
            cur.execute(
                """
                SELECT modulo,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados,
                       COUNT(*) FILTER (WHERE status_validacao = 'alerta_inconsistencia') AS inconsistencias,
                       COUNT(*) FILTER (WHERE status_validacao = 'pendente_revisao') AS pendentes
                FROM auditoria.vw_pendencias_quarentena
                WHERE dossie = %s AND status_validacao <> 'acervo_referencia'
                GROUP BY modulo ORDER BY modulo
                """,
                (cod,),
            )
            quarentena = cur.fetchall()
    return {"empresa": emp, "secoes": secoes, "quarentena": quarentena}


def salvar_secao(sec_id: int | None, form: dict[str, str]) -> int:
    documento = (form.get("documento") or "").strip()
    titulo = (form.get("titulo") or "").strip()
    if sec_id is None and documento not in DOCUMENTOS_SECAO:
        raise ValueError(f"Documento invalido: {documento!r}.")
    if not titulo:
        raise ValueError("O titulo da secao nao pode ficar vazio.")
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        cod = emp["dossie"]
        with conn.cursor() as cur:
            if sec_id is None:
                codigo = _slug(form.get("codigo_secao") or titulo)[:40]
                cur.execute(
                    "SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM erp.documento_secao WHERE empresa_id = %s AND documento = %s",
                    (emp_id, documento),
                )
                ordem = parse_int_br(form.get("ordem"), int(cur.fetchone()["prox"]))
                cur.execute(
                    """
                    INSERT INTO erp.documento_secao
                        (chave, empresa_id, documento, ordem, codigo_secao, titulo, conteudo_md,
                         origem_registro, status_validacao, justificativa_contadora, dossie)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'usuario', %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        f"docsec:usr:{cod.lower()}:{documento}:{codigo}", emp_id, documento, max(ordem, 1), codigo, titulo,
                        (form.get("conteudo_md") or "").strip(), form.get("status_validacao", "pendente_revisao"),
                        (form.get("justificativa_contadora") or "").strip() or None, cod,
                    ),
                )
                sec_id = int(cur.fetchone()["id"])
            else:
                cur.execute(
                    """
                    UPDATE erp.documento_secao
                    SET ordem = %s, titulo = %s, conteudo_md = %s,
                        status_validacao = %s, justificativa_contadora = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (
                        max(parse_int_br(form.get("ordem"), 1), 1), titulo, (form.get("conteudo_md") or "").strip(),
                        form.get("status_validacao", "pendente_revisao"),
                        (form.get("justificativa_contadora") or "").strip() or None, sec_id, emp_id,
                    ),
                )
        _validar_coerencia(conn, emp_id)
        conn.commit()
    return sec_id


def excluir_secao(sec_id: int) -> None:
    with conectar_pg() as conn:
        emp = empresa_em_foco(conn)
        emp_id = int(emp["id"])
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erp.documento_secao WHERE id = %s AND empresa_id = %s", (sec_id, emp_id))
        _validar_coerencia(conn, emp_id)
        conn.commit()
