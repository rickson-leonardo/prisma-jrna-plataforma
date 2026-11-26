-- Cenarios de referencia (comparativos, nao oficiais) podem ficar fora da quarentena como 'acervo_referencia',
-- como ja ocorre nas demais tabelas do ERP. Idempotente.
ALTER TABLE erp.orcamento_cenario DROP CONSTRAINT IF EXISTS orcamento_cenario_status_validacao_check;
ALTER TABLE erp.orcamento_cenario ADD CONSTRAINT orcamento_cenario_status_validacao_check
    CHECK (status_validacao IN ('acervo_referencia', 'pendente_revisao', 'alerta_inconsistencia', 'homologado_contadora'));
