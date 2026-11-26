-- Dossiê 2, Estação 1 (Cadastro): ajustes finais de dados (C-11 a C-13 do registro docs/REVISAO_D2_ROTA_SUL.md).
-- Fonte: Estudo de Caso 02 / Anexo I no acervo (arquivo 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf', pp. 1, 2, 7, 8 e 10).
-- Não altera origem_registro nem status_validacao. Tudo ou nada.
DO $a$
DECLARE
  v_arq bigint;
  v_ancoras int;
  v_emp int;
  v_soc int;
  v_enq int;
  n int;
BEGIN
  SELECT id INTO v_arq FROM acervo.bru_arquivo WHERE chave = 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf';
  IF v_arq IS NULL THEN RAISE EXCEPTION 'Arquivo do Estudo de Caso 02 não encontrado no acervo'; END IF;

  -- 1. Conferências de entrada no acervo e nas tabelas do cadastro
  WITH arq AS (SELECT v_arq AS id)
  SELECT
    (SELECT count(*) FROM acervo.bru_linha l, arq WHERE l.arquivo_id = arq.id AND (
         (pagina = 1  AND n_linha = 33 AND strpos(texto, 'comércio a varejo de automóveis, camionetas e utilitários usados') > 0)
      OR (pagina = 2  AND n_linha = 12 AND texto = 'ROTA SUL IMPORTADORA')
      OR (pagina = 2  AND n_linha = 33 AND texto = 'Ambos os sócios, assinando individualmente')
      OR (pagina = 7  AND n_linha = 23 AND strpos(texto, 'ROTA SUL IMPORTADORA') > 0)
      OR (pagina = 8  AND n_linha = 29 AND strpos(texto, 'ROTA SUL IMPORTADORA') > 0)
      OR (pagina = 10 AND n_linha = 28 AND strpos(texto, 'HELENA APARECIDA MENDES DUARTE e BRUNO MENDES') > 0)
      OR (pagina = 10 AND n_linha = 29 AND strpos(texto, 'assinando individualmente') > 0)
    )),
    (SELECT count(*) FROM erp.empresa
      WHERE id = 1 AND chave = 'emp:rota_sul_d2' AND nome_curto = 'Rota Sul (Caso D2)'),
    (SELECT count(*) FROM erp.participacao_societaria
      WHERE empresa_id = 1 AND chave IN ('part:d2:helena', 'part:d2:bruno') AND papel = 'socio_administrador'),
    (SELECT count(*) FROM erp.enquadramento_historico
      WHERE empresa_id = 1 AND chave IN ('enq:rota_sul_d2:2026', 'enq:rota_sul_d2:2026-09')
        AND status_validacao = 'homologado_contadora'
        AND strpos(apontamento_auditoria, 'clausula de Importacao') > 0)
  INTO v_ancoras, v_emp, v_soc, v_enq;

  IF v_ancoras <> 7 THEN RAISE EXCEPTION 'Âncoras do EC02 divergem (% de 7)', v_ancoras; END IF;
  IF v_emp <> 1 THEN RAISE EXCEPTION 'Empresa fora do estado esperado (% de 1)', v_emp; END IF;
  IF v_soc <> 2 THEN RAISE EXCEPTION 'Sócios fora do estado esperado (% de 2)', v_soc; END IF;
  IF v_enq <> 2 THEN RAISE EXCEPTION 'Enquadramento fora do estado esperado (% de 2)', v_enq; END IF;

  -- C-11: Nome fantasia oficial do caso (EC02 pp. 2, 7 e 8)
  UPDATE erp.empresa
     SET nome_curto = 'Rota Sul Importadora',
         atualizado_em = now()
   WHERE id = 1 AND chave = 'emp:rota_sul_d2' AND nome_curto = 'Rota Sul (Caso D2)';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'C-11 empresa: % (esperado 1)', n; END IF;

  -- C-12: Papel dos sócios em texto legível conforme EC02 p. 2 e Cl. 8ª (p. 10)
  UPDATE erp.participacao_societaria
     SET papel = CASE chave
           WHEN 'part:d2:helena' THEN 'Sócia administradora (assina individualmente)'
           ELSE 'Sócio administrador (assina individualmente)'
         END,
         atualizado_em = now()
   WHERE empresa_id = 1 AND chave IN ('part:d2:helena', 'part:d2:bruno') AND papel = 'socio_administrador';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'C-12 sócios: % (esperado 2)', n; END IF;

  -- C-13: Ressalva histórica do período anterior à 2ª Alteração (22/07/2025) e correção de acentuação em apontamento_auditoria
  UPDATE erp.enquadramento_historico
     SET apontamento_auditoria = replace(replace(replace(apontamento_auditoria, 'CRITICO', 'CRÍTICO'), 'clausula', 'cláusula'), 'Importacao', 'Importação'),
         justificativa_contadora = CASE chave
           WHEN 'enq:rota_sul_d2:2026' THEN
             'Período de 28/10/2024 a 31/08/2026, sob o escritório anterior (não identificado no Estudo de Caso 02, p. 1). Ressalva histórica: antes da 2ª Alteração (22/07/2025), a atividade original era o comércio a varejo de automóveis, camionetas e utilitários usados (EC02 p. 1); o contrato original e a 1ª Alteração não foram fornecidos (DOC-01), mantendo-se os 18 CNAEs consolidados do Anexo I (p. 9). Porte ME e CNAE principal são premissas da PR-01. O risco ao Simples pelos CNAEs de veículos sob "Importação" é do caso e está tratado na PR-02 e no saneamento R-01 (3ª Alteração).'
           ELSE justificativa_contadora
         END,
         atualizado_em = now()
   WHERE empresa_id = 1
     AND chave IN ('enq:rota_sul_d2:2026', 'enq:rota_sul_d2:2026-09')
     AND status_validacao = 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'C-13 enquadramento: % (esperado 2)', n; END IF;

  -- Pós-condições
  SELECT count(*) INTO n FROM erp.empresa WHERE id = 1 AND nome_curto = 'Rota Sul Importadora';
  IF n <> 1 THEN RAISE EXCEPTION 'Pós-condição C-11 falhou'; END IF;
  SELECT count(*) INTO n FROM erp.participacao_societaria WHERE empresa_id = 1 AND papel = 'socio_administrador';
  IF n <> 0 THEN RAISE EXCEPTION 'Pós-condição C-12 falhou (% com socio_administrador)', n; END IF;
  SELECT count(*) INTO n FROM erp.enquadramento_historico WHERE empresa_id = 1 AND strpos(apontamento_auditoria, 'clausula de Importacao') > 0;
  IF n <> 0 THEN RAISE EXCEPTION 'Pós-condição C-13 falhou (% sem acento)', n; END IF;
END
$a$;

SELECT 'empresa' AS tabela, chave, nome_curto AS detalhe, status_validacao FROM erp.empresa WHERE id = 1
UNION ALL
SELECT 'socio', chave, papel, status_validacao FROM erp.participacao_societaria WHERE empresa_id = 1
UNION ALL
SELECT 'enq', chave, vigente_de || ' a ' || coalesce(vigente_ate::text, 'atual') || ' | ' || left(apontamento_auditoria, 60), status_validacao
  FROM erp.enquadramento_historico WHERE empresa_id = 1
ORDER BY 1, 2;
