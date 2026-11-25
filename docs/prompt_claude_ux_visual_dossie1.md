# Prompt Técnico para o Claude — Revisão UX/UI, Identidade Visual PRISMA JRNA (`DMA-v3`), Ajuda Contextual Total e Emissão de PDFs (Escopo Estrito: Dossiê 1)

> **Como usar este arquivo:** copie integralmente o bloco dentro de `=== INÍCIO DO PROMPT ===` ... `=== FIM DO PROMPT ===` para enviar ao Claude (ou, no Claude Code, peça para ele ler e executar este arquivo passo a passo).

---

=== INÍCIO DO PROMPT ===

Você vai atuar como **Designer Sênior de Produto / UX Contábil, Arquiteto Frontend e Engenheiro de Geração Documental (PDF/XLSX)** sobre uma plataforma contábil real já funcional no repositório `C:\Users\Asa Branca\Github\UnB-Laboratorio-Contabil\plataforma`.

Leia primeiro estes arquivos para entender o estado exato do sistema antes de propor ou alterar qualquer linha de código:
1. Arquitetura e diretriz anti-enviesamento: `docs/plano_plataforma_contabil_etapa1.md`
2. Esquema PostgreSQL e motor contábil (não quebrar regras fiscais/contábeis):
   - `sistema/pg/migrations/003_erp_societario_planejamento.sql`
   - `sistema/pg/migrations/004_ajustes_auditoria_d1.sql`
   - `sistema/erp/motor_contabil.py`
3. Camada Web atual que você vai revisar e evoluir:
   - `sistema/web/app.py`
   - `sistema/web/repo.py`
   - `sistema/web/exportador_dossie1.py`
   - `sistema/web/static/style.css`
   - `sistema/web/templates/base.html`, `painel.html`, `cadastro.html`, `instrumentos.html`, `legalizacao.html`, `planejamento.html`, `sustentacao.html`
4. Identidade Visual oficial da empresa (`DMA-PRISMA-2026-v3`) e ferramentas de renderização existentes (somente leitura na origem):
   - `G:\Meu Drive\Nath\Trabalho 01\_planejamento\DMA_Guia_Padrao_Visual_PRISMA_JRNA_v3.html`
   - `G:\Meu Drive\Nath\Trabalho 01\_planejamento\brand\` (logos, símbolo, wordmark, tagline, watermark e fontes `AdwaitaSans` / `AdwaitaMono`)
   - `G:\Meu Drive\Nath\Trabalho 01\_planejamento\ferramentas\render.py` e `checkpdf.py`
   - Referência de estrutura textual do Dossiê 1: `G:\Meu Drive\Nath\Trabalho 01\_entrega_limpa_Dossie1\00_Indice_Geral_Dossie1_PRISMA_JRNA.md` e `02_Plano_de_Negocios_PRISMA_JRNA.md`

---

## 1. Contexto Fundamental: A Dupla Natureza ("Os Dois Mundos") e Trava de Escopo

1. **Não é uma "plataforma de curso" nem um formulário de prova.** Na camada principal (`schema: erp`), a usuária é a **contadora responsável (Nathalia Peres Araujo, CRC-DF)** operando um **Sistema Contábil e Societário real** da organização *PRISMA JRNA Auditoria e Contabilidade Ltda.* Ela cadastra empresa, sócias, CNAEs e RT; redige e compara Contrato Social e Acordo de Sócias (MoU); executa o workflow paralegal no DF; simula regimes tributários (Simples Nacional progressivo Anexos III/V + Fator R, pró-labore, DRE, Fluxo de Caixa, Balanço fechado a `R$ 0,00`, Ponto de Equilíbrio, VPL/TIR/Sensibilidade); e **investiga, edita e homologa** decisões técnicas por CRUD completo.
2. **Simultaneamente, a plataforma conversa com o curso (`Laboratório Contábil — CCA 0174 / UnB`).** Na camada de sustentação (`schema: auditoria`), cada operação alimenta a **fundamentação técnica para a defesa oral**, mantém dados trazidos de tentativas anteriores em **quarentena anti-enviesamento** (`status_validacao` = `pendente_revisao` | `alerta_inconsistencia` | `homologado_contadora`), exibe a crítica literal da banca (`v1`), audita os `200` critérios das 4 Matrizes (sem inflar notas automaticamente) e permite compilar e baixar os entregáveis oficiais do **Dossiê 1**.
3. **TRAVA DE ESCOPO INEGOCIÁVEL:** Esta etapa cobre **EXCLUSIVAMENTE o Dossiê 1** (constituição do escritório, legalização DF e planejamento financeiro/tributário 36 meses). **Não crie telas, menus, simulações ou fluxos de Dossiê 2, 3 ou 4** e nunca invente nem preencha dados fáticos não verificados para simular conclusão. Preserve 100% intactos `acervo.*`, os dados de D2/D3/D4 no banco e os testes existentes.

---

## 2. Missão 1 — Revisão Completa de UX, Usabilidade e Fluxo de Trabalho Contábil

Faça uma auditoria crítica da usabilidade atual de `sistema/web/` como se você estivesse no lugar de uma contadora usando a ferramenta diariamente e precisando defender cada decisão:

- **Hierarquia "Sistema Contábil Primeiro, Sustentação Acoplada":**
  - Separe visualmente com nitidez o que é **Operação ERP Contábil** (editar QSA, ajustar pró-labore, homologar cláusula, avançar etapa Redesim) do que é **Sustentação & Quarentena do Dossiê 1** (critério da matriz, crítica v1, alerta de premissa assumida, justificativa para defesa).
  - Elimine jargões crus de banco de dados na UI (ex.: substitua `simples_segregado`, `pendente_revisao`, `homologado_contadora`, `acervo_sigaa` em rótulos visíveis por nomes legíveis em português contábil com o código técnico discreto apenas em metadado/tooltip).
- **Fluxo CRUD Ergonomicamente Limpo (Fim das Tabelas/Formulários Esmagados):**
  - Na tela atual, formulários inteiros estão comprimidos dentro de `<td>` ou listados todos abertos em sequência longa (como 33 cláusulas e 14 etapas abertas simultaneamente).
  - Reorganize para leitura executiva + edição ágil: **tabela-resumo / lista escaneável com badges de status**, painel/gaveta ou expansão focada por item para edição detalhada, botões claros de **"Salvar rascunho"**, **"Homologar decisão"** (validando se há justificativa quando exigido) e **"Excluir" com confirmação explícita em modal/diálogo acessível** (nunca exclusão acidental em 1 clique!).
  - Preserve **filtros rápidos úteis**: ex. *"Somente pendentes de revisão"*, *"Com alertas/inconsistências"*, *"Já homologados"*, busca instantânea por palavra-chave/código nas tabelas de cláusulas, etapas e 200 critérios.
  - Adicione **progresso visual por Estação** (ex.: barra/indicador `12/33 cláusulas homologadas`, `0/4 cenários homologados`) e atalho direto dos alertas do Painel (`/`) até o registro exato que gerou o conflito (`#clausula-18`, `#cenario-...`).
- **Segurança & Ergonomia Web:**
  - Adicione proteção CSRF leve nas rotas `POST` (sem adicionar bibliotecas pesadas externas desnecessárias; pode ser helper próprio em `app.py` com `<input type="hidden" name="csrf_token">` via `context_processor`), garantindo que todos os testes automatizados continuem passando.
  - Adicione links diretos de download de relatórios/PDFs e validação amigável nos inputs numéricos brasileiros (`R$ 1.500,00`, `20.000`, `15,0%`).

---

## 3. Missão 2 — Aplicação Integral do Padrão Visual Oficial PRISMA JRNA (`DMA-PRISMA-2026-v3`)

Reestruture completamente `sistema/web/static/style.css` e os templates (`base.html` e páginas) copiando os ativos oficiais de `G:\Meu Drive\Nath\Trabalho 01\_planejamento\brand\` para `plataforma/sistema/web/static/brand/` (fonts `Adwaita Sans` + `Adwaita Mono`, logos PNG/SVG, símbolo e marca d'água):

1. **Paleta Institucional Estrita (Regra `DMA v3` — `70% Branco / 18% Grafite / 9% Neutros / <= 3% Status`):**
   - Grafite e Neutros: `--g900: #111827`, `--g800: #1F2937` (sidebar/cabeçalhos/ações primárias), `--c700: #374151`, `--m500: #6B7280`, `--l300: #D1D5DB`, `--l200: #E5E7EB`, `--n100: #F3F4F6`, `--n50: #F9FAFB`, `--w: #FFFFFF`.
   - Cores de Status **exclusivas** para status funcionais (sempre acompanhadas de texto explícito, nunca cor isolada):
     - Conforme / Homologado: `#166534` sobre `#F0FDF4` (borda `#BBF7D0`)
     - Atenção / Pendente Revisão: `#92400E` sobre `#FFFBEB` (borda `#FDE68A`)
     - Crítico / Alerta Inconsistência: `#991B1B` sobre `#FEF2F2` (borda `#FECACA`)
     - Informativo / Nota: `#1E40AF` sobre `#EFF6FF` (borda `#BFDBFE`)
2. **Tipografia e Logotipo:**
   - Embuta via `@font-face` **`Adwaita Sans`** (toda a UI, tabelas e rótulos) e **`Adwaita Mono`** (`font-variant-numeric: tabular-nums` em CNPJs, CPFs, CRCs, NIREs, CNAEs, códigos de critérios e colunas numéricas alinhadas à direita).
   - Na sidebar/cabeçalho institucional, exiba a **marca PRISMA JRNA real em imagem** (`simbolo_prisma_jrna.png` / `wordmark_prisma_jrna.png` / `logo_prisma_jrna_hd.png`) respeitando a área de proteção (`x` = altura do "P"), sem fundo gradiente espalhafatoso e sem substituir o wordmark por fonte do sistema.
   - **Proibido uso de "pílulas cinza" (`<code>` com fundo) em texto corrido** (conforme `DMA v3` Seção 03): use monoespaçado limpo apenas em identificadores verificáveis e valores contábeis.
3. **Convenção Visual Contábil de Auditoria em Campos Financeiros (`DMA v3` Seção 07):**
   - No Planejamento Financeiro (`planejamento.html`), aplique sutilmente a convenção de papel de trabalho:
     - Campos de **premissa digitada/editável** identificados em azul técnico (`#1D4ED8` / fundo `#EFF6FF`)
     - Valores **calculados pelo motor** (`DRE`, `BP`, `VPL`, `TIR`, `DAS`) em Grafite `#111827`
     - Valores **vinculados de outro módulo** (ex.: Capital Social vindo do QSA) marcados com indicador verde `#15803D`.

---

## 4. Missão 3 — Ícones de Explicação Contextual em TUDO (Página, Campo, Botão, Função e Tabela)

A contadora (e um avaliador ou colega de dupla navegando no sistema) precisa entender **exatamente** o papel contábil e de curso de cada elemento da tela sem precisar adivinhar:

1. **Componente Único Reutilizável de Ajuda Contextual (`macro help_tip(...)` em Jinja + JS leve vanilla):**
   - Crie uma macro padronizada (ex.: `sistema/web/templates/_macros.html`) que renderize um ícone discreto e nítido **`?` / `ⓘ`** em SVG/HTML acessível (`aria-label`, `role="button"`, `tabindex="0"`).
   - Deve funcionar por **hover/foco (tooltip rápido)** E por **clique (popover fixo/fechável ao clicar fora ou `Esc`)** para textos explicativos mais longos — com posicionamento inteligente para nunca vazar da borda da tela nem quebrar layouts de tabela!
2. **Cobertura Obrigatória de 100% dos Elementos Visíveis:**
   - **Cada Página / Estação (topo):** botão/banner *"Como usar esta estação"* explicando *(a)* O que a contadora executa na prática profissional; *(b)* O que precisa validar/desenviesar frente à `v1` e ao rascunho; *(c)* Como isso sustenta o Dossiê 1.
   - **Cada Campo de Formulário:** todo `<label>` de todas as 5 estações deve conter ícone explicando: o conceito contábil/societário do campo, regra/formato aceito e base legal/impacto (ex.: por que *Pró-Labore M1–M3* afeta o *Fator R*; por que *Método de Haveres* tem de bater entre Contrato e MoU; por que *CNAE 6920-6/02* precisa estar no Contrato se houver Auditoria).
   - **Cada Botão de Ação:** tooltip/ícone ou microdescrição clara explicando o efeito real no PostgreSQL (ex.: *"Recalcula os 36 meses do fluxo, DRE, BP e VPL sem sobrescrever outros cenários"*, *"Gera o conjunto de arquivos do Dossiê 1 diretamente do banco"*).
   - **Cada Função / Indicador / Card KPI:** explicação da fórmula exata e critério de decisão (ex.: fórmula `VPL`, `TIR`, `Payback Descontado`, `LTV = Margem Contribuição × Retenção`, `Fator R = FS12 / RBT12 >= 28%`, `IABP = Soma(Média Bloco / 4 × Peso)`, `Check BP = Ativo - Passivo - PL`).
   - **Cada Tabela e Cabeçalho de Coluna:** título institucional numerado + fonte dos dados (`erp.*` / `auditoria.*`) + ícone nas colunas técnicas (`RBT12`, `Fator R`, `Alíq. Efetiva`, `IABP`, `Nota v1`, `Quarentena`, etc.).
3. **Sem poluição visual:** mantenha os ícones `ⓘ` discretos (`#6B7280`, escurecendo para `#1F2937` / `#1E40AF` no hover) para preservar os 70% branco / sobriedade do `DMA-PRISMA-2026-v3`.

---

## 5. Missão 4 — Emissão Completa dos Documentos do Dossiê 1 em PDF (Padrão `DMA-PRISMA-2026-v3`)

Atualmente `sistema/web/exportador_dossie1.py` gera apenas arquivos `.md` e `.xlsx` parciais (por exemplo, ainda não monta o documento completo de Plano de Negócios a partir do banco/narrativa nem emite PDFs oficiais formatados). Você deve **construir a emissão completa em PDF dos documentos necessários do Dossiê 1**, usando **Playwright + Edge (`channel="msedge"`)** e fontes Adwaita conforme `DMA_Guia_Padrao_Visual_PRISMA_JRNA_v3.html` e adaptado do padrão já validado em `G:\Meu Drive\Nath\Trabalho 01\_planejamento\ferramentas\render.py`!

### Pacote de Saída Exigido para Dossiê 1 (gerado em `plataforma/exportacoes/dossie1/` + botão na UI para baixar individualmente ou em lote `.zip`/pasta):
1. **`00_Indice_Geral_Dossie1_PRISMA_JRNA.pdf`**: capa executiva + sumário + quadro de evolução (`v1` vs atual), matriz de coerência cruzada e rastreabilidade extraída do banco + declaração do status de quarentena/homologação real (nunca maquiar itens pendentes!).
2. **`01_Pesquisa_Registro_Profissional_e_Redesim_DF.pdf`**: `Q1`–`Q10` compiladas de `erp.consulta_normativa` + Quadro de Decisões Preliminares (`erp.empresa_decisao_preliminar`) + trecho de IA da Pesquisa.
3. **`02_Plano_de_Negocios_PRISMA_JRNA.pdf`**: seções estratégicas completas do Plano (Sumário Executivo, Missão/Visão/Valores, Canvas 9 blocos, TAM/SAM/SOM com fontes, PESTEL/Porter/Concorrentes, Perfil Fundadoras, Validação/MVP com transparência metodológica sobre D2, Riscos com responsáveis) **obrigatoriamente sincronizadas aos números vivos calculados pelo PostgreSQL (`motor_contabil.py` do cenário oficial)**: Receitas Anos 1–3, DRE, BP (`Check = R$ 0,00`), Fluxo, Ponto de Equilíbrio Fase 1 e 2, VPL, TIR, Paybacks, Unit Economics (`LTV/CAC`), 3 Cenários e Matriz `5×5` de Sensibilidade. *(Se faltarem textos estratégicos no banco para Canvas/PESTEL/TAM-SAM-SOM/Riscos, adicione suporte limpo — ex. tabela ou seção editável em `erp.orcamento_cenario` / nova migração `005` ou seção estruturada no banco alimentada em quarentena a partir de `02_Plano_de_Negocios_PRISMA_JRNA.md` — para que a contadora também possa editar esses textos via CRUD sem hardcode estático!)*
4. **`02_Plano_Financeiro_PRISMA_JRNA_Planilha.pdf`** (junto ao `.xlsx` editável já melhorado para seguir as cores azul/preto/verde e aba `Leia-me` do `DMA v3`!): renderização fiel das tabelas financeiras (`Premissas`, `Fluxo M0-M36`, `DRE 3 Anos`, `Balanço Patrimonial`, `Viabilidade & Unit Economics`, `Cenários & Sensibilidade`) em páginas **paisagem** legíveis.
5. **`03_Contrato_Social_PRISMA_JRNA.pdf`**: Preâmbulo completo + todas as cláusulas de `erp.instrumento_societario_clausula` (`aplica_contrato = true`) + Quadro de Quotas (`erp.participacao_societaria`) + Anexos I–IV — **com texto justificado, hifenização e recuo conforme Regra Seção 03 do `DMA v3`**.
6. **`04_Memorando_de_Entendimentos_MOU_PRISMA_JRNA.pdf`**: Preâmbulo + todas as cláusulas de `erp.instrumento_societario_clausula` (`aplica_mou = true`) + Quadro de Coerência Cruzada (`MoU × Contrato × Plano`) + bloco de testemunhas — **texto justificado**.
7. **`05_Fluxo_Abertura_Empresa_DF_Redesim_e_BPMN.pdf`**: Blocos `A`–`H` compilados de `erp.processo_legalizacao_etapa` + tabela dos 8 órgãos licenciadores do DF + Balanço de Abertura `M0` + **diagrama BPMN vetorial SVG limpo gerado dinamicamente das raias/etapas do banco cabendo integralmente em 1 única página** (requisito `H7` da Matriz, sem depender de internet nem CDNs!) + cadeia de evidências.
8. **`06_Declaracao_Uso_Inteligencia_Artificial_Dossie1.pdf`**: compilado diretamente de `auditoria.diario_ia` (`dossie = 'D1'`).

### Regras Obrigatórias de Qualidade Editorial nos PDFs (`DMA-PRISMA-2026-v3` + `checkpdf.py`):
- Página 1 em A4 retrato com a marca principal (`logo_prisma_jrna_hd.png`), banda Grafite `#1F2937` e **sem rodapé gerado** (nem oculto).
- Páginas 2 a N: cabeçalho com marca horizontal (`simbolo_prisma_jrna.png`) à esquerda + código/seção à direita; marca d'água apenas com símbolo centralizado a 4% de opacidade; rodapé institucional com RT + `Página X de Y`.
- Fontes incorporadas no PDF **exclusivamente `Adwaita Sans` e `Adwaita Mono`** (verificar com `pymupdf`).
- Orientação mista automática (`A4 portrait` / `@page land` `A4 landscape`) para tabelas largas sem quebra de código ou valor; números alinhados à direita; negativos entre parênteses `(142,25)`; badges de status com texto explícito; nenhuma página com menos de `1/4` ocupado (exceto fim natural de seção).
- Incluir **aviso explícito de governança** caso o pacote seja emitido enquanto ainda houver itens não homologados na quarentena (`auditoria.vw_pendencias_quarentena`), permitindo pré-visualizar rascunhos sem enganar a usuária.

---

## 6. Diretrizes de Código, Migração e Critérios de Aceitação

1. **Lean / `/ponytail`:** mantenha Flask + Jinja2 + CSS limpo + JS vanilla mínimo (zero React/Node/Tailwind CDN/bibliotecas pesadas). Não duplique lógica de cálculo: todo número dos PDFs e das telas deve vir exclusivamente de `motor_contabil.py` / PostgreSQL.
2. **Se precisar ampliar o schema PostgreSQL** (por exemplo, para tornar editáveis via CRUD os blocos narrativos do Plano de Negócios como Canvas, TAM/SAM/SOM, PESTEL, Riscos — sem hardcodar textos em Python!), crie uma nova migração incremental `sistema/pg/migrations/005_...sql` seguindo `001`–`004` (`BIGINT GENERATED ALWAYS AS IDENTITY`, índices explícitos em 100% das FKs -> `auditoria.vw_pg_fks_sem_indice` deve permanecer com **0 linhas**, colunas de quarentena/governança e trigger `atualizado_em`).
3. **Verificação Obrigatória antes de concluir:**
   - Rode os testes existentes (`pytest -v sistema/testes/test_pg_banco_unico.py sistema/testes/test_erp_dossie1_motor.py sistema/testes/test_web_dossie1_crud.py`) e crie novos testes verificando a renderização das páginas atualizadas, ajuda contextual, download/emissão dos PDFs do Dossiê 1, incorporação das fontes Adwaita via PyMuPDF e ausência de páginas esparsas/quebradas.
   - Confira visualmente os PDFs e a aplicação web rodando em `http://127.0.0.1:5000`.
4. **Não toque nos diretórios raiz `D1/`, `D2/`, `D3/`, `D4/`, `Resultado/`, `_paginas/` nem modifique arquivos originais em `G:\Meu Drive\Nath\`.** Todo código novo fica dentro de `plataforma/`.

=== FIM DO PROMPT ===
