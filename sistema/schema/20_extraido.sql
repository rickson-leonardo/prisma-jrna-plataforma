-- Camada 2: Extraido (fiel ao formato de cada fonte, antes da normalizacao 3FN)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ext_documento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: extdoc:<caminho_relativo>:<pagina_inicio>
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    modelo TEXT NOT NULL, -- Nome canonico do modelo (ex.: NFe, Contrato-cambio)
    tipo TEXT NOT NULL, -- Categoria macro do documento
    numero TEXT, -- Numero impresso do documento
    serie TEXT,
    data_emissao TEXT, -- ISO-8601
    data_referencia TEXT, -- Data do pacote / movimento (ISO-8601)
    doc_ref TEXT, -- Chave comum Doc/Ref (ex.: TRF106997, BOL005)
    estabelecimento_prefixo TEXT, -- M, F, G, NF ou NULL
    valor_total_centavos INTEGER,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    valor_total_texto TEXT
);

CREATE TABLE IF NOT EXISTS ext_campo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    documento_id INTEGER NOT NULL REFERENCES ext_documento(id),
    secao TEXT,
    rotulo TEXT NOT NULL,
    valor_texto TEXT NOT NULL,
    valor_centavos INTEGER,
    moeda TEXT,
    valor_micro INTEGER, -- Escala 10^-6 para taxas, aliquotas e quantidades fracionarias
    valor_data TEXT, -- ISO-8601
    linha_bruto_id INTEGER REFERENCES bru_linha(id)
);

CREATE TABLE IF NOT EXISTS ext_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    documento_id INTEGER NOT NULL REFERENCES ext_documento(id),
    tabela TEXT NOT NULL, -- Nome logico da tabela no documento
    n_linha INTEGER NOT NULL CHECK (n_linha >= 1),
    colunas_json TEXT NOT NULL, -- JSON com o texto exato das colunas
    linha_bruto_id INTEGER REFERENCES bru_linha(id),
    UNIQUE (documento_id, tabela, n_linha)
);

CREATE TABLE IF NOT EXISTS ext_extrato_linha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: extmov:<conta>:<aba>:<n_linha>
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    aba TEXT NOT NULL,
    n_linha INTEGER NOT NULL,
    conta_codigo TEXT NOT NULL, -- matriz_2025, matriz_2026, filial, goiania
    data_movimento TEXT NOT NULL, -- ISO-8601
    historico TEXT NOT NULL,
    doc_ref TEXT NOT NULL,
    debito_centavos INTEGER,
    credito_centavos INTEGER,
    saldo_centavos INTEGER NOT NULL,
    origem_valor TEXT NOT NULL CHECK (origem_valor IN ('impresso', 'calculado_formula')),
    celula_saldo_id INTEGER REFERENCES bru_celula(id)
);

CREATE TABLE IF NOT EXISTS ext_diario_lancamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- ex.: extlanc:2025:0001
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    ano INTEGER NOT NULL,
    numero_lancamento INTEGER NOT NULL,
    data_lancamento TEXT NOT NULL, -- ISO-8601
    historico TEXT NOT NULL,
    tag_ref TEXT, -- Tag extraida de [TAG] no historico (ex.: NF-e 1243, TRF106997)
    linha_bruto_id INTEGER REFERENCES bru_linha(id),
    UNIQUE (ano, numero_lancamento)
);

CREATE TABLE IF NOT EXISTS ext_diario_partida (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    lancamento_id INTEGER NOT NULL REFERENCES ext_diario_lancamento(id),
    ordem INTEGER NOT NULL,
    conta_codigo TEXT NOT NULL,
    conta_nome TEXT NOT NULL,
    dc TEXT NOT NULL CHECK (dc IN ('D', 'C')),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
    valor_texto TEXT NOT NULL,
    linha_bruto_id INTEGER REFERENCES bru_linha(id),
    UNIQUE (lancamento_id, ordem)
);

CREATE TABLE IF NOT EXISTS ext_razao_linha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    ano INTEGER NOT NULL,
    conta_codigo TEXT NOT NULL,
    conta_nome TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    data_movimento TEXT,
    numero_lancamento INTEGER,
    historico TEXT NOT NULL,
    debito_centavos INTEGER,
    credito_centavos INTEGER,
    saldo_centavos INTEGER,
    saldo_dc TEXT CHECK (saldo_dc IN ('D', 'C', NULL)),
    linha_bruto_id INTEGER REFERENCES bru_linha(id)
);

CREATE TABLE IF NOT EXISTS ext_balancete_linha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    fonte TEXT NOT NULL CHECK (fonte IN ('pdf', 'xlsx')),
    periodo TEXT NOT NULL, -- ex.: 2024-12, 2025-01, 2025-12-antes, 2025-12-pos
    conta_codigo TEXT NOT NULL,
    conta_nome TEXT NOT NULL,
    saldo_anterior_centavos INTEGER NOT NULL,
    debito_centavos INTEGER NOT NULL,
    credito_centavos INTEGER NOT NULL,
    saldo_atual_centavos INTEGER NOT NULL,
    origem_valor TEXT NOT NULL CHECK (origem_valor IN ('impresso', 'calculado_formula')),
    celula_id INTEGER REFERENCES bru_celula(id),
    linha_bruto_id INTEGER REFERENCES bru_linha(id)
);

CREATE TABLE IF NOT EXISTS ext_estoque_linha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    aba TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    produto_codigo TEXT,
    descricao TEXT,
    dados_json TEXT NOT NULL,
    celula_id INTEGER REFERENCES bru_celula(id)
);

CREATE TABLE IF NOT EXISTS ext_parametro_planilha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    aba TEXT NOT NULL,
    rotulo TEXT NOT NULL,
    valor_texto TEXT NOT NULL,
    celula_id INTEGER REFERENCES bru_celula(id)
);

CREATE TABLE IF NOT EXISTS ext_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    dossie TEXT NOT NULL,
    categoria TEXT NOT NULL, -- plano_ensino, aula, matriz_requisitos, estudo_caso, devolutiva, orientacao, pagina_sigaa
    titulo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ext_secao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    material_id INTEGER NOT NULL REFERENCES ext_material(id),
    ordem INTEGER NOT NULL,
    titulo TEXT,
    conteudo TEXT NOT NULL,
    paragrafo_id INTEGER REFERENCES bru_paragrafo(id),
    linha_bruto_id INTEGER REFERENCES bru_linha(id)
);

CREATE TABLE IF NOT EXISTS ext_nota_didatica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    documento_id INTEGER REFERENCES ext_documento(id),
    texto TEXT NOT NULL,
    linha_bruto_id INTEGER REFERENCES bru_linha(id),
    celula_id INTEGER REFERENCES bru_celula(id),
    paragrafo_id INTEGER REFERENCES bru_paragrafo(id)
);
