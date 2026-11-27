-- Dossiê 2, etapa 6: Doc 00 (índice geral). Fecha a revisão do dossiê.
-- Inventário com os arquivos que a plataforma gera e o produto da régua de cada um; matriz de produtos e quarentena saem do banco;
-- resumo executivo com marcadores vivos; sem Res. CFC 1.708 como norma do contrato, sem SRT, sem "220 fórmulas", sem 4 passagens.
-- Fonte da afirmação sobre a 1ª entrega: devolutiva oficial do Dossiê 2 (G07), p. 3 (produtos 8 e 9 considerados não entregues).
-- Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_00_indice' AND status_validacao = 'pendente_revisao';
  IF n <> 4 THEN RAISE EXCEPTION 'Seções do Doc 00 fora do estado esperado (% de 4)', n; END IF;

  UPDATE erp.documento_secao s SET conteudo_md = v.txt, titulo = coalesce(v.tit, s.titulo), atualizado_em = now()
  FROM (VALUES
    ('cabecalho', NULL, $t$# ÍNDICE GERAL DO DOSSIÊ 2 — ONBOARDING E DEPARTAMENTO PESSOAL (ROTA SUL IMPORTADORA)

**Universidade de Brasília (UnB) — FACE — Departamento de Ciências Contábeis e Atuariais (CCA)**
**Disciplina:** Laboratório Contábil (`CCA 0174`) — 2026/2
**Dupla (Grupo G07):** Jeovanna Ripardo Lustosa e Nathalia Peres Araujo
**Escritório simulado:** PRISMA JRNA Auditoria e Contabilidade Ltda. (CNPJ `48.123.456/0001-90` | CRC-DF `004.821/O-2` — *dados fictícios didáticos*)
**Cliente:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. (Matriz Goiânia-GO `11.222.333/0001-81`, NIRE `52900000015` | Filial Itajaí-SC `11.222.333/0002-62`, NIRE `42900000012`)
**Competência:** setembro/2026 | **Última revisão:** 27/11/2026$t$),
    ('1_inventario_de_documentos_da_en', '1. Inventário de Documentos da Entrega', $t$Todos os documentos são gerados pela plataforma PRISMA JRNA a partir do mesmo banco de dados: os quadros saem dos registros homologados e os valores da folha, do motor de cálculo. A planilha da folha, com fórmulas abertas (abas Leia-me, Parametros, Folha_Set2026, Memoria_Calculo e Provisoes_e_Integracao), acompanha o doc. 11. A **Tabela 1** relaciona os produtos mínimos do Estudo de Caso aos documentos e mostra a situação de homologação de cada um.

| Nº | Documento (arquivo) | Conteúdo | Produto |
|---|---|---|---|
| 00 | Índice geral (`00_Indice_Geral_Dossie2_Rota_Sul.pdf`) | Inventário, governança da dupla e resumo dos números | — |
| 01 | Diagnóstico societário (`01_Diagnostico_Societario_Rota_Sul.pdf`) | Análise crítica do Anexo I, matriz de riscos e plano de saneamento (3ª Alteração) | P1 |
| 02 | Proposta de honorários (`02_Proposta_Honorarios_BPO.pdf`) | Escopo, memória de custo (horas × valor-hora) e condições comerciais | P2 |
| 03 | Contrato e procuração (`03_Contrato_Servicos_Procuracao.pdf`) | Contrato de prestação de serviços (Res. CFC nº 1.590/2020), LGPD e minuta de procuração | P2 |
| 04 | Termo de responsabilidade técnica (`04_Termo_Responsabilidade_Tecnica.pdf`) | Assunção da RT, delimitação de responsabilidade e rol de pendências | P2 |
| 05 | Comunicação de onboarding (`05_Comunicacao_Onboarding_Pendencias.pdf`) | Checklist de documentos, perguntas e respostas do cliente e pendências | P3 |
| 06 | Prontuário e eSocial (`06_Prontuario_Roteiro_eSocial_VT_VR.pdf`) | Índice do prontuário, eventos do eSocial, CCT, dependentes, termos de VT/VR e de prorrogação | P4 |
| 07 e 09 | Fichas de registro (`07_Ficha_Registro_E1_Aux_Adm.pdf`, `09_Ficha_Registro_E2_Vendedor.pdf`) | Dados de registro de E1 e E2 | P4 |
| 08 e 10 | Contratos de experiência (`08_Contrato_Experiencia_E1.pdf`, `10_Contrato_Experiencia_E2.pdf`) | 45 + 45 dias (E1) e 30 + 60 dias (E2) | P4 |
| 11 | Folha e memória de cálculo (`11_Folha_Set2026_Memoria_Calculo.pdf` + planilha) | Rubricas do motor com fórmula, regras aplicadas e cenários A e B | P5 |
| 12 | Resumo, provisões e contabilização (`12_Resumo_Provisoes_Contabilizacao.pdf`) | Resumo e encargos no Simples, provisões, lançamentos L1 a L4, conciliação e recibos | P6 |
| 13 | Auditoria trabalhista (`13_Relatorio_Auditoria_Trabalhista.pdf`) | Planejamento, testes, recálculo independente, encargos e achados do cliente | P7 |
| 14 | Registro de premissas (`14_Registro_Premissas_Fontes.pdf`) | Premissas `PR-01` a `PR-20` com fonte oficial, quem decide, prazo e impacto | P8 |
| 15 | Uso de IA e LGPD (`15_Declaracao_Uso_IA_LGPD.pdf`) | Finalidade, ferramentas, verificação em fonte oficial e correções humanas | P9 |

### O que mudou em relação à 1ª entrega
- Incluídos os produtos 8 (registro de premissas) e 9 (declaração de uso de IA), considerados não entregues na 1ª entrega (devolutiva oficial do Dossiê 2, p. 3), e os docs. 01 e 06.
- Folha calculada pelo motor da plataforma, com comissão, DSR, vale-refeição, contribuição negocial e provisões, salário-família analisado pela remuneração do mês e vale-transporte de 2 conduções/dia, conferida por recálculo independente.
- Auditoria voltada aos achados do cliente na competência 09/2026.
- Documentos gerados do banco, sem valores digitados, com a origem de cada informação (material dos professores, respostas do cliente e legislação).$t$),
    ('2_matriz_de_contribuicao_individ', NULL, $t$| Documento(s) | Escopo principal | Liderança / elaboração | Revisão cruzada | Status |
|---|---|---|---|---|
| **01** | Diagnóstico do cliente e análise do contrato social (Anexo I) | **Jeovanna Ripardo Lustosa** | Nathalia Peres Araujo | Validado pela dupla (G07) |
| **02, 03 e 04** | Proposta de honorários, contrato (+ procuração) e termo de RT | **Nathalia Peres Araujo** | Jeovanna Ripardo Lustosa | Validado pela dupla (G07) |
| **05** | Comunicação de onboarding, checklist, perguntas e respostas | **Jeovanna Ripardo Lustosa** | Nathalia Peres Araujo | Validado pela dupla (G07) |
| **06 a 10** | Prontuários dos empregados 1 e 2 (índice, termos, fichas e contratos) | **Nathalia Peres Araujo** | Jeovanna Ripardo Lustosa | Validado pela dupla (G07) |
| **11 e planilha** | Folha de setembro/2026 e memória de cálculo | **Jeovanna Ripardo Lustosa** | Nathalia Peres Araujo | Validado pela dupla (G07) |
| **12** | Resumo da folha, provisões, integração contábil e recibos | **Nathalia Peres Araujo** | Jeovanna Ripardo Lustosa | Validado pela dupla (G07) |
| **13** | Relatório de auditoria trabalhista (`PT-01` a `PT-05`; `AUD-01` a `AUD-08`) | **Jeovanna Ripardo Lustosa** | Nathalia Peres Araujo | Validado pela dupla (G07) |
| **14** | Registro de premissas e fontes oficiais (`PR-01` a `PR-20`) | **Jeovanna Ripardo Lustosa** | Nathalia Peres Araujo | Validado pela dupla (G07) |
| **15 e 00** | Declaração de uso de IA (LGPD) e índice geral | **Nathalia Peres Araujo** | Jeovanna Ripardo Lustosa | Validado pela dupla (G07) |$t$),
    ('3_resumo_executivo_dos_numeros_r', NULL, $t$Valores calculados pelo motor da folha (doc. 11) e conferidos por recálculo independente (doc. 13):

| Indicador (competência 09/2026) | Valor |
|---|---:|
| Remuneração bruta | {{BRUTO_TOTAL}} |
| INSS retido (DCTFWeb) | {{INSS_TOTAL}} |
| FGTS da folha (8% — FGTS Digital) | {{FGTS_TOTAL}} |
| Líquido a pagar — cenário A (sem oposição à contribuição negocial) | {{LIQUIDO_A}} |
| Líquido a pagar — cenário B (com oposição documentada) | {{LIQUIDO_B}} |
| Subsídio de vale-transporte (empresa, 2 conduções/dia) | {{SUBSIDIO_VT}} |
| Vale-refeição (empresa) | {{VR_TOTAL}} |
| Provisões trabalhistas + FGTS | {{PROVISOES_TOTAL}} |
| **Custo total de pessoal do mês (Simples Nacional)** | **{{CUSTO_SIMPLES}}** |
| Lançamentos L1 a L4 (débitos = créditos) | {{PARTIDAS_DOBRADAS}} |
| Sensibilidade: encargo adicional se excluída do Simples (não é valor da folha) | {{IMPACTO_EXCLUSAO_SIMPLES}} |$t$)
  ) AS v(cod, tit, txt)
  WHERE s.empresa_id = 1 AND s.documento = 'd2_00_indice' AND s.codigo_secao = v.cod;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Doc 00: % (esperado 4)', n; END IF;

  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_00_indice'
     AND (conteudo_md ~ '(1\.708|SRT00189|220 fórmulas|4 passagens|_entrega_limpa|\.md\b|4\.238|4\.128|917,40|234,00|24/11/2026|`PR-01` a `PR-18`|10 achados|AUD-10)'
          OR conteudo_md ~ 'R\$ (1\.200,00|1\.633,33|2\.833,33|212,68|226,67|2\.416,30|2\.510,65|504,00|330,00)');
  IF n <> 0 THEN RAISE EXCEPTION 'Doc 00 com legado: %', n; END IF;

  UPDATE erp.documento_secao SET status_validacao = 'homologado_contadora', atualizado_em = now(),
    justificativa_contadora = 'Doc 00 revisado (27/11/2026): inventário com os arquivos gerados pela plataforma e o produto da régua de cada um; matriz de produtos e quarentena do banco; resumo com marcadores vivos; afirmação sobre a 1ª entrega conferida na devolutiva oficial (p. 3).'
   WHERE empresa_id = 1 AND documento = 'd2_00_indice' AND status_validacao = 'pendente_revisao';
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION 'Doc 00 homologado: %', n; END IF;
END
$a$;

SELECT documento, count(*) FILTER (WHERE status_validacao = 'homologado_contadora') AS homologados, count(*) AS total
  FROM erp.documento_secao WHERE empresa_id = 1 AND dossie = 'D2' GROUP BY 1 ORDER BY 1;
