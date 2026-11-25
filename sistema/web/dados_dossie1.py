"""Carregador unico do estado do Dossie 1 no PostgreSQL para emissao de PDFs e planilha.

Nenhum numero e calculado aqui: tudo vem de tabelas do ERP ou dos demonstrativos que o
motor_contabil.py gravou para o cenario oficial.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sistema.pg.db import conectar_pg

EMPRESA_CHAVE = "emp:prisma_jrna_g07"


def carregar_dados_dossie1() -> dict[str, Any]:
    d: dict[str, Any] = {"emitido_em": datetime.now()}
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT e.*, p.nome_canonico AS razao_social FROM erp.empresa e JOIN erp.pessoa p ON p.id = e.pessoa_id WHERE e.chave = %s",
            (EMPRESA_CHAVE,),
        )
        emp = cur.fetchone()
        if not emp:
            raise RuntimeError("Empresa do Dossie 1 nao encontrada no banco.")
        emp_id = int(emp["id"])
        d["empresa"] = emp

        cur.execute("SELECT * FROM erp.estabelecimento WHERE empresa_id = %s ORDER BY id", (emp_id,))
        d["estabelecimentos"] = cur.fetchall()
        d["sede"] = next((e for e in d["estabelecimentos"] if e["tipo"] in ("matriz", "unico")), d["estabelecimentos"][0] if d["estabelecimentos"] else None)

        cur.execute(
            """
            SELECT ps.*, p.nome_canonico, p.id AS pessoa_id
            FROM erp.participacao_societaria ps JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id
            WHERE ps.empresa_id = %s AND ps.vigente_ate IS NULL ORDER BY ps.id
            """,
            (emp_id,),
        )
        d["socios"] = cur.fetchall()
        pessoa_ids = [int(emp["pessoa_id"])] + [int(s["pessoa_id"]) for s in d["socios"]]
        cur.execute(
            """
            SELECT pi.*, p.nome_canonico FROM erp.pessoa_identificador pi JOIN erp.pessoa p ON p.id = pi.pessoa_id
            WHERE pi.pessoa_id = ANY(%s) ORDER BY pi.pessoa_id, pi.tipo_id, pi.id
            """,
            (pessoa_ids,),
        )
        d["identificadores"] = cur.fetchall()
        ids_por_pessoa: dict[int, dict[str, Any]] = defaultdict(dict)
        for pi in d["identificadores"]:
            ids_por_pessoa[int(pi["pessoa_id"])].setdefault(pi["tipo_id"], pi)
        d["ids_por_pessoa"] = ids_por_pessoa
        d["capital_qsa_centavos"] = sum(int(s["valor_centavos"] or 0) for s in d["socios"])
        d["quotas_total"] = sum(int(s["quotas"] or 0) for s in d["socios"])

        cur.execute(
            """
            SELECT enq.*, p.nome_canonico AS rt_nome FROM erp.enquadramento_historico enq
            LEFT JOIN erp.pessoa p ON p.id = enq.responsavel_tecnico_pessoa_id
            WHERE enq.empresa_id = %s ORDER BY enq.vigente_de DESC, enq.id DESC LIMIT 1
            """,
            (emp_id,),
        )
        enq = cur.fetchone()
        d["enquadramento"] = enq
        rt_crc = None
        if enq and enq["responsavel_tecnico_pessoa_id"]:
            rt_crc = ids_por_pessoa.get(int(enq["responsavel_tecnico_pessoa_id"]), {}).get("CRC")
        d["rt"] = {"nome": (enq or {}).get("rt_nome"), "crc": rt_crc["valor"] if rt_crc else None}
        d["cnpj"] = ids_por_pessoa.get(int(emp["pessoa_id"]), {}).get("CNPJ") or (
            {"valor": d["sede"]["cnpj"], "eh_ficticio": True} if d["sede"] else None
        )

        cur.execute("SELECT * FROM erp.instrumento_societario_clausula WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
        cls = cur.fetchall()
        d["clausulas_contrato"] = [c for c in cls if c["aplica_contrato"]]
        d["clausulas_mou"] = [c for c in cls if c["aplica_mou"]]

        cur.execute("SELECT * FROM erp.processo_legalizacao_etapa WHERE empresa_id = %s ORDER BY ordem, id", (emp_id,))
        d["etapas"] = cur.fetchall()
        cur.execute("SELECT * FROM erp.consulta_normativa WHERE empresa_id = %s ORDER BY numero_questao", (emp_id,))
        d["consultas"] = cur.fetchall()
        cur.execute("SELECT * FROM erp.empresa_decisao_preliminar WHERE empresa_id = %s ORDER BY ordem", (emp_id,))
        d["decisoes"] = cur.fetchall()

        cur.execute(
            """
            SELECT c.*, d1.das_centavos AS a1_das, d1.fator_r_anual_micro AS a1_fator_r, d1.lucro_liquido_centavos AS a1_lucro,
                   d0.indicadores_json
            FROM erp.orcamento_cenario c
            LEFT JOIN erp.orcamento_demonstrativo_anual d1 ON d1.cenario_id = c.id AND d1.ano_ordem = 1
            LEFT JOIN erp.orcamento_demonstrativo_anual d0 ON d0.cenario_id = c.id AND d0.ano_ordem = 0
            WHERE c.empresa_id = %s ORDER BY c.eh_oficial DESC, c.id
            """,
            (emp_id,),
        )
        d["cenarios"] = cur.fetchall()
        cen = next((c for c in d["cenarios"] if c["eh_oficial"]), None)
        d["cenario"] = cen
        d["demonstrativos"], d["mensal"], d["indicadores"] = [], [], {}
        if cen:
            cur.execute("SELECT * FROM erp.orcamento_demonstrativo_anual WHERE cenario_id = %s ORDER BY ano_ordem", (cen["id"],))
            d["demonstrativos"] = cur.fetchall()
            cur.execute("SELECT * FROM erp.orcamento_projecao_mensal WHERE cenario_id = %s ORDER BY mes_ordem", (cen["id"],))
            d["mensal"] = cur.fetchall()
            d["indicadores"] = dict(cen["indicadores_json"] or {})
        d["anos"] = {int(x["ano_ordem"]): x for x in d["demonstrativos"]}

        cur.execute("SELECT * FROM auditoria.diario_ia WHERE empresa_id = %s AND dossie = 'D1' ORDER BY id", (emp_id,))
        d["diario_ia"] = cur.fetchall()
        cur.execute("SELECT * FROM auditoria.vw_placar_conformidade WHERE empresa_id = %s ORDER BY matriz", (emp_id,))
        d["placar"] = cur.fetchall()
        cur.execute(
            """
            SELECT c.matriz, c.codigo, c.descricao, av.nota, av.nao_aplicavel, av.referencia_localizacao, av.status_validacao
            FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id
            WHERE av.empresa_id = %s AND (av.referencia_localizacao IS NOT NULL OR av.nota IS NOT NULL)
            ORDER BY c.matriz, c.id
            """,
            (emp_id,),
        )
        d["rastreabilidade"] = cur.fetchall()
        cur.execute("SELECT * FROM auditoria.alerta_coerencia WHERE empresa_id = %s ORDER BY CASE severidade WHEN 'critico' THEN 1 WHEN 'alerta' THEN 2 ELSE 3 END, id", (emp_id,))
        d["alertas"] = cur.fetchall()
        cur.execute(
            """
            SELECT modulo, COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados,
                   COUNT(*) FILTER (WHERE status_validacao = 'alerta_inconsistencia') AS inconsistencias,
                   COUNT(*) FILTER (WHERE status_validacao = 'pendente_revisao') AS pendentes
            FROM auditoria.vw_pendencias_quarentena
            WHERE status_validacao <> 'acervo_referencia'
            GROUP BY modulo ORDER BY modulo
            """
        )
        d["quarentena"] = cur.fetchall()
        d["pendencias_total"] = sum(int(q["pendentes"]) + int(q["inconsistencias"]) for q in d["quarentena"])

        cur.execute("SELECT * FROM erp.documento_secao WHERE empresa_id = %s ORDER BY documento, ordem, id", (emp_id,))
        secoes: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for s in cur.fetchall():
            secoes[s["documento"]].append(s)
        d["secoes"] = secoes
    return d


def secao(d: dict[str, Any], documento: str, codigo: str) -> dict[str, Any] | None:
    return next((s for s in d["secoes"].get(documento, []) if s["codigo_secao"] == codigo), None)
