-- Dossiê 2, etapa 5 (Estação 5 — Premissas e IA): 20 premissas, Docs 14 e 15, diário de IA e data de pagamento da folha.
-- Achados PRM-01 a PRM-11 (REVISAO_D2_ROTA_SUL.md). Decisões da usuária (27/11/2026): PRM-04 (porte EPP), PRM-06 (Res. CFC 1.590/2020
-- para contrato/distrato; 1.708/2023 só para registro), PRM-07 (CCT como premissa didática, registro não localizado), PRM-08 (pagamento 06/10/2026).
-- A revisita dos Docs 01 a 04 (PRM-06 e G-01/G-05) fica para o SQL 13. Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
  c_socias constant text := 'Sócias da PRISMA JRNA (Nathalia Peres Araujo e Jeovanna Ripardo Lustosa)';
BEGIN
  -- 0. Estado esperado
  SELECT count(*) INTO n FROM erp.consulta_normativa WHERE empresa_id = 1 AND dossie = 'D2' AND status_validacao = 'pendente_revisao';
  IF n <> 20 THEN RAISE EXCEPTION 'Premissas fora do estado esperado (% de 20)', n; END IF;
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento IN ('d2_14_premissas', 'd2_15_ia') AND status_validacao = 'pendente_revisao';
  IF n <> 9 THEN RAISE EXCEPTION 'Seções dos Docs 14–15 fora do estado esperado (% de 9)', n; END IF;
  SELECT count(*) INTO n FROM auditoria.diario_ia WHERE empresa_id = 1 AND dossie = 'D2' AND id BETWEEN 186 AND 192 AND status_validacao = 'pendente_revisao';
  IF n <> 7 THEN RAISE EXCEPTION 'Diário de IA fora do estado esperado (% de 7)', n; END IF;
  SELECT count(*) INTO n FROM auditoria.diario_ia WHERE chave = 'ia:d2:revisao-plataforma-2026-11';
  IF n <> 0 THEN RAISE EXCEPTION 'Registro da revisão já existe no diário de IA'; END IF;
  SELECT count(*) INTO n FROM erp.folha_competencia WHERE empresa_id = 1 AND competencia = '2026-09' AND data_pagamento = DATE '2026-10-07';
  IF n <> 1 THEN RAISE EXCEPTION 'Data de pagamento fora do estado esperado'; END IF;

  -- 1. Premissas (PRM-02 a PRM-09): decisão sem números calculados, fonte com link e acesso, quem decide, quando e impacto
  UPDATE erp.consulta_normativa c SET
      enunciado = coalesce(v.enun, c.enunciado), resposta_autoral = coalesce(v.resp, c.resposta_autoral),
      norma_citada = coalesce(v.norma, c.norma_citada), link_oficial = coalesce(v.link, c.link_oficial),
      data_acesso = coalesce(v.acesso, c.data_acesso), decisao_impactada = coalesce(v.dec, c.decisao_impactada),
      impacto_se_alterada = coalesce(v.imp, c.impacto_se_alterada), responsavel_decisao = coalesce(v.quem, c.responsavel_decisao),
      prazo_decisao = coalesce(v.quando, c.prazo_decisao), apontamento_auditoria = NULL, atualizado_em = now()
  FROM (VALUES
    (1, 'PR-01 — Enquadramento tributário (Simples Nacional), porte EPP e CNAE principal',
       $t$A Rota Sul é optante pelo Simples Nacional desde o início das atividades (resposta do cliente no grupo da disciplina, G-05): Anexo I (comércio), CPP dentro do DAS e classificação tributária 01 no eSocial. Porte **EPP**: o cliente informou receita bruta de R$ 2.878.147,98 nos últimos 12 meses (G-05), acima do limite da ME (R$ 360.000,00) e abaixo do da EPP (R$ 4.800.000,00) (LC 123/2006, art. 3º). CNAE principal 4530-7/02 (premissa: primeiro CNAE da atividade-foco, EC02, p. 2), a confirmar no cartão CNPJ (DOC-08).$t$,
       'LC nº 123/2006, art. 3º, I e II, art. 13, VI, e art. 18; resposta do cliente no grupo (G-05)', NULL, DATE '2026-11-27',
       'Docs. 01 (enquadramento), 06 (S-1000, classificação 01), 11 a 13 (CPP no DAS); Dossiê 3 (receita bruta dos 12 meses e faixa do DAS)',
       'Se a receita dos 12 meses for outra, muda a faixa do DAS (Dossiê 3), não a folha. Se o CNAE principal for outro, revisar cadastro, anexo do Simples e enquadramento sindical.',
       'RT da PRISMA JRNA (Nathalia Peres Araujo), com confirmação documental do cliente (DOC-08)', 'Decidido em 14/09/2026; confirmação documental até 30/09/2026 (DOC-08)'),
    (2, NULL,
       $t$A atividade real da Rota Sul é a importação e a distribuição de pneus e câmaras de ar para motocicletas (EC02, p. 1) e o comércio de pneumáticos (4530-7/02 e 4530-7/05) e de peças e acessórios para motocicletas (4541-2/02 e 4541-2/06), com importação própria (p. 2). O Anexo I lista sob "Importação e Exportação" também 4541-2/01 e 4541-2/03 (motocicletas) e 4511-1/02 (automóveis usados) (pp. 7 a 9), o que expõe a empresa à vedação do Simples para quem importa automóveis e motocicletas (LC 123/2006, art. 17, VIII). Decisão: manter a Rota Sul no Simples (PR-01) e recomendar a exclusão de 4541-2/01, 4541-2/03 e 4511-1/02 na 3ª Alteração Contratual (R-01), preservando os CNAEs de pneus e peças. A filial de Itajaí deve ter objeto restrito à importação de pneus (resposta do cliente, G-02); o Simples não proíbe filial (não está entre as vedações do art. 17). Risco material, nível crítico.$t$,
       'LC nº 123/2006, art. 17, VIII, e arts. 29 e 30; resposta do cliente no grupo (G-02)', NULL, DATE '2026-11-27',
       NULL, NULL, NULL, '20/10/2026 (3ª Alteração Contratual — PEND-02)'),
    (3, 'PR-03 — Convenção Coletiva de Trabalho (CCT) de referência — premissa didática',
       $t$A Rota Sul não soube informar o sindicato da categoria (resposta do cliente no grupo, G-11). Adotada, como manda a aula de DP (p. 21: "Premissa didática: usar SECEG × SINDILOJAS-GO"), a CCT SECEG × SINDILOJAS-GO, Termo Aditivo 2026/2027: cl. 3ª (piso geral de R$ 1.722,25 desde 01/04/2026; garantia do vendedor em Goiânia de R$ 1.863,00), cl. 6ª (VT de salário misto com base até R$ 2.257,50) e cl. 11ª (contribuição negocial de 3,33%, teto de R$ 148,00, com direito de oposição) (aula de DP, p. 29). Pesquisa de 27/11/2026: número de registro não localizado no Mediador; a lista pública de CCTs de Goiás traz outras convenções do SINDILOJAS-GO 2025/2027 (GO000379/2025, GO000758/2025 e GO000822/2025), nenhuma com o SECEG. Pendência: confirmar o sindicato da atividade preponderante e o registro no Mediador.$t$,
       'CCT SECEG × SINDILOJAS-GO — Termo Aditivo 2026/2027, cl. 3ª, 6ª e 11ª (aula de DP, pp. 21 e 29); registro no Mediador não localizado em 27/11/2026',
       'https://www3.mte.gov.br/sistemas/mediador/', DATE '2026-11-27',
       'Docs. 06 a 11 (piso, base do VT de salário misto e contribuição negocial)',
       'Se outra CCT for a aplicável, refazer o confronto de piso, a base do VT e a contribuição negocial; a folha é recalculada pelo motor.',
       c_socias || ', com confirmação da atividade preponderante pelos sócios da Rota Sul', '20/10/2026 (confirmação do sindicato e do registro)'),
    (4, 'PR-04 — Tabela progressiva do INSS (4 faixas — 2026)', NULL, NULL, NULL, NULL,
       'Doc. 11 (rubrica INSS-RET de E1 e E2); Doc. 12 (L1 e DCTFWeb)',
       'Tabela oficial: só muda com nova portaria; o motor recalcula.', 'DP da PRISMA JRNA (aplicação da tabela oficial)', 'Vigente em 2026 (competência 09/2026)'),
    (5, 'PR-05 — Tabela do IRRF 2026, desconto simplificado e redução da Lei nº 15.270/2025', NULL, NULL, NULL, NULL,
       'Doc. 11 (rubrica IRRF de E1 e E2)',
       'Rendimentos acima de R$ 5.000,00 passam à redução parcial ou à tabela cheia; o motor aplica a regra automaticamente.', 'DP da PRISMA JRNA (aplicação da tabela oficial)', 'Vigente em 2026 (competência 09/2026)'),
    (6, 'PR-06 — Salário-família: elegibilidade pela remuneração do mês e cota 2026',
       $t$Não há salário-família para o E1: o direito é definido pela remuneração que seria devida no mês, independentemente dos dias trabalhados (portaria interministerial anual, art. 4º, § 2º), e o salário contratual de R$ 2.400,00 supera o limite de R$ 1.980,38 (Portaria Interministerial MPS/MF nº 13/2026; aula de DP, p. 24). A cota de R$ 67,54 fica parametrizada (proporcional nos meses de admissão e demissão — § 4º). O E2 não tem dependentes. O filho do E1 vale como dependente no IRRF.$t$,
       'Portaria Interministerial MPS/MF nº 13/2026 (valores de 2026); regra do art. 4º, §§ 2º e 4º, conferida no texto da Portaria Interministerial MPS/MF nº 26/2023',
       'https://www.gov.br/previdencia/pt-br/assuntos/rpps/legislacao-dos-rpps/portarias/PortariaInterministerialMPSMFn26de10jan2023atualizadaem08mai2023.pdf', DATE '2026-11-27',
       'Docs. 06 (declaração de dependentes) e 11 (rubrica SAL-FAMILIA)',
       'Se o salário contratual ficar dentro do limite, a cota passa a ser devida, proporcional aos dias no mês de admissão.', 'DP da PRISMA JRNA', 'Decidido em 28/09/2026 (folha)'),
    (7, 'PR-07 — Base de vendas líquidas e DSR do Empregado 2',
       $t$Adotada a premissa didática de vendas líquidas de R$ 60.000,00 de 21 a 30/09/2026 (aula de DP, p. 25): comissão de 1,5% e DSR em rubrica destacada (comissão ÷ 9 dias trabalháveis × 1 repouso, em 27/09). Valores no doc. 11. O relatório comercial de vendas fica como pendência (DOC-13, PEND-05, AUD-04).$t$,
       NULL, NULL, NULL,
       'Docs. 10, 11, 12 e 13 (comissão, DSR, INSS, FGTS e contribuição negocial do E2)',
       'Outro valor de vendas muda comissão, DSR, INSS, FGTS, contribuição negocial e provisões futuras do E2; o motor recalcula.',
       'Diretoria comercial da Rota Sul (relatório de vendas); DP da PRISMA JRNA aplica', '09/10/2026 (DOC-13 — AUD-04)'),
    (8, NULL,
       $t$O Estudo de Caso 02 informa "Vale-transporte (2 conduções/dia)" para os dois empregados (p. 3), e a aula de DP fixa "VT: 2 viagens/dia" (p. 24). Decisão: 2 viagens por dia, na tarifa do transporte coletivo de Goiânia (R$ 4,30, conferida na Carta de Serviço do Governo de Goiás de 08/05/2026). O desconto do empregado é o menor valor entre 6% do salário básico proporcional e o custo do vale-transporte (Lei nº 7.418/1985, art. 4º, parágrafo único); para o vendedor (salário misto), a base do desconto é limitada pela cl. 6ª do Termo Aditivo 2026/2027. Os valores são calculados pelo motor da folha (docs. 11 e 12). A quantidade será confirmada no termo de opção assinado (DOC-12).$t$,
       'Lei nº 7.418/1985, art. 4º, parágrafo único; Termo Aditivo 2026/2027 da CCT SECEG × SINDILOJAS-GO, cl. 6ª; Carta de Serviço do Governo de Goiás (tarifa)',
       NULL, NULL, NULL, NULL, NULL, '09/10/2026 (termos de VT e VR — DOC-12, AUD-02)'),
    (9, 'PR-09 — Vale-refeição do Empregado 1 (CLT, art. 457, § 2º)',
       $t$O E1 recebe vale-refeição de R$ 30,00 por dia trabalhado (EC02, p. 3), custeado pela empresa e fornecido sem pagamento em dinheiro: não integra a remuneração nem tem incidência de INSS, FGTS e IRRF (CLT, art. 457, § 2º; aula de DP, p. 27). A adesão ao PAT não consta do caso e não é premissa; se houver, passa a valer também a Lei nº 6.321/1976. O E2 não recebe vale-refeição (EC02, p. 3).$t$,
       'CLT, art. 457, § 2º; Estudo de Caso 02, p. 3', 'https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm', DATE '2026-11-27',
       'Docs. 06 (termo de VR), 11 (rubrica de VR) e 12 (lote L3)',
       'Se o VR for pago em dinheiro, passa a integrar a remuneração (com incidências); a CCT pode trazer regra própria.',
       'Diretoria da Rota Sul (forma de fornecimento); DP da PRISMA JRNA', '09/10/2026 (termo de VR assinado — DOC-12)'),
    (10, 'PR-10 — Contribuição negocial (CCT — cenários A e B)',
       $t$Contribuição negocial de 3,33% da remuneração, teto de R$ 148,00 (Termo Aditivo 2026/2027, cl. 11ª — aula de DP, p. 29), com direito de oposição (STF, Tema 935). O cenário A (sem oposição documentada) desconta; o cenário B (com oposição) não. A empregadora não induz nem fornece modelo de oposição. Valores no doc. 11.$t$,
       NULL, NULL, NULL,
       'Docs. 06, 11 e 12 (rubrica NEGOCIAL, líquido nos cenários A e B, conta 2.1.2.05)',
       'Oposição documentada leva ao cenário B: o desconto sai e o líquido sobe.', 'Cada empregado (oposição perante o sindicato); DP da PRISMA JRNA aplica o cenário', 'Até o fechamento de cada folha'),
    (11, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '09/10/2026 (PEND-04 — AUD-05)'),
    (12, 'PR-12 — Provisões trabalhistas (13º, férias, 1/3 e FGTS)',
       $t$Provisionar 1/12 avo de 13º, férias e 1/3 só para quem trabalha 15 dias ou mais no mês (Lei nº 4.090/1962, art. 1º, § 2º; CLT, art. 146, parágrafo único): o E1 adquire o avo em setembro; o E2 (10 dias) não. FGTS de 8% sobre as provisões, sem CPP (Simples). Valores no doc. 11 (rubricas PROV) e no lote L4 (doc. 12). A partir de 10/2026, a base do E2 inclui a média de comissões e DSR (CLT, art. 142, § 3º).$t$,
       'Lei nº 4.090/1962, art. 1º, § 2º; CLT, arts. 142 e 146; NBC TG 33 (benefícios a empregados)', 'https://www.planalto.gov.br/ccivil_03/leis/l4090.htm', DATE '2026-11-27',
       'Docs. 11, 12 (lote L4) e 13', 'Outra contagem de dias muda o avo e o lote L4.', 'Contabilidade da PRISMA JRNA', 'Decidido em 30/09/2026 (fechamento)'),
    (13, 'PR-13 — FGTS Digital, eSocial S-1.3 e SST (S-2220 e S-2240)',
       $t$FGTS de 8% recolhido pelo FGTS Digital; eventos do eSocial (leiaute S-1.3) registrados sem inventar recibo; o S-2220 depende do ASO (NR-7) e o S-2240 depende do inventário de riscos (PGR, ou DIR para ME/EPP — NR-1, item 1.8.4), com LTCAT só se houver agente nocivo.$t$,
       'MOS eSocial S-1.3; Lei nº 8.036/1990; NR-1 (item 1.8.4) e NR-7', NULL, NULL,
       'Docs. 06 (tabela de eventos) e 13 (AUD-01, AUD-02 e AUD-07)',
       'Sem ASO e sem inventário de riscos, o S-2220 e o S-2240 ficam pendentes e a empresa fica exposta a autuação.',
       'Diretoria da Rota Sul + clínica SST; DP da PRISMA JRNA transmite', 'Imediato (PEND-01) e 15/10/2026 (PEND-07)'),
    (14, 'PR-14 — Normas do CFC aplicadas (contrato, distrato e registro) e dados da PRISMA JRNA',
       $t$Proposta, contrato, distrato e comunicação com o contador anterior seguem a Resolução CFC nº 1.590/2020 (contrato escrito após a proposta, conteúdo mínimo, distrato obrigatório e comunicação ao novo responsável técnico — arts. 1º, 2º e 5º a 9º). O registro da PRISMA JRNA no CRC segue a Resolução CFC nº 1.708/2023 ("dispõe sobre o registro das organizações contábeis"; revogou a nº 1.555/2018). Dados da contratada padronizados com o Dossiê 1: CNPJ 48.123.456/0001-90, CRC-DF 004.821/O-2 e RT Nathalia Peres Araujo, CRC-DF 025.431/O-7.$t$,
       'Resolução CFC nº 1.590/2020; Resolução CFC nº 1.708/2023 (art. 28); NBC PG 01', 'https://www.legisweb.com.br/legislacao/?id=452099', DATE '2026-11-27',
       'Docs. 02, 03 e 04 (fundamentação) e Doc. 01 (R-07)',
       'Citar a norma errada fragiliza a proposta, o contrato e o termo de RT; a correção dos Docs. 01 a 04 é feita na revisita (SQL 13).',
       c_socias, 'Corrigido em 27/11/2026'),
    (15, 'PR-15 — Pró-labore dos sócios e distribuição de lucros',
       $t$Não há pró-labore definido em 09/2026 e não se lança pró-labore fictício (PEND-08). O cliente informou no grupo que a retirada é "80% do lucro líquido do mês", de forma verbal e sem valor fixado (G-09). Orientação da PRISMA JRNA: formalizar o pró-labore dos sócios administradores (segurados obrigatórios — Lei nº 8.212/1991, art. 12, V, "f"; evento S-2300) e distribuir lucros só com base em escrituração, sem distribuição enquanto houver débitos fiscais em aberto (Lei nº 4.357/1964, art. 32).$t$,
       'Lei nº 8.212/1991, art. 12, V, "f"; Lei nº 4.357/1964, art. 32; resposta do cliente no grupo (G-09)', NULL, DATE '2026-11-27',
       'Docs. 06 (S-2300) e 13 (AUD-07)',
       'Com pró-labore, entram o S-2300, a rubrica no S-1200 e a retenção de INSS do sócio.',
       'Sócios administradores (Helena e Bruno), com orientação da PRISMA JRNA', '15/10/2026 (AUD-07)'),
    (16, 'PR-16 — Segregação funcional das despesas de pessoal (administrativas × comerciais)',
       $t$Despesas de pessoal segregadas por função na DRE (NBC TG 26, item 99): E1 em despesas administrativas (4.1.1.*) e E2 em despesas comerciais (4.2.1.*), nos lotes L1 a L4 do doc. 12. O plano de contas reduzido definitivo fica para o Dossiê 4.$t$,
       NULL, NULL, NULL,
       'Doc. 12 (lançamentos L1 a L4)', 'Reclassificar contas muda a apresentação da DRE, não os totais.', 'Contabilidade da PRISMA JRNA', 'Decidido em 30/09/2026; plano definitivo no Dossiê 4'),
    (17, 'PR-17 — Sensibilidade de exclusão do Simples Nacional (27,8% sobre a folha)',
       $t$Sensibilidade, não valor da folha: se a Rota Sul for excluída do Simples (PR-02), a folha passaria a ter CPP de 20%, RAT de 2% e terceiros de 5,8% (27,8%) sobre remuneração e provisões. O encargo adicional é calculado pelo motor e aparece no doc. 12 e no AUD-06. RAT de 2% e terceiros de 5,8% são premissas da dupla para o comércio, a confirmar pelo CNAE e pelo FAP.$t$,
       NULL, NULL, NULL,
       'Docs. 12 (sensibilidade) e 13 (AUD-06)', 'Outro RAT/FAP ou outra alíquota de terceiros muda o valor da sensibilidade.', c_socias, 'Decidido em 30/09/2026'),
    (18, 'PR-18 — Dados pessoais fictícios dos empregados e do dependente (LGPD)',
       $t$Nomes, CPFs, RGs e endereços dos empregados e do filho do E1 são fictícios, para fins didáticos, e tratados como informados verbalmente pelos sócios (EC02, p. 2: dados a confirmar documentalmente); os documentos comprobatórios ficam a coletar e conferir (DOC-09, AUD-03). Os dados de trabalho (cargo, CBO, admissão, salário, jornada, benefícios e dependente) são os do caso. Decisão das sócias em 27/11/2026: a empresa, o CNPJ e o NIRE também são fictícios, e a identificação concreta deixa fichas, contratos e termos completos.$t$,
       NULL, NULL, NULL,
       'Docs. 06 a 12', 'Os dados reais substituem os fictícios na coleta (DOC-09), sem mudar a folha.', c_socias, 'Decidido em 27/11/2026'),
    (19, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (20, NULL, NULL, 'Premissa da dupla; Resolução CFC nº 1.590/2020, art. 2º (honorários no contrato escrito)', 'https://www.normaslegais.com.br/legislacao/resolucao-cfc-1590-2020.htm', DATE '2026-11-27', NULL, NULL, NULL, NULL)
  ) AS v(num, enun, resp, norma, link, acesso, dec, imp, quem, quando)
  WHERE c.empresa_id = 1 AND c.dossie = 'D2' AND c.numero_questao = v.num;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 20 THEN RAISE EXCEPTION 'Premissas: % (esperado 20)', n; END IF;

  -- 2. Data de pagamento (PRM-08): 5º dia útil de outubro/2026 contando o sábado
  UPDATE erp.folha_competencia SET data_pagamento = DATE '2026-10-06', atualizado_em = now(),
    justificativa_contadora = justificativa_contadora || ' Pagamento em 06/10/2026: 5º dia útil de outubro com o sábado na contagem (CLT, art. 459, § 1º; IN nº 1/1989) — decisão de 27/11/2026 (PRM-08).'
   WHERE empresa_id = 1 AND competencia = '2026-09';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Data de pagamento: %', n; END IF;

  -- 3. Doc 14 (PRM-01): tabelas saem do banco
  UPDATE erp.documento_secao s SET conteudo_md = v.txt, titulo = coalesce(v.tit, s.titulo), atualizado_em = now()
  FROM (VALUES
    ('d2_14_premissas', 'cabecalho', NULL, $t$# REGISTRO NUMERADO DE PREMISSAS, FONTES OFICIAIS E DECISÕES — DOSSIÊ 2

**Dossiê 2 — Onboarding e Departamento Pessoal (Competência 09/2026)**
**Cliente:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. (Matriz Goiânia-GO / Filial Itajaí-SC)
**Escritório responsável:** PRISMA JRNA Auditoria e Contabilidade Ltda. (Líder: Jeovanna Ripardo Lustosa | Revisão técnica: Nathalia Peres Araujo — CRC-DF `025.431/O-7`)$t$),
    ('d2_14_premissas', '1_objetivo_deste_registro', NULL, $t$Este documento reúne, de forma numerada e rastreável (`PR-01` a `PR-20`), as premissas técnicas, normativas, contábeis e operacionais adotadas nos documentos 01 a 13 do Dossiê 2, com a decisão e o motivo, os documentos impactados, a fonte oficial (norma, artigo ou cláusula, link e data de acesso), quem decide, até quando e o impacto se a premissa for alterada.$t$),
    ('d2_14_premissas', '2_registro_numerado_de_premissas', '2. Registro Numerado de Premissas (`PR-01` a `PR-20`)', $t$O registro numerado está na **Tabela 1**, gerada pela plataforma: cada premissa traz a decisão e o motivo, os documentos impactados e a fonte oficial com link e data de acesso. Os parâmetros oficiais usados pelo motor da folha (INSS, IRRF, salário-família, FGTS e cláusulas da CCT) estão na **Tabela 3**, com norma, link e data de consulta. Quando uma premissa se apoia em resposta do cliente, a fonte indica a resposta (carta de onboarding ou respostas dadas pelo professor no grupo da disciplina).$t$),
    ('d2_14_premissas', '3_quadro_de_decisoes_e_pendencia', NULL, $t$A **Tabela 2** traz, para cada premissa, quem decide, até quando e o impacto se ela for alterada. As pendências que dependem do cliente seguem no doc. 05 (`PEND-01` a `PEND-08`), e os achados de auditoria, no doc. 13 (`AUD-01` a `AUD-08`).$t$)
  ) AS v(doc, cod, tit, txt)
  WHERE s.empresa_id = 1 AND s.documento = v.doc AND s.codigo_secao = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Doc 14: % (esperado 4)', n; END IF;

  -- 4. Doc 15 (PRM-10): o que foi feito, com que ferramenta, o que confirmou cada ponto e as decisões humanas
  UPDATE erp.documento_secao s SET conteudo_md = v.txt, atualizado_em = now()
  FROM (VALUES
    ('cabecalho', $t$# DECLARAÇÃO DE USO DE INTELIGÊNCIA ARTIFICIAL, VERIFICAÇÃO EM FONTES OFICIAIS E PROTEÇÃO DE DADOS (LGPD)

**Disciplina:** Laboratório Contábil (`CCA 0174`) — 2026/2 — Universidade de Brasília (UnB / FACE / CCA)
**Dossiê:** Dossiê 2 — Onboarding e Departamento Pessoal da Rota Sul Importadora (Competência 09/2026)
**Dupla (Grupo G07):** Jeovanna Ripardo Lustosa e Nathalia Peres Araujo
**Escritório simulado:** PRISMA JRNA Auditoria e Contabilidade Ltda.
**Última revisão:** 27/11/2026 (revisão na plataforma PRISMA JRNA)$t$),
    ('1_declaracao_de_transparencia_e_', $t$Declaramos que usamos ferramentas de inteligência artificial generativa como **apoio** na redação, na organização, na construção da plataforma e na revisão deste dossiê. **A responsabilidade técnica, a verificação em fonte oficial e as decisões são da dupla.** O registro por entregável está na **Tabela 1** (diário de uso de IA).

| Etapa | Escopo | Finalidade do uso de IA |
|---|---|---|
| Primeira entrega (V1) | Docs. 01 a 13 | Apoio à redação inicial de proposta, contrato, termo de RT, fichas, contratos de experiência e relatório técnico |
| Revisão da V1 (V2) | Docs. 01 a 15 | Mapeamento dos arquivos, análise das lacunas apontadas na devolutiva e rascunhos de revisão para decisão da dupla |
| Plataforma PRISMA JRNA | Base de dados e documentos | Extração do caso para o banco (com quarentena), motor da folha, eventos do eSocial, auditoria e emissão dos documentos a partir do banco |
| Revisão na plataforma (26 e 27/11/2026) | Docs. 01 a 15, por produto da régua (P1 a P9) | Conferência de cada registro contra o material original e a legislação, achados registrados, propostas de correção e scripts de homologação executados pela dupla |$t$),
    ('2_ferramentas_utilizadas_e_resum', $t$### 2.1 Ferramentas
1. **Google Gemini** — primeira entrega (V1).
2. **Antigravity (Gemini)** — revisão da V1 (V2): mapeamento, análise das lacunas e rascunhos.
3. **Claude (Anthropic), via Claude Code no VS Code** — construção da plataforma PRISMA JRNA e revisão do Dossiê 2 na plataforma (26 e 27/11/2026).

### 2.2 Comandos resumidos (sem dados pessoais reais)
- *"Auxiliar na estruturação de proposta de honorários, contrato de prestação de serviços contábeis e termo de responsabilidade técnica para o onboarding de uma empresa importadora do Simples Nacional (caso didático)."* (V1)
- *"Elaborar minutas iniciais de ficha de registro e contrato de experiência para dois empregados (Auxiliar Administrativo e Vendedor com comissão)."* (V1)
- *"Elaborar o plano de correção dos pontos da devolutiva, com perguntas diretas para a dupla onde os documentos não forem suficientes."* (V2)
- *"Criar pessoas fictícias para o Empregado 1 e o Empregado 2, já que é um trabalho acadêmico."* (V2 — origem da `PR-18`)
- *"Revisar tudo o que foi feito e retomar o trabalho"*; *"avançar pelos documentos gerados e pelos produtos da régua"*; *"registrar cada achado novo"*. (revisão na plataforma)
- *"Usar o material dos professores como fonte; legado (rascunhos e versões anteriores) só fica se o original confirmar."* (regra da revisão na plataforma)$t$),
    ('3_verificacao_independente_das_r', $t$Nada sugerido por IA foi aceito sem conferência no material original ou em fonte oficial. Na revisão de 26 e 27/11/2026, cada ponto foi conferido assim:

| Tema | Fonte que confirmou | O que confirmou |
|---|---|---|
| Dados do caso (empregados, salários, jornadas, benefícios, dependente) | Estudo de Caso 02, pp. 2 e 3 | Cargos, CBO, admissões, salários, experiência 45 + 45 e 30 + 60, VT de 2 conduções/dia, VR de R$ 30,00 só para o E1, 1 filho de 6 anos |
| Parâmetros da folha e da CCT | Aula de DP, pp. 24 a 29 | Salário-família 2026, comissão sobre R$ 60.000,00 e DSR, INSS 2026, piso, garantia do vendedor, base do VT de salário misto e contribuição negocial |
| Salário-família no mês de admissão | Portaria Interministerial MPS/MF, art. 4º, §§ 2º e 4º (texto de 2023 conferido) | Direito definido pela remuneração devida no mês, independentemente dos dias trabalhados; cota proporcional na admissão |
| Normas do CFC | Resoluções CFC nº 1.590/2020 e nº 1.708/2023 | A 1.590/2020 rege contrato, distrato e comunicação ao novo RT; a 1.708/2023 rege o registro das organizações contábeis (corrigido na `PR-14`) |
| Registro da CCT | Mediador do MTE e lista pública de CCTs de Goiás | Registro "SRT00189/2025" não localizado; CCT tratada como premissa didática da aula (`PR-03`) |
| Tarifa do VT | Carta de Serviço do Governo de Goiás (08/05/2026) | Tarifa de R$ 4,30 |
| Vedação do Simples | LC nº 123/2006, art. 17, VIII (Planalto) | Vedação para quem importa automóveis e motocicletas |
| Cálculo da folha | Recálculo independente da plataforma (doc. 13) | Diferença zero entre o motor e o recálculo, rubrica a rubrica |$t$),
    ('4_correcoes_humanas_realizadas_e', $t$### 4.1 Decisões e correções da dupla
1. **Quarentena:** todo dado extraído ou gerado por IA entra como pendente e só vale após a homologação expressa da contadora, registro a registro.
2. **Fonte de verdade:** número só vale se calculado pelo motor da plataforma; rascunhos e versões anteriores não são fonte.
3. **Vale-transporte:** 2 conduções/dia, como no caso e na aula (a V1 usava 4).
4. **Dados pessoais fictícios mantidos** (`PR-18`), com documentos comprobatórios como pendência real.
5. **Auditoria do cliente:** os achados do doc. 13 passaram a ser da Rota Sul, e não da entrega anterior da dupla.
6. **Contabilização do VT/VR** contra passivo "VT/VR a pagar", quitado em outubro.
7. **CCT** como premissa didática, sem número de registro não confirmado; **porte EPP** com a receita informada pelo cliente; **pagamento em 06/10/2026**; **Resolução CFC nº 1.590/2020** para contrato e distrato.

### 4.2 Proteção de dados pessoais (LGPD — Lei nº 13.709/2018)
- Nenhum dado pessoal real foi submetido a ferramentas de IA.
- Empresa, sócios, empregados, dependente e escritório são fictícios ou anonimizados para fins didáticos (art. 6º da LGPD: finalidade, adequação, necessidade e segurança).

---

Brasília-DF, 27 de novembro de 2026.

**Nathalia Peres Araujo** (Responsável Técnica — CRC-DF `025.431/O-7`) e **Jeovanna Ripardo Lustosa** — Dupla G07 (PRISMA JRNA)$t$)
  ) AS v(cod, txt)
  WHERE s.empresa_id = 1 AND s.documento = 'd2_15_ia' AND s.codigo_secao = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 5 THEN RAISE EXCEPTION 'Doc 15: % (esperado 5)', n; END IF;

  -- 5. Diário de IA (PRM-11): registros legados sem afirmações falsas + registro desta revisão
  UPDATE auditoria.diario_ia d SET fonte_oficial = coalesce(v.fonte, d.fonte_oficial), prompt_resumo = coalesce(v.prompt, d.prompt_resumo),
         revisao_humana = coalesce(v.rev, d.revisao_humana)
  FROM (VALUES
    (186, NULL, 'Decomposição dos itens da devolutiva em plano de correção e questionário objetivo para decisão da dupla.', NULL),
    (188, 'Res. CFC nº 1.590/2020 (contrato e distrato) + Res. CFC nº 1.708/2023 (registro) + Contrato Social do Dossiê 1', 'Alinhamento da proposta, do contrato e do termo de RT com o Dossiê 1 e com a hora técnica de R$ 125,00 (PR-20).',
       'Eliminados os campos a preencher; na revisão de 27/11/2026, a fundamentação passou à Res. CFC nº 1.590/2020 (a 1.708/2023 trata do registro das organizações contábeis).'),
    (190, NULL, 'Remoção de resíduos de IA, roteiro do eSocial S-1.3 sem recibos fictícios, termos de VT/VR e dados pessoais fictícios (PR-18).', NULL),
    (191, 'Portaria MPS/MF nº 13/2026; Lei nº 15.270/2025; CCT SECEG × SINDILOJAS-GO (Termo Aditivo 2026/2027, aula de DP, p. 29); NBC TG 33', 'Construção da memória de cálculo com fórmulas, INSS e IRRF 2026, provisões e lotes L1 a L4.',
       'Valores do rascunho descartados como fonte; a folha vale pelo motor da plataforma, conferido por recálculo independente (doc. 13).'),
    (192, 'NBC TA 315/330 + Portal da Legislação (Planalto)', 'Estruturação dos papéis de trabalho e do registro de premissas.',
       'Na revisão de 27/11/2026, os achados passaram a ser do cliente (AUD-01 a AUD-08) e as premissas a ser 20, com quem decide, prazo e impacto.')
  ) AS v(id, fonte, prompt, rev)
  WHERE d.id = v.id AND d.empresa_id = 1 AND d.dossie = 'D2';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 5 THEN RAISE EXCEPTION 'Diário de IA: % (esperado 5)', n; END IF;

  INSERT INTO auditoria.diario_ia (chave, dossie, empresa_id, autor, entregavel, ferramenta, finalidade, prompt_resumo, fonte_oficial, revisao_humana, origem_registro, status_validacao)
  VALUES ('ia:d2:revisao-plataforma-2026-11', 'D2', 1, 'Grupo G07', 'Revisão do Dossiê 2 na plataforma (Docs. 01 a 15, produtos P1 a P9)',
    'Claude (Claude Code no VS Code)',
    'Conferir cada registro do Dossiê 2 contra o material original (Estudo de Caso 02, aula de DP, carta de onboarding, devolutiva e respostas do professor no grupo) e contra a legislação, registrar os achados e propor as correções.',
    'Revisar o que foi feito na versão anterior; avançar pelos documentos gerados e pelos produtos da régua; registrar cada achado novo; buscar a fonte oficial de cada norma citada.',
    'Estudo de Caso 02; aula de DP (pp. 21 a 29); LC nº 123/2006; Portaria Interministerial MPS/MF (salário-família); Resoluções CFC nº 1.590/2020 e nº 1.708/2023; Carta de Serviço do Governo de Goiás.',
    'A dupla validou cada proposta antes de executar e rodou os scripts de homologação; decidiu manter os dados fictícios, auditar o cliente e não a V1, lançar VT/VR em passivo, tratar a CCT como premissa didática, adotar porte EPP e pagamento em 06/10/2026 e corrigir a norma do CFC (achados no registro de revisão do Dossiê 2).',
    'usuario', 'pendente_revisao');

  -- 6. Pós-condições
  SELECT count(*) INTO n FROM erp.consulta_normativa WHERE empresa_id = 1 AND dossie = 'D2'
     AND (concat_ws(' ', enunciado, resposta_autoral, norma_citada, decisao_impactada) ~ '(SRT00189|PAT /|\(PAT|4\.238|4\.128|2\.416,30|2\.510,65|917,40|2\.247,20|1\.880,80|[Vv]1\b|3\.048/1999,? art\. 82)'
          OR impacto_se_alterada IS NULL OR responsavel_decisao IS NULL OR prazo_decisao IS NULL OR apontamento_auditoria IS NOT NULL);
  IF n <> 0 THEN RAISE EXCEPTION 'Premissas com legado ou campos vazios: %', n; END IF;
  SELECT count(*) INTO n FROM erp.consulta_normativa WHERE empresa_id = 1 AND dossie = 'D2'
     AND strpos(concat_ws(' ', resposta_autoral, norma_citada), '1.708') > 0 AND strpos(concat_ws(' ', resposta_autoral, norma_citada), '1.590') = 0;
  IF n <> 0 THEN RAISE EXCEPTION 'Premissas citando a 1.708/2023 sem a 1.590/2020: %', n; END IF;
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento IN ('d2_14_premissas', 'd2_15_ia')
     AND conteudo_md ~ '(Registro MTE|220 fórmulas|4 passagens|AUD-10|`PR-01` a `PR-18`|23/11/2026|24/11/2026|art\. 82|917,40|4\.238)';
  IF n <> 0 THEN RAISE EXCEPTION 'Seções dos Docs 14–15 com legado: %', n; END IF;
  SELECT count(*) INTO n FROM auditoria.diario_ia WHERE empresa_id = 1 AND dossie = 'D2'
     AND concat_ws(' ', fonte_oficial, prompt_resumo, revisao_humana) ~ '(SRT00189|confronto triplo|10 achados|18 premissas|47 itens)';
  IF n <> 0 THEN RAISE EXCEPTION 'Diário de IA com legado: %', n; END IF;

  -- 7. Homologação: 20 premissas, 9 seções e 8 registros do diário
  UPDATE erp.consulta_normativa SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Premissa conferida (27/11/2026): decisão e motivo, fonte oficial com link e data de acesso, quem decide, prazo e impacto (régua C-40 a C-43); números calculados ficam no motor (docs. 11 e 12).'
   WHERE empresa_id = 1 AND dossie = 'D2' AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 20 THEN RAISE EXCEPTION 'Premissas homologadas: % (esperado 20)', n; END IF;

  UPDATE erp.documento_secao SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Docs 14–15 revisados (27/11/2026, achados PRM-01 a PRM-11): tabelas de premissas e diário de IA gerados do banco; verificações em fonte oficial declaradas; decisões humanas registradas.'
   WHERE empresa_id = 1 AND documento IN ('d2_14_premissas', 'd2_15_ia') AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 9 THEN RAISE EXCEPTION 'Seções homologadas: % (esperado 9)', n; END IF;

  UPDATE auditoria.diario_ia SET status_validacao = 'homologado_contadora'
   WHERE empresa_id = 1 AND dossie = 'D2' AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 8 THEN RAISE EXCEPTION 'Diário de IA homologado: % (esperado 8)', n; END IF;
END
$a$;

SELECT 'premissas' AS item, count(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados, count(*) AS total FROM erp.consulta_normativa WHERE empresa_id = 1 AND dossie = 'D2'
UNION ALL SELECT 'seções Docs 14–15', count(*) FILTER (WHERE status_validacao = 'homologado_contadora'), count(*) FROM erp.documento_secao WHERE empresa_id = 1 AND documento IN ('d2_14_premissas', 'd2_15_ia')
UNION ALL SELECT 'diário de IA', count(*) FILTER (WHERE status_validacao = 'homologado_contadora'), count(*) FROM auditoria.diario_ia WHERE empresa_id = 1 AND dossie = 'D2';
