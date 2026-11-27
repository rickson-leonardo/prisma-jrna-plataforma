-- Dossiê 2, etapa 3 (Estação 8 — Departamento Pessoal): Docs 06 a 10, 10 eventos do eSocial e 2 contratos de trabalho.
-- Achados DP-01 a DP-09 (REVISAO_D2_ROTA_SUL.md). Decisão DP-01: manter os dados pessoais fictícios declarados (PR-18),
-- tratados como informados verbalmente pelos sócios; documentos comprobatórios a coletar e conferir (DP-02, DOC-09).
-- Fontes: Estudo de Caso 02 (EC02), aula de DP (AULA) e normas citadas. Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
  c_cct constant text := 'CCT SECEG × SINDILOJAS-GO — Termo Aditivo 2026/2027, cl. 3ª, 6ª e 11ª (aula de DP, p. 29; premissa didática, p. 21)';
BEGIN
  -- 0. Estado esperado
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND dossie = 'D2' AND status_validacao = 'pendente_revisao'
     AND documento IN ('d2_06_prontuario', 'd2_07_ficha_e1', 'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2');
  IF n <> 27 THEN RAISE EXCEPTION 'Seções dos Docs 06–10 fora do estado esperado (% de 27)', n; END IF;
  SELECT count(*) INTO n FROM erp.esocial_evento WHERE empresa_id = 1 AND status_validacao <> 'homologado_contadora';
  IF n <> 10 THEN RAISE EXCEPTION 'Eventos eSocial fora do estado esperado (% de 10)', n; END IF;
  SELECT count(*) INTO n FROM erp.contrato_trabalho WHERE empresa_id = 1 AND status_validacao <> 'homologado_contadora';
  IF n <> 2 THEN RAISE EXCEPTION 'Contratos de trabalho fora do estado esperado (% de 2)', n; END IF;
  SELECT count(*) INTO n FROM erp.diligencia_item WHERE empresa_id = 1 AND codigo = 'DOC-09' AND status_item = 'concluido';
  IF n <> 1 THEN RAISE EXCEPTION 'DOC-09 fora do estado esperado'; END IF;

  -- 1. Contratos de trabalho (DP-02, DP-07): referência da CCT com fonte; documentos civis a coletar e conferir
  UPDATE erp.contrato_trabalho c SET cct_referencia = c_cct, docs_admissionais_json = v.docs::jsonb, atualizado_em = now()
  FROM (VALUES
    ('E1', $j$[
      {"documento": "RG e CPF", "status": "A coletar e conferir", "observacao": "Dados informados verbalmente pelos sócios (fictícios — PR-18); EC02, p. 3: documentos de admissão a apurar (DOC-09)"},
      {"documento": "Comprovante de residência", "status": "A coletar e conferir", "observacao": "DOC-09"},
      {"documento": "Certidão de nascimento e CPF do filho (6 anos)", "status": "A coletar e conferir", "observacao": "Lastro do dependente para IRRF e salário-família (DOC-09)"}
    ]$j$),
    ('E2', $j$[
      {"documento": "RG e CPF", "status": "A coletar e conferir", "observacao": "Dados informados verbalmente pelos sócios (fictícios — PR-18); EC02, p. 3 (DOC-09)"},
      {"documento": "Comprovante de residência", "status": "A coletar e conferir", "observacao": "DOC-09"}
    ]$j$)
  ) AS v(cod, docs)
  WHERE c.empresa_id = 1 AND c.codigo_empregado = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Contratos: % (esperado 2)', n; END IF;

  -- 2. DOC-09 reaberto (DP-02): documentos de admissão são pendência real do caso
  UPDATE erp.diligencia_item SET status_item = 'em_saneamento', atualizado_em = now(),
    enunciado = 'Documentos civis admissionais de E1 e E2 (RG, CPF, comprovante de residência; certidão e CPF do filho de E1)',
    resposta_literal = 'Dados pessoais informados verbalmente pelos sócios e usados nas fichas e contratos (fictícios para fins didáticos — PR-18); documentos comprobatórios a coletar e conferir.',
    fonte_evidencia = 'EC02, p. 3 ("Informações a apurar: … documentos de admissão"); aula de DP, p. 23',
    justificativa_contadora = 'Reaberto em 27/11/2026 (achado DP-02): o caso lista os documentos de admissão entre as informações a apurar; o item fica em saneamento até a conferência dos documentos.'
   WHERE empresa_id = 1 AND codigo = 'DOC-09';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'DOC-09: %', n; END IF;

  -- 3. Eventos do eSocial (DP-04, DP-05, DP-06): nomes corretos, sem valores digitados, status real
  UPDATE erp.esocial_evento e SET nome_evento = coalesce(v.nome, e.nome_evento), prazo_legal = coalesce(v.prazo, e.prazo_legal),
         status_envio = coalesce(v.st, e.status_envio), observacao = coalesce(v.obs, e.observacao), atualizado_em = now()
  FROM (VALUES
    (3, 'Admissão do trabalhador — E1 Mariana Alves Costa (16/09/2026)', NULL, NULL, NULL),
    (4, 'Admissão do trabalhador — E2 Rafael Souza Lima (21/09/2026)', NULL, NULL, NULL),
    (5, NULL, 'Até o dia 15 do mês seguinte ao do exame (ASO não realizado — PEND-01)', NULL, NULL),
    (6, NULL, 'Até o dia 15 do mês seguinte ao do exame (ASO não realizado — PEND-01)', NULL, NULL),
    (7, NULL, NULL, NULL, 'Depende do inventário de riscos (PGR, ou DIR para ME/EPP — NR-1, item 1.8.4) (PEND-07). Sem agente nocivo nas funções administrativa e de vendas, informar ausência (código 09.01.001); LTCAT só se houver agente nocivo.'),
    (9, 'Remuneração do trabalhador no RGPS — folha 09/2026 (E1 e E2)', NULL, 'aguardando_insumo', 'Valores da folha do doc. 11 (motor de cálculo, etapa 4); transmissão depende da folha homologada e do e-CNPJ (DOC-04).'),
    (10, 'Fechamento dos eventos periódicos 09/2026 → DCTFWeb e FGTS Digital', NULL, 'aguardando_insumo', 'Gera o débito na DCTFWeb e a guia do FGTS Digital (vencimento 20/10/2026); valores no doc. 11 (etapa 4).')
  ) AS v(ordem, nome, prazo, st, obs)
  WHERE e.empresa_id = 1 AND e.ordem = v.ordem;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 7 THEN RAISE EXCEPTION 'Eventos: % (esperado 7)', n; END IF;

  -- 4. Registro da CCT sem fonte (DP-07) nos Docs 06–10
  UPDATE erp.documento_secao SET conteudo_md = regexp_replace(conteudo_md, '(CCT 2025/2027 — )?(Registro MTE )?\*{0,2}`SRT00189/2025`\*{0,2} \+ ', '', 'g'), atualizado_em = now()
   WHERE empresa_id = 1 AND documento IN ('d2_06_prontuario', 'd2_07_ficha_e1', 'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2')
     AND strpos(conteudo_md, 'SRT00189') > 0 AND codigo_secao <> '3_confronto_de_cbo_piso_salarial';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 5 THEN RAISE EXCEPTION 'Registro da CCT: % seções (esperado 5)', n; END IF;

  -- 5. Fichas (DP-02): declaração dos dados fictícios e documentos a conferir; VT com 2 conduções/dia (DP-03)
  UPDATE erp.documento_secao SET conteudo_md = replace(replace(replace(conteudo_md,
      '> Dados pessoais fictícios, criados para fins didáticos (`PR-18`).',
      '> Dados pessoais fictícios para fins didáticos (`PR-18`), tratados como informados verbalmente pelos sócios (EC02, p. 2); documentos comprobatórios a coletar e conferir (`DOC-09`).'),
      '| Vale-transporte | Optante — desconto limitado a 6% do salário básico (`PR-08`) |',
      '| Vale-transporte | Optante — 2 conduções/dia (EC02, p. 3); desconto limitado a 6% do salário básico (`PR-08`) |'),
      '| Vale-transporte | Optante — desconto limitado a 6% do salário básico, sem comissões (`PR-08`) |',
      '| Vale-transporte | Optante — 2 conduções/dia (EC02, p. 3); desconto limitado a 6% do salário básico, sem comissões (`PR-08`) |'),
    atualizado_em = now()
   WHERE empresa_id = 1 AND documento IN ('d2_07_ficha_e1', 'd2_09_ficha_e2') AND codigo_secao = 'iii_contrato_de_trabalho'
     AND strpos(conteudo_md, '> Dados pessoais fictícios, criados para fins didáticos') > 0 AND strpos(conteudo_md, '| Vale-transporte | Optante — desconto') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Fichas: % (esperado 2)', n; END IF;

  -- 6. Doc 06, seção 4 (DP-02): documentos do dependente a apresentar
  UPDATE erp.documento_secao SET conteudo_md = replace(replace(conteudo_md,
      '(certidão de nascimento, CPF, caderneta de vacinação e comprovante escolar entregues — `DOC-09`)',
      '(certidão de nascimento e CPF do dependente a apresentar — `DOC-09`)'),
      '**Portaria Interministerial MPS/MF nº 13/2026** (cota R$ 67,54 até R$ 1.980,38)',
      '**Portaria Interministerial MPS/MF nº 13/2026** (cota R$ 67,54 para remuneração até R$ 1.980,38 — aula de DP, p. 24)'),
    atualizado_em = now()
   WHERE empresa_id = 1 AND documento = 'd2_06_prontuario' AND codigo_secao = '4_declaracoes_de_dependentes_irr'
     AND strpos(conteudo_md, 'comprovante escolar entregues') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Doc 06, seção 4: %', n; END IF;

  -- 7. Doc 06, seção 6: razão social completa
  UPDATE erp.documento_secao SET conteudo_md = replace(conteudo_md, '**Rota Sul Importadora Ltda.**', '**Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda.**'), atualizado_em = now()
   WHERE empresa_id = 1 AND documento = 'd2_06_prontuario' AND codigo_secao = '6_modelos_de_termo_de_prorrogaca'
     AND strpos(conteudo_md, '**Rota Sul Importadora Ltda.**') > 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Doc 06, seção 6: %', n; END IF;

  -- 8. Doc 06, seções 1, 2, 3 e 5 reescritas (DP-03, DP-04, DP-06, DP-07): sem valores digitados; quadros saem do banco
  UPDATE erp.documento_secao s SET conteudo_md = v.txt, atualizado_em = now()
  FROM (VALUES
    ('1_sub_indices_individuais_dos_pr', $t$### 1.1 Prontuário — Empregado 1: Mariana Alves Costa (Auxiliar Administrativo — CBO `4110-05` | Adm.: `16/09/2026`)
| Item | Documento | Status real | Referência |
|---|---|---|---|
| 01 | Ficha de registro de empregado | **Elaborada** *(dados pessoais fictícios — `PR-18`; conferência documental pendente)* | doc. 07 |
| 02 | Contrato de experiência (45 + 45 dias) | **Elaborado** *(jornada literal do caso, intervalo de 1h48; diferença 41h × 44h tratada na `PR-11` / `PEND-04`)* | doc. 08 |
| 03 | Termo de prorrogação (31/10 a 14/12/2026) | **Modelo disponível** *(assinar até 30/10/2026 — CLT, art. 451)* | Seção 6.1 |
| 04 | Exame médico admissional (ASO — NR-7) | **Pendente crítico** *(não realizado antes da admissão)* | `PEND-01` |
| 05 | Documentos civis (RG, CPF, comprovante de residência; certidão e CPF do filho) | **A coletar e conferir** | `DOC-09` |
| 06 | Declaração de dependentes (IRRF e salário-família) | **Minuta pronta** *(1 filho, 6 anos; salário-família não elegível)* | Seção 4.1 |
| 07 | Termo de opção de vale-transporte | **Minuta pronta** *(optante; 2 conduções/dia; desconto limitado a 6% do salário básico)* | Seção 5.1 |
| 08 | Termo de vale-refeição | **Minuta pronta** *(R$ 30,00 por dia trabalhado — EC02, p. 3)* | Seção 5.3 |
| 09 | Contribuição negocial (Termo Aditivo 2026/2027, cl. 11ª) | **Sem oposição documentada** *(cenário A; cenário B no doc. 11)* | `PR-10` / doc. 11 |
| 10 | Eventos do eSocial e CTPS Digital | **Roteiro na Tabela 2** *(sem recibos inventados)* | Seção 2 |

### 1.2 Prontuário — Empregado 2: Rafael Souza Lima (Vendedor interno — CBO `5211-10` | Adm.: `21/09/2026`)
| Item | Documento | Status real | Referência |
|---|---|---|---|
| 01 | Ficha de registro de empregado | **Elaborada** *(dados pessoais fictícios — `PR-18`; conferência documental pendente)* | doc. 09 |
| 02 | Contrato de experiência (30 + 60 dias) | **Elaborado** *(comissão de 1,5% + DSR em rubrica destacada; estorno restrito — Lei nº 3.207/1957, art. 7º)* | doc. 10 |
| 03 | Termo de prorrogação (21/10 a 19/12/2026) | **Modelo disponível** *(assinar até 20/10/2026 — CLT, art. 451)* | Seção 6.2 |
| 04 | Exame médico admissional (ASO — NR-7) | **Pendente crítico** *(não realizado antes da admissão)* | `PEND-01` |
| 05 | Documentos civis (RG, CPF, comprovante de residência) | **A coletar e conferir** | `DOC-09` |
| 06 | Declaração de dependentes (IRRF e salário-família) | **Minuta pronta** *(nenhum dependente)* | Seção 4.2 |
| 07 | Termo de opção de vale-transporte | **Minuta pronta** *(optante; 2 conduções/dia; 6% do salário básico, sem comissões; base limitada pela CCT)* | Seção 5.2 |
| 08 | Vale-refeição | **Não concedido** *(EC02, p. 3)* | — |
| 09 | Contribuição negocial (Termo Aditivo 2026/2027, cl. 11ª) | **Sem oposição documentada** *(cenário A; cenário B no doc. 11)* | `PR-10` / doc. 11 |
| 10 | Eventos do eSocial e CTPS Digital | **Roteiro na Tabela 2** *(sem recibos inventados)* | Seção 2 |

> **Regra de conduta sindical (Termo Aditivo 2026/2027, cl. 11ª; STF, Tema 935 — aula de DP, p. 29):** a empregadora **não deve induzir nem fornecer modelo de carta de oposição** à contribuição negocial. Se o empregado apresentar oposição protocolada no sindicato, aplica-se o cenário B do doc. 11.$t$),
    ('2_roteiro_completo_de_eventos_do', $t$> **Nota de integridade (aula de DP, p. 23):** *documento ≠ evento.* Nenhum número de recibo ou protocolo do eSocial foi inventado: a transmissão depende do certificado digital e-CNPJ (`DOC-04`), do ASO (`DOC-10`) e do inventário de riscos (`DOC-11`).

Os eventos do eSocial (leiaute S-1.3) estão na **Tabela 2** acima, gerada pela plataforma a partir do registro de eventos, com prazo legal, status real de envio e recibo (só quando transmitido). Complementos:
- **S-2190 (registro preliminar):** alternativa quando os dados completos do S-2200 não estiverem disponíveis até o dia anterior ao início das atividades (aula de DP, p. 23).
- **CTPS Digital:** não há anotação manual; admissão, cargo, CBO e salário aparecem para o empregado a partir do S-2200 processado (CLT, art. 29, com redação da Lei nº 13.874/2019).
- **Remuneração e fechamento (S-1200 e S-1299):** os valores saem da folha do doc. 11 (motor de cálculo) e só são transmitidos com a folha homologada e o e-CNPJ; o S-1299 gera o débito na DCTFWeb e a guia do FGTS Digital, com vencimento em 20/10/2026.$t$),
    ('3_confronto_de_cbo_piso_salarial', $t$- **Instrumento coletivo:** CCT SECEG × SINDILOJAS-GO, Termo Aditivo 2026/2027, cláusulas 3ª, 6ª e 11ª (aula de DP, p. 29). Enquadramento adotado como premissa didática; no caso real, confirmar a atividade preponderante e o sindicato patronal (aula de DP, p. 21; `PR-03` em doc. 14).
- **Empregado 1 (Auxiliar Administrativo — CBO `4110-05`):** salário contratual R$ 2.400,00 ≥ piso geral R$ 1.722,25 (vigente desde 01/04/2026 — cl. 3ª) → **conforme**.
- **Empregado 2 (Vendedor interno — CBO `5211-10`):** fixo contratual R$ 1.900,00 ≥ garantia mínima do vendedor em Goiânia R$ 1.863,00 (cl. 3ª e 6ª) → **conforme**. O confronto da remuneração proporcional de setembro (fixo + comissão + DSR) com a garantia proporcional está no doc. 11 (motor da folha).
- **CBO:** códigos informados pelos sócios como "a confirmar" (EC02, p. 2); a conferência no portal da CBO (MTE) fica registrada no doc. 14.$t$),
    ('5_termos_de_opcao_de_vale_transp', $t$> **Premissa de quantidade (`PR-08` em doc. 14):** 2 conduções por dia (EC02, p. 3; aula de DP, p. 24: "VT: 2 viagens/dia"). A tarifa e os valores do mês saem da folha do doc. 11 (motor de cálculo).

### 5.1 Termo de opção de VT — Mariana Alves Costa (Lei nº 7.418/1985)
- **[X] OPTANTE** — 2 conduções por dia trabalhado, no trajeto residência–trabalho–residência. Autorizo o desconto de até **6% do salário básico** (Lei nº 7.418/1985, art. 4º, parágrafo único; Decreto nº 10.854/2021), cabendo à empregadora a parcela que exceder esse limite. Comprometo-me a informar mudança de endereço ou de meio de transporte.

Goiânia-GO, ____/____/2026 — Assinatura: __________________________________ (Mariana Alves Costa)

### 5.2 Termo de opção de VT — Rafael Souza Lima (Lei nº 7.418/1985 e Termo Aditivo 2026/2027, cl. 6ª)
- **[X] OPTANTE** — 2 conduções por dia trabalhado, no trajeto residência–trabalho–residência. Autorizo o desconto de até **6% do salário básico, excluídas as comissões**; no salário misto, a base fica limitada a **R$ 2.257,50** (Termo Aditivo 2026/2027, cl. 6ª — aula de DP, p. 29), cabendo à empregadora a parcela que exceder esse limite. Comprometo-me a informar mudança de endereço ou de meio de transporte.

Goiânia-GO, ____/____/2026 — Assinatura: __________________________________ (Rafael Souza Lima)

### 5.3 Termo de vale-refeição — Mariana Alves Costa
- **[X] BENEFICIÁRIA** — **R$ 30,00 por dia trabalhado** (EC02, p. 3). A incidência de encargos segue o instrumento que institui o benefício (PAT — Lei nº 6.321/1976 — ou CCT) e é tratada na folha (doc. 11; aula de DP, p. 27). *(Empregado 2 sem vale-refeição — EC02, p. 3.)*

Goiânia-GO, ____/____/2026 — Assinatura: __________________________________ (Mariana Alves Costa)$t$)
  ) AS v(cod, txt)
  WHERE s.empresa_id = 1 AND s.documento = 'd2_06_prontuario' AND s.codigo_secao = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Doc 06, seções 1/2/3/5: % (esperado 4)', n; END IF;

  -- 9. Pós-condições: nenhum resto de legado nos Docs 06–10, nos eventos e nos contratos
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1
     AND documento IN ('d2_06_prontuario', 'd2_07_ficha_e1', 'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2')
     AND (strpos(conteudo_md, 'SRT00189') > 0 OR strpos(conteudo_md, '4 passagens') > 0 OR strpos(conteudo_md, '17,20') > 0
          OR strpos(conteudo_md, 'Recebidos') > 0 OR strpos(conteudo_md, 'entregues — `DOC-09`') > 0
          OR conteudo_md ~ '(189,20|154,80|117,20|116,80|39,96|54,39|330,00|2\.833,33|212,68|226,67|1\.633,33|621,00|677,75)');
  IF n <> 0 THEN RAISE EXCEPTION 'Seções dos Docs 06–10 com legado: %', n; END IF;
  SELECT count(*) INTO n FROM erp.esocial_evento WHERE empresa_id = 1
     AND (status_envio = 'pronto_envio' OR nome_evento ~ '(R\$|Cadastramento)' OR observacao ~ 'R\$' OR strpos(observacao, 'requer PGR/DIR, PCMSO e LTCAT') > 0);
  IF n <> 0 THEN RAISE EXCEPTION 'Eventos com legado: %', n; END IF;
  SELECT count(*) INTO n FROM erp.contrato_trabalho WHERE empresa_id = 1
     AND (strpos(cct_referencia, 'SRT') > 0 OR jsonb_typeof(docs_admissionais_json -> 0) <> 'object');
  IF n <> 0 THEN RAISE EXCEPTION 'Contratos com legado: %', n; END IF;

  -- 10. Homologação: 2 contratos, 10 eventos e 27 seções
  UPDATE erp.contrato_trabalho SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Contrato conferido (27/11/2026) com o EC02, pp. 2–3 (cargo, CBO, admissão, salário, jornada, experiência, VT, VR, dependentes) e a aula de DP, p. 29 (CCT). Dados pessoais fictícios declarados (PR-18); documentos civis e ASO seguem como pendência real (DOC-09, PEND-01).'
   WHERE empresa_id = 1 AND status_validacao <> 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'Contratos homologados: % (esperado 2)', n; END IF;

  UPDATE erp.esocial_evento SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Evento conferido (27/11/2026): nome, prazo legal e status real de envio; nenhum recibo inventado (aula de DP, p. 23). Homologar valida o registro; o status de envio segue retratando o caso.'
   WHERE empresa_id = 1 AND status_validacao <> 'homologado_contadora';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 10 THEN RAISE EXCEPTION 'Eventos homologados: % (esperado 10)', n; END IF;

  UPDATE erp.documento_secao SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Docs 06–10 revisados (27/11/2026, achados DP-01 a DP-09): dados do caso (EC02, pp. 2–3), CCT com fonte (aula de DP, p. 29), 2 conduções/dia, sem valores digitados (folha no doc. 11), documentos civis e ASO como pendência real; dados pessoais fictícios declarados (PR-18).'
   WHERE empresa_id = 1 AND status_validacao = 'pendente_revisao'
     AND documento IN ('d2_06_prontuario', 'd2_07_ficha_e1', 'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2');
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 27 THEN RAISE EXCEPTION 'Seções homologadas: % (esperado 27)', n; END IF;
END
$a$;

SELECT 'contratos' AS item, count(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados, count(*) AS total FROM erp.contrato_trabalho WHERE empresa_id = 1
UNION ALL SELECT 'eventos eSocial', count(*) FILTER (WHERE status_validacao = 'homologado_contadora'), count(*) FROM erp.esocial_evento WHERE empresa_id = 1
UNION ALL SELECT 'seções Docs 06–10', count(*) FILTER (WHERE status_validacao = 'homologado_contadora'), count(*) FROM erp.documento_secao
  WHERE empresa_id = 1 AND documento IN ('d2_06_prontuario', 'd2_07_ficha_e1', 'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2');
