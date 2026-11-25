-- Migracao 001: Banco Unico PostgreSQL 17 (lab_contabil)
-- Schemas: acervo (copia imutavel SIGAA), erp (dominio contabil multi-empresa 3FN), auditoria (rastreabilidade e controle)

CREATE SCHEMA IF NOT EXISTS acervo;
CREATE SCHEMA IF NOT EXISTS erp;
CREATE SCHEMA IF NOT EXISTS auditoria;

-- =============================================================================
-- FUNCOES E CONTROLE DE AUDITORIA
-- =============================================================================
CREATE TABLE IF NOT EXISTS auditoria.schema_migration (
    versao TEXT PRIMARY KEY,
    descricao TEXT NOT NULL,
    aplicado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION auditoria.fn_set_atualizado_em()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em = now();
    RETURN NEW;
END;
$$;

-- =============================================================================
-- SCHEMA: acervo (Camada 1 Bruta + Camada 2 Extraida do SIGAA)
-- =============================================================================
CREATE TABLE IF NOT EXISTS acervo.bru_arquivo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    caminho_relativo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    extensao TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    tamanho_bytes BIGINT NOT NULL CHECK (tamanho_bytes >= 0),
    dossie TEXT NOT NULL CHECK (dossie IN ('D1', 'D2', 'D3', 'D4', 'Resultado', '_paginas')),
    dominio TEXT NOT NULL CHECK (dominio IN ('empresa', 'curso', 'misto')),
    papel_acervo TEXT NOT NULL CHECK (
        papel_acervo IN ('primario', 'container_zip', 'duplicata_sha256', 'consolidado_espelho', 'formato_espelho')
    ),
    zip_origem_id BIGINT REFERENCES acervo.bru_arquivo(id),
    duplicata_de_id BIGINT REFERENCES acervo.bru_arquivo(id),
    paginas_total INTEGER CHECK (paginas_total IS NULL OR paginas_total >= 0)
);

CREATE TABLE IF NOT EXISTS acervo.bru_zip_entrada (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    zip_arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    caminho_interno TEXT NOT NULL,
    tamanho_bytes BIGINT NOT NULL CHECK (tamanho_bytes >= 0),
    crc32 BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    arquivo_disco_id BIGINT REFERENCES acervo.bru_arquivo(id),
    UNIQUE (zip_arquivo_id, caminho_interno)
);

CREATE TABLE IF NOT EXISTS acervo.bru_linha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    pagina INTEGER NOT NULL CHECK (pagina >= 1),
    n_linha INTEGER NOT NULL CHECK (n_linha >= 1),
    texto TEXT NOT NULL,
    x0 DOUBLE PRECISION NOT NULL DEFAULT 0,
    y0 DOUBLE PRECISION NOT NULL DEFAULT 0,
    tam_fonte DOUBLE PRECISION NOT NULL DEFAULT 0,
    fonte TEXT,
    cor_hex TEXT,
    eh_marca_dagua BOOLEAN NOT NULL DEFAULT false,
    destino TEXT,
    UNIQUE (arquivo_id, pagina, n_linha)
);

CREATE TABLE IF NOT EXISTS acervo.bru_celula (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    aba TEXT NOT NULL,
    ordem_aba INTEGER NOT NULL CHECK (ordem_aba >= 1),
    linha INTEGER NOT NULL CHECK (linha >= 1),
    coluna INTEGER NOT NULL CHECK (coluna >= 1),
    endereco TEXT NOT NULL,
    tipo_dado TEXT NOT NULL CHECK (tipo_dado IN ('texto', 'numero', 'data', 'formula', 'booleano', 'vazio')),
    valor_texto TEXT,
    valor_cacheado TEXT,
    formula TEXT,
    formato_numero TEXT,
    destino TEXT,
    UNIQUE (arquivo_id, aba, endereco)
);

CREATE TABLE IF NOT EXISTS acervo.bru_paragrafo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    origem_bloco TEXT NOT NULL CHECK (origem_bloco IN ('paragrafo', 'tabela_celula', 'html_bloco', 'txt_linha')),
    tabela_idx INTEGER,
    linha_idx INTEGER,
    coluna_idx INTEGER,
    estilo TEXT,
    texto TEXT NOT NULL,
    destino TEXT,
    UNIQUE (arquivo_id, ordem)
);

CREATE TABLE IF NOT EXISTS acervo.bru_sigaa_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    ordem INTEGER NOT NULL UNIQUE CHECK (ordem >= 1),
    status_fetch TEXT NOT NULL,
    content_type TEXT,
    bytes_fetch BIGINT,
    rotulo_sigaa TEXT NOT NULL,
    link_texto TEXT,
    dossie_inferido TEXT CHECK (dossie_inferido IN ('D1', 'D2', 'D3', 'D4', 'Resultado', '_paginas')),
    arquivo_id BIGINT REFERENCES acervo.bru_arquivo(id),
    observacao TEXT
);

CREATE TABLE IF NOT EXISTS acervo.ext_documento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    modelo TEXT NOT NULL,
    tipo TEXT NOT NULL,
    numero TEXT,
    serie TEXT,
    data_emissao TEXT,
    data_referencia TEXT,
    doc_ref TEXT,
    estabelecimento_prefixo TEXT,
    valor_total_centavos BIGINT,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    valor_total_texto TEXT
);

CREATE TABLE IF NOT EXISTS acervo.ext_campo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    documento_id BIGINT NOT NULL REFERENCES acervo.ext_documento(id),
    secao TEXT,
    rotulo TEXT NOT NULL,
    valor_texto TEXT NOT NULL,
    valor_centavos BIGINT,
    moeda TEXT,
    valor_micro BIGINT,
    valor_data TEXT,
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    documento_id BIGINT NOT NULL REFERENCES acervo.ext_documento(id),
    tabela TEXT NOT NULL,
    n_linha INTEGER NOT NULL CHECK (n_linha >= 1),
    colunas_json JSONB NOT NULL,
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id),
    UNIQUE (documento_id, tabela, n_linha)
);

CREATE TABLE IF NOT EXISTS acervo.ext_extrato_linha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    aba TEXT NOT NULL,
    n_linha INTEGER NOT NULL,
    conta_codigo TEXT NOT NULL,
    data_movimento TEXT NOT NULL,
    historico TEXT NOT NULL,
    doc_ref TEXT NOT NULL,
    debito_centavos BIGINT,
    credito_centavos BIGINT,
    saldo_centavos BIGINT NOT NULL,
    origem_valor TEXT NOT NULL CHECK (origem_valor IN ('impresso', 'calculado_formula')),
    celula_saldo_id BIGINT REFERENCES acervo.bru_celula(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_diario_lancamento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    ano INTEGER NOT NULL,
    numero_lancamento INTEGER NOT NULL,
    data_lancamento TEXT NOT NULL,
    historico TEXT NOT NULL,
    tag_ref TEXT,
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id),
    UNIQUE (ano, numero_lancamento)
);

CREATE TABLE IF NOT EXISTS acervo.ext_diario_partida (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    lancamento_id BIGINT NOT NULL REFERENCES acervo.ext_diario_lancamento(id),
    ordem INTEGER NOT NULL,
    conta_codigo TEXT NOT NULL,
    conta_nome TEXT NOT NULL,
    dc TEXT NOT NULL CHECK (dc IN ('D', 'C')),
    valor_centavos BIGINT NOT NULL CHECK (valor_centavos >= 0),
    valor_texto TEXT NOT NULL,
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id),
    UNIQUE (lancamento_id, ordem)
);

CREATE TABLE IF NOT EXISTS acervo.ext_razao_linha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    ano INTEGER NOT NULL,
    conta_codigo TEXT NOT NULL,
    conta_nome TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    data_movimento TEXT,
    numero_lancamento INTEGER,
    historico TEXT NOT NULL,
    debito_centavos BIGINT,
    credito_centavos BIGINT,
    saldo_centavos BIGINT,
    saldo_dc TEXT CHECK (saldo_dc IN ('D', 'C') OR saldo_dc IS NULL),
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_balancete_linha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    fonte TEXT NOT NULL CHECK (fonte IN ('pdf', 'xlsx')),
    periodo TEXT NOT NULL,
    conta_codigo TEXT NOT NULL,
    conta_nome TEXT NOT NULL,
    saldo_anterior_centavos BIGINT NOT NULL,
    debito_centavos BIGINT NOT NULL,
    credito_centavos BIGINT NOT NULL,
    saldo_atual_centavos BIGINT NOT NULL,
    origem_valor TEXT NOT NULL CHECK (origem_valor IN ('impresso', 'calculado_formula')),
    celula_id BIGINT REFERENCES acervo.bru_celula(id),
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_estoque_linha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    aba TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    produto_codigo TEXT,
    descricao TEXT,
    dados_json JSONB NOT NULL,
    celula_id BIGINT REFERENCES acervo.bru_celula(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_parametro_planilha (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    aba TEXT NOT NULL,
    rotulo TEXT NOT NULL,
    valor_texto TEXT NOT NULL,
    celula_id BIGINT REFERENCES acervo.bru_celula(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_material (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    dossie TEXT NOT NULL,
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS acervo.ext_secao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    material_id BIGINT NOT NULL REFERENCES acervo.ext_material(id),
    ordem INTEGER NOT NULL,
    titulo TEXT,
    conteudo TEXT NOT NULL,
    paragrafo_id BIGINT REFERENCES acervo.bru_paragrafo(id),
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id)
);

CREATE TABLE IF NOT EXISTS acervo.ext_nota_didatica (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id),
    documento_id BIGINT REFERENCES acervo.ext_documento(id),
    texto TEXT NOT NULL,
    linha_bruto_id BIGINT REFERENCES acervo.bru_linha(id),
    celula_id BIGINT REFERENCES acervo.bru_celula(id),
    paragrafo_id BIGINT REFERENCES acervo.bru_paragrafo(id)
);

-- =============================================================================
-- SCHEMA: erp (Modelo 3FN Multi-Empresa + D1 Editavel)
-- =============================================================================
CREATE TABLE IF NOT EXISTS erp.pessoa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    tipo_pessoa TEXT NOT NULL CHECK (tipo_pessoa IN ('PF', 'PJ', 'estrangeira')),
    nome_canonico TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.pessoa_identificador (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    pessoa_id BIGINT NOT NULL REFERENCES erp.pessoa(id),
    tipo_id TEXT NOT NULL CHECK (tipo_id IN ('CPF', 'CNPJ', 'IE', 'IM', 'NIRE', 'CRC', 'SWIFT', 'OUTRO')),
    valor TEXT NOT NULL,
    eh_ficticio BOOLEAN NOT NULL DEFAULT true,
    fonte_chave TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.pessoa_ocorrencia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    pessoa_id BIGINT NOT NULL REFERENCES erp.pessoa(id),
    nome_impresso TEXT NOT NULL,
    identificador_impresso TEXT,
    papel TEXT NOT NULL,
    fonte_chave TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.empresa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    pessoa_id BIGINT NOT NULL REFERENCES erp.pessoa(id),
    nome_curto TEXT NOT NULL,
    papel_no_caso TEXT NOT NULL CHECK (
        papel_no_caso IN (
            'escritorio_contabil',
            'cliente_d2',
            'cliente_d4',
            'empresa_relacionada_d4',
            'caso_auditoria_d3',
            'contraparte'
        )
    ),
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.relacao_escritorio_cliente (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    escritorio_empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    cliente_empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    vigente_de DATE NOT NULL,
    vigente_ate DATE,
    status TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'suspenso', 'encerrado', 'estudo_caso')),
    contrato_ref TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vigente_ate IS NULL OR vigente_ate >= vigente_de),
    CHECK (escritorio_empresa_id <> cliente_empresa_id)
);

CREATE TABLE IF NOT EXISTS erp.estabelecimento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('matriz', 'filial', 'unico')),
    cnpj TEXT NOT NULL,
    uf TEXT,
    municipio TEXT,
    endereco TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.conta_bancaria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    banco_nome TEXT NOT NULL,
    agencia TEXT,
    conta_numero TEXT,
    descricao TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.evento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT REFERENCES erp.empresa(id),
    tipo_evento TEXT NOT NULL,
    data_evento DATE NOT NULL,
    descricao TEXT NOT NULL,
    fonte_chave TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.fato (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    sujeito_chave TEXT NOT NULL,
    evento_id BIGINT REFERENCES erp.evento(id),
    atributo TEXT NOT NULL,
    valor_texto TEXT NOT NULL,
    valor_centavos BIGINT,
    vigente_de DATE NOT NULL,
    vigente_ate DATE,
    fonte_chave TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vigente_ate IS NULL OR vigente_ate >= vigente_de)
);

CREATE TABLE IF NOT EXISTS erp.participacao_societaria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    socio_pessoa_id BIGINT NOT NULL REFERENCES erp.pessoa(id),
    quotas BIGINT,
    valor_centavos BIGINT,
    percentual_micro BIGINT,
    papel TEXT NOT NULL,
    vigente_de DATE NOT NULL,
    vigente_ate DATE,
    fonte_chave TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vigente_ate IS NULL OR vigente_ate >= vigente_de)
);

CREATE TABLE IF NOT EXISTS erp.enquadramento_historico (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    porte TEXT NOT NULL CHECK (porte IN ('ME', 'EPP', 'Demais')),
    regime_tributario TEXT NOT NULL CHECK (
        regime_tributario IN (
            'Simples_Anexo_I', 'Simples_Anexo_III', 'Simples_Anexo_V',
            'Simples_Misto', 'Lucro_Presumido', 'Lucro_Real'
        )
    ),
    cnae_principal TEXT NOT NULL,
    cnaes_secundarios JSONB NOT NULL DEFAULT '[]'::jsonb,
    registro_crc TEXT,
    responsavel_tecnico_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    vigente_de DATE NOT NULL,
    vigente_ate DATE,
    fonte_chave TEXT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vigente_ate IS NULL OR vigente_ate >= vigente_de)
);

-- Operacoes fiscais
CREATE TABLE IF NOT EXISTS erp.produto (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    codigo_interno TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    ncm TEXT,
    cest TEXT,
    origem TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.documento_fiscal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    tipo_documento TEXT NOT NULL CHECK (
        tipo_documento IN (
            'NFe', 'NFSe', 'CTe', 'NFe_compra', 'NFe_entrada_importacao',
            'NFCe_faixa', 'Fatura_energia', 'Fatura_telecom'
        )
    ),
    numero TEXT,
    serie TEXT,
    chave_acesso TEXT,
    data_emissao DATE NOT NULL,
    emitente_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    destinatario_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    natureza_operacao TEXT,
    valor_total_centavos BIGINT NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    doc_ref TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.documento_fiscal_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    documento_fiscal_id BIGINT NOT NULL REFERENCES erp.documento_fiscal(id),
    n_item INTEGER NOT NULL,
    produto_id BIGINT REFERENCES erp.produto(id),
    codigo_item_documento TEXT,
    descricao TEXT NOT NULL,
    ncm_hs TEXT,
    cfop TEXT,
    cst_csosn TEXT,
    unidade TEXT,
    quantidade_micro BIGINT,
    valor_unitario_micro BIGINT,
    valor_total_centavos BIGINT NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'BRL'
);

CREATE TABLE IF NOT EXISTS erp.item_tributo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    item_id BIGINT REFERENCES erp.documento_fiscal_item(id),
    documento_fiscal_id BIGINT NOT NULL REFERENCES erp.documento_fiscal(id),
    tributo TEXT NOT NULL,
    base_centavos BIGINT,
    aliquota_micro BIGINT,
    aliquota_texto TEXT,
    valor_centavos BIGINT NOT NULL
);

-- Operacoes financeiras
CREATE TABLE IF NOT EXISTS erp.movimento_bancario (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    conta_bancaria_id BIGINT NOT NULL REFERENCES erp.conta_bancaria(id),
    data_movimento DATE NOT NULL,
    historico TEXT NOT NULL,
    doc_ref TEXT NOT NULL,
    tipo_dc TEXT NOT NULL CHECK (tipo_dc IN ('D', 'C')),
    valor_centavos BIGINT NOT NULL CHECK (valor_centavos >= 0),
    saldo_apos_centavos BIGINT NOT NULL,
    origem_saldo TEXT NOT NULL CHECK (origem_saldo IN ('impresso', 'calculado_formula')),
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.comprovante (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    subtipo TEXT NOT NULL,
    data_operacao DATE NOT NULL,
    valor_centavos BIGINT NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    contraparte_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    doc_ref TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.titulo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    subtipo TEXT NOT NULL CHECK (subtipo IN ('Boleto_aluguel', 'Boleto_condominio', 'Duplicata')),
    numero TEXT,
    data_vencimento DATE,
    valor_centavos BIGINT NOT NULL,
    beneficiario_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    doc_ref TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.cambio (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    contrato_numero TEXT NOT NULL,
    data_contratacao DATE NOT NULL,
    moeda_estrangeira TEXT NOT NULL,
    valor_estrangeiro_centavos BIGINT NOT NULL,
    taxa_micro BIGINT NOT NULL,
    taxa_texto TEXT NOT NULL,
    principal_brl_centavos BIGINT NOT NULL,
    iof_centavos BIGINT,
    tarifa_centavos BIGINT,
    valor_total_brl_centavos BIGINT NOT NULL,
    exportador_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    invoice_numero TEXT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.contrato_credito (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    numero_contrato TEXT NOT NULL,
    data_contratacao DATE NOT NULL,
    principal_centavos BIGINT NOT NULL,
    taxa_juros_texto TEXT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.parcela (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    contrato_id BIGINT NOT NULL REFERENCES erp.contrato_credito(id),
    numero_parcela INTEGER NOT NULL,
    data_vencimento DATE NOT NULL,
    amortizacao_centavos BIGINT NOT NULL,
    juros_centavos BIGINT NOT NULL,
    total_centavos BIGINT NOT NULL,
    situacao TEXT
);

CREATE TABLE IF NOT EXISTS erp.liquidacao_cartao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    data_liquidacao DATE NOT NULL,
    valor_bruto_centavos BIGINT NOT NULL,
    taxa_centavos BIGINT,
    valor_liquido_centavos BIGINT NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.liquidacao_cartao_venda (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    liquidacao_id BIGINT NOT NULL REFERENCES erp.liquidacao_cartao(id),
    data_venda DATE,
    autorizacao TEXT,
    modalidade TEXT,
    parcela_texto TEXT,
    valor_bruto_centavos BIGINT NOT NULL,
    valor_liquido_centavos BIGINT
);

-- Tributario e aduaneiro
CREATE TABLE IF NOT EXISTS erp.guia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    tipo_guia TEXT NOT NULL,
    competencia TEXT,
    data_vencimento DATE,
    valor_principal_centavos BIGINT NOT NULL,
    valor_total_centavos BIGINT NOT NULL,
    uf TEXT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.guia_composicao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    guia_id BIGINT NOT NULL REFERENCES erp.guia(id),
    tributo_codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor_centavos BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS erp.apuracao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    tipo_apuracao TEXT NOT NULL,
    competencia TEXT NOT NULL,
    receita_bruta_centavos BIGINT,
    rbt12_centavos BIGINT,
    tributo_apurado_centavos BIGINT NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.di (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    numero_di TEXT NOT NULL,
    data_registro DATE NOT NULL,
    moeda TEXT NOT NULL DEFAULT 'USD',
    taxa_micro BIGINT NOT NULL,
    taxa_texto TEXT NOT NULL,
    valor_fob_moeda_centavos BIGINT NOT NULL,
    frete_seguro_moeda_centavos BIGINT,
    valor_aduaneiro_brl_centavos BIGINT NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.di_adicao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    di_id BIGINT NOT NULL REFERENCES erp.di(id),
    numero_adicao TEXT NOT NULL,
    ncm TEXT NOT NULL,
    valor_aduaneiro_centavos BIGINT NOT NULL,
    ii_centavos BIGINT NOT NULL,
    ipi_centavos BIGINT NOT NULL,
    pis_imp_centavos BIGINT NOT NULL,
    cofins_imp_centavos BIGINT NOT NULL
);

-- Controle interno
CREATE TABLE IF NOT EXISTS erp.fechamento_caixa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    data_fechamento DATE NOT NULL,
    valor_total_centavos BIGINT NOT NULL,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.fechamento_caixa_dia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    fechamento_id BIGINT NOT NULL REFERENCES erp.fechamento_caixa(id),
    data_dia DATE NOT NULL,
    valor_centavos BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS erp.memorando (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    data_memorando DATE NOT NULL,
    assunto TEXT NOT NULL,
    valor_centavos BIGINT,
    doc_ref TEXT
);

CREATE TABLE IF NOT EXISTS erp.recibo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    subtipo TEXT NOT NULL CHECK (subtipo IN ('aluguel', 'retirada_socio', 'prolabore', 'autonomo')),
    data_recibo DATE NOT NULL,
    competencia TEXT,
    beneficiario_pessoa_id BIGINT REFERENCES erp.pessoa(id),
    valor_centavos BIGINT NOT NULL,
    doc_ref TEXT
);

-- Contabil e estoques (multi-empresa)
CREATE TABLE IF NOT EXISTS erp.conta_contabil (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    grupo INTEGER NOT NULL,
    natureza TEXT CHECK (natureza IN ('D', 'C') OR natureza IS NULL)
);

CREATE TABLE IF NOT EXISTS erp.lancamento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    ano INTEGER NOT NULL,
    numero_lancamento INTEGER NOT NULL,
    data_lancamento DATE NOT NULL,
    historico TEXT NOT NULL,
    tag_ref TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, ano, numero_lancamento)
);

CREATE TABLE IF NOT EXISTS erp.partida (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    lancamento_id BIGINT NOT NULL REFERENCES erp.lancamento(id),
    ordem INTEGER NOT NULL,
    conta_id BIGINT NOT NULL REFERENCES erp.conta_contabil(id),
    dc TEXT NOT NULL CHECK (dc IN ('D', 'C')),
    valor_centavos BIGINT NOT NULL CHECK (valor_centavos >= 0)
);

CREATE TABLE IF NOT EXISTS erp.saldo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    conta_id BIGINT NOT NULL REFERENCES erp.conta_contabil(id),
    periodo TEXT NOT NULL,
    fonte TEXT NOT NULL,
    saldo_anterior_centavos BIGINT,
    debito_centavos BIGINT,
    credito_centavos BIGINT,
    saldo_atual_centavos BIGINT NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.ciclo_importacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT REFERENCES erp.empresa(id),
    cambio_doc_ref TEXT NOT NULL,
    data_cambio DATE NOT NULL,
    data_entrada_estoque DATE,
    pais_origem TEXT,
    principal_brl_centavos BIGINT,
    iof_centavos BIGINT
);

CREATE TABLE IF NOT EXISTS erp.estoque_movimento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    produto_id BIGINT NOT NULL REFERENCES erp.produto(id),
    ciclo_importacao_id BIGINT REFERENCES erp.ciclo_importacao(id),
    tipo_movimento TEXT NOT NULL CHECK (tipo_movimento IN ('abertura', 'entrada_importacao', 'saida_nfe', 'saldo_mensal')),
    data_movimento DATE NOT NULL,
    quantidade INTEGER NOT NULL,
    custo_unitario_centavos BIGINT,
    valor_total_centavos BIGINT
);

-- Transacao (multi-empresa)
CREATE TABLE IF NOT EXISTS erp.transacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    regra_agrupamento TEXT NOT NULL CHECK (regra_agrupamento IN ('doc_ref_unico', 'recorrente_mensal', 'nfe_vinculada', 'avulso')),
    doc_ref TEXT,
    estabelecimento_id BIGINT REFERENCES erp.estabelecimento(id),
    ano_mes TEXT,
    data_referencia DATE,
    status_vinculo TEXT NOT NULL CHECK (status_vinculo IN ('ligado', 'ambiguo', 'sem_par')),
    origem_registro TEXT NOT NULL DEFAULT 'acervo_sigaa' CHECK (origem_registro IN ('acervo_sigaa', 'usuario'))
);

CREATE TABLE IF NOT EXISTS erp.transacao_membro (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    transacao_id BIGINT NOT NULL REFERENCES erp.transacao(id),
    tabela_membro TEXT NOT NULL,
    membro_chave TEXT NOT NULL,
    papel_membro TEXT NOT NULL,
    criterio_vinculo TEXT NOT NULL,
    UNIQUE (transacao_id, tabela_membro, membro_chave)
);

-- Curso
CREATE TABLE IF NOT EXISTS erp.dossie (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    codigo TEXT NOT NULL UNIQUE,
    titulo TEXT NOT NULL,
    periodo_texto TEXT,
    prazo_texto TEXT
);

CREATE TABLE IF NOT EXISTS erp.requisito (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    dossie_id BIGINT NOT NULL REFERENCES erp.dossie(id),
    codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    fonte_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS erp.material (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    dossie_id BIGINT REFERENCES erp.dossie(id),
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    arquivo_id BIGINT NOT NULL REFERENCES acervo.bru_arquivo(id)
);

CREATE TABLE IF NOT EXISTS erp.material_secao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    material_id BIGINT NOT NULL REFERENCES erp.material(id),
    ordem INTEGER NOT NULL,
    titulo TEXT,
    conteudo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS erp.devolutiva (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    dossie_id BIGINT NOT NULL REFERENCES erp.dossie(id),
    grupo TEXT NOT NULL,
    nossa_dupla BOOLEAN NOT NULL DEFAULT false,
    nota_texto TEXT,
    resumo TEXT,
    material_id BIGINT NOT NULL REFERENCES erp.material(id)
);

CREATE TABLE IF NOT EXISTS erp.nota_didatica (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    origem_chave TEXT NOT NULL,
    texto TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS erp.tema (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    termo TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS erp.vinculo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    tema_id BIGINT NOT NULL REFERENCES erp.tema(id),
    alvo_tabela TEXT NOT NULL,
    alvo_chave TEXT NOT NULL,
    criterio TEXT NOT NULL
);

-- Tabelas estruturantes do Dossie 1 (trabalho da contadora sobre erp.empresa)
CREATE TABLE IF NOT EXISTS erp.d1_plano_cenario (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    codigo_cenario TEXT NOT NULL CHECK (codigo_cenario IN ('base', 'pessimista', 'otimista')),
    nome TEXT NOT NULL,
    tma_micro BIGINT NOT NULL DEFAULT 150000,
    ticket_medio_centavos BIGINT NOT NULL DEFAULT 150000,
    inadimplencia_micro BIGINT NOT NULL DEFAULT 50000,
    capex_centavos BIGINT NOT NULL DEFAULT 1000000,
    capital_giro_centavos BIGINT NOT NULL DEFAULT 3000000,
    premissas_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, codigo_cenario)
);

CREATE TABLE IF NOT EXISTS erp.d1_plano_projecao_mensal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    cenario_id BIGINT NOT NULL REFERENCES erp.d1_plano_cenario(id),
    mes_ordem INTEGER NOT NULL CHECK (mes_ordem BETWEEN 1 AND 36),
    competencia_ym TEXT NOT NULL,
    clientes_ativos INTEGER NOT NULL CHECK (clientes_ativos >= 0),
    receita_bruta_centavos BIGINT NOT NULL,
    prolabore_centavos BIGINT NOT NULL,
    folha_clt_centavos BIGINT NOT NULL DEFAULT 0,
    rbt12_centavos BIGINT NOT NULL,
    fator_r_micro BIGINT NOT NULL,
    anexo_simples TEXT NOT NULL CHECK (anexo_simples IN ('Anexo_III', 'Anexo_V')),
    aliquota_efetiva_micro BIGINT NOT NULL,
    das_centavos BIGINT NOT NULL,
    custos_fixos_centavos BIGINT NOT NULL,
    custos_detalhe_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    inadimplencia_centavos BIGINT NOT NULL DEFAULT 0,
    lucro_liquido_centavos BIGINT NOT NULL,
    fluxo_caixa_centavos BIGINT NOT NULL,
    saldo_caixa_centavos BIGINT NOT NULL,
    UNIQUE (cenario_id, mes_ordem)
);

CREATE TABLE IF NOT EXISTS erp.d1_clausula_societaria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    bloco TEXT NOT NULL,
    codigo_criterio TEXT NOT NULL,
    titulo TEXT NOT NULL,
    regra_texto TEXT NOT NULL,
    aplica_mou BOOLEAN NOT NULL DEFAULT true,
    aplica_contrato BOOLEAN NOT NULL DEFAULT true,
    clausula_mou TEXT,
    clausula_contrato TEXT,
    versao INTEGER NOT NULL DEFAULT 1 CHECK (versao >= 1),
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS erp.d1_fluxo_etapa (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    codigo TEXT NOT NULL,
    nome_etapa TEXT NOT NULL,
    orgao TEXT NOT NULL,
    portal_url TEXT,
    data_consulta DATE,
    entrada_docs TEXT NOT NULL,
    saida_doc TEXT NOT NULL,
    regra_retorno_exigencia TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'em_andamento', 'concluida', 'exigencia')),
    protocolo_simulado TEXT,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, ordem)
);

CREATE TABLE IF NOT EXISTS erp.d1_pesquisa_resposta (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    numero_questao INTEGER NOT NULL CHECK (numero_questao BETWEEN 1 AND 10),
    enunciado TEXT NOT NULL,
    resposta_autoral TEXT NOT NULL,
    norma_citada TEXT NOT NULL,
    link_oficial TEXT NOT NULL,
    data_acesso DATE NOT NULL,
    origem_registro TEXT NOT NULL DEFAULT 'usuario' CHECK (origem_registro IN ('acervo_sigaa', 'usuario')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, numero_questao)
);

CREATE TABLE IF NOT EXISTS erp.d1_matriz_criterio (
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
-- SCHEMA: auditoria (Linhagem, Conferencias, Trabalho Humano, IABP e IA)
-- =============================================================================
CREATE TABLE IF NOT EXISTS auditoria.evidencia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    tabela_destino TEXT NOT NULL,
    registro_chave TEXT NOT NULL,
    bru_tabela TEXT NOT NULL CHECK (bru_tabela IN ('bru_arquivo', 'bru_linha', 'bru_celula', 'bru_paragrafo')),
    bru_chave TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auditoria.conferencia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    regra TEXT NOT NULL,
    severidade TEXT NOT NULL CHECK (severidade IN ('info', 'alerta', 'divergencia', 'gate_ok', 'gate_falha')),
    registros_json JSONB NOT NULL,
    valores_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('aberto', 'ok', 'registrado')),
    descricao TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auditoria.anotacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    alvo_tabela TEXT NOT NULL,
    alvo_chave TEXT NOT NULL,
    autor TEXT NOT NULL,
    dossie TEXT,
    conteudo TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auditoria.decisao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    dossie TEXT NOT NULL,
    alvo_chave TEXT,
    titulo TEXT NOT NULL,
    justificativa TEXT NOT NULL,
    fonte_oficial TEXT,
    autor TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auditoria.classificacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    alvo_tabela TEXT NOT NULL,
    alvo_chave TEXT NOT NULL,
    categoria TEXT NOT NULL,
    valor TEXT NOT NULL,
    observacao TEXT,
    autor TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auditoria.resposta_requisito (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    requisito_id BIGINT REFERENCES erp.requisito(id),
    requisito_chave TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pendente', 'rascunho', 'revisado', 'entregue')),
    resposta_md TEXT NOT NULL,
    evidencias_chaves_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auditoria.avaliacao_iabp (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    empresa_id BIGINT NOT NULL REFERENCES erp.empresa(id),
    criterio_id BIGINT NOT NULL REFERENCES erp.d1_matriz_criterio(id),
    nota INTEGER CHECK (nota BETWEEN 0 AND 4),
    nao_aplicavel BOOLEAN NOT NULL DEFAULT false,
    referencia_localizacao TEXT,
    observacao TEXT,
    autor TEXT NOT NULL DEFAULT 'G07',
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, criterio_id)
);

CREATE TABLE IF NOT EXISTS auditoria.diario_ia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    dossie TEXT NOT NULL CHECK (dossie IN ('D1', 'D2', 'D3', 'D4')),
    empresa_id BIGINT REFERENCES erp.empresa(id),
    finalidade TEXT NOT NULL,
    prompt_resumo TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    revisao_humana TEXT NOT NULL,
    autor TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- INDICES EXPLICITOS EM 100% DAS FOREIGN KEYS E CHAVES DE CONSULTA
-- =============================================================================
-- acervo
CREATE INDEX IF NOT EXISTS idx_bru_arquivo_sha256 ON acervo.bru_arquivo(sha256);
CREATE INDEX IF NOT EXISTS idx_bru_arquivo_papel ON acervo.bru_arquivo(papel_acervo);
CREATE INDEX IF NOT EXISTS idx_bru_arquivo_zip_origem ON acervo.bru_arquivo(zip_origem_id);
CREATE INDEX IF NOT EXISTS idx_bru_arquivo_duplicata ON acervo.bru_arquivo(duplicata_de_id);
CREATE INDEX IF NOT EXISTS idx_bru_zip_entrada_zip ON acervo.bru_zip_entrada(zip_arquivo_id);
CREATE INDEX IF NOT EXISTS idx_bru_zip_entrada_disco ON acervo.bru_zip_entrada(arquivo_disco_id);
CREATE INDEX IF NOT EXISTS idx_bru_linha_arq_dest ON acervo.bru_linha(arquivo_id, destino);
CREATE INDEX IF NOT EXISTS idx_bru_celula_arq_dest ON acervo.bru_celula(arquivo_id, destino);
CREATE INDEX IF NOT EXISTS idx_bru_paragrafo_arq_dest ON acervo.bru_paragrafo(arquivo_id, destino);
CREATE INDEX IF NOT EXISTS idx_bru_sigaa_item_arq ON acervo.bru_sigaa_item(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_documento_arq ON acervo.ext_documento(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_documento_docref ON acervo.ext_documento(doc_ref);
CREATE INDEX IF NOT EXISTS idx_ext_campo_doc ON acervo.ext_campo(documento_id);
CREATE INDEX IF NOT EXISTS idx_ext_campo_lin ON acervo.ext_campo(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_item_doc ON acervo.ext_item(documento_id);
CREATE INDEX IF NOT EXISTS idx_ext_item_lin ON acervo.ext_item(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_extrato_arq ON acervo.ext_extrato_linha(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_extrato_cel ON acervo.ext_extrato_linha(celula_saldo_id);
CREATE INDEX IF NOT EXISTS idx_ext_diario_lanc_arq ON acervo.ext_diario_lancamento(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_diario_lanc_lin ON acervo.ext_diario_lancamento(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_diario_part_lanc ON acervo.ext_diario_partida(lancamento_id);
CREATE INDEX IF NOT EXISTS idx_ext_diario_part_lin ON acervo.ext_diario_partida(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_razao_arq ON acervo.ext_razao_linha(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_razao_lin ON acervo.ext_razao_linha(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_bal_arq ON acervo.ext_balancete_linha(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_bal_cel ON acervo.ext_balancete_linha(celula_id);
CREATE INDEX IF NOT EXISTS idx_ext_bal_lin ON acervo.ext_balancete_linha(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_estq_arq ON acervo.ext_estoque_linha(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_estq_cel ON acervo.ext_estoque_linha(celula_id);
CREATE INDEX IF NOT EXISTS idx_ext_param_arq ON acervo.ext_parametro_planilha(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_param_cel ON acervo.ext_parametro_planilha(celula_id);
CREATE INDEX IF NOT EXISTS idx_ext_material_arq ON acervo.ext_material(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_secao_mat ON acervo.ext_secao(material_id);
CREATE INDEX IF NOT EXISTS idx_ext_secao_par ON acervo.ext_secao(paragrafo_id);
CREATE INDEX IF NOT EXISTS idx_ext_secao_lin ON acervo.ext_secao(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_nota_arq ON acervo.ext_nota_didatica(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_ext_nota_doc ON acervo.ext_nota_didatica(documento_id);
CREATE INDEX IF NOT EXISTS idx_ext_nota_lin ON acervo.ext_nota_didatica(linha_bruto_id);
CREATE INDEX IF NOT EXISTS idx_ext_nota_cel ON acervo.ext_nota_didatica(celula_id);
CREATE INDEX IF NOT EXISTS idx_ext_nota_par ON acervo.ext_nota_didatica(paragrafo_id);

-- erp
CREATE INDEX IF NOT EXISTS idx_erp_pess_id_pessoa ON erp.pessoa_identificador(pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_pess_oc_pessoa ON erp.pessoa_ocorrencia(pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_empresa_pessoa ON erp.empresa(pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_rel_escr ON erp.relacao_escritorio_cliente(escritorio_empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_rel_cli ON erp.relacao_escritorio_cliente(cliente_empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_estab_emp ON erp.estabelecimento(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_ctabco_emp ON erp.conta_bancaria(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_ctabco_estab ON erp.conta_bancaria(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_evento_emp ON erp.evento(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_fato_evento ON erp.fato(evento_id);
CREATE INDEX IF NOT EXISTS idx_erp_fato_sujeito ON erp.fato(sujeito_chave, vigente_de);
CREATE INDEX IF NOT EXISTS idx_erp_part_soc_emp ON erp.participacao_societaria(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_part_soc_pes ON erp.participacao_societaria(socio_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_enq_emp ON erp.enquadramento_historico(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_enq_rt ON erp.enquadramento_historico(responsavel_tecnico_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_df_estab ON erp.documento_fiscal(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_df_emit ON erp.documento_fiscal(emitente_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_df_dest ON erp.documento_fiscal(destinatario_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_dfi_df ON erp.documento_fiscal_item(documento_fiscal_id);
CREATE INDEX IF NOT EXISTS idx_erp_dfi_prod ON erp.documento_fiscal_item(produto_id);
CREATE INDEX IF NOT EXISTS idx_erp_itrib_item ON erp.item_tributo(item_id);
CREATE INDEX IF NOT EXISTS idx_erp_itrib_df ON erp.item_tributo(documento_fiscal_id);
CREATE INDEX IF NOT EXISTS idx_erp_mov_cta ON erp.movimento_bancario(conta_bancaria_id);
CREATE INDEX IF NOT EXISTS idx_erp_comp_estab ON erp.comprovante(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_comp_cp ON erp.comprovante(contraparte_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_tit_estab ON erp.titulo(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_tit_ben ON erp.titulo(beneficiario_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_camb_estab ON erp.cambio(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_camb_exp ON erp.cambio(exportador_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_ccred_emp ON erp.contrato_credito(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_parc_ctr ON erp.parcela(contrato_id);
CREATE INDEX IF NOT EXISTS idx_erp_lqc_estab ON erp.liquidacao_cartao(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_lqcv_liq ON erp.liquidacao_cartao_venda(liquidacao_id);
CREATE INDEX IF NOT EXISTS idx_erp_guia_estab ON erp.guia(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_gcomp_guia ON erp.guia_composicao(guia_id);
CREATE INDEX IF NOT EXISTS idx_erp_apur_emp ON erp.apuracao(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_di_estab ON erp.di(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_diad_di ON erp.di_adicao(di_id);
CREATE INDEX IF NOT EXISTS idx_erp_fcaixa_estab ON erp.fechamento_caixa(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_fcaixad_fc ON erp.fechamento_caixa_dia(fechamento_id);
CREATE INDEX IF NOT EXISTS idx_erp_memo_estab ON erp.memorando(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_rec_estab ON erp.recibo(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_rec_ben ON erp.recibo(beneficiario_pessoa_id);
CREATE INDEX IF NOT EXISTS idx_erp_lanc_emp ON erp.lancamento(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_part_lanc ON erp.partida(lancamento_id);
CREATE INDEX IF NOT EXISTS idx_erp_part_cta ON erp.partida(conta_id);
CREATE INDEX IF NOT EXISTS idx_erp_saldo_emp ON erp.saldo(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_saldo_cta ON erp.saldo(conta_id);
CREATE INDEX IF NOT EXISTS idx_erp_ciclo_emp ON erp.ciclo_importacao(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_estqmov_emp ON erp.estoque_movimento(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_estqmov_prod ON erp.estoque_movimento(produto_id);
CREATE INDEX IF NOT EXISTS idx_erp_estqmov_ciclo ON erp.estoque_movimento(ciclo_importacao_id);
CREATE INDEX IF NOT EXISTS idx_erp_tx_emp ON erp.transacao(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_tx_estab ON erp.transacao(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_erp_tx_docref ON erp.transacao(doc_ref);
CREATE INDEX IF NOT EXISTS idx_erp_txm_tx ON erp.transacao_membro(transacao_id);
CREATE INDEX IF NOT EXISTS idx_erp_req_dos ON erp.requisito(dossie_id);
CREATE INDEX IF NOT EXISTS idx_erp_mat_dos ON erp.material(dossie_id);
CREATE INDEX IF NOT EXISTS idx_erp_mat_arq ON erp.material(arquivo_id);
CREATE INDEX IF NOT EXISTS idx_erp_matsec_mat ON erp.material_secao(material_id);
CREATE INDEX IF NOT EXISTS idx_erp_dev_dos ON erp.devolutiva(dossie_id);
CREATE INDEX IF NOT EXISTS idx_erp_dev_mat ON erp.devolutiva(material_id);
CREATE INDEX IF NOT EXISTS idx_erp_vinc_tema ON erp.vinculo(tema_id);
CREATE INDEX IF NOT EXISTS idx_erp_d1cen_emp ON erp.d1_plano_cenario(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_d1proj_cen ON erp.d1_plano_projecao_mensal(cenario_id);
CREATE INDEX IF NOT EXISTS idx_erp_d1clau_emp ON erp.d1_clausula_societaria(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_d1flux_emp ON erp.d1_fluxo_etapa(empresa_id);
CREATE INDEX IF NOT EXISTS idx_erp_d1pesq_emp ON erp.d1_pesquisa_resposta(empresa_id);

-- auditoria
CREATE INDEX IF NOT EXISTS idx_aud_ev_reg ON auditoria.evidencia(tabela_destino, registro_chave);
CREATE INDEX IF NOT EXISTS idx_aud_respreq_req ON auditoria.resposta_requisito(requisito_id);
CREATE INDEX IF NOT EXISTS idx_aud_iabp_emp ON auditoria.avaliacao_iabp(empresa_id);
CREATE INDEX IF NOT EXISTS idx_aud_iabp_crit ON auditoria.avaliacao_iabp(criterio_id);
CREATE INDEX IF NOT EXISTS idx_aud_ia_emp ON auditoria.diario_ia(empresa_id);

-- =============================================================================
-- TRIGGERS: atualizado_em + INTEGRIDADE DE PARTIDAS DOBRADAS NO COMMIT
-- =============================================================================
DO $$
DECLARE
    t TEXT;
    tabelas_ts TEXT[] := ARRAY[
        'erp.pessoa', 'erp.pessoa_identificador', 'erp.empresa',
        'erp.relacao_escritorio_cliente', 'erp.estabelecimento', 'erp.conta_bancaria',
        'erp.evento', 'erp.fato', 'erp.participacao_societaria', 'erp.enquadramento_historico',
        'erp.documento_fiscal', 'erp.lancamento', 'erp.d1_plano_cenario',
        'erp.d1_clausula_societaria', 'erp.d1_fluxo_etapa', 'erp.d1_pesquisa_resposta'
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

CREATE OR REPLACE FUNCTION auditoria.fn_validar_partidas_dobradas()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_lanc_id BIGINT;
    v_cnt BIGINT;
    v_deb BIGINT;
    v_cred BIGINT;
BEGIN
    v_lanc_id := COALESCE(NEW.lancamento_id, OLD.lancamento_id);
    IF v_lanc_id IS NULL THEN
        RETURN NULL;
    END IF;
    SELECT
        COUNT(*),
        COALESCE(SUM(CASE WHEN dc = 'D' THEN valor_centavos ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN dc = 'C' THEN valor_centavos ELSE 0 END), 0)
    INTO v_cnt, v_deb, v_cred
    FROM erp.partida
    WHERE lancamento_id = v_lanc_id;

    IF v_cnt > 0 AND v_deb <> v_cred THEN
        RAISE EXCEPTION 'Integridade contabil violada: lancamento_id=% desbalanceado no COMMIT (Debito=% <> Credito=%)',
            v_lanc_id, v_deb, v_cred;
    END IF;
    RETURN NULL;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_validar_partidas_dobradas') THEN
        CREATE CONSTRAINT TRIGGER trg_validar_partidas_dobradas
        AFTER INSERT OR UPDATE OR DELETE ON erp.partida
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION auditoria.fn_validar_partidas_dobradas();
    END IF;
END $$;
