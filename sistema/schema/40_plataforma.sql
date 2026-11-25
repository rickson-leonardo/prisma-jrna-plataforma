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
