-- Migracao 006: Suporte multi-dossie (D1/D2) + 8 tabelas do ERP para Onboarding, DP, Folha e Auditoria
-- Escopo: Parte A (ajustes em tabelas/views existentes) + Parte B (8 tabelas novas com indices em todas as FKs e governanca).

-- =============================================================================
-- PARTE A — AJUSTES EM TABELAS EXISTENTES
-- =============================================================================

ALTER TABLE erp.dossie ADD COLUMN IF NOT EXISTS empresa_id BIGINT REFERENCES erp.empresa(id);
ALTER TABLE erp.dossie ADD COLUMN IF NOT EXISTS competencia TEXT;
ALTER TABLE erp.dossie ADD COLUMN IF NOT EXISTS prazo_entrega DATE;
ALTER TABLE erp.dossie ADD COLUMN IF NOT EXISTS peso_micro INTEGER;
CREATE INDEX IF NOT EXISTS idx_erp_dossie_empresa ON erp.dossie(empresa_id);

UPDATE erp.dossie
SET empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07'),
    competencia = COALESCE(competencia, '2026-09')
WHERE codigo = 'D1';

UPDATE erp.dossie
SET empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:rota_sul_d2'),
    competencia = COALESCE(competencia, '2026-09')
WHERE codigo = 'D2';

ALTER TABLE erp.requisito ADD COLUMN IF NOT EXISTS ordem INTEGER;
ALTER TABLE erp.requisito ADD COLUMN IF NOT EXISTS documentos_json JSONB;

-- Segmentacao por dossie na Sustentacao e documentos
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'erp.consulta_normativa',
        'erp.empresa_decisao_preliminar',
        'erp.documento_secao',
        'auditoria.alerta_coerencia',
        'auditoria.criterio_conformidade',
        'auditoria.avaliacao_conformidade'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS dossie TEXT NOT NULL DEFAULT ''D1''', t);
    END LOOP;
END $$;

ALTER TABLE erp.consulta_normativa DROP CONSTRAINT IF EXISTS consulta_normativa_dossie_check;
ALTER TABLE erp.consulta_normativa ADD CONSTRAINT consulta_normativa_dossie_check CHECK (dossie IN ('D1','D2','D3','D4'));

ALTER TABLE erp.empresa_decisao_preliminar DROP CONSTRAINT IF EXISTS empresa_decisao_preliminar_dossie_check;
ALTER TABLE erp.empresa_decisao_preliminar ADD CONSTRAINT empresa_decisao_preliminar_dossie_check CHECK (dossie IN ('D1','D2','D3','D4'));

ALTER TABLE erp.documento_secao DROP CONSTRAINT IF EXISTS documento_secao_dossie_check;
ALTER TABLE erp.documento_secao ADD CONSTRAINT documento_secao_dossie_check CHECK (dossie IN ('D1','D2','D3','D4'));

ALTER TABLE auditoria.alerta_coerencia DROP CONSTRAINT IF EXISTS alerta_coerencia_dossie_check;
ALTER TABLE auditoria.alerta_coerencia ADD CONSTRAINT alerta_coerencia_dossie_check CHECK (dossie IN ('D1','D2','D3','D4'));

ALTER TABLE auditoria.criterio_conformidade DROP CONSTRAINT IF EXISTS criterio_conformidade_dossie_check;
ALTER TABLE auditoria.criterio_conformidade ADD CONSTRAINT criterio_conformidade_dossie_check CHECK (dossie IN ('D1','D2','D3','D4'));

ALTER TABLE auditoria.avaliacao_conformidade DROP CONSTRAINT IF EXISTS avaliacao_conformidade_dossie_check;
ALTER TABLE auditoria.avaliacao_conformidade ADD CONSTRAINT avaliacao_conformidade_dossie_check CHECK (dossie IN ('D1','D2','D3','D4'));

-- Ampliar CHECKs de documento, matriz e origem_registro
ALTER TABLE erp.documento_secao DROP CONSTRAINT IF EXISTS documento_secao_documento_check;
ALTER TABLE erp.documento_secao ADD CONSTRAINT documento_secao_documento_check CHECK (
    documento IN (
        'indice', 'pesquisa', 'plano_negocios', 'contrato_social', 'memorando', 'fluxo_abertura',
        'd2_00_indice', 'd2_01_diagnostico', 'd2_02_proposta', 'd2_03_contrato',
        'd2_04_termo_rt', 'd2_05_onboarding', 'd2_06_prontuario', 'd2_07_ficha_e1',
        'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2', 'd2_11_folha',
        'd2_12_resumo_contab', 'd2_13_auditoria', 'd2_14_premissas', 'd2_15_ia'
    )
);

ALTER TABLE auditoria.criterio_conformidade DROP CONSTRAINT IF EXISTS d1_matriz_criterio_matriz_check;
ALTER TABLE auditoria.criterio_conformidade ADD CONSTRAINT d1_matriz_criterio_matriz_check CHECK (
    matriz IN (
        'plano_negocios', 'contrato_social', 'memorando', 'fluxo_abertura',
        'd2_p1', 'd2_p2', 'd2_p3', 'd2_p4', 'd2_p5', 'd2_p6', 'd2_p7', 'd2_p8', 'd2_p9'
    )
);

ALTER TABLE erp.instrumento_societario_clausula
    ADD COLUMN IF NOT EXISTS tipo_instrumento TEXT NOT NULL DEFAULT 'contrato_mou'
    CHECK (tipo_instrumento IN ('contrato_mou', '2a_alteracao', '3a_alteracao'));

-- Origem motor_calculo e governanca em lancamento/guia/conta_contabil
ALTER TABLE erp.lancamento DROP CONSTRAINT IF EXISTS lancamento_origem_registro_check;
ALTER TABLE erp.lancamento ADD CONSTRAINT lancamento_origem_registro_check CHECK (
    origem_registro IN ('acervo_sigaa', 'importado_v1', 'importado_rascunho_v2', 'usuario', 'motor_calculo')
);
ALTER TABLE erp.lancamento ADD COLUMN IF NOT EXISTS status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao'
    CHECK (status_validacao IN ('acervo_referencia', 'pendente_revisao', 'alerta_inconsistencia', 'homologado_contadora'));
ALTER TABLE erp.lancamento ADD COLUMN IF NOT EXISTS referencia_v1_original TEXT;
ALTER TABLE erp.lancamento ADD COLUMN IF NOT EXISTS apontamento_auditoria TEXT;
ALTER TABLE erp.lancamento ADD COLUMN IF NOT EXISTS justificativa_contadora TEXT;
UPDATE erp.lancamento SET origem_registro = 'acervo_sigaa' WHERE origem_registro IS NULL OR origem_registro = '';

ALTER TABLE erp.conta_contabil ADD COLUMN IF NOT EXISTS empresa_id BIGINT REFERENCES erp.empresa(id);
CREATE INDEX IF NOT EXISTS idx_erp_conta_contabil_empresa ON erp.conta_contabil(empresa_id);
UPDATE erp.conta_contabil
SET empresa_id = (SELECT id FROM erp.empresa WHERE chave = 'emp:rota_sul_d4')
WHERE empresa_id IS NULL;

ALTER TABLE erp.guia ADD COLUMN IF NOT EXISTS origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa'
    CHECK (origem_registro IN ('acervo_sigaa', 'importado_v1', 'importado_rascunho_v2', 'usuario', 'motor_calculo'));
ALTER TABLE erp.guia ADD COLUMN IF NOT EXISTS status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao'
    CHECK (status_validacao IN ('acervo_referencia', 'pendente_revisao', 'alerta_inconsistencia', 'homologado_contadora'));
ALTER TABLE erp.guia ADD COLUMN IF NOT EXISTS referencia_v1_original TEXT;
ALTER TABLE erp.guia ADD COLUMN IF NOT EXISTS apontamento_auditoria TEXT;
ALTER TABLE erp.guia ADD COLUMN IF NOT EXISTS justificativa_contadora TEXT;

-- =============================================================================
-- PARTE B — 8 TABELAS NOVAS DO ERP (DOMINIO CONTABIL, DP, FOLHA E AUDITORIA)
-- =============================================================================

CREATE TABLE IF NOT EXISTS erp.contrato_servico (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    relacao_id BIGINT REFERENCES erp.relacao_escritorio_cliente(id),
    codigo_documento TEXT NOT NULL CHECK (codigo_documento IN ('proposta', 'contrato', 'termo_rt', 'procuracao')),
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    titulo TEXT NOT NULL,
    honorario_mensal_centavos BIGINT NOT NULL DEFAULT 0,
    tem_decimo_terceiro BOOLEAN NOT NULL DEFAULT true,
    valor_hora_centavos BIGINT NOT NULL DEFAULT 0,
    horas_mes_estimadas INTEGER NOT NULL DEFAULT 0,
    memoria_horas_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    vigencia_inicio DATE,
    foro TEXT,
    escopo_resumo TEXT NOT NULL DEFAULT '',
    conteudo_md TEXT NOT NULL DEFAULT '',
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erp_contrato_servico_emp ON erp.contrato_servico(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_contrato_servico_rel ON erp.contrato_servico(relacao_id);

CREATE TABLE IF NOT EXISTS erp.diligencia_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('pergunta', 'documento', 'pendencia')),
    codigo TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    ator TEXT NOT NULL CHECK (ator IN ('cliente', 'contador_anterior', 'advogado', 'escritorio')),
    tema TEXT NOT NULL DEFAULT '',
    enunciado TEXT NOT NULL,
    resposta_literal TEXT,
    fonte_evidencia TEXT,
    data_interacao DATE,
    responsavel TEXT,
    prazo_texto TEXT,
    risco TEXT,
    status_item TEXT NOT NULL DEFAULT 'pendente_critico' CHECK (status_item IN ('concluido', 'pendente_critico', 'em_saneamento', 'sem_resposta')),
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erp_diligencia_emp ON erp.diligencia_item(empresa_id);

CREATE TABLE IF NOT EXISTS erp.parametro_legal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT REFERENCES erp.empresa(id),
    vigencia TEXT NOT NULL DEFAULT '2026',
    categoria TEXT NOT NULL CHECK (categoria IN ('inss', 'irrf', 'reducao_irrf_2026', 'salario_familia', 'fgts', 'cct_clausula')),
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    limite_centavos BIGINT,
    aliquota_micro INTEGER,
    deducao_centavos BIGINT,
    valor_centavos BIGINT,
    norma_citada TEXT NOT NULL DEFAULT '',
    link_oficial TEXT,
    data_consulta DATE,
    regra_texto TEXT NOT NULL DEFAULT '',
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erp_parametro_legal_emp ON erp.parametro_legal(empresa_id);

CREATE TABLE IF NOT EXISTS erp.contrato_trabalho (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    codigo_empregado TEXT NOT NULL,
    nome_empregado TEXT NOT NULL,
    cpf_ficticio TEXT,
    cargo TEXT NOT NULL,
    departamento TEXT NOT NULL DEFAULT 'administrativo' CHECK (departamento IN ('administrativo', 'comercial')),
    cbo TEXT NOT NULL,
    data_admissao DATE NOT NULL,
    experiencia_dias_1 INTEGER NOT NULL DEFAULT 45,
    experiencia_dias_2 INTEGER NOT NULL DEFAULT 45,
    salario_base_centavos BIGINT NOT NULL,
    piso_cct_centavos BIGINT NOT NULL DEFAULT 0,
    comissao_pct_micro INTEGER NOT NULL DEFAULT 0,
    jornada_semanal_horas INTEGER NOT NULL DEFAULT 44,
    jornada_descricao TEXT NOT NULL DEFAULT '',
    intervalo_minutos INTEGER NOT NULL DEFAULT 60,
    cct_referencia TEXT NOT NULL DEFAULT '',
    vt_optante BOOLEAN NOT NULL DEFAULT true,
    vt_passagens_dia INTEGER NOT NULL DEFAULT 2,
    vt_tarifa_centavos BIGINT NOT NULL DEFAULT 430,
    vr_elegivel BOOLEAN NOT NULL DEFAULT false,
    vr_valor_dia_centavos BIGINT NOT NULL DEFAULT 3000,
    aso_status TEXT NOT NULL DEFAULT 'pendente_critico' CHECK (aso_status IN ('pendente_critico', 'apto', 'dispensado')),
    aso_observacao TEXT NOT NULL DEFAULT '',
    qtd_dependentes_ir INTEGER NOT NULL DEFAULT 0,
    qtd_dependentes_sf INTEGER NOT NULL DEFAULT 0,
    dependentes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    docs_admissionais_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erp_contrato_trabalho_emp ON erp.contrato_trabalho(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_contrato_trabalho_est ON erp.contrato_trabalho(estabelecimento_id);

CREATE TABLE IF NOT EXISTS erp.esocial_evento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    contrato_trabalho_id BIGINT REFERENCES erp.contrato_trabalho(id) ON DELETE SET NULL,
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    codigo_evento TEXT NOT NULL,
    nome_evento TEXT NOT NULL,
    competencia TEXT NOT NULL DEFAULT '2026-09',
    prazo_legal TEXT NOT NULL DEFAULT '',
    status_envio TEXT NOT NULL DEFAULT 'aguardando_insumo' CHECK (status_envio IN ('pendente','aguardando_insumo','pronto_envio','transmitido','dispensado')),
    numero_recibo TEXT,
    observacao TEXT NOT NULL DEFAULT '',
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (numero_recibo IS NULL OR numero_recibo = '' OR status_envio = 'transmitido')
);
CREATE INDEX IF NOT EXISTS idx_erp_esocial_emp ON erp.esocial_evento(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_esocial_ct ON erp.esocial_evento(contrato_trabalho_id);

CREATE TABLE IF NOT EXISTS erp.folha_competencia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    competencia TEXT NOT NULL DEFAULT '2026-09',
    status_folha TEXT NOT NULL DEFAULT 'aberta' CHECK (status_folha IN ('aberta', 'calculada', 'homologada')),
    vendas_liquidas_e2_centavos BIGINT NOT NULL DEFAULT 6000000,
    dias_mes_padrao INTEGER NOT NULL DEFAULT 30,
    dias_trabalhados_e1 INTEGER NOT NULL DEFAULT 15,
    dias_trabalhados_e2 INTEGER NOT NULL DEFAULT 10,
    dias_uteis_comissao_e2 INTEGER NOT NULL DEFAULT 9,
    domingos_feriados_e2 INTEGER NOT NULL DEFAULT 1,
    dias_uteis_vt_e1 INTEGER NOT NULL DEFAULT 11,
    dias_uteis_vt_e2 INTEGER NOT NULL DEFAULT 9,
    dias_uteis_vr_e1 INTEGER NOT NULL DEFAULT 11,
    cenario_negocial TEXT NOT NULL DEFAULT 'A_desconta' CHECK (cenario_negocial IN ('A_desconta', 'B_patronal')),
    data_pagamento DATE,
    bruto_total_centavos BIGINT NOT NULL DEFAULT 0,
    inss_total_centavos BIGINT NOT NULL DEFAULT 0,
    fgts_total_centavos BIGINT NOT NULL DEFAULT 0,
    liquido_total_centavos BIGINT NOT NULL DEFAULT 0,
    provisoes_total_centavos BIGINT NOT NULL DEFAULT 0,
    custo_total_centavos BIGINT NOT NULL DEFAULT 0,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, competencia)
);
CREATE INDEX IF NOT EXISTS idx_erp_folha_comp_emp ON erp.folha_competencia(empresa_id);

CREATE TABLE IF NOT EXISTS erp.folha_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    competencia_id BIGINT NOT NULL REFERENCES erp.folha_competencia(id) ON DELETE CASCADE,
    contrato_trabalho_id BIGINT NOT NULL REFERENCES erp.contrato_trabalho(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    codigo_rubrica TEXT NOT NULL,
    nome_rubrica TEXT NOT NULL,
    tipo_rubrica TEXT NOT NULL CHECK (tipo_rubrica IN ('provento', 'desconto', 'encargo', 'provisao', 'informativo')),
    referencia_texto TEXT NOT NULL DEFAULT '',
    base_centavos BIGINT NOT NULL DEFAULT 0,
    valor_centavos BIGINT NOT NULL DEFAULT 0,
    formula_texto TEXT NOT NULL DEFAULT '',
    fonte_normativa TEXT NOT NULL DEFAULT '',
    incide_inss BOOLEAN NOT NULL DEFAULT false,
    incide_irrf BOOLEAN NOT NULL DEFAULT false,
    incide_fgts BOOLEAN NOT NULL DEFAULT false,
    origem_registro TEXT NOT NULL DEFAULT 'motor_calculo' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erp_folha_item_comp ON erp.folha_item(competencia_id);
CREATE INDEX IF NOT EXISTS idx_erp_folha_item_ct ON erp.folha_item(contrato_trabalho_id);

CREATE TABLE IF NOT EXISTS erp.auditoria_folha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    tipo_registro TEXT NOT NULL CHECK (tipo_registro IN ('papel_trabalho', 'achado')),
    codigo TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    titulo TEXT NOT NULL,
    norma_referencia TEXT NOT NULL DEFAULT '',
    objetivo_ou_evidencia TEXT NOT NULL DEFAULT '',
    procedimento_ou_risco TEXT NOT NULL DEFAULT '',
    valor_v1_centavos BIGINT,
    valor_recalculado_centavos BIGINT,
    conclusao_ou_correcao TEXT NOT NULL DEFAULT '',
    responsavel TEXT,
    prazo_texto TEXT,
    situacao_achado TEXT NOT NULL DEFAULT 'aberto_cliente' CHECK (situacao_achado IN ('saneado_v2', 'aberto_cliente', 'conforme')),
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa','importado_v1','importado_rascunho_v2','usuario','motor_calculo')),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (status_validacao IN ('pendente_revisao','alerta_inconsistencia','homologado_contadora')),
    referencia_v1_original TEXT,
    apontamento_auditoria TEXT,
    justificativa_contadora TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erp_auditoria_folha_emp ON erp.auditoria_folha(empresa_id);

-- Triggers atualizado_em para as 8 tabelas novas
DO $$
DECLARE
    tbl TEXT;
    trg TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'erp.contrato_servico',
        'erp.diligencia_item',
        'erp.parametro_legal',
        'erp.contrato_trabalho',
        'erp.esocial_evento',
        'erp.folha_competencia',
        'erp.folha_item',
        'erp.auditoria_folha'
    ]
    LOOP
        trg := 'trg_' || replace(tbl, '.', '_') || '_upd';
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = trg) THEN
            EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION auditoria.fn_set_atualizado_em()', trg, tbl);
        END IF;
    END LOOP;
END $$;

-- =============================================================================
-- VIEWS MULTI-DOSSIE (novas colunas adicionadas AO FINAL para manter contrato CREATE OR REPLACE)
-- =============================================================================

CREATE OR REPLACE VIEW auditoria.vw_placar_conformidade AS
WITH blocos AS (
    SELECT
        e.id AS empresa_id,
        e.chave AS empresa_chave,
        e.nome_curto,
        c.matriz,
        c.dossie,
        c.bloco,
        c.bloco_peso,
        COUNT(*) FILTER (WHERE COALESCE(av.nao_aplicavel, false) = false) AS itens_aplicaveis,
        COUNT(*) FILTER (WHERE av.nota IS NOT NULL AND COALESCE(av.nao_aplicavel, false) = false) AS itens_avaliados,
        COUNT(*) FILTER (WHERE av.nota_v1 IS NOT NULL AND COALESCE(av.nao_aplicavel, false) = false) AS itens_v1_apontados,
        COALESCE(
            AVG(COALESCE(av.nota, 0)::numeric) FILTER (WHERE COALESCE(av.nao_aplicavel, false) = false),
            0
        ) AS media_bloco
    FROM erp.dossie ds
    JOIN erp.empresa e ON e.id = ds.empresa_id
    JOIN auditoria.criterio_conformidade c ON c.dossie = ds.codigo
    LEFT JOIN auditoria.avaliacao_conformidade av
        ON av.empresa_id = e.id AND av.criterio_id = c.id
    WHERE ds.codigo IN ('D1', 'D2')
    GROUP BY e.id, e.chave, e.nome_curto, c.matriz, c.dossie, c.bloco, c.bloco_peso
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
    ) AS nota_estimada_10,
    dossie
FROM blocos
GROUP BY empresa_id, empresa_chave, nome_curto, matriz, dossie
ORDER BY dossie, empresa_chave, matriz;

CREATE OR REPLACE VIEW auditoria.vw_pendencias_quarentena AS
-- Empresa + Estabelecimentos + Socios + Pessoas + Identificadores + Enquadramento (por dossie vinculado)
SELECT 'cadastro_empresa' AS modulo, e.chave, e.nome_curto AS titulo, e.origem_registro, e.status_validacao, e.apontamento_auditoria, ds.codigo AS dossie, e.id AS empresa_id
FROM erp.dossie ds JOIN erp.empresa e ON e.id = ds.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'cadastro_estabelecimento', es.chave, es.cnpj || ' - ' || COALESCE(es.endereco, ''), es.origem_registro, es.status_validacao, es.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.estabelecimento es JOIN erp.dossie ds ON ds.empresa_id = es.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'cadastro_socios', ps.chave, p.nome_canonico || ' (' || ps.papel || ')', ps.origem_registro, ps.status_validacao, ps.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.participacao_societaria ps JOIN erp.pessoa p ON p.id = ps.socio_pessoa_id JOIN erp.dossie ds ON ds.empresa_id = ps.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'cadastro_pessoas', p.chave, p.nome_canonico, p.origem_registro, p.status_validacao, p.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.dossie ds
JOIN erp.empresa e ON e.id = ds.empresa_id
JOIN erp.pessoa p ON p.id = e.pessoa_id OR p.id IN (SELECT ps.socio_pessoa_id FROM erp.participacao_societaria ps WHERE ps.empresa_id = e.id)
WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'cadastro_identificadores', pi.chave, p.nome_canonico || ' [' || pi.tipo_id || ': ' || pi.valor || ']', pi.origem_registro, pi.status_validacao, pi.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.dossie ds
JOIN erp.empresa e ON e.id = ds.empresa_id
JOIN erp.pessoa_identificador pi ON pi.pessoa_id = e.pessoa_id OR pi.pessoa_id IN (SELECT ps.socio_pessoa_id FROM erp.participacao_societaria ps WHERE ps.empresa_id = e.id)
JOIN erp.pessoa p ON p.id = pi.pessoa_id
WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'cadastro_enquadramento', enq.chave, enq.porte || ' / ' || enq.cnae_principal, enq.origem_registro, enq.status_validacao, enq.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.enquadramento_historico enq JOIN erp.dossie ds ON ds.empresa_id = enq.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'instrumentos_societarios', cl.chave, cl.numero_clausula || ' - ' || cl.titulo, cl.origem_registro, cl.status_validacao, cl.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.instrumento_societario_clausula cl JOIN erp.dossie ds ON ds.empresa_id = cl.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'legalizacao_df', le.chave, le.codigo || ' - ' || le.nome_etapa, le.origem_registro, le.status_validacao, le.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.processo_legalizacao_etapa le JOIN erp.dossie ds ON ds.empresa_id = le.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'orcamento_tributario', oc.chave, oc.codigo_cenario || ' - ' || oc.nome, oc.origem_registro, oc.status_validacao, oc.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.orcamento_cenario oc JOIN erp.dossie ds ON ds.empresa_id = oc.empresa_id WHERE ds.codigo IN ('D1','D2')
UNION ALL
SELECT 'consultas_normativas', cn.chave, 'Q' || cn.numero_questao || ' - ' || LEFT(cn.enunciado, 60), cn.origem_registro, cn.status_validacao, cn.apontamento_auditoria, cn.dossie, cn.empresa_id
FROM erp.consulta_normativa cn
UNION ALL
SELECT 'decisoes_preliminares', dp.chave, dp.elemento || ' -> ' || dp.opcao_adotada, dp.origem_registro, dp.status_validacao, dp.apontamento_auditoria, dp.dossie, dp.empresa_id
FROM erp.empresa_decisao_preliminar dp
UNION ALL
SELECT 'conformidade_criterios', av.chave, c.matriz || ':' || c.codigo, av.origem_registro, av.status_validacao, av.critica_v1, c.dossie, av.empresa_id
FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id
UNION ALL
SELECT 'diario_ia', ia.chave, COALESCE(ia.entregavel, ia.finalidade), ia.origem_registro, ia.status_validacao, ia.revisao_humana, ia.dossie, ia.empresa_id
FROM auditoria.diario_ia ia WHERE ia.dossie IN ('D1','D2')
UNION ALL
SELECT 'documentos_dossie1', sec.chave, sec.documento || ' / ' || sec.codigo_secao || ' - ' || sec.titulo, sec.origem_registro, sec.status_validacao, sec.apontamento_auditoria, sec.dossie, sec.empresa_id
FROM erp.documento_secao sec
UNION ALL
-- Novas tabelas D2 (Onboarding, DP, Folha e Auditoria)
SELECT 'contratos_servico', cs.chave, cs.codigo_documento || ' - ' || cs.titulo, cs.origem_registro, cs.status_validacao, cs.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.contrato_servico cs JOIN erp.dossie ds ON ds.empresa_id = cs.empresa_id WHERE ds.codigo = 'D2'
UNION ALL
SELECT 'diligencia_onboarding', dl.chave, dl.codigo || ' - ' || LEFT(dl.enunciado, 60), dl.origem_registro, dl.status_validacao, dl.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.diligencia_item dl JOIN erp.dossie ds ON ds.empresa_id = dl.empresa_id WHERE ds.codigo = 'D2'
UNION ALL
SELECT 'dp_contratos', ct.chave, ct.codigo_empregado || ' - ' || ct.nome_empregado, ct.origem_registro, ct.status_validacao, ct.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.contrato_trabalho ct JOIN erp.dossie ds ON ds.empresa_id = ct.empresa_id WHERE ds.codigo = 'D2'
UNION ALL
SELECT 'dp_esocial', es.chave, es.codigo_evento || ' - ' || es.nome_evento, es.origem_registro, es.status_validacao, es.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.esocial_evento es JOIN erp.dossie ds ON ds.empresa_id = es.empresa_id WHERE ds.codigo = 'D2'
UNION ALL
SELECT 'dp_parametros', pl.chave, pl.categoria || ' - ' || pl.codigo, pl.origem_registro, pl.status_validacao, pl.apontamento_auditoria, 'D2', pl.empresa_id
FROM erp.parametro_legal pl WHERE pl.empresa_id IS NOT NULL
UNION ALL
SELECT 'folha_pagamento', fc.chave, 'Folha ' || fc.competencia || ' (' || fc.cenario_negocial || ')', fc.origem_registro, fc.status_validacao, fc.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.folha_competencia fc JOIN erp.dossie ds ON ds.empresa_id = fc.empresa_id WHERE ds.codigo = 'D2'
UNION ALL
SELECT 'auditoria_trabalhista', af.chave, af.codigo || ' - ' || af.titulo, af.origem_registro, af.status_validacao, af.apontamento_auditoria, ds.codigo, ds.empresa_id
FROM erp.auditoria_folha af JOIN erp.dossie ds ON ds.empresa_id = af.empresa_id WHERE ds.codigo = 'D2';
