-- Migracao 010: Doc 16 do Dossie 2 (rastreabilidade das correcoes) passa a ser documento valido em erp.documento_secao.
ALTER TABLE erp.documento_secao DROP CONSTRAINT IF EXISTS documento_secao_documento_check;
ALTER TABLE erp.documento_secao ADD CONSTRAINT documento_secao_documento_check CHECK (
    documento IN (
        'indice', 'pesquisa', 'plano_negocios', 'contrato_social', 'memorando', 'fluxo_abertura',
        'd2_00_indice', 'd2_01_diagnostico', 'd2_02_proposta', 'd2_03_contrato',
        'd2_04_termo_rt', 'd2_05_onboarding', 'd2_06_prontuario', 'd2_07_ficha_e1',
        'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2', 'd2_11_folha',
        'd2_12_resumo_contab', 'd2_13_auditoria', 'd2_14_premissas', 'd2_15_ia',
        'd2_16_rastreabilidade'
    )
);
