-- Dossiê 2: autoavaliação V2 dos 48 elementos da régua (devolutiva G07, "Para chegar ao 4"), opção A aprovada em 27/11/2026.
-- Nota V2 = autoavaliação da dupla sobre os documentos gerados pela plataforma (não é nota oficial). nota_v1 (devolutiva) não muda.
-- Nota 3 onde há lacuna conhecida: C-12 (resposta do advogado não localizada) e C-40 (registro da CCT não localizado no Mediador).
-- Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM auditoria.avaliacao_conformidade WHERE dossie = 'D2' AND nota IS NULL AND status_validacao = 'pendente_revisao';
  IF n <> 48 THEN RAISE EXCEPTION 'Avaliações fora do estado esperado (% de 48)', n; END IF;

  UPDATE auditoria.avaliacao_conformidade av SET nota = v.nota, referencia_localizacao = v.ref, justificativa_sustentacao = v.just,
         status_validacao = 'homologado_contadora', atualizado_em = now()
  FROM auditoria.criterio_conformidade c, (VALUES
    ('C-01', 4, 'Doc. 01 §3.1–3.2; PR-02', 'Objeto, 18 CNAEs da matriz × 17 da filial, importação de motocicletas frente ao art. 17, VIII da LC 123/2006 e denominação analisados; filial com objeto restrito à importação de pneus (G-02).'),
    ('C-02', 4, 'Doc. 01 §3.4; diretrizes R-03, R-04, R-05 e R-09', 'Administração, quórum 50/50 e impasse, três critérios de haveres, AGO/tesouraria em Ltda. e pró-labore/JCP analisados, com a retirada informal informada pelo cliente (G-09).'),
    ('C-03', 4, 'Doc. 01 §4–§5; diretrizes R-01 a R-09', 'Plano de saneamento da 3ª Alteração com providência, responsável, prazo, risco e fundamento legal por achado.'),
    ('C-04', 4, 'Doc. 01 §1 e §3.1', 'Matriz (Goiânia) e filial (Itajaí) com CNPJ, NIRE, endereço e dados do contrato; "Sala 223 × 223 A 32" e "Distribuidora × Distribuição" apontados.'),
    ('C-05', 4, 'Doc. 01 sumário, §3 e §4', 'Relatório com sumário, classificação formal × material e referência ao dispositivo do Anexo I em cada apontamento.'),
    ('C-06', 4, 'Doc. 01 §2, §3.3, §4 (R-02) e §5', 'Divergência de datas (31/07/2026 × 31/07/2025, errata reconhecida pelo cliente — Q5 e G-01), R$ 500.000,00 não integralizados e mora (CC, arts. 1.004 e 1.058).'),
    ('C-07', 4, 'Doc. 03', 'Contrato com partes qualificadas, objeto, prazo, obrigações, rescisão, foro e dados completos da contratada (CNPJ 48.123.456/0001-90, CRC-DF 004.821/O-2), sem campos em branco; Res. CFC nº 1.590/2020.'),
    ('C-08', 4, 'Doc. 02 §3 (memória de custo)', 'Honorários de implantação, recuperação, mensais e 13º calculados pela plataforma (horas por frente × valor-hora, PR-20), coerentes com o escopo do caso.'),
    ('C-09', 4, 'Doc. 03 (cláusulas e Anexo I — procuração)', 'Responsabilidades de cada parte, LGPD e procuração com poderes definidos.'),
    ('C-10', 4, 'Doc. 04 §5 e assinatura', 'Termo de RT com rol de pendências e riscos do onboarding e assinatura da RT (Nathalia Peres Araujo, CRC-DF 025.431/O-7).'),
    ('C-11', 4, 'Docs. 02 a 04', 'Proposta, contrato e termo coerentes entre si e com a Rota Sul (valores pelos mesmos marcadores; datas pela PR-19).'),
    ('C-12', 3, 'Doc. 05 (perguntas e respostas)', 'Respostas do cliente (carta, p. 3, e grupo da disciplina) e do contador anterior registradas com a origem; a resposta do advogado não foi localizada (Q9) — lacuna declarada.'),
    ('C-13', 4, 'Doc. 05 (pendências PEND-01 a PEND-08)', 'Quadro de pendências com risco, responsável, prazo, providência e origem.'),
    ('C-14', 4, 'Doc. 05 (checklist DOC-01 a DOC-13)', 'Checklist por pessoa e tema com documento, finalidade, responsável, prazo e status real.'),
    ('C-15', 4, 'Doc. 05 (Q1 a Q9)', 'Perguntas objetivas sobre capital e prazo, regime tributário, RADAR, ponto e DSR, ASO, contador anterior e advogado; CCT perguntada no grupo (G-11).'),
    ('C-16', 4, 'Doc. 06 §1 e Tabela 1', 'Prontuário de E1 e E2 com índice e status real de cada peça.'),
    ('C-17', 4, 'Doc. 06 §3; Docs. 07 a 10', 'CBO, piso e garantia confrontados com a CCT, com cláusula (Termo Aditivo 2026/2027, cl. 3ª e 6ª) e fonte (aula de DP, p. 29; PR-03).'),
    ('C-18', 4, 'Doc. 06 §4–§5', 'Declarações de dependentes, termos de opção de VT (2 conduções/dia) e de VR.'),
    ('C-19', 4, 'Doc. 06 §2 e Tabela 2', 'Roteiro do eSocial de S-1000 a S-1299, S-2220, S-2240 e S-2300, e CTPS Digital, sem recibo inventado.'),
    ('C-20', 4, 'Docs. 07 e 09', 'Fichas com os dados do caso (cargo, CBO, salário, jornada, admissões em 16/09 e 21/09/2026); dados pessoais fictícios declarados (PR-18) e documentos a conferir (DOC-09).'),
    ('C-21', 4, 'Docs. 08 e 10; Doc. 06 §6', 'Contratos de experiência de 45 + 45 e 30 + 60 dias coerentes, com termos de prorrogação; jornada literal do E1 (PR-11).'),
    ('C-22', 4, 'Docs. 06, 07 e 09; AUD-01 e AUD-03', 'ASO e documentos de admissão tratados como pendência real.'),
    ('C-23', 4, 'Doc. 11 (rubricas COMISSAO e DSR-COM)', 'Comissão sobre R$ 60.000,00 e DSR destacado calculados pelo motor (premissa da aula, p. 25).'),
    ('C-24', 4, 'Planilha do doc. 11', 'Planilha com fórmulas ligadas aos parâmetros e à memória de cálculo, gerada pela plataforma; tabela de rubricas com a coluna Fórmula.'),
    ('C-25', 4, 'Doc. 11 (SAL-FAMILIA); Doc. 06 §3', 'Salário-família analisado (zero pela remuneração do mês — portaria, art. 4º, § 2º) e piso/garantia da CCT confrontados.'),
    ('C-26', 4, 'Doc. 11 (VT-DESC, VR, NEGOCIAL)', 'VT limitado a 6%, VR por dia trabalhado e contribuição negocial nos cenários A e B, com premissas declaradas (PR-08 a PR-10).'),
    ('C-27', 4, 'Doc. 11 (INSS-RET)', 'INSS por faixas conferido pelo motor e pelo recálculo independente.'),
    ('C-28', 4, 'Doc. 11 (IRRF e FGTS-8)', 'IRRF zero (desconto simplificado e redução da Lei nº 15.270/2025) e FGTS de 8% de E1 e E2.'),
    ('C-29', 4, 'Doc. 12 §2; lote L4', 'Provisões de 13º, férias e 1/3 só para quem completou o avo (E1), com FGTS; E2 sem avo.'),
    ('C-30', 4, 'Doc. 12 (partidas L1 a L4)', 'Lançamentos de integração em partidas dobradas, com histórico e contas, gerados pelo motor.'),
    ('C-31', 4, 'Doc. 12 (conciliação)', 'Conciliação folha × lançamentos rubrica a rubrica com diferença zero.'),
    ('C-32', 4, 'Doc. 12 §1 e §5', 'Encargos no Simples (CPP no DAS; FGTS à parte); a exclusão do Simples aparece só como sensibilidade.'),
    ('C-33', 4, 'Doc. 12 §1 e recibos', 'Resumo com bruto, descontos, líquido, FGTS e totais pelos marcadores do motor; recibos gerados das rubricas.'),
    ('C-34', 4, 'Doc. 13 PT-03 e Tabela 2', 'Recálculo independente de 100% das rubricas comparado com o motor e a planilha.'),
    ('C-35', 4, 'Doc. 13 PT-01', 'Plano de auditoria com risco, escopo, materialidade, critérios e procedimentos.'),
    ('C-36', 4, 'Doc. 13 PT-04', 'Conferência de INSS × DCTFWeb, FGTS × FGTS Digital, CPP no DAS e eventos do eSocial.'),
    ('C-37', 4, 'Doc. 13 PT-02', 'Testes cadastrais e documentais com evidência, sem atestar como conforme o que não existe (ASO, documentos, recibos).'),
    ('C-38', 4, 'Doc. 13 PT-05 e Tabela 3', 'Achados do cliente (AUD-01 a AUD-08) com evidência, risco, valor envolvido e documento de origem.'),
    ('C-39', 4, 'Doc. 13 Tabela 3', 'Correção proposta por achado, com responsável, prazo e valor.'),
    ('C-40', 3, 'Doc. 14 Tabela 3; PR-03 a PR-06', 'Tabelas oficiais com norma, link e data de consulta; CCT com cláusulas e fonte (aula de DP), mas sem número de registro, não localizado no Mediador (PR-03) — lacuna declarada.'),
    ('C-41', 4, 'Doc. 14 Tabela 2', 'Decisões e pendências de cada premissa com quem decide e até quando.'),
    ('C-42', 4, 'Doc. 14 Tabela 1', 'Registro numerado PR-01 a PR-20 com decisão, motivo e impacto.'),
    ('C-43', 4, 'Doc. 14 Tabela 1', 'Fonte oficial com link e data de acesso para cada premissa.'),
    ('C-44', 4, 'Doc. 15 §1 e Tabela 1', 'Finalidade do uso de IA declarada por etapa e por entregável.'),
    ('C-45', 4, 'Doc. 15 §2', 'Ferramentas e comandos resumidos, sem dados pessoais reais.'),
    ('C-46', 4, 'Doc. 15 §3', 'Qual fonte oficial confirmou cada ponto (caso, aula, portaria, resoluções do CFC, LC 123/2006, recálculo).'),
    ('C-47', 4, 'Doc. 15 §4', 'Correções e decisões humanas registradas e tratamento de dados pessoais (LGPD).'),
    ('C-48', 4, 'Doc. 11 (SAL-PROP)', 'Salário proporcional de E1 (15/30) e E2 (10/30) calculado pelo motor.')
  ) AS v(cod, nota, ref, just)
  WHERE c.id = av.criterio_id AND c.dossie = 'D2' AND c.codigo = v.cod AND av.dossie = 'D2' AND av.nota IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 48 THEN RAISE EXCEPTION 'Avaliações: % (esperado 48)', n; END IF;
END
$a$;

SELECT c.matriz, count(*) AS itens, round(avg(av.nota_v1), 2) AS media_v1, round(avg(av.nota), 2) AS media_v2
  FROM auditoria.avaliacao_conformidade av JOIN auditoria.criterio_conformidade c ON c.id = av.criterio_id
 WHERE av.dossie = 'D2' GROUP BY 1 ORDER BY 1;
