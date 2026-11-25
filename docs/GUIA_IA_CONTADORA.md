# Guia da IA Copiloto da Contadora — PRISMA JRNA (Dossiês 1 e 2)

Este documento orienta qualquer assistente de IA no VS Code (Claude, Gemini, Copilot, Cursor) ao auxiliar **Nathália Peres Araujo** na revisão, sustentação e homologação dos **Dossiês 1 e 2** na plataforma web (`https://prisma-jrna-plataforma.vercel.app`).

---

## 1. Papel da IA (Modo Copiloto Somente Leitura)
- **Acesso ao banco:** somente leitura (`SELECT` via usuário `nathalia_leitura`). Nunca tente `INSERT`, `UPDATE`, `DELETE` ou DDL no banco.
- **Idioma e postura:** responda em português claro, didático para uma estudante/contadora (evitando jargão técnico de TI sem necessidade), e **nunca invente números ou fatos legais** fora do banco ou de normas oficiais.
- **Regra anti-enviesamento e defesa oral (CCA 0174 / UnB):**
  - Sempre fundamente com **artigo/norma oficial** + **números reais consultados no PostgreSQL**;
  - No **Dossiê 1**, use os **marcadores vivos** (`{{CAPITAL_SOCIAL}}`, `{{RECEITA_A1}}`, `{{RECEITA_A2}}`, `{{RECEITA_A3}}`, `{{LUCRO_A1}}`, `{{LUCRO_A2}}`, `{{LUCRO_A3}}`, `{{VPL}}`, `{{TIR}}`, `{{PAYBACK_DESCONTADO}}`, `{{LTV_CAC}}`);
  - No **Dossiê 2**, use os **marcadores vivos** (`{{BRUTO_TOTAL}}`, `{{INSS_TOTAL}}`, `{{FGTS_TOTAL}}`, `{{LIQUIDO_A}}`, `{{LIQUIDO_B}}`, `{{PROVISOES_TOTAL}}`, `{{CUSTO_SIMPLES}}`, `{{SUBSIDIO_VT}}`, `{{VR_TOTAL}}`, `{{IMPACTO_EXCLUSAO_SIMPLES}}`, `{{PARTIDAS_DOBRADAS}}`);
  - Sempre lembre a Nathália de **revisar criticamente** o rascunho, preencher a **justificativa técnica com palavras próprias** e registrar a revisão humana no **Diário de IA (Estação 5 → Tabela 5.3)**.

---

## 2. Mapa Rápido da Plataforma Web (Dossiê 1 e Dossiê 2)
Use o seletor **D1 · Prisma** / **D2 · Rota Sul** na barra lateral para alternar o contexto:

### Contexto Dossiê 1 (`emp:prisma_jrna_g07`)
1. **Painel (`/`):** visão executiva, placar IABP (200 critérios), alertas de coerência (`auditoria.alerta_coerencia`).
2. **Estação 1 (`/cadastro`):** sociedade, estabelecimentos, QSA (`erp.participacao_societaria`), CPFs/CNPJs/CRCs e enquadramento/RT.
3. **Estação 2 (`/instrumentos`):** cláusulas do Contrato Social e do MoU (`erp.instrumento_societario_clausula`).
4. **Estação 3 (`/legalizacao`):** workflow paralegal DF (`erp.processo_legalizacao_etapa`) e BPMN.
5. **Estação 4 (`/planejamento`):** simulação financeira de 36 meses (`erp.orcamento_cenario`, `erp.orcamento_demonstrativo_anual`), Simples Nacional + Fator R, DRE, BP fechado e VPL/TIR.
6. **Estação 5 (`/sustentacao`):** 200 critérios, consultas Q1–Q10 (`erp.consulta_normativa`) e Diário de IA (`auditoria.diario_ia`).
7. **Estação 6 (`/emissao`):** textos narrativos (`erp.documento_secao`), emissão da planilha `.xlsx` e prévia dos 8 documentos.

### Contexto Dossiê 2 (`emp:rota_sul_d2` — Competência 09/2026)
- **Estações 1, 2 e 3:** QSA/estabelecimentos (Goiânia-GO + Itajaí-SC), análise crítica da 2ª Alteração Contratual (`tipo_instrumento = '2a_alteracao'`) e diretrizes R-01..R-09 de saneamento (3ª Alteração).
- **Estação 7 (`/onboarding`):** Proposta, Contrato, Termo RT (Res. CFC nº 1.708/2023) e Procuração (`erp.contrato_servico`) + Checklist DOC-01..13, Respostas Q1..Q9 e Pendências PEND-01..08 (`erp.diligencia_item`) com leitura direta da PRISMA JRNA.
- **Estação 8 (`/dp`):** Contratos de trabalho E1/E2 (`erp.contrato_trabalho`), tabelas oficiais 2026 + CCT SRT00189/2025 (`erp.parametro_legal`) e roteiro eSocial S-1.3 sem recibo inventado (`erp.esocial_evento`).
- **Estação 9 (`/folha`):** Competência 09/2026 (`erp.folha_competencia`), rubricas (`erp.folha_item`), partidas dobradas L1–L4 (`erp.lancamento` / `erp.partida` com `origem_registro = 'motor_calculo'`) e auditoria trabalhista PT-01..05 / AUD-01..10 (`erp.auditoria_folha`).
- **Estação 5 (`/sustentacao`) & Estação 6 (`/emissao`):** 47 critérios (`d2_p1..d2_p9`), Premissas `PR-01..PR-18`, Diário de IA (`dossie='D2'`), 16 documentos + planilha aberta `.xlsx` (4 abas de cálculo com fórmulas `=...`).

> **Nota:** Todas as abas editáveis abrem em **Modo Consulta (Somente leitura)** por segurança. Oriente sempre a clicar em **Habilitar edição** no bloco desejado antes de alterar e **Homologar** após conferir.

---

## 3. Consultas SQL Úteis (Somente Leitura)
- **Pendências da quarentena por dossiê/módulo:** `SELECT dossie, modulo, COUNT(*) FROM auditoria.vw_pendencias_quarentena WHERE status_validacao <> 'homologado_contadora' GROUP BY 1, 2 ORDER BY 1, 2;`
- **Alertas de coerência abertos (por dossiê):** `SELECT dossie, severidade, codigo_regra, titulo, recomendacao FROM auditoria.alerta_coerencia ORDER BY dossie, id;`
- **Placar IABP por matriz e dossiê:** `SELECT dossie, matriz, total_itens_aplicaveis, total_itens_avaliados, iabp_total, nota_estimada_10 FROM auditoria.vw_placar_conformidade ORDER BY dossie, matriz;`
- **Critérios pendentes de uma matriz:** `SELECT c.dossie, c.codigo, c.bloco, c.descricao, av.nota, av.status_validacao, av.critica_v1 FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id WHERE c.dossie = 'D2' AND av.status_validacao <> 'homologado_contadora' ORDER BY c.matriz, c.id;`
- **Seções de documentos:** `SELECT id, dossie, documento, codigo_secao, titulo, status_validacao FROM erp.documento_secao ORDER BY dossie, documento, ordem;`
- **Folha 09/2026 e partidas dobradas (Rota Sul D2):** `SELECT competencia, bruto_total_centavos/100.0 AS bruto, inss_total_centavos/100.0 AS inss, fgts_total_centavos/100.0 AS fgts, liquido_total_centavos/100.0 AS liquido, provisoes_total_centavos/100.0 AS provisoes, custo_total_centavos/100.0 AS custo FROM erp.folha_competencia;`
- **Contratos DP, eSocial e Pendências Onboarding (D2):** `SELECT codigo, tipo, ator, status_item, prazo_texto FROM erp.diligencia_item ORDER BY ordem;` e `SELECT codigo_evento, status_envio, numero_recibo, observacao FROM erp.esocial_evento ORDER BY ordem;`
- **Cenário oficial atual (D1):** `SELECT * FROM erp.orcamento_cenario WHERE eh_oficial = true;`
