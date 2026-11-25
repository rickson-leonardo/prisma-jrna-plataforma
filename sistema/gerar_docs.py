"""Gerador de docs/dicionario.md e docs/er.md a partir do schema SQLite."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from sistema.config import DOCS_DIR, LABORATORIO_DB, SCHEMA_DIR, TRABALHO_DB


def _extrair_comentarios_sql() -> dict[str, dict[str, str]]:
    """Extrai comentarios inline de colunas por tabela nos arquivos .sql."""
    comentarios: dict[str, dict[str, str]] = {}
    for sql_path in sorted(SCHEMA_DIR.glob("*.sql")):
        texto = sql_path.read_text(encoding="utf-8")
        tabela_atual: str | None = None
        for linha in texto.splitlines():
            m_tab = re.match(r"^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)\s*\(", linha, re.I)
            if m_tab:
                tabela_atual = m_tab.group(1)
                comentarios.setdefault(tabela_atual, {})
                continue
            if tabela_atual and re.match(r"^\s*\)\s*;", linha):
                tabela_atual = None
                continue
            if tabela_atual:
                m_col = re.match(r"^\s*([a-zA-Z0-9_]+)\s+(?:INTEGER|TEXT|REAL|BLOB)\b.*?--\s*(.+)$", linha, re.I)
                if m_col:
                    comentarios[tabela_atual][m_col.group(1)] = m_col.group(2).strip()
    return comentarios


def gerar_documentacao(
    lab_db: Path = LABORATORIO_DB,
    trab_db: Path = TRABALHO_DB,
    docs_dir: Path = DOCS_DIR,
) -> tuple[Path, Path]:
    """Gera docs/dicionario.md e docs/er.md lendo os bancos SQLite reais."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    comentarios = _extrair_comentarios_sql()

    dic_linhas = [
        "# Dicionário de Dados — Laboratório Contábil",
        "",
        "Documento gerado automaticamente por `python -m sistema.gerar_docs` a partir do schema SQLite.",
        "",
    ]
    er_linhas = [
        "# Diagrama Entidade-Relacionamento (ER) — Laboratório Contábil",
        "",
        "Documento gerado automaticamente por `python -m sistema.gerar_docs` a partir das FKs do SQLite.",
        "",
    ]

    for titulo_db, db_path in [("laboratorio.db", lab_db), ("trabalho.db", trab_db)]:
        if not db_path.exists():
            continue
        conn = sqlite3.connect(db_path)
        tabelas = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        views = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
            ).fetchall()
        ]

        dic_linhas.append(f"## Banco `{titulo_db}`")
        dic_linhas.append("")
        er_linhas.append(f"## `{titulo_db}`")
        er_linhas.append("")
        er_linhas.append("```mermaid")
        er_linhas.append("erDiagram")

        fks_mermaid: list[str] = []
        for tabela in tabelas:
            cols = conn.execute(f'PRAGMA table_info("{tabela}")').fetchall()
            fks = conn.execute(f'PRAGMA foreign_key_list("{tabela}")').fetchall()
            fk_map = {fk[3]: f"{fk[2]}.{fk[4]}" for fk in fks}
            for fk in fks:
                fks_mermaid.append(f"    {fk[2]} ||--o{{ {tabela} : \"{fk[3]}\"")

            dic_linhas.append(f"### `{tabela}`")
            dic_linhas.append("")
            dic_linhas.append("| Coluna | Tipo | Obrigatória | PK | FK | Descrição |")
            dic_linhas.append("|---|---|---|---|---|---|")
            er_linhas.append(f"    {tabela} {{")
            for _, nome, tipo, notnull, _, pk in cols:
                tipo_clean = tipo or "TEXT"
                obrig = "Sim" if (notnull or pk) else "Não"
                pk_str = "PK" if pk else ""
                fk_str = fk_map.get(nome, "")
                desc = comentarios.get(tabela, {}).get(nome, "")
                dic_linhas.append(f"| `{nome}` | `{tipo_clean}` | {obrig} | {pk_str} | `{fk_str}` | {desc} |")
                key_tag = "PK" if pk else ("FK" if fk_str else "")
                er_linhas.append(f"        {tipo_clean.lower()} {nome} {key_tag}".rstrip())
            er_linhas.append("    }")
            dic_linhas.append("")

        er_linhas.extend(sorted(set(fks_mermaid)))
        er_linhas.append("```")
        er_linhas.append("")

        if views:
            dic_linhas.append(f"### Views em `{titulo_db}`")
            dic_linhas.append("")
            for v in views:
                dic_linhas.append(f"- `{v}`")
            dic_linhas.append("")

        conn.close()

    dic_path = docs_dir / "dicionario.md"
    er_path = docs_dir / "er.md"
    dic_path.write_text("\n".join(dic_linhas) + "\n", encoding="utf-8")
    er_path.write_text("\n".join(er_linhas) + "\n", encoding="utf-8")
    return dic_path, er_path


if __name__ == "__main__":
    dic, er = gerar_documentacao()
    print(f"Gerados: {dic} e {er}")
