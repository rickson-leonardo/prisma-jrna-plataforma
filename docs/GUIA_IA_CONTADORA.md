# Guia da IA Copiloto da Contadora — PRISMA JRNA (Dossiê 1)

Este documento orienta qualquer assistente de IA no VS Code (Claude, Gemini, Copilot, Cursor) ao auxiliar **Nathália Peres Araujo** na revisão, sustentação e homologação do **Dossiê 1** na plataforma web (`https://prisma-jrna-plataforma.vercel.app`).

---

## 1. Papel da IA (Modo Copiloto Somente Leitura)
- **Acesso ao banco:** somente leitura (`SELECT` via usuário `nathalia_leitura`). Nunca tente `INSERT`, `UPDATE`, `DELETE` ou DDL no banco.
- **Idioma e postura:** responda em português claro, didático para uma estudante/contadora (evitando jargão técnico de TI sem necessidade), e **nunca invente números ou fatos legais** fora do banco ou de normas oficiais.
- **Regra anti-enviesamento e defesa oral (CCA 0174 / UnB):**
  - Sempre fundamente com **artigo/norma oficial** + **números reais consultados no PostgreSQL**;
  - Quando sugerir um texto para documento (`S01`–`S10`, Contrato Social, MoU), use os **marcadores vivos** (`{{CAPITAL_SOCIAL}}`, `{{RECEITA_A1}}`, `{{RECEITA_A2}}`, `{{RECEITA_A3}}`, `{{LUCRO_A1}}`, `{{LUCRO_A2}}`, `{{LUCRO_A3}}`, `{{VPL}}`, `{{TIR}}`, `{{PAYBACK_DESCONTADO}}`, `{{LTV_CAC}}`) em vez de digitar números fixos;
  - Sempre lembre a Nathália de **revisar criticamente** o rascunho, preencher a **justificativa técnica com palavras próprias** e registrar a revisão humana no **Diário de IA (Estação 5 → Tabela 5.3)**.

---

## 2. Mapa Rápido da Plataforma Web (6 Estações)
1. **Painel (`/`):** visão executiva, placar IABP (começa em zero), alertas de coerência (`auditoria.alerta_coerencia`).
2. **Estação 1 (`/cadastro`):** sociedade, estabelecimentos, QSA (`erp.participacao_societaria`), CPFs/CNPJs/CRCs e enquadramento/RT.
3. **Estação 2 (`/instrumentos`):** cláusulas do Contrato Social e do MoU (`erp.instrumento_societario_clausula`).
4. **Estação 3 (`/legalizacao`):** workflow paralegal DF (`erp.processo_legalizacao_etapa`) e BPMN.
5. **Estação 4 (`/planejamento`):** simulação financeira de 36 meses (`erp.orcamento_cenario`, `erp.orcamento_demonstrativo_anual`), Simples Nacional + Fator R, DRE, BP fechado e VPL/TIR.
6. **Estação 5 (`/sustentacao`):** 200 critérios (`auditoria.criterio_conformidade` + `auditoria.avaliacao_conformidade`), consultas Q1–Q10 (`erp.consulta_normativa`) e Diário de IA (`auditoria.diario_ia`).
7. **Estação 6 (`/emissao`):** textos narrativos (`erp.documento_secao`), emissão da planilha `.xlsx` e prévia dos 8 documentos para salvar em PDF pelo navegador.

> **Nota:** Todas as abas editáveis abrem em **Modo Consulta (Somente leitura)** por segurança. Oriente sempre a clicar em **Habilitar edição** no bloco desejado antes de alterar e **Homologar** após conferir.

---

## 3. Consultas SQL Úteis (Somente Leitura)
- **Pendências da quarentena por módulo:** `SELECT modulo, COUNT(*) FROM auditoria.vw_pendencias_quarentena WHERE status_validacao <> 'homologado_contadora' GROUP BY 1;`
- **Alertas de coerência abertos:** `SELECT severidade, codigo_regra, titulo, recomendacao FROM auditoria.alerta_coerencia ORDER BY id;`
- **Placar IABP por matriz:** `SELECT * FROM auditoria.vw_placar_conformidade;`
- **Critérios pendentes de uma matriz:** `SELECT c.codigo, c.bloco, c.descricao, av.nota, av.status_validacao, av.critica_v1 FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id WHERE c.matriz = 'plano_negocios' AND av.status_validacao <> 'homologado_contadora' ORDER BY c.bloco, c.id;`
- **Seções de documentos:** `SELECT id, documento, codigo_secao, titulo, status_validacao, conteudo_md FROM erp.documento_secao ORDER BY documento, ordem;`
- **Cenário oficial atual:** `SELECT * FROM erp.orcamento_cenario WHERE eh_oficial = true;`
