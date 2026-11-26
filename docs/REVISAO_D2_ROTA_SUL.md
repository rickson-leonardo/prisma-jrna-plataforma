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
| C-08 | Endereço da filial gravado com texto de análise junto ("Sala 223 (Anexo I: Sala 223 A 32)" e o NIRE) | EC02 p. 2: "Sala 223"; EC02 p. 8: "Sala 223 A 32" | Endereço copiado do acervo exatamente como na ficha do caso (p. 2); a divergência fica no achado R-06. O NIRE da filial (42900000012, EC02 p. 2) não tem campo próprio — 🔁 incluir no plano | ✅ |

| C-09 | Tela: o campo "Responsável técnica" do período da PRISMA aparecia vazio (a lista só tinha sócios do cliente); salvar apagaria a RT | — (defeito de código) | `repo.py`: RT gravada entra na lista de opções (commit `0d4270c`, em produção) | ✅ |
| C-10 | Contador da tela "0/2": os dois períodos do enquadramento estavam como "Inconsistência apontada" (status herdado do rascunho) | — | Homologar os dois períodos com justificativa (o risco de CNAE é do caso: PR-02 e R-01). SQL: `docs/revisao_d2_sql/01_estacao1_homologar_enquadramento.sql` (confirmado em produção: 2/2) | ✅ |
| C-11 | Nome fantasia gravado como `"Rota Sul (Caso D2)"` (rótulo interno; sai na Tabela 1 do PDF do Doc 01) | EC02 pp. 2, 7 e 8: `ROTA SUL IMPORTADORA` | Corrigir `erp.empresa.nome_curto` para `Rota Sul Importadora` no SQL `docs/revisao_d2_sql/03_estacao1_ajustes_finais_cadastro.sql` | ✅ |
| C-12 | Papel dos sócios gravado como código cru `socio_administrador` (sai na tela 1.3 e na Tabela 2 do PDF do Doc 01) | EC02 p. 2 e Cl. 8ª (p. 10): "Ambos os sócios, assinando individualmente" | Corrigir para `Sócia administradora (assina individualmente)` e `Sócio administrador (assina individualmente)` no SQL `03_` | ✅ |
| C-13 | Enquadramento 2024–2026 sem ressalva do objeto anterior à 2ª Alteração (22/07/2025) e `apontamento_auditoria` sem acentos | EC02 p. 1 (atividade original: automóveis usados; DOC-01 pendente) | Acrescentar ressalva histórica na `justificativa_contadora` e corrigir acentuação no SQL `03_` | ✅ |
| C-14 | Barra de progresso da tela `/cadastro` mostra `2/13` (ignora os 11 registros `acervo_referencia`) | — (código `cadastro.html`) | Calcular progresso sobre registros revisáveis (excluindo `acervo_referencia`, exibindo `2/2` + contagem de referências do acervo) | ✅ |
| C-15 | Seção 1.5 não exibe `vigente_ate` (período 2024–2026 parece aberto na tela) | — (código `cadastro.html` / `app.py`) | Exibir `Vigente de DD/MM/AAAA a DD/MM/AAAA` quando `vigente_ate` preenchido (`data_br`) | ✅ |
| C-16 | Rótulos herdados do D1 na tela compartilhada (`sede no Distrito Federal`, `Quadro de Sócias`, dropdown `+ Novo` da 1.4 listando a RT) | — (código `cadastro.html` / `repo.py`) | Adaptar rótulos para D2 e restringir `select` de `Pessoa` da 1.4 (`pessoas_ident`) a empresa + sócios | ✅ |
| C-17 | NIRE da Filial (`42900000012`) sem coluna própria em `erp.estabelecimento` (e sem exibição dedicada no Doc 01) | EC02 p. 2 e p. 8: Matriz `52900000015` (JUCEG) · Filial `42900000012` (JUCESC) | Migração `009_estabelecimento_nire.sql` + UI/PDF aplicados em código; carga oficial no SQL `docs/revisao_d2_sql/04_estacao1_nire_estabelecimento.sql` | ⏳ |

> **Nota de método:** o caso é propositalmente cheio de erros e desvios (é um laboratório da vida real). Corrigimos só o que **a plataforma registrou diferente da fonte**; os erros **do próprio caso** (datas divergentes, CNAEs vedados, jornada incoerente) não são "consertados": viram achados, premissas e providências.
>
> **Lição de processo:** o primeiro envio do SQL falhou ("19 CNAEs"): a linha de continuação "anteriormente;" entrava como vazia. O ensaio usava `string_agg`, que esconde vazios. Ensaios passam a usar a mesma consulta do SQL final.

## Classificação das fontes: original × legado

| Classe | O que é | Como tratar |
|---|---|---|
| **Original** | Material dos professores: Estudo de Caso 02 + Anexo I, aulas, devolutivas, respostas oficiais do cliente | É a premissa do trabalho. Erros e omissões do caso são propositais: viram achados e providências |
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
