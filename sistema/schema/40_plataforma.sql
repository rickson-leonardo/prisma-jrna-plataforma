-- Camada 4: Visoes SQL para exploracao e plataforma (Datasette)
PRAGMA foreign_keys = ON;

CREATE VIEW IF NOT EXISTS vw_inventario_acervo AS
SELECT
    dossie,
    extensao,
    papel_acervo,
    COUNT(*) AS qtd_arquivos,
    SUM(tamanho_bytes) AS total_bytes,
    COALESCE(SUM(paginas_total), 0) AS total_paginas
FROM bru_arquivo
GROUP BY dossie, extensao, papel_acervo
ORDER BY dossie, papel_acervo, extensao;

CREATE VIEW IF NOT EXISTS vw_cobertura_bruto AS
SELECT
    'bru_linha' AS origem,
    COUNT(*) AS total,
    SUM(CASE WHEN destino IS NOT NULL THEN 1 ELSE 0 END) AS com_destino,
    SUM(CASE WHEN destino IS NULL THEN 1 ELSE 0 END) AS sem_destino
FROM bru_linha
UNION ALL
SELECT
    'bru_celula' AS origem,
    COUNT(*) AS total,
    SUM(CASE WHEN destino IS NOT NULL THEN 1 ELSE 0 END) AS com_destino,
    SUM(CASE WHEN destino IS NULL THEN 1 ELSE 0 END) AS sem_destino
FROM bru_celula
UNION ALL
SELECT
    'bru_paragrafo' AS origem,
    COUNT(*) AS total,
    SUM(CASE WHEN destino IS NOT NULL THEN 1 ELSE 0 END) AS com_destino,
    SUM(CASE WHEN destino IS NULL THEN 1 ELSE 0 END) AS sem_destino
FROM bru_paragrafo;

CREATE VIEW IF NOT EXISTS vw_sigaa_cobertura AS
SELECT
    status_fetch,
    COUNT(*) AS total_itens,
    SUM(CASE WHEN arquivo_id IS NOT NULL THEN 1 ELSE 0 END) AS mapeados,
    SUM(CASE WHEN arquivo_id IS NULL THEN 1 ELSE 0 END) AS nao_mapeados
FROM bru_sigaa_item
GROUP BY status_fetch;

CREATE VIEW IF NOT EXISTS vw_linha_do_tempo AS
SELECT
    f.sujeito_chave,
    f.vigente_de,
    f.vigente_ate,
    f.atributo,
    f.valor_texto,
    f.valor_centavos,
    e.tipo_evento,
    e.data_evento,
    f.fonte_chave
FROM nrm_fato f
LEFT JOIN nrm_evento e ON e.id = f.evento_id
ORDER BY f.sujeito_chave, f.vigente_de, f.atributo;

CREATE VIEW IF NOT EXISTS vw_situacao_em AS
SELECT
    f.sujeito_chave,
    f.atributo,
    f.valor_texto,
    f.valor_centavos,
    f.vigente_de,
    f.vigente_ate,
    f.fonte_chave
FROM nrm_fato f;

CREATE VIEW IF NOT EXISTS vw_resumo_conferencia AS
SELECT
    regra,
    severidade,
    status,
    COUNT(*) AS qtd
FROM conferencia
GROUP BY regra, severidade, status
ORDER BY severidade, regra;

CREATE VIEW IF NOT EXISTS vw_ficha_documento AS
SELECT
    d.chave AS doc_chave,
    a.caminho_relativo,
    d.modelo,
    d.tipo,
    d.numero,
    d.data_emissao,
    d.data_referencia,
    d.doc_ref,
    d.estabelecimento_prefixo,
    d.valor_total_centavos,
    d.moeda,
    (SELECT COUNT(*) FROM ext_campo c WHERE c.documento_id = d.id) AS qtd_campos,
    (SELECT COUNT(*) FROM ext_item i WHERE i.documento_id = d.id) AS qtd_itens,
    (SELECT COUNT(*) FROM ext_nota_didatica n WHERE n.documento_id = d.id) AS qtd_notas_didaticas
FROM ext_documento d
JOIN bru_arquivo a ON a.id = d.arquivo_id
ORDER BY d.data_referencia, d.modelo, d.numero;

CREATE VIEW IF NOT EXISTS vw_navegacao_doc_ref AS
SELECT
    t.chave AS transacao_chave,
    t.regra_agrupamento,
    t.doc_ref,
    t.ano_mes,
    t.data_referencia,
    t.status_vinculo,
    m.tabela_membro,
    m.membro_chave,
    m.papel_membro,
    m.criterio_vinculo
FROM nrm_transacao t
JOIN nrm_transacao_membro m ON m.transacao_id = t.id
ORDER BY t.data_referencia, t.chave, m.papel_membro, m.id;

CREATE VIEW IF NOT EXISTS vw_auditoria_retencoes_d3 AS
SELECT
    df.chave AS documento_chave,
    df.numero,
    df.data_emissao,
    pe.nome_canonico AS prestador,
    pd.nome_canonico AS tomador,
    df.valor_total_centavos,
    it.tributo,
    it.base_centavos,
    it.aliquota_texto,
    it.valor_centavos
FROM nrm_documento_fiscal df
JOIN nrm_item_tributo it ON it.documento_fiscal_id = df.id
LEFT JOIN nrm_pessoa pe ON pe.id = df.emitente_pessoa_id
LEFT JOIN nrm_pessoa pd ON pd.id = df.destinatario_pessoa_id
WHERE df.chave = 'nrm:df:d3:nfse_2026_000184'
ORDER BY it.id;

CREATE VIEW IF NOT EXISTS vw_d4_faturamento_grupo_economico AS
SELECT
    substr(df.data_emissao, 1, 7) AS ano_mes,
    e.chave AS empresa_chave,
    e.nome_curto AS empresa,
    COUNT(*) AS qtd_nfes,
    SUM(df.valor_total_centavos) AS faturamento_centavos
FROM nrm_documento_fiscal df
JOIN nrm_estabelecimento est ON est.id = df.estabelecimento_id
JOIN nrm_empresa e ON e.id = est.empresa_id
WHERE df.tipo_documento = 'NFe'
GROUP BY substr(df.data_emissao, 1, 7), e.id
ORDER BY ano_mes, e.chave;

CREATE VIEW IF NOT EXISTS vw_curso_devolutivas_e_requisitos AS
SELECT
    dos.codigo AS dossie,
    dos.titulo AS dossie_titulo,
    dev.grupo,
    dev.nossa_dupla,
    dev.nota_texto,
    dev.resumo,
    mat.chave AS material_chave
FROM nrm_devolutiva dev
JOIN nrm_dossie dos ON dos.id = dev.dossie_id
JOIN nrm_material mat ON mat.id = dev.material_id
ORDER BY dos.codigo, dev.nossa_dupla DESC, dev.grupo;
