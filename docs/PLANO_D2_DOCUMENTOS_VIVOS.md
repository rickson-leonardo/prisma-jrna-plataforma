# Plano — Dossiê 2: documentos gerados a partir do banco (de "parcial" para "satisfatório" nos 9 produtos)

> **Status:** 🟢 LIBERADO (26/11/2026) — executar a partir da Fase 1 com os ajustes da Seção 10
> **Autor do plano:** Claude (Claude Code) · **Executor:** Gemini 4 Neon — Orchestrator (Antigravity)
> **Data:** 26/11/2026 · **Repositório:** `plataforma/` (Flask + PostgreSQL/Supabase, deploy Vercel)

## 0. Protocolo de trabalho (ler antes de tudo)

1. **Executor (Gemini)** lê este plano inteiro e o código citado, e **preenche a Seção 9 ("Pontos levantados pelo executor")** com dúvidas, riscos, discordâncias e propostas de ajuste. **Não altera código nesta fase.**
2. **Revisor (Claude)** analisa a Seção 9, responde na **Seção 10** e muda o status para 🟢 **LIBERADO** (ou pede nova rodada).
3. Só com 🟢 o executor implementa, **seguindo as fases da Seção 7, na ordem**, marcando os checkboxes deste arquivo.
4. Ao final de cada fase: rodar os testes indicados, registrar o resultado na **Seção 11 (Diário de execução)** e parar para revisão se algo divergir do plano.

### Ambiente (decisão da usuária em 26/11/2026)
A plataforma vive em **GitHub + Vercel + Supabase**. **Não existe banco local**: o único banco é o **Supabase de produção** (projeto `qyuocganeujiitakpgqp`). O banco do `.env` (localhost) está desatualizado e **não deve ser usado nem apontado para a produção**.

### Regras invioláveis
- **Banco — leitura sim, escrita não:** o executor pode **ler** a produção (consultas e prévias HTML). **Nenhum teste, script ou ação do executor grava no Supabase.** Gravações (migração 008, recálculo da folha com a nova rubrica de 1/3, alertas novos) são feitas **pelo revisor via MCP** ou **pela contadora na tela**, depois do merge.
- **Testes que gravam no banco são proibidos contra a produção.** Estes arquivos fazem `INSERT/UPDATE/DELETE`, importação ou recálculo e **não podem ser executados com conexão ao Supabase**: `test_web_dossie1_crud.py`, `test_web_dossie1_ux_pdf.py`, `test_pg_banco_unico.py`, `test_erp_dossie1_motor.py` (o teste `test_pg_quarentena_motor_e_detector_coerencia` devolve a Q1 para `pendente_revisao`), `test_fase6_7_normalizacao_plataforma.py`, `test_web_dossie2.py`, `test_fase0_base.py`. Com o `.env` em localhost e sem PostgreSQL local, esses testes são **pulados automaticamente** (`skipif _pg_disponivel`) — mantenha assim.
- **Testes novos deste plano são puros (sem banco):** usar `html_documento(doc, dados=...)` (que já aceita os dados por parâmetro) e funções do motor com dicionários montados no próprio teste. Os valores do gabarito (Seção 6) servem de dados de teste.
- **Git e Vercel:** trabalhar no branch `feat/d2-documentos-vivos` e fazer **push só desse branch** — a Vercel gera uma **prévia** (Preview Deployment) para conferência visual. **Proibido** push/merge em `master` (é a produção). O merge é feito pelo revisor, com o ok da usuária.
- **Atenção na prévia da Vercel:** ela usa o banco de produção. Conferir só **lendo** (telas e prévias de documentos); **não salvar formulários** na prévia.
- Commits pequenos por fase, com mensagem em português.
- **Não quebrar o Dossiê 1:** nenhuma mudança de comportamento em telas, motor ou PDFs do D1. A suíte do D1 deve continuar verde.
- **Preservar `origem_registro`:** UPDATE feito pela tela **não** altera `origem_registro` (regra já aplicada em `repo.py` e `repo_d2.py`, commit `e119765`). INSERT pela tela grava `'usuario'`.
- **Nenhum número digitado em documento:** todo valor monetário/percentual exibido vem do banco ou do motor. Sem `or <constante>` como "valor reserva".
- **Abordagem enxuta (ponytail):** sem dependências novas; reaproveitar `d2_doc.html`, macros de `templates/pdf/_m.html`, `texto.brl/brl_tab/md_html`, padrão de `ia.html` e `fluxo_abertura.html` do D1. Nada de abstração que não seja usada por pelo menos dois documentos.
- **Textos da interface e dos PDFs em português com acentos.** Arquivos com final de linha LF.

## 1. Contexto e objetivo

O Dossiê 2 (onboarding e departamento pessoal da Rota Sul, competência 09/2026) exige **9 produtos mínimos** (Estudo de Caso, item 6). A V1 entregue tirou **3,60**. A devolutiva do professor lista, para cada elemento, **o que a régua espera para a nota 4** — essas exigências viraram os **47 critérios** `auditoria.criterio_conformidade` com `dossie='D2'` (matrizes `d2_p1` … `d2_p9`).

**Diagnóstico atual da plataforma:**

| # | Produto | Dados no banco | Documento hoje |
|---|---|---|---|
| 1 | Diagnóstico do Anexo I | `erp.instrumento_societario_clausula` (9 linhas, `empresa_id=1`, `tipo_instrumento='2a_alteracao'`), cadastro (`empresa`, `estabelecimento`, `participacao_societaria`, `pessoa_identificador`) | Texto fixo (`documento_secao`, doc `d2_01_diagnostico`) |
| 2 | Contrato, proposta, termo RT | `erp.contrato_servico` (4: proposta, contrato, termo_rt, procuracao; honorário, 13º, valor-hora, horas, `memoria_horas_json`, vigência, foro) | Texto fixo (docs 02–04) |
| 3 | Checklist, perguntas e respostas | `erp.diligencia_item` (30: `tipo` = documento / pergunta / pendencia; ator, tema, enunciado, resposta_literal, fonte_evidencia, data, responsável, prazo, risco, status) | Texto fixo (doc 05) |
| 4 | Prontuário E1/E2 | `erp.contrato_trabalho` (2: CBO, admissão, experiência, salário, piso, jornada, intervalo, VT, VR, dependentes, ASO, `docs_admissionais_json`), `erp.esocial_evento` (10) | Texto fixo (docs 06–10) |
| 5 | Folha set/2026 | `motor_folha` (bate com o gabarito), `erp.parametro_legal` (19), planilha `.xlsx` com fórmulas | 🟢 Doc 11 já usa `folha_item` |
| 6 | Resumo, encargos, lançamento | Lotes L1–L4 em `erp.lancamento/partida`, conciliação no `.xlsx` | 🟢 Doc 12 já usa as partidas — **mas com constantes digitadas** |
| 7 | Auditoria trabalhista | `erp.auditoria_folha` (15: `tipo_registro` = papel_trabalho / achado; norma, evidência, risco, valor V1, valor recalculado, correção, responsável, prazo, situação) | Texto fixo (doc 13) |
| 8 | Premissas com fonte | `erp.consulta_normativa` com `dossie='D2'` (**PR-01 a PR-18**: enunciado, resposta_autoral, norma_citada, link_oficial, data_acesso, decisao_impactada) + `erp.parametro_legal` | Texto fixo (doc 14) |
| 9 | Declaração de IA | `auditoria.diario_ia` com `dossie='D2'` (7) | Texto fixo (doc 15) |

**Objetivo:** cada um dos 16 documentos do D2 passa a ter **quadros gerados do banco** (o que a régua cobra como estrutura), mantendo as **seções narrativas** (`documento_secao`) para a argumentação. Assim, corrigir um dado na tela corrige o PDF, e a revisão de conteúdo acontece uma única vez, no banco.

**Fora do escopo deste plano:** revisar o *conteúdo* dos registros (isso será feito depois, tela a tela, pela contadora com o revisor); comprovantes simulados do Fluxo do D1; Dossiês 3 e 4.

## 2. Arquivos envolvidos

| Arquivo | Papel | Mudança |
|---|---|---|
| `sistema/web/emissor_dossie2.py` | Carrega dados e renderiza os 16 docs | Carregar as tabelas novas; remover constantes; passar quadros ao template |
| `sistema/web/templates/pdf/d2_doc.html` | Template único do D2 | Blocos de quadros por documento (Seção 4) |
| `sistema/web/templates/pdf/_m.html` | Macros PDF | Reaproveitar `badge`, `ficha`, `assinaturas`; criar no máximo 1 macro de tabela genérica se não existir equivalente |
| `sistema/erp/motor_folha.py` | Motor da folha + `validar_coerencia_dossie2` | Cenário B calculado; provisão de férias e 1/3 separadas; recálculo independente; 3 regras novas |
| `sistema/pg/migrations/008_d2_documentos_vivos.sql` | Nova migração | Colunas nullable (Seção 3) — idempotente |
| `sistema/web/repo_d2.py` + `templates/onboarding.html`, `dp.html`, `folha.html` | Telas do D2 | Campos novos editáveis |
| `sistema/web/repo.py` + `templates/instrumentos.html` / `sustentacao.html` | Telas compartilhadas | Campos novos (achado societário e premissa) só quando o dossiê em foco for D2 |
| `sistema/web/planilha_dossie2.py` | `.xlsx` aberto | Manter; só ajustar se a separação férias/1/3 mudar rubricas |
| `sistema/testes/test_web_dossie2.py` | Testes do D2 | Novos testes (Seção 6) |

## 3. Mudanças no banco (migração 008, idempotente, colunas **nullable**)

Usar `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Não alterar CHECKs existentes. Não popular dados na migração (o conteúdo será preenchido depois pela contadora).

| Tabela | Colunas novas | Uso |
|---|---|---|
| `erp.instrumento_societario_clausula` | `risco_tipo text` (formal / material), `risco_nivel text` (baixo / médio / alto / crítico), `providencia text`, `fundamento_legal text`, `responsavel text`, `prazo_texto text` | Quadro de achados e plano de saneamento R-01…R-09 (P1) |
| `erp.consulta_normativa` | `responsavel_decisao text`, `prazo_decisao text`, `impacto_se_alterada text` | Quadro "decisões e pendências sobre premissas" (P8, critério C-41) |

> Não criar tabelas novas. Se o executor achar que alguma coluna é desnecessária porque o dado já existe em outro campo, registrar na Seção 9.

## 4. Especificação por documento (o que cada PDF passa a mostrar do banco)

Regra geral: no `d2_doc.html`, **depois** do resumo executivo e **antes/depois** das seções narrativas conforme indicado, renderizar os quadros abaixo com `<p class="tt">Tabela N — …</p>`, `<table>` e `<p class="fonte">Fonte: <tabela do banco></p>` (padrão do D1). Valores monetários com `brl_tab`; vazio = "—". Cada quadro mostra o `badge(status_validacao)` por linha quando a tabela tiver esse campo.

### Doc 00 — Índice (`d2_00_indice`)
- [x] Quadro **Produtos 1–9 × documentos**: produto (texto do Estudo de Caso), documentos que o atendem (de `erp.requisito.documentos_json`), nº de registros homologados / total por documento.
- [x] Quadro **Quarentena por módulo** (já carregado em `quarentena`) — reaproveitar o padrão do índice do D1.

### Doc 01 — Diagnóstico societário (P1)
- [x] **Identificação do cliente**: razão social, nome fantasia, natureza jurídica; **matriz e filial** (CNPJ, NIRE quando houver em `pessoa_identificador`, endereço, município/UF); sócios com quotas e % (`participacao_societaria`); capital (integralizado × a integralizar).
- [x] **Quadro de achados do Anexo I** (`instrumento_societario_clausula`, `empresa_id` do D2, ordem): nº da cláusula, achado (`titulo` + `regra_texto`), risco (`risco_tipo` / `risco_nivel`), fundamento legal, providência.
- [x] **Plano de saneamento (3ª alteração contratual)**: mesmas linhas, colunas providência, responsável, prazo, situação.

### Docs 02, 03, 04 — Proposta, contrato e procuração, termo RT (P2)
- [x] **Qualificação das partes** (em todos): contratada = escritório do D1 (`emp:prisma_jrna_g07`: razão social, CNPJ, CRC da PJ, RT e CRC da RT vindos de `pessoa_identificador`) e contratante = Rota Sul (razão social, CNPJ matriz e filial). **Proibido** placeholder `[INSERIR …]`.
- [x] **Condições comerciais** (do `contrato_servico` do próprio documento): honorário mensal, 13º honorário (sim/não e valor), valor-hora, horas/mês, vigência, foro, escopo.
- [x] **Memória de custo** (doc 02): tabela a partir de `memoria_horas_json` (atividade, horas, valor-hora, total) com total calculado no template ou no Python — nunca digitado.
- [x] Doc 04 (termo RT): **rol de pendências do onboarding** = `diligencia_item` com `tipo='pendencia'` e status ≠ concluído (código, pendência, risco, responsável, prazo).

### Doc 05 — Onboarding (P3)
- [x] **Checklist de documentos** (`tipo='documento'`): código, documento/finalidade (`enunciado`), ator, tema, responsável, prazo, status.
- [x] **Perguntas e respostas** (`tipo='pergunta'`): código, pergunta, **resposta literal**, **origem** (`fonte_evidencia`), data da interação, status.
- [x] **Quadro de pendências** (`tipo='pendencia'`): código, pendência, risco, responsável, prazo, providência, status.

### Doc 06 — Prontuário e eSocial (P4)
- [x] **Índice do prontuário por empregado**: para E1 e E2, cada item de `docs_admissionais_json` com status real (entregue / pendente / não aplicável). ASO com `aso_status` e `aso_observacao` — **nunca** marcado como entregue se o banco disser pendente.
- [x] **Roteiro eSocial** (`esocial_evento`, por empregado): evento, nome, competência, prazo legal, status de envio, **nº do recibo ou "não transmitido"**. Proibido exibir recibo inexistente.
- [x] **Termos de VT e VR**: optante, passagens/dia, tarifa, elegível VR, valor/dia (de `contrato_trabalho`).

### Docs 07 e 09 — Fichas de registro (P4)
- [x] **Ficha gerada de `contrato_trabalho`**: nome (fictício), CPF (fictício), cargo, CBO, departamento, estabelecimento, admissão, salário, **piso da CCT e referência** (`piso_cct_centavos`, `cct_referencia`), jornada (`jornada_descricao`, `jornada_semanal_horas`, `intervalo_minutos` mostrado em h:min), VT, VR, dependentes (IRRF e salário-família), ASO.

### Docs 08 e 10 — Contratos de experiência (P4)
- [x] **Quadro-resumo no topo**, de `contrato_trabalho`: prazos (`experiencia_dias_1` + `experiencia_dias_2`), salário, comissão (% de `comissao_pct_micro`), jornada e intervalo. As cláusulas seguem nas seções narrativas.

### Docs 11 e 12 — Folha e resumo (P5, P6)
- [x] Manter o que existe.
- [x] **Remover todas as constantes** de `_marcadores_d2` e do `resumo_exec` (`283333`, `21268`, `22667`, `241630`, **`251065`**, `50400`, `412800`, `23400`, `33000`, `91740`, `423800`): cada marcador vem de `folha_competencia`, de somas de `folha_item` por `codigo_rubrica` ou de `partida`. Se faltar dado → "—".
- [x] **Líquido do Cenário B** (sem contribuição negocial) **calculado**: líquido do cenário A + soma das rubricas `NEGOCIAL`.
- [x] **Impacto da exclusão do Simples** (`IMPACTO_EXCLUSAO_SIMPLES`): calcular a partir da folha (CPP patronal 20% + RAT + terceiros sobre a base, com alíquotas em `parametro_legal`) ou, se o motor já calcular, ler do motor — registrar na Seção 9 qual caminho.
- [x] Doc 12: quadro **Conciliação** folha × resumo × lançamento com a diferença (deve ser R$ 0,00), a partir das somas do banco.

### Doc 13 — Auditoria trabalhista (P7)
- [x] **Planejamento (PT-01)**: objetivos, população, materialidade, riscos — vindo dos `auditoria_folha` com `tipo_registro='papel_trabalho'`.
- [x] **Papéis de trabalho**: código, título, norma, objetivo/evidência, procedimento/risco, conclusão, situação.
- [x] **Recálculo independente (100% dos empregados)**: tabela por empregado × rubrica com **V1** (`valor_v1_centavos` quando houver), **motor** (`folha_item`) e **recálculo independente** (função nova, item 5.3) e a diferença.
- [x] **Achados AUD-01…AUD-10** (`tipo_registro='achado'`): código, achado, evidência, risco, valor (V1 × recalculado), correção, responsável, prazo, situação.

### Doc 14 — Premissas (P8)
- [x] **Registro numerado PR-01…PR-18** (`consulta_normativa`, `dossie='D2'`, ordem por `numero_questao`): premissa (`enunciado`), decisão e motivo (`resposta_autoral`), documentos impactados (`decisao_impactada`), fonte (`norma_citada`), link e data de acesso.
- [x] **Quadro de decisões e pendências**: premissa, quem decide (`responsavel_decisao`), prazo (`prazo_decisao`), impacto se alterada (`impacto_se_alterada`).
- [x] **Tabelas oficiais usadas** (`parametro_legal` por categoria): INSS (faixas e alíquotas), IRRF (faixas, deduções, redução 2026), salário-família, FGTS, cláusulas da CCT — cada linha com norma, link e data de consulta.

### Doc 15 — Declaração de IA e LGPD (P9)
- [x] Mesmo padrão do `ia.html` do D1, filtrando `diario_ia` por `dossie='D2'`: entregável, ferramenta, **finalidade**, **comandos resumidos** (`prompt_resumo`), **verificação em fonte oficial** (`fonte_oficial`), **revisão humana**, situação. Manter as seções narrativas (LGPD) e as assinaturas.

## 5. Motor, regras de auditoria e telas

### 5.1 Regras novas em `validar_coerencia_dossie2` (motor_folha.py)
- [x] `D2_TEXTO_RESIDUO` (crítico): procura em `documento_secao` (D2) e `contrato_servico.conteudo_md` os padrões `[INSERIR`, `[cite`, `1.555/2018`, `XX.XXX`, `TODO`, `???`. Lista documento e trecho.
- [x] `D2_PROPOSTA_CONTRATO_DIVERGENTE` (alerta): compara entre proposta, contrato e termo RT: honorário mensal, `tem_decimo_terceiro`, vigência. Divergência = alerta com os valores.
- [x] `D2_SALARIO_ABAIXO_PISO` (crítico): `salario_base_centavos < piso_cct_centavos` (considerar garantia do comissionado se houver parâmetro). Também alerta se `piso_cct_centavos` ou `cct_referencia` estiverem vazios.
- [x] `D2_RECALCULO_DIVERGENTE` (crítico): diferença ≠ 0 entre motor e recálculo independente em qualquer rubrica.

### 5.2 Ajustes no motor
- [x] Provisão de férias e de 1/3 em **rubricas separadas** (`PROV-FER` = 1/12 do salário; `PROV-1/3` = 1/3 disso), mantendo o total (E1: R$ 200,00 + R$ 66,67). Ajustar a planilha `.xlsx` se ela referenciar a rubrica combinada. (Critério C-29.)
- [x] Persistir/expor o **líquido do cenário B** (sem negocial) — ou calcular no emissor a partir das rubricas (escolher o mais simples e registrar).

### 5.3 Recálculo independente
- [x] Função `recalcular_folha_independente(conn, competencia_id) -> list[dict]` em `motor_folha.py`, **sem reutilizar** as funções de cálculo do motor (implementação direta e curta a partir de `contrato_trabalho` + `parametro_legal` + `folha_competencia`): salário proporcional, comissão e DSR, INSS progressivo, IRRF, FGTS, VT (6% limitado ao custo), VR, contribuição negocial, salário-família. Retorna por empregado × rubrica: valor do motor, valor recalculado, diferença.

### 5.4 Telas
- [x] Instrumentos (quando dossiê em foco = D2): campos `risco_tipo`, `risco_nivel`, `providencia`, `fundamento_legal`, `responsavel`, `prazo_texto`.
- [x] Sustentação → Consultas (quando D2): `responsavel_decisao`, `prazo_decisao`, `impacto_se_alterada`.
- [x] Verificar que onboarding, DP e folha já permitem editar todos os campos usados nos quadros; acrescentar os que faltarem.
- [x] O D1 não exibe esses campos novos.

## 6. Testes (pytest **puros**, sem banco — ver Seção 0)

Montar no teste um dicionário `dados` no formato de `carregar_dados_dossie2()` (fixture em `sistema/testes/`), com os valores do caso e do gabarito, e chamar `html_documento(doc, dados=dados)`. As regras de auditoria devem ter a lógica em **funções puras** (recebem listas/dicts e devolvem alertas), chamadas por `validar_coerencia_dossie2` — assim são testáveis sem banco.

- [x] `test_d2_documentos_sem_constantes`: nenhum valor das constantes da Seção 4 (Docs 11/12) aparece literalmente em `emissor_dossie2.py`; o resumo usa os dados recebidos.
- [x] `test_d2_quadros_por_documento`: para cada doc 00–15, a prévia HTML contém o título da(s) tabela(s) especificada(s) e pelo menos 1 linha vinda dos dados (ex.: PR-01 no doc 14; AUD- no doc 13; DOC- no doc 05; S-2200 no doc 06; CBO 4110-05 no doc 07).
- [x] `test_d2_dado_muda_pdf_muda`: alterar um campo no dicionário (ex.: `intervalo_minutos` do E1, ou `honorario_mensal_centavos` da proposta) e verificar que a prévia reflete o novo valor.
- [x] `test_d2_regras_novas`: chamar as funções puras das regras com dados que provocam cada alerta (texto com `[INSERIR`, proposta ≠ contrato, salário < piso, recálculo divergente) e com os falsos positivos do item 4 da Seção 9 (que devem dar zero alertas).
- [x] `test_d2_recalculo_independente_bate_com_gabarito`: E1 INSS 90,00 / FGTS 96,00 / VR 330,00 / negocial 39,96; E2 comissão 900,00 / DSR 100,00 / INSS 122,68 / FGTS 130,67 / negocial 54,39; diferença zero contra o motor.
- [x] `test_d2_cenario_b`: líquido B = líquido A + soma de NEGOCIAL (R$ 2.510,65 com os dados atuais) — sem constante.
- [x] Suíte existente: rodar `pytest sistema/testes` com o `.env` apontando para localhost (sem PostgreSQL): os testes puros devem passar e os de banco devem aparecer como **pulados** — nunca como executados contra o Supabase.
- [ ] Conferência de integração (sem gravar): na **prévia da Vercel** do branch, abrir as prévias dos 16 documentos do D2 e 3 do D1, que leem a produção. Registrar o resultado na Seção 11.

## 7. Fases de execução (ordem obrigatória)

- [ ] **Fase 0 — Pré-requisito do revisor:** aplicar a migração 008 em produção via MCP (colunas novas e opcionais; não afeta o código atual) antes de o executor precisar ler as colunas novas na prévia da Vercel.
- [x] **Fase 1 — Base:** branch, arquivo da migração 008 (só o arquivo; quem aplica é o revisor), remoção das constantes, cenário B calculado, regra `D2_TEXTO_RESIDUO`. Testes: `test_d2_documentos_sem_constantes`, `test_d2_cenario_b` + suíte existente.
- [x] **Fase 2 — Docs 00, 05, 06, 07, 09, 14, 15** (dados já completos no banco). Testes de quadros.
- [x] **Fase 3 — Docs 01, 02, 03, 04, 08, 10** + regras `D2_PROPOSTA_CONTRATO_DIVERGENTE` e `D2_SALARIO_ABAIXO_PISO` + telas da Seção 5.4.
- [x] **Fase 4 — Doc 13 + recálculo independente + separação férias/1/3 + regra `D2_RECALCULO_DIVERGENTE`** (planilha `.xlsx` ajustada se preciso).
- [ ] **Fase 5 — Verificação final:** suíte completa (puros passando, de banco pulados), push do branch, conferência na **prévia da Vercel** das prévias dos 16 documentos + `.xlsx` (sem salvar nada), conferência visual de 3 documentos (01, 06, 13), registro no Diário (Seção 11) com o resumo dos commits e a URL da prévia.
- [ ] **Fase 6 — Produção (revisor + usuária):** com o ok da usuária, merge em `master` (deploy Vercel); o revisor dispara o recálculo da folha (nova rubrica de 1/3) e a revalidação, e confere os alertas `D2_*` via MCP.

## 8. Critérios de aceite (produto a produto → "satisfatório")

| Produto | Aceite (o que a régua da devolutiva pede para o 4) |
|---|---|
| 1 | Identificação de matriz e filial; achados por cláusula com risco formal × material, fundamento e providência; plano de saneamento com responsável e prazo — tudo do banco |
| 2 | Partes qualificadas sem campos em branco; condições e memória de custo do banco; regra acusa divergência proposta × contrato × termo; termo RT com rol de pendências |
| 3 | Checklist com responsável e status; respostas literais com origem; quadro de pendências com responsável, prazo e providência |
| 4 | Prontuário com índice e status real por peça; fichas e contratos coerentes com `contrato_trabalho`; roteiro eSocial sem recibo inventado; VT/VR e dependentes |
| 5 | Já atende (motor + planilha com fórmulas) — manter verde |
| 6 | Sem constantes; provisões separadas; conciliação com diferença zero exibida |
| 7 | Planejamento, papéis de trabalho, recálculo independente de 100% e achados com risco, valor, responsável e prazo |
| 8 | PR-01…PR-18 com decisão, motivo, impacto, fonte, link e data; quadro de decisões; tabelas oficiais |
| 9 | Diário de IA do D2 com finalidade, comandos, verificação e revisão humana por registro |
| Geral | Corrigir um dado na tela altera o PDF; nenhuma marca de rascunho/IA (`[INSERIR`, `[cite`) passa sem alerta crítico; D1 intacto |

## 9. Pontos levantados pelo executor (Gemini preenche)

> Liste aqui, numerados: dúvidas, riscos, discordâncias técnicas, itens que já existem no código e não precisam ser feitos, estimativa de esforço por fase e qualquer mudança proposta ao plano. **Não implementar antes da liberação.**

### A. O que já existe no código / banco e pode ser dispensado ou reaproveitado direto

1. **Estação 7 (`repo_d2.carregar_onboarding` e `onboarding.html`) já lê o escritório do D1 sem redigitação:** a query que busca `emp:prisma_jrna_g07` (razão social, CNPJ, `registro_crc` da PJ, `rt_nome`, `rt_crc` e endereço da sede) já está pronta em `repo_d2.py` (linhas 58–73). Basta mover/reaproveitar a mesma consulta em `emissor_dossie2.carregar_dados_dossie2()` para alimentar a qualificação das partes nos Docs 02, 03 e 04.
2. **Motor da folha (`motor_folha.recalcular_folha_d2`) já calcula Cenário B, 1/3 de férias separado em memória e Impacto da Exclusão do Simples:**
   - Em `motor_folha.py` (linhas 298–308 e 450–452), `tot["liq_b"]` (`251_065`), `pfer` (`20_000`), `pter` (`6_667`) e `exclusao_simples_extra` (`91_740`) já são calculados e inclusive testados em `test_motor_folha_d2_reconciliacao_e_partidas_dobradas()`.
   - **Caminho escolhido para `LIQUIDO_B`, `SUBSIDIO_VT`, `VR_TOTAL` e `IMPACTO_EXCLUSAO_SIMPLES` (Seção 4, Docs 11/12 e Seção 5.2):** calcular no emissor a partir das rubricas de `erp.folha_item` e parâmetros de `erp.parametro_legal` (sem adicionar colunas redundantes em `folha_competencia`):
     - `LIQUIDO_B` = `comp["liquido_total_centavos"] + sum(valor_centavos de codigo_rubrica == 'NEGOCIAL')` (quando `cenario_negocial == 'A_desconta'`, ou igual ao líquido quando `'B_patronal'`).
     - `SUBSIDIO_VT` = soma de `folha_item` com `codigo_rubrica == 'VT-SUBS'`.
     - `VR_TOTAL` = soma de `folha_item` com `codigo_rubrica == 'VR-PAT'`.
     - `IMPACTO_EXCLUSAO_SIMPLES` = `_round_cent(Decimal(base_exclusao) * Decimal("0.278"))` (ou lido de `parametro_legal` se parametrizado), onde `base_exclusao` = soma de `valor_centavos` dos `folha_item` com `tipo_rubrica == 'provento'` + `codigo_rubrica in ('PROV-13', 'PROV-FER', 'PROV-1/3')`. Se `comp` ou `itens` estiverem vazios, todos retornam `"—"`.
3. **Telas de Onboarding, DP e Folha já editam quase 100% dos campos dos quadros:**
   - `onboarding.html` já edita todos os campos escalares de `contrato_servico` e `diligencia_item` (faltando apenas `data_interacao` no form de edição de `diligencia_item` — hoje `salvar_diligencia` lê `form.get("data_interacao")`, mas o `<input type="date" name="data_interacao">` não está no template `onboarding.html`).
   - `dp.html` já edita todos os campos escalares de `contrato_trabalho`, `parametro_legal` e `esocial_evento`, exceto `jornada_semanal_horas` e `cct_referencia` (que existem na tabela `erp.contrato_trabalho`, mas não têm `<input>` em `dp.html` nem estão no `UPDATE` de `salvar_contrato_trabalho`) e `data_consulta` em `parametro_legal`.
   - `folha.html` já edita todos os campos de `folha_competencia` e `auditoria_folha`, exceto `valor_v1_centavos` e `valor_recalculado_centavos` em `auditoria_folha` (que existem na tabela `erp.auditoria_folha`, mas não estão no form de `folha.html` nem no `UPDATE` de `salvar_auditoria_item`).
   - **Proposta:** incluir esses inputs faltantes (`data_interacao` em `onboarding.html`; `jornada_semanal_horas`, `cct_referencia` e `data_consulta` em `dp.html`/`repo_d2.py`; `valor_v1_reais` e `valor_recalculado_reais` em `folha.html`/`repo_d2.py`) na Fase 3 para cumprir 100% da regra *"corrigir um dado na tela altera o PDF"*.

---

### B. Dúvidas, riscos e discordâncias técnicas (com propostas de ajuste)

4. **[CRÍTICO — Falso positivo em `D2_TEXTO_RESIDUO` (Seção 5.1)]:**
   Inspecionando o banco local (`erp.documento_secao` e `erp.contrato_servico` do D2), uma busca ingênua pelos padrões `[INSERIR`, `[cite`, `1.555/2018` e `TODO` dispara **25 falsos positivos** no texto atual:
   - `"TODO"`: casa em case-insensitive com as palavras em português `"todos os documentos"`, `"todo o contrato"`, `"todo dia 10"`. **Correção obrigatória:** exigir `TODO` em maiúsculas com word-boundary (`r"\bTODO\b"` sem `re.IGNORECASE`, ou seguido de `:` / `[`).
   - `"[INSERIR"`, `"[cite"` e `"1.555/2018"`: aparecem nas seções narrativas de auditoria/histórico da V2 explicando o que foi corrigido em relação à V1 (ex.: ``Eliminados campos `[INSERIR]` ``, ``Removidos os 6 resíduos `[cite: 19, 25]` ``, ``Substituiu a revogada Res. CFC 1.555/2018 pela Res. CFC nº 1.708/2023``).
   - **Proposta de ajuste para `D2_TEXTO_RESIDUO`:**
     1. Para `[INSERIR` e `[cite`: ignorar ocorrências envoltas em crases de código inline (`` `...` ``) ou cujo contexto imediato (±40 caracteres) contenha palavras de saneamento (`eliminado`, `removido`, `expurgo`, `saneado`, `substitu`). Ou, melhor ainda: para `[INSERIR`, casar placeholders reais abertos fora de backticks (`r"(?<!`)\[INSERIR[^\]\n]*\](?!`)"`); para `[cite`, casar `r"(?<!`)\[cite[^\]]*\](?!`)"`.
     2. Para `1.555/2018`: só alertar se a linha/parágrafo mencionar `1.555/2018` **sem** mencionar `revogad` ou `1.708/2023` na mesma sentença.
     3. Confirmar se o revisor concorda com essa heurística contextual para que o banco atual (saneado) fique com 0 alertas `D2_TEXTO_RESIDUO`, mas qualquer `[INSERIR ...]` ou `[cite: ...]` real fora de citação histórica dispare alerta crítico imediato.

5. **[CRÍTICO — Divergência atual entre Proposta, Contrato e Termo RT no banco (`D2_PROPOSTA_CONTRATO_DIVERGENTE`)]:**
   No banco local hoje (`erp.contrato_servico`), temos:
   - `proposta`: `honorario_mensal_centavos = 400000`, `tem_decimo_terceiro = True`, `vigencia_inicio = 2026-09-14`
   - `contrato`: `honorario_mensal_centavos = 400000`, `tem_decimo_terceiro = True`, `vigencia_inicio = 2026-09-01`
   - `termo_rt`: `honorario_mensal_centavos = 400000`, `tem_decimo_terceiro = True`, `vigencia_inicio = 2026-09-01`
   - `procuracao`: `honorario_mensal_centavos = 0`, `vigencia_inicio = 2026-09-14`
   Como `proposta.vigencia_inicio` é `2026-09-14` (data da assinatura da proposta) e `contrato`/`termo_rt` têm `2026-09-01` (início da competência contábil 09/2026), se a regra `D2_PROPOSTA_CONTRATO_DIVERGENTE` comparar `vigencia_inicio` com igualdade estrita entre os 3, o banco padrão ficará permanentemente com alerta ativo (a menos que a contadora iguale as datas na tela).
   - **Dúvida ao revisor:** É intencional que `D2_PROPOSTA_CONTRATO_DIVERGENTE` já nasça disparando esse alerta sobre `2026-09-14` vs. `2026-09-01` para a contadora sanear na tela (ou comparar apenas mesmo mês/ano `YYYY-MM`, ou comparar estritamente `vigencia_inicio` para que ela alinhe para `2026-09-01`)? E confirmar que `codigo_documento = 'procuracao'` fica excluído dessa comparação comercial.

6. **[IMPORTANTE — Separação de `PROV-FER` e `PROV-1/3` (Seção 5.2) × Planilha `.xlsx` × `folha.html`]:**
   - Hoje `motor_folha.py` grava 3 rubricas de provisão para E1: `PROV-13` (ordem 12, R$ 200,00), `PROV-FER` (ordem 13, R$ 266,67 = férias + 1/3) e `PROV-FGTS` (ordem 14, R$ 37,33).
   - Ao separar em 4 rubricas (`PROV-13` ordem 12 = `20_000`; `PROV-FER` ordem 13 = `20_000`; `PROV-1/3` ordem 14 = `6_667`; `PROV-FGTS` ordem 15 = `37_33`), o total `provisoes_total_centavos` continua `50_400` (R$ 504,00).
   - **Efeito no Lote L4 (`erp.partida`) e na Planilha (`planilha_dossie2.py`):**
     - No plano de contas (`CONTAS_FOLHA_D2`), as contas `4.1.1.08` (*Despesas Administrativas — Provisão Férias e 1/3 (E1)*) e `2.1.2.11` (*Provisão para Férias e 1/3 Constitucional*) contabilizam o passivo/despesa conjunto de R$ 266,67 no Lote L4.
     - Na planilha `planilha_dossie2.py`, a aba `Provisoes_e_Integracao` usa posições fixas de linha (`rows 6..9` para provisões, `rows 12..32` para L1–L4 e `rows 35..43` para conciliação), e a aba `Memoria_Calculo` referencia `Provisoes_e_Integracao!E8` e `Provisoes_e_Integracao!E9`.
     - **Proposta ponytail:** separar as rubricas em `erp.folha_item` (`PROV-FER` = R$ 200,00 e `PROV-1/3` = R$ 66,67) — que é o que aparece nos PDFs Docs 11 e 12 — e na aba `Provisoes_e_Integracao` da planilha podemos manter o Lote L4 contábil nas contas `4.1.1.08`/`2.1.2.11` (R$ 266,67) ou adicionar uma linha na tabela de provisões ajustando as referências `E8`/`E9` → `E9`/`E10`. Manter L4 nas contas existentes evita criar contas contábeis novas desnecessárias. Confirmar se na planilha `.xlsx` deseja que a linha 7 seja desdobrada em duas linhas (Férias 1/12 e 1/3 Constitucional) ou se a separação em `erp.folha_item` (Docs 11 e 12) já atende integralmente ao critério C-29.

7. **[DÚVIDA — Dados de Natureza Jurídica, NIRE da Filial e Capital Integralizado × A Integralizar no Doc 01 (Seção 4, Doc 01)]:**
   Verifiquei o esquema de `erp.empresa` e `erp.estabelecimento` no banco local:
   - `erp.empresa` **não possui** colunas `natureza_juridica`, `capital_integralizado_centavos` ou `capital_a_integralizar_centavos`.
   - Porém, esses dados **já existem no banco** em tabelas correlatas:
     - **Capital social atual (R$ 1.500.000,00)**: soma de `erp.participacao_societaria.valor_centavos` (`75_000_000 + 75_000_000 = 150_000_000`) e também em `erp.fato` (`chave = 'fato:d2:rs:capital_depois'`, `valor_centavos = 150000000`, `valor_texto = 'R$ 1.500.000,00 (R$ 1.000.000,00 integralizados + R$ 500.000,00 a integralizar)'`), enquanto `fato:d2:rs:capital_antes` tem `valor_centavos = 100000000` (R$ 1.000.000,00 integralizados).
     - **NIRE da Matriz (`52900000015`)**: está em `erp.pessoa_identificador` (`pessoa_id = 1, tipo_id = 'NIRE'`). O NIRE da Filial (`42900000012`) consta no texto de `erp.estabelecimento.endereco` da filial.
     - **Enquadramento / Regime / CNAEs**: estão em `erp.enquadramento_historico` (`empresa_id = 1`).
   - **Proposta:** No quadro de Identificação do Cliente (Doc 01), montar a ficha a partir de `erp.empresa` + `erp.estabelecimento` + `erp.participacao_societaria` + `erp.pessoa_identificador` + `erp.enquadramento_historico` + `erp.fato` (`capital_antes` = integralizado R$ 1.000.000,00; `capital_depois - capital_antes` = a integralizar R$ 500.000,00). Zero colunas extras em `erp.empresa` e zero constantes digitadas.

8. **[DÚVIDA — Doc 00 Índice: filtro de `erp.requisito` e contagem de homologados por documento]:**
   - Em `erp.requisito` para `dossie_id = 2`, existem 11 linhas: 9 linhas `D2-P1`..`D2-P9` (que têm `ordem = 1..9` e `documentos_json` preenchido) e 2 linhas legadas do acervo (`D2-REQ-01` e `D2-REQ-02`, com `ordem IS NULL` e `documentos_json IS NULL`).
   - **Proposta:** filtrar `WHERE dossie_id = (SELECT id FROM erp.dossie WHERE codigo = 'D2') AND documentos_json IS NOT NULL ORDER BY ordem` para listar exatamente os Produtos 1–9.
   - Para a coluna **"nº de registros homologados / total por documento"**: calcular em Python em `emissor_dossie2.py` somando os registros das tabelas que alimentam cada documento (ex.: `documento_secao` daquele doc + tabela específica como `instrumento_societario_clausula` no doc 01, `contrato_servico` nos docs 02–04, `diligencia_item` no doc 05, `contrato_trabalho`/`esocial_evento` nos docs 06–10, `folha_competencia`/`folha_item` nos docs 11–12, `auditoria_folha` no doc 13, `consulta_normativa`/`parametro_legal` no doc 14, `diario_ia` no doc 15), além de passar `pend_doc` individual por documento para a capa (`_base.html` / `m.aviso()`).

9. **[DÚVIDA — Formato de `memoria_horas_json` no Doc 02 e edição na tela]:**
   - No banco local, `erp.contrato_servico.memoria_horas_json` já está populado na proposta e no contrato com 5 itens no formato:
     `[{"frente": "Setup Fee (Implantação)", "horas": 16, "valor_hora": 125, "total": 2000}, ...]` (valores em reais inteiros no JSON).
   - **Proposta:** No Doc 02, calcular cada linha como `horas * valor_hora_centavos` (ou `int(item["valor_hora"]) * 100`) e a soma total em Python, formatando com `brl_tab` (sem usar o `"total"` pré-gravado se `horas` ou `valor_hora` mudarem).

10. **[DÚVIDA — Escopo das rubricas em `recalcular_folha_independente` (Seção 5.3 e `D2_RECALCULO_DIVERGENTE`)]:**
    - A Seção 5.3 lista: *"salário proporcional, comissão e DSR, INSS progressivo, IRRF, FGTS, VT (6% limitado ao custo), VR, contribuição negocial, salário-família"*.
    - Na Seção 4 (Doc 13) e 5.1 (`D2_RECALCULO_DIVERGENTE`), pede-se comparar todas as rubricas do motor (`folha_item`) contra o recálculo independente.
    - **Proposta:** incluir também no `recalcular_folha_independente` o subsídio de VT (`VT-SUBS`) e as provisões (`PROV-13`, `PROV-FER`, `PROV-1/3`, `PROV-FGTS`), pois elas também são linhas de `erp.folha_item`. Assim, o confronto 100% `folha_item` × `recalcular_folha_independente` bate em **todas** as rubricas sem exceção e com diferença zero.
    - Sobre a coluna **V1 (`valor_v1_centavos`)** na tabela de recálculo do Doc 13: como `valor_v1_centavos` hoje fica em `erp.auditoria_folha` (por achado `AUD-01..10`, e não por `codigo_rubrica`), propomos exibir `valor_v1_centavos` na tabela de Achados (`AUD-01..10`: Valor V1 × Valor Recalculado × Diferença) e, na tabela de Recálculo Independente por Empregado × Rubrica, exibir: `Empregado | Rubrica | Base (R$) | Motor (R$) | Recálculo Independente (R$) | Diferença (R$)`, ou mapear os valores V1 conhecidos quando houver achado vinculado à rubrica. Confirmar preferência.

11. **[OBSERVAÇÃO — Cabeçalho de `ficha()` e `aviso()` em `templates/pdf/_m.html`]:**
    - Em `_m.html` (linhas 16 e 27), as macros `aviso()` e `ficha()` têm o texto literal `"Dossiê 1"` hardcoded (`"registro(s) do Dossiê 1"` e `"({{ info.curto }} (Dossiê 1))"`).
    - **Proposta:** trocar `"Dossiê 1"` por `{{ info.get('dossie_label', 'Dossiê 1') }}` em `_m.html`. Não muda uma única letra na saída do D1 (cujo fallback é `'Dossiê 1'`) e corrige a capa de todos os 16 documentos do D2 (que já definem `'dossie_label': 'Dossiê 2'` em `emissor_dossie2.DOCUMENTOS`).

---

### C. Estimativa de esforço por fase e estratégia de execução

| Fase | Escopo resumido | Arquivos tocados | Estimativa |
|---|---|---|---|
| **Fase 1 — Base** | Branch `feat/d2-documentos-vivos`, migração `008_d2_documentos_vivos.sql` (local), remoção de 100% das constantes de `emissor_dossie2.py`, cálculo dinâmico de `LIQUIDO_B` / `SUBSIDIO_VT` / `VR_TOTAL` / `IMPACTO_EXCLUSAO_SIMPLES`, regra `D2_TEXTO_RESIDUO` e testes `test_d2_documentos_sem_constantes` + `test_d2_cenario_b`. | `008_d2_documentos_vivos.sql`, `emissor_dossie2.py`, `motor_folha.py`, `test_web_dossie2.py` | ~25 min |
| **Fase 2 — Docs 00, 05, 06, 07, 09, 14, 15** | Carregamento de `requisito`, `diligencia_item`, `esocial_evento`, `consulta_normativa` (D2) e `diario_ia` (D2) em `emissor_dossie2.py`; blocos de quadros em `d2_doc.html` + ajuste de `dossie_label` em `_m.html`; testes de quadros para esses 7 docs. | `emissor_dossie2.py`, `d2_doc.html`, `_m.html`, `test_web_dossie2.py` | ~40 min |
| **Fase 3 — Docs 01, 02, 03, 04, 08, 10 + Regras + Telas** | Carregamento de `instrumento_societario_clausula`, `participacao_societaria`, `pessoa_identificador`, `fato`, `escritorio_d1` e `contrato_servico`; quadros dos Docs 01–04, 08, 10 e conciliação no Doc 12; regras `D2_PROPOSTA_CONTRATO_DIVERGENTE` e `D2_SALARIO_ABAIXO_PISO`; campos novos em `instrumentos.html`, `sustentacao.html`, `dp.html`, `onboarding.html`, `folha.html`, `repo.py` e `repo_d2.py`. | `emissor_dossie2.py`, `d2_doc.html`, `motor_folha.py`, `repo.py`, `repo_d2.py`, `instrumentos.html`, `sustentacao.html`, `dp.html`, `onboarding.html`, `folha.html`, `test_web_dossie2.py` | ~55 min |
| **Fase 4 — Doc 13 + Recálculo + Férias/1/3** | Separação `PROV-FER` e `PROV-1/3` no motor (e ajuste na planilha se aplicável); função `recalcular_folha_independente`; regra `D2_RECALCULO_DIVERGENTE`; quadros do Doc 13 (PT-01..05, recálculo 100%, AUD-01..10); testes `test_d2_recalculo_independente_bate_com_gabarito`, `test_d2_regras_novas`, `test_d2_dado_muda_pdf_muda`. | `motor_folha.py`, `planilha_dossie2.py`, `emissor_dossie2.py`, `d2_doc.html`, `test_web_dossie2.py` | ~45 min |
| **Fase 5 — Verificação final** | Execução da suíte completa (D1 + D2), emissão local dos 16 PDFs + `.xlsx` via Playwright/Edge, inspeção visual e editorial (`verificar_pdf`) dos Docs 01, 06 e 13, preenchimento do Diário de Execução (Seção 11). | `PLANO_D2_DOCUMENTOS_VIVOS.md` | ~25 min |
| **Total estimado** | **5 fases com commits atômicos em português e verificação contínua** | **13 arquivos** | **~3h10min** |

## 10. Resposta do revisor (Claude preenche)

> Revisado em 26/11/2026. Pontos de dados conferidos também no **banco de produção** (o local pode estar desatualizado): as vigências do item 5 são idênticas em produção; o código do motor confirma os itens 2 e 6.

**1–3 (reaproveitamento):** ✅ Aprovados. Reaproveitar a consulta do escritório de `repo_d2.py` (sem duplicar SQL: extrair para uma função usada pelos dois lugares). Incluir os inputs faltantes (`data_interacao`, `jornada_semanal_horas`, `cct_referencia`, `data_consulta`, `valor_v1`, `valor_recalculado`) na Fase 3, como proposto.

**2 (`IMPACTO_EXCLUSAO_SIMPLES`) — ajuste obrigatório:** ❌ **Não** escrever `0.278` no emissor (seria uma constante nova duplicada). Extrair do motor uma função única, por exemplo `impacto_exclusao_simples(itens) -> int` em `motor_folha.py`, usada **pelo motor e pelo emissor**. A alíquota de 27,8% fica num só lugar: se existir parâmetro em `parametro_legal`, ler de lá; se não, uma constante nomeada no motor com comentário `# ponytail:` dizendo a composição (CPP 20% + RAT + terceiros) e que a evolução é parametrizá-la. `LIQUIDO_B`, `SUBSIDIO_VT` e `VR_TOTAL` a partir das rubricas: ✅ aprovado.

**4 (`D2_TEXTO_RESIDUO`):** ✅ Aprovada a heurística contextual: `\bTODO\b` sensível a maiúsculas; `[INSERIR…]` e `[cite…]` só fora de crases; `1.555/2018` só se a mesma frase não tiver `revogad` nem `1.708/2023`. Severidade **crítica**. O teste deve cobrir: (a) os falsos positivos atuais → 0 alertas; (b) um `[INSERIR CNPJ]` real fora de crases → alerta. Observação para depois (conteúdo, não código): os trechos narrativos que contam "o que foi corrigido em relação à V1" serão revistos pela contadora na fase de conteúdo.

**5 (vigências) — decisão:** a proposta tem data própria (14/09, assinatura da proposta) e **não** entra na comparação de vigência. A regra `D2_PROPOSTA_CONTRATO_DIVERGENTE` compara:
- **contrato × termo RT:** `vigencia_inicio` igual (hoje 01/09 = 01/09 → sem alerta);
- **proposta × contrato × termo RT:** `honorario_mensal_centavos`, `tem_decimo_terceiro` e `valor_hora_centavos` iguais;
- `procuracao` fica **fora** da comparação comercial.

**6 (férias e 1/3):** ✅ Separar em `folha_item` (`PROV-FER` = R$ 200,00 e `PROV-1/3` = R$ 66,67, ordens 13 e 14; `PROV-FGTS` vai para 15). **Contabilidade:** manter o Lote L4 nas contas existentes `4.1.1.08`/`2.1.2.11` (férias + 1/3 numa conta é prática usual). **Planilha:** desdobrar também a linha de provisões em duas (é a memória de cálculo avaliada no P5/P6), ajustando as referências `E8`/`E9`; o teste da planilha deve confirmar que os totais (R$ 504,00 e as partidas L4) não mudam.

**7 (Doc 01):** ✅ Aprovado montar a identificação a partir de `empresa`, `estabelecimento`, `participacao_societaria`, `pessoa_identificador`, `enquadramento_historico` e `erp.fato` (capital antes/depois). **Não** extrair o NIRE da filial por parsing do endereço: exibir o endereço como está (ele já contém o NIRE).

**8 (Doc 00):** ✅ Aprovado o filtro `documentos_json IS NOT NULL ORDER BY ordem` e a contagem por documento em Python, com `pend_doc` individual na capa.

**9 (memória de custo):** ✅ Calcular `horas × valor_hora_centavos` (coluna da tabela, fonte única) e a soma em Python. Se o `valor_hora` do JSON divergir da coluna, ignorar o do JSON (a coluna manda) — sem alerta adicional nesta etapa.

**10 (recálculo):** ✅ Incluir **todas** as rubricas de `folha_item` (inclusive `VT-SUBS` e provisões). A função deve ser **independente**: pode usar os mesmos parâmetros (`parametro_legal`, `contrato_trabalho`, `folha_competencia`), mas **não** chamar funções de cálculo do motor. Tabela do Doc 13: `Empregado | Rubrica | Base | Motor | Recálculo | Diferença`; o V1 aparece só no quadro de achados (AUD-01…10), como proposto.

**11 (`dossie_label`):** ✅ Aprovado. Critério: os testes de PDF do D1 (`test_web_dossie1_ux_pdf.py`) continuam verdes e a saída do D1 não muda.

**Acréscimos do revisor:**
- **A. Banco (atualizado após decisão da usuária):** não há banco local; o único banco é o Supabase de produção, **somente leitura** para o executor (ver Seção 0). As conclusões da Seção 9 tiradas do banco local foram conferidas em produção pelo revisor e valem.
- **B.** Ao fim de cada fase, rodar `pytest sistema/testes` (puros passando, de banco pulados) e conferir as prévias na Vercel do branch.
- **C.** Na Fase 5, anexar à Seção 11 a lista de arquivos alterados (`git diff --stat`) e a URL da prévia da Vercel. A contagem de alertas `D2_*` em produção será feita pelo revisor na Fase 6.

### Decisão: 🟢 LIBERADO para iniciar a Fase 1, com os ajustes dos itens 2, 5, 6, 7 e 10 acima.

## 11. Diário de execução (executor preenche por fase)

| Fase | Data | Commits | Testes | Observações |
|---|---|---|---|---|
| 1 | 26/11/2026 | `87f754f` | `pytest sistema/testes -q`: 29 passed, 23 skipped | Branch `feat/d2-documentos-vivos`, migração 008, remoção de constantes, `impacto_exclusao_simples`, `LIQUIDO_B` dinâmico e `detectar_residuos_texto_d2`. |
| 2 | 26/11/2026 | `af97d15` | `pytest sistema/testes -q`: 30 passed, 23 skipped | Quadros vivos dos Docs 00, 05, 06, 07, 09, 14 e 15; correção de `dossie_label` em `_m.html`; testes puros `test_d2_quadros_fase2`. |
| 3 | 26/11/2026 | `d831175` | `pytest sistema/testes -q`: 32 passed, 23 skipped | Docs 01–04, 08, 10 e conciliação Doc 12; regras `D2_PROPOSTA_CONTRATO_DIVERGENTE` e `D2_SALARIO_ABAIXO_PISO`; extração de `obter_dados_escritorio_d1`; telas D2 (sem afetar D1) e novos campos editáveis. |
| 4 | 26/11/2026 | `d7e1031` | `pytest sistema/testes -q`: 36 passed, 23 skipped | Doc 13 (PT-01..05, recálculo 100%, AUD-01..10), `recalcular_folha_independente_dados`/`recalcular_folha_independente`, separação `PROV-FER`/`PROV-1/3` no motor e na planilha `.xlsx`, regra `D2_RECALCULO_DIVERGENTE`. |
| 5 | 26/11/2026 | `87f754f`, `af97d15`, `d831175`, `d7e1031` (+ doc final) | `pytest sistema/testes -q`: 36 passed, 23 skipped; render local puro Docs 01/06/13 OK | Push de `feat/d2-documentos-vivos`; deploy Vercel concluído (`state: success`): https://prisma-jrna-plataforma-git-fe-06c7dc-ricksons-projects-31de7f0c.vercel.app . `git diff --stat master..HEAD`: 17 arquivos (`docs/PLANO_D2_DOCUMENTOS_VIVOS.md`, `sistema/erp/motor_folha.py`, `sistema/pg/migrations/008_d2_documentos_vivos.sql`, `sistema/testes/test_web_dossie2.py`, `sistema/web/{ajuda,emissor_dossie2,planilha_dossie2,repo,repo_d2,rotulos}.py`, `sistema/web/templates/{dp,folha,instrumentos,onboarding,sustentacao}.html`, `sistema/web/templates/pdf/{_m,d2_doc}.html`; +2679/-194). Conferência no navegador na prévia Vercel pendente por Chrome DevTools indisponível (`DevToolsActivePort` ausente) — requer abertura/login pela usuária. |
