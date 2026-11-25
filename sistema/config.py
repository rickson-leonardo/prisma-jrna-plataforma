"""Configurações e caminhos da plataforma do Laboratório Contábil."""

from __future__ import annotations

import os
from pathlib import Path

PLATAFORMA_DIR: Path = Path(__file__).resolve().parents[1]
SISTEMA_DIR: Path = PLATAFORMA_DIR / "sistema"
SCHEMA_DIR: Path = SISTEMA_DIR / "schema"
DOCS_DIR: Path = PLATAFORMA_DIR / "docs"
BANCO_DIR: Path = PLATAFORMA_DIR / "banco"

# Diretório-pai onde residem D1/, D2/, D3/, D4/, Resultado/, _paginas/
ACERVO_DIR: Path = Path(
    os.environ.get("ACERVO_DIR", str(PLATAFORMA_DIR.parent))
).resolve()

LABORATORIO_DB: Path = Path(
    os.environ.get("LABORATORIO_DB", str(BANCO_DIR / "laboratorio.db"))
).resolve()

TRABALHO_DB: Path = Path(
    os.environ.get("TRABALHO_DB", str(BANCO_DIR / "trabalho.db"))
).resolve()

PASTAS_ACERVO: tuple[str, ...] = ("D1", "D2", "D3", "D4", "Resultado", "_paginas")
