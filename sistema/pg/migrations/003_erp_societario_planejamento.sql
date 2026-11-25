-- Migracao 003: Refatoracao Semantica ERP Contabil Real + Governanca Anti-Enviesamento (Etapa 1 — Dossie 1)
-- Preserva 100% de acervo.* e dados D2/D3/D4 intactos; substitui tabelas d1_* por entidades de dominio ERP.

-- =============================================================================
-- 1. TRANSICAO SEGURA DAS TABELAS d1_* E avaliacao_iabp
-- =============================================================================
DROP VIEW IF EXISTS auditoria.vw_d1_placar_iabp;
DROP TABLE IF EXISTS auditoria.avaliacao_iabp;
DROP TABLE IF EXISTS erp.d1_plano_projecao_mensal;
DROP TABLE IF EXISTS erp.d1_plano_cenario;
DROP TABLE IF EXISTS erp.d1_clausula_societaria;
DROP TABLE IF EXISTS erp.d1_fluxo_etapa;
DROP TABLE IF EXISTS erp.d1_pesquisa_resposta;

DO $$
BEGIN
    IF to_regclass('erp.d1_matriz_criterio') IS NOT NULL
       AND to_regclass('auditoria.criterio_conformidade') IS NULL THEN
        ALTER TABLE erp.d1_matriz_criterio SET SCHEMA auditoria;
        ALTER TABLE auditoria.d1_matriz_criterio RENAME TO criterio_conformidade;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS auditoria.criterio_conformidade (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    matriz TEXT NOT NULL CHECK (matriz IN ('plano_negocios', 'contrato_social', 'memorando', 'fluxo_abertura')),
    bloco TEXT NOT NULL,
    bloco_titulo TEXT NOT NULL,
    bloco_peso INTEGER NOT NULL CHECK (bloco_peso > 0),
    codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    referencia_fonte TEXT,
    UNIQUE (matriz, codigo)
);

-- =============================================================================
-- 2. GOVERNANCA ANTI-ENVIESAMENTO NAS TABELAS SOCIETARIAS BASE (erp.*)
-- =============================================================================
DO $$
DECLARE
    tbl TEXT;
    cname TEXT;
    tbls TEXT[] := ARRAY[
        'erp.pessoa',
        'erp.pessoa_identificador',
        'erp.empresa',
        'erp.estabelecimento',
        'erp.participacao_societaria',
        'erp.enquadramento_historico'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        -- Remove constraint antiga de origem_registro, se houver
        FOR cname IN
            SELECT conname
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.conrelid = tbl::regclass
              AND c.contype = 'c'
              AND a.attname = 'origem_registro'
        LOOP
            EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I', tbl, cname);
        END LOOP;

        EXECUTE format(
            'ALTER TABLE %s ADD CONSTRAINT %I CHECK (origem_registro IN (''acervo_sigaa'', ''importado_v1'', ''importado_rascunho_v2'', ''usuario''))',
            tbl,
            replace(tbl, '.', '_') || '_origem_registro_chk'
        );

        EXECUTE format(
            'ALTER TABLE %s
                ADD COLUMN IF NOT EXISTS status_validacao TEXT NOT NULL DEFAULT ''acervo_referencia'',
                ADD COLUMN IF NOT EXISTS referencia_v1_original TEXT,
                ADD COLUMN IF NOT EXISTS apontamento_auditoria TEXT,
                ADD COLUMN IF NOT EXISTS justificativa_contadora TEXT',
            tbl
        );

        FOR cname IN
            SELECT conname
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.conrelid = tbl::regclass
              AND c.contype = 'c'
              AND a.attname = 'status_validacao'
        LOOP
            EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I', tbl, cname);
        END LOOP;

        EXECUTE format(
            'ALTER TABLE %s ADD CONSTRAINT %I CHECK (status_validacao IN (''acervo_referencia'', ''pendente_revisao'', ''alerta_inconsistencia'', ''homologado_contadora''))',
            tbl,
            replace(tbl, '.', '_') || '_status_validacao_chk'
        );
    END LOOP;
END $$;

-- =============================================================================
-- 3. ENTIDADES DO MODULO PLANEJAMENTO FINANCEIRO & TRIBUTARIO (schema: erp)
-- =============================================================================
CREATE TABLE IF NOT EXISTS erp.orcamento_cenario (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    codigo_cenario TEXT NOT NULL,
    nome TEXT NOT NULL,
    regime_simulacao TEXT NOT NULL DEFAULT 'simples_segregado' CHECK (
        regime_simulacao IN (
            'simples_segregado',
            'simples_fator_r_global',
            'simples_auto_prolabore_28',
            'v1_fixo_6_erro'
        )
    ),
    eh_oficial BOOLEAN NOT NULL DEFAULT false,
    horizonte_meses INTEGER NOT NULL DEFAULT 36 CHECK (horizonte_meses BETWEEN 12 AND 60),
    capital_social_centavos BIGINT NOT NULL DEFAULT 4000000 CHECK (capital_social_centavos >= 0),
    capex_m0_centavos BIGINT NOT NULL DEFAULT 1000000 CHECK (capex_m0_centavos >= 0),
    capex_ano2_centavos BIGINT NOT NULL DEFAULT 1200000 CHECK (capex_ano2_centavos >= 0),
    capex_ano3_centavos BIGINT NOT NULL DEFAULT 1500000 CHECK (capex_ano3_centavos >= 0),
    taxa_depreciacao_anual_micro BIGINT NOT NULL DEFAULT 200000 CHECK (taxa_depreciacao_anual_micro >= 0),
    ticket_medio_centavos BIGINT NOT NULL DEFAULT 150000 CHECK (ticket_medio_centavos >= 0),
    novos_clientes_mes INTEGER NOT NULL DEFAULT 2 CHECK (novos_clientes_mes >= 0),
    inadimplencia_micro BIGINT NOT NULL DEFAULT 50000 CHECK (inadimplencia_micro BETWEEN 0 AND 1000000),
    custo_variavel_micro BIGINT NOT NULL DEFAULT 30000 CHECK (custo_variavel_micro BETWEEN 0 AND 1000000),
    cac_centavos BIGINT NOT NULL DEFAULT 50000 CHECK (cac_centavos >= 0),
    retencao_meses INTEGER NOT NULL DEFAULT 24 CHECK (retencao_meses >= 1),
    tma_anual_micro BIGINT NOT NULL DEFAULT 150000 CHECK (tma_anual_micro >= 0),
    taxa_reserva_lucros_micro BIGINT NOT NULL DEFAULT 200000 CHECK (taxa_reserva_lucros_micro BETWEEN 0 AND 1000000),
    pct_cnae_principal_micro BIGINT NOT NULL DEFAULT 850000 CHECK (pct_cnae_principal_micro BETWEEN 0 AND 1000000),
    opex_fixo_ano1_mensal_centavos BIGINT NOT NULL DEFAULT 300000 CHECK (opex_fixo_ano1_mensal_centavos >= 0),
    opex_fixo_ano2_mensal_centavos BIGINT NOT NULL DEFAULT 650000 CHECK (opex_fixo_ano2_mensal_centavos >= 0),
    opex_fixo_ano3_mensal_centavos BIGINT NOT NULL DEFAULT 950000 CHECK (opex_fixo_ano3_mensal_centavos >= 0),
    prolabore_m1_3_mensal_centavos BIGINT NOT NULL DEFAULT 0 CHECK (prolabore_m1_3_mensal_centavos >= 0),
    prolabore_m4_12_mensal_centavos BIGINT NOT NULL DEFAULT 450000 CHECK (prolabore_m4_12_mensal_centavos >= 0),
    prolabore_ano2_mensal_centavos BIGINT NOT NULL DEFAULT 700000 CHECK (prolabore_ano2_mensal_centavos >= 0),
    prolabore_ano3_mensal_centavos BIGINT NOT NULL DEFAULT 1000000 CHECK (prolabore_ano3_mensal_centavos >= 0),
    folha_clt_ano2_mensal_centavos BIGINT NOT NULL DEFAULT 1000000 CHECK (folha_clt_ano2_mensal_centavos >= 0),
    folha_clt_ano3_mensal_centavos BIGINT NOT NULL DEFAULT 2520000 CHECK (folha_clt_ano3_mensal_centavos >= 0),
    encargos_clt_micro BIGINT NOT NULL DEFAULT 296400 CHECK (encargos_clt_micro >= 0),
    premissas_json JSONB NOT NULL DEFAULT '{}'::jsonb,
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
    UNIQUE (empresa_id, codigo_cenario)
);

CREATE TABLE IF NOT EXISTS erp.orcamento_projecao_mensal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    cenario_id BIGINT NOT NULL REFERENCES erp.orcamento_cenario(id) ON DELETE CASCADE,
    mes_ordem INTEGER NOT NULL CHECK (mes_ordem BETWEEN 0 AND 60),
    ano_num INTEGER NOT NULL CHECK (ano_num BETWEEN 0 AND 5),
    competencia_ym TEXT NOT NULL,
    novos_clientes INTEGER NOT NULL DEFAULT 0,
    clientes_ativos INTEGER NOT NULL DEFAULT 0,
    receita_bruta_centavos BIGINT NOT NULL DEFAULT 0,
    receita_cnae_principal_centavos BIGINT NOT NULL DEFAULT 0,
    receita_cnae_secundario_centavos BIGINT NOT NULL DEFAULT 0,
    prolabore_centavos BIGINT NOT NULL DEFAULT 0,
    folha_clt_encargos_centavos BIGINT NOT NULL DEFAULT 0,
    rbt12_proporcional_centavos BIGINT NOT NULL DEFAULT 0,
    fs12_proporcional_centavos BIGINT NOT NULL DEFAULT 0,
    fator_r_micro BIGINT NOT NULL DEFAULT 0,
    anexo_cnae_principal TEXT NOT NULL DEFAULT 'Anexo_III',
    anexo_cnae_secundario TEXT NOT NULL DEFAULT 'Anexo_V',
    aliquota_anexo_iii_micro BIGINT NOT NULL DEFAULT 0,
    aliquota_anexo_v_micro BIGINT NOT NULL DEFAULT 0,
    aliquota_efetiva_micro BIGINT NOT NULL DEFAULT 0,
    das_apurado_centavos BIGINT NOT NULL DEFAULT 0,
    das_pago_caixa_centavos BIGINT NOT NULL DEFAULT 0,
    inadimplencia_centavos BIGINT NOT NULL DEFAULT 0,
    recebimentos_centavos BIGINT NOT NULL DEFAULT 0,
    custos_variaveis_centavos BIGINT NOT NULL DEFAULT 0,
    cac_despesa_centavos BIGINT NOT NULL DEFAULT 0,
    opex_fixo_centavos BIGINT NOT NULL DEFAULT 0,
    depreciacao_centavos BIGINT NOT NULL DEFAULT 0,
    ebitda_centavos BIGINT NOT NULL DEFAULT 0,
    lucro_liquido_centavos BIGINT NOT NULL DEFAULT 0,
    fco_centavos BIGINT NOT NULL DEFAULT 0,
    capex_saida_centavos BIGINT NOT NULL DEFAULT 0,
    distribuicao_lucros_centavos BIGINT NOT NULL DEFAULT 0,
    fluxo_liquido_caixa_centavos BIGINT NOT NULL DEFAULT 0,
    saldo_caixa_centavos BIGINT NOT NULL DEFAULT 0,
    alerta_porte TEXT,
    UNIQUE (cenario_id, mes_ordem)
);

CREATE TABLE IF NOT EXISTS erp.orcamento_demonstrativo_anual (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    cenario_id BIGINT NOT NULL REFERENCES erp.orcamento_cenario(id) ON DELETE CASCADE,
    ano_ordem INTEGER NOT NULL CHECK (ano_ordem BETWEEN 0 AND 5),
    rotulo_periodo TEXT NOT NULL,
    porte_estimado TEXT NOT NULL,
    clientes_fim INTEGER NOT NULL DEFAULT 0,
    clientes_media_micro BIGINT NOT NULL DEFAULT 0,
    receita_bruta_centavos BIGINT NOT NULL DEFAULT 0,
    das_centavos BIGINT NOT NULL DEFAULT 0,
    inadimplencia_centavos BIGINT NOT NULL DEFAULT 0,
    receita_liquida_centavos BIGINT NOT NULL DEFAULT 0,
    custos_variaveis_centavos BIGINT NOT NULL DEFAULT 0,
    margem_contribuicao_centavos BIGINT NOT NULL DEFAULT 0,
    cac_centavos BIGINT NOT NULL DEFAULT 0,
    prolabore_centavos BIGINT NOT NULL DEFAULT 0,
    folha_clt_centavos BIGINT NOT NULL DEFAULT 0,
    opex_fixo_centavos BIGINT NOT NULL DEFAULT 0,
    ebitda_centavos BIGINT NOT NULL DEFAULT 0,
    depreciacao_centavos BIGINT NOT NULL DEFAULT 0,
    lucro_liquido_centavos BIGINT NOT NULL DEFAULT 0,
    distribuicao_lucros_centavos BIGINT NOT NULL DEFAULT 0,
    reserva_lucros_centavos BIGINT NOT NULL DEFAULT 0,
    fator_r_anual_micro BIGINT NOT NULL DEFAULT 0,
    aliquota_efetiva_anual_micro BIGINT NOT NULL DEFAULT 0,
    bp_caixa_centavos BIGINT NOT NULL DEFAULT 0,
    bp_imobilizado_bruto_centavos BIGINT NOT NULL DEFAULT 0,
    bp_depreciacao_acumulada_centavos BIGINT NOT NULL DEFAULT 0,
    bp_ativo_total_centavos BIGINT NOT NULL DEFAULT 0,
    bp_das_a_recolher_centavos BIGINT NOT NULL DEFAULT 0,
    bp_obrigacoes_trabalhistas_centavos BIGINT NOT NULL DEFAULT 0,
    bp_passivo_total_centavos BIGINT NOT NULL DEFAULT 0,
    bp_capital_social_centavos BIGINT NOT NULL DEFAULT 0,
    bp_reservas_lucros_centavos BIGINT NOT NULL DEFAULT 0,
    bp_pl_total_centavos BIGINT NOT NULL DEFAULT 0,
    bp_diferenca_centavos BIGINT NOT NULL DEFAULT 0 CHECK (bp_diferenca_centavos = 0),
    fluxo_livre_projeto_centavos BIGINT NOT NULL DEFAULT 0,
    indicadores_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (cenario_id, ano_ordem)
);

-- =============================================================================
-- 4. INSTRUMENTOS SOCIETARIOS, PARALEGAL DF & CONSULTAS NORMATIVAS (schema: erp)
-- =============================================================================
CREATE TABLE IF NOT EXISTS erp.instrumento_societario_clausula (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    ordem INTEGER NOT NULL DEFAULT 1 CHECK (ordem >= 1),
    bloco TEXT NOT NULL,
    codigo_criterio TEXT NOT NULL,
    numero_clausula TEXT NOT NULL,
    titulo TEXT NOT NULL,
    regra_texto TEXT NOT NULL,
    aplica_mou BOOLEAN NOT NULL DEFAULT true,
    aplica_contrato BOOLEAN NOT NULL DEFAULT true,
    redacao_mou TEXT,
    redacao_contrato TEXT,
    metodo_haveres TEXT NOT NULL DEFAULT 'nao_aplicavel',
    quorum_tipo TEXT NOT NULL DEFAULT 'nao_aplicavel',
    alcada_centavos BIGINT,
    versao INTEGER NOT NULL DEFAULT 1 CHECK (versao >= 1),
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
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.processo_legalizacao_etapa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    bloco TEXT NOT NULL,
    codigo TEXT NOT NULL,
    nome_etapa TEXT NOT NULL,
    raia_responsavel TEXT NOT NULL CHECK (
        raia_responsavel IN ('socias', 'escritorio_contabil', 'orgaos_publicos')
    ),
    orgao TEXT NOT NULL,
    portal_url TEXT,
    data_consulta DATE,
    entrada_docs TEXT NOT NULL,
    saida_doc TEXT NOT NULL,
    prazo_legal TEXT,
    regra_retorno_exigencia TEXT NOT NULL,
    classificacao_risco TEXT NOT NULL DEFAULT 'baixo' CHECK (
        classificacao_risco IN ('dispensa', 'baixo', 'alto_na', 'alto', 'regulatorio')
    ),
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (
        status IN ('pendente', 'em_andamento', 'concluida', 'exigencia')
    ),
    protocolo_simulado TEXT,
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
    UNIQUE (empresa_id, ordem)
);

CREATE TABLE IF NOT EXISTS erp.consulta_normativa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    numero_questao INTEGER NOT NULL CHECK (numero_questao >= 1),
    enunciado TEXT NOT NULL,
    resposta_autoral TEXT NOT NULL,
    norma_citada TEXT NOT NULL,
    link_oficial TEXT NOT NULL,
    data_acesso DATE NOT NULL,
    decisao_impactada TEXT,
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
    UNIQUE (empresa_id, numero_questao)
);

CREATE TABLE IF NOT EXISTS erp.empresa_decisao_preliminar (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    elemento TEXT NOT NULL,
    opcao_adotada TEXT NOT NULL,
    alternativas_consideradas TEXT,
    justificativa_documental TEXT NOT NULL,
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
    UNIQUE (empresa_id, ordem)
);

-- =============================================================================
-- 5. AUDITORIA: CONFORMIDADE, ALERTAS DE COERENCIA & DIARIO DE IA
-- =============================================================================
CREATE TABLE IF NOT EXISTS auditoria.avaliacao_conformidade (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    criterio_id BIGINT NOT NULL REFERENCES auditoria.criterio_conformidade(id),
    nota_v1 INTEGER CHECK (nota_v1 IS NULL OR nota_v1 BETWEEN 0 AND 4),
    nota INTEGER CHECK (nota IS NULL OR nota BETWEEN 0 AND 4),
    nao_aplicavel BOOLEAN NOT NULL DEFAULT false,
    referencia_localizacao TEXT,
    critica_v1 TEXT,
    justificativa_sustentacao TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (
        origem_registro IN ('acervo_sigaa', 'importado_v1', 'importado_rascunho_v2', 'usuario')
    ),
    status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao' CHECK (
        status_validacao IN ('pendente_revisao', 'alerta_inconsistencia', 'homologado_contadora')
    ),
    autor TEXT NOT NULL DEFAULT 'Nathalia Peres',
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, criterio_id)
);

CREATE TABLE IF NOT EXISTS auditoria.alerta_coerencia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    codigo_regra TEXT NOT NULL,
    severidade TEXT NOT NULL CHECK (severidade IN ('info', 'alerta', 'critico')),
    categoria TEXT NOT NULL,
    modulo_alvo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    recomendacao TEXT NOT NULL,
    resolvido BOOLEAN NOT NULL DEFAULT false,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE auditoria.diario_ia
    ADD COLUMN IF NOT EXISTS entregavel TEXT,
    ADD COLUMN IF NOT EXISTS ferramenta TEXT DEFAULT 'Assistente IA',
    ADD COLUMN IF NOT EXISTS origem_registro TEXT NOT NULL DEFAULT 'usuario',
    ADD COLUMN IF NOT EXISTS status_validacao TEXT NOT NULL DEFAULT 'pendente_revisao';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'auditoria_diario_ia_status_chk'
    ) THEN
        ALTER TABLE auditoria.diario_ia
            ADD CONSTRAINT auditoria_diario_ia_status_chk
            CHECK (status_validacao IN ('pendente_revisao', 'alerta_inconsistencia', 'homologado_contadora'));
    END IF;
END $$;

-- =============================================================================
-- 6. INDICES EXPLICITOS EM 100% DAS FOREIGN KEYS E CHAVES DE CONSULTA
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_erp_orc_cen_emp ON erp.orcamento_cenario(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_orc_proj_cen ON erp.orcamento_projecao_mensal(cenario_id);
CREATE INDEX IF NOT EXISTS idx_erp_orc_dem_cen ON erp.orcamento_demonstrativo_anual(cenario_id);
CREATE INDEX IF NOT EXISTS idx_erp_inst_clau_emp ON erp.instrumento_societario_clausula(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_inst_clau_bloco ON erp.instrumento_societario_clausula(empresa_id, bloco, ordem);
CREATE INDEX IF NOT EXISTS idx_erp_proc_leg_emp ON erp.processo_legalizacao_etapa(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_cons_norm_emp ON erp.consulta_normativa(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_dec_prelim_emp ON erp.empresa_decisao_preliminar(empresa_id);
CREATE INDEX IF NOT EXISTS idx_aud_av_conf_emp ON auditoria.avaliacao_conformidade(empresa_id);
CREATE INDEX IF NOT EXISTS idx_aud_av_conf_crit ON auditoria.avaliacao_conformidade(criterio_id);
CREATE INDEX IF NOT EXISTS idx_aud_alerta_coer_emp ON auditoria.alerta_coerencia(empresa_id);

-- =============================================================================
-- 7. TRIGGERS DE ATUALIZACAO TEMPORAL (atualizado_em)
-- =============================================================================
DO $$
DECLARE
    t TEXT;
    tabelas_ts TEXT[] := ARRAY[
        'erp.orcamento_cenario',
        'erp.instrumento_societario_clausula',
        'erp.processo_legalizacao_etapa',
        'erp.consulta_normativa',
        'erp.empresa_decisao_preliminar',
        'auditoria.avaliacao_conformidade',
        'auditoria.alerta_coerencia'
    ];
    trg_nome TEXT;
BEGIN
    FOREACH t IN ARRAY tabelas_ts LOOP
        trg_nome := 'trg_' || replace(t, '.', '_') || '_upd';
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = trg_nome) THEN
            EXECUTE format(
                'CREATE TRIGGER %I BEFORE UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION auditoria.fn_set_atualizado_em()',
                trg_nome, t
            );
        END IF;
    END LOOP;
END $$;

-- =============================================================================
-- 8. VISAO ANALITICA DE CONFORMIDADE (IABP) E QUARENTENA ANTI-ENVIESAMENTO
-- =============================================================================
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
        COALESCE(AVG(av.nota::numeric) FILTER (WHERE COALESCE(av.nao_aplicavel, false) = false), 0) AS media_bloco
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
    ROUND(SUM((media_bloco / 4.0) * bloco_peso), 2) AS iabp_total,
    ROUND(SUM((media_bloco / 4.0) * bloco_peso) / 10.0, 2) AS nota_estimada_10
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
SELECT 'instrumentos_societarios', chave, numero_clausula || ' - ' || titulo, origem_registro, status_validacao, apontamento_auditoria
FROM erp.instrumento_societario_clausula
UNION ALL
SELECT 'legalizacao_df', chave, codigo || ' - ' || nome_etapa, origem_registro, status_validacao, apontamento_auditoria
FROM erp.processo_legalizacao_etapa
UNION ALL
SELECT 'orcamento_tributario', chave, codigo_cenario || ' - ' || nome, origem_registro, status_validacao, apontamento_auditoria
FROM erp.orcamento_cenario
UNION ALL
SELECT 'consultas_normativas', chave, 'Q' || numero_questao || ' - ' || LEFT(enunciado, 60), origem_registro, status_validacao, apontamento_auditoria
FROM erp.consulta_normativa
UNION ALL
SELECT 'conformidade_criterios', av.chave, c.matriz || ':' || c.codigo, av.origem_registro, av.status_validacao, av.critica_v1
FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id;

CREATE OR REPLACE VIEW erp.vw_orcamento_resumo_anual AS
SELECT
    e.chave AS empresa_chave,
    c.codigo_cenario,
    c.nome AS cenario_nome,
    c.regime_simulacao,
    c.eh_oficial,
    c.status_validacao,
    d.ano_ordem,
    d.rotulo_periodo,
    d.porte_estimado,
    d.clientes_fim,
    ROUND(d.receita_bruta_centavos / 100.0, 2) AS receita_bruta_rs,
    ROUND(d.das_centavos / 100.0, 2) AS das_rs,
    ROUND(d.lucro_liquido_centavos / 100.0, 2) AS lucro_liquido_rs,
    ROUND(d.fator_r_anual_micro / 10000.0, 2) AS fator_r_pct,
    ROUND(d.aliquota_efetiva_anual_micro / 10000.0, 2) AS aliq_efetiva_pct,
    ROUND(d.bp_ativo_total_centavos / 100.0, 2) AS ativo_total_rs,
    ROUND(d.bp_passivo_total_centavos / 100.0, 2) AS passivo_total_rs,
    ROUND(d.bp_pl_total_centavos / 100.0, 2) AS pl_total_rs,
    d.bp_diferenca_centavos
FROM erp.orcamento_demonstrativo_anual d
JOIN erp.orcamento_cenario c ON c.id = d.cenario_id
JOIN erp.empresa e ON e.id = c.empresa_id
ORDER BY c.id, d.ano_ordem;
