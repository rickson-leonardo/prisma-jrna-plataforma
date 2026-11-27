-- Dossiê 2, Doc 01 (01_Diagnostico_Societario_Rota_Sul.pdf): revisão e homologação das 7 seções em erp.documento_secao (Opção B).
-- Fontes: Estudo de Caso 02 / Anexo I (arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf, pp. 1–2 e 7–13),
--         Respostas do cliente dadas pelo professor no grupo da disciplina (Solicitação_JRNA.pdf, p. 3; Devolutiva G07, p. 3) e leis vigentes (Planalto, 26/11/2026).
-- Não altera origem_registro. Tudo ou nada.
DO $a$
DECLARE
  v_secoes int;
  v_com_917 int;
  n int;
BEGIN
  -- 1. Pré-condição: 7 seções do Doc 01 em pendente_revisao e 3 ainda com número legado 917,40
  SELECT
    count(*) FILTER (WHERE id IN (431, 432, 433, 434, 435, 436, 437) AND documento = 'd2_01_diagnostico' AND status_validacao = 'pendente_revisao'),
    count(*) FILTER (WHERE id IN (434, 435, 436) AND strpos(conteudo_md, '917,40') > 0)
  INTO v_secoes, v_com_917
  FROM erp.documento_secao
  WHERE empresa_id = 1;

  IF v_secoes <> 7 THEN RAISE EXCEPTION 'Seções do Doc 01 fora do estado esperado (% de 7)', v_secoes; END IF;
  IF v_com_917 <> 3 THEN RAISE EXCEPTION 'Seções com legado 917,40 divergem (% de 3)', v_com_917; END IF;

  -- 2. Atualização e homologação das 7 seções (Opção B: preserva estrutura completa, alinha códigos R-01..R-09, remove legado e inclui CC art. 1.061)
  UPDATE erp.documento_secao AS ds
     SET conteudo_md = v.conteudo_md,
         status_validacao = 'homologado_contadora',
         justificativa_contadora = v.justificativa_contadora,
         atualizado_em = now()
    FROM (
      VALUES
        (
          431::bigint,
$md$# RELATÓRIO DE DIAGNÓSTICO SOCIETÁRIO, CADASTRAL E FISCAL — ANÁLISE TÉCNICA DA 2ª ALTERAÇÃO CONTRATUAL (ANEXO I)

**Dossiê 2 — Onboarding e Departamento Pessoal (Competência 09/2026)**
**Cliente:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda.
**Emissor:** PRISMA JRNA Auditoria e Contabilidade Ltda. — Grupo G07 (Jeovanna Ripardo Lustosa e Nathalia Peres Araujo)
**Destinatário:** Sócios Administradores — Helena Aparecida Mendes Duarte e Bruno Mendes Duarte
**Documento-Fonte Analisado:** Anexo I — 2ª Alteração Contratual e Consolidação do Contrato Social (assinada em 22/07/2025; registrada na JUCEG em 24/07/2025 sob nº `20259999999`, protocolo `259999999`)
**Data de Referência:** Setembro/2026 *(Revisão Final: 26/11/2026)*$md$,
          'Cabeçalho conferido contra o Estudo de Caso 02 (pp. 1, 7 e 13) e atualizado para a revisão de 26/11/2026.'
        ),
        (
          432::bigint,
$md$1. Identificação Completa do Cliente (Matriz e Filial)
2. Diagnóstico Operacional, Contábil, Fiscal e Trabalhista no Onboarding
3. Análise Crítica Dispositivo a Dispositivo do Anexo I
   - 3.1 Denominação Social, Endereços e Inconsistências Formais
   - 3.2 Objeto Social, 18 CNAEs (Matriz) × 17 CNAEs (Filial) e Conflito com o Simples Nacional
   - 3.3 Capital Social (R$ 1.500.000,00), Conflito de Prazos e Mora na Integralização
   - 3.4 Governança, Administração, Quórum 50/50, Três Critérios Conflitantes de Haveres, AGO/Tesouraria, Pró-Labore/JCP e Omissões
4. Matriz Consolidada de Riscos (Formal × Material)
5. Plano de Saneamento (Diretrizes para a 3ª Alteração Contratual e Onboarding)$md$,
          'Sumário conferido e limpo de links âncora internos que não navegam no PDF.'
        ),
        (
          433::bigint,
$md$| Elemento Cadastral | Matriz (Goiânia-GO) | Filial (Itajaí-SC) | Dispositivo no Anexo I |
|---|---|---|---|
| **Razão Social** | ROTA SUL IMPORTADORA, EXPORTADORA, COMÉRCIO E **DISTRIBUIDORA** LTDA *(divergência no título da Consolidação: **DISTRIBUIÇÃO**)* | Mesma razão social (Filial Itajaí-SC) | Preâmbulo (p. 7), Cl. 4ª (Título Consolidação, p. 8) e Cl. 1ª Consolidação (p. 8) |
| **Nome Fantasia** | ROTA SUL IMPORTADORA | ROTA SUL IMPORTADORA | Preâmbulo (p. 7) e Cl. 1ª Consolidação (p. 8) |
| **Natureza Jurídica** | Sociedade Empresária Limitada (CC, arts. 1.052 a 1.087) | Filial da mesma pessoa jurídica | Preâmbulo (p. 7) e Cl. 18ª Consolidação (p. 12) |
| **CNPJ / NIRE** | `11.222.333/0001-81` / NIRE `52900000015` (JUCEG) | `11.222.333/0002-62` / NIRE `42900000012` (JUCESC) | Ficha (p. 2), Preâmbulo (p. 7) e Cl. 1ª, § Único Consolidação (p. 8) |
| **Endereço Atual** | Rua das Mangueiras, Quadra 40, Lote 11, nº 215, Setor Campinas, Goiânia-GO, CEP `74.515-000` *(anterior: Av. das Indústrias, Qd. 12, Lt. 05, nº 320, Vila Aurora Oeste, CEP 74.425-000)* | BR-101, nº 15.000, **Sala 223** *(ficha do caso, p. 2)* × **Sala 223 A 32** *(Anexo I, p. 8)*, Bairro Canhanduba, Itajaí-SC, CEP `88.313-000` | Cl. 1ª Alteração (p. 7); Cl. 1ª e § Único Consolidação (p. 8) |
| **Início e Duração** | 28/10/2024 — prazo indeterminado | Operação de desembaraço aduaneiro e armazenagem | Cl. 2ª Consolidação (p. 8) |
| **Capital Social** | **R$ 1.500.000,00** (1.500.000 quotas de R$ 1,00): **R$ 1.000.000,00 integralizados** + **R$ 500.000,00 a integralizar** | Capital único da sociedade | Cl. 3ª Alteração (p. 8) e Cl. 4ª Consolidação (p. 9) |
| **Quadro Societário** | **Helena Aparecida Mendes Duarte** (CPF `111.444.777-35`, RG `1.111.111` DGPC-GO — **750.000 quotas / 50% / R$ 750.000,00**) e **Bruno Mendes Duarte** (CPF `529.982.247-25`, RG `2.222.222` PC-GO — **750.000 quotas / 50% / R$ 750.000,00**) | Mesma titularidade | Preâmbulo (p. 7), Cl. 3ª § 2º (p. 8) e Cl. 4ª § Único Consolidação (p. 9) |
| **Administração** | Ambos os sócios, assinando individualmente | Mesma representação | Cl. 8ª e Cl. 9ª Consolidação (p. 10) |
| **CNAEs Cadastrados** | **18 CNAEs** (foco: `4530-7/02`, `4530-7/05`, `4541-2/02`, `4541-2/06`; inclui `4541-2/01` atacado de motos, `4541-2/03` varejo de motos, `4511-1/02` automóveis usados sob "Importação" e `8211-3/00`) | **17 CNAEs** (reproduz os da Matriz, **omitindo `8211-3/00`**) | Cl. 2ª Alteração (p. 7); Cl. 1ª § Único (p. 8) e Cl. 3ª Consolidação (p. 9) |
| **Regime Tributário** | Simples Nacional (desde out/2024 — sob **alerta crítico de vedação/exclusão**) | Simples Nacional (unicidade CNPJ raiz) | Respostas do cliente dadas pelo professor no grupo da disciplina (`Solicitação_JRNA.pdf`, p. 3) |$md$,
          'Quadro cadastral conferido contra o Estudo de Caso 02 (pp. 2, 7–9) e Respostas do cliente dadas pelo professor no grupo da disciplina (Solicitação_JRNA.pdf, p. 3), alinhado ao cadastro na Estação 1.'
        ),
        (
          434::bigint,
$md$A assunção da contabilidade pela **PRISMA JRNA** a partir de **01/09/2026** revelou seis frentes críticas de risco imediato:

1. **Redirecionamento Operacional e Passivo Societário no Anexo I:** Originalmente voltada ao varejo de automóveis usados (`4511-1/02`), a empresa redirecionou-se à **importação (Ásia) e distribuição de pneus e câmaras de ar para motocicletas** (desembaraço na Filial Itajaí-SC e revenda atacado/varejo pela Matriz Goiânia-GO, EC02 p. 1). Contudo, a 2ª Alteração Contratual (22/07/2025) manteve e adicionou **18 CNAEs heterogêneos** (inclusive motos e automóveis usados sob importação) e apresenta vícios graves de redação, capital, governança e apuração de haveres.
2. **Risco Tributário Crítico (Simples Nacional × CNAEs de Motos/Automóveis sob Importação):** A presença de `4541-2/01` (atacado de motos), `4541-2/03` (varejo de motos) e `4511-1/02` (automóveis usados) sob o título "IMPORTAÇÃO E EXPORTAÇÃO" do objeto social expõe a empresa à **vedação do art. 17, inciso VIII, da LC nº 123/2006** (importação de automóveis e motocicletas). A eventual exclusão do Simples Nacional desloca a tributação para fora do DAS — com perda do recolhimento da CPP no DAS e incidência integral dos encargos patronais sobre a folha e provisões (ver decisão PR-02 e análise de sensibilidade calculada no doc. 12).
3. **Omissão Contábil e Fiscal (Março a Agosto/2026):** Conforme **respostas oficiais do cliente (24/09/2026, referidas na Devolutiva G07, p. 3 — pendência de arquivo primário P-01; ver doc. 05 e `PEND-03`)**, sob a contabilidade anterior (*Sócontas / Dr. Osvaldo*) houve paralisação da escrituração e ausência de transmissão do PGDAS-D durante 6 competências, gerando risco de MAED, juros SELIC, exclusão do Simples por débitos e **vedação legal à distribuição de lucros** (**Lei nº 4.357/1964, art. 32** — multa de 50%).
4. **Mora na Integralização do Capital Social (R$ 500.000,00):** Os sócios confirmaram formalmente (*Solicitação_JRNA.pdf*, p. 3) que **não integralizaram os R$ 500.000,00** nem retificaram o conflito de datas (`31/07/2026` × `31/07/2025`). Em setembro/2026, o prazo encontra-se **vencido sob ambas as datas**, configurando mora societária (CC, arts. 1.004, 1.052 e 1.058).
5. **Admissões sem ASO (NR-7), Falta de Ponto e Pendências SST (`S-2240`):** Os dois primeiros empregados (adm. 16/09 e 21/09/2026) iniciaram atividades sem ASO admissional, sem sistema de ponto (sócios planejavam anotar em papel/celular — *Solicitação_JRNA.pdf*, p. 3), sem laudos PGR/PCMSO/LTCAT e sem ciência prévia do reflexo de comissões em DSR.
6. **Risco Previdenciário de Pró-Labore (`Cl. 16ª`):** A Cláusula 16ª torna o pró-labore facultativo e não há definição de retirada em 09/2026. Retiradas informais de sócios administradores atuantes expõem a empresa à reclassificação previdenciária (INSS 11% — Lei nº 8.212/1991, art. 12, V, "f"; SC COSIT nº 120/2016) e à multa de 50% por distribuição de lucros com débito fiscal (Lei nº 4.357/1964, art. 32).$md$,
          'Diagnóstico operacional revisado: removido número legado 917,40 (22,22%), corrigida a fonte da omissão mar-ago/2026 (respostas oficiais de 24/09/2026 / P-01) e mantidas as referências literais de Solicitação_JRNA.pdf p. 3.'
        ),
        (
          435::bigint,
$md$### 3.1 Denominação Social, Endereços e Inconsistências Formais

| Dispositivo Exato do Anexo I | Inconsistência Identificada | Classificação | Fundamento Legal |
|---|---|---|---|
| **Cláusula 4ª — Título da Consolidação (p. 8) × Preâmbulo (p. 7), Cl. 1ª Consol. (p. 8) e Certidão (p. 13)** | Divergência na denominação social: grafada como **`DISTRIBUIÇÃO LTDA`** no título da Consolidação (p. 8) e **`DISTRIBUIDORA LTDA`** no preâmbulo (p. 7), Cl. 1ª Consolidação (p. 8) e certidão JUCEG (p. 13). | **Formal (Baixo)** | CC, arts. 1.158 e 1.163; IN DREI nº 81/2020. |
| **Cláusula 1ª, Parágrafo Único da Consolidação (p. 8) × Ficha Cadastral (p. 2)** | Divergência no complemento do endereço da Filial de Itajaí-SC: **`Sala 223 A 32`** no Anexo I (p. 8) versus **`Sala 223`** na ficha de qualificação do caso (p. 2). | **Formal (Médio)** | CC, art. 997, II c/c art. 1.054; IN RFB nº 2.119/2022; IN DREI nº 81/2020. |
| **Cláusula 3ª (p. 8) e Cláusula 4ª da Consolidação — Caput (p. 9)** | Erros literais de redação/concordância: *"pelo **pais**"* (p. 8), *"divididos em 1.500.000 (**um milhão e quinhentos mil reais**) quotas"* e *"a ser **integralizados**"* (p. 9). | **Formal (Baixo)** | Boa técnica registral (IN DREI nº 81/2020). |
| **Documentos de DP da 1ª entrega (v1) × Cl. 2ª Alteração / Cl. 3ª Consolidação** | A 1ª entrega de fichas e folha utilizou erroneamente o CNAE **`4530-7/01`** (peças/acessórios novos), inexistente no Anexo I (que traz **`4530-7/02`** e **`4530-7/05`** para pneumáticos). | **Material / Cadastral** | CONCLA/IBGE; IN RFB nº 2.119/2022. |

### 3.2 Objeto Social, 18 CNAEs (Matriz) × 17 CNAEs (Filial) e Conflito com o Simples Nacional

1. **Divergência entre Matriz (18 CNAEs) e Filial (17 CNAEs) — `Cl. 2ª Alteração` (p. 7), `Cl. 3ª Consolidação` (p. 9) × `Cl. 1ª, § Único Consolidação` (p. 8):**
   - A Matriz lista **18 CNAEs** (incluindo comércio de automóveis usados, pneumáticos, motocicletas/peças, eletrônicos, lustres, máquinas, materiais de construção, objetos de arte e **`8211-3/00` — Serviços combinados de escritório e apoio administrativo**).
   - A Filial de Itajaí-SC lista **17 CNAEs**, **omitindo o CNAE `8211-3/00`** sem justificativa expressa e mantendo atividades alheias ao foco de importação/armazenagem de pneus (ex.: varejo de automóveis usados e objetos de arte), o que amplia obrigações estaduais/municipais desnecessárias e distorce a parametrização fiscal (SEFAZ-SC / RADAR).
2. **Conflito Crítico com o Simples Nacional — `4541-2/01`, `4541-2/03` e `4511-1/02` sob Importação:**
   - **Dispositivo:** `Cláusula 2ª` da 2ª Alteração (p. 7), `Cláusula 1ª, § Único` (p. 8) e `Cláusula 3ª` da Consolidação (p. 9) — incluem expressamente **"IMPORTAÇÃO E EXPORTAÇÃO"** cumulado com **`4541-2/01`** (atacado de motocicletas), **`4541-2/03`** (varejo de motocicletas) e **`4511-1/02`** (automóveis usados).
   - **Base Legal:** **Lei Complementar nº 123/2006, art. 17, inciso VIII** — veda o recolhimento pelo Simples Nacional à empresa *"que exerça atividade de importação ou fabricação de automóveis e motocicletas"*. A venda interna isolada não consta do inciso; o risco nasce da combinação, no mesmo objeto social, do título **"IMPORTAÇÃO E EXPORTAÇÃO"** com os CNAEs de motocicletas e automóveis.
   - **Classificação:** **Risco Material Crítico**. Se a Rota Sul importar motocicletas ou automóveis, ficará sujeita à **exclusão do Simples Nacional** (LC 123/2006, arts. 29 e 30), perdendo o recolhimento da CPP no DAS e passando aos encargos patronais integrais do regime geral (ver decisão PR-02 e análise de sensibilidade calculada no doc. 12).
   - **Observação Adicional (Simples × Importação de Pneus):** A importação e distribuição de **pneumáticos e câmaras de ar** (`4530-7/02` e `4530-7/05`) não é vedada pelo art. 17, mas exige controle rigoroso fora do DAS (II, IPI, PIS/COFINS-Importação monofásico da Lei nº 10.485/2002, ICMS-Importação e ICMS-ST) e monitoramento do teto de receita bruta (R$ 4,8 milhões/ano).

### 3.3 Capital Social (R$ 1.500.000,00), Conflito de Prazos e Mora na Integralização

| Dispositivo Exato do Anexo I | Achado Técnico | Classificação | Fundamento Legal |
|---|---|---|---|
| **Cláusula 3ª, § 1º (Alteração, p. 8) × Cláusula 4ª (Consolidação, p. 9)** | **Conflito frontal de datas** para integralização da parcela de **R$ 500.000,00** (aumento de R$ 1.000.000,00 para R$ 1.500.000,00): a Cl. 3ª, § 1º fixa **`31/07/2026`**, enquanto a Cl. 4ª da Consolidação fixa **`31/07/2025`** (9 dias após a assinatura em 22/07/2025). | **Material Crítico** | CC, arts. 997, III e 1.052. |
| **Cláusula 4ª + Cláusula 6ª + Cláusula 7ª (pp. 9–10) × Resposta do Cliente (`Solicitação_JRNA.pdf`, p. 3)** | Em **14/09/2026**, os sócios confirmaram que **nada foi integralizado** dos R$ 500.000,00 e nenhuma retificação foi feita. Logo, **mesmo sob o prazo de `31/07/2026`, ambos os sócios já estão em mora** (sócios remissos), respondendo **solidariamente** pela integralização integral perante terceiros. | **Material Crítico** | **CC, art. 1.004** (mora e indenização por dano emergente), **art. 1.052** (responsabilidade solidária na Ltda.) e **art. 1.058** (notificação de 30 dias pela Cl. 7ª, exclusão ou redução do capital). |

> *Reflexo Contábil no Patrimônio Líquido:* O saldo de R$ 500.000,00 deve figurar na conta redutora **Capital Social a Integralizar** (Capital Subscrito R$ 1.500.000,00 menos R$ 500.000,00 = Capital Integralizado R$ 1.000.000,00).

### 3.4 Governança, Administração, Quórum 50/50, Três Critérios Conflitantes de Haveres, AGO/Tesouraria, Pró-Labore/JCP e Omissões

| Dispositivo Exato do Anexo I | Análise Crítica | Classificação | Fundamento Legal |
|---|---|---|---|
| **Cl. 7ª § 1º, Cl. 8ª–9ª, Cl. 10ª, Cl. 13ª, Cl. 14ª § 1º (pp. 10–12)** | **Quórum 50/50, Impasse (*Deadlock*), Alçada e Ilegalidade na Cl. 10ª:** Cada sócio detém **50%** (750.000 quotas), mas as cláusulas exigem **51% ou "maioria do capital"** (destituição, lucros/JCP, exclusão extrajudicial na Cl. 14ª § 1º e sócio remisso), tornando-as inaplicáveis sem consenso. As **Cls. 8ª–9ª** dão assinatura individual sem limite de alçada financeira. Além disso, a **Cl. 10ª** prevê nomear administrador não sócio por **51%**, violando o **art. 1.061 do CC** (redação da Lei nº 14.451/2022), que exige aprovação de no mínimo **2/3 dos sócios** enquanto o capital não estiver totalmente integralizado. | **Material Alto** | CC, arts. 1.010, § 2º, **1.061** (Lei nº 14.451/2022), 1.076 e 1.085. |
| **Cl. 5ª, I–II (p. 9) × Cl. 12ª, caput e §§ 1º/3º/4º (p. 11) × Cl. 14ª, I–IV e § 4º (pp. 11–12)** | **TRÊS Critérios Conflitantes de Apuração de Haveres no mesmo contrato:** **(1) Cl. 5ª, I:** valor das quotas corrigido pelo **IGPM-FGV + juros 3% a.a.**, em **24 parcelas** (1º venc. 90d), com renúncia a outra fórmula (inc. II); **(2) Cl. 12ª, §§ 1º e 4º:** **Balanço Especial** em 30 dias, em **10 parcelas** (1º venc. 30d), aplicável à retirada voluntária (§ 4º); **(3) Cl. 14ª, I–IV:** **Valor de mercado** por avaliadoras (sem prazo de pagamento e citando IGPM-FGV no inc. IV), também aplicável à retirada voluntária e exclusão — choque frontal com a Cl. 12ª § 4º. | **Material Alto** | CC, art. 1.031 e CPC, arts. 604 e 606 (balanço de determinação como regra supletiva diante de cláusula contraditória). |
| **Cláusula 5ª, inciso IV (p. 9)** | **AGO e Tesouraria em Ltda.:** Determina que quotas adquiridas pela sociedade serão distribuídas na *"primeira **AGO (Assembleia Geral Ordinária)** subsequente à aquisição pela **tesouraria**"*. AGO é instituto de S.A. (em Ltda. adota-se Reunião ou Assembleia de Sócios — CC art. 1.072) e aquisição de quotas próprias exige regência supletiva válida da Lei das S.A. | **Material Alto** | CC, art. 1.053, § único e art. 1.072; Lei nº 6.404/1976, art. 30. |
| **Cláusula 18ª (p. 12)** | **Regência Supletiva Contraditória:** Prevê aplicar nas omissões *"as normas da **Sociedade Simples conjuntamente com as normas da Sociedade Anônima**"*. Os regimes não se acumulam sem ordem: o art. 1.053 do CC impõe a Sociedade Simples como regra geral, facultando optar supletivamente pela Lei das S.A. | **Material Médio** | CC, art. 1.053, caput e parágrafo único. |
| **Cláusula 15ª (p. 12)** | **Quórum Legal Desatualizado (`3/4`):** Exige **3/4 do capital** para incorporação, fusão, dissolução, reforma e escolha de liquidante, reproduzindo dispositivo anterior à **Lei nº 14.451/2022** — que alterou o art. 1.076 do CC reduzindo o mínimo legal para **mais da metade do capital social** (e separando a deliberação de liquidante). | **Material Médio** | CC, arts. 1.071 e 1.076, II–III (redação da Lei nº 14.451/2022). |
| **Cláusula 11ª × Cláusula 10ª, § 2º (pp. 10–11)** | **Conflito de Mandato dos Sócios Administradores:** A Cl. 11ª aplica aos sócios administradores as mesmas cláusulas dos administradores não sócios — e a Cl. 10ª, § 2º limita o mandato destes a **3 anos**, criando ambiguidade sobre o prazo de mandato de Helena e Bruno. | **Material Alto** | CC, arts. 1.060, 1.061 e 1.063, § 1º. |
| **Cláusula 13ª, §§ 1º–3º (p. 11) e Cláusula 16ª (p. 12)** | **JCP (TJLP), Pró-Labore e Bloqueio de Lucros:** (1) **JCP** (Cl. 13ª § 1º) é oneroso/inadequado no Simples Nacional (incide 15% IRRF sem dedutibilidade); (2) **Pró-labore** (Cl. 16ª) aparece como facultativo (`"poderão"`), gerando risco previdenciário caso haja retiradas informais (SC COSIT 120/2016); (3) **Lei nº 4.357/1964, art. 32** veda distribuir lucros (inclusive antecipados da Cl. 13ª §§ 2º–3º) enquanto houver débitos fiscais de mar–ago/2026 sem garantia (multa 50%). | **Material Alto** | Lei nº 9.249/1995, art. 9º; LC nº 123/2006, art. 14 § 2º; Lei nº 8.212/1991, art. 12, V, "f"; SC COSIT nº 120/2016; **Lei nº 4.357/1964, art. 32**. |$md$,
          'Análise crítica dispositivo a dispositivo revisada: incluídos erro "pelo pais", ilegalidade da Cl. 10ª (CC art. 1.061 = 2/3), alçadas nas Cls. 8ª-9ª, páginas exatas do EC02 e remoção do número legado 917,40.'
        ),
        (
          436::bigint,
$md$| ID | Dispositivo Exato do Anexo I / Origem | Achado Técnico | Classificação | Gravidade | Impacto Principal |
|---|---|---|---|---|---|
| **R-01** | Cl. 2ª Alt. (p. 7), Cl. 1ª § Único (p. 8) e Cl. 3ª Consol. (p. 9) | Objeto heterogêneo + `4541-2/01`, `4541-2/03` e `4511-1/02` sob "Importação e Exportação" frente à vedação do Simples Nacional | **Material** | **Crítica** | Exclusão do Simples (LC 123/2006, arts. 17, VIII, 29 e 30) e perda do recolhimento da CPP no DAS (ver PR-02 e doc. 12). |
| **R-02** | Cl. 3ª § 1º Alt. (p. 8) × Cl. 4ª Consol. (p. 9) + Cls. 6ª–7ª | Capital de R$ 500.000,00 não integralizado (`Solicitação_JRNA.pdf`, p. 3) + conflito `31/07/2026` × `31/07/2025` | **Material** | **Crítica** | Sócios em mora (CC, arts. 1.004 e 1.058) e responsabilidade solidária pela integralização (CC, art. 1.052). |
| **R-03** | Cl. 5ª I (p. 9) × Cl. 12ª §§ 1º/4º (p. 11) × Cl. 14ª I–IV (pp. 11–12) | Três critérios conflitantes de apuração de haveres (IGPM+3% / Balanço Especial / Valor de Mercado) | **Material** | **Alta** | Litigiosidade e aplicação supletiva do Balanço de Determinação na saída ou exclusão de sócio (CC art. 1.031 / CPC art. 606). |
| **R-04** | Cls. 7ª–11ª, Cl. 14ª § 1º e Cl. 15ª (pp. 10–12) | Quórum 50/50 sem *deadlock*, ausência de alçada, Cl. 10ª com 51% (viola CC art. 1.061 = 2/3), mandato (Cl. 11ª) e Cl. 15ª com 3/4 revogado | **Material** | **Alta** | Paralisia decisória, nulidade de nomeação de diretor não sócio e risco operacional de assinatura isolada sem limite. |
| **R-05** | Cl. 5ª IV (p. 9) e Cl. 18ª (p. 12) | Institutos de S.A. (`AGO/tesouraria`) em Ltda. e regência supletiva contraditória (Sociedade Simples + S.A.) | **Material** | **Média** | Antinomia jurídica frente ao art. 1.053 do CC e exigência registral na Junta Comercial. |
| **R-06** | Título Consol. (p. 8), Cl. 1ª § Único (p. 8) e Cls. 3ª–4ª | Denominação `DISTRIBUIÇÃO × DISTRIBUIDORA`, filial `Sala 223 × Sala 223 A 32` e erros redacionais literais (`"pelo pais"`, `"reais) quotas"`) | **Formal** | **Baixa / Média** | Divergência cadastral entre contrato, cartão CNPJ, JUCEG, JUCESC, SEFAZ-SC e DBE Redesim. |
| **R-07** | Respostas oficiais 24/09/2026 (Devolutiva G07, p. 3 — P-01) | Omissão fiscal/contábil de mar–ago/2026 sob o contador anterior (*Sócontas / Dr. Osvaldo*) e ausência de transferência técnica | **Material** | **Alta** | MAED, juros SELIC, exclusão do Simples por débitos e proibição de distribuir lucros (Lei 4.357/1964, art. 32). |
| **R-08** | Cl. 1ª § Único (p. 8) × Cl. 3ª Consol. (p. 9) | Assimetria Matriz (18 CNAEs) × Filial (17 CNAEs, omite `8211-3/00`) e necessidade de protocolo sincronizado GO/SC | **Formal / Regulatório** | **Média** | Exigência na JUCEG/JUCESC e distorção na parametrização fiscal/aduaneira da filial em Itajaí-SC. |
| **R-09** | Cl. 13ª §§ 1º–3º (p. 11) e Cl. 16ª (p. 12) | JCP (TJLP) oneroso no Simples, pró-labore facultativo (`"poderão"`) e distribuição de lucros sem trava de regularidade fiscal | **Material** | **Alta** | 15% IRRF sem benefício no Simples, risco INSS 11% sobre saques (SC COSIT 120/2016) e multa de 50% (Lei 4.357/1964, art. 32). |

> *Nota sobre riscos trabalhistas e SST no onboarding:* A ausência de ASO admissional (NR-7), controle de ponto e laudos SST (`S-2240`) está detalhada no onboarding e nos papéis de auditoria trabalhista (Docs. 05, 06 e 13).$md$,
          'Matriz consolidada de riscos alinhada 100% aos códigos R-01..R-09 da Tabela 4 viva e do saneamento (Estação 3), sem número legado 917,40 e com CC art. 1.061.'
        ),
        (
          437::bigint,
$md$| ID | Achado / Dispositivo no Anexo I | Providência Recomendada (3ª Alteração e Onboarding) | Responsável | Prazo | Risco Mitigado | Fundamento Legal |
|---|---|---|---|---|---|---|
| **R-01** | **Objeto social e Simples** (Cl. 2ª Alt., Cl. 1ª § Único e Cl. 3ª Consol.) | Na **3ª Alteração Contratual**, depurar os CNAEs mantendo os efetivamente exercidos (`4530-7/02`, `4530-7/05`, `4541-2/02`, `4541-2/06`), **excluindo `4541-2/01`, `4541-2/03` e `4511-1/02`** e alinhando os CNAEs estranhos aos pneumáticos (PR-02). | Sócios + Advogado Societário (recomendação RT PRISMA JRNA) | **10 dias / até 20/10/2026** | R-01 (Material Crítico) | LC nº 123/2006, art. 17, VIII, e arts. 29 e 30. |
| **R-02** | **Capital Social e Mora** (Cl. 3ª § 1º Alt. × Cl. 4ª Consol. + Cl. 7ª) | Executar o rito da **Cl. 7ª** (notificação de 30 dias) e, na **3ª Alteração**, comprovar aporte dos R$ 500.000,00 em conta corrente ou reduzir o capital para R$ 1.000.000,00, eliminando o conflito `31/07/2026 × 31/07/2025` e os erros redacionais. | Sócios + Advogado Societário (apoio documental PRISMA JRNA) | **20/10/2026** | R-02 (Material Crítico) | CC, arts. 1.004, 1.031 § 1º, 1.052, 1.058, 1.082 e 1.084. |
| **R-03** | **Apuração de Haveres** (Cl. 5ª I × Cl. 12ª §§ 1º/4º × Cl. 14ª I–IV) | Revogar as disposições conflitantes e consolidar **critério único** para saída, falecimento ou exclusão de sócio pelo **Balanço de Determinação** (CPC, art. 606), com prazo e índice únicos. | Advogado Societário + Sócios (apoio técnico PRISMA JRNA) | **20/10/2026** | R-03 (Material Alto) | CC, art. 1.031; CPC, arts. 604 e 606. |
| **R-04** | **Quórum 50/50, Cl. 10ª, Alçada, Mandato e Cl. 15ª** (Cls. 7ª–11ª, 14ª § 1º e 15ª) | Inserir cláusula de resolução de impasse (*deadlock*: mediação/desempate), fixar alçada para assinatura conjunta, adequar a Cl. 10ª ao **CC art. 1.061 (2/3 dos sócios)**, explicitar mandato indeterminado na Cl. 11ª e atualizar a Cl. 15ª ao **CC art. 1.076** (separando liquidante). | Advogado Societário + Sócios | **20/10/2026** | R-04 (Material Alto/Médio) | CC, arts. 1.010, 1.030, 1.061, 1.063 § 1º, 1.076 e 1.085 (Lei nº 14.451/2022). |
| **R-05** | **AGO/Tesouraria e Regência Supletiva** (Cl. 5ª IV e Cl. 18ª) | Substituir `"AGO/tesouraria"` por **Reunião de Sócios** / quotas em sociedade e definir regência supletiva única na Cl. 18ª (Sociedade Simples como regra geral ou opção exclusiva pela Lei nº 6.404/1976). | Advogado Societário + Sócios | **20/10/2026** | R-05 (Material Alto/Médio) | CC, arts. 1.053, caput e § único, e 1.072; IN DREI nº 81/2020. |
| **R-06** | **Denominação e Endereço Filial SC** (Título p. 8 e Cl. 1ª § Único) | Uniformizar **`DISTRIBUIDORA LTDA`** em todo o contrato e confirmar matrícula/IPTU/locação em Itajaí-SC para padronizar o complemento exato (`Sala 223` vs. `Sala 223 A 32`) na 3ª Alteração e no DBE Redesim. | Sócios + PRISMA JRNA / Advogado Societário | **20/10/2026** | R-06 (Formal Baixo/Médio) | CC, arts. 1.158 e 1.163; IN RFB nº 2.119/2022; IN DREI nº 81/2020. |
| **R-07** | **Omissão Fiscal mar–ago/2026 e Bloqueio de Lucros** (P-01) | Notificar formalmente a contabilidade anterior (*Sócontas / Dr. Osvaldo*) para entrega de acervo e Termo de Transferência (`DOC-07`), levantar extratos OFX (`DOC-08`), transmitir PGDAS-D retroativos mar–ago/2026 e **suspender lucros** até quitação/parcelamento. | PRISMA JRNA + Sócios | **30/10/2026** | R-07 (Material Alto) | RFB (PGDAS-D); Res. CFC nº 1.708/2023; Lei nº 4.357/1964, art. 32. |
| **R-08** | **Protocolo da 3ª Alteração e Sincronização GO/SC** | Protocolar a 3ª Alteração Contratual Consolidada na JUCEG (Goiânia-GO) e sincronizar CNPJ/CNAEs na JUCESC (Itajaí-SC), compatibilizando matriz e filial (inclusive decisão sobre `8211-3/00`). | Órgãos Públicos / Advogado / PRISMA JRNA | **25/10/2026** | R-08 (Regulatório) | Lei nº 8.934/1994; IN DREI nº 81/2020; IN RFB nº 2.119/2022. |
| **R-09** | **Pró-Labore Formal e Exclusão de JCP** (Cl. 13ª § 1º e Cl. 16ª) | Suprimir previsão de JCP na Cl. 13ª, incluir salvaguardas de contabilidade e regularidade fiscal para distribuição de lucros, e formalizar ata/definição de pró-labore dos administradores com eventos `S-2300`/`S-1200` no eSocial (PR-15). | PRISMA JRNA + Sócios | **05/10/2026** | R-09 (Material Alto) | Lei nº 9.249/1995, art. 9º; Lei nº 8.212/1991, art. 12, V, "f"; SC COSIT nº 120/2016. |

> *Encaminhamento imediato de DP/SST no onboarding (Docs. 05, 06 e 13):* ASOs admissionais de E1 e E2 (`S-2220`), controle de ponto e laudos PGR/PCMSO/LTCAT (`S-2240`) seguem acompanhados nas Estações 7 e 8.$md$,
          'Plano de saneamento alinhado 100% às etapas R-01..R-09, prazos, responsáveis e fundamentos legais (incl. CC art. 1.061) da Tabela 4 viva e da Estação 3.'
        )
    ) AS v(id, conteudo_md, justificativa_contadora)
   WHERE ds.empresa_id = 1
     AND ds.documento = 'd2_01_diagnostico'
     AND ds.id = v.id
     AND ds.status_validacao = 'pendente_revisao';

  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 7 THEN RAISE EXCEPTION 'Seções do Doc 01 atualizadas: % (esperado 7)', n; END IF;

  -- 3. Pós-condição: 7/7 homologadas e sem vestígios legados
  SELECT count(*) INTO n
    FROM erp.documento_secao
   WHERE empresa_id = 1
     AND documento = 'd2_01_diagnostico'
     AND status_validacao = 'homologado_contadora'
     AND coalesce(trim(justificativa_contadora), '') <> ''
     AND strpos(conteudo_md, '917,40') = 0
     AND strpos(conteudo_md, '22,22%') = 0
     AND strpos(lower(conteudo_md), 'relato verbal') = 0;
  IF n <> 7 THEN RAISE EXCEPTION 'Pós-condição do Doc 01 falhou (% de 7)', n; END IF;
END
$a$;

SELECT id, ordem, codigo_secao, status_validacao, length(conteudo_md) AS chars
  FROM erp.documento_secao
 WHERE empresa_id = 1 AND documento = 'd2_01_diagnostico'
 ORDER BY ordem;
