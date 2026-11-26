-- Dossiê 2, Estação 2 (2ª Alteração Contratual — Anexo I): revisão dos 9 achados em erp.instrumento_societario_clausula (empresa_id = 1).
-- Fonte: Estudo de Caso 02 / Anexo I no acervo (arquivo 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf', pp. 2 e 7–13).
-- Remove número solto legado (+R$ 917,40/mês) e preenche os 6 campos novos da régua oficial do P1 (risco_tipo, risco_nivel, providencia, fundamento_legal, responsavel, prazo_texto).
-- Não altera origem_registro; mantém status_validacao atual para revisão e homologação da contadora na tela. Tudo ou nada.
DO $a$
DECLARE
  v_arq bigint;
  v_ancoras int;
  v_cnaes_filial int;
  v_cnaes_matriz int;
  v_clausulas int;
  n int;
BEGIN
  SELECT id INTO v_arq FROM acervo.bru_arquivo WHERE chave = 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf';
  IF v_arq IS NULL THEN RAISE EXCEPTION 'Arquivo do Estudo de Caso 02 não encontrado no acervo'; END IF;

  -- 1. Conferência literal das 27 linhas-âncora no texto do Estudo de Caso 02 / Anexo I + contagem de CNAEs (filial 17, matriz 18)
  WITH arq AS (SELECT v_arq AS id)
  SELECT
    (SELECT count(*) FROM acervo.bru_linha l, arq WHERE l.arquivo_id = arq.id AND (
         (pagina = 2  AND n_linha = 23 AND strpos(texto, 'Sala 223, Bairro Canhanduba') > 0)
      OR (pagina = 7  AND n_linha = 10 AND texto = 'ROTA SUL IMPORTADORA, EXPORTADORA, COMÉRCIO E DISTRIBUIDORA LTDA')
      OR (pagina = 7  AND n_linha = 31 AND texto = 'IMPORTAÇÃO E EXPORTAÇÃO:')
      OR (pagina = 7  AND n_linha = 50 AND strpos(texto, '8211-3/00') > 0)
      OR (pagina = 8  AND n_linha = 5  AND strpos(texto, 'moeda corrente pelo pais') > 0)
      OR (pagina = 8  AND n_linha = 8  AND strpos(texto, 'até o dia 31/07/2026') > 0)
      OR (pagina = 8  AND n_linha = 24 AND texto = 'ROTA SUL IMPORTADORA, EXPORTADORA, COMÉRCIO E DISTRIBUIÇÃO LTDA')
      OR (pagina = 8  AND n_linha = 28 AND strpos(texto, 'COMÉRCIO E DISTRIBUIDORA LTDA') > 0)
      OR (pagina = 8  AND n_linha = 33 AND strpos(texto, 'Sala 223 A 32') > 0)
      OR (pagina = 8  AND n_linha = 54 AND strpos(texto, '4789-0/99') > 0)
      OR (pagina = 9  AND n_linha = 25 AND strpos(texto, '8211-3/00') > 0)
      OR (pagina = 9  AND n_linha = 29 AND strpos(texto, 'reais) quotas') > 0)
      OR (pagina = 9  AND n_linha = 31 AND strpos(texto, 'até o dia 31/07/2025') > 0)
      OR (pagina = 9  AND n_linha = 49 AND strpos(texto, '24 (vinte e quatro) parcelas') > 0)
      OR (pagina = 9  AND n_linha = 53 AND strpos(texto, 'IGPM-FGV e incluso juros de 3% a.a.') > 0)
      OR (pagina = 9  AND n_linha = 58 AND strpos(texto, 'primeira AGO') > 0)
      OR (pagina = 9  AND n_linha = 59 AND strpos(texto, 'tesouraria') > 0)
      OR (pagina = 10 AND n_linha = 32 AND strpos(texto, '51% (cinquenta e um por cento)') > 0)
      OR (pagina = 10 AND n_linha = 46 AND strpos(texto, '51% (cinquenta e um por cento)') > 0)
      OR (pagina = 10 AND n_linha = 50 AND strpos(texto, 'prazo de 03 (três) anos') > 0)
      OR (pagina = 11 AND n_linha = 13 AND strpos(texto, 'mesmas cláusulas determinantes das obrigações') > 0)
      OR (pagina = 11 AND n_linha = 23 AND strpos(texto, 'Balanço Especial, em até 10 (dez) parcelas') > 0)
      OR (pagina = 11 AND n_linha = 37 AND strpos(texto, 'juros sobre o capital próprio (TJLP)') > 0)
      OR (pagina = 11 AND n_linha = 47 AND strpos(texto, 'valor de mercado da sociedade') > 0)
      OR (pagina = 12 AND n_linha = 17 AND strpos(texto, 'concordância de ¾ do capital') > 0)
      OR (pagina = 12 AND n_linha = 21 AND strpos(texto, 'Os sócios poderão, de comum acordo, fixar uma retirada mensal') > 0)
      OR (pagina = 12 AND n_linha = 33 AND strpos(texto, 'normas da Sociedade Simples conjuntamente com as normas da Sociedade') > 0)
    )),
    (SELECT count(*) FROM acervo.bru_linha l, arq, regexp_match(l.texto, '^(\d{4}-\d/\d{2}) ') AS m
      WHERE l.arquivo_id = arq.id AND l.pagina = 8 AND l.n_linha BETWEEN 37 AND 54 AND m IS NOT NULL),
    (SELECT count(*) FROM acervo.bru_linha l, arq, regexp_match(l.texto, '^(\d{4}-\d/\d{2}) ') AS m
      WHERE l.arquivo_id = arq.id AND l.pagina = 9 AND l.n_linha BETWEEN 7 AND 25 AND m IS NOT NULL),
    (SELECT count(*) FROM erp.instrumento_societario_clausula
      WHERE empresa_id = 1
        AND chave IN ('inst:d2:01','inst:d2:02','inst:d2:03','inst:d2:04','inst:d2:05','inst:d2:06','inst:d2:07','inst:d2:08','inst:d2:09')
        AND origem_registro = 'importado_rascunho_v2'
        AND risco_tipo IS NULL AND risco_nivel IS NULL
        AND providencia IS NULL AND fundamento_legal IS NULL
        AND responsavel IS NULL AND prazo_texto IS NULL)
  INTO v_ancoras, v_cnaes_filial, v_cnaes_matriz, v_clausulas;

  IF v_ancoras <> 27 THEN RAISE EXCEPTION 'Âncoras do Anexo I divergem (% de 27)', v_ancoras; END IF;
  IF v_cnaes_filial <> 17 THEN RAISE EXCEPTION 'CNAEs da filial divergem (% de 17)', v_cnaes_filial; END IF;
  IF v_cnaes_matriz <> 18 THEN RAISE EXCEPTION 'CNAEs da matriz divergem (% de 18)', v_cnaes_matriz; END IF;
  IF v_clausulas <> 9 THEN RAISE EXCEPTION 'Cláusulas fora do estado esperado (% de 9)', v_clausulas; END IF;

  -- 2. Atualização dos 9 achados com fontes oficiais, remoção do número solto legado e preenchimento dos 6 campos do P1
  UPDATE erp.instrumento_societario_clausula AS cl
     SET numero_clausula = v.numero_clausula,
         titulo = v.titulo,
         regra_texto = v.regra_texto,
         redacao_contrato = v.regra_texto,
         referencia_v1_original = v.referencia_v1_original,
         apontamento_auditoria = v.apontamento_auditoria,
         risco_tipo = v.risco_tipo,
         risco_nivel = v.risco_nivel,
         providencia = v.providencia,
         fundamento_legal = v.fundamento_legal,
         responsavel = v.responsavel,
         prazo_texto = v.prazo_texto,
         versao = cl.versao + 1,
         atualizado_em = now()
    FROM (
      VALUES
        (
          'inst:d2:01',
          'Preâmbulo / Título Consolidação / Cl. 1ª Consolidação',
          'Divergência na denominação social: DISTRIBUIÇÃO × DISTRIBUIDORA',
          'O preâmbulo da 2ª Alteração (EC02 p. 7), a Cl. 1ª da Consolidação (p. 8) e a certidão de registro (p. 13) grafam ''ROTA SUL IMPORTADORA, EXPORTADORA, COMÉRCIO E DISTRIBUIDORA LTDA'', enquanto o título da Consolidação (Cl. 4ª, p. 8) grafa ''...COMÉRCIO E DISTRIBUIÇÃO LTDA''.',
          'EC02 pp. 7, 8 e 13 (Anexo I)',
          'Uniformizar como ''ROTA SUL IMPORTADORA, EXPORTADORA, COMÉRCIO E DISTRIBUIDORA LTDA'' na 3ª Alteração Contratual (etapa R-06).',
          'formal',
          'baixo',
          'Rerratificar e uniformizar o título da Consolidação para ''ROTA SUL IMPORTADORA, EXPORTADORA, COMÉRCIO E DISTRIBUIDORA LTDA'' na 3ª Alteração Contratual, alinhando-o ao cartão CNPJ e ao registro na JUCEG (R-06).',
          'CC (Lei nº 10.406/2002), arts. 1.158 e 1.163 (https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm, acesso em 26/11/2026); EC02 pp. 7, 8 e 13.',
          'Advogado Societário / PRISMA JRNA (orientação cadastral)',
          '20/10/2026 (R-06 / 3ª Alteração Contratual)'
        ),
        (
          'inst:d2:02',
          'Cl. 1ª e Par. Único Consolidação',
          'Endereço da Filial de Itajaí-SC (Sala 223 × Sala 223 A 32)',
          'A Cl. 1ª altera a sede da matriz para Rua das Mangueiras, Qd. 40, Lt. 11, nº 215, Setor Campinas, Goiânia-GO (EC02 p. 7). Para a filial de Itajaí-SC (CNPJ 11.222.333/0002-62, NIRE 42900000012), a ficha do caso informa ''Sala 223'' (EC02 p. 2), enquanto o Par. Único da Cl. 1ª da Consolidação grafa ''Sala 223 A 32'' (EC02 p. 8).',
          'EC02 p. 2 × p. 8 (Cl. 1ª, Par. Único)',
          'Conferir contrato de locação/IPTU e cartão CNPJ da filial de Itajaí-SC para retificar o complemento no instrumento e no DBE Redesim (R-06).',
          'formal',
          'medio',
          'Solicitar matrícula/IPTU, contrato de locação e cartão CNPJ da filial de Itajaí-SC e padronizar o complemento exato (''Sala 223'' ou ''Sala 223 A 32'') na 3ª Alteração Contratual, na JUCESC e no DBE Redesim (R-06).',
          'IN RFB nº 2.119/2022 (CNPJ); IN DREI nº 81/2020 (https://www.gov.br/empresas-e-negocios/pt-br/drei, acesso em 26/11/2026); EC02 pp. 2 e 8.',
          'Sócios Rota Sul + PRISMA JRNA / Advogado Societário',
          '20/10/2026 (R-06 / DBE Redesim e 3ª Alteração)'
        ),
        (
          'inst:d2:03',
          'Cl. 2ª Alteração, Cl. 1ª Par. Único e Cl. 3ª Consolidação',
          'Objeto social heterogêneo: 18 CNAEs Matriz × 17 Filial e risco de vedação ao Simples (importação de motos/autos)',
          'A Cl. 2ª da Alteração (EC02 p. 7) e a Cl. 3ª da Consolidação (p. 9) listam 18 CNAEs para a matriz sob o título ''IMPORTAÇÃO E EXPORTAÇÃO:'', enquanto a Cl. 1ª, Par. Único (p. 8) lista 17 CNAEs para a filial, omitindo 8211-3/00. Ambos mantêm 4541-2/01 (motos atacado), 4541-2/03 (motos varejo) e 4511-1/02 (automóveis usados) sob importação, expondo a empresa à vedação do Simples Nacional (LC 123/2006, art. 17, VIII), além de CNAEs estranhos à atividade real de pneumáticos e peças (EC02 pp. 1–2).',
          'EC02 pp. 1–2 e 7–9 (Anexo I)',
          'CRÍTICO: excluir 4541-2/01, 4541-2/03 e 4511-1/02, alinhar os CNAEs entre matriz e filial e depurar atividades estranhas aos pneumáticos (PR-02 / R-01).',
          'material',
          'critico',
          'Aprovar com os sócios a depuração do objeto social na 3ª Alteração Contratual (R-01 / PR-02), excluindo 4541-2/01, 4541-2/03 e 4511-1/02, removendo CNAEs não exercidos e compatibilizando matriz (Goiânia-GO) e filial aduaneira (Itajaí-SC), com atualização imediata via DBE na JUCEG e JUCESC.',
          'LC nº 123/2006, art. 17, VIII e arts. 29–30 (https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm, acesso em 26/11/2026); EC02 pp. 1–2 e 7–9.',
          'Sócios Rota Sul + Advogado Societário (recomendação RT PRISMA JRNA)',
          '10 dias / até 20/10/2026 (urgente — R-01 / PR-02)'
        ),
        (
          'inst:d2:04',
          'Cl. 3ª § 1º Alt. × Cl. 4ª e Cl. 7ª Consolidação',
          'Capital Social R$ 1.500.000,00: conflito 31/07/2026 × 31/07/2025, mora de R$ 500 mil e erros redacionais',
          'O capital foi aumentado de R$ 1.000.000,00 para R$ 1.500.000,00 (750.000 quotas para Helena e 750.000 para Bruno). A Cl. 3ª § 1º da Alteração (EC02 p. 8) fixa integralização dos R$ 500.000,00 até 31/07/2026, enquanto a Cl. 4ª da Consolidação (p. 9) fixa 31/07/2025 — ambos vencidos em 14/09/2026, com a parcela de R$ 500.000,00 ainda a integralizar (p. 2), caracterizando mora e responsabilidade solidária (Cl. 7ª, p. 10). Há ainda erros redacionais literais: ''pelo pais'' (p. 8) e ''1.500.000 (um milhão e quinhentos mil reais) quotas'' / ''a ser integralizados'' (p. 9).',
          'EC02 pp. 2, 8, 9 e 10 (Anexo I)',
          'Notificar os sócios no prazo de 30 dias da Cl. 7ª para integralização efetiva dos R$ 500.000,00 ou redução do capital para R$ 1.000.000,00, corrigindo a redação na 3ª Alteração (R-02).',
          'material',
          'critico',
          'Comprovar extratos de eventual aporte (DOC-08) e formalizar o rito da Cl. 7ª (notificação de 30 dias): realizar a integralização dos R$ 500.000,00 ou reduzir o capital social para R$ 1.000.000,00 na 3ª Alteração Contratual, corrigindo o conflito de datas e os erros redacionais (R-02).',
          'CC (Lei nº 10.406/2002), arts. 1.004, 1.031 § 1º, 1.052 e 1.058 (https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm, acesso em 26/11/2026); EC02 pp. 2 e 8–10.',
          'Sócios Rota Sul + Advogado Societário (apoio documental PRISMA JRNA)',
          '20/10/2026 (notificação em 30 dias — R-02)'
        ),
        (
          'inst:d2:05',
          'Cl. 5ª, Cl. 12ª e Cl. 14ª Consolidação',
          'Três critérios conflitantes de apuração de haveres + institutos de S.A. (AGO/tesouraria)',
          'O Anexo I contém três regras incompatíveis de haveres: Cl. 5ª caput e inc. I (EC02 p. 9) fixa valor das quotas corrigido pelo IGPM-FGV + juros de 3% a.a. em até 24 parcelas (1ª em 90 dias); Cl. 12ª caput, §§ 1º e 4º (p. 11) prevê Balanço Especial levantado em 30 dias, pago em até 10 parcelas (1ª em 30 dias); e Cl. 14ª caput e incs. I–IV (pp. 11–12) prevê valor de mercado por avaliadoras, sem prazo de pagamento e citando IGPM-FGV no inc. IV — chocando-se diretamente com a Cl. 12ª § 4º na mesma retirada com aviso de 60 dias. Além disso, a Cl. 5ª, inc. IV (p. 9) menciona ''AGO (Assembleia Geral Ordinária)'' e ''tesouraria'', institutos típicos de S.A.',
          'EC02 pp. 9, 11 e 12 (Anexo I)',
          'Unificar os haveres em cláusula única (recomendado Balanço de Determinação — CC art. 1.031 / CPC art. 606) e substituir ''AGO/tesouraria'' por Reunião de Sócios/quotas em sociedade (R-03 e R-05).',
          'material',
          'alto',
          'Revogar as disposições conflitantes das Cls. 5ª, 12ª e 14ª na 3ª Alteração Contratual, consolidando critério único de apuração de haveres (Balanço de Determinação, prazos e índice de atualização) e substituindo ''AGO'' e ''tesouraria'' por institutos próprios de sociedade limitada (R-03 e R-05).',
          'CC arts. 1.029, 1.031, 1.053, 1.071 e 1.072 (https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm, acesso em 26/11/2026); CPC (Lei nº 13.105/2015), arts. 604 e 606 (https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm, acesso em 26/11/2026); EC02 pp. 9 e 11–12.',
          'Advogado Societário + Sócios Rota Sul (apoio técnico PRISMA JRNA)',
          '20/10/2026 (R-03 e R-05 / 3ª Alteração Contratual)'
        ),
        (
          'inst:d2:06',
          'Cls. 7ª–11ª e Cl. 14ª § 1º Consolidação',
          'Quórum 50/50 sem desempate (deadlock), alçada, mandato (Cl. 11ª) e ilegalidade na Cl. 10ª (CC art. 1.061)',
          'Com quotas divididas 50%/50% (750.000 cada), as Cls. 7ª § 1º, 8ª § 1º, 10ª, 13ª e 14ª § 1º (EC02 pp. 10–12) exigem 51% ou maioria do capital — quórum matematicamente inalcançável sem consenso, inclusive para exclusão extrajudicial (Cl. 14ª § 1º). As Cls. 8ª–9ª conferem assinatura individual sem limite de alçada financeira; a Cl. 10ª admite administrador não sócio por 51%, violando o art. 1.061 do CC (com capital não integralizado exige aprovação de no mínimo 2/3 dos sócios); e a Cl. 11ª remete sócios administradores às obrigações de não sócios, gerando dúvida sobre o mandato de 3 anos da Cl. 10ª § 2º.',
          'EC02 pp. 10–12 (Anexo I)',
          'Inserir mecanismo de desempate/mediação, alçadas financeiras, prazo indeterminado para sócios administradores e adequar a Cl. 10ª ao art. 1.061 do CC (R-04).',
          'material',
          'alto',
          'Incluir cláusula de resolução de impasses (mediação/desempate), fixar alçada para assinatura conjunta acima de limite definido pelos sócios, adequar a Cl. 10ª ao art. 1.061 do CC (mínimo 2/3 dos sócios enquanto o capital não estiver integralizado) e explicitar mandato indeterminado na Cl. 11ª (R-04).',
          'CC arts. 1.010, 1.030, 1.061 (redação da Lei nº 14.451/2022), 1.063 § 1º e 1.085 (https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/lei/L14451.htm, acesso em 26/11/2026); EC02 pp. 10–12.',
          'Advogado Societário + Sócios Rota Sul',
          '20/10/2026 (R-04 / 3ª Alteração Contratual)'
        ),
        (
          'inst:d2:07',
          'Cl. 13ª §§ 1º–3º e Cl. 16ª Consolidação',
          'JCP no Simples, lucros desproporcionais/antecipados sem travas, pró-labore facultativo e bloqueio fiscal',
          'A Cl. 13ª § 1º (EC02 p. 11) prevê pagamento de juros sobre o capital próprio (TJLP), que não gera dedutibilidade no Simples Nacional e sofre IRRF de 15%; os §§ 2º–3º autorizam lucros desproporcionais e antecipações por balancetes sem condicionar à escrituração contábil regular nem à inexistência de débitos fiscais (considerando os débitos mar–ago/2026 informados nas respostas oficiais de 24/09 — pendência P-01 —, incide vedação da Lei 4.357/1964, art. 32, com multa de 50%). A Cl. 16ª (p. 12) trata o pró-labore como mera faculdade (''poderão''), expondo retiradas ao risco previdenciário (SC COSIT 120/2016).',
          'EC02 pp. 1, 11 e 12 + respostas 24/09 (P-01)',
          'Excluir previsão de JCP, condicionar distribuição à contabilidade regular e quitação/parcelamento fiscal, suspender lucros mar–ago/2026 e formalizar pró-labore (R-07 e R-09).',
          'material',
          'alto',
          'Suprimir a previsão de JCP e incluir salvaguardas de escrituração e regularidade fiscal na Cl. 13ª (3ª Alteração), manter suspensão expressa de distribuição de lucros até regularizar o período mar–ago/2026 (R-07) e formalizar ata/definição de pró-labore dos administradores com envio ao eSocial S-2300/S-1200 (R-09 / PR-15).',
          'Lei nº 9.249/1995, art. 9º; LC nº 123/2006, art. 14 § 2º; Lei nº 4.357/1964, art. 32 (https://www.planalto.gov.br/ccivil_03/leis/l4357.htm, acesso em 26/11/2026); Lei nº 8.212/1991, art. 12, V, ''f''; SC COSIT nº 120/2016; EC02 pp. 11–12.',
          'PRISMA JRNA + Sócios Rota Sul (apoio Advogado Societário)',
          '05/10/2026 (pró-labore R-09) e 30/10/2026 (regularização fiscal R-07)'
        ),
        (
          'inst:d2:08',
          'Cl. 15ª Consolidação',
          'Quórum de 3/4 na Cl. 15ª citando redação revogada do art. 1.076 do CC (Lei 14.451/2022)',
          'A Cl. 15ª (EC02 p. 12) exige concordância de 3/4 do capital ''conforme artigos 1.071/1.076 do CC/2002'', inclusive para escolha do liquidante. Embora o contrato possa estipular quórum superior, o dispositivo reproduz o antigo inciso I do art. 1.076 revogado pela Lei nº 14.451/2022 (mínimo legal passou a ser mais da metade do capital social para reforma contratual, fusão, incorporação e dissolução, e maioria dos presentes/capital conforme o caso para liquidante).',
          'EC02 p. 12 (Cl. 15ª)',
          'Atualizar a remissão legal da Cl. 15ª ao art. 1.076 do CC (Lei 14.451/2022) e definir explicitamente o quórum desejado pelos sócios (considerando o quadro 50/50) na 3ª Alteração (R-04).',
          'material',
          'medio',
          'Atualizar a Cl. 15ª na 3ª Alteração Contratual para refletir o art. 1.076, II e III, do CC (redação da Lei nº 14.451/2022 — maioria absoluta como piso legal), separando a escolha do liquidante e definindo se os sócios mantêm quórum qualificado contratual ou adotam a regra legal (R-04).',
          'CC art. 1.071 e art. 1.076, II e III, com redação da Lei nº 14.451/2022 (https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/lei/L14451.htm, acesso em 26/11/2026); EC02 p. 12.',
          'Advogado Societário + Sócios Rota Sul',
          '20/10/2026 (R-04 / 3ª Alteração Contratual)'
        ),
        (
          'inst:d2:09',
          'Cl. 18ª Consolidação',
          'Regência supletiva contraditória (Sociedade Simples + S.A. simultaneamente)',
          'A Cl. 18ª (EC02 p. 12) determina que, na omissão das regras da limitada (arts. 1.052 a 1.087 do CC), aplicar-se-á ''o disposto pelas normas da Sociedade Simples conjuntamente com as normas da Sociedade Anônima''. A cumulação simultânea cria antinomia normativa frente ao art. 1.053, parágrafo único, do CC, que faculta eleger a regência supletiva da Lei das S.A. (Lei nº 6.404/1976) em lugar da regra geral da Sociedade Simples.',
          'EC02 p. 12 (Cl. 18ª)',
          'Definir regência supletiva única e clara (Sociedade Simples como regra geral ou opção expressa pela Lei nº 6.404/1976) na 3ª Alteração Contratual (R-05).',
          'material',
          'medio',
          'Redigir a Cl. 18ª na 3ª Alteração Contratual com regência supletiva única e inequívoca — recomendando as normas da Sociedade Simples para sociedade limitada familiar fechada, ou opção exclusiva pela Lei nº 6.404/1976 se desejado pelos sócios (R-05).',
          'CC (Lei nº 10.406/2002), art. 1.053, caput e parágrafo único (https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm, acesso em 26/11/2026); EC02 p. 12.',
          'Advogado Societário + Sócios Rota Sul',
          '20/10/2026 (R-05 / 3ª Alteração Contratual)'
        )
    ) AS v(
      chave, numero_clausula, titulo, regra_texto, referencia_v1_original, apontamento_auditoria,
      risco_tipo, risco_nivel, providencia, fundamento_legal, responsavel, prazo_texto
    )
   WHERE cl.empresa_id = 1
     AND cl.chave = v.chave
     AND cl.origem_registro = 'importado_rascunho_v2';

  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 9 THEN RAISE EXCEPTION 'Cláusulas atualizadas: % (esperado 9)', n; END IF;

  -- 3. Pós-condição: 9 linhas com os 6 campos do P1 preenchidos e sem número solto legado
  SELECT count(*) INTO n
    FROM erp.instrumento_societario_clausula
   WHERE empresa_id = 1
     AND chave IN ('inst:d2:01','inst:d2:02','inst:d2:03','inst:d2:04','inst:d2:05','inst:d2:06','inst:d2:07','inst:d2:08','inst:d2:09')
     AND risco_tipo IN ('formal', 'material')
     AND risco_nivel IN ('baixo', 'medio', 'alto', 'critico')
     AND coalesce(trim(providencia), '') <> ''
     AND coalesce(trim(fundamento_legal), '') <> ''
     AND coalesce(trim(responsavel), '') <> ''
     AND coalesce(trim(prazo_texto), '') <> ''
     AND strpos(regra_texto, '917,40') = 0
     AND strpos(coalesce(providencia, ''), '917,40') = 0;
  IF n <> 9 THEN RAISE EXCEPTION 'Pós-condição da Estação 2 falhou (% de 9)', n; END IF;
END
$a$;

SELECT ordem, chave, numero_clausula, risco_tipo, risco_nivel, responsavel, prazo_texto, status_validacao
  FROM erp.instrumento_societario_clausula
 WHERE empresa_id = 1
 ORDER BY ordem;
