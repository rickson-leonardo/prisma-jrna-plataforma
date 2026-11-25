"""Conexao com o banco unico PostgreSQL 17 (lab_contabil) via DATABASE_URL/.env."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from sistema.config import PLATAFORMA_DIR

ENV_PATH = PLATAFORMA_DIR / ".env"


def _carregar_env_arquivo(env_path: Path = ENV_PATH) -> None:
    if not env_path.exists():
        return
    for linha in env_path.read_text(encoding="utf-8").splitlines():
        s = linha.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        chave, val = s.split("=", 1)
        chave = chave.strip()
        val = val.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = val


def obter_database_url() -> str:
    """Retorna DATABASE_URL de ambiente ou plataforma/.env sem expor credenciais."""
    _carregar_env_arquivo()
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL nao configurada. Copie 'plataforma/.env.example' para 'plataforma/.env' "
            "e preencha DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5432/lab_contabil"
        )
    return url


def parse_database_url(url: str | None = None) -> dict[str, str | int]:
    """Extrai host, port, user, password e dbname de DATABASE_URL."""
    alvo = url or obter_database_url()
    u = urlparse(alvo)
    if u.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"Esquema de DATABASE_URL invalido: {u.scheme!r}")
    return {
        "host": u.hostname or "localhost",
        "port": int(u.port or 5432),
        "user": unquote(u.username or "postgres"),
        "password": unquote(u.password or ""),
        "dbname": (u.path or "/lab_contabil").lstrip("/") or "lab_contabil",
    }


def conectar_pg(dbname_override: str | None = None, autocommit: bool = False) -> PgConnection:
    """Abre conexao psycopg2 com RealDictCursor no banco configurado."""
    cfg = parse_database_url()
    dbname = dbname_override or str(cfg["dbname"])
    conn = psycopg2.connect(
        host=str(cfg["host"]),
        port=int(cfg["port"]),
        user=str(cfg["user"]),
        password=str(cfg["password"]),
        dbname=dbname,
        cursor_factory=RealDictCursor,
    )
    conn.autocommit = autocommit
    return conn


def garantir_banco_existe() -> str:
    """Cria o banco de destino (ex.: lab_contabil) caso ainda nao exista no Postgres 17."""
    cfg = parse_database_url()
    alvo = str(cfg["dbname"])
    conn_adm = conectar_pg(dbname_override="postgres", autocommit=True)
    try:
        with conn_adm.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (alvo,))
            if cur.fetchone() is None:
                ident = '"' + alvo.replace('"', '""') + '"'
                cur.execute(f"CREATE DATABASE {ident} ENCODING 'UTF8'")
    finally:
        conn_adm.close()
    return alvo
