"""Orquestrador do pipeline em camadas do Laboratório Contábil."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from sistema.bruto.acervo import executar_camada_bruta
from sistema.config import ACERVO_DIR, BANCO_DIR, LABORATORIO_DB, SCHEMA_DIR, TRABALHO_DB
from sistema.gerar_docs import gerar_documentacao


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
            resumo = executar_camada_bruta(conn_lab, args.acervo)
            print("Camada 1 (bruto) concluída:", resumo)

        if args.camada in ("extraido", "normalizado", "plataforma", "tudo"):
            if args.camada != "bruto":
                print(f"Aviso: camada '{args.camada}' ainda será implementada nas próximas fases.")

        conn_lab.commit()
    finally:
        conn_lab.close()
        conn_trab.close()

    gerar_documentacao(args.lab_db, args.trab_db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
