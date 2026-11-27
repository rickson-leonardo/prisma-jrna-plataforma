-- Dossiê 2, revisita das etapas 1 e 2 (Docs 01 a 05, já homologados) com os achados posteriores:
--   PRM-06: Res. CFC nº 1.590/2020 para contrato, distrato e comunicação ao novo RT; Res. CFC nº 1.708/2023 só para o registro.
--   G-01:   integralização — data correta 31/07/2026; "31/07/2025" é errata (resposta Q5 da carta e resposta no grupo).
--   G-05 / PRM-04: porte EPP (receita de 12 meses de R$ 2.878.147,98); EPP desde 01/01/2026 (LC 123/2006, art. 3º, § 9º).
--   D01-b:  Doc 01 sem a linha que auditava a entrega anterior (V1).
-- Substituições pontuais: cada trecho precisa existir exatamente uma vez. Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int; r record;
  c_just constant text := ' Revisitado em 27/11/2026 (PRM-06: Res. CFC nº 1.590/2020; G-01: errata de data da integralização; D01-b).';
BEGIN
  -- 0. Estado esperado
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND dossie = 'D2'
     AND documento IN ('d2_01_diagnostico', 'd2_02_proposta', 'd2_03_contrato', 'd2_04_termo_rt') AND status_validacao <> 'homologado_contadora';
  IF n <> 0 THEN RAISE EXCEPTION 'Há seções dos Docs 01–04 fora da homologação (%)', n; END IF;
  SELECT count(*) INTO n FROM erp.enquadramento_historico WHERE empresa_id = 1;
  IF n <> 2 THEN RAISE EXCEPTION 'Enquadramento fora do estado esperado (% registros)', n; END IF;
  SELECT count(*) INTO n FROM erp.enquadramento_historico WHERE chave = 'enq:rota_sul_d2:2026-01';
  IF n <> 0 THEN RAISE EXCEPTION 'Período EPP 2026-01 já existe'; END IF;

  -- 1. Seções: substituições pontuais (PRM-06 e G-01)
  FOR r IN SELECT * FROM (VALUES
    ('d2_01_diagnostico', '2_diagnostico_operacional_contab',
       'nem retificaram o conflito de datas (`31/07/2026` × `31/07/2025`). Em setembro/2026, o prazo encontra-se **vencido sob ambas as datas**,',
       'e reconheceram que a data correta é `31/07/2026` — a menção a `31/07/2025` na Cl. 4ª da Consolidação é errata (resposta Q5 da carta de onboarding e resposta do cliente no grupo da disciplina, G-01). Em setembro/2026, o prazo de `31/07/2026` está **vencido**,'),
    ('d2_01_diagnostico', '3_analise_critica_dispositivo_a_',
       '**Conflito frontal de datas** para integralização',
       '**Divergência de datas (errata)** para integralização'),
    ('d2_01_diagnostico', '3_analise_critica_dispositivo_a_',
       'fixa **`31/07/2025`** (9 dias após a assinatura em 22/07/2025).',
       'traz **`31/07/2025`** (9 dias após a assinatura em 22/07/2025). O cliente reconheceu que a data correta é `31/07/2026` e que `31/07/2025` é errata (Q5; G-01); a correção redacional entra na 3ª Alteração.'),
    ('d2_01_diagnostico', '4_matriz_consolidada_de_riscos_f',
       '+ conflito `31/07/2026` × `31/07/2025`',
       '+ errata `31/07/2025` na Cl. 4ª da Consolidação (data correta `31/07/2026` — Q5; G-01)'),
    ('d2_01_diagnostico', '5_plano_de_saneamento_diretrizes',
       'eliminando o conflito `31/07/2026 × 31/07/2025` e os erros redacionais.',
       'corrigindo a errata de data (`31/07/2025` → `31/07/2026`; Q5 e G-01) e os erros redacionais.'),
    ('d2_01_diagnostico', '5_plano_de_saneamento_diretrizes',
       'RFB (PGDAS-D); Res. CFC nº 1.708/2023; Lei nº 4.357/1964, art. 32.',
       'RFB (PGDAS-D); Res. CFC nº 1.590/2020 (distrato e comunicação com o contador anterior); Lei nº 4.357/1964, art. 32.'),
    ('d2_02_proposta', '2_escopo_dos_servicos',
       'Transição de responsabilidade técnica (Resolução CFC nº 1.708/2023)',
       'Transição de responsabilidade técnica (Resolução CFC nº 1.590/2020, arts. 6º a 9º)'),
    ('d2_02_proposta', '4_condicoes_comerciais_gerais',
       'garantindo devolução organizada da documentação (Resolução CFC nº 1.708/2023).',
       'garantindo devolução organizada da documentação (Resolução CFC nº 1.590/2020, arts. 2º e 9º).'),
    ('d2_03_contrato', 'cabecalho',
       'pela **Resolução CFC nº 1.708/2023**, pela',
       'pela **Resolução CFC nº 1.590/2020**, pela'),
    ('d2_03_contrato', 'clausula_2_dos_honorarios_forma_',
       'Suspensão de Serviços — Res. CFC nº 1.708/2023)',
       'Suspensão de Serviços — Res. CFC nº 1.590/2020)'),
    ('d2_03_contrato', 'clausula_2_dos_honorarios_forma_',
       'devolução de documentos nos termos da Resolução CFC nº 1.708/2023.',
       'devolução de documentos nos termos da Resolução CFC nº 1.590/2020 (art. 9º).'),
    ('d2_03_contrato', 'clausula_3_da_vigencia_e_da_resc',
       'transferência de responsabilidade técnica conforme a **Resolução CFC nº 1.708/2023**.',
       'transferência de responsabilidade técnica conforme a **Resolução CFC nº 1.590/2020** (arts. 6º a 9º).'),
    ('d2_04_termo_rt', 'cabecalho',
       '(RESOLUÇÃO CFC Nº 1.708/2023)',
       '(RESOLUÇÃO CFC Nº 1.590/2020)'),
    ('d2_04_termo_rt', 'cabecalho',
       '*(Elaborado em conformidade com a **Resolução CFC nº 1.708/2023** — que dispõe sobre o contrato de prestação de serviços contábeis, a transferência de responsabilidade técnica e o distrato, revogando a Resolução CFC nº 1.555/2018)*',
       '*(Elaborado em conformidade com a **Resolução CFC nº 1.590/2020** — que regulamenta o contrato de prestação de serviços contábeis, o distrato e a comunicação ao novo responsável técnico — e com a **Resolução CFC nº 1.708/2023**, que dispõe sobre o registro das organizações contábeis e revogou a Resolução CFC nº 1.555/2018)*'),
    ('d2_04_termo_rt', '3_declaracao_de_inicio_de_respon',
       'Nos termos da **Resolução CFC nº 1.708/2023**, a profissional',
       'Nos termos das **Resoluções CFC nº 1.590/2020 e nº 1.708/2023**, a profissional'),
    ('d2_04_termo_rt', '4_clausula_de_delimitacao_de_res',
       '(**Sócontas / Dr. Osvaldo**), nos termos da Resolução CFC nº 1.708/2023.',
       '(**Sócontas / Dr. Osvaldo**), nos termos da Resolução CFC nº 1.590/2020 (art. 8º).'),
    ('d2_04_termo_rt', '5_rol_de_pendencias_e_riscos_ide',
       'resguardo ético-profissional (Resolução CFC nº 1.708/2023)',
       'resguardo ético-profissional (Resolução CFC nº 1.590/2020)'),
    ('d2_04_termo_rt', '5_rol_de_pendencias_e_riscos_ide',
       'Notificação formal ao contador anterior conforme Resolução CFC nº 1.708/2023.',
       'Notificação formal ao contador anterior conforme Resolução CFC nº 1.590/2020 (art. 8º).'),
    ('d2_04_termo_rt', '5_rol_de_pendencias_e_riscos_ide',
       'conflito Cl. 3ª `31/07/2026` × Cl. 4ª `31/07/2025`',
       'errata de data na Cl. 4ª (`31/07/2025`; correta `31/07/2026`)')
  ) AS v(doc, cod, velho, novo) LOOP
    UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, r.velho, r.novo), atualizado_em = now()
     WHERE empresa_id = 1 AND dossie = 'D2' AND documento = r.doc AND codigo_secao = r.cod
       AND (length(conteudo_md) - length(replace(conteudo_md, r.velho, ''))) = length(r.velho);
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN RAISE EXCEPTION 'Trecho não encontrado exatamente uma vez em %/%: %', r.doc, r.cod, left(r.velho, 80); END IF;
  END LOOP;

  -- 2. Doc 01: título do item 3.3 e linha da V1 (D01-b)
  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, 'Conflito de Prazos', 'Errata de Prazo'), atualizado_em = now()
   WHERE empresa_id = 1 AND documento = 'd2_01_diagnostico' AND strpos(conteudo_md, 'Conflito de Prazos') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n < 1 THEN RAISE EXCEPTION 'Título 3.3 não encontrado'; END IF;
  UPDATE erp.documento_secao SET conteudo_md = regexp_replace(conteudo_md, '\| \*\*Documentos de DP da 1ª entrega \(v1\)[^\n]*\n', ''), atualizado_em = now()
   WHERE empresa_id = 1 AND documento = 'd2_01_diagnostico' AND codigo_secao = '3_analise_critica_dispositivo_a_' AND strpos(conteudo_md, '1ª entrega (v1)') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Linha da V1 no Doc 01: %', n; END IF;

  UPDATE erp.documento_secao SET justificativa_contadora = coalesce(justificativa_contadora, '') || c_just
   WHERE empresa_id = 1 AND dossie = 'D2' AND documento IN ('d2_01_diagnostico', 'd2_02_proposta', 'd2_03_contrato', 'd2_04_termo_rt')
     AND atualizado_em = now();

  -- 3. Cláusula do capital no Anexo I (G-01)
  UPDATE erp.instrumento_societario_clausula SET
      titulo = replace(titulo, 'conflito 31/07/2026 × 31/07/2025', 'errata de data (31/07/2025; correta 31/07/2026)'),
      regra_texto = replace(regra_texto, 'enquanto a Cl. 4ª da Consolidação (p. 9) fixa 31/07/2025 — ambos vencidos em 14/09/2026,',
                    'enquanto a Cl. 4ª da Consolidação (p. 9) traz 31/07/2025, errata reconhecida pelo cliente (resposta Q5 da carta de onboarding e G-01: a data correta é 31/07/2026, vencida em 14/09/2026),'),
      redacao_contrato = replace(redacao_contrato, 'enquanto a Cl. 4ª da Consolidação (p. 9) fixa 31/07/2025 — ambos vencidos em 14/09/2026,',
                    'enquanto a Cl. 4ª da Consolidação (p. 9) traz 31/07/2025, errata reconhecida pelo cliente (resposta Q5 da carta de onboarding e G-01: a data correta é 31/07/2026, vencida em 14/09/2026),'),
      providencia = replace(providencia, 'corrigindo o conflito de datas', 'corrigindo a errata de data'),
      justificativa_contadora = replace(justificativa_contadora, 'conflito de prazo 31/07/2026 × 31/07/2025', 'errata de data (31/07/2025 na Consolidação; correta 31/07/2026 — Q5 e G-01)'),
      atualizado_em = now()
   WHERE empresa_id = 1 AND id = 1273 AND strpos(titulo, 'conflito 31/07/2026 × 31/07/2025') > 0
     AND strpos(regra_texto, 'fixa 31/07/2025 — ambos vencidos') > 0 AND strpos(providencia, 'corrigindo o conflito de datas') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Cláusula do capital: %', n; END IF;

  -- 4. Doc 05 (PRM-06): DOC-07 e PEND-03
  UPDATE erp.diligencia_item SET enunciado = replace(enunciado, '(Res. CFC 1.708/2023)', '(Res. CFC nº 1.590/2020)'), atualizado_em = now()
   WHERE empresa_id = 1 AND codigo = 'DOC-07' AND strpos(enunciado, '(Res. CFC 1.708/2023)') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'DOC-07: %', n; END IF;
  UPDATE erp.diligencia_item SET fonte_evidencia = replace(fonte_evidencia, 'Res. CFC nº 1.708/2023', 'Res. CFC nº 1.590/2020 (arts. 6º a 8º)'),
         resposta_literal = replace(resposta_literal, '(Res. CFC 1.708/2023)', '(Res. CFC nº 1.590/2020, art. 8º)'), atualizado_em = now()
   WHERE empresa_id = 1 AND codigo = 'PEND-03' AND strpos(fonte_evidencia, 'Res. CFC nº 1.708/2023') > 0 AND strpos(resposta_literal, '(Res. CFC 1.708/2023)') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'PEND-03: %', n; END IF;

  -- 5. Contratos de serviço (PRM-06)
  UPDATE erp.contrato_servico SET titulo = replace(titulo, '(Res. CFC nº 1.708/2023)', '(Res. CFC nº 1.590/2020)'),
         conteudo_md = 'Fundamentado na Res. CFC nº 1.590/2020 (contrato, distrato e comunicação ao novo RT); registro da PRISMA JRNA pela Res. CFC nº 1.708/2023, que revogou a nº 1.555/2018.',
         atualizado_em = now()
   WHERE empresa_id = 1 AND codigo_documento = 'termo_rt' AND strpos(titulo, '1.708/2023') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Termo de RT: %', n; END IF;
  UPDATE erp.contrato_servico SET escopo_resumo = replace(escopo_resumo, 'Res. CFC nº 1.708/2023', 'Res. CFC nº 1.590/2020'), atualizado_em = now()
   WHERE empresa_id = 1 AND codigo_documento = 'contrato' AND strpos(escopo_resumo, 'Res. CFC nº 1.708/2023') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Contrato: %', n; END IF;

  -- 6. Enquadramento (G-05 / PRM-04): EPP desde 01/01/2026 (ano-calendário seguinte ao excesso — LC 123/2006, art. 3º, § 9º)
  INSERT INTO erp.enquadramento_historico (chave, empresa_id, porte, regime_tributario, cnae_principal, cnaes_secundarios, vigente_de, vigente_ate,
         registro_crc, fonte_chave, responsavel_tecnico_pessoa_id, origem_registro, status_validacao, apontamento_auditoria, justificativa_contadora)
  SELECT 'enq:rota_sul_d2:2026-01', empresa_id, 'EPP', regime_tributario, cnae_principal, cnaes_secundarios, DATE '2026-01-01', DATE '2026-08-31',
         registro_crc, fonte_chave, responsavel_tecnico_pessoa_id, 'usuario', 'homologado_contadora', apontamento_auditoria,
         'Período de 01/01/2026 a 31/08/2026, ainda sob o escritório anterior. Porte EPP: o cliente informou receita bruta de R$ 2.878.147,98 nos últimos 12 meses (resposta no grupo da disciplina, G-05), o que indica receita de 2025 acima do limite da ME; a EPP vale a partir do ano-calendário seguinte (LC 123/2006, art. 3º, § 9º). Premissa PR-01.'
    FROM erp.enquadramento_historico WHERE empresa_id = 1 AND chave = 'enq:rota_sul_d2:2026';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Período EPP 2026: %', n; END IF;
  UPDATE erp.enquadramento_historico SET vigente_ate = DATE '2025-12-31',
         justificativa_contadora = replace(justificativa_contadora, 'Período de 28/10/2024 a 31/08/2026', 'Período de 28/10/2024 a 31/12/2025')
           || ' Porte ME no período é premissa (receita de 2024 e 2025 não informada por ano); a partir de 01/01/2026, EPP (G-05).'
   WHERE empresa_id = 1 AND chave = 'enq:rota_sul_d2:2026' AND vigente_ate = DATE '2026-08-31';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Período ME: %', n; END IF;
  UPDATE erp.enquadramento_historico SET porte = 'EPP',
         justificativa_contadora = replace(justificativa_contadora, 'Porte ME e CNAE principal são premissas da PR-01.',
           'Porte EPP pela receita de 12 meses informada pelo cliente (R$ 2.878.147,98 — G-05; LC 123/2006, art. 3º, II e § 9º); CNAE principal é premissa da PR-01.')
   WHERE empresa_id = 1 AND chave = 'enq:rota_sul_d2:2026-09' AND porte = 'ME' AND strpos(justificativa_contadora, 'Porte ME e CNAE principal são premissas da PR-01.') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Período PRISMA JRNA: %', n; END IF;

  -- 7. Pós-condições
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND dossie = 'D2'
     AND documento IN ('d2_01_diagnostico', 'd2_02_proposta', 'd2_03_contrato', 'd2_04_termo_rt')
     AND ((strpos(conteudo_md, '1.708') > 0 AND strpos(conteudo_md, '1.590') = 0) OR conteudo_md ~* 'conflito[^\n]{0,40}31/07' OR strpos(conteudo_md, '(v1)') > 0);
  IF n <> 0 THEN RAISE EXCEPTION 'Seções dos Docs 01–04 com resto: %', n; END IF;
  SELECT count(*) INTO n FROM erp.diligencia_item WHERE empresa_id = 1 AND concat_ws(' ', enunciado, resposta_literal, fonte_evidencia) LIKE '%1.708%';
  IF n <> 0 THEN RAISE EXCEPTION 'Diligência citando a 1.708: %', n; END IF;
  SELECT count(*) INTO n FROM erp.enquadramento_historico WHERE empresa_id = 1 AND vigente_de >= DATE '2026-01-01' AND porte <> 'EPP';
  IF n <> 0 THEN RAISE EXCEPTION 'Períodos de 2026 fora de EPP: %', n; END IF;
END
$a$;

SELECT chave, porte, vigente_de, vigente_ate, status_validacao FROM erp.enquadramento_historico WHERE empresa_id = 1 ORDER BY vigente_de;
