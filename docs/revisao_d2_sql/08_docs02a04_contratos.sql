-- Dossiê 2, etapa 2 (Estação 7 — contratos): Docs 02 (proposta), 03 (contrato + procuração) e 04 (termo de RT).
-- Achados CT-01 a CT-08 do registro docs/REVISAO_D2_ROTA_SUL.md.
-- PRÉ-REQUISITO: o código dos marcadores de honorários (branch feat/d2-marcadores-honorarios) precisa estar em produção;
-- sem ele os PDFs mostrariam {{VALOR_SETUP}} etc. literalmente.
-- Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int; v_end_d1 text; v_end_novo text;
  v_end_velho constant text := 'Asa Sul, 6º andar, sala 901, Brasília-DF, CEP `70.390-000`';
BEGIN
  -- 0. Estado esperado: 21 seções e 4 contratos pendentes
  SELECT count(*) INTO n FROM erp.documento_secao
   WHERE empresa_id = 1 AND documento IN ('d2_02_proposta','d2_03_contrato','d2_04_termo_rt') AND status_validacao = 'pendente_revisao';
  IF n <> 21 THEN RAISE EXCEPTION 'Seções dos Docs 02–04 fora do estado esperado (% de 21)', n; END IF;
  SELECT count(*) INTO n FROM erp.contrato_servico WHERE empresa_id = 1 AND status_validacao = 'pendente_revisao';
  IF n <> 4 THEN RAISE EXCEPTION 'Contratos fora do estado esperado (% de 4)', n; END IF;

  -- 1. Memória de horas: código por frente; remove "total" e "valor_hora" digitados (o valor sai de horas × valor_hora_centavos)
  UPDATE erp.contrato_servico cs SET memoria_horas_json = (
      SELECT jsonb_agg(jsonb_build_object('codigo', CASE
                 WHEN it->>'frente' LIKE 'Setup Fee%' THEN 'SETUP'
                 WHEN it->>'frente' LIKE 'Recuperação Passivo%' THEN 'RECUPERACAO'
                 WHEN it->>'frente' LIKE 'Mensal Matriz%' THEN 'MENSAL_MATRIZ'
                 WHEN it->>'frente' LIKE 'Mensal Filial%' THEN 'MENSAL_FILIAL'
                 WHEN it->>'frente' LIKE '13º Honorário%' THEN 'DECIMO_TERCEIRO' END,
               'frente', it->>'frente', 'horas', (it->>'horas')::int) ORDER BY ord)
        FROM jsonb_array_elements(cs.memoria_horas_json) WITH ORDINALITY AS e(it, ord)),
    atualizado_em = now()
   WHERE empresa_id = 1 AND codigo_documento IN ('proposta', 'contrato') AND jsonb_array_length(memoria_horas_json) = 5;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Memória de horas: % (esperado 2)', n; END IF;
  SELECT count(*) INTO n FROM erp.contrato_servico, jsonb_array_elements(memoria_horas_json) it
   WHERE empresa_id = 1 AND codigo_documento IN ('proposta', 'contrato') AND it->>'codigo' IS NOT NULL;
  IF n <> 10 THEN RAISE EXCEPTION 'Frentes com código: % (esperado 10)', n; END IF;

  -- 2. Premissas novas: PR-19 (CT-01, opção A) e PR-20 (CT-04)
  INSERT INTO erp.consulta_normativa (chave, empresa_id, numero_questao, enunciado, resposta_autoral, norma_citada, link_oficial,
         data_acesso, decisao_impactada, responsavel_decisao, prazo_decisao, impacto_se_alterada, origem_registro, status_validacao, dossie)
  VALUES
  ('cn:d2:PR-19', 1, 19,
   'PR-19 — Organização contábil em atividade em 14/09/2026 (premissa do caso × cronograma do Dossiê 1)',
   'O Estudo de Caso 02 (p. 1) define que, a partir de 14/09/2026, "cada dupla — na condição de sócios da organização contábil constituída no Dossiê 1 — assume o atendimento continuado da empresa-cliente", inclusive com as admissões de setembro. Prevalece a premissa do caso: a PRISMA JRNA atende a Rota Sul como organização constituída e registrada (CNPJ 48.123.456/0001-90; CRC-DF 004.821/O-2) desde 14/09/2026. O cronograma do Dossiê 1 (contrato social em 15/09/2026; CNPJ e enquadramento em 01/10/2026) é a projeção do plano de abertura e não se aplica ao Dossiê 2.',
   'Estudo de Caso 02, p. 1 (enunciado da disciplina)', 'acervo:arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf#p1', DATE '2026-11-27',
   'Docs 02, 03 e 04 (datas e qualificação da contratada)',
   'Sócias da PRISMA JRNA (Nathalia Peres Araujo e Jeovanna Ripardo Lustosa)', 'Decidido em 27/11/2026',
   'Se o cronograma do Dossiê 1 prevalecer, proposta, contrato, procuração e termo precisam ser redatados para depois de 01/10/2026, e as admissões de setembro ficam sem contrato de serviços.',
   'usuario', 'pendente_revisao', 'D2'),
  ('cn:d2:PR-20', 1, 20,
   'PR-20 — Valor da hora técnica na precificação da proposta',
   'A hora técnica de R$ 125,00 é premissa de precificação da dupla: não decorre do enunciado nem do plano de negócios do Dossiê 1, que adota ticket médio de R$ 1.500,00/mês para microempresas de serviços. Os honorários da Rota Sul são as horas estimadas por frente (implantação, recuperação do passivo, mensal da matriz, mensal da filial e 13º) multiplicadas pelo valor-hora, calculados pela plataforma (doc. 02, memória de custo).',
   'Premissa da dupla; Resolução CFC nº 1.708/2023 (contrato escrito com honorários definidos)', 'https://cfc.org.br/', DATE '2026-11-27',
   'Docs 02, 03 e 04 (honorários)',
   'Sócias da PRISMA JRNA (Nathalia Peres Araujo e Jeovanna Ripardo Lustosa)', 'Decidido em 14/09/2026 (proposta)',
   'Se o valor-hora mudar, todos os honorários (implantação, recuperação, mensais e 13º) mudam na mesma proporção; os documentos acompanham pelos marcadores.',
   'usuario', 'pendente_revisao', 'D2');

  -- 3. Endereço completo da contratada (D1, erp.estabelecimento) — CT-03
  SELECT endereco INTO v_end_d1 FROM erp.estabelecimento WHERE empresa_id = 6 AND tipo = 'matriz';
  IF v_end_d1 IS NULL OR strpos(v_end_d1, ', CEP 70.390-000') = 0 THEN RAISE EXCEPTION 'Endereço do D1 inesperado: %', v_end_d1; END IF;
  v_end_novo := replace(v_end_d1, ', CEP 70.390-000', ', Brasília-DF, CEP `70.390-000`');
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND strpos(conteudo_md, v_end_velho) > 0
     AND documento IN ('d2_02_proposta','d2_03_contrato','d2_04_termo_rt');
  IF n <> 4 THEN RAISE EXCEPTION 'Endereço abreviado: % seções (esperado 4)', n; END IF;
  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, v_end_velho, v_end_novo)
   WHERE empresa_id = 1 AND documento IN ('d2_02_proposta','d2_03_contrato','d2_04_termo_rt') AND strpos(conteudo_md, v_end_velho) > 0;

  -- 4. "Sócontas Ltda." -> "Sócontas" em todo o D2 (CT-02; a devolutiva diz "Sócontas/Dr. Osvaldo")
  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, 'Sócontas Ltda.', 'Sócontas')
   WHERE empresa_id = 1 AND dossie = 'D2' AND strpos(conteudo_md, 'Sócontas Ltda.') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n < 3 THEN RAISE EXCEPTION 'Sócontas Ltda.: % seções (esperado ≥ 3)', n; END IF;

  -- 5. Doc 02 — cabeçalho (CT-07), cenário (CT-08), memória de custo (CT-04/CT-05) e condições (13º)
  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, ' *(Revisão Final: 23/11/2026)*', '')
   WHERE empresa_id = 1 AND documento = 'd2_02_proposta' AND codigo_secao = 'cabecalho' AND strpos(conteudo_md, '(Revisão Final: 23/11/2026)') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'CT-07: %', n; END IF;

  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md,
      'conforme relato verbal dos sócios a confirmar documentalmente (doc. 05, `PEND-03`)',
      'conforme as respostas do cliente dadas pelo professor no grupo da disciplina (doc. 05, `PEND-03`)')
   WHERE empresa_id = 1 AND documento = 'd2_02_proposta' AND codigo_secao = '1_cenario_atual_e_solucao_prisma'
     AND strpos(conteudo_md, 'conforme relato verbal dos sócios a confirmar documentalmente') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'CT-08: %', n; END IF;

  UPDATE erp.documento_secao SET conteudo_md = $t$Embora o *Plano de Negócios* da PRISMA JRNA (Dossiê 1, cenário oficial) adote ticket médio de **R$ 1.500,00/mês** para microempresas de serviços no DF, o escopo da Rota Sul envolve **dois estabelecimentos em UFs distintas (Matriz GO + Filial SC)**, **importação própria** (desembaraço aduaneiro, ICMS-ST/DIFAL) e **estruturação completa do Departamento Pessoal**. Por isso, a precificação parte das horas técnicas estimadas por frente, a **{{VALOR_HORA}}/h** (premissa de precificação da dupla — PR-20). A tabela de memória de custo abaixo é calculada pela plataforma (horas × valor-hora):

- **Taxa de implantação (*setup fee*):** {{HORAS_SETUP}} horas (diagnóstico do Anexo I, parametrização do eSocial e do FGTS Digital, onboarding e pauta da 3ª Alteração) — **{{VALOR_SETUP}}**, em parcela única na assinatura;
- **Recuperação do passivo (março a agosto/2026):** {{HORAS_RECUPERACAO}} horas (6 competências) — **{{VALOR_RECUPERACAO}}**, em pacote fechado, à vista ou em até 3 parcelas mensais iguais;
- **Honorários mensais:** Matriz (GO) + DP, {{HORAS_MENSAL_MATRIZ}} h/mês — **{{VALOR_MENSAL_MATRIZ}}**; Filial (SC), {{HORAS_MENSAL_FILIAL}} h/mês — **{{VALOR_MENSAL_FILIAL}}**; total de {{HORAS_MES}} h/mês — **{{HONORARIO_MENSAL}}**, com vencimento no dia 10 do mês subsequente;
- **13º honorário (dezembro):** {{HORAS_DECIMO_TERCEIRO}} horas (encerramento anual, Balanço/DRE, folha natalina e DEFIS) — **{{DECIMO_TERCEIRO}}**.

> **Nota sobre regularização societária:** o diagnóstico contábil e as diretrizes para a 3ª Alteração Contratual integram a taxa de implantação; taxas da JUCEG/JUCESC e honorários advocatícios são custeados diretamente pela contratante.$t$
   WHERE empresa_id = 1 AND documento = 'd2_02_proposta' AND codigo_secao = '3_memoria_de_custo_e_investiment'
     AND strpos(conteudo_md, 'aderente ao modelo financeiro de margem de contribuição do Dossiê 1') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'CT-04/05: %', n; END IF;

  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, '(inclusive o **13º honorário de R$ 4.000,00**)', '(inclusive o **13º honorário de {{DECIMO_TERCEIRO}}**)')
   WHERE empresa_id = 1 AND documento = 'd2_02_proposta' AND codigo_secao = '4_condicoes_comerciais_gerais'
     AND strpos(conteudo_md, '(inclusive o **13º honorário de R$ 4.000,00**)') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Proposta 13º: %', n; END IF;

  -- 6. Doc 03 — Cláusula 2ª com marcadores (valores saem do contrato)
  UPDATE erp.documento_secao SET conteudo_md =
      replace(replace(replace(replace(replace(conteudo_md,
        '**R$ 2.000,00** (dois mil reais)', '**{{VALOR_SETUP}}**'),
        '**R$ 12.000,00** (doze mil reais)', '**{{VALOR_RECUPERACAO}}**'),
        '(à vista ou em até 3 parcelas mensais de R$ 4.000,00)', '(à vista ou em até 3 parcelas mensais iguais)'),
        '**R$ 4.000,00** (quatro mil reais) mensais — sendo R$ 2.500,00 alocados à Matriz (GO) e DP, e R$ 1.500,00 à',
        '**{{HONORARIO_MENSAL}}** mensais — sendo {{VALOR_MENSAL_MATRIZ}} alocados à Matriz (GO) e DP, e {{VALOR_MENSAL_FILIAL}} à'),
        '(**R$ 4.000,00**)', '(**{{DECIMO_TERCEIRO}}**)')
   WHERE empresa_id = 1 AND documento = 'd2_03_contrato' AND codigo_secao = 'clausula_2_dos_honorarios_forma_';
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_03_contrato'
     AND codigo_secao = 'clausula_2_dos_honorarios_forma_' AND conteudo_md !~ 'R\$ ?[0-9]' AND strpos(conteudo_md, '{{VALOR_SETUP}}') > 0;
  IF n <> 1 THEN RAISE EXCEPTION 'Cláusula 2ª ainda com valor digitado'; END IF;

  -- 7. Doc 04 — item 5 do rol de pendências (CT-06)
  UPDATE erp.documento_secao SET conteudo_md = replace(replace(conteudo_md,
      'pela presença do CNAE `4541-2/01` (motocicletas) sob cláusula de importação no objeto social (LC 123/2006, art. 17, VIII — veda a importação de automóveis e motocicletas; impacto estimado de `+R$ 917,40/mês` na folha, doc. 12)',
      'pela presença dos CNAEs `4541-2/01` e `4541-2/03` (motocicletas) e `4511-1/02` (automóveis) sob o título "Importação e Exportação" do objeto social (LC 123/2006, art. 17, VIII — veda a importação de automóveis e motocicletas; ver PR-02 e a sensibilidade PR-17, calculada pela plataforma no doc. 12)'),
      'Depurar os 18 CNAEs na 3ª Alteração (excluindo `4541-2/01`)',
      'Depurar os 18 CNAEs na 3ª Alteração (excluindo `4541-2/01`, `4541-2/03` e `4511-1/02` — PR-02)')
   WHERE empresa_id = 1 AND documento = 'd2_04_termo_rt' AND codigo_secao = '5_rol_de_pendencias_e_riscos_ide';
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_04_termo_rt'
     AND codigo_secao = '5_rol_de_pendencias_e_riscos_ide' AND strpos(conteudo_md, '917,40') = 0 AND strpos(conteudo_md, '— PR-02)') > 0;
  IF n <> 1 THEN RAISE EXCEPTION 'CT-06 não aplicado'; END IF;

  -- 8. Pós-condições nos Docs 02–04
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento IN ('d2_02_proposta','d2_03_contrato','d2_04_termo_rt')
     AND (strpos(conteudo_md, 'Sócontas Ltda') > 0 OR strpos(conteudo_md, '917,40') > 0 OR strpos(conteudo_md, v_end_velho) > 0
          OR strpos(conteudo_md, 'Revisão Final') > 0 OR strpos(conteudo_md, 'aderente ao modelo financeiro') > 0);
  IF n <> 0 THEN RAISE EXCEPTION 'Restaram % seções com legado', n; END IF;

  -- 9. Homologação: 21 seções e 4 contratos
  UPDATE erp.documento_secao SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = CASE documento
      WHEN 'd2_02_proposta' THEN 'Proposta revisada (27/11/2026): contratada com dados completos do Dossiê 1, valores por marcadores vivos (horas × valor-hora, PR-20), omissão de mar–ago/2026 citada como resposta do professor no grupo da disciplina e datas conforme a premissa do caso (PR-19).'
      WHEN 'd2_03_contrato' THEN 'Contrato e minuta de procuração revisados (27/11/2026): partes qualificadas com dados completos, honorários da Cláusula 2ª por marcadores vivos iguais à proposta e ao termo, responsabilidades, LGPD, procuração com poderes e vedações, foro e assinatura conjunta (alçada do Contrato Social do D1, Cl. 9ª). Datas conforme PR-19.'
      ELSE 'Termo de RT revisado (27/11/2026): Res. CFC nº 1.708/2023, RT exclusiva de Nathalia Peres Araujo (Contrato Social do D1, Cl. 11ª), marco temporal a partir de 01/09/2026 e rol de 7 pendências do onboarding alinhado às PR-02 e PR-17 (sem valores digitados). Datas conforme PR-19.'
    END
   WHERE empresa_id = 1 AND documento IN ('d2_02_proposta','d2_03_contrato','d2_04_termo_rt') AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 21 THEN RAISE EXCEPTION 'Seções homologadas: % (esperado 21)', n; END IF;

  UPDATE erp.contrato_servico SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Conferido (27/11/2026): honorário mensal, 13º e valor-hora iguais na proposta, no contrato e no termo; vigência de contrato e termo em 01/09/2026; memória de horas com código por frente (valores calculados pela plataforma); premissas PR-19 e PR-20.'
   WHERE empresa_id = 1 AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Contratos homologados: % (esperado 4)', n; END IF;
END
$a$;

SELECT documento, count(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologadas, count(*) AS total
  FROM erp.documento_secao WHERE empresa_id = 1 AND documento IN ('d2_02_proposta','d2_03_contrato','d2_04_termo_rt') GROUP BY 1 ORDER BY 1;
