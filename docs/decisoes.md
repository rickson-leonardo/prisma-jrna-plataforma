# Decisões de Arquitetura — Laboratório Contábil

1. **Isolamento em `plataforma/`**: Código, schemas, testes, documentação gerada e bancos ficam em `plataforma/`, mantendo `D1/`, `D2/`, `D3/`, `D4/`, `Resultado/` e `_paginas/` intactos no diretório-pai (`ACERVO_DIR`).
2. **Quatro camadas com contrato**: `bru_*` (bruto) → `ext_*` (extraído) → `nrm_*` (normalizado em 3FN) → `vw_*` + `trabalho.db` (plataforma).
3. **Derivados × Humanos**: `banco/laboratorio.db` é descartável e recriado pelo pipeline; `banco/trabalho.db` guarda anotações, decisões, classificações e respostas ligadas por `chave` textual estável e nunca é apagado.
4. **Motores de leitura fiéis**:
   - PDFs via `pymupdf` (preserva layout sem fragmentar marcas-d'água diagonais como `pdftotext`).
   - Planilhas `.xlsx` via `openpyxl`, preservando fórmula e `valor_cacheado` na Camada 1 e avaliando deterministicamente as 648 células sem cache na Camada 2 (`origem_valor`).
   - Documentos `.docx` via `python-docx` (parágrafos e células de tabela na ordem do documento) e HTMLs do SIGAA em `ISO-8859-1`.
5. **Redundância quádrupla classificada em `bru_arquivo.papel_acervo`**: `primario`, `container_zip`, `duplicata_sha256`, `consolidado_espelho`, `formato_espelho`. Só `primario` gera registros próprios na Camada 3; espelhos participam dos cruzamentos da Fase 5 e viram `evidencia` adicional.
6. **Fidelidade numérica**: valores monetários em `*_centavos INTEGER` + `moeda`; taxas/alíquotas em `*_micro INTEGER` ($10^{-6}$) + `*_texto`; códigos com zeros à esquerda como `TEXT`; datas em ISO-8601.
7. **Sem julgamento silencioso**: conflitos entre fontes geram registros na tabela `conferencia`.
