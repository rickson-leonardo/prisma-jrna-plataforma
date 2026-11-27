-- Dossiê 2, etapa 2 (Estação 7 — onboarding): Doc 05 e os 30 itens de diligência. Achados OB-01 a OB-13.
-- Fontes: carta de onboarding (acervo: D2/Solicitacao_JRNA.pdf, pp. 2–3), Estudo de Caso 02 (EC02), aula de DP (AULA),
-- devolutiva oficial do D2 (DEV G07, p. 3) e normas citadas. Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
  c_resp_prof constant text := 'Respostas do cliente dadas pelo professor no grupo da disciplina, registradas na carta de onboarding (acervo: Solicitação_JRNA.pdf, p. 3)';
  c_dev constant text := 'Resposta do cliente dada pelo professor no grupo da disciplina, citada na devolutiva oficial do Dossiê 2 (p. 3)';
BEGIN
  -- 0. Estado esperado
  SELECT count(*) INTO n FROM erp.diligencia_item WHERE empresa_id = 1 AND status_validacao = 'pendente_revisao';
  IF n <> 30 THEN RAISE EXCEPTION 'Diligência fora do estado esperado (% de 30)', n; END IF;
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_05_onboarding' AND status_validacao = 'pendente_revisao';
  IF n <> 4 THEN RAISE EXCEPTION 'Seções do Doc 05 fora do estado esperado (% de 4)', n; END IF;
  SELECT count(*) INTO n FROM acervo.bru_linha l JOIN acervo.bru_arquivo a ON a.id = l.arquivo_id
   WHERE (a.chave = 'arq:D2/Solicitacao_JRNA.pdf' AND l.pagina = 2 AND l.texto LIKE 'Checklist de Documentos Iniciais%')
      OR (a.chave = 'arq:D2/Aulas_DP_Admissao_Folha_Fechamento_2026_Atualizado_IRRF_.pdf' AND l.pagina = 25 AND l.texto LIKE 'Premissa didática: vendas líquidas de R$ 60.000%');
  IF n <> 2 THEN RAISE EXCEPTION 'Fontes do acervo não conferem (% de 2)', n; END IF;

  -- 1. Documentos (OB-05, OB-06, OB-12, OB-13): responsável por pessoa, origem real e textos atualizados
  UPDATE erp.diligencia_item d SET responsavel = v.resp, fonte_evidencia = v.fonte,
         resposta_literal = coalesce(v.texto, d.resposta_literal), atualizado_em = now()
  FROM (VALUES
    ('DOC-01', 'Sócios (Helena e Bruno) / advogado', 'Carta de onboarding (14/09/2026), checklist item 1 (acervo, p. 2)', NULL),
    ('DOC-02', 'Sócios (Helena e Bruno) / advogado', 'Anexo I entregue pelos sócios (EC02, p. 1: "Os sócios entregam apenas o ANEXO I")', NULL),
    ('DOC-03', 'Sócios (Helena e Bruno)', 'Carta de onboarding, checklist item 6 (acervo, p. 2)', NULL),
    ('DOC-04', 'Sócios (diretoria)', 'Carta de onboarding, checklist item 1 — certificações (acervo, p. 2)', NULL),
    ('DOC-05', 'Sócios (diretoria)', 'Carta de onboarding, checklist item 2 (acervo, p. 2)', NULL),
    ('DOC-06', 'Sócios / despachante em Itajaí', 'Resposta Q3 (carta de onboarding, acervo, p. 3)', NULL),
    ('DOC-07', 'Contador anterior (Sócontas / Dr. Osvaldo)', 'Carta de onboarding, checklist item 4 (acervo, p. 2); DEV G07, p. 3', NULL),
    ('DOC-08', 'Contador anterior + sócios', 'Carta de onboarding, checklist itens 3 e 5 (acervo, p. 2)', NULL),
    ('DOC-09', 'Empregados E1 e E2', 'EC02, p. 3 (executar a admissão: documentos e exame admissional)', NULL),
    ('DOC-10', 'Diretoria Rota Sul + clínica SST', 'EC02, p. 3 (exame admissional); NR-7', NULL),
    ('DOC-11', 'Diretoria Rota Sul + clínica SST', 'NR-1, NR-4 e NR-7; eSocial S-2240', NULL),
    ('DOC-12', 'Empregados E1 e E2', 'EC02, p. 3 (vale-transporte e vale-refeição); AULA, p. 24; PR-08',
       'Lastrear o desconto de VT (6%; 2 viagens/dia — PR-08), o VR/PAT e a apuração da jornada.'),
    ('DOC-13', 'Diretoria comercial Rota Sul', 'AULA, p. 25 (premissa didática de vendas líquidas)',
       'Validar a premissa didática de vendas líquidas de R$ 60.000,00 no período (aula de DP, p. 25), base da comissão e do DSR (doc. 11).')
  ) AS v(codigo, resp, fonte, texto)
  WHERE d.empresa_id = 1 AND d.codigo = v.codigo AND d.tipo = 'documento';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 13 THEN RAISE EXCEPTION 'Documentos: % (esperado 13)', n; END IF;

  -- 2. Perguntas (OB-03, OB-04, OB-07, OB-11, OB-13)
  UPDATE erp.diligencia_item d SET fonte_evidencia = v.fonte, prazo_texto = v.prazo,
         resposta_literal = coalesce(v.texto, d.resposta_literal), atualizado_em = now()
  FROM (VALUES
    ('Q1', c_resp_prof, 'Respondida', NULL),
    ('Q2', c_resp_prof, 'Respondida', NULL),
    ('Q3', c_resp_prof, 'Respondida', NULL),
    ('Q4', c_resp_prof, 'Respondida', NULL),
    ('Q5', c_resp_prof, 'Respondida', NULL),
    ('Q6', 'EC02, pp. 2–3 (informações verbais dos sócios)', 'Respondida', NULL),
    ('Q7', c_dev, '02/10/2026 (PEND-01)',
       'ASO admissional não realizado antes do início das atividades de E1 e E2; tratado na PEND-01, sem atestar exame inexistente.'),
    ('Q8', c_dev, '30/10/2026 (PEND-03)',
       'Escrituração e PGDAS-D paralisados de março a agosto/2026 sob o contador anterior (Sócontas / Dr. Osvaldo), sem distrato nem termo de transferência; tratado na PEND-03.'),
    ('Q9', 'Resposta não localizada nos registros da dupla (busca no acervo e nos arquivos da tentativa anterior em 27/11/2026)', '20/10/2026 (PEND-02)',
       'Resposta do advogado não localizada nos registros da dupla; as providências societárias seguem na PEND-02.')
  ) AS v(codigo, fonte, prazo, texto)
  WHERE d.empresa_id = 1 AND d.codigo = v.codigo AND d.tipo = 'pergunta';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 9 THEN RAISE EXCEPTION 'Perguntas: % (esperado 9)', n; END IF;

  -- 3. Pendências (OB-06, OB-08, OB-13): responsável legível e origem real
  UPDATE erp.diligencia_item d SET responsavel = v.resp, fonte_evidencia = v.fonte,
         enunciado = coalesce(v.enun, d.enunciado), atualizado_em = now()
  FROM (VALUES
    ('PEND-01', 'Diretoria Rota Sul + clínica SST', 'Q7 (DEV G07, p. 3); NR-7; eSocial S-2220', NULL),
    ('PEND-02', 'Sócios + advogado societário (apoio PRISMA JRNA)', 'Achados do Anexo I (doc. 01, Estação 2); PR-02',
       '3ª Alteração Contratual (CNAEs 4541-2/01, 4541-2/03 e 4511-1/02; R$ 500 mil; datas; 3 critérios de haveres; 50/50; AGO; Sala 223)'),
    ('PEND-03', 'PRISMA JRNA + sócios + contador anterior', 'Q8 (DEV G07, p. 3); Res. CFC nº 1.708/2023', NULL),
    ('PEND-04', 'Empregados E1/E2 + diretoria + DP PRISMA JRNA', 'Q4 (carta, p. 3); PR-08 e PR-11', NULL),
    ('PEND-05', 'Diretoria comercial Rota Sul', 'AULA, p. 25 (premissa didática); DOC-13', NULL),
    ('PEND-06', 'Sócios + despachante em Itajaí + PRISMA JRNA', 'Q3 (carta, p. 3); minuta de procuração (doc. 03)', NULL),
    ('PEND-07', 'Diretoria Rota Sul + clínica SST', 'NR-1 e NR-4; eSocial S-2240', NULL),
    ('PEND-08', 'Sócios administradores + PRISMA JRNA', 'Anexo I, Cl. 16ª (pró-labore facultativo, EC02); DOC-03', NULL)
  ) AS v(codigo, resp, fonte, enun)
  WHERE d.empresa_id = 1 AND d.codigo = v.codigo AND d.tipo = 'pendencia';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 8 THEN RAISE EXCEPTION 'Pendências: % (esperado 8)', n; END IF;

  -- 4. Seções do Doc 05 (OB-01, OB-02, OB-09, OB-10): texto curto; os quadros saem do banco
  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, ' | **Atualização:** 23/11/2026', '')
   WHERE empresa_id = 1 AND documento = 'd2_05_onboarding' AND codigo_secao = 'cabecalho' AND strpos(conteudo_md, '**Atualização:** 23/11/2026') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Cabeçalho: %', n; END IF;

  UPDATE erp.documento_secao s SET conteudo_md = v.txt
  FROM (VALUES
    ('1_checklist_de_documentos_organi', $t$Os documentos solicitados ao cliente, ao contador anterior e aos empregados estão no quadro **Checklist de documentos** abaixo, gerado pela plataforma a partir do registro de diligência, com responsável, prazo, origem e status real de cada documento. A lista parte da carta de onboarding de 14/09/2026 (checklist de documentos iniciais) e das tarefas de admissão do Estudo de Caso 02 (p. 3).$t$),
    ('2_perguntas_formuladas_e_registr', $t$As perguntas da carta de onboarding (14/09/2026) e as respostas estão no quadro **Perguntas e respostas** abaixo, com a origem de cada informação. As respostas Q1 a Q5 foram dadas pelo professor, no grupo da disciplina, no papel dos sócios, e estão registradas na carta de onboarding (acervo, p. 3). As informações sobre o ASO não realizado, o contador anterior (Sócontas / Dr. Osvaldo) e a omissão de março a agosto/2026 vieram pelo mesmo canal (devolutiva oficial do Dossiê 2, p. 3). A resposta do advogado não foi localizada nos registros da dupla; as providências societárias seguem na PEND-02. As premissas adotadas estão no doc. 14 (PR-01 a PR-20).$t$),
    ('3_quadro_de_tratamento_das_pende', $t$As pendências abertas no onboarding estão no quadro **Pendências** abaixo, com risco, responsável, prazo, providência e origem de cada uma, e são acompanhadas pela plataforma até a baixa.$t$)
  ) AS v(cod, txt)
  WHERE s.empresa_id = 1 AND s.documento = 'd2_05_onboarding' AND s.codigo_secao = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'Seções 1–3: % (esperado 3)', n; END IF;

  -- 5. Pós-condições: nenhuma fonte circular, nenhum responsável genérico, nenhum resto de legado
  SELECT count(*) INTO n FROM erp.diligencia_item WHERE empresa_id = 1
     AND (fonte_evidencia LIKE 'Doc. 05 §%' OR responsavel IN ('Diretoria / DP PRISMA', 'cliente', 'advogado', 'contador_anterior', 'escritorio')
          OR prazo_texto = '23/11/2026' OR strpos(resposta_literal, '4x2') > 0 OR strpos(enunciado, '(CNAE 4541-2/01,') > 0);
  IF n <> 0 THEN RAISE EXCEPTION 'Restaram % itens com legado', n; END IF;
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_05_onboarding'
     AND (strpos(conteudo_md, '23/11/2026') > 0 OR conteudo_md ~ 'R\$ ?[0-9]');
  IF n <> 0 THEN RAISE EXCEPTION 'Seções do Doc 05 com legado: %', n; END IF;

  -- 6. Homologação: 30 itens e 4 seções
  UPDATE erp.diligencia_item SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = CASE tipo
      WHEN 'documento' THEN 'Documento conferido (27/11/2026): responsável por pessoa, prazo, status real e origem (carta de onboarding, Estudo de Caso 02, aula de DP ou norma). Homologar valida o registro; o status do item segue retratando o caso.'
      WHEN 'pergunta' THEN 'Pergunta e resposta conferidas (27/11/2026) com a origem: respostas do professor no grupo da disciplina (carta no acervo, p. 3; devolutiva oficial, p. 3), Estudo de Caso 02 ou resposta não localizada (advogado).'
      ELSE 'Pendência conferida (27/11/2026): risco, responsável, prazo, providência e origem; acompanhada até a baixa.'
    END
   WHERE empresa_id = 1 AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 30 THEN RAISE EXCEPTION 'Itens homologados: % (esperado 30)', n; END IF;

  UPDATE erp.documento_secao SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Doc 05 revisado (27/11/2026): texto curto de apresentação; checklist, perguntas e respostas e pendências saem do registro de diligência (fonte única), com origem de cada informação.'
   WHERE empresa_id = 1 AND documento = 'd2_05_onboarding' AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Seções homologadas: % (esperado 4)', n; END IF;
END
$a$;

SELECT tipo, count(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados, count(*) AS total
  FROM erp.diligencia_item WHERE empresa_id = 1 GROUP BY 1 ORDER BY 1;
