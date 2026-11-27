-- Dossiê 2, Estação 2 (2ª Alteração Contratual — Anexo I): homologação dos 9 achados e limpeza de 3 metadados herdados do D1.
-- Fonte: Estudo de Caso 02 / Anexo I (arquivo 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf', pp. 2 e 7–13).
-- Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE
  v_prontas int;
  v_meta_d1 int;
  n int;
BEGIN
  -- 1. Pré-condição: 9 achados já revisados e 3 metadados herdados do D1
  SELECT
    count(*) FILTER (WHERE chave IN ('inst:d2:01','inst:d2:02','inst:d2:03','inst:d2:04','inst:d2:05','inst:d2:06','inst:d2:07','inst:d2:08','inst:d2:09')
                       AND status_validacao IN ('alerta_inconsistencia', 'pendente_revisao')
                       AND risco_tipo IN ('formal', 'material')
                       AND risco_nivel IN ('baixo', 'medio', 'alto', 'critico')
                       AND coalesce(trim(providencia), '') <> ''
                       AND coalesce(trim(fundamento_legal), '') <> ''
                       AND coalesce(trim(responsavel), '') <> ''
                       AND coalesce(trim(prazo_texto), '') <> ''),
    count(*) FILTER (WHERE (chave = 'inst:d2:05' AND metodo_haveres = 'balanco_determinacao')
                        OR (chave IN ('inst:d2:06', 'inst:d2:08') AND quorum_tipo = 'unanimidade'))
  INTO v_prontas, v_meta_d1
  FROM erp.instrumento_societario_clausula
  WHERE empresa_id = 1;

  IF v_prontas <> 9 THEN RAISE EXCEPTION 'Cláusulas prontas para homologar divergem (% de 9)', v_prontas; END IF;
  IF v_meta_d1 <> 3 THEN RAISE EXCEPTION 'Metadados herdados do D1 divergem (% de 3)', v_meta_d1; END IF;

  -- 2. Homologar os 9 achados com justificativa técnica e limpar metadados herdados do D1
  UPDATE erp.instrumento_societario_clausula AS cl
     SET status_validacao = 'homologado_contadora',
         metodo_haveres = CASE WHEN cl.chave = 'inst:d2:05' THEN 'nao_aplicavel' ELSE cl.metodo_haveres END,
         quorum_tipo = CASE WHEN cl.chave IN ('inst:d2:06', 'inst:d2:08') THEN 'nao_aplicavel' ELSE cl.quorum_tipo END,
         justificativa_contadora = v.justificativa_contadora,
         atualizado_em = now()
    FROM (
      VALUES
        (
          'inst:d2:01',
          'Achado conferido no Anexo I (EC02 pp. 7, 8 e 13): a divergência DISTRIBUIÇÃO × DISTRIBUIDORA é vício formal do caso. Diagnosticado com base nos arts. 1.158 e 1.163 do CC e encaminhado para uniformização na 3ª Alteração Contratual (etapa R-06).'
        ),
        (
          'inst:d2:02',
          'Achado conferido na ficha do caso e no Anexo I (EC02 p. 2 × p. 8, Cl. 1ª Par. Único): divergência Sala 223 × Sala 223 A 32 é vício formal do caso. Encaminhado para conferência documental (IPTU/locação/CNPJ) e retificação na 3ª Alteração e DBE Redesim (etapa R-06).'
        ),
        (
          'inst:d2:03',
          'Achado conferido no Anexo I (EC02 pp. 7–9, Cl. 2ª Alt., Cl. 1ª Par. Único e Cl. 3ª Consol.): matriz com 18 CNAEs e filial com 17 (omite 8211-3/00), mantendo 4541-2/01, 4541-2/03 e 4511-1/02 sob IMPORTAÇÃO E EXPORTAÇÃO. Risco material crítico frente à LC 123/2006, art. 17, VIII; tratado na PR-02 e encaminhado para depuração urgente na 3ª Alteração (etapa R-01).'
        ),
        (
          'inst:d2:04',
          'Achado conferido na ficha do caso e no Anexo I (EC02 pp. 2, 8–10, Cl. 3ª § 1º Alt., Cl. 4ª e Cl. 7ª): conflito de prazo 31/07/2026 × 31/07/2025, R$ 500.000,00 a integralizar em mora e erros redacionais literais. Risco material crítico (CC arts. 1.004, 1.052 e 1.058), encaminhado para notificação de 30 dias e saneamento na 3ª Alteração (etapa R-02).'
        ),
        (
          'inst:d2:05',
          'Achado conferido no Anexo I (EC02 pp. 9 e 11–12, Cls. 5ª, 12ª e 14ª): três critérios conflitantes de haveres (IGPM+3% em 24x, Balanço Especial em 10x e Valor de Mercado sem prazo) mais AGO/tesouraria (Cl. 5ª IV). Limpo metodo_haveres herdado do D1 (Balanço de Determinação é proposta de saneamento, não o texto da 2ª Alteração). Encaminhado para unificação (R-03 e R-05).'
        ),
        (
          'inst:d2:06',
          'Achado conferido no Anexo I (EC02 pp. 10–12, Cls. 7ª–11ª e 14ª § 1º): quórum 50/50 sem cláusula de desempate, ausência de alçada financeira, ambiguidade de mandato na Cl. 11ª e ilegalidade da Cl. 10ª frente ao CC art. 1.061 (Lei 14.451/2022: mínimo de 2/3 dos sócios com capital não integralizado). Limpo quorum_tipo herdado do D1 e encaminhado para saneamento (etapa R-04).'
        ),
        (
          'inst:d2:07',
          'Achado conferido no Anexo I (EC02 pp. 11–12, Cl. 13ª §§ 1º–3º e Cl. 16ª) e vinculado às respostas de 24/09/2026 (pendência P-01): JCP (TJLP) oneroso no Simples, lucros sem trava de regularidade fiscal/contábil (Lei 4.357/1964, art. 32) e pró-labore facultativo (SC COSIT 120/2016). Encaminhado para supressão de JCP, bloqueio de lucros e formalização de pró-labore (PR-15, R-07 e R-09).'
        ),
        (
          'inst:d2:08',
          'Achado conferido no Anexo I (EC02 p. 12, Cl. 15ª): quórum de 3/4 reproduz remissão revogada do art. 1.076 do CC (Lei 14.451/2022 reduziu o piso legal para mais da metade) e estende 3/4 ao liquidante. Limpo quorum_tipo herdado do D1 e encaminhado para atualização na 3ª Alteração (etapa R-04).'
        ),
        (
          'inst:d2:09',
          'Achado conferido no Anexo I (EC02 p. 12, Cl. 18ª): cumulação simultânea de normas da Sociedade Simples e da Sociedade Anônima cria antinomia frente ao CC art. 1.053, parágrafo único. Encaminhado para definição de regência supletiva única na 3ª Alteração (etapa R-05).'
        )
    ) AS v(chave, justificativa_contadora)
   WHERE cl.empresa_id = 1
     AND cl.chave = v.chave
     AND cl.status_validacao IN ('alerta_inconsistencia', 'pendente_revisao');

  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 9 THEN RAISE EXCEPTION 'Cláusulas homologadas: % (esperado 9)', n; END IF;

  -- 3. Pós-condição: 9/9 homologadas, com justificativa e sem metadados herdados do D1
  SELECT count(*) INTO n
    FROM erp.instrumento_societario_clausula
   WHERE empresa_id = 1
     AND chave IN ('inst:d2:01','inst:d2:02','inst:d2:03','inst:d2:04','inst:d2:05','inst:d2:06','inst:d2:07','inst:d2:08','inst:d2:09')
     AND status_validacao = 'homologado_contadora'
     AND coalesce(trim(justificativa_contadora), '') <> ''
     AND metodo_haveres = 'nao_aplicavel'
     AND quorum_tipo = 'nao_aplicavel';
  IF n <> 9 THEN RAISE EXCEPTION 'Pós-condição da homologação da Estação 2 falhou (% de 9)', n; END IF;
END
$a$;

SELECT ordem, chave, risco_tipo, risco_nivel, metodo_haveres, quorum_tipo, status_validacao
  FROM erp.instrumento_societario_clausula
 WHERE empresa_id = 1
 ORDER BY ordem;
