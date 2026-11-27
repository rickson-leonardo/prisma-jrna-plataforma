-- Dossiê 2, etapa 4 (Estação 9 — Folha): Docs 11 a 13, folha 09/2026, lançamentos L1–L4 e auditoria trabalhista.
-- Achados FO-01 a FO-12 (REVISAO_D2_ROTA_SUL.md). Decisões: FO-03 (achados do cliente, não da V1) e FO-08 (L3 em passivo).
-- PRÉ-REQUISITO: deploy do commit da etapa 4 e "Recalcular" na tela da folha (o recálculo regrava rubricas e lançamentos).
-- Fontes: EC02, aula de DP (AULA), devolutiva G07 (régua), respostas do professor no grupo (G-08, G-09) e normas citadas.
-- Valores: só marcadores vivos ({{...}}) e campos calculados aqui a partir de erp.folha_item (motor). Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int; v_d bigint; v_c bigint; v_excl bigint; v_com bigint;
  c_docs constant text[] := ARRAY['d2_11_folha', 'd2_12_resumo_contab', 'd2_13_auditoria'];
BEGIN
  -- 0. Estado esperado (inclui o recálculo pós-deploy)
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = ANY(c_docs) AND status_validacao = 'pendente_revisao';
  IF n <> 17 THEN RAISE EXCEPTION 'Seções dos Docs 11–13 fora do estado esperado (% de 17)', n; END IF;
  SELECT count(*) INTO n FROM erp.auditoria_folha WHERE empresa_id = 1 AND status_validacao <> 'homologado_contadora';
  IF n <> 15 THEN RAISE EXCEPTION 'Auditoria fora do estado esperado (% de 15)', n; END IF;
  SELECT count(*) INTO n FROM erp.folha_item fi JOIN erp.folha_competencia fc ON fc.id = fi.competencia_id
   WHERE fc.empresa_id = 1 AND fi.origem_registro = 'motor_calculo' AND fi.nome_rubrica = 'Vale-Refeição (CLT art. 457, § 2º)';
  IF n <> 1 THEN RAISE EXCEPTION 'Recálculo pós-deploy não encontrado (rubrica de VR com o nome novo: %). Rodar "Recalcular" na tela da folha.', n; END IF;
  SELECT sum(p.valor_centavos) FILTER (WHERE p.dc = 'D'), sum(p.valor_centavos) FILTER (WHERE p.dc = 'C') INTO v_d, v_c
    FROM erp.lancamento l JOIN erp.partida p ON p.lancamento_id = l.id WHERE l.empresa_id = 1 AND l.origem_registro = 'motor_calculo';
  IF v_d IS NULL OR v_d <> v_c THEN RAISE EXCEPTION 'Partidas do motor não fecham (D % × C %)', v_d, v_c; END IF;
  SELECT count(*) INTO n FROM erp.lancamento l JOIN erp.partida p ON p.lancamento_id = l.id JOIN erp.conta_contabil cc ON cc.id = p.conta_id
   WHERE l.empresa_id = 1 AND l.origem_registro = 'motor_calculo' AND l.tag_ref = 'folha_l3' AND p.dc = 'C' AND cc.codigo = '2.1.2.06';
  IF n <> 1 THEN RAISE EXCEPTION 'L3 sem crédito em 2.1.2.06 VT/VR a Pagar (FO-08): %', n; END IF;

  -- valores do motor usados nos achados (calculados aqui a partir de erp.folha_item, não digitados)
  SELECT round(sum(fi.valor_centavos) FILTER (WHERE fi.tipo_rubrica = 'provento' OR fi.codigo_rubrica IN ('PROV-13', 'PROV-FER', 'PROV-1/3')) * 0.278),
         sum(fi.valor_centavos) FILTER (WHERE fi.codigo_rubrica IN ('COMISSAO', 'DSR-COM'))
    INTO v_excl, v_com
    FROM erp.folha_item fi JOIN erp.folha_competencia fc ON fc.id = fi.competencia_id WHERE fc.empresa_id = 1;

  -- 1. Parâmetros (FO-07): referência da CCT com fonte; apontamentos antigos do rascunho
  UPDATE erp.parametro_legal SET norma_citada = v.norma, atualizado_em = now()
  FROM (VALUES
    ('CCT-PISO-GERAL', 'CCT SECEG × SINDILOJAS-GO — Termo Aditivo 2026/2027, cl. 3ª (aula de DP, p. 29)'),
    ('CCT-PISO-VEND', 'CCT SECEG × SINDILOJAS-GO — Termo Aditivo 2026/2027, cl. 3ª e 6ª (aula de DP, p. 29)')
  ) AS v(cod, norma)
  WHERE erp.parametro_legal.empresa_id = 1 AND erp.parametro_legal.codigo = v.cod AND strpos(erp.parametro_legal.norma_citada, 'SRT00189') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Parâmetros CCT: % (esperado 2)', n; END IF;
  UPDATE erp.parametro_legal SET apontamento_auditoria = NULL, atualizado_em = now()
   WHERE empresa_id = 1 AND strpos(apontamento_auditoria, 'SRT00189') > 0 AND status_validacao = 'homologado_contadora';

  -- 2. Auditoria (FO-03, FO-05, FO-06): papéis de trabalho e achados do cliente na competência 09/2026
  UPDATE erp.auditoria_folha a SET titulo = v.tit, norma_referencia = v.norma, objetivo_ou_evidencia = v.obj,
         procedimento_ou_risco = v.proc, conclusao_ou_correcao = v.concl, responsavel = v.resp, prazo_texto = v.prazo,
         situacao_achado = v.sit, valor_v1_centavos = NULL, valor_recalculado_centavos = v.valor, atualizado_em = now()
  FROM (VALUES
    ('PT-01', 'Planejamento, avaliação de risco e materialidade', 'NBC TA 315 e NBC TA 330',
       'Admissões e folha de 09/2026 da Rota Sul (E1 e E2 — 100% da população); EC02, aulas 14 e 15.',
       'Risco inerente e de controle altos (primeira folha, remuneração variável, ASO e SST ausentes, retirada informal dos sócios); testes substantivos em 100% das rubricas.',
       'Plano executado: cadastral/documental (PT-02), recálculo (PT-03), encargos e eSocial (PT-04) e achados (PT-05).',
       'Auditoria PRISMA JRNA', '05/10 e 07/10/2026', 'conforme', NULL::bigint),
    ('PT-02', 'Auditoria cadastral e documental (prontuário, eventos, CCT)', 'CLT arts. 29, 41 e 168; NR-7; CCT (Termo Aditivo 2026/2027); MOS eSocial S-1.3',
       'Prontuários (doc. 06), fichas (docs. 07 e 09), contratos (docs. 08 e 10), registro de eventos e diligência (doc. 05).',
       'Completude do prontuário, tempestividade do S-2200, ASO, termos de VT/VR, documentos civis, jornada e aderência à CCT.',
       'Contratos, CBO e piso conformes; abertos: ASO (AUD-01), eventos e termos (AUD-02), documentos civis (AUD-03), jornada do E1 (AUD-05) e SST/ponto/pró-labore (AUD-07).',
       'Diretoria Rota Sul + DP PRISMA JRNA', '05/10/2026', 'aberto_cliente', NULL),
    ('PT-03', 'Recálculo independente da folha (100% dos empregados)', 'Portaria MPS/MF nº 13/2026; Lei nº 15.270/2025; CCT; Lei nº 8.036/1990',
       'Rubricas do motor (erp.folha_item) × recálculo independente com os mesmos contratos e parâmetros, sem reutilizar o motor.',
       'Recálculo rubrica a rubrica de E1 e E2 (tabela 2 do doc. 13) e conferência com a planilha do doc. 11.',
       'Diferença zero em todas as rubricas; a comissão depende da premissa de vendas (AUD-04).',
       'DP PRISMA JRNA', '07/10/2026', 'conforme', NULL),
    ('PT-04', 'Conferência de encargos, eSocial, DCTFWeb e FGTS Digital', 'LC 123/2006, art. 13, VI; Lei nº 8.036/1990; MOS eSocial S-1.3',
       'Folha (doc. 11) × lançamentos L1–L4 e conciliação (doc. 12) × eventos S-1200/S-1299 (doc. 06).',
       'Cruzamento INSS retido × DCTFWeb, FGTS × FGTS Digital, CPP no DAS (Simples), eventos periódicos e de SST.',
       'Valores conciliados com diferença zero; S-1200/S-1299 aguardam e-CNPJ; S-2220 e S-2240 dependem de ASO e inventário de riscos.',
       'DP PRISMA JRNA', '15/10/2026', 'aberto_cliente', NULL),
    ('PT-05', 'Quadro de achados e correções propostas', 'NBC TA 330; NBC TA 265 (comunicação de deficiências)',
       'Achados do cliente na competência 09/2026 (AUD-01 a AUD-08), com evidência, risco e valor.',
       'Classificação de risco, valor envolvido, correção, responsável e prazo.',
       'Oito achados comunicados à administração; acompanhamento pelas pendências do doc. 05.',
       'PRISMA JRNA + Diretoria Rota Sul', '07/10/2026', 'aberto_cliente', NULL),
    ('AUD-01', 'ASO admissional não realizado antes do início das atividades (E1 e E2)', 'CLT art. 168; NR-7; eSocial S-2220',
       'Resposta do cliente (Q7 — devolutiva oficial, p. 3); PEND-01; doc. 06 (prontuário).',
       'Crítico: empregados em atividade sem atestado de aptidão; multa administrativa conforme gradação da NR-28; S-2220 sem lastro.',
       'Realizar os exames admissionais em clínica de medicina do trabalho e transmitir o S-2220 com o ASO.',
       'Diretoria Rota Sul + clínica SST', 'Imediato (PEND-01 venceu em 02/10/2026)', 'aberto_cliente', NULL),
    ('AUD-02', 'Admissões sem comprovação de envio do S-2200 e termos de VT/VR não assinados', 'MOS eSocial S-1.3 (S-2200 até o dia anterior ao início); Lei nº 7.418/1985',
       'Tabela de eventos (doc. 06): sem recibo do S-2200 (prazos 15/09 e 20/09/2026); DOC-12 pendente; aula de DP, p. 23.',
       'Alto: risco de intempestividade do registro e fragilidade probatória do desconto de VT.',
       'Transmitir ou comprovar o S-2200 e arquivar os recibos; colher os termos de opção de VT e de VR assinados (sem fornecer modelo de oposição sindical).',
       'Diretoria Rota Sul + DP PRISMA JRNA', '09/10/2026', 'aberto_cliente', NULL),
    ('AUD-03', 'Documentos civis dos empregados e do dependente não apresentados', 'CLT art. 41; Lei nº 9.250/1995, art. 4º, III (dependente no IRRF)',
       'DOC-09 em saneamento; EC02, p. 3 ("documentos de admissão" a apurar).',
       'Médio: prontuário incompleto e dependente de IRRF sem comprovação.',
       'Coletar e conferir RG, CPF, comprovante de residência e a certidão e o CPF do filho de E1.',
       'Empregados E1 e E2 + DP PRISMA JRNA', '09/10/2026', 'aberto_cliente', NULL),
    ('AUD-04', 'Comissão do E2 calculada sobre premissa didática, sem relatório comercial de vendas', 'Lei nº 3.207/1957; CLT art. 466; Súmula 27 do TST',
       'Vendas líquidas de R$ 60.000,00 como premissa didática (aula de DP, p. 25); DOC-13 e PEND-05 em saneamento.',
       'Médio: a base da comissão e do DSR não tem documento de suporte; valor envolvido = comissão + DSR do motor.',
       'Obter o relatório de vendas líquidas de 21 a 30/09/2026 assinado pela diretoria comercial e recalcular se divergir.',
       'Diretoria comercial Rota Sul', '09/10/2026', 'aberto_cliente', v_com),
    ('AUD-05', 'Jornada do E1: horário informado soma 41h semanais × 44h contratuais', 'CLT arts. 58, 59 e 71',
       'EC02, p. 2 (08h–18h, intervalo de 1h48, segunda a sexta); PEND-04; PR-11.',
       'Médio: 3h semanais sem definição (compensação ou redução da jornada contratual).',
       'Definir com os sócios a distribuição das 44h ou ajustar a jornada contratual, com acordo escrito e controle de ponto.',
       'Diretoria Rota Sul + DP PRISMA JRNA', '09/10/2026', 'aberto_cliente', NULL),
    ('AUD-06', 'Risco de exclusão do Simples Nacional com efeito nos encargos da folha', 'LC 123/2006, art. 17, VIII, e arts. 29 e 30',
       'Doc. 01 (R-01: CNAE 4541-2/01 com importação); PEND-02; sensibilidade no doc. 12.',
       'Crítico: fora do Simples, a folha passaria a ter CPP, RAT e terceiros (27,8%); valor envolvido = encargo adicional mensal estimado pelo motor.',
       'Excluir os CNAEs vedados na 3ª Alteração Contratual (PEND-02) antes de qualquer comunicação de exclusão.',
       'Sócios + advogado societário (apoio PRISMA JRNA)', '20/10/2026 (PEND-02)', 'aberto_cliente', v_excl),
    ('AUD-07', 'SST além do ASO, controle de ponto e retirada dos sócios sem pró-labore formal', 'NR-1 (item 1.8.4); NR-7; CLT art. 74; Lei nº 8.212/1991, art. 12, V, "f"',
       'Resposta Q4 (carta, p. 3: ponto em papel/celular); PEND-07 e PEND-08; resposta do professor no grupo: retirada de "80% do lucro líquido do mês", verbal, sem pró-labore (G-09).',
       'Alto: S-2240 sem inventário de riscos, prova de jornada frágil e retirada informal dos sócios administradores (contribuição previdenciária e lastro contábil da distribuição).',
       'Contratar o inventário de riscos (PGR ou DIR) e o PCMSO; implantar ponto; formalizar pró-labore (S-2300) e distribuição de lucros com base em escrituração.',
       'Diretoria Rota Sul + PRISMA JRNA', '15/10/2026', 'aberto_cliente', NULL),
    ('AUD-08', 'Causa trabalhista em curso sem avaliação do advogado', 'NBC TG 25 (provisões e passivos contingentes)',
       'Resposta do professor no grupo: causa trabalhista de R$ 120.987,00, "detalhes com o advogado" (G-08).',
       'Alto: sem a avaliação do advogado (provável, possível ou remota) não há base para provisionar ou divulgar.',
       'Solicitar ao advogado a carta de avaliação do processo e registrar provisão ou nota explicativa conforme a probabilidade.',
       'Sócios + advogado', '20/10/2026', 'aberto_cliente', 12098700::bigint)
  ) AS v(cod, tit, norma, obj, proc, concl, resp, prazo, sit, valor)
  WHERE a.empresa_id = 1 AND a.codigo = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 13 THEN RAISE EXCEPTION 'Auditoria: % (esperado 13)', n; END IF;
  DELETE FROM erp.auditoria_folha WHERE empresa_id = 1 AND codigo IN ('AUD-09', 'AUD-10') AND tipo_registro = 'achado';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Achados removidos: % (esperado 2)', n; END IF;

  -- 3. Competência (FO-11)
  UPDATE erp.folha_competencia SET apontamento_auditoria = 'Rubricas e lotes L1–L4 gerados pelo motor (2 conduções/dia); recálculo independente e conciliação com diferença zero (doc. 13, PT-03 e PT-04).', atualizado_em = now()
   WHERE empresa_id = 1 AND competencia = '2026-09';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Competência: %', n; END IF;

  -- 4. Seções (FO-01, FO-02, FO-04, FO-05, FO-07, FO-10): regra + marcadores; tabelas saem do banco
  UPDATE erp.documento_secao s SET conteudo_md = v.txt, atualizado_em = now()
  FROM (VALUES
    ('d2_11_folha', 'cabecalho', $t$# FOLHA DE PAGAMENTO E MEMÓRIA DE CÁLCULO — COMPETÊNCIA SETEMBRO/2026

**Dossiê 2 — Onboarding e Departamento Pessoal (Competência 09/2026)**
**Empregadora:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. (CNPJ `11.222.333/0001-81` | NIRE `52900000015` — Matriz Goiânia-GO)
**CNAEs-foco (Anexo I):** `4530-7/02`, `4530-7/05`, `4541-2/02`, `4541-2/06` | **Regime:** Simples Nacional (classificação tributária `01` no eSocial — CPP no DAS)
**Fontes oficiais:** Portaria Interministerial MPS/MF nº 13/2026 (INSS e salário-família); Lei nº 15.270/2025 (IRRF 2026); CCT SECEG × SINDILOJAS-GO, Termo Aditivo 2026/2027, cl. 3ª, 6ª e 11ª (aula de DP, p. 29); premissas no doc. 14.
**Planilha com fórmulas:** gerada pela plataforma a partir do mesmo banco (abas Leia-me, Parametros, Folha_Set2026, Memoria_Calculo e Provisoes_e_Integracao).$t$),
    ('d2_11_folha', '1_folha_de_pagamento_consolidada', $t$A tabela **Espelho dinâmico do motor** traz todas as rubricas de E1 e E2 calculadas pelo motor da folha, com referência, fórmula, base e valor. Totais da competência (cenário A — sem oposição documentada à contribuição negocial):
- Remuneração bruta: **{{BRUTO_TOTAL}}**; INSS retido: **{{INSS_TOTAL}}**; IRRF: zero (desconto simplificado e redução da Lei nº 15.270/2025);
- Líquido a pagar: **{{LIQUIDO_A}}** (cenário B, com oposição documentada: **{{LIQUIDO_B}}**);
- FGTS a recolher (8%, FGTS Digital, vencimento 20/10/2026): **{{FGTS_TOTAL}}**;
- Benefícios custeados pela empresa: subsídio de vale-transporte **{{SUBSIDIO_VT}}** (2 conduções/dia — `PR-08`) e vale-refeição **{{VR_TOTAL}}**.

### 1.1 Cenário B — oposição à contribuição negocial (`PR-10`)
A empregadora não induz nem fornece modelo de oposição (Termo Aditivo 2026/2027, cl. 11ª; aula de DP, p. 29). Se o empregado apresentar oposição protocolada no sindicato, a contribuição deixa de ser descontada e o líquido passa ao valor do cenário B.$t$),
    ('d2_11_folha', '2_memoria_de_calculo_detalhada_p', $t$As fórmulas e os valores de cada rubrica estão na tabela do motor (coluna **Fórmula**) e na planilha. Regras aplicadas:
1. **Salário proporcional** — contagem civil sobre 30 dias: E1 15/30 (16 a 30/09) e E2 10/30 (21 a 30/09) (aula de DP, p. 26).
2. **Piso e garantia da CCT** — confronto no doc. 06, seção 3; a remuneração do E2 em setembro (fixo + comissão + DSR) supera a garantia proporcional do vendedor (cl. 3ª e 6ª).
3. **Comissão e DSR (E2)** — 1,5% sobre vendas líquidas de R$ 60.000,00 (premissa didática, aula de DP, p. 25; `PR-07`); DSR = comissão ÷ 9 dias trabalháveis × 1 repouso (27/09), em rubrica destacada (Lei nº 605/1949; Súmula 27 do TST).
4. **Salário-família** — cota de R$ 67,54 só para remuneração até R$ 1.980,38 (Portaria MPS/MF nº 13/2026; aula de DP, p. 24). O E1 tem salário contratual de R$ 2.400,00; o critério de remuneração mensal está na `PR-06` (doc. 14) → não devido. O E2 não tem dependentes.
5. **INSS** — tabela progressiva por faixas (Portaria MPS/MF nº 13/2026).
6. **IRRF** — maior entre a dedução legal (INSS + dependentes) e o desconto simplificado de R$ 607,20; a redução da Lei nº 15.270/2025 zera o imposto até R$ 5.000,00.
7. **Vale-transporte** — 2 conduções/dia × dias úteis × tarifa (`PR-08`); desconto limitado a 6% do salário básico proporcional, sem comissões; no E2, base limitada pela cl. 6ª.
8. **Vale-refeição (E1)** — R$ 30,00 por dia trabalhado (EC02, p. 3); fornecido sem pagamento em dinheiro, não integra a remuneração (CLT, art. 457, § 2º; `PR-09`).
9. **Contribuição negocial** — 3,33% da remuneração, teto de R$ 148,00 (cl. 11ª); o cenário A desconta, o cenário B não.
10. **FGTS** — 8% da remuneração (Lei nº 8.036/1990), sem desconto do empregado.$t$),
    ('d2_12_resumo_contab', 'cabecalho', $t$# RESUMO DA FOLHA, ENCARGOS, PROVISÕES, INTEGRAÇÃO CONTÁBIL E RECIBOS — SETEMBRO/2026

**Dossiê 2 — Onboarding e Departamento Pessoal (Competência 09/2026)**
**Empregadora:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. (Matriz Goiânia-GO — CNPJ `11.222.333/0001-81`, NIRE `52900000015`)
**Regime tributário:** Simples Nacional — Anexo I (classificação tributária `01` no eSocial)
**Base:** rubricas e lançamentos gerados pelo motor da folha (doc. 11), com conciliação automática.$t$),
    ('d2_12_resumo_contab', '1_resumo_consolidado_da_folha_e_', $t$| Indicador (09/2026) | Valor |
|---|---:|
| Remuneração bruta | {{BRUTO_TOTAL}} |
| INSS retido (DCTFWeb, vencimento 20/10/2026) | {{INSS_TOTAL}} |
| Líquido a pagar — cenário A (até o 5º dia útil de outubro, CLT art. 459, § 1º) | {{LIQUIDO_A}} |
| Líquido a pagar — cenário B (com oposição documentada) | {{LIQUIDO_B}} |
| FGTS 8% (FGTS Digital, vencimento 20/10/2026) | {{FGTS_TOTAL}} |
| Subsídio de vale-transporte (empresa) | {{SUBSIDIO_VT}} |
| Vale-refeição (empresa) | {{VR_TOTAL}} |
| Provisões trabalhistas + FGTS | {{PROVISOES_TOTAL}} |
| **Custo total de pessoal do mês** | **{{CUSTO_SIMPLES}}** |

> **Encargos no Simples Nacional (`PR-01`):** no Anexo I a CPP é recolhida no DAS sobre a receita bruta (LC 123/2006, art. 13, VI). Na folha não incidem CPP de 20%, RAT nem terceiros; recolhem-se o INSS retido dos empregados (DCTFWeb) e o FGTS de 8% (FGTS Digital).$t$),
    ('d2_12_resumo_contab', '2_provisoes_trabalhistas_regime_', $t$Só adquire 1/12 avo de 13º e de férias quem trabalha 15 dias ou mais no mês (Lei nº 4.090/1962, art. 1º, § 2º; CLT, art. 146, parágrafo único):
- **Empregado 1** (15 dias: 16 a 30/09) adquire 1/12 avo sobre o salário de R$ 2.400,00 — 13º, férias e 1/3 constitucional, mais FGTS de 8% sobre as provisões;
- **Empregado 2** (10 dias: 21 a 30/09) não adquire avo em setembro.

Total de provisões + FGTS: **{{PROVISOES_TOTAL}}** (rubricas `PROV-*` do doc. 11 e lote L4), sem CPP (Simples Nacional).

> **Nota prospectiva (E2 a partir de 10/2026):** a base de 13º e férias do vendedor com salário misto soma o fixo e a média das comissões e do DSR (CLT, art. 142, § 3º; Decreto nº 10.854/2021).$t$),
    ('d2_12_resumo_contab', '3_lancamentos_contabeis_de_integ', $t$Os lançamentos de integração estão na tabela **Partidas dobradas verificadas pelo banco**, gerada pelo motor com débitos iguais aos créditos (**{{PARTIDAS_DOBRADAS}}**), em 30/09/2026. Classificação funcional: despesas administrativas (`4.1.1.*`, E1) e comerciais (`4.2.1.*`, E2) (NBC TG 26); o plano de contas reduzido definitivo fica para o Dossiê 4.
- **L1** apropria salários, comissão e DSR contra salários a pagar, INSS retido, contribuição negocial e a recuperação do desconto de VT;
- **L2** registra o FGTS de 8%;
- **L3** apropria o VT e o VR do mês contra **VT/VR a pagar às operadoras** (passivo), quitado na compra em outubro;
- **L4** constitui as provisões de 13º, férias + 1/3 e FGTS.

> **Eventos de outubro/2026:** pagamento dos salários (D Salários a pagar / C Bancos — {{LIQUIDO_A}}, ou {{LIQUIDO_B}} no cenário B) até o 5º dia útil; recolhimento do INSS retido ({{INSS_TOTAL}}) e do FGTS ({{FGTS_TOTAL}}) até 20/10/2026; pagamento às operadoras de VT/VR; repasse da contribuição negocial ao sindicato no prazo da CCT.$t$),
    ('d2_12_resumo_contab', '4_conciliacao_planilha_do_doc_11', $t$A tabela **Conciliação folha × resumo × lançamentos contábeis** compara, rubrica por rubrica, os valores da folha (motor) com as partidas L1–L4; a diferença esperada é zero. A planilha do doc. 11 refaz a mesma conciliação por fórmulas.$t$),
    ('d2_12_resumo_contab', '5_analise_de_sensibilidade_tribu', $t$**Sensibilidade — não é valor da folha (régua C-32).** Se a Rota Sul for excluída do Simples Nacional (risco do CNAE 4541-2/01 com importação — LC 123/2006, art. 17, VIII; doc. 01, R-01; `PEND-02`), a folha passaria a ter CPP de 20%, RAT de 2% e terceiros de 5,8% (27,8%) sobre remuneração e provisões (`PR-17`). Encargo adicional estimado pelo motor para 09/2026: **{{IMPACTO_EXCLUSAO_SIMPLES}}**, sobre o custo atual de **{{CUSTO_SIMPLES}}**.$t$),
    ('d2_12_resumo_contab', '6_recibos_de_pagamento_competenc', $t$Os recibos de E1 e E2 estão na seção **Recibos de pagamento**, gerada das rubricas do motor (proventos, descontos, líquido, FGTS e vale-refeição), com campo de assinatura do empregado.$t$),
    ('d2_13_auditoria', 'cabecalho', $t$# RELATÓRIO DE AUDITORIA TRABALHISTA E PAPÉIS DE TRABALHO — COMPETÊNCIA 09/2026

**Dossiê 2 — Onboarding e Departamento Pessoal (Competência 09/2026)**
**Entidade auditada:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. (Matriz Goiânia-GO — CNPJ `11.222.333/0001-81`, NIRE `52900000015`)
**Equipe de auditoria:** PRISMA JRNA Auditoria e Contabilidade Ltda. (Líder: Jeovanna Ripardo Lustosa | Revisão técnica: Nathalia Peres Araujo — CRC-DF `025.431/O-7`)
**Referência:** NBC TA 315 e NBC TA 330 aplicadas ao escopo trabalhista | **Data:** 07/10/2026$t$),
    ('d2_13_auditoria', 'pt_01_planejamento_avaliacao_de_', $t$- **Objetivo:** avaliar a conformidade cadastral, documental, trabalhista, previdenciária, sindical e contábil das admissões e da folha de setembro/2026 (EC02, aulas 14 e 15).
- **Escopo:** 100% dos empregados (E1, Auxiliar Administrativo, admitido em 16/09/2026; E2, Vendedor interno, admitido em 21/09/2026) e docs. 05 a 12.
- **Materialidade:** folha inaugural de dois empregados — tolerância de R$ 0,01 para erros de cálculo, encargos, provisões e conciliação, mais avaliação qualitativa das exposições legais (NR-7, NR-1, eSocial, CCT e Simples Nacional).

| Dimensão | Nível | Justificativa | Resposta (NBC TA 330) |
|---|---|---|---|
| Risco inerente | Alto | Primeira folha da empresa, remuneração variável (comissão + DSR), jornada do E1 incoerente no caso (41h × 44h), obrigações do contador anterior em atraso (Q8) e risco de exclusão do Simples (doc. 01) | Testes substantivos em 100% das rubricas |
| Risco de controle | Alto | ASO não realizado (Q7), ponto em papel/celular (Q4), vendas sem relatório comercial, SST sem inventário de riscos, retirada dos sócios informal (G-09) | Não confiar em controles; exigir evidência primária e não atestar como conforme o que não existe |
| Risco de detecção | Baixo | Consequência dos riscos acima | Recálculo independente integral e cruzamento folha × contabilidade × eSocial × FGTS Digital |$t$),
    ('d2_13_auditoria', 'pt_02_auditoria_cadastral_contra', $t$| Item testado | Critério | Evidência | Resultado | Achado |
|---|---|---|---|---|
| Contratos de experiência | CLT arts. 443 e 445 (até 90 dias); EC02, p. 2 | Docs. 08 e 10 (45 + 45 e 30 + 60 dias) | Conforme | — |
| CBO, piso e garantia da CCT | Termo Aditivo 2026/2027, cl. 3ª e 6ª (aula de DP, p. 29) | Doc. 06, seção 3 | Conforme | — |
| ASO admissional | CLT art. 168; NR-7 | Q7; PEND-01 | Não conforme — crítico | AUD-01 |
| Registro no eSocial (S-2200) e termos de VT/VR | MOS eSocial S-1.3; Lei nº 7.418/1985 | Tabela de eventos (doc. 06); DOC-12 | Sem comprovação | AUD-02 |
| Documentos civis e do dependente | CLT art. 41 | DOC-09 | Pendente | AUD-03 |
| Base da comissão (vendas líquidas) | Lei nº 3.207/1957 | Aula de DP, p. 25; DOC-13 | Sem documento de suporte | AUD-04 |
| Jornada do E1 | CLT arts. 58 e 71 | EC02, p. 2; PEND-04 | Incoerente (41h × 44h) | AUD-05 |
| SST, ponto e pró-labore | NR-1 item 1.8.4; CLT art. 74 | Q4; PEND-07; PEND-08; G-09 | Não conforme | AUD-07 |
| Contingência trabalhista | NBC TG 25 | G-08 | Sem avaliação do advogado | AUD-08 |$t$),
    ('d2_13_auditoria', 'pt_03_recalculo_independente_da_', $t$A **Tabela 2** traz o recálculo independente de 100% das rubricas de E1 e E2: os mesmos contratos e parâmetros oficiais são recalculados sem reutilizar o motor e comparados, rubrica a rubrica, com a folha do motor (doc. 11) e a planilha. Diferença esperada: zero. Totais conferidos: bruto **{{BRUTO_TOTAL}}**, INSS **{{INSS_TOTAL}}**, FGTS **{{FGTS_TOTAL}}**, líquido **{{LIQUIDO_A}}** (cenário A) e provisões **{{PROVISOES_TOTAL}}**.$t$),
    ('d2_13_auditoria', 'pt_04_conferencia_de_encargos_es', $t$| Obrigação | Regra | Valor (motor) | Cruzamento | Canal / vencimento |
|---|---|---:|---|---|
| INSS retido | Tabela progressiva (Portaria MPS/MF nº 13/2026) | {{INSS_TOTAL}} | Folha × L1 × S-1200/S-1299 | DCTFWeb — 20/10/2026 |
| CPP, RAT e terceiros | Simples Nacional, Anexo I (LC 123/2006, art. 13, VI) | R$ 0,00 na folha | Classificação tributária 01 (S-1000) | DAS (PGDAS-D) |
| FGTS mensal | 8% (Lei nº 8.036/1990) | {{FGTS_TOTAL}} | Folha × L2 × S-1200 | FGTS Digital — 20/10/2026 |
| IRRF | Simplificado + redução (Lei nº 15.270/2025) | R$ 0,00 | Folha × S-1200 | Sem guia |
| Provisões + FGTS | NBC TG 33 (competência) | {{PROVISOES_TOTAL}} | Folha × L4 | Passivo (2.1.2.10 a 2.1.2.12) |
| Eventos de SST (S-2220, S-2240) | MOS eSocial S-1.3; NR-7; NR-1 | — | Doc. 06 (tabela de eventos) | Dependem do ASO e do inventário de riscos |$t$),
    ('d2_13_auditoria', 'pt_05_quadro_consolidado_de_acha', $t$A **Tabela 3** consolida os achados do cliente na competência 09/2026 (AUD-01 a AUD-08), com evidência, risco, valor envolvido, correção proposta, responsável e prazo. Os valores envolvidos vêm do motor da folha (AUD-04 e AUD-06) ou das respostas do cliente (AUD-08); os demais não são quantificáveis sem a providência indicada.$t$),
    ('d2_13_auditoria', 'conclusao_da_auditoria', $t$A folha de setembro/2026 foi **recalculada integralmente com diferença zero** em relação ao motor e à planilha, e os lançamentos L1–L4 estão **conciliados** (débitos = créditos = {{PARTIDAS_DOBRADAS}}): bruto {{BRUTO_TOTAL}}, INSS {{INSS_TOTAL}}, FGTS {{FGTS_TOTAL}}, líquido {{LIQUIDO_A}} (cenário A) ou {{LIQUIDO_B}} (cenário B), provisões {{PROVISOES_TOTAL}} e custo total {{CUSTO_SIMPLES}}.

Permanecem **abertos, sob responsabilidade da administração da Rota Sul**, os achados AUD-01 (ASO), AUD-02 (S-2200 e termos de VT/VR), AUD-03 (documentos civis), AUD-04 (relatório de vendas), AUD-05 (jornada do E1), AUD-06 (CNAEs vedados no Simples), AUD-07 (SST, ponto e pró-labore) e AUD-08 (avaliação da causa trabalhista pelo advogado).$t$)
  ) AS v(doc, cod, txt)
  WHERE s.empresa_id = 1 AND s.documento = v.doc AND s.codigo_secao = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 17 THEN RAISE EXCEPTION 'Seções: % (esperado 17)', n; END IF;
  UPDATE erp.documento_secao SET titulo = 'PT-03 — Recálculo Independente da Folha (100% dos Empregados)'
   WHERE empresa_id = 1 AND documento = 'd2_13_auditoria' AND codigo_secao = 'pt_03_recalculo_independente_da_';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Título PT-03: %', n; END IF;

  -- 5. Pós-condições: nenhum resto de legado
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = ANY(c_docs)
     AND (conteudo_md ~ '(SRT00189|4 passagens|4\.238|4\.128|234,00|189,20|154,80|917,40|5\.045|220 fórmulas|23/11/2026|\(v1\)|1ª entrega|PAT)'
          OR conteudo_md ~ 'R\$ (90,00|122,68|212,68|226,67|998,04|1\.418,26|2\.416,30|2\.833,33|504,00|330,00)');
  IF n <> 0 THEN RAISE EXCEPTION 'Seções dos Docs 11–13 com legado: %', n; END IF;
  SELECT count(*) INTO n FROM erp.auditoria_folha WHERE empresa_id = 1
     AND (concat_ws(' ', titulo, norma_referencia, objetivo_ou_evidencia, procedimento_ou_risco, conclusao_ou_correcao) ~ '(SRT00189|v1|V1|4 passagens|4\.238|R\$ 1\.129)'
          OR valor_v1_centavos IS NOT NULL);
  IF n <> 0 THEN RAISE EXCEPTION 'Auditoria com legado: %', n; END IF;
  SELECT count(*) INTO n FROM erp.parametro_legal WHERE empresa_id = 1 AND (strpos(norma_citada, 'SRT00189') > 0 OR strpos(apontamento_auditoria, 'SRT00189') > 0);
  IF n <> 0 THEN RAISE EXCEPTION 'Parâmetros com SRT00189: %', n; END IF;

  -- 6. Homologação: competência, rubricas, lançamentos, 13 registros de auditoria e 17 seções
  UPDATE erp.folha_competencia SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Folha 09/2026 conferida (27/11/2026) contra a régua (C-23 a C-29, C-48): valores do motor com 2 conduções/dia; recálculo independente e conciliação com diferença zero.'
   WHERE empresa_id = 1 AND competencia = '2026-09' AND status_validacao <> 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Competência homologada: %', n; END IF;

  UPDATE erp.folha_item fi SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Rubrica do motor conferida (27/11/2026) com a regra e a fonte (doc. 11) e com o recálculo independente (doc. 13).'
  FROM erp.folha_competencia fc WHERE fc.id = fi.competencia_id AND fc.empresa_id = 1 AND fi.origem_registro = 'motor_calculo' AND fi.status_validacao <> 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n < 20 THEN RAISE EXCEPTION 'Rubricas homologadas: % (esperado ao menos 20)', n; END IF;

  UPDATE erp.lancamento SET status_validacao = 'homologado_contadora', atualizado_em = now()
   WHERE empresa_id = 1 AND origem_registro = 'motor_calculo' AND tag_ref IN ('folha_l1', 'folha_l2', 'folha_l3', 'folha_l4') AND status_validacao <> 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Lançamentos homologados: % (esperado 4)', n; END IF;

  UPDATE erp.auditoria_folha SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = CASE tipo_registro
      WHEN 'papel_trabalho' THEN 'Papel de trabalho revisado (27/11/2026): escopo no cliente, competência 09/2026 (EC02, aulas 14 e 15), sem referências à entrega anterior.'
      ELSE 'Achado do cliente conferido (27/11/2026): evidência com origem, risco, valor envolvido (motor ou resposta do cliente), correção, responsável e prazo.'
    END
   WHERE empresa_id = 1 AND status_validacao <> 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 13 THEN RAISE EXCEPTION 'Auditoria homologada: % (esperado 13)', n; END IF;

  UPDATE erp.documento_secao SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Docs 11–13 revisados (27/11/2026, achados FO-01 a FO-12): texto de regra com marcadores vivos; rubricas, partidas, conciliação, recibos, recálculo e achados gerados do banco; 2 conduções/dia; auditoria do cliente.'
   WHERE empresa_id = 1 AND documento = ANY(c_docs) AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 17 THEN RAISE EXCEPTION 'Seções homologadas: % (esperado 17)', n; END IF;
END
$a$;

SELECT 'auditoria' AS item, count(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados, count(*) AS total FROM erp.auditoria_folha WHERE empresa_id = 1
UNION ALL SELECT 'rubricas', count(*) FILTER (WHERE fi.status_validacao = 'homologado_contadora'), count(*) FROM erp.folha_item fi JOIN erp.folha_competencia fc ON fc.id = fi.competencia_id WHERE fc.empresa_id = 1
UNION ALL SELECT 'lançamentos L1–L4', count(*) FILTER (WHERE status_validacao = 'homologado_contadora'), count(*) FROM erp.lancamento WHERE empresa_id = 1 AND tag_ref LIKE 'folha_l%'
UNION ALL SELECT 'seções Docs 11–13', count(*) FILTER (WHERE status_validacao = 'homologado_contadora'), count(*) FROM erp.documento_secao WHERE empresa_id = 1 AND documento IN ('d2_11_folha', 'd2_12_resumo_contab', 'd2_13_auditoria');
