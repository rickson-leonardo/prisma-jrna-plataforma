-- Camada 3: Normalizado (modelo de dominio em 3FN + linhagem + conferencia)
PRAGMA foreign_keys = ON;

-- 1. Cadastro e historia temporal
CREATE TABLE IF NOT EXISTS nrm_pessoa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: pes:cpf:11122233397:ronaldo
    tipo_pessoa TEXT NOT NULL CHECK (tipo_pessoa IN ('PF', 'PJ', 'estrangeira')),
    nome_canonico TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_pessoa_identificador (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    pessoa_id INTEGER NOT NULL REFERENCES nrm_pessoa(id),
    tipo_id TEXT NOT NULL CHECK (tipo_id IN ('CPF', 'CNPJ', 'IE', 'IM', 'NIRE', 'CRC', 'SWIFT', 'OUTRO')),
    valor TEXT NOT NULL, -- Texto preservando zeros a esquerda
    eh_ficticio INTEGER NOT NULL DEFAULT 1 CHECK (eh_ficticio IN (0, 1)),
    fonte_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_pessoa_ocorrencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    pessoa_id INTEGER NOT NULL REFERENCES nrm_pessoa(id),
    nome_impresso TEXT NOT NULL,
    identificador_impresso TEXT,
    papel TEXT NOT NULL, -- emitente, destinatario, tomador, prestador, socio, empregado, banco, contador, etc.
    fonte_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: emp:rota_sul_d2, emp:rota_sul_d4, emp:meia_ponte, emp:horizonte
    pessoa_id INTEGER NOT NULL REFERENCES nrm_pessoa(id),
    nome_curto TEXT NOT NULL,
    papel_no_caso TEXT NOT NULL CHECK (
        papel_no_caso IN ('cliente_d2', 'cliente_d4', 'empresa_relacionada_d4', 'caso_auditoria_d3', 'contraparte')
    )
);

CREATE TABLE IF NOT EXISTS nrm_estabelecimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: est:rota_sul_d4:matriz, est:rota_sul_d4:filial_itajai
    empresa_id INTEGER NOT NULL REFERENCES nrm_empresa(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('matriz', 'filial', 'unico')),
    cnpj TEXT NOT NULL,
    uf TEXT,
    municipio TEXT,
    endereco TEXT
);

CREATE TABLE IF NOT EXISTS nrm_conta_bancaria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: cta:meridional:0001:matriz
    empresa_id INTEGER NOT NULL REFERENCES nrm_empresa(id),
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    banco_nome TEXT NOT NULL,
    agencia TEXT,
    conta_numero TEXT,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_evento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    empresa_id INTEGER REFERENCES nrm_empresa(id),
    tipo_evento TEXT NOT NULL, -- constituicao, alteracao_contratual, abertura_filial, mudanca_regime, carta_socios, admissao_prevista
    data_evento TEXT NOT NULL, -- ISO-8601
    descricao TEXT NOT NULL,
    fonte_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_fato (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    sujeito_chave TEXT NOT NULL, -- Chave da empresa, estabelecimento ou pessoa
    evento_id INTEGER REFERENCES nrm_evento(id),
    atributo TEXT NOT NULL, -- razao_social, sede, regime, porte, cnae, capital_social, ie, im, empregado_parametro, etc.
    valor_texto TEXT NOT NULL,
    valor_centavos INTEGER,
    vigente_de TEXT NOT NULL, -- ISO-8601
    vigente_ate TEXT, -- ISO-8601 ou NULL se vigente
    fonte_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_participacao_societaria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    empresa_id INTEGER NOT NULL REFERENCES nrm_empresa(id),
    socio_pessoa_id INTEGER NOT NULL REFERENCES nrm_pessoa(id),
    quotas INTEGER,
    valor_centavos INTEGER,
    percentual_micro INTEGER,
    papel TEXT NOT NULL, -- socio, socio_administrador, procurador, socio_de_fato, titular_formal
    vigente_de TEXT NOT NULL,
    vigente_ate TEXT,
    fonte_chave TEXT NOT NULL
);

-- 2. Operacoes fiscais
CREATE TABLE IF NOT EXISTS nrm_produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: prod:PN-9018
    codigo_interno TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    ncm TEXT,
    cest TEXT,
    origem TEXT
);

CREATE TABLE IF NOT EXISTS nrm_documento_fiscal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    tipo_documento TEXT NOT NULL CHECK (
        tipo_documento IN ('NFe', 'NFSe', 'CTe', 'NFe_compra', 'NFe_entrada_importacao', 'NFCe_faixa', 'Fatura_energia', 'Fatura_telecom')
    ),
    numero TEXT,
    serie TEXT,
    chave_acesso TEXT,
    data_emissao TEXT NOT NULL,
    emitente_pessoa_id INTEGER REFERENCES nrm_pessoa(id),
    destinatario_pessoa_id INTEGER REFERENCES nrm_pessoa(id),
    natureza_operacao TEXT,
    valor_total_centavos INTEGER NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_documento_fiscal_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    documento_fiscal_id INTEGER NOT NULL REFERENCES nrm_documento_fiscal(id),
    n_item INTEGER NOT NULL,
    produto_id INTEGER REFERENCES nrm_produto(id), -- Produto interno (quando mapeado)
    codigo_item_documento TEXT, -- Codigo impresso no documento (inclusive SKU do fornecedor)
    descricao TEXT NOT NULL,
    ncm_hs TEXT,
    cfop TEXT,
    cst_csosn TEXT,
    unidade TEXT,
    quantidade_micro INTEGER,
    valor_unitario_micro INTEGER,
    valor_total_centavos INTEGER NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'BRL'
);

CREATE TABLE IF NOT EXISTS nrm_item_tributo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    item_id INTEGER REFERENCES nrm_documento_fiscal_item(id),
    documento_fiscal_id INTEGER NOT NULL REFERENCES nrm_documento_fiscal(id),
    tributo TEXT NOT NULL, -- ICMS, ICMS_ST, DIFAL, IPI, PIS, COFINS, ISS, IRRF, CSLL, CIP
    base_centavos INTEGER,
    aliquota_micro INTEGER,
    aliquota_texto TEXT,
    valor_centavos INTEGER NOT NULL
);

-- 3. Operacoes financeiras
CREATE TABLE IF NOT EXISTS nrm_movimento_bancario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: mov:matriz:2025-01-04:TRF106997:6
    conta_bancaria_id INTEGER NOT NULL REFERENCES nrm_conta_bancaria(id),
    data_movimento TEXT NOT NULL,
    historico TEXT NOT NULL,
    doc_ref TEXT NOT NULL,
    tipo_dc TEXT NOT NULL CHECK (tipo_dc IN ('D', 'C')),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
    saldo_apos_centavos INTEGER NOT NULL,
    origem_saldo TEXT NOT NULL CHECK (origem_saldo IN ('impresso', 'calculado_formula'))
);

CREATE TABLE IF NOT EXISTS nrm_comprovante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    subtipo TEXT NOT NULL, -- PIX_enviado, PIX_recebido, TED_enviada, TED_recebida, pagto_boleto, pagto_tributo, debito_automatico, cheque_pago, deposito_especie, credito_cartao, aviso_tarifas, etc.
    data_operacao TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    contraparte_pessoa_id INTEGER REFERENCES nrm_pessoa(id),
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_titulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    subtipo TEXT NOT NULL CHECK (subtipo IN ('Boleto_aluguel', 'Boleto_condominio', 'Duplicata')),
    numero TEXT,
    data_vencimento TEXT,
    valor_centavos INTEGER NOT NULL,
    beneficiario_pessoa_id INTEGER REFERENCES nrm_pessoa(id),
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_cambio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    contrato_numero TEXT NOT NULL,
    data_contratacao TEXT NOT NULL,
    moeda_estrangeira TEXT NOT NULL,
    valor_estrangeiro_centavos INTEGER NOT NULL,
    taxa_micro INTEGER NOT NULL,
    taxa_texto TEXT NOT NULL,
    principal_brl_centavos INTEGER NOT NULL,
    iof_centavos INTEGER,
    tarifa_centavos INTEGER,
    valor_total_brl_centavos INTEGER NOT NULL,
    exportador_pessoa_id INTEGER REFERENCES nrm_pessoa(id),
    invoice_numero TEXT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_contrato_credito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    empresa_id INTEGER NOT NULL REFERENCES nrm_empresa(id),
    numero_contrato TEXT NOT NULL,
    data_contratacao TEXT NOT NULL,
    principal_centavos INTEGER NOT NULL,
    taxa_juros_texto TEXT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_parcela (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    contrato_id INTEGER NOT NULL REFERENCES nrm_contrato_credito(id),
    numero_parcela INTEGER NOT NULL,
    data_vencimento TEXT NOT NULL,
    amortizacao_centavos INTEGER NOT NULL,
    juros_centavos INTEGER NOT NULL,
    total_centavos INTEGER NOT NULL,
    situacao TEXT
);

CREATE TABLE IF NOT EXISTS nrm_liquidacao_cartao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    data_liquidacao TEXT NOT NULL,
    valor_bruto_centavos INTEGER NOT NULL,
    taxa_centavos INTEGER,
    valor_liquido_centavos INTEGER NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_liquidacao_cartao_venda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    liquidacao_id INTEGER NOT NULL REFERENCES nrm_liquidacao_cartao(id),
    data_venda TEXT,
    autorizacao TEXT,
    modalidade TEXT,
    parcela_texto TEXT,
    valor_bruto_centavos INTEGER NOT NULL,
    valor_liquido_centavos INTEGER
);

-- 4. Tributario e aduaneiro
CREATE TABLE IF NOT EXISTS nrm_guia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    tipo_guia TEXT NOT NULL, -- DAS, DARF_IPI, DARE_SC, DARE_GO_ICMS_IMP, DARE_GO_ST, GNRE_DF, GNRE_ES, GNRE_MG, AFRMM
    competencia TEXT,
    data_vencimento TEXT,
    valor_principal_centavos INTEGER NOT NULL,
    valor_total_centavos INTEGER NOT NULL,
    uf TEXT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_guia_composicao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    guia_id INTEGER NOT NULL REFERENCES nrm_guia(id),
    tributo_codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_apuracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    empresa_id INTEGER NOT NULL REFERENCES nrm_empresa(id),
    tipo_apuracao TEXT NOT NULL, -- PGDAS_D, IPI
    competencia TEXT NOT NULL,
    receita_bruta_centavos INTEGER,
    rbt12_centavos INTEGER,
    tributo_apurado_centavos INTEGER NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_di (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    numero_di TEXT NOT NULL,
    data_registro TEXT NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'USD',
    taxa_micro INTEGER NOT NULL,
    taxa_texto TEXT NOT NULL,
    valor_fob_moeda_centavos INTEGER NOT NULL,
    frete_seguro_moeda_centavos INTEGER,
    valor_aduaneiro_brl_centavos INTEGER NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_di_adicao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    di_id INTEGER NOT NULL REFERENCES nrm_di(id),
    numero_adicao TEXT NOT NULL,
    ncm TEXT NOT NULL,
    valor_aduaneiro_centavos INTEGER NOT NULL,
    ii_centavos INTEGER NOT NULL,
    ipi_centavos INTEGER NOT NULL,
    pis_imp_centavos INTEGER NOT NULL,
    cofins_imp_centavos INTEGER NOT NULL
);

-- 5. Controle interno
CREATE TABLE IF NOT EXISTS nrm_fechamento_caixa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    data_fechamento TEXT NOT NULL,
    valor_total_centavos INTEGER NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_fechamento_caixa_dia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    fechamento_id INTEGER NOT NULL REFERENCES nrm_fechamento_caixa(id),
    data_dia TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_memorando (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    data_memorando TEXT NOT NULL,
    assunto TEXT NOT NULL,
    valor_centavos INTEGER,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS nrm_recibo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    subtipo TEXT NOT NULL CHECK (subtipo IN ('aluguel', 'retirada_socio', 'prolabore', 'autonomo')),
    data_recibo TEXT NOT NULL,
    competencia TEXT,
    beneficiario_pessoa_id INTEGER REFERENCES nrm_pessoa(id),
    valor_centavos INTEGER NOT NULL,
    doc_ref TEXT
);

-- 6. Contabil e estoques
CREATE TABLE IF NOT EXISTS nrm_conta_contabil (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: cc:1.1.01.001
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    grupo INTEGER NOT NULL,
    natureza TEXT CHECK (natureza IN ('D', 'C'))
);

CREATE TABLE IF NOT EXISTS nrm_lancamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: lanc:2025:0360
    ano INTEGER NOT NULL,
    numero_lancamento INTEGER NOT NULL,
    data_lancamento TEXT NOT NULL,
    historico TEXT NOT NULL,
    tag_ref TEXT,
    UNIQUE (ano, numero_lancamento)
);

CREATE TABLE IF NOT EXISTS nrm_partida (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    lancamento_id INTEGER NOT NULL REFERENCES nrm_lancamento(id),
    ordem INTEGER NOT NULL,
    conta_id INTEGER NOT NULL REFERENCES nrm_conta_contabil(id),
    dc TEXT NOT NULL CHECK (dc IN ('D', 'C')),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0)
);

CREATE TABLE IF NOT EXISTS nrm_saldo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    conta_id INTEGER NOT NULL REFERENCES nrm_conta_contabil(id),
    periodo TEXT NOT NULL,
    fonte TEXT NOT NULL, -- balancete_xlsx, balancete_pdf, razao, abertura_d1
    saldo_anterior_centavos INTEGER,
    debito_centavos INTEGER,
    credito_centavos INTEGER,
    saldo_atual_centavos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_ciclo_importacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    empresa_id INTEGER REFERENCES nrm_empresa(id),
    cambio_doc_ref TEXT NOT NULL,
    data_cambio TEXT NOT NULL,
    data_entrada_estoque TEXT,
    pais_origem TEXT,
    principal_brl_centavos INTEGER,
    iof_centavos INTEGER
);

CREATE TABLE IF NOT EXISTS nrm_estoque_movimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    produto_id INTEGER NOT NULL REFERENCES nrm_produto(id),
    ciclo_importacao_id INTEGER REFERENCES nrm_ciclo_importacao(id),
    tipo_movimento TEXT NOT NULL CHECK (tipo_movimento IN ('abertura', 'entrada_importacao', 'saida_nfe', 'saldo_mensal')),
    data_movimento TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    custo_unitario_centavos INTEGER,
    valor_total_centavos INTEGER
);

-- 7. Relacao central: transacao
CREATE TABLE IF NOT EXISTS nrm_transacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: tx:TRF106997 ou tx:matriz:2025-01:BOL005
    regra_agrupamento TEXT NOT NULL CHECK (regra_agrupamento IN ('doc_ref_unico', 'recorrente_mensal', 'nfe_vinculada', 'avulso')),
    doc_ref TEXT,
    estabelecimento_id INTEGER REFERENCES nrm_estabelecimento(id),
    ano_mes TEXT,
    data_referencia TEXT,
    status_vinculo TEXT NOT NULL CHECK (status_vinculo IN ('ligado', 'ambiguo', 'sem_par'))
);

CREATE TABLE IF NOT EXISTS nrm_transacao_membro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    transacao_id INTEGER NOT NULL REFERENCES nrm_transacao(id),
    tabela_membro TEXT NOT NULL,
    membro_chave TEXT NOT NULL,
    papel_membro TEXT NOT NULL, -- documento, movimento_bancario, lancamento_contabil, ciclo_importacao
    criterio_vinculo TEXT NOT NULL,
    UNIQUE (transacao_id, tabela_membro, membro_chave)
);

-- 8. Curso
CREATE TABLE IF NOT EXISTS nrm_dossie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: dos:D1, dos:D2, dos:D3, dos:D4
    codigo TEXT NOT NULL UNIQUE,
    titulo TEXT NOT NULL,
    periodo_texto TEXT,
    prazo_texto TEXT
);

CREATE TABLE IF NOT EXISTS nrm_requisito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    dossie_id INTEGER NOT NULL REFERENCES nrm_dossie(id),
    codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    fonte_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    dossie_id INTEGER REFERENCES nrm_dossie(id),
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id)
);

CREATE TABLE IF NOT EXISTS nrm_material_secao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    material_id INTEGER NOT NULL REFERENCES nrm_material(id),
    ordem INTEGER NOT NULL,
    titulo TEXT,
    conteudo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_devolutiva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    dossie_id INTEGER NOT NULL REFERENCES nrm_dossie(id),
    grupo TEXT NOT NULL, -- G00..G29
    nossa_dupla INTEGER NOT NULL DEFAULT 0 CHECK (nossa_dupla IN (0, 1)),
    nota_texto TEXT,
    resumo TEXT,
    material_id INTEGER NOT NULL REFERENCES nrm_material(id)
);

CREATE TABLE IF NOT EXISTS nrm_nota_didatica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    origem_chave TEXT NOT NULL,
    texto TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nrm_tema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    termo TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS nrm_vinculo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    tema_id INTEGER NOT NULL REFERENCES nrm_tema(id),
    alvo_tabela TEXT NOT NULL,
    alvo_chave TEXT NOT NULL,
    criterio TEXT NOT NULL
);

-- 9. Transversais: evidencia e conferencia
CREATE TABLE IF NOT EXISTS evidencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    tabela_destino TEXT NOT NULL,
    registro_chave TEXT NOT NULL,
    bru_tabela TEXT NOT NULL CHECK (bru_tabela IN ('bru_arquivo', 'bru_linha', 'bru_celula', 'bru_paragrafo')),
    bru_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conferencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    regra TEXT NOT NULL, -- ex.: sigaa_html_vazio, cpf_divergente, saldo_divergente, gate_cobertura
    severidade TEXT NOT NULL CHECK (severidade IN ('info', 'alerta', 'divergencia', 'gate_ok', 'gate_falha')),
    registros_json TEXT NOT NULL, -- JSON com chaves e arquivos envolvidos
    valores_json TEXT NOT NULL, -- JSON com valores encontrados
    status TEXT NOT NULL CHECK (status IN ('aberto', 'ok', 'registrado')),
    descricao TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidencia_reg ON evidencia(tabela_destino, registro_chave);
CREATE INDEX IF NOT EXISTS idx_nrm_fato_sujeito ON nrm_fato(sujeito_chave, vigente_de);
CREATE INDEX IF NOT EXISTS idx_nrm_tx_docref ON nrm_transacao(doc_ref);
