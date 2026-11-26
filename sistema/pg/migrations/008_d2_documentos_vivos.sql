-- Migracao 008: Colunas opcionais para os quadros vivos do Dossie 2 (P1 — Diagnostico Societario e P8 — Premissas)
-- Idempotente, sem alterar CHECKs existentes e sem popular dados (preenchimento pela contadora na plataforma).

ALTER TABLE erp.instrumento_societario_clausula
    ADD COLUMN IF NOT EXISTS risco_tipo TEXT,
    ADD COLUMN IF NOT EXISTS risco_nivel TEXT,
    ADD COLUMN IF NOT EXISTS providencia TEXT,
    ADD COLUMN IF NOT EXISTS fundamento_legal TEXT,
    ADD COLUMN IF NOT EXISTS responsavel TEXT,
    ADD COLUMN IF NOT EXISTS prazo_texto TEXT;

ALTER TABLE erp.consulta_normativa
    ADD COLUMN IF NOT EXISTS responsavel_decisao TEXT,
    ADD COLUMN IF NOT EXISTS prazo_decisao TEXT,
    ADD COLUMN IF NOT EXISTS impacto_se_alterada TEXT;
