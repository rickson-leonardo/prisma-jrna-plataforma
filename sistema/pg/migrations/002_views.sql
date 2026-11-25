-- Migracao 002: Visoes SQL analiticas e de auditoria estrutural (D1 a D4 + DBeaver)

CREATE OR REPLACE VIEW auditoria.vw_inventario_acervo AS
SELECT
    dossie,
    extensao,
    papel_acervo,
    COUNT(*) AS qtd_arquivos,
    SUM(tamanho_bytes) AS total_bytes,
    COALESCE(SUM(paginas_total), 0) AS total_paginas
FROM acervo.bru_arquivo
GROUP BY dossie, extensao, papel_acervo
ORDER BY dossie, papel_acervo, extensao;

CREATE OR REPLACE VIEW auditoria.vw_cobertura_bruto AS
SELECT
    'bru_linha' AS origem,
    COUNT(*) AS total,
    SUM(CASE WHEN destino IS NOT NULL THEN 1 ELSE 0 END) AS com_destino,
    SUM(CASE WHEN destino IS NULL THEN 1 ELSE 0 END) AS sem_destino
FROM acervo.bru_linha
UNION ALL
SELECT
    'bru_celula' AS origem,
    COUNT(*) AS total,
    SUM(CASE WHEN destino IS NOT NULL THEN 1 ELSE 0 END) AS com_destino,
    SUM(CASE WHEN destino IS NULL THEN 1 ELSE 0 END) AS sem_destino
FROM acervo.bru_celula
UNION ALL
SELECT
    'bru_paragrafo' AS origem,
    COUNT(*) AS total,
    SUM(CASE WHEN destino IS NOT NULL THEN 1 ELSE 0 END) AS com_destino,
    SUM(CASE WHEN destino IS NULL THEN 1 ELSE 0 END) AS sem_destino
FROM acervo.bru_paragrafo;

CREATE OR REPLACE VIEW auditoria.vw_sigaa_cobertura AS
SELECT
    status_fetch,
    COUNT(*) AS total_itens,
    SUM(CASE WHEN arquivo_id IS NOT NULL THEN 1 ELSE 0 END) AS mapeados,
    SUM(CASE WHEN arquivo_id IS NULL THEN 1 ELSE 0 END) AS nao_mapeados
FROM acervo.bru_sigaa_item
GROUP BY status_fetch;

CREATE OR REPLACE VIEW auditoria.vw_resumo_conferencia AS
SELECT
    regra,
    severidade,
    status,
    COUNT(*) AS qtd
FROM auditoria.conferencia
GROUP BY regra, severidade, status
ORDER BY severidade, regra;

CREATE OR REPLACE VIEW erp.vw_linha_do_tempo AS
SELECT
    f.sujeito_chave,
    f.vigente_de,
    f.vigente_ate,
    f.atributo,
    f.valor_texto,
    f.valor_centavos,
    e.tipo_evento,
    e.data_evento,
    f.fonte_chave,
    f.origem_registro
FROM erp.fato f
LEFT JOIN erp.evento e ON e.id = f.evento_id
ORDER BY f.sujeito_chave, f.vigente_de, f.atributo;

CREATE OR REPLACE VIEW erp.vw_ficha_documento AS
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
    (SELECT COUNT(*) FROM acervo.ext_campo c WHERE c.documento_id = d.id) AS qtd_campos,
    (SELECT COUNT(*) FROM acervo.ext_item i WHERE i.documento_id = d.id) AS qtd_itens,
    (SELECT COUNT(*) FROM acervo.ext_nota_didatica n WHERE n.documento_id = d.id) AS qtd_notas_didaticas
FROM acervo.ext_documento d
JOIN acervo.bru_arquivo a ON a.id = d.arquivo_id
ORDER BY d.data_referencia, d.modelo, d.numero;

CREATE OR REPLACE VIEW erp.vw_navegacao_doc_ref AS
SELECT
    t.chave AS transacao_chave,
    e.chave AS empresa_chave,
    t.regra_agrupamento,
    t.doc_ref,
    t.ano_mes,
    t.data_referencia,
    t.status_vinculo,
    m.tabela_membro,
    m.membro_chave,
    m.papel_membro,
    m.criterio_vinculo
FROM erp.transacao t
JOIN erp.empresa e ON e.id = t.empresa_id
JOIN erp.transacao_membro m ON m.transacao_id = t.id
ORDER BY t.data_referencia, t.chave, m.papel_membro, m.id;

CREATE OR REPLACE VIEW erp.vw_auditoria_retencoes_d3 AS
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
FROM erp.documento_fiscal df
JOIN erp.item_tributo it ON it.documento_fiscal_id = df.id
LEFT JOIN erp.pessoa pe ON pe.id = df.emitente_pessoa_id
LEFT JOIN erp.pessoa pd ON pd.id = df.destinatario_pessoa_id
WHERE df.chave = 'nrm:df:d3:nfse_2026_000184'
ORDER BY it.id;

CREATE OR REPLACE VIEW erp.vw_d4_faturamento_grupo_economico AS
SELECT
    to_char(df.data_emissao, 'YYYY-MM') AS ano_mes,
    e.chave AS empresa_chave,
    e.nome_curto AS empresa,
    COUNT(*) AS qtd_nfes,
    SUM(df.valor_total_centavos) AS faturamento_centavos
FROM erp.documento_fiscal df
JOIN erp.estabelecimento est ON est.id = df.estabelecimento_id
JOIN erp.empresa e ON e.id = est.empresa_id
WHERE df.tipo_documento = 'NFe'
GROUP BY to_char(df.data_emissao, 'YYYY-MM'), e.id, e.chave, e.nome_curto
ORDER BY ano_mes, e.chave;

CREATE OR REPLACE VIEW erp.vw_curso_devolutivas_e_requisitos AS
SELECT
    dos.codigo AS dossie,
    dos.titulo AS dossie_titulo,
    dev.grupo,
    dev.nossa_dupla,
    dev.nota_texto,
    dev.resumo,
    mat.chave AS material_chave
FROM erp.devolutiva dev
JOIN erp.dossie dos ON dos.id = dev.dossie_id
JOIN erp.material mat ON mat.id = dev.material_id
ORDER BY dos.codigo, dev.nossa_dupla DESC, dev.grupo;

CREATE OR REPLACE VIEW auditoria.vw_d1_placar_iabp AS
WITH blocos AS (
    SELECT
        e.id AS empresa_id,
        e.chave AS empresa_chave,
        e.nome_curto,
        c.matriz,
        c.bloco,
        c.bloco_peso,
        COUNT(*) FILTER (WHERE COALESCE(av.nao_aplicavel, false) = false) AS itens_aplicaveis,
        COUNT(*) FILTER (WHERE av.nota IS NOT NULL AND COALESCE(av.nao_aplicavel, false) = false) AS itens_avaliados,
        COALESCE(AVG(av.nota::numeric) FILTER (WHERE COALESCE(av.nao_aplicavel, false) = false), 0) AS media_bloco
    FROM erp.empresa e
    CROSS JOIN erp.d1_matriz_criterio c
    LEFT JOIN auditoria.avaliacao_iabp av
        ON av.empresa_id = e.id AND av.criterio_id = c.id
    WHERE e.papel_no_caso = 'escritorio_contabil'
    GROUP BY e.id, e.chave, e.nome_curto, c.matriz, c.bloco, c.bloco_peso
)
SELECT
    empresa_id,
    empresa_chave,
    nome_curto,
    matriz,
    SUM(itens_aplicaveis) AS total_itens_aplicaveis,
    SUM(itens_avaliados) AS total_itens_avaliados,
    ROUND(SUM((media_bloco / 4.0) * bloco_peso), 2) AS iabp_total,
    ROUND(SUM((media_bloco / 4.0) * bloco_peso) / 10.0, 2) AS nota_estimada_10
FROM blocos
GROUP BY empresa_id, empresa_chave, nome_curto, matriz
ORDER BY empresa_chave, matriz;

CREATE OR REPLACE VIEW auditoria.vw_pg_fks_sem_indice AS
SELECT
    n.nspname AS schema_nome,
    c.conrelid::regclass::text AS tabela,
    a.attname AS coluna_fk,
    c.conname AS constraint_nome
FROM pg_constraint c
JOIN pg_class cl ON cl.oid = c.conrelid
JOIN pg_namespace n ON n.oid = cl.relnamespace
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND n.nspname IN ('acervo', 'erp', 'auditoria')
  AND NOT EXISTS (
      SELECT 1
      FROM pg_index i
      WHERE i.indrelid = c.conrelid
        AND i.indisvalid
        AND a.attnum = ANY(i.indkey)
  )
ORDER BY n.nspname, tabela, coluna_fk;
