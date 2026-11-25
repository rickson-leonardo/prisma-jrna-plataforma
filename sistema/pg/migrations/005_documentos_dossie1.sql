-- Migracao 005: Secoes narrativas editaveis dos documentos do Dossie 1 + ancora de alertas
-- Escopo estrito Dossie 1. Nao altera acervo.* nem dados D2/D3/D4.
-- Textos estrategicos (Canvas, TAM/SAM/SOM, PESTEL, Riscos, preambulos, anexos) deixam de existir
-- apenas em .md: passam a ser registros CRUD com governanca anti-enviesamento (quarentena).

CREATE TABLE IF NOT EXISTS erp.documento_secao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    documento TEXT NOT NULL CHECK (
        documento IN ('indice', 'pesquisa', 'plano_negocios', 'contrato_social', 'memorando', 'fluxo_abertura')
    ),
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    codigo_secao TEXT NOT NULL,
    titulo TEXT NOT NULL,
    conteudo_md TEXT NOT NULL DEFAULT '',
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (
        origem_registro IN ('acervo_sigaa', 'importado_v1', 'importado_rascunho_v2', 'usuario')
    ),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (
        status_validacao IN ('pendente_revisao', 'alerta_inconsistencia', 'homologado_contadora')
    ),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, documento, codigo_secao)
);

CREATE INDEX IF NOT EXISTS idx_erp_doc_secao_emp ON erp.documento_secao(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_doc_secao_doc ON erp.documento_secao(empresa_id, documento, ordem);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_erp_documento_secao_upd') THEN
        CREATE TRIGGER trg_erp_documento_secao_upd
            BEFORE UPDATE ON erp.documento_secao
            FOR EACH ROW EXECUTE FUNCTION auditoria.fn_set_atualizado_em();
    END IF;
END $$;

-- Ancora do registro que gerou o alerta (ex.: '/instrumentos#clausula-18'), usada pelo Painel
ALTER TABLE auditoria.alerta_coerencia ADD COLUMN IF NOT EXISTS ancora TEXT;

-- Quarentena passa a incluir as secoes narrativas dos documentos do Dossie 1
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
WHERE dossie = 'D1' AND empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07')
UNION ALL
SELECT 'documentos_dossie1', chave, documento || ' / ' || codigo_secao || ' - ' || titulo, origem_registro, status_validacao, apontamento_auditoria
FROM erp.documento_secao
WHERE empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07');
