-- Camada 1: Bruto (copia fiel e imutavel do acervo)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS bru_arquivo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- Chave estavel: arq:<caminho_relativo>
    caminho_relativo TEXT NOT NULL UNIQUE, -- Caminho POSIX relativo a ACERVO_DIR
    nome TEXT NOT NULL, -- Nome do arquivo com extensao
    extensao TEXT NOT NULL, -- Extensao em minusculas (ex.: .pdf, .xlsx, .2026)
    sha256 TEXT NOT NULL, -- Hash SHA-256 em hexadecimal
    tamanho_bytes INTEGER NOT NULL CHECK (tamanho_bytes >= 0),
    dossie TEXT NOT NULL CHECK (dossie IN ('D1', 'D2', 'D3', 'D4', 'Resultado', '_paginas')),
    dominio TEXT NOT NULL CHECK (dominio IN ('empresa', 'curso', 'misto')),
    papel_acervo TEXT NOT NULL CHECK (
        papel_acervo IN (
            'primario',
            'container_zip',
            'duplicata_sha256',
            'consolidado_espelho',
            'formato_espelho'
        )
    ),
    zip_origem_id INTEGER REFERENCES bru_arquivo(id), -- ZIP que originou este arquivo no disco
    duplicata_de_id INTEGER REFERENCES bru_arquivo(id), -- Arquivo primario identico por sha256
    paginas_total INTEGER CHECK (paginas_total IS NULL OR paginas_total >= 0)
);

CREATE TABLE IF NOT EXISTS bru_zip_entrada (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- Chave estavel: zip:<caminho_zip>:<caminho_interno>
    zip_arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    caminho_interno TEXT NOT NULL, -- Caminho interno no arquivo ZIP
    tamanho_bytes INTEGER NOT NULL CHECK (tamanho_bytes >= 0),
    crc32 INTEGER NOT NULL,
    sha256 TEXT NOT NULL, -- Hash SHA-256 do conteudo descompactado
    arquivo_disco_id INTEGER REFERENCES bru_arquivo(id), -- Arquivo correspondente extraido no disco
    UNIQUE (zip_arquivo_id, caminho_interno)
);

CREATE TABLE IF NOT EXISTS bru_linha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- Chave estavel: lin:<caminho_relativo>:<pagina>:<n_linha>
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    pagina INTEGER NOT NULL CHECK (pagina >= 1),
    n_linha INTEGER NOT NULL CHECK (n_linha >= 1),
    texto TEXT NOT NULL, -- Texto exato extraido via pymupdf
    eh_marca_dagua INTEGER NOT NULL DEFAULT 0 CHECK (eh_marca_dagua IN (0, 1)),
    destino TEXT, -- Identificador do consumidor na Camada 2 (NULL = nao consumida)
    UNIQUE (arquivo_id, pagina, n_linha)
);

CREATE TABLE IF NOT EXISTS bru_celula (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- Chave estavel: cel:<caminho_relativo>:<aba>:<endereco>
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    aba TEXT NOT NULL, -- Nome exato da aba da planilha
    ordem_aba INTEGER NOT NULL CHECK (ordem_aba >= 1),
    linha INTEGER NOT NULL CHECK (linha >= 1),
    coluna INTEGER NOT NULL CHECK (coluna >= 1),
    endereco TEXT NOT NULL, -- Endereco A1 (ex.: F6)
    tipo_dado TEXT NOT NULL CHECK (tipo_dado IN ('texto', 'numero', 'data', 'formula', 'booleano', 'vazio')),
    valor_texto TEXT, -- Representacao textual exata (ISO-8601 se data)
    valor_cacheado TEXT, -- Valor cacheado no XML (<v>); NULL quando ausente
    formula TEXT, -- Formula original comecando com '='
    formato_numero TEXT, -- number_format da celula no Excel
    destino TEXT, -- Consumidor na Camada 2
    UNIQUE (arquivo_id, aba, endereco)
);

CREATE TABLE IF NOT EXISTS bru_paragrafo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- Chave estavel: par:<caminho_relativo>:<ordem>
    arquivo_id INTEGER NOT NULL REFERENCES bru_arquivo(id),
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    origem_bloco TEXT NOT NULL CHECK (origem_bloco IN ('paragrafo', 'tabela_celula', 'html_bloco', 'txt_linha')),
    tabela_idx INTEGER, -- Indice 1-based da tabela quando origem_bloco = tabela_celula
    linha_idx INTEGER, -- Indice 1-based da linha na tabela
    coluna_idx INTEGER, -- Indice 1-based da coluna na tabela
    estilo TEXT, -- Nome do estilo do paragrafo ou tag HTML
    texto TEXT NOT NULL, -- Texto integral do bloco
    destino TEXT, -- Consumidor na Camada 2
    UNIQUE (arquivo_id, ordem)
);

CREATE TABLE IF NOT EXISTS bru_sigaa_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE, -- Chave estavel: sigaa:<ordem>
    ordem INTEGER NOT NULL UNIQUE CHECK (ordem >= 1),
    status_fetch TEXT NOT NULL, -- '200' ou 'ERRO' conforme _relatorio.txt
    content_type TEXT, -- Content-Type retornado quando status 200
    bytes_fetch INTEGER, -- Tamanho em bytes retornado quando status 200
    rotulo_sigaa TEXT NOT NULL, -- Rotulo/nome exibido na linha do _relatorio.txt
    link_texto TEXT, -- Texto do link quando status 200
    dossie_inferido TEXT CHECK (dossie_inferido IN ('D1', 'D2', 'D3', 'D4', 'Resultado', '_paginas')),
    arquivo_id INTEGER REFERENCES bru_arquivo(id), -- Arquivo correspondente no acervo local
    observacao TEXT -- Ex.: 'duplicata_no_relatorio', 'pagina_vazia_sigaa'
);

CREATE INDEX IF NOT EXISTS idx_bru_arquivo_sha256 ON bru_arquivo(sha256);
CREATE INDEX IF NOT EXISTS idx_bru_arquivo_papel ON bru_arquivo(papel_acervo);
CREATE INDEX IF NOT EXISTS idx_bru_linha_arq_dest ON bru_linha(arquivo_id, destino);
CREATE INDEX IF NOT EXISTS idx_bru_celula_arq_dest ON bru_celula(arquivo_id, destino);
CREATE INDEX IF NOT EXISTS idx_bru_paragrafo_arq_dest ON bru_paragrafo(arquivo_id, destino);
