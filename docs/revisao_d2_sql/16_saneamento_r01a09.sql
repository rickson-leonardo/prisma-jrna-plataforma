-- Dossiê 2, tela "Saneamento (3ª Alteração)": diretrizes R-01 a R-09 (erp.processo_legalizacao_etapa), nunca revisadas.
-- Coerência com o Doc 01 (plano de saneamento, homologado) e com as respostas do grupo (G-01, G-02, G-03, G-06, G-09) e a PRM-06.
-- Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM erp.processo_legalizacao_etapa WHERE chave LIKE 'leg:d2:R-0_' AND status_validacao = 'pendente_revisao';
  IF n <> 9 THEN RAISE EXCEPTION 'Diretrizes fora do estado esperado (% de 9)', n; END IF;

  UPDATE erp.processo_legalizacao_etapa e SET
      nome_etapa = coalesce(v.nome, e.nome_etapa), orgao = coalesce(v.orgao, e.orgao),
      entrada_docs = coalesce(v.entrada, e.entrada_docs), saida_doc = coalesce(v.saida, e.saida_doc),
      regra_retorno_exigencia = coalesce(v.regra, e.regra_retorno_exigencia), atualizado_em = now()
  FROM (VALUES
    ('R-01', NULL, NULL,
       'Anexo I + relatório de operações reais da filial de Itajaí-SC (resposta do cliente no grupo, G-02: finalidade real da filial é só a importação de pneus)',
       'Minuta de objeto social focado em pneumáticos e câmaras de ar; objeto da filial restrito à importação de pneus (o Simples Nacional não proíbe filial)', NULL),
    ('R-02', 'Saneamento da mora de integralização do capital (R$ 500.000,00) e correção da errata de data (31/07/2025 → 31/07/2026)', NULL,
       'Carta de onboarding (respostas Q1 e Q5) e resposta do cliente no grupo (G-01: data correta 31/07/2026; os R$ 500.000,00 não foram integralizados) + extratos bancários', NULL, NULL),
    ('R-05', 'Substituição de AGO/Tesouraria (S.A.) e definição da regência supletiva (Cl. 18ª) por orientação da PRISMA JRNA', NULL,
       'Cl. 5ª IV e Cl. 18ª do Anexo I; resposta do cliente no grupo (G-03: "dependemos do que vocês vão nos orientar")', NULL, NULL),
    ('R-07', NULL, 'RFB (PGDAS-D) + contador anterior (Res. CFC nº 1.590/2020, arts. 6º a 8º — distrato e comunicação)',
       'Extratos OFX (DOC-08) + termo de transferência (DOC-07) + base do sistema Domínio usado pela Sócontas (resposta do cliente no grupo, G-06)', NULL, NULL),
    ('R-09', 'Definição formal de pró-labore dos sócios e da distribuição de lucros (sem JCP no Simples)', 'PRISMA JRNA / sócios (Lei nº 8.212/1991, art. 12, V, "f"; Lei nº 4.357/1964, art. 32)',
       'PEND-08 + Cl. 13ª § 1º e Cl. 16ª; resposta do cliente no grupo (G-09: retirada verbal de "80% do lucro líquido do mês", sem valor fixado)',
       'Ata de definição do pró-labore (S-2300 e rubrica no S-1200) e política de distribuição de lucros com base em escrituração',
       'Sem pró-labore definido, não distribuir lucros sem escrituração e enquanto houver débitos fiscais em aberto (Lei nº 4.357/1964, art. 32).')
  ) AS v(cod, nome, orgao, entrada, saida, regra)
  WHERE e.chave = 'leg:d2:' || v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 5 THEN RAISE EXCEPTION 'Diretrizes corrigidas: % (esperado 5)', n; END IF;

  SELECT count(*) INTO n FROM erp.processo_legalizacao_etapa WHERE chave LIKE 'leg:d2:R-0_'
     AND concat_ws(' ', nome_etapa, orgao, entrada_docs, saida_doc, regra_retorno_exigencia) ~ '(1\.708|conflito 2025|COSIT 120)';
  IF n <> 0 THEN RAISE EXCEPTION 'Diretrizes com legado: %', n; END IF;

  UPDATE erp.processo_legalizacao_etapa SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Diretriz conferida (27/11/2026) com o plano de saneamento do Doc 01 (homologado), as respostas do cliente (carta de onboarding e grupo da disciplina) e a legislação citada.'
   WHERE chave LIKE 'leg:d2:R-0_' AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 9 THEN RAISE EXCEPTION 'Diretrizes homologadas: % (esperado 9)', n; END IF;
END
$a$;

SELECT codigo, nome_etapa, status_validacao FROM erp.processo_legalizacao_etapa WHERE chave LIKE 'leg:d2:R-0_' ORDER BY codigo;
