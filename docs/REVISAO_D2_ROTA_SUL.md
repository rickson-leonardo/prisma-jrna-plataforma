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

## Estação 1 — Cadastro (falta só o C-10)

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
| C-10 | Contador da tela "0/2": os dois períodos do enquadramento estavam como "Inconsistência apontada" (status herdado do rascunho) | — | Homologar os dois períodos com justificativa (o risco de CNAE é do caso: PR-02 e R-01). SQL: `docs/revisao_d2_sql/01_estacao1_homologar_enquadramento.sql` | ⏳ |

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

## Estação 2 — 2ª Alteração (Anexo I) — próxima

Os 9 achados de cláusula são **legado** (`importado_rascunho_v2`). Roteiro:
1. Conferir cada achado contra o texto do Anexo I no acervo (arquivo 70, p. 7 a 13). O que bater fica; o que for invenção sai.
2. Preencher os 6 campos novos de cada achado (natureza do risco formal/material, nível, providência, fundamento legal, responsável, prazo), como pede a régua do P1.

| Nº | Achado | Fonte oficial | Solução | Status |
|---|---|---|---|---|
