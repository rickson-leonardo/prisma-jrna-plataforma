-- Dossiê 2, pente fino final (27/11/2026): restos de legado encontrados na varredura de todos os registros do D2.
-- Não exige recálculo da folha: só textos de fonte e descrições (a rubrica do salário-família ganha o mesmo texto que o motor passa a gravar).
-- Não altera origem_registro nem status de homologação. Tudo ou nada.
DO $a$
DECLARE n int;
  c_sf constant text := 'Portaria Interministerial MPS/MF nº 13/2026 (art. 4º, §§ 2º e 4º)';
BEGIN
  -- 1. Salário-família: fundamento na portaria (PRM-05), não no Decreto 3.048, art. 82
  UPDATE erp.parametro_legal SET norma_citada = c_sf || ' — cota e limite de 2026; direito definido pela remuneração que seria devida no mês (aula de DP, p. 24)', atualizado_em = now()
   WHERE empresa_id = 1 AND codigo = 'SF-2026' AND strpos(norma_citada, '3.048') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Parâmetro SF-2026: %', n; END IF;

  UPDATE erp.folha_item fi SET fonte_normativa = c_sf
  FROM erp.folha_competencia fc WHERE fc.id = fi.competencia_id AND fc.empresa_id = 1
     AND fi.codigo_rubrica = 'SAL-FAMILIA' AND strpos(fi.fonte_normativa, '3.048') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Rubricas de salário-família: % (esperado 2)', n; END IF;

  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md,
      ' e Decreto nº 3.048/1999, art. 82, o salário contratual',
      ' e pela regra do art. 4º, § 2º (direito definido pela remuneração que seria devida no mês, independentemente dos dias trabalhados), o salário contratual'),
    atualizado_em = now()
   WHERE empresa_id = 1 AND documento = 'd2_06_prontuario' AND codigo_secao = '4_declaracoes_de_dependentes_irr'
     AND strpos(conteudo_md, ' e Decreto nº 3.048/1999, art. 82, o salário contratual') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Doc 06, seção 4: %', n; END IF;

  -- 2. DOC-12 sem "PAT" (FO-09)
  UPDATE erp.diligencia_item SET resposta_literal = replace(resposta_literal, 'o VR/PAT e', 'o vale-refeição e'), atualizado_em = now()
   WHERE empresa_id = 1 AND codigo = 'DOC-12' AND strpos(resposta_literal, 'o VR/PAT e') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'DOC-12: %', n; END IF;

  -- 3. Diário de IA (PRM-06, PRM-11)
  UPDATE auditoria.diario_ia SET finalidade = replace(finalidade, '(PR-01 a PR-18)', '(PR-01 a PR-20)')
   WHERE empresa_id = 1 AND id = 192 AND strpos(finalidade, '(PR-01 a PR-18)') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Diário 192: %', n; END IF;
  UPDATE auditoria.diario_ia SET fonte_oficial = replace(fonte_oficial, 'Res. CFC nº 1.708/2023.', 'Res. CFC nº 1.590/2020 (contrato) e nº 1.708/2023 (registro).')
   WHERE empresa_id = 1 AND id = 198 AND strpos(fonte_oficial, 'Res. CFC nº 1.708/2023.') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Diário 198: %', n; END IF;

  -- 4. Descrição dos produtos na matriz do Doc 00
  UPDATE erp.requisito r SET descricao = v.txt
  FROM (VALUES
    ('D2-P2', 'Proposta de Honorários, Contrato de Prestação de Serviços, Procuração e Termo RT (Res. CFC nº 1.590/2020)'),
    ('D2-P7', 'Relatório Técnico de Auditoria Trabalhista (Papéis de Trabalho PT-01..05 e Achados AUD-01..08)'),
    ('D2-P8', 'Registro Numerado de Premissas Adotadas e Fontes Oficiais (PR-01..PR-20)')
  ) AS v(cod, txt)
  WHERE r.codigo = v.cod AND r.dossie_id = (SELECT id FROM erp.dossie WHERE codigo = 'D2');
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'Requisitos: % (esperado 3)', n; END IF;

  -- 5. Pós-condição: varredura dos mesmos padrões
  SELECT count(*) INTO n FROM (
    SELECT conteudo_md x FROM erp.documento_secao WHERE empresa_id = 1 AND dossie = 'D2'
    UNION ALL SELECT to_jsonb(p)::text FROM erp.parametro_legal p WHERE empresa_id = 1
    UNION ALL SELECT fi.fonte_normativa FROM erp.folha_item fi JOIN erp.folha_competencia fc ON fc.id = fi.competencia_id WHERE fc.empresa_id = 1
    UNION ALL SELECT resposta_literal FROM erp.diligencia_item WHERE empresa_id = 1
    UNION ALL SELECT concat_ws(' ', finalidade, fonte_oficial) FROM auditoria.diario_ia WHERE empresa_id = 1 AND dossie = 'D2'
    UNION ALL SELECT descricao FROM erp.requisito WHERE dossie_id = (SELECT id FROM erp.dossie WHERE codigo = 'D2')
  ) t WHERE x ~ '(3\.048/1999,? art\. 82|3\.048/99 art\. 82|VR/PAT|PR-01 a PR-18|PR-01\.\.PR-18|AUD-01\.\.10|4 passagens|4\.238|4\.128|917,40)'
         OR (x ~ '1\.708' AND x !~ '1\.590' AND x !~ 'registro');
  IF n <> 0 THEN RAISE EXCEPTION 'Restos de legado após o pente fino: %', n; END IF;
END
$a$;
