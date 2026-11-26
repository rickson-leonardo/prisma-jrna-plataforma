-- Migracao 009: Campo opcional nire em erp.estabelecimento (permite registrar NIRE proprio de matriz e filiais em outra UF).
ALTER TABLE erp.estabelecimento
    ADD COLUMN IF NOT EXISTS nire TEXT;
