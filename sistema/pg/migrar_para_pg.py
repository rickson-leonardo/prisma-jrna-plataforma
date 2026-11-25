"""Carga idempotente do staging SQLite (laboratorio.db + trabalho.db) para o banco unico PostgreSQL 17."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from psycopg2.extras import execute_values

from sistema.config import BANCO_DIR, LABORATORIO_DB, PLATAFORMA_DIR, TRABALHO_DB
from sistema.pg.db import conectar_pg, garantir_banco_existe, parse_database_url

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
SNAPSHOTS_DIR = BANCO_DIR / "snapshots"
PG_DUMP_EXE = Path(r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe")

# Mapas de arquivos de matriz D1 -> codigo de matriz
MATRIZES_D1 = {
    "Matriz_de_Requisitos_-_Plano_de_Negocios_-_Laboratorio_Contabil_CCA_0174.docx": "plano_negocios",
    "Matriz_de_Requisitos_-_Contrato_Social_-_CCA_0174.docx": "contrato_social",
    "Matriz_de_Requisitos_-_Memorando_de_Entendimento_dos_Socios_-_CCA_0174.docx": "memorando",
    "Matriz_de_Requisitos_-_Fluxo_de_Abertura_de_Empresas_no_DF_-_CCA_0174.docx": "fluxo_abertura",
}


@dataclass(frozen=True)
class CriterioMatriz:
    chave: str
    matriz: str
    bloco: str
    bloco_titulo: str
    bloco_peso: int
    codigo: str
    descricao: str
    referencia_fonte: str | None


def extrair_criterios_matrizes_d1(sqlite_conn: sqlite3.Connection) -> list[CriterioMatriz]:
    """Extrai os blocos (peso=100 por matriz) e criterios das 4 Matrizes de Requisitos do D1."""
    criterios: list[CriterioMatriz] = []
    re_bloco = re.compile(r"^Bloco\s+([A-Z])\s*[—–-]\s*(.+?)\s*\(peso\s+(\d+)\s+pontos\)", re.I)
    re_cod = re.compile(r"^[A-Z]\d+$")

    for nome_arq, matriz_cod in sorted(MATRIZES_D1.items()):
        rows = sqlite_conn.execute(
            """
            SELECT p.origem_bloco, p.tabela_idx, p.linha_idx, p.coluna_idx, p.texto
            FROM bru_paragrafo p
            JOIN bru_arquivo a ON a.id = p.arquivo_id
            WHERE a.nome = ?
            ORDER BY p.ordem
            """,
            (nome_arq,),
        ).fetchall()

        bloco_atual = ("?", "Geral", 0)
        linhas_tab: dict[tuple[int, int], dict[int, str]] = {}
        bloco_por_tab_linha: dict[tuple[int, int], tuple[str, str, int]] = {}

        for ob, tidx, lidx, cidx, txt in rows:
            t = str(txt).strip()
            m_b = re_bloco.match(t)
            if m_b:
                bloco_atual = (m_b.group(1).upper(), m_b.group(2).strip(), int(m_b.group(3)))
                continue
            if ob == "tabela_celula" and tidx is not None and lidx is not None and cidx is not None:
                key = (int(tidx), int(lidx))
                linhas_tab.setdefault(key, {})[int(cidx)] = t
                bloco_por_tab_linha[key] = bloco_atual

        for key in sorted(linhas_tab):
            cols = linhas_tab[key]
            cod = cols.get(1, "").strip()
            if not re_cod.match(cod):
                continue
            b_cod, b_tit, b_peso = bloco_por_tab_linha[key]
            desc = cols.get(2, "").strip()
            ref = cols.get(3, "").strip() or None
            criterios.append(
                CriterioMatriz(
                    chave=f"d1mat:{matriz_cod}:{cod}",
                    matriz=matriz_cod,
                    bloco=b_cod,
                    bloco_titulo=b_tit,
                    bloco_peso=b_peso,
                    codigo=cod,
                    descricao=desc,
                    referencia_fonte=ref,
                )
            )
    return criterios


def aplicar_migracoes_pg(pg_conn: Any) -> list[str]:
    """Aplica arquivos *.sql em sistema/pg/migrations em ordem alfabetica e registra em schema_migration."""
    aplicadas: list[str] = []
    with pg_conn.cursor() as cur:
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            versao = sql_file.stem
            sql_txt = sql_file.read_text(encoding="utf-8")
            cur.execute(sql_txt)
            cur.execute(
                """
                INSERT INTO auditoria.schema_migration (versao, descricao)
                VALUES (%s, %s)
                ON CONFLICT (versao) DO NOTHING
                """,
                (versao, f"Aplicada a partir de {sql_file.name}"),
            )
            aplicadas.append(versao)
    pg_conn.commit()
    return aplicadas


def _mapa_chave_id(pg_cur: Any, tabela_pg: str) -> dict[str, int]:
    pg_cur.execute(f"SELECT chave, id FROM {tabela_pg}")
    return {str(r["chave"]): int(r["id"]) for r in pg_cur.fetchall()}


def _carregar_tabela_por_chave(
    sl_conn: sqlite3.Connection,
    pg_cur: Any,
    tabela_sl: str,
    tabela_pg: str,
    colunas_pg: list[str],
    transform_row: Callable[[sqlite3.Row], tuple[Any, ...] | None],
    page_size: int = 2000,
) -> tuple[int, dict[int, int]]:
    """Copia linhas via chave natural sem sobrescrever registros existentes (ON CONFLICT DO NOTHING)."""
    sl_rows = sl_conn.execute(f"SELECT * FROM {tabela_sl} ORDER BY id").fetchall()
    valores: list[tuple[Any, ...]] = []
    sl_id_por_chave: dict[str, int] = {}

    for row in sl_rows:
        t = transform_row(row)
        if t is None:
            continue
        valores.append(t)
        sl_id_por_chave[str(row["chave"])] = int(row["id"])

    if valores:
        cols_sql = ", ".join(colunas_pg)
        sql = f"INSERT INTO {tabela_pg} ({cols_sql}) VALUES %s ON CONFLICT (chave) DO NOTHING"
        execute_values(pg_cur, sql, valores, page_size=page_size)

    pg_cur.execute(f"SELECT id, chave FROM {tabela_pg}")
    pg_id_por_chave = {str(r["chave"]): int(r["id"]) for r in pg_cur.fetchall()}
    id_map = {sl_id: pg_id_por_chave[ch] for ch, sl_id in sl_id_por_chave.items() if ch in pg_id_por_chave}
    return len(valores), id_map


def migrar_staging_para_pg(
    lab_db: Path = LABORATORIO_DB,
    trab_db: Path = TRABALHO_DB,
    gerar_backup: bool = False,
) -> dict[str, Any]:
    """Executa migracao completa e idempotente de SQLite -> PostgreSQL 17."""
    if not lab_db.exists():
        raise FileNotFoundError(f"Staging SQLite nao encontrado: {lab_db}")

    banco_nome = garantir_banco_existe()
    pg_conn = conectar_pg()
    sl_lab = sqlite3.connect(lab_db)
    sl_lab.row_factory = sqlite3.Row
    sl_trab = sqlite3.connect(trab_db) if trab_db.exists() else None
    if sl_trab is not None:
        sl_trab.row_factory = sqlite3.Row

    contagens: dict[str, int] = {}
    try:
        migracoes = aplicar_migracoes_pg(pg_conn)

        with pg_conn.cursor() as cur:
            # --- 1. SCHEMA acervo (bruto + extraido) ---
            # 1a. bru_arquivo sem self-FKs primeiro; depois atualiza zip_origem_id e duplicata_de_id
            n, arq_map = _carregar_tabela_por_chave(
                sl_lab, cur, "bru_arquivo", "acervo.bru_arquivo",
                ["chave", "caminho_relativo", "nome", "extensao", "sha256", "tamanho_bytes", "dossie", "dominio", "papel_acervo", "paginas_total"],
                lambda r: (r["chave"], r["caminho_relativo"], r["nome"], r["extensao"], r["sha256"], r["tamanho_bytes"], r["dossie"], r["dominio"], r["papel_acervo"], r["paginas_total"]),
            )
            contagens["acervo.bru_arquivo"] = n
            updates_self = [
                (
                    arq_map.get(r["zip_origem_id"]) if r["zip_origem_id"] else None,
                    arq_map.get(r["duplicata_de_id"]) if r["duplicata_de_id"] else None,
                    arq_map[int(r["id"])],
                )
                for r in sl_lab.execute("SELECT id, zip_origem_id, duplicata_de_id FROM bru_arquivo WHERE zip_origem_id IS NOT NULL OR duplicata_de_id IS NOT NULL").fetchall()
            ]
            if updates_self:
                cur.executemany(
                    "UPDATE acervo.bru_arquivo SET zip_origem_id = %s, duplicata_de_id = %s WHERE id = %s",
                    updates_self,
                )

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "bru_zip_entrada", "acervo.bru_zip_entrada",
                ["chave", "zip_arquivo_id", "caminho_interno", "tamanho_bytes", "crc32", "sha256", "arquivo_disco_id"],
                lambda r: (r["chave"], arq_map[r["zip_arquivo_id"]], r["caminho_interno"], r["tamanho_bytes"], r["crc32"], r["sha256"], arq_map.get(r["arquivo_disco_id"]) if r["arquivo_disco_id"] else None),
            )
            contagens["acervo.bru_zip_entrada"] = n

            n, lin_map = _carregar_tabela_por_chave(
                sl_lab, cur, "bru_linha", "acervo.bru_linha",
                ["chave", "arquivo_id", "pagina", "n_linha", "texto", "x0", "y0", "tam_fonte", "fonte", "cor_hex", "eh_marca_dagua", "destino"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["pagina"], r["n_linha"], r["texto"], r["x0"], r["y0"], r["tam_fonte"], r["fonte"], r["cor_hex"], bool(r["eh_marca_dagua"]), r["destino"]),
                page_size=5000,
            )
            contagens["acervo.bru_linha"] = n

            n, cel_map = _carregar_tabela_por_chave(
                sl_lab, cur, "bru_celula", "acervo.bru_celula",
                ["chave", "arquivo_id", "aba", "ordem_aba", "linha", "coluna", "endereco", "tipo_dado", "valor_texto", "valor_cacheado", "formula", "formato_numero", "destino"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["aba"], r["ordem_aba"], r["linha"], r["coluna"], r["endereco"], r["tipo_dado"], r["valor_texto"], r["valor_cacheado"], r["formula"], r["formato_numero"], r["destino"]),
            )
            contagens["acervo.bru_celula"] = n

            n, par_map = _carregar_tabela_por_chave(
                sl_lab, cur, "bru_paragrafo", "acervo.bru_paragrafo",
                ["chave", "arquivo_id", "ordem", "origem_bloco", "tabela_idx", "linha_idx", "coluna_idx", "estilo", "texto", "destino"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["ordem"], r["origem_bloco"], r["tabela_idx"], r["linha_idx"], r["coluna_idx"], r["estilo"], r["texto"], r["destino"]),
            )
            contagens["acervo.bru_paragrafo"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "bru_sigaa_item", "acervo.bru_sigaa_item",
                ["chave", "ordem", "status_fetch", "content_type", "bytes_fetch", "rotulo_sigaa", "link_texto", "dossie_inferido", "arquivo_id", "observacao"],
                lambda r: (r["chave"], r["ordem"], r["status_fetch"], r["content_type"], r["bytes_fetch"], r["rotulo_sigaa"], r["link_texto"], r["dossie_inferido"], arq_map.get(r["arquivo_id"]) if r["arquivo_id"] else None, r["observacao"]),
            )
            contagens["acervo.bru_sigaa_item"] = n

            # Extraido (ext_*)
            n, doc_map = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_documento", "acervo.ext_documento",
                ["chave", "arquivo_id", "modelo", "tipo", "numero", "serie", "data_emissao", "data_referencia", "doc_ref", "estabelecimento_prefixo", "valor_total_centavos", "moeda", "valor_total_texto"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["modelo"], r["tipo"], r["numero"], r["serie"], r["data_emissao"], r["data_referencia"], r["doc_ref"], r["estabelecimento_prefixo"], r["valor_total_centavos"], r["moeda"], r["valor_total_texto"]),
            )
            contagens["acervo.ext_documento"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_campo", "acervo.ext_campo",
                ["chave", "documento_id", "secao", "rotulo", "valor_texto", "valor_centavos", "moeda", "valor_micro", "valor_data", "linha_bruto_id"],
                lambda r: (r["chave"], doc_map[r["documento_id"]], r["secao"], r["rotulo"], r["valor_texto"], r["valor_centavos"], r["moeda"], r["valor_micro"], r["valor_data"], lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
                page_size=4000,
            )
            contagens["acervo.ext_campo"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_item", "acervo.ext_item",
                ["chave", "documento_id", "tabela", "n_linha", "colunas_json", "linha_bruto_id"],
                lambda r: (r["chave"], doc_map[r["documento_id"]], r["tabela"], r["n_linha"], r["colunas_json"], lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
            )
            contagens["acervo.ext_item"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_extrato_linha", "acervo.ext_extrato_linha",
                ["chave", "arquivo_id", "aba", "n_linha", "conta_codigo", "data_movimento", "historico", "doc_ref", "debito_centavos", "credito_centavos", "saldo_centavos", "origem_valor", "celula_saldo_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["aba"], r["n_linha"], r["conta_codigo"], r["data_movimento"], r["historico"], r["doc_ref"], r["debito_centavos"], r["credito_centavos"], r["saldo_centavos"], r["origem_valor"], cel_map.get(r["celula_saldo_id"]) if r["celula_saldo_id"] else None),
            )
            contagens["acervo.ext_extrato_linha"] = n

            n, dlanc_map = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_diario_lancamento", "acervo.ext_diario_lancamento",
                ["chave", "arquivo_id", "ano", "numero_lancamento", "data_lancamento", "historico", "tag_ref", "linha_bruto_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["ano"], r["numero_lancamento"], r["data_lancamento"], r["historico"], r["tag_ref"], lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
            )
            contagens["acervo.ext_diario_lancamento"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_diario_partida", "acervo.ext_diario_partida",
                ["chave", "lancamento_id", "ordem", "conta_codigo", "conta_nome", "dc", "valor_centavos", "valor_texto", "linha_bruto_id"],
                lambda r: (r["chave"], dlanc_map[r["lancamento_id"]], r["ordem"], r["conta_codigo"], r["conta_nome"], r["dc"], r["valor_centavos"], r["valor_texto"], lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
            )
            contagens["acervo.ext_diario_partida"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_razao_linha", "acervo.ext_razao_linha",
                ["chave", "arquivo_id", "ano", "conta_codigo", "conta_nome", "ordem", "data_movimento", "numero_lancamento", "historico", "debito_centavos", "credito_centavos", "saldo_centavos", "saldo_dc", "linha_bruto_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["ano"], r["conta_codigo"], r["conta_nome"], r["ordem"], r["data_movimento"], r["numero_lancamento"], r["historico"], r["debito_centavos"], r["credito_centavos"], r["saldo_centavos"], r["saldo_dc"], lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
            )
            contagens["acervo.ext_razao_linha"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_balancete_linha", "acervo.ext_balancete_linha",
                ["chave", "arquivo_id", "fonte", "periodo", "conta_codigo", "conta_nome", "saldo_anterior_centavos", "debito_centavos", "credito_centavos", "saldo_atual_centavos", "origem_valor", "celula_id", "linha_bruto_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["fonte"], r["periodo"], r["conta_codigo"], r["conta_nome"], r["saldo_anterior_centavos"], r["debito_centavos"], r["credito_centavos"], r["saldo_atual_centavos"], r["origem_valor"], cel_map.get(r["celula_id"]) if r["celula_id"] else None, lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
            )
            contagens["acervo.ext_balancete_linha"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_estoque_linha", "acervo.ext_estoque_linha",
                ["chave", "arquivo_id", "aba", "ordem", "produto_codigo", "descricao", "dados_json", "celula_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["aba"], r["ordem"], r["produto_codigo"], r["descricao"], r["dados_json"], cel_map.get(r["celula_id"]) if r["celula_id"] else None),
            )
            contagens["acervo.ext_estoque_linha"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_parametro_planilha", "acervo.ext_parametro_planilha",
                ["chave", "arquivo_id", "aba", "rotulo", "valor_texto", "celula_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["aba"], r["rotulo"], r["valor_texto"], cel_map.get(r["celula_id"]) if r["celula_id"] else None),
            )
            contagens["acervo.ext_parametro_planilha"] = n

            n, emat_map = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_material", "acervo.ext_material",
                ["chave", "arquivo_id", "dossie", "categoria", "titulo"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], r["dossie"], r["categoria"], r["titulo"]),
            )
            contagens["acervo.ext_material"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_secao", "acervo.ext_secao",
                ["chave", "material_id", "ordem", "titulo", "conteudo", "paragrafo_id", "linha_bruto_id"],
                lambda r: (r["chave"], emat_map[r["material_id"]], r["ordem"], r["titulo"], r["conteudo"], par_map.get(r["paragrafo_id"]) if r["paragrafo_id"] else None, lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None),
            )
            contagens["acervo.ext_secao"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "ext_nota_didatica", "acervo.ext_nota_didatica",
                ["chave", "arquivo_id", "documento_id", "texto", "linha_bruto_id", "celula_id", "paragrafo_id"],
                lambda r: (r["chave"], arq_map[r["arquivo_id"]], doc_map.get(r["documento_id"]) if r["documento_id"] else None, r["texto"], lin_map.get(r["linha_bruto_id"]) if r["linha_bruto_id"] else None, cel_map.get(r["celula_id"]) if r["celula_id"] else None, par_map.get(r["paragrafo_id"]) if r["paragrafo_id"] else None),
            )
            contagens["acervo.ext_nota_didatica"] = n

            # --- 2. SCHEMA erp (normalizado 3FN multi-empresa) ---
            n, pes_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_pessoa", "erp.pessoa",
                ["chave", "tipo_pessoa", "nome_canonico"],
                lambda r: (r["chave"], r["tipo_pessoa"], r["nome_canonico"]),
            )
            contagens["erp.pessoa"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_pessoa_identificador", "erp.pessoa_identificador",
                ["chave", "pessoa_id", "tipo_id", "valor", "eh_ficticio", "fonte_chave"],
                lambda r: (r["chave"], pes_map[r["pessoa_id"]], r["tipo_id"], r["valor"], bool(r["eh_ficticio"]), r["fonte_chave"]),
            )
            contagens["erp.pessoa_identificador"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_pessoa_ocorrencia", "erp.pessoa_ocorrencia",
                ["chave", "pessoa_id", "nome_impresso", "identificador_impresso", "papel", "fonte_chave"],
                lambda r: (r["chave"], pes_map[r["pessoa_id"]], r["nome_impresso"], r["identificador_impresso"], r["papel"], r["fonte_chave"]),
            )
            contagens["erp.pessoa_ocorrencia"] = n

            def _papel_empresa(chave_emp: str, papel_orig: str) -> str:
                if chave_emp == "emp:prisma_jrna_g07":
                    return "escritorio_contabil"
                return papel_orig

            n, emp_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_empresa", "erp.empresa",
                ["chave", "pessoa_id", "nome_curto", "papel_no_caso"],
                lambda r: (r["chave"], pes_map[r["pessoa_id"]], r["nome_curto"], _papel_empresa(str(r["chave"]), str(r["papel_no_caso"]))),
            )
            contagens["erp.empresa"] = n

            n, est_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_estabelecimento", "erp.estabelecimento",
                ["chave", "empresa_id", "tipo", "cnpj", "uf", "municipio", "endereco"],
                lambda r: (r["chave"], emp_map[r["empresa_id"]], r["tipo"], r["cnpj"], r["uf"], r["municipio"], r["endereco"]),
            )
            contagens["erp.estabelecimento"] = n

            est_to_emp_pg: dict[int, int] = {}
            for r in sl_lab.execute("SELECT id, empresa_id FROM nrm_estabelecimento").fetchall():
                est_to_emp_pg[est_map[int(r["id"])]] = emp_map[int(r["empresa_id"])]

            emp_pg_by_chave = _mapa_chave_id(cur, "erp.empresa")
            emp_rs_d4_pg = emp_pg_by_chave["emp:rota_sul_d4"]

            n, cta_bco_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_conta_bancaria", "erp.conta_bancaria",
                ["chave", "empresa_id", "estabelecimento_id", "banco_nome", "agencia", "conta_numero", "descricao"],
                lambda r: (r["chave"], emp_map[r["empresa_id"]], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["banco_nome"], r["agencia"], r["conta_numero"], r["descricao"]),
            )
            contagens["erp.conta_bancaria"] = n

            n, evt_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_evento", "erp.evento",
                ["chave", "empresa_id", "tipo_evento", "data_evento", "descricao", "fonte_chave"],
                lambda r: (r["chave"], emp_map.get(r["empresa_id"]) if r["empresa_id"] else None, r["tipo_evento"], r["data_evento"], r["descricao"], r["fonte_chave"]),
            )
            contagens["erp.evento"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_fato", "erp.fato",
                ["chave", "sujeito_chave", "evento_id", "atributo", "valor_texto", "valor_centavos", "vigente_de", "vigente_ate", "fonte_chave"],
                lambda r: (r["chave"], r["sujeito_chave"], evt_map.get(r["evento_id"]) if r["evento_id"] else None, r["atributo"], r["valor_texto"], r["valor_centavos"], r["vigente_de"], r["vigente_ate"], r["fonte_chave"]),
            )
            contagens["erp.fato"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_participacao_societaria", "erp.participacao_societaria",
                ["chave", "empresa_id", "socio_pessoa_id", "quotas", "valor_centavos", "percentual_micro", "papel", "vigente_de", "vigente_ate", "fonte_chave"],
                lambda r: (r["chave"], emp_map[r["empresa_id"]], pes_map[r["socio_pessoa_id"]], r["quotas"], r["valor_centavos"], r["percentual_micro"], r["papel"], r["vigente_de"], r["vigente_ate"], r["fonte_chave"]),
            )
            contagens["erp.participacao_societaria"] = n

            n, prod_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_produto", "erp.produto",
                ["chave", "codigo_interno", "descricao", "ncm", "cest", "origem"],
                lambda r: (r["chave"], r["codigo_interno"], r["descricao"], r["ncm"], r["cest"], r["origem"]),
            )
            contagens["erp.produto"] = n

            n, df_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_documento_fiscal", "erp.documento_fiscal",
                ["chave", "estabelecimento_id", "tipo_documento", "numero", "serie", "chave_acesso", "data_emissao", "emitente_pessoa_id", "destinatario_pessoa_id", "natureza_operacao", "valor_total_centavos", "moeda", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["tipo_documento"], r["numero"], r["serie"], r["chave_acesso"], r["data_emissao"], pes_map.get(r["emitente_pessoa_id"]) if r["emitente_pessoa_id"] else None, pes_map.get(r["destinatario_pessoa_id"]) if r["destinatario_pessoa_id"] else None, r["natureza_operacao"], r["valor_total_centavos"], r["moeda"], r["doc_ref"]),
            )
            contagens["erp.documento_fiscal"] = n

            n, dfi_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_documento_fiscal_item", "erp.documento_fiscal_item",
                ["chave", "documento_fiscal_id", "n_item", "produto_id", "codigo_item_documento", "descricao", "ncm_hs", "cfop", "cst_csosn", "unidade", "quantidade_micro", "valor_unitario_micro", "valor_total_centavos", "moeda"],
                lambda r: (r["chave"], df_map[r["documento_fiscal_id"]], r["n_item"], prod_map.get(r["produto_id"]) if r["produto_id"] else None, r["codigo_item_documento"], r["descricao"], r["ncm_hs"], r["cfop"], r["cst_csosn"], r["unidade"], r["quantidade_micro"], r["valor_unitario_micro"], r["valor_total_centavos"], r["moeda"]),
            )
            contagens["erp.documento_fiscal_item"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_item_tributo", "erp.item_tributo",
                ["chave", "item_id", "documento_fiscal_id", "tributo", "base_centavos", "aliquota_micro", "aliquota_texto", "valor_centavos"],
                lambda r: (r["chave"], dfi_map.get(r["item_id"]) if r["item_id"] else None, df_map[r["documento_fiscal_id"]], r["tributo"], r["base_centavos"], r["aliquota_micro"], r["aliquota_texto"], r["valor_centavos"]),
            )
            contagens["erp.item_tributo"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_movimento_bancario", "erp.movimento_bancario",
                ["chave", "conta_bancaria_id", "data_movimento", "historico", "doc_ref", "tipo_dc", "valor_centavos", "saldo_apos_centavos", "origem_saldo"],
                lambda r: (r["chave"], cta_bco_map[r["conta_bancaria_id"]], r["data_movimento"], r["historico"], r["doc_ref"], r["tipo_dc"], r["valor_centavos"], r["saldo_apos_centavos"], r["origem_saldo"]),
            )
            contagens["erp.movimento_bancario"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_comprovante", "erp.comprovante",
                ["chave", "estabelecimento_id", "subtipo", "data_operacao", "valor_centavos", "moeda", "contraparte_pessoa_id", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["subtipo"], r["data_operacao"], r["valor_centavos"], r["moeda"], pes_map.get(r["contraparte_pessoa_id"]) if r["contraparte_pessoa_id"] else None, r["doc_ref"]),
            )
            contagens["erp.comprovante"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_titulo", "erp.titulo",
                ["chave", "estabelecimento_id", "subtipo", "numero", "data_vencimento", "valor_centavos", "beneficiario_pessoa_id", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["subtipo"], r["numero"], r["data_vencimento"], r["valor_centavos"], pes_map.get(r["beneficiario_pessoa_id"]) if r["beneficiario_pessoa_id"] else None, r["doc_ref"]),
            )
            contagens["erp.titulo"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_cambio", "erp.cambio",
                ["chave", "estabelecimento_id", "contrato_numero", "data_contratacao", "moeda_estrangeira", "valor_estrangeiro_centavos", "taxa_micro", "taxa_texto", "principal_brl_centavos", "iof_centavos", "tarifa_centavos", "valor_total_brl_centavos", "exportador_pessoa_id", "invoice_numero", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["contrato_numero"], r["data_contratacao"], r["moeda_estrangeira"], r["valor_estrangeiro_centavos"], r["taxa_micro"], r["taxa_texto"], r["principal_brl_centavos"], r["iof_centavos"], r["tarifa_centavos"], r["valor_total_brl_centavos"], pes_map.get(r["exportador_pessoa_id"]) if r["exportador_pessoa_id"] else None, r["invoice_numero"], r["doc_ref"]),
            )
            contagens["erp.cambio"] = n

            n, ccred_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_contrato_credito", "erp.contrato_credito",
                ["chave", "empresa_id", "numero_contrato", "data_contratacao", "principal_centavos", "taxa_juros_texto", "doc_ref"],
                lambda r: (r["chave"], emp_map[r["empresa_id"]], r["numero_contrato"], r["data_contratacao"], r["principal_centavos"], r["taxa_juros_texto"], r["doc_ref"]),
            )
            contagens["erp.contrato_credito"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_parcela", "erp.parcela",
                ["chave", "contrato_id", "numero_parcela", "data_vencimento", "amortizacao_centavos", "juros_centavos", "total_centavos", "situacao"],
                lambda r: (r["chave"], ccred_map[r["contrato_id"]], r["numero_parcela"], r["data_vencimento"], r["amortizacao_centavos"], r["juros_centavos"], r["total_centavos"], r["situacao"]),
            )
            contagens["erp.parcela"] = n

            n, lqc_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_liquidacao_cartao", "erp.liquidacao_cartao",
                ["chave", "estabelecimento_id", "data_liquidacao", "valor_bruto_centavos", "taxa_centavos", "valor_liquido_centavos", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["data_liquidacao"], r["valor_bruto_centavos"], r["taxa_centavos"], r["valor_liquido_centavos"], r["doc_ref"]),
            )
            contagens["erp.liquidacao_cartao"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_liquidacao_cartao_venda", "erp.liquidacao_cartao_venda",
                ["chave", "liquidacao_id", "data_venda", "autorizacao", "modalidade", "parcela_texto", "valor_bruto_centavos", "valor_liquido_centavos"],
                lambda r: (r["chave"], lqc_map[r["liquidacao_id"]], r["data_venda"], r["autorizacao"], r["modalidade"], r["parcela_texto"], r["valor_bruto_centavos"], r["valor_liquido_centavos"]),
            )
            contagens["erp.liquidacao_cartao_venda"] = n

            n, guia_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_guia", "erp.guia",
                ["chave", "estabelecimento_id", "tipo_guia", "competencia", "data_vencimento", "valor_principal_centavos", "valor_total_centavos", "uf", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["tipo_guia"], r["competencia"], r["data_vencimento"], r["valor_principal_centavos"], r["valor_total_centavos"], r["uf"], r["doc_ref"]),
            )
            contagens["erp.guia"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_guia_composicao", "erp.guia_composicao",
                ["chave", "guia_id", "tributo_codigo", "descricao", "valor_centavos"],
                lambda r: (r["chave"], guia_map[r["guia_id"]], r["tributo_codigo"], r["descricao"], r["valor_centavos"]),
            )
            contagens["erp.guia_composicao"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_apuracao", "erp.apuracao",
                ["chave", "empresa_id", "tipo_apuracao", "competencia", "receita_bruta_centavos", "rbt12_centavos", "tributo_apurado_centavos", "doc_ref"],
                lambda r: (r["chave"], emp_map[r["empresa_id"]], r["tipo_apuracao"], r["competencia"], r["receita_bruta_centavos"], r["rbt12_centavos"], r["tributo_apurado_centavos"], r["doc_ref"]),
            )
            contagens["erp.apuracao"] = n

            n, di_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_di", "erp.di",
                ["chave", "estabelecimento_id", "numero_di", "data_registro", "moeda", "taxa_micro", "taxa_texto", "valor_fob_moeda_centavos", "frete_seguro_moeda_centavos", "valor_aduaneiro_brl_centavos", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["numero_di"], r["data_registro"], r["moeda"], r["taxa_micro"], r["taxa_texto"], r["valor_fob_moeda_centavos"], r["frete_seguro_moeda_centavos"], r["valor_aduaneiro_brl_centavos"], r["doc_ref"]),
            )
            contagens["erp.di"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_di_adicao", "erp.di_adicao",
                ["chave", "di_id", "numero_adicao", "ncm", "valor_aduaneiro_centavos", "ii_centavos", "ipi_centavos", "pis_imp_centavos", "cofins_imp_centavos"],
                lambda r: (r["chave"], di_map[r["di_id"]], r["numero_adicao"], r["ncm"], r["valor_aduaneiro_centavos"], r["ii_centavos"], r["ipi_centavos"], r["pis_imp_centavos"], r["cofins_imp_centavos"]),
            )
            contagens["erp.di_adicao"] = n

            n, fc_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_fechamento_caixa", "erp.fechamento_caixa",
                ["chave", "estabelecimento_id", "data_fechamento", "valor_total_centavos", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["data_fechamento"], r["valor_total_centavos"], r["doc_ref"]),
            )
            contagens["erp.fechamento_caixa"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_fechamento_caixa_dia", "erp.fechamento_caixa_dia",
                ["chave", "fechamento_id", "data_dia", "valor_centavos"],
                lambda r: (r["chave"], fc_map[r["fechamento_id"]], r["data_dia"], r["valor_centavos"]),
            )
            contagens["erp.fechamento_caixa_dia"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_memorando", "erp.memorando",
                ["chave", "estabelecimento_id", "data_memorando", "assunto", "valor_centavos", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["data_memorando"], r["assunto"], r["valor_centavos"], r["doc_ref"]),
            )
            contagens["erp.memorando"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_recibo", "erp.recibo",
                ["chave", "estabelecimento_id", "subtipo", "data_recibo", "competencia", "beneficiario_pessoa_id", "valor_centavos", "doc_ref"],
                lambda r: (r["chave"], est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None, r["subtipo"], r["data_recibo"], r["competencia"], pes_map.get(r["beneficiario_pessoa_id"]) if r["beneficiario_pessoa_id"] else None, r["valor_centavos"], r["doc_ref"]),
            )
            contagens["erp.recibo"] = n

            # Contabil & Estoque (agora com empresa_id explicito!)
            n, cc_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_conta_contabil", "erp.conta_contabil",
                ["chave", "codigo", "nome", "grupo", "natureza"],
                lambda r: (r["chave"], r["codigo"], r["nome"], r["grupo"], r["natureza"]),
            )
            contagens["erp.conta_contabil"] = n

            n, lanc_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_lancamento", "erp.lancamento",
                ["chave", "empresa_id", "ano", "numero_lancamento", "data_lancamento", "historico", "tag_ref"],
                lambda r: (r["chave"], emp_rs_d4_pg, r["ano"], r["numero_lancamento"], r["data_lancamento"], r["historico"], r["tag_ref"]),
            )
            contagens["erp.lancamento"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_partida", "erp.partida",
                ["chave", "lancamento_id", "ordem", "conta_id", "dc", "valor_centavos"],
                lambda r: (r["chave"], lanc_map[r["lancamento_id"]], r["ordem"], cc_map[r["conta_id"]], r["dc"], r["valor_centavos"]),
            )
            contagens["erp.partida"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_saldo", "erp.saldo",
                ["chave", "empresa_id", "conta_id", "periodo", "fonte", "saldo_anterior_centavos", "debito_centavos", "credito_centavos", "saldo_atual_centavos"],
                lambda r: (r["chave"], emp_rs_d4_pg, cc_map[r["conta_id"]], r["periodo"], r["fonte"], r["saldo_anterior_centavos"], r["debito_centavos"], r["credito_centavos"], r["saldo_atual_centavos"]),
            )
            contagens["erp.saldo"] = n

            n, cic_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_ciclo_importacao", "erp.ciclo_importacao",
                ["chave", "empresa_id", "cambio_doc_ref", "data_cambio", "data_entrada_estoque", "pais_origem", "principal_brl_centavos", "iof_centavos"],
                lambda r: (r["chave"], emp_map.get(r["empresa_id"]) if r["empresa_id"] else emp_rs_d4_pg, r["cambio_doc_ref"], r["data_cambio"], r["data_entrada_estoque"], r["pais_origem"], r["principal_brl_centavos"], r["iof_centavos"]),
            )
            contagens["erp.ciclo_importacao"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_estoque_movimento", "erp.estoque_movimento",
                ["chave", "empresa_id", "produto_id", "ciclo_importacao_id", "tipo_movimento", "data_movimento", "quantidade", "custo_unitario_centavos", "valor_total_centavos"],
                lambda r: (r["chave"], emp_rs_d4_pg, prod_map[r["produto_id"]], cic_map.get(r["ciclo_importacao_id"]) if r["ciclo_importacao_id"] else None, r["tipo_movimento"], r["data_movimento"], r["quantidade"], r["custo_unitario_centavos"], r["valor_total_centavos"]),
            )
            contagens["erp.estoque_movimento"] = n

            n, tx_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_transacao", "erp.transacao",
                ["chave", "empresa_id", "regra_agrupamento", "doc_ref", "estabelecimento_id", "ano_mes", "data_referencia", "status_vinculo"],
                lambda r: (
                    r["chave"],
                    est_to_emp_pg.get(est_map[r["estabelecimento_id"]], emp_rs_d4_pg) if r["estabelecimento_id"] and r["estabelecimento_id"] in est_map else emp_rs_d4_pg,
                    r["regra_agrupamento"],
                    r["doc_ref"],
                    est_map.get(r["estabelecimento_id"]) if r["estabelecimento_id"] else None,
                    r["ano_mes"],
                    r["data_referencia"],
                    r["status_vinculo"],
                ),
            )
            contagens["erp.transacao"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_transacao_membro", "erp.transacao_membro",
                ["chave", "transacao_id", "tabela_membro", "membro_chave", "papel_membro", "criterio_vinculo"],
                lambda r: (r["chave"], tx_map[r["transacao_id"]], r["tabela_membro"], r["membro_chave"], r["papel_membro"], r["criterio_vinculo"]),
            )
            contagens["erp.transacao_membro"] = n

            # Curso (erp.*)
            n, dos_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_dossie", "erp.dossie",
                ["chave", "codigo", "titulo", "periodo_texto", "prazo_texto"],
                lambda r: (r["chave"], r["codigo"], r["titulo"], r["periodo_texto"], r["prazo_texto"]),
            )
            contagens["erp.dossie"] = n

            n, req_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_requisito", "erp.requisito",
                ["chave", "dossie_id", "codigo", "descricao", "fonte_chave"],
                lambda r: (r["chave"], dos_map[r["dossie_id"]], r["codigo"], r["descricao"], r["fonte_chave"]),
            )
            contagens["erp.requisito"] = n

            n, mat_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_material", "erp.material",
                ["chave", "dossie_id", "categoria", "titulo", "arquivo_id"],
                lambda r: (r["chave"], dos_map.get(r["dossie_id"]) if r["dossie_id"] else None, r["categoria"], r["titulo"], arq_map[r["arquivo_id"]]),
            )
            contagens["erp.material"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_material_secao", "erp.material_secao",
                ["chave", "material_id", "ordem", "titulo", "conteudo"],
                lambda r: (r["chave"], mat_map[r["material_id"]], r["ordem"], r["titulo"], r["conteudo"]),
            )
            contagens["erp.material_secao"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_devolutiva", "erp.devolutiva",
                ["chave", "dossie_id", "grupo", "nossa_dupla", "nota_texto", "resumo", "material_id"],
                lambda r: (r["chave"], dos_map[r["dossie_id"]], r["grupo"], bool(r["nossa_dupla"]), r["nota_texto"], r["resumo"], mat_map[r["material_id"]]),
            )
            contagens["erp.devolutiva"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_nota_didatica", "erp.nota_didatica",
                ["chave", "origem_chave", "texto"],
                lambda r: (r["chave"], r["origem_chave"], r["texto"]),
            )
            contagens["erp.nota_didatica"] = n

            n, tema_map = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_tema", "erp.tema",
                ["chave", "termo"],
                lambda r: (r["chave"], r["termo"]),
            )
            contagens["erp.tema"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "nrm_vinculo", "erp.vinculo",
                ["chave", "tema_id", "alvo_tabela", "alvo_chave", "criterio"],
                lambda r: (r["chave"], tema_map[r["tema_id"]], r["alvo_tabela"], r["alvo_chave"], r["criterio"]),
            )
            contagens["erp.vinculo"] = n

            # --- 3. MULTI-EMPRESA + CATALOGO D1 (200 criterios) ---
            # 3a. Relacoes iniciais escritorio (Prisma JRNA G07) -> clientes do estudo
            escr_id = emp_pg_by_chave.get("emp:prisma_jrna_g07")
            if escr_id:
                rels = [
                    ("rel:g07:rota_sul_d2", escr_id, emp_pg_by_chave["emp:rota_sul_d2"], "2026-09-14", "estudo_caso", "D2 — Estudo de Caso 02"),
                    ("rel:g07:rota_sul_d4", escr_id, emp_pg_by_chave["emp:rota_sul_d4"], "2026-09-14", "estudo_caso", "D4 — Contrato Continuado"),
                    ("rel:g07:meia_ponte", escr_id, emp_pg_by_chave["emp:meia_ponte"], "2026-09-14", "estudo_caso", "D4 — Consulta Tributaria"),
                    ("rel:g07:horizonte", escr_id, emp_pg_by_chave["emp:horizonte"], "2026-10-20", "estudo_caso", "D3 — Auditoria NFSe"),
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO erp.relacao_escritorio_cliente
                        (chave, escritorio_empresa_id, cliente_empresa_id, vigente_de, status, contrato_ref, origem_registro)
                    VALUES %s ON CONFLICT (chave) DO NOTHING
                    """,
                    [(c, e, cl, dt, st, ref, "acervo_sigaa") for (c, e, cl, dt, st, ref) in rels],
                )
                contagens["erp.relacao_escritorio_cliente"] = len(rels)

                enqs = [
                    ("enq:g07:2026", escr_id, "ME", "Simples_Anexo_III", "6920-6/01", '["6920-6/02"]', "DF-SIMULADO-G07", "2026-09-09", "arq:D1/Devolutivas_Individuais_Dossie1/Devolutiva_Dossie1_G07.docx"),
                    ("enq:rs_d4:2025", emp_pg_by_chave["emp:rota_sul_d4"], "EPP", "Simples_Anexo_I", "4530-7/05", '[]', None, "2025-01-01", "arq:D4/Carta_dos_socios_ao_contador_Goiania.pdf"),
                    ("enq:mp:2021", emp_pg_by_chave["emp:meia_ponte"], "ME", "Simples_Anexo_I", "4530-7/05", '[]', None, "2021-01-01", "arq:D4/Carta_dos_socios_ao_contador_Goiania.pdf"),
                    ("enq:hz:2026", emp_pg_by_chave["emp:horizonte"], "EPP", "Lucro_Presumido", "7112-0/00", '[]', None, "2026-10-20", "arq:D3/01_NFSe_Ficticia_Auditoria_Ente_Federal.pdf"),
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO erp.enquadramento_historico
                        (chave, empresa_id, porte, regime_tributario, cnae_principal, cnaes_secundarios, registro_crc, vigente_de, fonte_chave, origem_registro)
                    VALUES %s ON CONFLICT (chave) DO NOTHING
                    """,
                    [(c, e, p, r, cp, cs, crc, dt, src, "acervo_sigaa") for (c, e, p, r, cp, cs, crc, dt, src) in enqs],
                )
                contagens["erp.enquadramento_historico"] = len(enqs)

            # 3b. Catalogo de criterios das 4 matrizes D1
            criterios = extrair_criterios_matrizes_d1(sl_lab)
            if criterios:
                execute_values(
                    cur,
                    """
                    INSERT INTO erp.d1_matriz_criterio
                        (chave, matriz, bloco, bloco_titulo, bloco_peso, codigo, descricao, referencia_fonte)
                    VALUES %s ON CONFLICT (chave) DO NOTHING
                    """,
                    [
                        (c.chave, c.matriz, c.bloco, c.bloco_titulo, c.bloco_peso, c.codigo, c.descricao, c.referencia_fonte)
                        for c in criterios
                    ],
                )
            contagens["erp.d1_matriz_criterio"] = len(criterios)

            # --- 4. SCHEMA auditoria (evidencia + conferencia + trabalho.db) ---
            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "evidencia", "auditoria.evidencia",
                ["chave", "tabela_destino", "registro_chave", "bru_tabela", "bru_chave"],
                lambda r: (r["chave"], r["tabela_destino"], r["registro_chave"], r["bru_tabela"], r["bru_chave"]),
                page_size=4000,
            )
            contagens["auditoria.evidencia"] = n

            n, _ = _carregar_tabela_por_chave(
                sl_lab, cur, "conferencia", "auditoria.conferencia",
                ["chave", "regra", "severidade", "registros_json", "valores_json", "status", "descricao"],
                lambda r: (r["chave"], r["regra"], r["severidade"], r["registros_json"], r["valores_json"], r["status"], r["descricao"]),
            )
            contagens["auditoria.conferencia"] = n

            if sl_trab is not None:
                n, _ = _carregar_tabela_por_chave(
                    sl_trab, cur, "anotacao", "auditoria.anotacao",
                    ["chave", "alvo_tabela", "alvo_chave", "autor", "dossie", "conteudo", "criado_em"],
                    lambda r: (r["chave"], r["alvo_tabela"], r["alvo_chave"], r["autor"], r["dossie"], r["conteudo"], r["criado_em"]),
                )
                contagens["auditoria.anotacao"] = n

                n, _ = _carregar_tabela_por_chave(
                    sl_trab, cur, "decisao", "auditoria.decisao",
                    ["chave", "dossie", "alvo_chave", "titulo", "justificativa", "fonte_oficial", "autor", "criado_em"],
                    lambda r: (r["chave"], r["dossie"], r["alvo_chave"], r["titulo"], r["justificativa"], r["fonte_oficial"], r["autor"], r["criado_em"]),
                )
                contagens["auditoria.decisao"] = n

                n, _ = _carregar_tabela_por_chave(
                    sl_trab, cur, "classificacao", "auditoria.classificacao",
                    ["chave", "alvo_tabela", "alvo_chave", "categoria", "valor", "observacao", "autor", "criado_em"],
                    lambda r: (r["chave"], r["alvo_tabela"], r["alvo_chave"], r["categoria"], r["valor"], r["observacao"], r["autor"], r["criado_em"]),
                )
                contagens["auditoria.classificacao"] = n

                req_pg_by_chave = _mapa_chave_id(cur, "erp.requisito")
                n, _ = _carregar_tabela_por_chave(
                    sl_trab, cur, "resposta_requisito", "auditoria.resposta_requisito",
                    ["chave", "requisito_id", "requisito_chave", "status", "resposta_md", "evidencias_chaves_json", "atualizado_em"],
                    lambda r: (r["chave"], req_pg_by_chave.get(str(r["requisito_chave"])), r["requisito_chave"], r["status"], r["resposta_md"], r["evidencias_chaves_json"], r["atualizado_em"]),
                )
                contagens["auditoria.resposta_requisito"] = n

        pg_conn.commit()
    finally:
        pg_conn.close()
        sl_lab.close()
        if sl_trab is not None:
            sl_trab.close()

    backup_path: Path | None = None
    if gerar_backup:
        backup_path = gerar_snapshot_pg()

    return {
        "banco": banco_nome,
        "migracoes": migracoes,
        "contagens": contagens,
        "backup": str(backup_path) if backup_path else None,
    }


def gerar_snapshot_pg(destino: Path | None = None) -> Path:
    """Gera snapshot binario da copia original no Postgres via pg_dump."""
    if not PG_DUMP_EXE.exists():
        raise FileNotFoundError(f"pg_dump nao encontrado em: {PG_DUMP_EXE}")
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    alvo = destino or (SNAPSHOTS_DIR / "lab_contabil_original.dump")
    cfg = parse_database_url()
    env = os.environ.copy()
    env["PGPASSWORD"] = str(cfg["password"])
    cmd = [
        str(PG_DUMP_EXE),
        "--host", str(cfg["host"]),
        "--port", str(cfg["port"]),
        "--username", str(cfg["user"]),
        "--format=custom",
        "--file", str(alvo),
        str(cfg["dbname"]),
    ]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"pg_dump falhou ({res.returncode}): {res.stderr.strip()}")
    return alvo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migra staging SQLite para o banco unico PostgreSQL 17.")
    parser.add_argument("--backup", action="store_true", help="Gera snapshot via pg_dump apos a carga.")
    parser.add_argument("--lab-db", type=Path, default=LABORATORIO_DB, help="Caminho para laboratorio.db.")
    parser.add_argument("--trab-db", type=Path, default=TRABALHO_DB, help="Caminho para trabalho.db.")
    args = parser.parse_args(argv)

    res = migrar_staging_para_pg(lab_db=args.lab_db, trab_db=args.trab_db, gerar_backup=args.backup)
    print(f"Banco PostgreSQL '{res['banco']}' atualizado. Migracoes: {res['migracoes']}")
    print("Tabelas carregadas:", len(res["contagens"]))
    if res["backup"]:
        print("Snapshot salvo em:", res["backup"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
