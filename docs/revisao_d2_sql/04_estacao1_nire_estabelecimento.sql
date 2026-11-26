-- Dossiê 2, Estação 1 (Cadastro): C-08 / C-17 — campo NIRE por estabelecimento e carga oficial de matriz (GO) e filial (SC).
-- Fonte: Estudo de Caso 02 no acervo (arquivo 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf', pp. 2 e 8).
-- Idempotente; não altera origem_registro nem status_validacao. Tudo ou nada na carga.
ALTER TABLE erp.estabelecimento
    ADD COLUMN IF NOT EXISTS nire TEXT;

DO $a$
DECLARE
  v_arq bigint;
  v_ancoras int;
  v_est int;
  n int;
BEGIN
  SELECT id INTO v_arq FROM acervo.bru_arquivo WHERE chave = 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf';
  IF v_arq IS NULL THEN RAISE EXCEPTION 'Arquivo do Estudo de Caso 02 não encontrado no acervo'; END IF;

  SELECT count(*) INTO v_ancoras
    FROM acervo.bru_linha
   WHERE arquivo_id = v_arq
     AND (
          (pagina = 2 AND n_linha = 16 AND strpos(texto, 'NIRE 52900000015') > 0)
       OR (pagina = 2 AND n_linha = 21 AND strpos(texto, 'NIRE 42900000012') > 0)
       OR (pagina = 8 AND n_linha = 35 AND strpos(texto, 'NIRE nº 42900000012') > 0)
     );
  IF v_ancoras <> 3 THEN RAISE EXCEPTION 'Âncoras de NIRE no acervo divergem (% de 3)', v_ancoras; END IF;

  SELECT count(*) INTO v_est
    FROM erp.estabelecimento
   WHERE empresa_id = 1
     AND chave IN ('est:rota_sul_d2:matriz', 'est:rota_sul_d2:filial_itajai');
  IF v_est <> 2 THEN RAISE EXCEPTION 'Estabelecimentos esperados não encontrados (% de 2)', v_est; END IF;

  UPDATE erp.estabelecimento
     SET nire = CASE chave
           WHEN 'est:rota_sul_d2:matriz' THEN '52900000015'
           ELSE '42900000012'
         END,
         atualizado_em = now()
   WHERE empresa_id = 1
     AND chave IN ('est:rota_sul_d2:matriz', 'est:rota_sul_d2:filial_itajai');
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Estabelecimentos atualizados: % (esperado 2)', n; END IF;

  SELECT count(*) INTO n
    FROM erp.estabelecimento
   WHERE empresa_id = 1
     AND (
          (chave = 'est:rota_sul_d2:matriz' AND nire = '52900000015')
       OR (chave = 'est:rota_sul_d2:filial_itajai' AND nire = '42900000012')
     );
  IF n <> 2 THEN RAISE EXCEPTION 'Pós-condição de NIRE falhou (% de 2)', n; END IF;
END
$a$;

SELECT chave, tipo, cnpj, nire, uf, municipio, status_validacao
  FROM erp.estabelecimento
 WHERE empresa_id = 1
 ORDER BY id;
