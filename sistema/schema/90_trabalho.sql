-- Banco humano (trabalho.db): nunca apagado pelo pipeline de rebuild
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS anotacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: anot:<uuid_ou_seq>
    alvo_tabela TEXT NOT NULL,
    alvo_chave TEXT NOT NULL,
    autor TEXT NOT NULL,
    dossie TEXT,
    conteudo TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS decisao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    dossie TEXT NOT NULL,
    alvo_chave TEXT,
    titulo TEXT NOT NULL,
    justificativa TEXT NOT NULL,
    fonte_oficial TEXT,
    autor TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS classificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    alvo_tabela TEXT NOT NULL,
    alvo_chave TEXT NOT NULL,
    categoria TEXT NOT NULL,
    valor TEXT NOT NULL,
    observacao TEXT,
    autor TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS resposta_requisito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    requisito_chave TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pendente', 'rascunho', 'revisado', 'entregue')),
    resposta_md TEXT NOT NULL,
    evidencias_chaves_json TEXT NOT NULL DEFAULT '[]',
    autor TEXT NOT NULL,
    atualizado_em TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
