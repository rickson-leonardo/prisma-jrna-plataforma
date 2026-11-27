# Revisão do Dossiê 2 — Rota Sul: registro de achados e soluções

> Registro vivo da revisão tela a tela do Dossiê 2. Cada linha diz **o que estava errado**, **qual fonte oficial resolve** e **qual solução foi adotada**.
> Regra: só vale o que tem fonte oficial dentro da plataforma (acervo) ou fonte primária pública (lei, órgão oficial) com link e data. Rascunho, texto importado e conta feita no chat não são fonte.

## Fontes oficiais usadas

| Código | Documento | Onde está |
|---|---|---|
| **EC02** | Estudo de Caso 02 (inclui o Anexo I — 2ª Alteração e Consolidação do Contrato Social) | acervo, arquivo 70 (`D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf`) |
| **AULA** | Aulas de DP 14 e 15 (admissão, folha, fechamento 2026) | acervo, arquivo 69 (`D2/Aulas_DP_Admissao_Folha_Fechamento_2026_Atualizado_IRRF_.pdf`) |
| **DEV** | Devolutiva oficial do Dossiê 2 (G07, nota 3,60) | acervo (`D2/REF_Devolutiva_Dossie2_G07.pdf`) |
| **RÉGUA** | Devolutivas oficiais D2 das outras duplas (régua de 48 elementos) | acervo (`D1/Devolutivas_Individuais_Dossie2/`) |
| **LEI** | Textos legais no Planalto e páginas oficiais | link e data em cada registro |

Legenda de status: ✅ aplicado em produção · ⏳ SQL pronto, aguardando execução · ❓ aguarda decisão · 🔁 depende de código (plano, Seção 12)

---

## Já resolvido antes deste registro (26/11/2026)

| Nº | Achado | Solução | Status |
|---|---|---|---|
| A-01 | Critérios D2 importados de rascunho: 18 de 47 notas V1 erradas e 1 elemento faltando | Devolutiva G07 registrada no acervo; 48 critérios alinhados à régua oficial (DEV + RÉGUA), com conferência automática da nota 3,60 | ✅ |
| A-02 | Capital integralizado deduzido do capital anterior | Fato `capital_integralizado` = R$ 1.000.000,00 (EC02 p. 2) | ✅ |
| A-03 | VT com 4 viagens/dia (interpretação do rascunho) | PR-08: 2 viagens/dia (EC02 p. 3; AULA p. 24); contratos E1/E2 corrigidos; folha recalculada (desconto 72,00/38,00 mantido) | ✅ (PR-08 aguarda homologação na tela) |
| A-04 | Jornada do E1 incoerente no próprio caso (41h × 44h) | PR-11: horário literal, PEND-04 e acordo de compensação | ✅ (aguarda homologação na tela) |
| A-05 | CNAEs de veículos sob "Importação e Exportação" | PR-02: manter Simples; excluir 4541-2/01, 4541-2/03 e 4511-1/02 na 3ª Alteração | ✅ (aguarda homologação na tela) |
| A-06 | 19 parâmetros do DP sem fonte verificada; IRRF citando a tabela de 2024 | 15 conferidos na AULA; 4 na Lei 9.250/Lei 15.270 (Planalto) e na Carta de Serviço do Governo de Goiás; todos homologados | ✅ |
| A-07 | Código: alerta falso de resíduo, risco pré-selecionado, campos trocados no PDF, valores de reserva, "47 critérios" fixo, "4/dia" na planilha | Corrigido (branches `fix/d2-revisao-claude` e `fix/d2-revisao-fase5`), folha recalculada e revalidada | ✅ |

---

## Estação 1 — Cadastro (concluída)

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| C-01 | CPF da sócia Helena não cadastrado (só o de Bruno) | EC02 p. 7: "CPF/MF sob nº 111.444.777-35" | Cadastrar o CPF (fictício do caso) | ✅ |
| C-02 | RG dos dois sócios não cadastrado | EC02 p. 7: RG 1.111.111 (DGPC-GO) e 2.222.222 (PC-GO) | Cadastrar como identificador "OUTRO" | ✅ |
| C-03 | Objeto social incompleto: o banco tinha 8 dos 18 CNAEs do Anexo I (faltavam 4649-4/02, 4649-4/06, 4649-4/99, 4665-6/00, 4669-9/99, 4679-6/99, 4689-3/99, 4759-8/99, 4789-0/03, 4789-0/99). A devolutiva cobra a análise do objeto e dos CNAEs | EC02 p. 9 (Cláusula Segunda consolidada) | Registrar os 18 CNAEs exatamente como no Anexo I | ✅ |
| C-04 | Percentual dos sócios gravado em unidade errada (50.000.000 em vez de 500.000 = 50%, padrão do D1) | EC02 p. 8: 750.000 quotas para cada sócio (50%) | Corrigir para 500.000 | ✅ |
| C-05 | Datas societárias erradas: quadro societário e capital de R$ 1,5 milhão com vigência em 14/09/2026 (data do onboarding); capital anterior desde 01/01/2024 (antes da própria empresa existir) | EC02 p. 13: "COM EFEITOS DO REGISTRO EM: 22/07/2025"; EC02 p. 8: início das atividades em 28/10/2024 | Vigência do quadro e do capital atual = 22/07/2025; capital anterior de 28/10/2024 a 21/07/2025 (contrato original e 1ª alteração não fornecidos — DOC-01) | ✅ |
| C-06 | O enquadramento mostrava a PRISMA JRNA (Nathalia; escritório CRC-DF 004.821/O-2) como responsável técnica desde 28/10/2024. **Origem: rascunho da V2** (`importado_rascunho_v2`), não documento oficial | EC02 p. 1: em 14/09/2026 os sócios, "insatisfeitos com o escritório anterior", procuram a dupla; termo de RT a partir de 01/09/2026 (elogiado na DEV) | Histórico em dois períodos: 28/10/2024 a 31/08/2026 com o "escritório anterior" (não identificado no caso); a partir de 01/09/2026 com a PRISMA | ✅ |
| C-07 | Porte "ME" e CNAE principal 4530-7/02 são premissas: o caso não informa faturamento nem CNAE principal | EC02 p. 2 lista a "atividade-foco" (4530-7/02 em primeiro) | Registradas na PR-01, com responsável, prazo (DOC-08) e impacto se alteradas | ✅ |
| C-08 | Endereço da filial gravado com texto de análise junto ("Sala 223 (Anexo I: Sala 223 A 32)" e o NIRE) | EC02 p. 2: "Sala 223"; EC02 p. 8: "Sala 223 A 32" | Endereço copiado do acervo exatamente como na ficha do caso (p. 2); a divergência fica no achado R-06. O NIRE da filial (`42900000012`, EC02 p. 2) foi resolvido em C-17 | ✅ |

| C-09 | Tela: o campo "Responsável técnica" do período da PRISMA aparecia vazio (a lista só tinha sócios do cliente); salvar apagaria a RT | — (defeito de código) | `repo.py`: RT gravada entra na lista de opções (commit `0d4270c`, em produção) | ✅ |
| C-10 | Contador da tela "0/2": os dois períodos do enquadramento estavam como "Inconsistência apontada" (status herdado do rascunho) | — | Homologar os dois períodos com justificativa (o risco de CNAE é do caso: PR-02 e R-01). SQL: `docs/revisao_d2_sql/01_estacao1_homologar_enquadramento.sql` (confirmado em produção: 2/2) | ✅ |
| C-11 | Nome fantasia gravado como `"Rota Sul (Caso D2)"` (rótulo interno; sai na Tabela 1 do PDF do Doc 01) | EC02 pp. 2, 7 e 8: `ROTA SUL IMPORTADORA` | Corrigir `erp.empresa.nome_curto` para `Rota Sul Importadora` no SQL `docs/revisao_d2_sql/03_estacao1_ajustes_finais_cadastro.sql` | ✅ |
| C-12 | Papel dos sócios gravado como código cru `socio_administrador` (sai na tela 1.3 e na Tabela 2 do PDF do Doc 01) | EC02 p. 2 e Cl. 8ª (p. 10): "Ambos os sócios, assinando individualmente" | Corrigir para `Sócia administradora (assina individualmente)` e `Sócio administrador (assina individualmente)` no SQL `03_` | ✅ |
| C-13 | Enquadramento 2024–2026 sem ressalva do objeto anterior à 2ª Alteração (22/07/2025) e `apontamento_auditoria` sem acentos | EC02 p. 1 (atividade original: automóveis usados; DOC-01 pendente) | Acrescentar ressalva histórica na `justificativa_contadora` e corrigir acentuação no SQL `03_` | ✅ |
| C-14 | Barra de progresso da tela `/cadastro` mostra `2/13` (ignora os 11 registros `acervo_referencia`) | — (código `cadastro.html`) | Calcular progresso sobre registros revisáveis (excluindo `acervo_referencia`, exibindo `2/2` + contagem de referências do acervo) | ✅ |
| C-15 | Seção 1.5 não exibe `vigente_ate` (período 2024–2026 parece aberto na tela) | — (código `cadastro.html` / `app.py`) | Exibir `Vigente de DD/MM/AAAA a DD/MM/AAAA` quando `vigente_ate` preenchido (`data_br`) | ✅ |
| C-16 | Rótulos herdados do D1 na tela compartilhada (`sede no Distrito Federal`, `Quadro de Sócias`, dropdown `+ Novo` da 1.4 listando a RT) | — (código `cadastro.html` / `repo.py`) | Adaptar rótulos para D2 e restringir `select` de `Pessoa` da 1.4 (`pessoas_ident`) a empresa + sócios | ✅ |
| C-17 | NIRE da Filial (`42900000012`) sem coluna própria em `erp.estabelecimento` (e sem exibição dedicada no Doc 01) | EC02 p. 2 e p. 8: Matriz `52900000015` (JUCEG) · Filial `42900000012` (JUCESC) | Migração `009_estabelecimento_nire.sql` + UI/PDF aplicados em código; carga oficial aplicada via SQL `docs/revisao_d2_sql/04_estacao1_nire_estabelecimento.sql` | ✅ |

> **Nota de método:** o caso é propositalmente cheio de erros e desvios (é um laboratório da vida real). Corrigimos só o que **a plataforma registrou diferente da fonte**; os erros **do próprio caso** (datas divergentes, CNAEs vedados, jornada incoerente) não são "consertados": viram achados, premissas e providências.
>
> **Lição de processo:** o primeiro envio do SQL falhou ("19 CNAEs"): a linha de continuação "anteriormente;" entrava como vazia. O ensaio usava `string_agg`, que esconde vazios. Ensaios passam a usar a mesma consulta do SQL final.

## Perguntas ao professor (grupo da disciplina)

Critério (usuária, 27/11/2026): o professor faz o papel de todos os personagens do caso (cliente, contador anterior, advogado). Só perguntamos **fatos do caso** que só ele conhece; nunca o que a legislação vigente ou o próprio material responde.

| Data | Pergunta | Papel | Status |
|---|---|---|---|
| 27/11/2026 | Houve manifestação do advogado sobre as diretrizes da 3ª Alteração? (liga a Q9 / PEND-02) | Advogado | ⏳ enviada pela usuária |
| 27/11/2026 | As respostas de 24/09/2026 (cliente, contador anterior e advogado) estão reunidas em algum documento? (fonte do P3) | Professor | ⏳ enviada pela usuária |

Descartadas por serem respondidas pela lei ou pelo material: datas de admissão (EC02 p. 2), leitura das provisões (CF art. 7º, XVII; FGTS 8%), jornada 41h × 44h (incoerência proposital, tratada na PR-11).

## Classificação das fontes: original × legado

| Classe | O que é | Como tratar |
|---|---|---|
| **Original** | Material dos professores: Estudo de Caso 02 + Anexo I, aulas, devolutivas, respostas oficiais do cliente | É a premissa do trabalho. Erros e omissões do caso são propositais: viram achados e providências |
| **Original registrado pela dupla anterior** | Respostas que o professor deu no grupo da disciplina às perguntas dos alunos (o caso foi feito para os alunos irem descobrindo e perguntando), transcritas pela dupla anterior — ex.: `Solicitação_JRNA.pdf`, p. 3 (respostas Q1 a Q5), e os fatos citados nas devolutivas (Sócontas / Dr. Osvaldo, omissão de março a agosto/2026) | Vale como fonte (é resposta do professor); citar como "respostas do cliente dadas pelo professor no grupo da disciplina" e com a página do registro. Não perguntaremos nada novo ao professor por ora |
| **Legado** | Tudo o que as tentativas anteriores produziram (V1, rascunhos da V2, pasta `Arquivado_antigo`, registros `importado_v1` / `importado_rascunho_v2`) | Não é fonte. Só fica se for confirmado por material original; senão é invenção a remover |

### Perguntas em aberto

- **P-01 — Contador anterior "Sócontas / Dr. Osvaldo" e omissão de março a agosto/2026.** Não estão no Estudo de Caso nem na aula, mas **são material original**: a devolutiva oficial da G07 (p. 3) cita "Sócontas/Dr. Osvaldo e a omissão de março a agosto" como fatos "que vieram da resposta do cliente"; a devolutiva da G17 cita "as respostas oficiais do cliente (24/09)" (ASO não realizado, nenhum evento no eSocial, Simples desde 28/10/2024, obrigações de março a agosto em atraso); a da G00 cita o "quadro de respostas (inclusive do contador anterior)"; e a régua pede "respostas do cliente, do contador e do advogado". **Falta o documento primário**: as respostas oficiais do cliente, do contador anterior e do advogado, entregues pelos professores em 24/09/2026, não estão no acervo. Pendente: localizar (SIGAA, e-mail) e registrar no acervo.

---

## Estação 2 — 2ª Alteração (Anexo I)

Os 9 achados de cláusula são **legado** (`importado_rascunho_v2`). Roteiro:
1. Conferir cada achado contra o texto do Anexo I no acervo (arquivo 70, p. 7 a 13). O que bater fica; o que for invenção sai.
2. Preencher os 6 campos novos de cada achado (natureza do risco formal/material, nível, providência, fundamento legal, responsável, prazo), como pede a régua do P1.

> **Resultado da conferência:** todos os 9 achados existem no Anexo I (nenhum foi inventado), com ajustes de precisão textual, remoção do número solto legado (`+R$ 917,40/mês`) e preenchimento dos 6 campos novos da régua do P1 no SQL `docs/revisao_d2_sql/02_estacao2_clausulas_anexo1.sql` (sem alterar `origem_registro` e mantendo `status_validacao` para revisão e homologação da contadora na tela ou em SQL seguinte). SQL aplicado em produção; revisão/homologação de tela na sequência.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| E2-01 | `inst:d2:01` — Denominação social `DISTRIBUIDORA` × `DISTRIBUIÇÃO` com citação legada de página errada ("Anexo I pág. 1 vs. pág. 8") | EC02 pp. 7, 8 e 13 (Preâmbulo, título da Consolidação e Cl. 1ª); CC arts. 1.158 e 1.163 ([Planalto](https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm), 26/11/2026) | Corrigir referência para EC02 pp. 7–8 e 13, classificar **Formal / Baixo** e preencher providência, responsável e prazo (R-06) no SQL `02_estacao2_clausulas_anexo1.sql` | ✅ |
| E2-02 | `inst:d2:02` — Endereço da filial Itajaí-SC (`Sala 223` × `Sala 223 A 32`) sem os 6 campos de saneamento | EC02 p. 2 × p. 8 (Cl. 1ª, Par. Único); IN RFB nº 2.119/2022; IN DREI nº 81/2020 ([gov.br/drei](https://www.gov.br/empresas-e-negocios/pt-br/drei), 26/11/2026) | Confirmar achado, classificar **Formal / Médio** e preencher providência, fundamento, responsável e prazo (R-06) no SQL `02_` | ✅ |
| E2-03 | `inst:d2:03` — Objeto social (18 CNAEs Matriz × 17 Filial omitindo `8211-3/00`; `4541-2/01`, `4541-2/03`, `4511-1/02` sob `IMPORTAÇÃO E EXPORTAÇÃO:`) com número legado digitado em texto (`+R$ 917,40/mês na folha se excluída`) e sem citar Cl. 1ª Par. Único | EC02 pp. 7–9 (Cl. 2ª Alt., Cl. 1ª Par. Único e Cl. 3ª Consol.); LC 123/2006 art. 17, VIII ([Planalto](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm), 26/11/2026) | Remover `+R$ 917,40/mês`, incluir Cl. 1ª Par. Único, classificar **Material / Crítico** e preencher os 6 campos (PR-02 / R-01) no SQL `02_` | ✅ |
| E2-04 | `inst:d2:04` — Capital R$ 1,5M com conflito de prazo `31/07/2026` × `31/07/2025`, mora de R$ 500 mil (P-01) e erros redacionais não citados (`"pelo pais"`, `"reais) quotas"`, `"a ser integralizados"`) | EC02 pp. 2, 8–10 (Cl. 3ª § 1º Alt., Cl. 4ª e Cl. 7ª Consol.); CC arts. 1.004, 1.052 e 1.058 ([Planalto](https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm), 26/11/2026) | Incorporar erros redacionais e rito da Cl. 7ª, classificar **Material / Crítico** e preencher os 6 campos (R-02) no SQL `02_` | ✅ |
| E2-05 | `inst:d2:05` — Três critérios conflitantes de haveres (Cl. 5ª IGPM+3% em 24x × Cl. 12ª Balanço Especial em 10x × Cl. 14ª Valor de Mercado sem prazo) e AGO/tesouraria (Cl. 5ª IV) | EC02 pp. 9 e 11–12; CC arts. 1.029, 1.031, 1.053, 1.071–1.072; CPC arts. 604 e 606 ([Planalto](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm), 26/11/2026) | Detalhar choque direto Cl. 12ª § 4º × Cl. 14ª caput (ambas retirada com 60 dias), classificar **Material / Alto** e preencher os 6 campos (R-03 e R-05) no SQL `02_` | ✅ |
| E2-06 | `inst:d2:06` — Quórum 50/50 sem desempate (deadlock), assinatura isolada sem alçada (Cls. 8ª–9ª), ilegalidade da Cl. 10ª (51% para adm. não sócio viola CC art. 1.061 que exige 2/3 dos sócios com capital não integralizado), exclusão extrajudicial inexequível no 50/50 (Cl. 14ª § 1º / CC art. 1.085) e ambiguidade de mandato de 3 anos (Cl. 11ª × Cl. 10ª § 2º) | EC02 pp. 10–12; CC arts. 1.010, 1.030, 1.061 (Lei 14.451/2022), 1.063 § 1º e 1.085 ([Planalto](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/lei/L14451.htm), 26/11/2026) | Ampliar achado com ilegalidade do art. 1.061, alçada e art. 1.085, classificar **Material / Alto** e preencher os 6 campos (R-04) no SQL `02_` | ✅ |
| E2-07 | `inst:d2:07` — JCP (TJLP) oneroso no Simples (Cl. 13ª § 1º), lucros desproporcionais/antecipados sem travas de escrituração e regularidade fiscal (Cl. 13ª §§ 2º–3º; débitos mar–ago/2026 via P-01) e pró-labore facultativo (Cl. 16ª) | EC02 pp. 1 e 11–12; Lei 9.249/1995 art. 9º; LC 123/2006 art. 14 § 2º; Lei 4.357/1964 art. 32 ([Planalto](https://www.planalto.gov.br/ccivil_03/leis/l4357.htm), 26/11/2026); Lei 8.212/1991 art. 12, V, "f"; SC COSIT 120/2016 | Vincular corretamente os débitos à P-01, classificar **Material / Alto** e preencher os 6 campos (R-07 e R-09) no SQL `02_` | ✅ |
| E2-08 | `inst:d2:08` — Quórum de 3/4 na Cl. 15ª citando arts. 1.071/1.076 do CC desatualizados frente à Lei 14.451/2022 (mínimo legal passou a >50%) e estendendo 3/4 à escolha do liquidante | EC02 p. 12 (Cl. 15ª); CC art. 1.076, II–III c/ redação da Lei 14.451/2022 ([Planalto](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/lei/L14451.htm), 26/11/2026) | Precisar que o contrato pode fixar quórum maior mas reproduz dispositivo revogado e estende 3/4 ao liquidante, classificar **Material / Médio** e preencher os 6 campos (R-04) no SQL `02_` | ✅ |
| E2-09 | `inst:d2:09` — Regência supletiva contraditória na Cl. 18ª (Sociedade Simples "conjuntamente" com S.A.) | EC02 p. 12 (Cl. 18ª); CC art. 1.053 par. único ([Planalto](https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm), 26/11/2026) | Confirmar antinomia frente ao CC art. 1.053 par. único, classificar **Material / Médio** e preencher os 6 campos (R-05) no SQL `02_` | ✅ |
| E2-10 | 9 achados conferidos mas ainda 0/9 homologados na quarentena e 3 metadados herdados do D1 (`metodo_haveres`/`quorum_tipo` em 05, 06 e 08) | EC02 pp. 7–13 (Anexo I) | Homologar os 9 achados com justificativa técnica e limpar os 3 metadados D1 para `nao_aplicavel` no SQL `docs/revisao_d2_sql/05_estacao2_homologar_anexo1.sql` | ✅ |

| D01 | Doc. 01 (diagnóstico): 7 seções pendentes, 3 com o número legado R$ 917,40; texto reescrito pela Gemini citava `Solicitação_JRNA.pdf` como "Respostas Oficiais do Cliente" e chamava o contador anterior de "Sócontas **Ltda.**" | EC02 pp. 1–2 e 7–13; respostas do professor (Solicitação_JRNA p. 3); DEV p. 3 | Revisão (Claude, 27/11): fonte renomeada para "respostas do cliente dadas pelo professor no grupo da disciplina" e "Ltda." removido (não consta da devolutiva). SQL `06_doc01_secoes_homologar.sql` | ✅ |
| A-08 | A carta de onboarding com as respostas do professor (`Solicitação_JRNA.pdf`) não estava no acervo | Arquivo da dupla (sha256 ec866df0…) | Registrar no acervo (74 linhas) e conferir que as respostas Q1–Q5 do banco estão literalmente na p. 3 (conferido localmente: 5/5). SQL `07_acervo_solicitacao_jrna.sql` | ✅ |
| A-09 | Migração 009 (coluna NIRE) aplicada no banco mas sem registro no controle de migrações | — | Registrada em `auditoria.schema_migration` (27/11) | ✅ |

---

## Ordem de trabalho a partir de 27/11/2026: por documento e produto

Decisão da usuária: avançar pelos documentos gerados e pelos produtos da régua, e não mais pela ordem das telas. Cada etapa fecha as telas que alimentam um grupo de documentos.

| Etapa | Telas | Documentos | Produto (régua) | Status |
|---|---|---|---|---|
| 1 | Estação 1 + Estação 2 + 7 seções do Doc 01 | Doc 01 | P1 (V1: 1,7) | ✅ |
| 2 | Estação 7 (Onboarding e Contratos) | Docs 02, 03, 04 e 05 | P2 e P3 | ✅ (27/11/2026) |
| 3 | Estação 8 (DP) | Docs 06 a 10 | P4 | ⏳ em andamento |
| 4 | Estação 9 (Folha e Auditoria) | Docs 11, 12, 13 + planilha .xlsx | P5, P6 e P7 | |
| 5 | Estação 5 (Conformidade, PR e IA) | Docs 14 e 15 | P8 e P9 | |
| 6 | Todas fechadas | Doc 00 (índice) | Consolidado | |

> A Estação 3 (Saneamento, etapas R-01 a R-09) não gera nenhum documento do D2 (conferido no emissor); entra como conferência de coerência com os achados da Estação 2 quando algum documento citar os códigos R-xx. Telas já fechadas recebem linhas novas sempre que uma etapa posterior revelar algo.

## Etapa 2 — Estação 7, contratos (Docs 02, 03 e 04 → P2)

Régua do P2 (V1: todos os 5 elementos com nota 2): contrato com dados completos da contratada (CNPJ e CRC); proposta com memória de custo; responsabilidades, LGPD e procuração; termo com rol de pendências e assinatura da RT; coerência entre os três e com o cliente.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| CT-01 | A PRISMA assina em 14/09/2026 com CNPJ, CRC e "ME", mas o D1 projetou contrato social em 15/09/2026 e CNPJ em 01/10/2026 | EC02 p. 1: "cada dupla — na condição de sócios da organização contábil constituída no Dossiê 1 — assume o atendimento" | **Opção A (decisão da usuária, 27/11):** prevalece a premissa do caso; nova PR-19 registra que o cronograma do D1 é projeção do plano de abertura | ✅ |
| CT-02 | "Sócontas **Ltda.**" nos três documentos (e em outra seção do D2) | DEV G07 p. 3: "Sócontas/Dr. Osvaldo" | "Sócontas / Dr. Osvaldo" em todo o D2 | ✅ |
| CT-03 | Endereço da contratada abreviado ("Asa Sul, 6º andar, sala 901") | D1: `erp.estabelecimento` da PRISMA (SCS, Quadra 06, Bloco A, Lote 157…) | Endereço completo lido do D1 pelo próprio SQL | ✅ |
| CT-04 | "Hora técnica de R$ 125, aderente ao modelo financeiro do Dossiê 1": o D1 não tem esse valor (só o ticket médio de R$ 1.500, que confere) | D1: cenário oficial `v2_segregacao` (ticket R$ 1.500); RÉGUA (G02): valores "premissa da dupla" aceitos se declarados | Nova PR-20 declara a hora técnica como premissa de precificação | ✅ |
| CT-05 | Valores digitados nos textos (proposta, Cláusula 2ª do contrato, 13º) | — | Marcadores vivos `{{VALOR_SETUP}}`, `{{HONORARIO_MENSAL}}` etc. (código no branch `feat/d2-marcadores-honorarios`); memória de horas ganha código por frente e perde os campos digitados "total" e "valor_hora" | ✅ |
| CT-06 | Termo de RT com "+R$ 917,40/mês" e só o CNAE 4541-2/01 | PR-02 | Sem número digitado; os 3 CNAEs (4541-2/01, 4541-2/03, 4511-1/02) e remissão à PR-02 e à sensibilidade PR-17 | ✅ |
| CT-07 | Cabeçalho da proposta com "(Revisão Final: 23/11/2026)", resto da tentativa anterior | — | Removido | ✅ |
| CT-08 | Omissão de março a agosto citada como "relato verbal dos sócios a confirmar" | Respostas do professor no grupo (classe "original registrado pela dupla anterior") | "respostas do cliente dadas pelo professor no grupo da disciplina" | ✅ |

Aplicado em 27/11/2026 (merge `9b64874` em produção + SQL 08: 21 seções e 4 contratos homologados; PR-19 e PR-20 criadas, pendentes de homologação na tela Sustentação). Ordem que era obrigatória: **merge do branch `feat/d2-marcadores-honorarios` → SQL `08_docs02a04_contratos.sql`** (sem o código, os PDFs mostrariam `{{VALOR_SETUP}}` literalmente). Pré-condições do SQL 08 conferidas só com leitura em 27/11: 21 seções e 4 contratos pendentes, 10 frentes de horas, 4 endereços e todos os trechos a substituir presentes.

## Etapa 2 — Estação 7, onboarding (Doc 05 → P3)

Régua do P3 (V1: respostas 1, pendências 1, checklist 2, perguntas 2): respostas do cliente, do contador e do advogado registradas com a origem; quadro de pendências com responsável, prazo e providência; checklist por pessoa/tema com responsável e status; perguntas objetivas sobre as lacunas.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| OB-01 | Quadros em duplicidade: as seções 1 a 3 repetem à mão os quadros que o PDF já gera do banco (`diligencia_item`) e já divergem (DOC-02 "Recebido" no texto × "em saneamento" no banco) | Emissor (`d2_doc.html`, quadros dil_docs/dil_pergs/dil_pends) | Seções 1–3 viram introdução curta; conteúdo único = os 30 itens de diligência do banco | ✅ |
| OB-02 | Cabeçalho com "Atualização: 23/11/2026" (tentativa anterior) | — | Remover | ✅ |
| OB-03 | Q1–Q5 citadas como "retorno formal / resposta escrita dos sócios" | Classe "original registrado pela dupla anterior"; carta no acervo (p. 3) | "Respostas do cliente dadas pelo professor no grupo da disciplina, registradas na carta (acervo, p. 3)" | ✅ |
| OB-04 | Q7 (ASO) e Q8 (Sócontas e omissão) citados como "relato de onboarding, 1ª entrega" | DEV G07 p. 3 ("fatos que vieram da resposta do cliente") | Mesma fonte: resposta do professor no grupo, citada na devolutiva oficial | ✅ |
| OB-05 | DOC-12 com "VT 4×2 passagens"; Q6 com "2 conduções por trajeto" | AULA p. 24; PR-08 | 2 viagens/dia | ✅ |
| OB-06 | Os 13 documentos com responsável genérico "Diretoria / DP PRISMA" (a régua pede checklist por pessoa com responsável) | Régua P3 | Responsável por documento (sócios, advogado, contador anterior, empregados, clínica SST, despachante, diretoria comercial) | ✅ |
| OB-07 | Q1–Q9 com prazo "23/11/2026" (data de revisão da tentativa anterior) | — | Q1–Q6 "Respondida"; Q7, Q8 e Q9 com os prazos das pendências ligadas (PEND-01 02/10, PEND-03 30/10, PEND-02 20/10) | ✅ |
| OB-08 | PEND-02 cita só o CNAE 4541-2/01 | PR-02 | Os 3 CNAEs | ✅ |
| OB-09 | Valores digitados no texto ("R$ 12.000", "R$ 900 e R$ 100") | — | Sem números; valores ficam nos docs que os calculam (02 e 11) | ✅ |
| OB-10 | "PR-01 a PR-18" | — | PR-01 a PR-20 | ✅ |
| OB-11 | Q9 (advogado) afirma "não houve resposta formal" | Busca em `Arquivado_antigo` (27/11): nenhuma resposta do advogado; anotação PQ-07 de 23/11 da tentativa anterior: Nathalia "não sei / não lembro" | Redação honesta: "resposta do advogado não localizada nos registros da dupla; providência segue em PEND-02" | ✅ |
| OB-12 | Premissa "vendas líquidas de R$ 60.000" (DOC-13, PEND-05, Q10) sem fonte precisa | AULA p. 25: "Premissa didática: vendas líquidas de R$ 60.000 no período; 9 dias trabalháveis e 1 DSR" | Citar AULA p. 25 | ✅ |
| OB-13 | Fonte circular: os 13 documentos e as 8 pendências citavam como origem o próprio Doc 05 ("Doc. 05 §1/§3") | Régua P3: "origem de cada informação" | Cada item aponta a origem real: carta de onboarding (acervo, p. 2–3), EC02 p. 1 e p. 3, AULA p. 24–25, DEV G07 p. 3, NR-1/4/7 e Anexo I Cl. 16ª | ✅ |

Aceite da usuária em 27/11/2026 para OB-01 a OB-12. SQL `09_doc05_onboarding.sql` (pré-condições conferidas só com leitura: 30 itens, 4 seções, fontes do acervo e trechos a substituir).

## Etapa 3 — Estação 8, Departamento Pessoal (Docs 06 a 10 → P4)

Régua do P4 (V1: prontuário 1; CBO/piso 2; dependentes/VT/VR 2; eSocial 2; ficha 3; contrato de experiência 3; ASO 3).

Conferido com EC02 pp. 2–3 (27/11/2026): cargos, CBOs, admissões (16/09 e 21/09), salários, jornadas, experiência (45+45 e 30+60), VT, VR (R$ 30/dia só E1), dependentes (E1: 1 filho, 6 anos; E2: nenhum) e CCT — **batem**.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| DP-01 | Dados pessoais inventados pela tentativa anterior: nomes "Mariana Alves Costa" e "Rafael Souza Lima", CPFs, e o filho "Lucas Alves Costa" com CPF e nascimento 12/03/2020 (marcados como "fictícios", PR-18). O caso e a aula só falam em "Empregado 1", "Empregado 2" e "1 filho, 6 anos" | EC02 pp. 2–3; AULA p. 21; RÉGUA C-20: "Ficha com dados do caso (…) **sem dados inventados**"; RÉGUA C-22: documentos de admissão "como pendência real" | Opção A (recomendada): remover os dados pessoais inventados; "Empregado 1 (Auxiliar Administrativo)" / "Empregado 2 (Vendedor)"; dados pessoais "a coletar (DOC-09)"; filho "1 filho, 6 anos (EC02 p. 3); certidão a coletar" | ✅ decidido: manter (ver abaixo) |
| DP-02 | (efeito na Estação 7) DOC-09 "Documentos civis admissionais" homologado como **concluído/recebido**, mas o caso lista "documentos de admissão" entre as "informações a apurar" | EC02 p. 3 ("Informações a apurar: … documentos de admissão") | Reabrir o DOC-09 como pendente (linha nova na Estação 7, conforme a regra de telas fechadas) | ✅ SQL 10 |
| DP-03 | Doc 06 (seções 1 e 5) ainda usa **4 passagens/dia** (R$ 189,20 / R$ 154,80; subsídio R$ 117,20 / R$ 116,80) e a "nota de sensibilidade"; o banco e a PR-08 já estão em 2/dia (mesmo erro do OB-05) | EC02 p. 3; AULA p. 24 ("VT: 2 viagens/dia"); A-03 | Termos de VT com 2 viagens/dia; valores em R$ saem do texto e passam a remeter ao doc. 11 (motor da folha) | ✅ SQL 10 |
| DP-04 | Valores digitados no texto, não calculados pelo motor: VT, VR R$ 330,00, contribuição negocial R$ 39,96 / R$ 54,39 (Doc 06); bruto R$ 2.833,33, INSS R$ 212,68 e FGTS R$ 226,67 no nome/observação dos eventos S-1200/S-1299 | Regra "plataforma é a fonte de verdade"; AULA p. 30 ("sem valor digitado") | Texto passa a citar regra + "valor no doc. 11"; os números só aparecem depois de homologados na etapa 4 (folha) | ✅ SQL 10 |
| DP-05 | S-1200 e S-1299 com status "pronto_envio", mas a folha ainda não foi homologada (etapa 4) | AULA p. 23 ("Documento ≠ evento"); etapa 4 pendente | Voltar para "aguardando_insumo" (folha + e-CNPJ) | ✅ SQL 10 |
| DP-06 | S-2240 "BLOQUEADO: requer PGR/DIR, PCMSO e **LTCAT**". O LTCAT só é exigido se houver agente nocivo; para funções administrativa e de vendas o S-2240 é enviado com "ausência de agente nocivo", com base no inventário de riscos (PGR ou DIR da ME/EPP) | NR-1, item 1.8.4 (DIR para ME/EPP grau de risco 1 e 2); Lei 8.213/91, art. 58, §1º (LTCAT para aposentadoria especial); MOS eSocial S-2240 | Observação: "depende do inventário de riscos (PGR ou DIR — NR-1 1.8.4); sem agente nocivo, informar ausência (código 09.01.001); LTCAT só se houver agente nocivo" | ✅ SQL 10 |
| DP-07 | Registro MTE "SRT00189/2025" da CCT não consta do material oficial; a aula só cita "Termo Aditivo 2026/2027, cláusulas 3ª, 6ª e 11ª". Os valores da CCT (piso R$ 1.722,25; vendedor R$ 1.863,00; base VT R$ 2.257,50; negocial 3,33%, teto R$ 148) **batem** com a AULA p. 29 | AULA pp. 21 e 29 | Retirar o número de registro e citar "CCT SECEG × SINDILOJAS-GO, Termo Aditivo 2026/2027, cl. 3ª, 6ª e 11ª (AULA p. 29); premissa didática (AULA p. 21)" | ✅ SQL 10 |
| DP-08 | Tarifa de VT "RMTC Goiânia R$ 4,30" (contratos e PR-08) sem fonte oficial citada; o material não informa a tarifa | — (fato público, não pergunta ao professor) | Citar a fonte oficial da tarifa na PR-08 (etapa 5) ou deixar como premissa declarada; nos Docs 06–10 só "2 viagens/dia" | ✅ resolvido: tarifa conferida na Carta de Serviço do Governo de Goiás (08/05/2026), já homologada no parâmetro CCT-VT-MISTO |
| DP-09 | Efeitos do DP-01: nomes nos títulos dos eventos S-2200 ("Mariana", "Rafael"), nas declarações de dependentes, nos termos de VT/VR e de prorrogação, nas fichas (I e II) e nos contratos (qualificação e assinatura) | ver DP-01 | Trocar por "Empregado 1" / "Empregado 2" e campos "a coletar (DOC-09)" | ✅ SQL 10 |

Conferido sem achado: prazos de experiência e prorrogação (30/10 → 14/12; 20/10 → 19/12; CLT art. 445 e 451); piso × salário (E1 conforme; E2 fixo R$ 1.900 ≥ R$ 1.863); salário-família E1 não elegível (R$ 2.400 > R$ 1.980,38 — AULA p. 24, Port. MPS/MF 13/2026); DSR da comissão em rubrica destacada (AULA p. 25); ASO como pendência real (S-2220 em alerta); S-2300 condicional ao pró-labore.

**Decisão DP-01 (usuária, 27/11/2026): manter os dados pessoais fictícios.** A própria empresa, o CNPJ e o NIRE são fictícios; nomear os empregados deixa ficha, contrato e termos concretos. Leitura adotada da régua C-20: "sem dados inventados" vale para **fatos que mudam o caso** (salário, datas, recibos, ASO realizado), não para identificação de preenchimento declarada (PR-18). Para manter o C-22, os dados pessoais são tratados como informados verbalmente pelos sócios (EC02 p. 2) e os documentos comprobatórios ficam "a coletar e conferir" (DOC-09 reaberto, DP-02). DP-09 passa a ser só a troca de "Cadastramento inicial" por "Admissão do trabalhador" no S-2200.

SQL: `docs/revisao_d2_sql/10_docs06a10_dp.sql` — 2 contratos (CCT com fonte, documentos civis com status), DOC-09 em saneamento, 7 eventos corrigidos (S-2200, S-2220, S-2240, S-1200 e S-1299 em aguardando insumo), Doc 06 seções 1/2/3/5 reescritas sem valores digitados, registro SRT retirado de 5 seções, fichas com declaração dos fictícios; homologa 2 contratos, 10 eventos e 27 seções. Pré-condições conferidas por leitura em 27/11/2026.

SQL 10 rodado pela usuária em 27/11/2026: 2/2 contratos, 10/10 eventos, 27/27 seções homologados. **Etapa 3 ✅.**

## Etapa 4 — Estação 9, Folha (Docs 11 a 13 + planilha → P5, P6, P7)

Régua (devolutiva G07, "Para chegar ao 4"): C-23 a C-28 e C-48 (P5), C-29 a C-33 (P6), C-34 a C-39 (P7).

**Motor da folha conferido contra a régua (27/11/2026), valores calculados pelo motor (`erp.folha_item`, origem `motor_calculo`):** salário proporcional R$ 1.200,00 / R$ 633,33 (C-48); comissão R$ 900,00 e DSR R$ 100,00 (C-23); salário-família zero (C-25); VT R$ 72,00 / R$ 38,00, VR R$ 330,00, negocial R$ 39,96 / R$ 54,39 (C-26); INSS R$ 90,00 / R$ 122,68 (C-27); IRRF zero e FGTS R$ 96,00 / R$ 130,67 (C-28); provisões E1 13º R$ 200,00, férias + 1/3 R$ 266,67, FGTS R$ 37,33, E2 sem avo (C-29). Lançamentos L1–L4 do motor com 2 passagens/dia: débitos = créditos = R$ 4.066,00.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| FO-01 | Docs 11, 12 e 13 ainda usam **4 passagens/dia**: VT R$ 189,20 / R$ 154,80, subsídio R$ 234,00, L3 R$ 674,00, partidas R$ 4.238,00, custo R$ 4.128,00, notas de sensibilidade e o achado AUD-10. O motor já está em 2/dia (subsídio R$ 62,00; L3 R$ 502,00; partidas R$ 4.066,00; custo R$ 3.956,00) | EC02 p. 3; AULA p. 24; A-03 | Textos com marcadores vivos; AUD-10 deixa de ser achado (premissa resolvida na PR-08) | ❓ |
| FO-02 | Tabelas digitadas nas seções duplicam as tabelas que o PDF já gera do banco (rubricas, partidas L1–L4, conciliação, recálculo independente, papéis de trabalho e achados) | Régua C-24 ("não valores digitados"); AULA p. 30 | Seções viram texto de regra + marcadores (`{{BRUTO_TOTAL}}`, `{{LIQUIDO_A}}`, `{{LIQUIDO_B}}`, `{{FGTS_TOTAL}}`, `{{PROVISOES_TOTAL}}`, `{{CUSTO_SIMPLES}}`, `{{SUBSIDIO_VT}}`, `{{VR_TOTAL}}`, `{{PARTIDAS_DOBRADAS}}`, `{{IMPACTO_EXCLUSAO_SIMPLES}}`); a tabela de rubricas ganha a coluna **Fórmula** (`formula_texto`) e os recibos passam a ser gerados do banco | ❓ |
| FO-03 | Doc 13 audita a **entrega anterior da dupla (V1)**, não o cliente: AUD-02 (comissão omitida na V1), AUD-03 (salário-família na V1), AUD-04 (VR/negocial/provisões omitidos na V1), AUD-05 (piso R$ 1.580 na V1), AUD-06 (CNAE 4530-7/01 na V1) e a coluna "Folha original V1" do PT-03 | EC02 p. 4, aulas 14 e 15 (auditoria da completude do prontuário, tempestividade dos eventos, aderência à CCT, recálculo e cruzamento folha × eSocial × FGTS Digital); régua C-34 (recálculo "comparado com a planilha") e C-37/C-38 | Achados passam a ser do cliente na competência 09/2026 (proposta abaixo) | ❓ decisão |
| FO-04 | Afirmações não verificáveis sobre a planilha ("220 fórmulas recalculadas no Microsoft Excel, 0 erros, 0 células sem cache"); a planilha real é gerada pela plataforma (abas Leia-me, Parametros, Folha_Set2026, Memoria_Calculo, Provisoes_e_Integracao) e o Leia-me tem R$ 504,00, R$ 4.238,00 e "VT 4x2" digitados | Regra da plataforma | Texto cita a planilha gerada; Leia-me sem números fixos (código) | ❓ |
| FO-05 | Doc 13: data 23/11/2026 e "Revisão Definitiva" (fora da linha do tempo do caso: auditoria nas aulas 14–15, 05 e 07/10/2026; entrega em 14/10/2026) | EC02 p. 4 | Data do relatório 07/10/2026 | ❓ |
| FO-06 | AUD-01 com faixa de multa "R$ 1.129 a R$ 6.708 (Portaria MTP 667/2021)" sem fonte conferida | — | Citar CLT art. 168 e NR-7; multa "conforme gradação da NR-28", sem valor inventado | ❓ |
| FO-07 | Registro "SRT00189/2025" ainda em parâmetros (CCT-PISO-GERAL e CCT-PISO-VEND: `norma_citada`), na auditoria (PT-02, AUD-05), no Doc 11, no Doc 13 e na planilha (abas Parametros e Leia-me); apontamentos antigos "Conferir … SRT00189/2025 antes de homologar" em parâmetros já homologados | DP-07; AULA p. 29 | Mesmo tratamento do DP-07 | ❓ |
| FO-08 | L3 credita "1.1.4.01 Adiantamentos de Benefícios VT/VR", mas o Doc 12 diz que a compra dos benefícios acontece em outubro ("eventos subsequentes"): sem lançamento de compra em setembro, o adiantamento fica com saldo credor | NBC TG (competência); coerência L3 × fluxo financeiro | Creditar passivo "VT/VR a pagar (operadoras)", baixado na compra em outubro (alteração no motor) | ❓ decisão |
| FO-09 | VR chamado de "PAT" (rubrica, conta 4.1.1.06, planilha). A adesão ao PAT não consta do caso; a não incidência vem da CLT art. 457, §2º (auxílio-alimentação não pago em dinheiro) | EC02 p. 3; AULA p. 27 ("validar instrumento, não presumir incidência") | Nome "Vale-refeição (CLT art. 457, §2º)"; PAT só como possibilidade na PR-09 | ❓ |
| FO-10 | Fundamentação do salário-família no Doc 11 ("Decreto 3.048/1999, art. 82 determina que no mês de admissão o direito é aferido pela remuneração contratual integral") sem conferência do texto da norma; a aula trata o ponto como desafio | AULA p. 24 | Doc 11 cita só a Portaria e a aula e remete o critério à PR-06 (conferir a norma na etapa 5) | ❓ |
| FO-11 | Restos de 4 passagens no motor: texto da fórmula do subsídio "(sensib 2/dia = …)", alerta OP-01 com R$ 4.128,00 / R$ 3.956,00 digitados; apontamento da competência "lotes L1–L4 (R$ 4.238)" | — | Limpeza no código e no registro | ❓ |
| FO-12 | Observação (sem correção): a régua C-29 diz "férias R$ 266,67 e 1/3 R$ 37,33". Os números batem com o L4 do motor (férias + 1/3 = R$ 266,67; FGTS sobre provisões = R$ 37,33); o "1/3" do texto da devolutiva corresponde ao FGTS | DEV G07 p. 3 | Nenhuma; registrado para a leitura da nota | ✅ |
| FO-13 | Data de pagamento da folha gravada como 07/10/2026 (`folha_competencia.data_pagamento`). Se o sábado contar como dia útil na contagem do 5º dia útil (entendimento do MTE), o prazo seria 06/10/2026. O SQL 11 deixou os textos com "até o 5º dia útil de outubro (CLT, art. 459, § 1º)", sem data | CLT, art. 459, § 1º | Conferir a norma de contagem na etapa 5 e ajustar a data na tela da folha | ✅ PRM-08 (06/10/2026, SQL 12) |

**Proposta para o FO-03 (achados do cliente, competência 09/2026):**

| Código | Achado | Evidência | Risco |
|---|---|---|---|
| AUD-01 | ASO admissional não realizado antes do início (E1 e E2) | Q7 (DEV G07 p. 3); PEND-01 | Crítico |
| AUD-02 | Admissões sem comprovação de envio do S-2200 até o dia anterior ao início (tempestividade) e termos VT/VR não assinados | Tabela de eventos (doc. 06); DOC-12; AULA p. 23 | Alto |
| AUD-03 | Documentos civis e do dependente não apresentados (prontuário incompleto) | DOC-09; EC02 p. 3 | Médio |
| AUD-04 | Comissão do E2 calculada sobre premissa didática, sem relatório comercial de vendas | AULA p. 25; DOC-13; PEND-05 | Médio |
| AUD-05 | Jornada do E1: 41h no horário informado × 44h contratuais | EC02 p. 2; PEND-04; PR-11 | Médio |
| AUD-06 | Risco de exclusão do Simples (CNAE 4541-2/01 com importação), com sensibilidade de encargos da folha calculada pelo motor | Doc. 01; PEND-02; LC 123/2006, art. 17, VIII | Crítico |
| AUD-07 | SST além do ASO (inventário de riscos PGR/DIR, PCMSO), controle de ponto e pró-labore indefinidos | Resposta Q4 (carta p. 3); PEND-07; PEND-08 | Alto |

As correções da V1 (comissão, salário-família, VR, negocial, provisões, piso) saem do quadro de achados; o recálculo independente (tabela gerada) mostra a folha conforme.

Decisões da usuária (27/11/2026): **FO-03 aprovado** (achados do cliente, não da V1) e **FO-08 aprovado** (L3 credita passivo "VT/VR a pagar"). Demais propostas FO aprovadas. Código na branch `d2-etapa4-folha` + `docs/revisao_d2_sql/11_docs11a13_folha.sql`. O Doc 13 ganhou o AUD-08 (contingência trabalhista, G-08) e o AUD-07 incorporou a retirada informal dos sócios (G-09). Ordem: merge → deploy → "Recalcular" na tela da folha → SQL 11.

## Respostas do professor no grupo da disciplina (informadas pela usuária em 27/11/2026)

Classe: **original registrado** (respostas do cliente dadas pelo professor no grupo). Falta registrar o texto no acervo (SQL próprio, como o 07).

| Nº | Resposta | Impacto | Onde tratar |
|---|---|---|---|
| G-01 | Integralização: data correta **31/07/2026**; "31/07/2025" na consolidação é errata. Os R$ 500.000 **não** foram integralizados (extratos simulados não podem ter esse lançamento) | Doc 01 trata como "conflito de datas" → passa a "errata confirmada pelo cliente; prazo de 31/07/2026 vencido, sócios em mora" | Doc 01 (linha nova na Estação 2); D3 (extratos) |
| G-02 | Filial de Itajaí: objeto registrado errado; finalidade real é **só importação de pneus**. Sócio acha que filial exige sair do Simples ("vocês é que vão nos orientar") | Reforça R-01 (depurar CNAEs da filial na 3ª Alteração); orientar que o Simples não veda filial (o limite de receita é da empresa toda) | Doc 01 / PEND-02; parecer tributário (D2 Doc 01 ou D3) |
| G-03 | Regime supletivo (Cl. 18ª): sem resposta, "dependemos do que vocês vão nos orientar" | Orientação nossa na 3ª Alteração | Doc 01 / PEND-02 |
| G-04 | Cônjuge de Helena: **João Alves Duarte**, mesmo endereço; nenhum ato depende de outorga uxória | Qualificação dos sócios; sem providência | Doc 01 (qualificação) |
| G-05 | Faturamento dos últimos 12 meses **R$ 2.878.147,98**; Simples Nacional desde o início | Porte **EPP** (acima de R$ 360 mil); base do RBT12 | Doc 01 (enquadramento) e D3 |
| G-06 | Escritório anterior **Sócontas Ltda.**: obrigações acessórias dos últimos seis meses não entregues; sistema **Domínio** | Confirma Q8/PEND-03; migração de dados do Domínio | Doc 05 (Q8/PEND-03: nova fonte) |
| G-07 | Importação a simular: 1.000 pneus de Singapura a USD 18,79 (INCOTERM, frete, câmbio e NCM ficam como premissa dos alunos) | D3 | D3 |
| G-08 | **Contingência: causa trabalhista de R$ 120.987,00** (detalhes "com o advogado") | Achado de auditoria trabalhista (avaliação de provisão/divulgação depende do advogado) | Doc 13 (AUD-08); D4 (NBC TG 25) |
| G-09 | Pró-labore/distribuição: "80% do lucro líquido do mês", informal e verbal, sem valor fixado | Sócios administradores sem pró-labore formal e retirada informal: risco previdenciário e de distribuição sem lastro contábil | Doc 13 (AUD-07); PEND-08; S-2300 |
| G-10 | Assinatura individual para todos os atos, sem limite de alçada | Risco de governança (já apontado no Doc 01) | Doc 01 |
| G-11 | Sindicato/CCT: sócio não sabe responder (o aluno apura em fonte oficial) | Confirma a CCT como apuração da dupla (premissa didática da AULA p. 21; PR-03) | Doc 06 seção 3 / PR-03 |

Novo achado ligado ao G-01: **D01-b** — o Doc 01 (seção 3) ainda traz a linha "Documentos de DP da 1ª entrega (v1) × Cl. 2ª Alteração" (autoauditoria da V1, mesmo problema do FO-03). Tratar junto com o G-01 na revisita do Doc 01.

Sobre as perguntas enviadas ao professor: o G-06 e o G-08 respondem parte da pergunta sobre as respostas consolidadas de 24/09/2026; a manifestação do advogado continua sem resposta (o G-08 remete ao advogado).

Merge da branch `d2-etapa4-folha` no master (2d54125), recálculo na tela da folha e SQL 11 rodado pela usuária em 27/11/2026: auditoria 13/13, rubricas 23/23, lançamentos L1–L4 4/4, seções 17/17 homologados. **Etapa 4 ✅.**

## Etapa 5 — Estação 5, Premissas e IA (Docs 14 e 15 → P8, P9)

Pendências herdadas para esta etapa: PR-01, 02, 08, 11, 19 e 20 aguardando homologação; DP-08 resolvido (tarifa); FO-10 (critério do salário-família, PR-06); FO-13 (contagem do 5º dia útil); citar como fonte as respostas do grupo G-05, G-09 e G-11 nas premissas afetadas.

Régua (devolutiva G07): C-40 a C-43 (P8) e C-44 a C-47 (P9).

Verificações em fonte oficial feitas em 27/11/2026 (Claude Code, busca e leitura das páginas):
- **Salário-família:** Portaria Interministerial MPS/MF nº 26/2023, art. 4º, § 2º ("o direito à cota do salário-família é definido em razão da remuneração que seria devida ao empregado no mês, independentemente do número de dias efetivamente trabalhados") e § 4º (cota proporcional nos meses de admissão e demissão). A portaria de 2026 (nº 13/2026) repete a estrutura com os valores de 2026 (cota R$ 67,54; limite R$ 1.980,38 — aula de DP, p. 24). O texto de 2026 não foi lido diretamente.
- **Resolução CFC nº 1.708/2023:** ementa "Dispõe sobre o registro das organizações contábeis"; art. 28 revoga a Res. CFC nº 1.555/2018 (legisweb, DOU 21/11/2023).
- **Resolução CFC nº 1.590/2020:** ementa "Regulamenta a obrigatoriedade do contrato de prestação de serviços contábeis"; art. 1º e 5º (contrato escrito após a proposta), art. 2º (conteúdo mínimo: serviços, duração, honorários, prazo de pagamento, cláusula rescisória), art. 6º (distrato obrigatório e notificação do cliente), art. 7º e 9º (devolução de documentos), art. 8º (comunicação ao novo responsável técnico). Art. 11 revogado pela Res. CFC nº 1.703/2023.
- **CCT SECEG × SINDILOJAS-GO:** o registro "SRT00189/2025" não foi localizado. A lista de CCTs de Goiás (Pontotel, 212 convenções) traz outras CCTs do SINDILOJAS-GO 2025/2027 no formato do Mediador (SECCAN GO000379/2025, SECIP GO000758/2025, SECSHEGO GO000822/2025) e nenhuma com o SECEG. Notícias de 2026 relatam impasse entre SINDILOJAS-GO e SECEG. A aula manda usar SECEG × SINDILOJAS-GO como **premissa didática** (p. 21) e o cliente não sabe o sindicato (G-11).
- **5º dia útil:** a maioria das fontes (secundárias) inclui o sábado na contagem (Instrução Normativa nº 1/1989, texto oficial não lido). Com o sábado, o 5º dia útil de outubro/2026 é **06/10/2026** (01 qui, 02 sex, 03 sáb, 05 seg, 06 ter); sem o sábado, 07/10/2026.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
| PRM-01 | Doc 14: a seção 2 (registro numerado, 14,9 mil caracteres) e a seção 3 (quadro de decisões, com 4 passagens, R$ 234,00, R$ 917,40, AUD antigos) duplicam as tabelas 1 e 2 geradas do banco; cabeçalho com "Revisão Definitiva 23/11/2026" e "PR-01 a PR-18" (são 20) | Régua C-41/C-42; regra da plataforma | Seções 2 e 3 viram texto curto que remete às tabelas; cabeçalho sem data legada | ✅ SQL 12 |
| PRM-02 | Premissas com valores digitados ou referências à V1 em `resposta_autoral` / `decisao_impactada` (PR-04, 05, 06, 07, 09, 10, 12, 16, 17: R$ 2.416,30, R$ 4.128,00, R$ 4.238,00, R$ 2.247,20, R$ 917,40, "corrige a v1") | Régua C-24 e C-42 | Texto da decisão sem números calculados (remete aos docs 11 e 12); parâmetros oficiais (faixas, cotas, pisos) continuam citados | ✅ SQL 12 |
| PRM-03 | 14 premissas sem `impacto_se_alterada` e/ou `responsavel_decisao` e `prazo_decisao` (PR-03 a 07, 09, 10, 12 a 18) | Régua C-41 ("quem decide e quando") e C-42 ("impacto") | Preencher os três campos nas 20 premissas | ✅ SQL 12 |
| PRM-04 | PR-01 adota porte **ME** como premissa ("o caso não informa faturamento"), mas o cliente informou no grupo faturamento de 12 meses de **R$ 2.878.147,98** (G-05) | G-05; LC 123/2006, art. 3º, II | Porte **EPP**, com a receita informada pelo cliente como fonte; Doc 01 e D3 a revisitar | ✅ SQL 12 |
| PRM-05 | PR-06 fundamentada no "Decreto 3.048/1999, art. 82"; a regra do mês de admissão está na portaria interministerial (art. 4º, §§ 2º e 4º) | Portaria Interministerial (texto 2023 conferido) | Trocar a fundamentação; resolve o FO-10 | ✅ SQL 12 |
| PRM-06 | **Resolução CFC nº 1.708/2023 citada como norma do contrato, da transferência de RT e do distrato** nos Docs 02, 03 e 04 (já homologados), no Doc 01 (R-07), no Doc 00, na PR-14, na PR-20 e no Doc 15. A 1.708/2023 trata do **registro** das organizações contábeis; o contrato, o distrato e a comunicação ao novo RT estão na **Res. CFC nº 1.590/2020** | Res. CFC nº 1.708/2023 (ementa, art. 28); Res. CFC nº 1.590/2020 (arts. 1º, 2º, 5º a 9º) | Citar a 1.590/2020 para contrato/distrato/transferência e a 1.708/2023 só para o registro da PRISMA JRNA (CRC-DF 004.821/O-2); linha nova nas etapas 1 e 2 | ✅ SQL 12 |
| PRM-07 | PR-03 com "Registro MTE SRT00189/2025", não localizado; régua C-40 pede número de registro | Pesquisa acima; AULA p. 21; G-11 | Declarar a CCT como premissa didática da aula, com a pesquisa feita (sem registro localizado no Mediador em 27/11/2026) e a pendência de confirmar o sindicato da atividade preponderante | ✅ SQL 12 |
| PRM-08 | FO-13: data de pagamento 07/10/2026; com o sábado na contagem, o prazo é 06/10/2026 | CLT art. 459, § 1º; IN nº 1/1989 (fontes secundárias) | Adotar **06/10/2026** (pagar antes nunca é atraso) e registrar a premissa | ✅ SQL 12 |
| PRM-09 | PR-09 ainda com "PAT" e "dia útil"; PR-15 sem a retirada informal de "80% do lucro" (G-09); PR-18 sem a decisão DP-01 (dados informados verbalmente; documentos a conferir) | FO-09; G-09; DP-01 | Atualizar as três premissas | ✅ SQL 12 |
| PRM-10 | Doc 15 com afirmações falsas ou superadas: "registro MTE SRT00189/2025 conferido no Mediador", "220 fórmulas recalculadas no Excel", "deliberação de 4 passagens/dia", "10 achados AUD-01 a AUD-10", "PR-01 a PR-18", salário-família pelo "Dec. 3.048 art. 82", Res. 1.708 como norma do contrato | Régua C-46 ("qual fonte confirmou o quê") e C-47 | Reescrever as seções com o que foi de fato verificado e as decisões humanas desta revisão | ✅ SQL 12 |
| PRM-11 | Diário de IA: 7 registros legados com as mesmas afirmações (SRT, "confronto triplo v1", "10 achados + 18 premissas") e sem a revisão feita na plataforma em 26–27/11/2026 | Régua C-44 a C-47 | Corrigir os 7 registros e incluir o registro desta revisão (Claude Code: fontes conferidas e decisões da usuária) | ✅ SQL 12 |

Decisões da usuária (27/11/2026): PRM-04 (EPP), PRM-06 (Res. CFC 1.590/2020), PRM-07 (CCT premissa didática) e PRM-08 (06/10/2026) aprovados; demais propostas aprovadas. SQL: `docs/revisao_d2_sql/12_docs14e15_premissas_ia.sql` — 20 premissas reescritas com quem decide, prazo e impacto; data de pagamento 06/10/2026; Docs 14 e 15 (9 seções); diário de IA (5 registros corrigidos + registro desta revisão); homologa 20 premissas, 9 seções e 8 registros do diário. A correção dos Docs 01 a 04 (PRM-06, G-01, G-05, D01-b) fica para o SQL 13. Padrões das pós-condições conferidos por leitura contra os textos atuais.

SQL 12 rodado pela usuária em 27/11/2026: premissas 20/20, seções dos Docs 14–15 9/9, diário de IA 10/10 homologados. **Etapa 5 ✅.**

## Revisita das etapas 1 e 2 (Docs 01 a 05) — SQL 13

`docs/revisao_d2_sql/13_revisita_docs01a05.sql`, conferido por leitura (19 trechos, cada um presente exatamente uma vez):
- **PRM-06:** Res. CFC nº 1.590/2020 no lugar da 1.708/2023 onde o assunto é contrato, distrato, devolução de documentos ou comunicação ao novo RT (Docs 01 R-07, 02, 03, 04; DOC-07 e PEND-03 do Doc 05; registros do termo de RT e do contrato). O Termo de RT cita as duas: a 1.590/2020 (contrato) e a 1.708/2023 (registro da organização contábil).
- **G-01:** "conflito de datas" passa a "errata reconhecida pelo cliente" — a resposta Q5 da carta já dizia "o prazo real que a gente se comprometeu é 31/07/2026"; o G-01 confirma que 31/07/2025 é errata. O prazo de 31/07/2026 está vencido e a mora permanece (Doc 01 seções 2 a 5, título 3.3, cláusula do capital, Doc 04).
- **G-05 / PRM-04:** enquadramento em três períodos — 28/10/2024 a 31/12/2025 ME (premissa), 01/01/2026 a 31/08/2026 EPP e a partir de 01/09/2026 EPP (LC 123/2006, art. 3º, § 9º: EPP no ano-calendário seguinte ao excesso). O Doc 01 mostra o período atual.
- **D01-b:** sai do Doc 01 a linha "Documentos de DP da 1ª entrega (v1)".
- Fica para a etapa 6: Doc 00 (cita a 1.708/2023 e a entrega V1).
