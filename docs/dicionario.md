# Dicionário de Dados — Laboratório Contábil

Documento gerado automaticamente por `python -m sistema.gerar_docs` a partir do schema SQLite.

## Banco `laboratorio.db`

### `bru_arquivo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | Chave estavel: arq:<caminho_relativo> |
| `caminho_relativo` | `TEXT` | Sim |  | `` | Caminho POSIX relativo a ACERVO_DIR |
| `nome` | `TEXT` | Sim |  | `` | Nome do arquivo com extensao |
| `extensao` | `TEXT` | Sim |  | `` | Extensao em minusculas (ex.: .pdf, .xlsx, .2026) |
| `sha256` | `TEXT` | Sim |  | `` | Hash SHA-256 em hexadecimal |
| `tamanho_bytes` | `INTEGER` | Sim |  | `` |  |
| `dossie` | `TEXT` | Sim |  | `` |  |
| `dominio` | `TEXT` | Sim |  | `` |  |
| `papel_acervo` | `TEXT` | Sim |  | `` |  |
| `zip_origem_id` | `INTEGER` | Não |  | `bru_arquivo.id` | ZIP que originou este arquivo no disco |
| `duplicata_de_id` | `INTEGER` | Não |  | `bru_arquivo.id` | Arquivo primario identico por sha256 |
| `paginas_total` | `INTEGER` | Não |  | `` |  |

### `bru_celula`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | Chave estavel: cel:<caminho_relativo>:<aba>:<endereco> |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `aba` | `TEXT` | Sim |  | `` | Nome exato da aba da planilha |
| `ordem_aba` | `INTEGER` | Sim |  | `` |  |
| `linha` | `INTEGER` | Sim |  | `` |  |
| `coluna` | `INTEGER` | Sim |  | `` |  |
| `endereco` | `TEXT` | Sim |  | `` | Endereco A1 (ex.: F6) |
| `tipo_dado` | `TEXT` | Sim |  | `` |  |
| `valor_texto` | `TEXT` | Não |  | `` | Representacao textual exata (ISO-8601 se data) |
| `valor_cacheado` | `TEXT` | Não |  | `` | Valor cacheado no XML (<v>); NULL quando ausente |
| `formula` | `TEXT` | Não |  | `` | Formula original comecando com '=' |
| `formato_numero` | `TEXT` | Não |  | `` | number_format da celula no Excel |
| `destino` | `TEXT` | Não |  | `` | Consumidor na Camada 2 |

### `bru_linha`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | Chave estavel: lin:<caminho_relativo>:<pagina>:<n_linha> |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `pagina` | `INTEGER` | Sim |  | `` |  |
| `n_linha` | `INTEGER` | Sim |  | `` |  |
| `texto` | `TEXT` | Sim |  | `` | Texto exato extraido via pymupdf |
| `x0` | `REAL` | Sim |  | `` | Coordenada horizontal inicial (pt) |
| `y0` | `REAL` | Sim |  | `` | Coordenada vertical superior (pt) |
| `tam_fonte` | `REAL` | Sim |  | `` | Tamanho da fonte em pt |
| `fonte` | `TEXT` | Não |  | `` | Nome da fonte no PDF |
| `cor_hex` | `TEXT` | Não |  | `` | Cor RGB em hexadecimal (ex.: 0x1d2433, 0x5a6477) |
| `eh_marca_dagua` | `INTEGER` | Sim |  | `` |  |
| `destino` | `TEXT` | Não |  | `` | Identificador do consumidor na Camada 2 (NULL = nao consumida) |

### `bru_paragrafo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | Chave estavel: par:<caminho_relativo>:<ordem> |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `origem_bloco` | `TEXT` | Sim |  | `` |  |
| `tabela_idx` | `INTEGER` | Não |  | `` | Indice 1-based da tabela quando origem_bloco = tabela_celula |
| `linha_idx` | `INTEGER` | Não |  | `` | Indice 1-based da linha na tabela |
| `coluna_idx` | `INTEGER` | Não |  | `` | Indice 1-based da coluna na tabela |
| `estilo` | `TEXT` | Não |  | `` | Nome do estilo do paragrafo ou tag HTML |
| `texto` | `TEXT` | Sim |  | `` | Texto integral do bloco |
| `destino` | `TEXT` | Não |  | `` | Consumidor na Camada 2 |

### `bru_sigaa_item`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | Chave estavel: sigaa:<ordem> |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `status_fetch` | `TEXT` | Sim |  | `` | '200' ou 'ERRO' conforme _relatorio.txt |
| `content_type` | `TEXT` | Não |  | `` | Content-Type retornado quando status 200 |
| `bytes_fetch` | `INTEGER` | Não |  | `` | Tamanho em bytes retornado quando status 200 |
| `rotulo_sigaa` | `TEXT` | Sim |  | `` | Rotulo/nome exibido na linha do _relatorio.txt |
| `link_texto` | `TEXT` | Não |  | `` | Texto do link quando status 200 |
| `dossie_inferido` | `TEXT` | Não |  | `` |  |
| `arquivo_id` | `INTEGER` | Não |  | `bru_arquivo.id` | Arquivo correspondente no acervo local |
| `observacao` | `TEXT` | Não |  | `` | Ex.: 'duplicata_no_relatorio', 'pagina_vazia_sigaa' |

### `bru_zip_entrada`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | Chave estavel: zip:<caminho_zip>:<caminho_interno> |
| `zip_arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `caminho_interno` | `TEXT` | Sim |  | `` | Caminho interno no arquivo ZIP |
| `tamanho_bytes` | `INTEGER` | Sim |  | `` |  |
| `crc32` | `INTEGER` | Sim |  | `` |  |
| `sha256` | `TEXT` | Sim |  | `` | Hash SHA-256 do conteudo descompactado |
| `arquivo_disco_id` | `INTEGER` | Não |  | `bru_arquivo.id` | Arquivo correspondente extraido no disco |

### `conferencia`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `regra` | `TEXT` | Sim |  | `` | ex.: sigaa_html_vazio, cpf_divergente, saldo_divergente, gate_cobertura |
| `severidade` | `TEXT` | Sim |  | `` |  |
| `registros_json` | `TEXT` | Sim |  | `` | JSON com chaves e arquivos envolvidos |
| `valores_json` | `TEXT` | Sim |  | `` | JSON com valores encontrados |
| `status` | `TEXT` | Sim |  | `` |  |
| `descricao` | `TEXT` | Sim |  | `` |  |

### `evidencia`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `tabela_destino` | `TEXT` | Sim |  | `` |  |
| `registro_chave` | `TEXT` | Sim |  | `` |  |
| `bru_tabela` | `TEXT` | Sim |  | `` |  |
| `bru_chave` | `TEXT` | Sim |  | `` |  |

### `ext_balancete_linha`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `fonte` | `TEXT` | Sim |  | `` |  |
| `periodo` | `TEXT` | Sim |  | `` | ex.: 2024-12, 2025-01, 2025-12-antes, 2025-12-pos |
| `conta_codigo` | `TEXT` | Sim |  | `` |  |
| `conta_nome` | `TEXT` | Sim |  | `` |  |
| `saldo_anterior_centavos` | `INTEGER` | Sim |  | `` |  |
| `debito_centavos` | `INTEGER` | Sim |  | `` |  |
| `credito_centavos` | `INTEGER` | Sim |  | `` |  |
| `saldo_atual_centavos` | `INTEGER` | Sim |  | `` |  |
| `origem_valor` | `TEXT` | Sim |  | `` |  |
| `celula_id` | `INTEGER` | Não |  | `bru_celula.id` |  |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `ext_campo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `documento_id` | `INTEGER` | Sim |  | `ext_documento.id` |  |
| `secao` | `TEXT` | Não |  | `` |  |
| `rotulo` | `TEXT` | Sim |  | `` |  |
| `valor_texto` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Não |  | `` |  |
| `moeda` | `TEXT` | Não |  | `` |  |
| `valor_micro` | `INTEGER` | Não |  | `` | Escala 10^-6 para taxas, aliquotas e quantidades fracionarias |
| `valor_data` | `TEXT` | Não |  | `` | ISO-8601 |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `ext_diario_lancamento`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: extlanc:2025:0001 |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `ano` | `INTEGER` | Sim |  | `` |  |
| `numero_lancamento` | `INTEGER` | Sim |  | `` |  |
| `data_lancamento` | `TEXT` | Sim |  | `` | ISO-8601 |
| `historico` | `TEXT` | Sim |  | `` |  |
| `tag_ref` | `TEXT` | Não |  | `` | Tag extraida de [TAG] no historico (ex.: NF-e 1243, TRF106997) |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `ext_diario_partida`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `lancamento_id` | `INTEGER` | Sim |  | `ext_diario_lancamento.id` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `conta_codigo` | `TEXT` | Sim |  | `` |  |
| `conta_nome` | `TEXT` | Sim |  | `` |  |
| `dc` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |
| `valor_texto` | `TEXT` | Sim |  | `` |  |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `ext_documento`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: extdoc:<caminho_relativo>:<pagina_inicio> |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `modelo` | `TEXT` | Sim |  | `` | Nome canonico do modelo (ex.: NFe, Contrato-cambio) |
| `tipo` | `TEXT` | Sim |  | `` | Categoria macro do documento |
| `numero` | `TEXT` | Não |  | `` | Numero impresso do documento |
| `serie` | `TEXT` | Não |  | `` |  |
| `data_emissao` | `TEXT` | Não |  | `` | ISO-8601 |
| `data_referencia` | `TEXT` | Não |  | `` | Data do pacote / movimento (ISO-8601) |
| `doc_ref` | `TEXT` | Não |  | `` | Chave comum Doc/Ref (ex.: TRF106997, BOL005) |
| `estabelecimento_prefixo` | `TEXT` | Não |  | `` | M, F, G, NF ou NULL |
| `valor_total_centavos` | `INTEGER` | Não |  | `` |  |
| `moeda` | `TEXT` | Sim |  | `` |  |
| `valor_total_texto` | `TEXT` | Não |  | `` |  |

### `ext_estoque_linha`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `aba` | `TEXT` | Sim |  | `` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `produto_codigo` | `TEXT` | Não |  | `` |  |
| `descricao` | `TEXT` | Não |  | `` |  |
| `dados_json` | `TEXT` | Sim |  | `` |  |
| `celula_id` | `INTEGER` | Não |  | `bru_celula.id` |  |

### `ext_extrato_linha`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: extmov:<conta>:<aba>:<n_linha> |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `aba` | `TEXT` | Sim |  | `` |  |
| `n_linha` | `INTEGER` | Sim |  | `` |  |
| `conta_codigo` | `TEXT` | Sim |  | `` | matriz_2025, matriz_2026, filial, goiania |
| `data_movimento` | `TEXT` | Sim |  | `` | ISO-8601 |
| `historico` | `TEXT` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Sim |  | `` |  |
| `debito_centavos` | `INTEGER` | Não |  | `` |  |
| `credito_centavos` | `INTEGER` | Não |  | `` |  |
| `saldo_centavos` | `INTEGER` | Sim |  | `` |  |
| `origem_valor` | `TEXT` | Sim |  | `` |  |
| `celula_saldo_id` | `INTEGER` | Não |  | `bru_celula.id` |  |

### `ext_item`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `documento_id` | `INTEGER` | Sim |  | `ext_documento.id` |  |
| `tabela` | `TEXT` | Sim |  | `` | Nome logico da tabela no documento |
| `n_linha` | `INTEGER` | Sim |  | `` |  |
| `colunas_json` | `TEXT` | Sim |  | `` | JSON com o texto exato das colunas |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `ext_material`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `dossie` | `TEXT` | Sim |  | `` |  |
| `categoria` | `TEXT` | Sim |  | `` | plano_ensino, aula, matriz_requisitos, estudo_caso, devolutiva, orientacao, pagina_sigaa |
| `titulo` | `TEXT` | Sim |  | `` |  |

### `ext_nota_didatica`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `documento_id` | `INTEGER` | Não |  | `ext_documento.id` |  |
| `texto` | `TEXT` | Sim |  | `` |  |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |
| `celula_id` | `INTEGER` | Não |  | `bru_celula.id` |  |
| `paragrafo_id` | `INTEGER` | Não |  | `bru_paragrafo.id` |  |

### `ext_parametro_planilha`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `aba` | `TEXT` | Sim |  | `` |  |
| `rotulo` | `TEXT` | Sim |  | `` |  |
| `valor_texto` | `TEXT` | Sim |  | `` |  |
| `celula_id` | `INTEGER` | Não |  | `bru_celula.id` |  |

### `ext_razao_linha`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |
| `ano` | `INTEGER` | Sim |  | `` |  |
| `conta_codigo` | `TEXT` | Sim |  | `` |  |
| `conta_nome` | `TEXT` | Sim |  | `` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `data_movimento` | `TEXT` | Não |  | `` |  |
| `numero_lancamento` | `INTEGER` | Não |  | `` |  |
| `historico` | `TEXT` | Sim |  | `` |  |
| `debito_centavos` | `INTEGER` | Não |  | `` |  |
| `credito_centavos` | `INTEGER` | Não |  | `` |  |
| `saldo_centavos` | `INTEGER` | Não |  | `` |  |
| `saldo_dc` | `TEXT` | Não |  | `` |  |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `ext_secao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `material_id` | `INTEGER` | Sim |  | `ext_material.id` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `titulo` | `TEXT` | Não |  | `` |  |
| `conteudo` | `TEXT` | Sim |  | `` |  |
| `paragrafo_id` | `INTEGER` | Não |  | `bru_paragrafo.id` |  |
| `linha_bruto_id` | `INTEGER` | Não |  | `bru_linha.id` |  |

### `nrm_apuracao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `empresa_id` | `INTEGER` | Sim |  | `nrm_empresa.id` |  |
| `tipo_apuracao` | `TEXT` | Sim |  | `` | PGDAS_D, IPI |
| `competencia` | `TEXT` | Sim |  | `` |  |
| `receita_bruta_centavos` | `INTEGER` | Não |  | `` |  |
| `rbt12_centavos` | `INTEGER` | Não |  | `` |  |
| `tributo_apurado_centavos` | `INTEGER` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_cambio`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `contrato_numero` | `TEXT` | Sim |  | `` |  |
| `data_contratacao` | `TEXT` | Sim |  | `` |  |
| `moeda_estrangeira` | `TEXT` | Sim |  | `` |  |
| `valor_estrangeiro_centavos` | `INTEGER` | Sim |  | `` |  |
| `taxa_micro` | `INTEGER` | Sim |  | `` |  |
| `taxa_texto` | `TEXT` | Sim |  | `` |  |
| `principal_brl_centavos` | `INTEGER` | Sim |  | `` |  |
| `iof_centavos` | `INTEGER` | Não |  | `` |  |
| `tarifa_centavos` | `INTEGER` | Não |  | `` |  |
| `valor_total_brl_centavos` | `INTEGER` | Sim |  | `` |  |
| `exportador_pessoa_id` | `INTEGER` | Não |  | `nrm_pessoa.id` |  |
| `invoice_numero` | `TEXT` | Não |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_ciclo_importacao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `empresa_id` | `INTEGER` | Não |  | `nrm_empresa.id` |  |
| `cambio_doc_ref` | `TEXT` | Sim |  | `` |  |
| `data_cambio` | `TEXT` | Sim |  | `` |  |
| `data_entrada_estoque` | `TEXT` | Não |  | `` |  |
| `pais_origem` | `TEXT` | Não |  | `` |  |
| `principal_brl_centavos` | `INTEGER` | Não |  | `` |  |
| `iof_centavos` | `INTEGER` | Não |  | `` |  |

### `nrm_comprovante`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `subtipo` | `TEXT` | Sim |  | `` | PIX_enviado, PIX_recebido, TED_enviada, TED_recebida, pagto_boleto, pagto_tributo, debito_automatico, cheque_pago, deposito_especie, credito_cartao, aviso_tarifas, etc. |
| `data_operacao` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |
| `moeda` | `TEXT` | Sim |  | `` |  |
| `contraparte_pessoa_id` | `INTEGER` | Não |  | `nrm_pessoa.id` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_conta_bancaria`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: cta:meridional:0001:matriz |
| `empresa_id` | `INTEGER` | Sim |  | `nrm_empresa.id` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `banco_nome` | `TEXT` | Sim |  | `` |  |
| `agencia` | `TEXT` | Não |  | `` |  |
| `conta_numero` | `TEXT` | Não |  | `` |  |
| `descricao` | `TEXT` | Sim |  | `` |  |

### `nrm_conta_contabil`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: cc:1.1.01.001 |
| `codigo` | `TEXT` | Sim |  | `` |  |
| `nome` | `TEXT` | Sim |  | `` |  |
| `grupo` | `INTEGER` | Sim |  | `` |  |
| `natureza` | `TEXT` | Não |  | `` |  |

### `nrm_contrato_credito`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `empresa_id` | `INTEGER` | Sim |  | `nrm_empresa.id` |  |
| `numero_contrato` | `TEXT` | Sim |  | `` |  |
| `data_contratacao` | `TEXT` | Sim |  | `` |  |
| `principal_centavos` | `INTEGER` | Sim |  | `` |  |
| `taxa_juros_texto` | `TEXT` | Não |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_devolutiva`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `dossie_id` | `INTEGER` | Sim |  | `nrm_dossie.id` |  |
| `grupo` | `TEXT` | Sim |  | `` | G00..G29 |
| `nossa_dupla` | `INTEGER` | Sim |  | `` |  |
| `nota_texto` | `TEXT` | Não |  | `` |  |
| `resumo` | `TEXT` | Não |  | `` |  |
| `material_id` | `INTEGER` | Sim |  | `nrm_material.id` |  |

### `nrm_di`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `numero_di` | `TEXT` | Sim |  | `` |  |
| `data_registro` | `TEXT` | Sim |  | `` |  |
| `moeda` | `TEXT` | Sim |  | `` |  |
| `taxa_micro` | `INTEGER` | Sim |  | `` |  |
| `taxa_texto` | `TEXT` | Sim |  | `` |  |
| `valor_fob_moeda_centavos` | `INTEGER` | Sim |  | `` |  |
| `frete_seguro_moeda_centavos` | `INTEGER` | Não |  | `` |  |
| `valor_aduaneiro_brl_centavos` | `INTEGER` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_di_adicao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `di_id` | `INTEGER` | Sim |  | `nrm_di.id` |  |
| `numero_adicao` | `TEXT` | Sim |  | `` |  |
| `ncm` | `TEXT` | Sim |  | `` |  |
| `valor_aduaneiro_centavos` | `INTEGER` | Sim |  | `` |  |
| `ii_centavos` | `INTEGER` | Sim |  | `` |  |
| `ipi_centavos` | `INTEGER` | Sim |  | `` |  |
| `pis_imp_centavos` | `INTEGER` | Sim |  | `` |  |
| `cofins_imp_centavos` | `INTEGER` | Sim |  | `` |  |

### `nrm_documento_fiscal`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `tipo_documento` | `TEXT` | Sim |  | `` |  |
| `numero` | `TEXT` | Não |  | `` |  |
| `serie` | `TEXT` | Não |  | `` |  |
| `chave_acesso` | `TEXT` | Não |  | `` |  |
| `data_emissao` | `TEXT` | Sim |  | `` |  |
| `emitente_pessoa_id` | `INTEGER` | Não |  | `nrm_pessoa.id` |  |
| `destinatario_pessoa_id` | `INTEGER` | Não |  | `nrm_pessoa.id` |  |
| `natureza_operacao` | `TEXT` | Não |  | `` |  |
| `valor_total_centavos` | `INTEGER` | Sim |  | `` |  |
| `moeda` | `TEXT` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_documento_fiscal_item`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `documento_fiscal_id` | `INTEGER` | Sim |  | `nrm_documento_fiscal.id` |  |
| `n_item` | `INTEGER` | Sim |  | `` |  |
| `produto_id` | `INTEGER` | Não |  | `nrm_produto.id` | Produto interno (quando mapeado) |
| `codigo_item_documento` | `TEXT` | Não |  | `` | Codigo impresso no documento (inclusive SKU do fornecedor) |
| `descricao` | `TEXT` | Sim |  | `` |  |
| `ncm_hs` | `TEXT` | Não |  | `` |  |
| `cfop` | `TEXT` | Não |  | `` |  |
| `cst_csosn` | `TEXT` | Não |  | `` |  |
| `unidade` | `TEXT` | Não |  | `` |  |
| `quantidade_micro` | `INTEGER` | Não |  | `` |  |
| `valor_unitario_micro` | `INTEGER` | Não |  | `` |  |
| `valor_total_centavos` | `INTEGER` | Sim |  | `` |  |
| `moeda` | `TEXT` | Sim |  | `` |  |

### `nrm_dossie`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: dos:D1, dos:D2, dos:D3, dos:D4 |
| `codigo` | `TEXT` | Sim |  | `` |  |
| `titulo` | `TEXT` | Sim |  | `` |  |
| `periodo_texto` | `TEXT` | Não |  | `` |  |
| `prazo_texto` | `TEXT` | Não |  | `` |  |

### `nrm_empresa`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: emp:rota_sul_d2, emp:rota_sul_d4, emp:meia_ponte, emp:horizonte |
| `pessoa_id` | `INTEGER` | Sim |  | `nrm_pessoa.id` |  |
| `nome_curto` | `TEXT` | Sim |  | `` |  |
| `papel_no_caso` | `TEXT` | Sim |  | `` |  |

### `nrm_estabelecimento`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: est:rota_sul_d4:matriz, est:rota_sul_d4:filial_itajai |
| `empresa_id` | `INTEGER` | Sim |  | `nrm_empresa.id` |  |
| `tipo` | `TEXT` | Sim |  | `` |  |
| `cnpj` | `TEXT` | Sim |  | `` |  |
| `uf` | `TEXT` | Não |  | `` |  |
| `municipio` | `TEXT` | Não |  | `` |  |
| `endereco` | `TEXT` | Não |  | `` |  |

### `nrm_estoque_movimento`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `produto_id` | `INTEGER` | Sim |  | `nrm_produto.id` |  |
| `ciclo_importacao_id` | `INTEGER` | Não |  | `nrm_ciclo_importacao.id` |  |
| `tipo_movimento` | `TEXT` | Sim |  | `` |  |
| `data_movimento` | `TEXT` | Sim |  | `` |  |
| `quantidade` | `INTEGER` | Sim |  | `` |  |
| `custo_unitario_centavos` | `INTEGER` | Não |  | `` |  |
| `valor_total_centavos` | `INTEGER` | Não |  | `` |  |

### `nrm_evento`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `empresa_id` | `INTEGER` | Não |  | `nrm_empresa.id` |  |
| `tipo_evento` | `TEXT` | Sim |  | `` | constituicao, alteracao_contratual, abertura_filial, mudanca_regime, carta_socios, admissao_prevista |
| `data_evento` | `TEXT` | Sim |  | `` | ISO-8601 |
| `descricao` | `TEXT` | Sim |  | `` |  |
| `fonte_chave` | `TEXT` | Sim |  | `` |  |

### `nrm_fato`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `sujeito_chave` | `TEXT` | Sim |  | `` | Chave da empresa, estabelecimento ou pessoa |
| `evento_id` | `INTEGER` | Não |  | `nrm_evento.id` |  |
| `atributo` | `TEXT` | Sim |  | `` | razao_social, sede, regime, porte, cnae, capital_social, ie, im, empregado_parametro, etc. |
| `valor_texto` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Não |  | `` |  |
| `vigente_de` | `TEXT` | Sim |  | `` | ISO-8601 |
| `vigente_ate` | `TEXT` | Não |  | `` | ISO-8601 ou NULL se vigente |
| `fonte_chave` | `TEXT` | Sim |  | `` |  |

### `nrm_fechamento_caixa`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `data_fechamento` | `TEXT` | Sim |  | `` |  |
| `valor_total_centavos` | `INTEGER` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_fechamento_caixa_dia`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `fechamento_id` | `INTEGER` | Sim |  | `nrm_fechamento_caixa.id` |  |
| `data_dia` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |

### `nrm_guia`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `tipo_guia` | `TEXT` | Sim |  | `` | DAS, DARF_IPI, DARE_SC, DARE_GO_ICMS_IMP, DARE_GO_ST, GNRE_DF, GNRE_ES, GNRE_MG, AFRMM |
| `competencia` | `TEXT` | Não |  | `` |  |
| `data_vencimento` | `TEXT` | Não |  | `` |  |
| `valor_principal_centavos` | `INTEGER` | Sim |  | `` |  |
| `valor_total_centavos` | `INTEGER` | Sim |  | `` |  |
| `uf` | `TEXT` | Não |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_guia_composicao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `guia_id` | `INTEGER` | Sim |  | `nrm_guia.id` |  |
| `tributo_codigo` | `TEXT` | Sim |  | `` |  |
| `descricao` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |

### `nrm_item_tributo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `item_id` | `INTEGER` | Não |  | `nrm_documento_fiscal_item.id` |  |
| `documento_fiscal_id` | `INTEGER` | Sim |  | `nrm_documento_fiscal.id` |  |
| `tributo` | `TEXT` | Sim |  | `` | ICMS, ICMS_ST, DIFAL, IPI, PIS, COFINS, ISS, IRRF, CSLL, CIP |
| `base_centavos` | `INTEGER` | Não |  | `` |  |
| `aliquota_micro` | `INTEGER` | Não |  | `` |  |
| `aliquota_texto` | `TEXT` | Não |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |

### `nrm_lancamento`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: lanc:2025:0360 |
| `ano` | `INTEGER` | Sim |  | `` |  |
| `numero_lancamento` | `INTEGER` | Sim |  | `` |  |
| `data_lancamento` | `TEXT` | Sim |  | `` |  |
| `historico` | `TEXT` | Sim |  | `` |  |
| `tag_ref` | `TEXT` | Não |  | `` |  |

### `nrm_liquidacao_cartao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `data_liquidacao` | `TEXT` | Sim |  | `` |  |
| `valor_bruto_centavos` | `INTEGER` | Sim |  | `` |  |
| `taxa_centavos` | `INTEGER` | Não |  | `` |  |
| `valor_liquido_centavos` | `INTEGER` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_liquidacao_cartao_venda`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `liquidacao_id` | `INTEGER` | Sim |  | `nrm_liquidacao_cartao.id` |  |
| `data_venda` | `TEXT` | Não |  | `` |  |
| `autorizacao` | `TEXT` | Não |  | `` |  |
| `modalidade` | `TEXT` | Não |  | `` |  |
| `parcela_texto` | `TEXT` | Não |  | `` |  |
| `valor_bruto_centavos` | `INTEGER` | Sim |  | `` |  |
| `valor_liquido_centavos` | `INTEGER` | Não |  | `` |  |

### `nrm_material`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `dossie_id` | `INTEGER` | Não |  | `nrm_dossie.id` |  |
| `categoria` | `TEXT` | Sim |  | `` |  |
| `titulo` | `TEXT` | Sim |  | `` |  |
| `arquivo_id` | `INTEGER` | Sim |  | `bru_arquivo.id` |  |

### `nrm_material_secao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `material_id` | `INTEGER` | Sim |  | `nrm_material.id` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `titulo` | `TEXT` | Não |  | `` |  |
| `conteudo` | `TEXT` | Sim |  | `` |  |

### `nrm_memorando`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `data_memorando` | `TEXT` | Sim |  | `` |  |
| `assunto` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Não |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_movimento_bancario`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: mov:matriz:2025-01-04:TRF106997:6 |
| `conta_bancaria_id` | `INTEGER` | Sim |  | `nrm_conta_bancaria.id` |  |
| `data_movimento` | `TEXT` | Sim |  | `` |  |
| `historico` | `TEXT` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Sim |  | `` |  |
| `tipo_dc` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |
| `saldo_apos_centavos` | `INTEGER` | Sim |  | `` |  |
| `origem_saldo` | `TEXT` | Sim |  | `` |  |

### `nrm_nota_didatica`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `origem_chave` | `TEXT` | Sim |  | `` |  |
| `texto` | `TEXT` | Sim |  | `` |  |

### `nrm_parcela`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `contrato_id` | `INTEGER` | Sim |  | `nrm_contrato_credito.id` |  |
| `numero_parcela` | `INTEGER` | Sim |  | `` |  |
| `data_vencimento` | `TEXT` | Sim |  | `` |  |
| `amortizacao_centavos` | `INTEGER` | Sim |  | `` |  |
| `juros_centavos` | `INTEGER` | Sim |  | `` |  |
| `total_centavos` | `INTEGER` | Sim |  | `` |  |
| `situacao` | `TEXT` | Não |  | `` |  |

### `nrm_participacao_societaria`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `empresa_id` | `INTEGER` | Sim |  | `nrm_empresa.id` |  |
| `socio_pessoa_id` | `INTEGER` | Sim |  | `nrm_pessoa.id` |  |
| `quotas` | `INTEGER` | Não |  | `` |  |
| `valor_centavos` | `INTEGER` | Não |  | `` |  |
| `percentual_micro` | `INTEGER` | Não |  | `` |  |
| `papel` | `TEXT` | Sim |  | `` | socio, socio_administrador, procurador, socio_de_fato, titular_formal |
| `vigente_de` | `TEXT` | Sim |  | `` |  |
| `vigente_ate` | `TEXT` | Não |  | `` |  |
| `fonte_chave` | `TEXT` | Sim |  | `` |  |

### `nrm_partida`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `lancamento_id` | `INTEGER` | Sim |  | `nrm_lancamento.id` |  |
| `ordem` | `INTEGER` | Sim |  | `` |  |
| `conta_id` | `INTEGER` | Sim |  | `nrm_conta_contabil.id` |  |
| `dc` | `TEXT` | Sim |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |

### `nrm_pessoa`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: pes:cpf:11122233397:ronaldo |
| `tipo_pessoa` | `TEXT` | Sim |  | `` |  |
| `nome_canonico` | `TEXT` | Sim |  | `` |  |

### `nrm_pessoa_identificador`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `pessoa_id` | `INTEGER` | Sim |  | `nrm_pessoa.id` |  |
| `tipo_id` | `TEXT` | Sim |  | `` |  |
| `valor` | `TEXT` | Sim |  | `` | Texto preservando zeros a esquerda |
| `eh_ficticio` | `INTEGER` | Sim |  | `` |  |
| `fonte_chave` | `TEXT` | Sim |  | `` |  |

### `nrm_pessoa_ocorrencia`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `pessoa_id` | `INTEGER` | Sim |  | `nrm_pessoa.id` |  |
| `nome_impresso` | `TEXT` | Sim |  | `` |  |
| `identificador_impresso` | `TEXT` | Não |  | `` |  |
| `papel` | `TEXT` | Sim |  | `` | emitente, destinatario, tomador, prestador, socio, empregado, banco, contador, etc. |
| `fonte_chave` | `TEXT` | Sim |  | `` |  |

### `nrm_produto`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: prod:PN-9018 |
| `codigo_interno` | `TEXT` | Sim |  | `` |  |
| `descricao` | `TEXT` | Sim |  | `` |  |
| `ncm` | `TEXT` | Não |  | `` |  |
| `cest` | `TEXT` | Não |  | `` |  |
| `origem` | `TEXT` | Não |  | `` |  |

### `nrm_recibo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `subtipo` | `TEXT` | Sim |  | `` |  |
| `data_recibo` | `TEXT` | Sim |  | `` |  |
| `competencia` | `TEXT` | Não |  | `` |  |
| `beneficiario_pessoa_id` | `INTEGER` | Não |  | `nrm_pessoa.id` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_requisito`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `dossie_id` | `INTEGER` | Sim |  | `nrm_dossie.id` |  |
| `codigo` | `TEXT` | Sim |  | `` |  |
| `descricao` | `TEXT` | Sim |  | `` |  |
| `fonte_chave` | `TEXT` | Sim |  | `` |  |

### `nrm_saldo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `conta_id` | `INTEGER` | Sim |  | `nrm_conta_contabil.id` |  |
| `periodo` | `TEXT` | Sim |  | `` |  |
| `fonte` | `TEXT` | Sim |  | `` | balancete_xlsx, balancete_pdf, razao, abertura_d1 |
| `saldo_anterior_centavos` | `INTEGER` | Não |  | `` |  |
| `debito_centavos` | `INTEGER` | Não |  | `` |  |
| `credito_centavos` | `INTEGER` | Não |  | `` |  |
| `saldo_atual_centavos` | `INTEGER` | Sim |  | `` |  |

### `nrm_tema`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `termo` | `TEXT` | Sim |  | `` |  |

### `nrm_titulo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `subtipo` | `TEXT` | Sim |  | `` |  |
| `numero` | `TEXT` | Não |  | `` |  |
| `data_vencimento` | `TEXT` | Não |  | `` |  |
| `valor_centavos` | `INTEGER` | Sim |  | `` |  |
| `beneficiario_pessoa_id` | `INTEGER` | Não |  | `nrm_pessoa.id` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |

### `nrm_transacao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: tx:TRF106997 ou tx:matriz:2025-01:BOL005 |
| `regra_agrupamento` | `TEXT` | Sim |  | `` |  |
| `doc_ref` | `TEXT` | Não |  | `` |  |
| `estabelecimento_id` | `INTEGER` | Não |  | `nrm_estabelecimento.id` |  |
| `ano_mes` | `TEXT` | Não |  | `` |  |
| `data_referencia` | `TEXT` | Não |  | `` |  |
| `status_vinculo` | `TEXT` | Sim |  | `` |  |

### `nrm_transacao_membro`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `transacao_id` | `INTEGER` | Sim |  | `nrm_transacao.id` |  |
| `tabela_membro` | `TEXT` | Sim |  | `` |  |
| `membro_chave` | `TEXT` | Sim |  | `` |  |
| `papel_membro` | `TEXT` | Sim |  | `` | documento, movimento_bancario, lancamento_contabil, ciclo_importacao |
| `criterio_vinculo` | `TEXT` | Sim |  | `` |  |

### `nrm_vinculo`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `tema_id` | `INTEGER` | Sim |  | `nrm_tema.id` |  |
| `alvo_tabela` | `TEXT` | Sim |  | `` |  |
| `alvo_chave` | `TEXT` | Sim |  | `` |  |
| `criterio` | `TEXT` | Sim |  | `` |  |

### Views em `laboratorio.db`

- `vw_cobertura_bruto`
- `vw_inventario_acervo`
- `vw_linha_do_tempo`
- `vw_resumo_conferencia`
- `vw_sigaa_cobertura`
- `vw_situacao_em`

## Banco `trabalho.db`

### `anotacao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` | ex.: anot:<uuid_ou_seq> |
| `alvo_tabela` | `TEXT` | Sim |  | `` |  |
| `alvo_chave` | `TEXT` | Sim |  | `` |  |
| `autor` | `TEXT` | Sim |  | `` |  |
| `dossie` | `TEXT` | Não |  | `` |  |
| `conteudo` | `TEXT` | Sim |  | `` |  |
| `criado_em` | `TEXT` | Sim |  | `` |  |

### `classificacao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `alvo_tabela` | `TEXT` | Sim |  | `` |  |
| `alvo_chave` | `TEXT` | Sim |  | `` |  |
| `categoria` | `TEXT` | Sim |  | `` |  |
| `valor` | `TEXT` | Sim |  | `` |  |
| `observacao` | `TEXT` | Não |  | `` |  |
| `autor` | `TEXT` | Sim |  | `` |  |
| `criado_em` | `TEXT` | Sim |  | `` |  |

### `decisao`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `dossie` | `TEXT` | Sim |  | `` |  |
| `alvo_chave` | `TEXT` | Não |  | `` |  |
| `titulo` | `TEXT` | Sim |  | `` |  |
| `justificativa` | `TEXT` | Sim |  | `` |  |
| `fonte_oficial` | `TEXT` | Não |  | `` |  |
| `autor` | `TEXT` | Sim |  | `` |  |
| `criado_em` | `TEXT` | Sim |  | `` |  |

### `resposta_requisito`

| Coluna | Tipo | Obrigatória | PK | FK | Descrição |
|---|---|---|---|---|---|
| `id` | `INTEGER` | Sim | PK | `` |  |
| `chave` | `TEXT` | Sim |  | `` |  |
| `requisito_chave` | `TEXT` | Sim |  | `` |  |
| `status` | `TEXT` | Sim |  | `` |  |
| `resposta_md` | `TEXT` | Sim |  | `` |  |
| `evidencias_chaves_json` | `TEXT` | Sim |  | `` |  |
| `autor` | `TEXT` | Sim |  | `` |  |
| `atualizado_em` | `TEXT` | Sim |  | `` |  |

