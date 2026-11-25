-- Migracao 004: Correcao das views de placar IABP (criterios nao avaliados = 0) e quarentena completa D1

CREATE OR REPLACE VIEW auditoria.vw_placar_conformidade AS
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
        COUNT(*) FILTER (WHERE av.nota_v1 IS NOT NULL AND COALESCE(av.nao_aplicavel, false) = false) AS itens_v1_apontados,
        COALESCE(
            AVG(COALESCE(av.nota, 0)::numeric) FILTER (WHERE COALESCE(av.nao_aplicavel, false) = false),
            0
        ) AS media_bloco
    FROM erp.empresa e
    CROSS JOIN auditoria.criterio_conformidade c
    LEFT JOIN auditoria.avaliacao_conformidade av
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
    SUM(itens_v1_apontados) AS total_itens_v1_apontados,
    COALESCE(
        ROUND(
            (SUM((media_bloco / 4.0) * bloco_peso) FILTER (WHERE itens_aplicaveis > 0)
            / NULLIF(SUM(bloco_peso) FILTER (WHERE itens_aplicaveis > 0), 0)) * 100.0,
            2
        ),
        0.00
    ) AS iabp_total,
    COALESCE(
        ROUND(
            ((SUM((media_bloco / 4.0) * bloco_peso) FILTER (WHERE itens_aplicaveis > 0)
            / NULLIF(SUM(bloco_peso) FILTER (WHERE itens_aplicaveis > 0), 0)) * 100.0) / 10.0,
            2
        ),
        0.00
    ) AS nota_estimada_10
FROM blocos
GROUP BY empresa_id, empresa_chave, nome_curto, matriz
ORDER BY empresa_chave, matriz;

CREATE OR REPLACE VIEW auditoria.vw_pendencias_quarentena AS
SELECT 'cadastro_empresa' AS modulo, chave, nome_curto AS titulo, origem_registro, status_validacao, apontamento_auditoria
FROM erp.empresa WHERE papel_no_caso = 'escritorio_contabil'
UNION ALL
SELECT 'cadastro_estabelecimento', chave, cnpj || ' - ' || COALESCE(endereco, ''), origem_registro, status_validacao, apontamento_auditoria
FROM erp.estabelecimento WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'cadastro_socios', ps.chave, p.nome_canonico || ' (' || ps.papel || ')', ps.origem_registro, ps.status_validacao, ps.apontamento_auditoria
FROM erp.participacao_societaria ps JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id
WHERE ps.empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'cadastro_pessoas', p.chave, p.nome_canonico, p.origem_registro, p.status_validacao, p.apontamento_auditoria
FROM erp.pessoa p
WHERE p.id IN (
    SELECT e.pessoa_id FROM erp.empresa e WHERE e.chave = 'emp:prisma_jrna_g07'
    UNION
    SELECT ps.socio_pessoa_id FROM erp.participacao_societaria ps
    JOIN erp.empresa e ON e.id = ps.empresa_id WHERE e.chave = 'emp:prisma_jrna_g07'
)
UNION ALL
SELECT 'cadastro_identificadores', pi.chave, p.nome_canonico || ' [' || pi.tipo_id || ': ' || pi.valor || ']', pi.origem_registro, pi.status_validacao, pi.apontamento_auditoria
FROM erp.pessoa_identificador pi
JOIN erp.pessoa p ON p.id = pi.pessoa_id
WHERE pi.pessoa_id IN (
    SELECT e.pessoa_id FROM erp.empresa e WHERE e.chave = 'emp:prisma_jrna_g07'
    UNION
    SELECT ps.socio_pessoa_id FROM erp.participacao_societaria ps
    JOIN erp.empresa e ON e.id = ps.empresa_id WHERE e.chave = 'emp:prisma_jrna_g07'
)
UNION ALL
SELECT 'cadastro_enquadramento', enq.chave, enq.porte || ' / ' || enq.cnae_principal, enq.origem_registro, enq.status_validacao, enq.apontamento_auditoria
FROM erp.enquadramento_historico enq
WHERE enq.empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'instrumentos_societarios', chave, numero_clausula || ' - ' || titulo, origem_registro, status_validacao, apontamento_auditoria
FROM erp.instrumento_societario_clausula
WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'legalizacao_df', chave, codigo || ' - ' || nome_etapa, origem_registro, status_validacao, apontamento_auditoria
FROM erp.processo_legalizacao_etapa
WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'orcamento_tributario', chave, codigo_cenario || ' - ' || nome, origem_registro, status_validacao, apontamento_auditoria
FROM erp.orcamento_cenario
WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'consultas_normativas', chave, 'Q' || numero_questao || ' - ' || LEFT(enunciado, 60), origem_registro, status_validacao, apontamento_auditoria
FROM erp.consulta_normativa
WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'decisoes_preliminares', chave, elemento || ' -> ' || opcao_adotada, origem_registro, status_validacao, apontamento_auditoria
FROM erp.empresa_decisao_preliminar
WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'conformidade_criterios', av.chave, c.matriz || ':' || c.codigo, av.origem_registro, av.status_validacao, av.critica_v1
FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id
WHERE av.empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'diario_ia', chave, COALESCE(entregavel, finalidade), origem_registro, status_validacao, revisao_humana
FROM auditoria.diario_ia
WHERE dossie = 'D1' AND empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07');
