-- Dossiê 2, Estação 1: homologação dos dois períodos do enquadramento da Rota Sul.
-- Confere antes o estado esperado (dados corrigidos na Estação 1). Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM erp.enquadramento_historico WHERE empresa_id = 1 AND status_validacao = 'alerta_inconsistencia' AND (
       (chave = 'enq:rota_sul_d2:2026'    AND vigente_de = DATE '2024-10-28' AND vigente_ate = DATE '2026-08-31' AND responsavel_tecnico_pessoa_id IS NULL)
    OR (chave = 'enq:rota_sul_d2:2026-09' AND vigente_de = DATE '2026-09-01' AND vigente_ate IS NULL AND responsavel_tecnico_pessoa_id = 463))
    AND cnae_principal = '4530-7/02' AND jsonb_array_length(cnaes_secundarios) = 17;
  IF n <> 2 THEN RAISE EXCEPTION 'Enquadramento fora do estado esperado (% de 2)', n; END IF;

  UPDATE erp.enquadramento_historico SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = CASE chave
      WHEN 'enq:rota_sul_d2:2026' THEN
        'Período de 28/10/2024 a 31/08/2026, sob o escritório anterior (não identificado no Estudo de Caso 02, p. 1). Cadastro conferido com o Anexo I (18 CNAEs, p. 9) e com o Estudo de Caso 02 (p. 1 e 2). Porte ME e CNAE principal são premissas da PR-01. O risco ao Simples pelos CNAEs de veículos sob "Importação" é do caso e está tratado na PR-02 e no saneamento R-01 (3ª Alteração).'
      ELSE
        'Período a partir de 01/09/2026, com a PRISMA JRNA (RT Nathalia Peres Araujo, termo de responsabilidade técnica com vigência em 01/09/2026). Cadastro conferido com o Anexo I (18 CNAEs, p. 9) e com o Estudo de Caso 02 (p. 1 e 2). Porte ME e CNAE principal são premissas da PR-01. O risco ao Simples pelos CNAEs de veículos sob "Importação" é do caso e está tratado na PR-02 e no saneamento R-01 (3ª Alteração).'
    END
  WHERE empresa_id = 1 AND chave IN ('enq:rota_sul_d2:2026', 'enq:rota_sul_d2:2026-09') AND status_validacao = 'alerta_inconsistencia';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Homologados: % (esperado 2)', n; END IF;
END
$a$;

SELECT chave, vigente_de, vigente_ate, responsavel_tecnico_pessoa_id, status_validacao
  FROM erp.enquadramento_historico WHERE empresa_id = 1 ORDER BY vigente_de;
