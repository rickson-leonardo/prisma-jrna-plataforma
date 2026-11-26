-- Dossiê 2, Estação 1 (Cadastro): correções C-01 a C-05 do registro docs/REVISAO_D2_ROTA_SUL.md.
-- Fonte: Estudo de Caso 02 / Anexo I no acervo (arquivo 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf').
-- Cada dado é conferido no texto do acervo antes de gravar. Status 'acervo_referencia' e origem 'acervo_sigaa'
-- (dado do caso oficial) são mantidos. Tudo ou nada.
DO $a$
DECLARE n int; v_arq bigint; v_cnaes text[];
BEGIN
  SELECT id INTO v_arq FROM acervo.bru_arquivo WHERE chave = 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf';

  -- Conferência das fontes (Anexo I e certidão de registro)
  SELECT count(*) INTO n FROM acervo.bru_linha WHERE arquivo_id = v_arq AND (
       (pagina = 7 AND n_linha = 16 AND strpos(texto, 'Carteira de Identidade nº 1.111.111') > 0 AND strpos(texto, 'DGPC-GO') > 0)
    OR (pagina = 7 AND n_linha = 17 AND texto LIKE '111.444.777-35%')
    OR (pagina = 7 AND n_linha = 21 AND strpos(texto, 'Identidade nº 2.222.222') > 0 AND strpos(texto, 'PC-GO') > 0)
    OR (pagina = 8 AND n_linha IN (14, 17) AND texto = '750.000')
    OR (pagina = 13 AND strpos(texto, 'COM EFEITOS DO REGISTRO EM: 22/07/2025') > 0)
    OR (strpos(texto, 'iniciou suas atividades em 28 de Outubro de 2024') > 0));
  IF n <> 7 THEN RAISE EXCEPTION 'Fontes do acervo não conferem (% de 7 linhas)', n; END IF;

  -- C-01 e C-02: CPF da Helena e RG dos dois sócios (dados fictícios do caso)
  INSERT INTO erp.pessoa_identificador (chave, pessoa_id, tipo_id, valor, eh_ficticio, fonte_chave, origem_registro, status_validacao)
  VALUES
    ('pid:pes:pf:helena_aparecida_mendes_duarte:CPF:11144477735', 7, 'CPF', '111.444.777-35', true,
     'lin:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf:7:17', 'acervo_sigaa', 'acervo_referencia'),
    ('pid:pes:pf:helena_aparecida_mendes_duarte:OUTRO:rg1111111', 7, 'OUTRO', 'RG 1.111.111 DGPC-GO (2ª via, 29/12/2003)', true,
     'lin:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf:7:16', 'acervo_sigaa', 'acervo_referencia'),
    ('pid:pes:pf:bruno_mendes_duarte:OUTRO:rg2222222', 8, 'OUTRO', 'RG 2.222.222 PC-GO (2ª via, 05/01/2016)', true,
     'lin:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf:7:21', 'acervo_sigaa', 'acervo_referencia');
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'Identificadores: % (esperado 3)', n; END IF;

  -- C-03: os 18 CNAEs lidos diretamente do Anexo I (Cláusula Segunda consolidada, p. 9)
  SELECT array_agg(m[1] ORDER BY n_linha) INTO v_cnaes
    FROM acervo.bru_linha, regexp_match(texto, '^(\d{4}-\d/\d{2}) ') AS m
   WHERE arquivo_id = v_arq AND pagina = 9 AND n_linha BETWEEN 7 AND 25 AND m IS NOT NULL;
  IF coalesce(array_length(v_cnaes, 1), 0) <> 18 OR NOT ('4530-7/02' = ANY (v_cnaes)) THEN
    RAISE EXCEPTION 'CNAEs do Anexo I: % (esperado 18)', coalesce(array_length(v_cnaes, 1), 0); END IF;
  UPDATE erp.enquadramento_historico SET cnaes_secundarios = to_jsonb(array_remove(v_cnaes, '4530-7/02')), atualizado_em = now()
   WHERE chave = 'enq:rota_sul_d2:2026' AND cnae_principal = '4530-7/02';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Enquadramento: % (esperado 1)', n; END IF;

  -- C-04 e C-05: percentual no padrão do D1 (500.000 = 50%) e vigência pela data de efeito da 2ª alteração
  UPDATE erp.participacao_societaria SET percentual_micro = 500000, vigente_de = DATE '2025-07-22', atualizado_em = now()
   WHERE empresa_id = 1 AND chave IN ('part:d2:helena', 'part:d2:bruno') AND quotas = 750000 AND percentual_micro = 50000000;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Sócios: % (esperado 2)', n; END IF;

  UPDATE erp.fato SET vigente_de = DATE '2025-07-22', atualizado_em = now()
   WHERE chave IN ('fato:d2:rs:capital_depois', 'fato:d2:rs:capital_integralizado') AND vigente_de = DATE '2026-09-14';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Capital atual: % (esperado 2)', n; END IF;

  UPDATE erp.fato SET vigente_de = DATE '2024-10-28', vigente_ate = DATE '2025-07-21', atualizado_em = now()
   WHERE chave = 'fato:d2:rs:capital_antes' AND vigente_de = DATE '2024-01-01';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Capital anterior: % (esperado 1)', n; END IF;

  -- C-06: a PRISMA JRNA não é responsável técnica desde 2024. EC02 p. 1: em 14/09/2026 os sócios,
  -- "insatisfeitos com o escritório anterior", procuram a organização contábil da dupla; termo de RT a partir de 01/09/2026.
  SELECT count(*) INTO n FROM acervo.bru_linha WHERE arquivo_id = v_arq AND pagina = 1 AND n_linha = 47
     AND strpos(texto, 'insatisfeitos com o escritório anterior') > 0;
  IF n <> 1 THEN RAISE EXCEPTION 'Fonte do escritório anterior não confere'; END IF;
  IF NOT EXISTS (SELECT 1 FROM erp.contrato_servico WHERE chave = 'cs:d2:termo_rt' AND vigencia_inicio = DATE '2026-09-01') THEN
    RAISE EXCEPTION 'Termo de RT com vigência 01/09/2026 não encontrado'; END IF;
  -- período da PRISMA (registro novo, para ficar como o mais recente)
  INSERT INTO erp.enquadramento_historico (chave, empresa_id, vigente_de, vigente_ate, porte, regime_tributario, cnae_principal,
         cnaes_secundarios, registro_crc, responsavel_tecnico_pessoa_id, fonte_chave, origem_registro, status_validacao, apontamento_auditoria)
  SELECT 'enq:rota_sul_d2:2026-09', empresa_id, DATE '2026-09-01', NULL, porte, regime_tributario, cnae_principal,
         cnaes_secundarios, registro_crc, responsavel_tecnico_pessoa_id, 'cs:d2:termo_rt', 'usuario', status_validacao, apontamento_auditoria
    FROM erp.enquadramento_historico WHERE chave = 'enq:rota_sul_d2:2026' AND responsavel_tecnico_pessoa_id IS NOT NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Enquadramento PRISMA: % (esperado 1)', n; END IF;
  -- período anterior: escritório não identificado no caso
  UPDATE erp.enquadramento_historico SET vigente_ate = DATE '2026-08-31', responsavel_tecnico_pessoa_id = NULL, registro_crc = NULL,
         apontamento_auditoria = 'Período anterior à PRISMA JRNA: o caso informa apenas "escritório anterior", sem identificá-lo (Estudo de Caso 02, p. 1). ' || coalesce(apontamento_auditoria, ''),
         atualizado_em = now()
   WHERE chave = 'enq:rota_sul_d2:2026' AND vigente_ate IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Enquadramento anterior: % (esperado 1)', n; END IF;

  -- C-07: porte ME e CNAE principal registrados como premissas na PR-01
  UPDATE erp.consulta_normativa SET
    enunciado = 'PR-01 — Enquadramento tributário (Simples Nacional), porte e CNAE principal',
    resposta_autoral = 'Tratar a Rota Sul como optante pelo Simples Nacional desde a abertura, em outubro de 2024, conforme a resposta dos sócios à carta de onboarding: Anexo I (comércio), CPP dentro do DAS e classificação tributária 01 no eSocial. Premissas de cadastro, porque o caso não informa faturamento nem CNAE principal: (i) porte ME; (ii) CNAE principal 4530-7/02, o primeiro da atividade-foco indicada no Estudo de Caso 02 (p. 2). Ambas serão confirmadas com o faturamento e o cartão CNPJ (DOC-08).',
    responsavel_decisao = 'RT da PRISMA JRNA (Nathalia Peres Araujo), com confirmação documental do cliente',
    prazo_decisao = '30/09/2026 (DOC-08: balanço, DRE e balancetes)',
    impacto_se_alterada = 'Se a receita bruta superar o limite da ME, o porte passa a EPP no ano-calendário seguinte (LC 123/2006, art. 3º); o Simples continua cabível até o limite da EPP. Se o CNAE principal for outro, revisar o cadastro, o anexo do Simples e o enquadramento sindical (CCT).'
  WHERE empresa_id = 1 AND dossie = 'D2' AND numero_questao = 1 AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'PR-01: % (esperado 1)', n; END IF;

  -- C-08: endereço da filial exatamente como na ficha do caso (EC02 p. 2); a divergência "Sala 223 A 32" fica no achado R-06
  UPDATE erp.estabelecimento SET endereco = (SELECT texto FROM acervo.bru_linha WHERE arquivo_id = v_arq AND pagina = 2 AND n_linha = 23),
         atualizado_em = now()
   WHERE chave = 'est:rota_sul_d2:filial_itajai'
     AND (SELECT texto FROM acervo.bru_linha WHERE arquivo_id = v_arq AND pagina = 2 AND n_linha = 23) = 'BR-101, nº 15.000, Sala 223, Bairro Canhanduba, Itajaí-SC, CEP 88.313-000';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Endereço da filial: % (esperado 1)', n; END IF;
END
$a$;

SELECT 'enq ' || chave AS item, cnae_principal || ' + ' || jsonb_array_length(cnaes_secundarios) || ' secundários; ' || vigente_de || ' a ' || coalesce(vigente_ate::text, 'atual') || '; RT ' || coalesce(responsavel_tecnico_pessoa_id::text, '—') AS valor
  FROM erp.enquadramento_historico WHERE empresa_id = 1
UNION ALL SELECT 'socio ' || chave, percentual_micro || ' desde ' || vigente_de FROM erp.participacao_societaria WHERE empresa_id = 1
UNION ALL SELECT 'fato ' || chave, vigente_de || ' a ' || coalesce(vigente_ate::text, 'atual') FROM erp.fato WHERE sujeito_chave = 'emp:rota_sul_d2' AND atributo LIKE 'capital%'
UNION ALL SELECT 'id ' || tipo_id, valor FROM erp.pessoa_identificador WHERE pessoa_id IN (7, 8);
