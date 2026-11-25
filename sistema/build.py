"""Orquestrador do pipeline em camadas do Laboratório Contábil."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from sistema.bruto.acervo import executar_camada_bruta
from sistema.config import ACERVO_DIR, LABORATORIO_DB, SCHEMA_DIR, TRABALHO_DB
from sistema.extracao.curso import extrair_curso
from sistema.extracao.livros import extrair_livros
from sistema.extracao.motor import extrair_documentos_pdf, parse_nome_arquivo_d4
from sistema.extracao.planilhas import extrair_planilhas
from sistema.gerar_docs import gerar_documentacao
from sistema.normalizacao import normalizar_tudo
from sistema.qualidade.gates import executar_gates_fidelidade


def aplicar_schema_arquivo(conn: sqlite3.Connection, sql_path: Path) -> None:
    """Executa um script SQL de schema com foreign_keys habilitado."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(sql_path.read_text(encoding="utf-8"))


def inicializar_bancos(
    lab_db: Path = LABORATORIO_DB,
    trab_db: Path = TRABALHO_DB,
    recriar_lab: bool = True,
) -> tuple[sqlite3.Connection, sqlite3.Connection]:
    """Cria/recria laboratorio.db e garante trabalho.db sem apagar dados humanos."""
    lab_db.parent.mkdir(parents=True, exist_ok=True)
    trab_db.parent.mkdir(parents=True, exist_ok=True)

    if recriar_lab and lab_db.exists():
        lab_db.unlink()

    conn_lab = sqlite3.connect(lab_db)
    conn_lab.execute("PRAGMA journal_mode = WAL;")
    conn_lab.execute("PRAGMA synchronous = NORMAL;")
    conn_lab.execute("PRAGMA foreign_keys = ON;")

    for nome_sql in ("10_bruto.sql", "20_extraido.sql", "30_normalizado.sql", "40_plataforma.sql"):
        aplicar_schema_arquivo(conn_lab, SCHEMA_DIR / nome_sql)
    conn_lab.commit()

    conn_trab = sqlite3.connect(trab_db)
    conn_trab.execute("PRAGMA foreign_keys = ON;")
    aplicar_schema_arquivo(conn_trab, SCHEMA_DIR / "90_trabalho.sql")
    conn_trab.commit()

    return conn_lab, conn_trab


def _limpar_camada_normalizada(conn: sqlite3.Connection) -> None:
    """Limpa registros da Camada 3 e conferencia em ordem reversa de FK."""
    tabelas = (
        "evidencia",
        "conferencia",
        "nrm_vinculo",
        "nrm_tema",
        "nrm_nota_didatica",
        "nrm_devolutiva",
        "nrm_material_secao",
        "nrm_material",
        "nrm_requisito",
        "nrm_dossie",
        "nrm_transacao_membro",
        "nrm_transacao",
        "nrm_estoque_movimento",
        "nrm_ciclo_importacao",
        "nrm_saldo",
        "nrm_partida",
        "nrm_lancamento",
        "nrm_conta_contabil",
        "nrm_recibo",
        "nrm_memorando",
        "nrm_fechamento_caixa_dia",
        "nrm_fechamento_caixa",
        "nrm_di_adicao",
        "nrm_di",
        "nrm_apuracao",
        "nrm_guia_composicao",
        "nrm_guia",
        "nrm_liquidacao_cartao_venda",
        "nrm_liquidacao_cartao",
        "nrm_parcela",
        "nrm_contrato_credito",
        "nrm_cambio",
        "nrm_titulo",
        "nrm_comprovante",
        "nrm_movimento_bancario",
        "nrm_item_tributo",
        "nrm_documento_fiscal_item",
        "nrm_documento_fiscal",
        "nrm_produto",
        "nrm_participacao_societaria",
        "nrm_fato",
        "nrm_evento",
        "nrm_conta_bancaria",
        "nrm_estabelecimento",
        "nrm_empresa",
        "nrm_pessoa_ocorrencia",
        "nrm_pessoa_identificador",
        "nrm_pessoa",
    )
    for tabela in tabelas:
        if tabela == "conferencia":
            conn.execute("DELETE FROM conferencia WHERE regra != 'sigaa_html_vazio'")
        else:
            conn.execute(f"DELETE FROM {tabela}")


def _limpar_camada_extraida(conn: sqlite3.Connection, filtro_modelo: str | None = None) -> None:
    """Limpa registros da Camada 2 antes de re-extrair (total ou por modelo)."""
    if filtro_modelo is None:
        _limpar_camada_normalizada(conn)
        for tabela in (
            "ext_campo",
            "ext_item",
            "ext_nota_didatica",
            "ext_documento",
            "ext_extrato_linha",
            "ext_diario_partida",
            "ext_diario_lancamento",
            "ext_razao_linha",
            "ext_balancete_linha",
            "ext_estoque_linha",
            "ext_parametro_planilha",
            "ext_secao",
            "ext_material",
        ):
            conn.execute(f"DELETE FROM {tabela}")
        conn.execute(
            "UPDATE bru_linha SET destino = CASE WHEN eh_marca_dagua = 1 THEN 'marca_dagua' ELSE NULL END"
        )
        conn.execute("UPDATE bru_celula SET destino = NULL")
        conn.execute("UPDATE bru_paragrafo SET destino = NULL")
    else:
        doc_ids = [
            r[0]
            for r in conn.execute("SELECT id FROM ext_documento WHERE modelo = ?", (filtro_modelo,)).fetchall()
        ]
        if doc_ids:
            placeholders = ",".join("?" for _ in doc_ids)
            conn.execute(f"DELETE FROM ext_campo WHERE documento_id IN ({placeholders})", doc_ids)
            conn.execute(f"DELETE FROM ext_item WHERE documento_id IN ({placeholders})", doc_ids)
            conn.execute(f"DELETE FROM ext_nota_didatica WHERE documento_id IN ({placeholders})", doc_ids)
            conn.execute(f"DELETE FROM ext_documento WHERE id IN ({placeholders})", doc_ids)
        arq_rows = conn.execute(
            """
            SELECT id, nome FROM bru_arquivo
            WHERE dossie = 'D4' AND extensao = '.pdf' AND papel_acervo = 'primario' AND nome NOT LIKE 'Livro_%'
            """
        ).fetchall()
        alvo_arqs = [
            r[0] for r in arq_rows if parse_nome_arquivo_d4(str(r[1]))[0] == filtro_modelo
        ]
        if alvo_arqs:
            placeholders = ",".join("?" for _ in alvo_arqs)
            conn.execute(
                f"""
                UPDATE bru_linha
                SET destino = CASE WHEN eh_marca_dagua = 1 THEN 'marca_dagua' ELSE NULL END
                WHERE arquivo_id IN ({placeholders})
                """,
                alvo_arqs,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Constrói o banco relacional do Laboratório Contábil.")
    parser.add_argument(
        "--camada",
        choices=("bruto", "extraido", "normalizado", "plataforma", "tudo"),
        default="bruto",
        help="Camada alvo do build.",
    )
    parser.add_argument("--modelo", default=None, help="Filtra execução da Camada 2 para um modelo específico.")
    parser.add_argument("--acervo", type=Path, default=ACERVO_DIR, help="Diretório raiz do acervo.")
    parser.add_argument("--lab-db", type=Path, default=LABORATORIO_DB, help="Caminho para laboratorio.db.")
    parser.add_argument("--trab-db", type=Path, default=TRABALHO_DB, help="Caminho para trabalho.db.")
    args = parser.parse_args(argv)

    recriar = args.camada in ("bruto", "tudo")
    conn_lab, conn_trab = inicializar_bancos(args.lab_db, args.trab_db, recriar_lab=recriar)
    try:
        if args.camada in ("bruto", "tudo"):
            resumo_bruto = executar_camada_bruta(conn_lab, args.acervo)
            print("Camada 1 (bruto) concluída:", resumo_bruto)

        if args.camada in ("extraido", "tudo"):
            if not recriar:
                _limpar_camada_extraida(conn_lab, filtro_modelo=args.modelo)
            if args.modelo is not None:
                resumo_docs = extrair_documentos_pdf(conn_lab, filtro_modelo=args.modelo)
                print(f"Camada 2 (modelo={args.modelo}) concluída:", resumo_docs)
            else:
                resumo_livros = extrair_livros(conn_lab)
                print("Camada 2 (livros) concluída:", resumo_livros)
                resumo_planilhas = extrair_planilhas(conn_lab)
                print("Camada 2 (planilhas) concluída:", resumo_planilhas)
                resumo_docs = extrair_documentos_pdf(conn_lab)
                print("Camada 2 (documentos PDF) concluída:", resumo_docs)
                resumo_curso = extrair_curso(conn_lab)
                print("Camada 2 (curso) concluída:", resumo_curso)

        if args.camada in ("normalizado", "tudo"):
            if not recriar:
                _limpar_camada_normalizada(conn_lab)
            resumo_nrm = normalizar_tudo(conn_lab)
            print("Camada 3 (normalizado) concluída:", resumo_nrm)
            resumo_gates = executar_gates_fidelidade(conn_lab, incluir_camada3=True)
            print("Camada 3 (gates de fidelidade) concluída:", resumo_gates)

        if args.camada in ("plataforma", "tudo"):
            aplicar_schema_arquivo(conn_lab, SCHEMA_DIR / "40_plataforma.sql")
            print("Camada 4 (visões da plataforma) atualizada.")

        conn_lab.commit()
    finally:
        conn_lab.close()
        conn_trab.close()

    gerar_documentacao(args.lab_db, args.trab_db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
