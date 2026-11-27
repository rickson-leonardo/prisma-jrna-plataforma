-- Dossiê 2: Doc 16 (rastreabilidade — devolutiva da 1ª entrega × correção × evidência + inconsistências propositais do caso).
-- PRÉ-REQUISITO: deploy da branch d2-doc16 (o documento passa a existir na emissão). As tabelas 1 e 2 saem do banco
-- (auditoria.avaliacao_conformidade, homologada no SQL 17); aqui entram só as 3 seções de texto e a linha do Doc 16 no índice (Doc 00).
-- Tudo ou nada.
DO $a$
DECLARE n int;
BEGIN
  -- Migração 010 (sistema/pg/migrations/010_doc16_rastreabilidade.sql): Doc 16 como documento válido
  ALTER TABLE erp.documento_secao DROP CONSTRAINT IF EXISTS documento_secao_documento_check;
  ALTER TABLE erp.documento_secao ADD CONSTRAINT documento_secao_documento_check CHECK (documento IN (
    'indice', 'pesquisa', 'plano_negocios', 'contrato_social', 'memorando', 'fluxo_abertura',
    'd2_00_indice', 'd2_01_diagnostico', 'd2_02_proposta', 'd2_03_contrato', 'd2_04_termo_rt', 'd2_05_onboarding',
    'd2_06_prontuario', 'd2_07_ficha_e1', 'd2_08_exp_e1', 'd2_09_ficha_e2', 'd2_10_exp_e2', 'd2_11_folha',
    'd2_12_resumo_contab', 'd2_13_auditoria', 'd2_14_premissas', 'd2_15_ia', 'd2_16_rastreabilidade'));
  INSERT INTO auditoria.schema_migration (versao, descricao, aplicado_em)
  VALUES ('010_doc16_rastreabilidade', 'Aplicada a partir de 010_doc16_rastreabilidade.sql (dentro do SQL 18 da revisão D2)', now())
  ON CONFLICT DO NOTHING;

  SELECT count(*) INTO n FROM erp.documento_secao WHERE empresa_id = 1 AND documento = 'd2_16_rastreabilidade';
  IF n <> 0 THEN RAISE EXCEPTION 'Doc 16 já tem seções (%)', n; END IF;
  SELECT count(*) INTO n FROM auditoria.avaliacao_conformidade WHERE dossie = 'D2' AND nota IS NOT NULL AND status_validacao = 'homologado_contadora';
  IF n <> 48 THEN RAISE EXCEPTION 'Avaliações V2 não homologadas (% de 48) — rodar o SQL 17 antes', n; END IF;

  INSERT INTO erp.documento_secao (chave, empresa_id, dossie, documento, ordem, codigo_secao, titulo, conteudo_md, origem_registro, status_validacao, justificativa_contadora)
  VALUES
  ('docsec:d2:d2_16_rastreabilidade:cabecalho', 1, 'D2', 'd2_16_rastreabilidade', 1, 'cabecalho', 'Identificacao e cabecalho do documento',
   $t$# RASTREABILIDADE DAS CORREÇÕES — DEVOLUTIVA DA 1ª ENTREGA, CORREÇÕES E EVIDÊNCIAS

**Dossiê 2 — Onboarding e Departamento Pessoal (Competência 09/2026)**
**Cliente:** Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda.
**Escritório:** PRISMA JRNA Auditoria e Contabilidade Ltda. (Líder: Jeovanna Ripardo Lustosa | Revisão técnica: Nathalia Peres Araujo — CRC-DF `025.431/O-7`)
**Base:** devolutiva oficial do Dossiê 2 (G07), régua "Para chegar ao 4" | **Última revisão:** 27/11/2026$t$,
   'usuario', 'homologado_contadora', 'Doc 16 criado em 27/11/2026 (decisão da usuária): rastreabilidade gerada do banco.'),
  ('docsec:d2:d2_16_rastreabilidade:1_objetivo', 1, 'D2', 'd2_16_rastreabilidade', 2, '1_objetivo', '1. Objetivo e leitura das tabelas',
   $t$Este documento mostra, para cada um dos 48 elementos da régua da devolutiva oficial do Dossiê 2, **o que foi apontado na 1ª entrega, o que foi corrigido e onde está a evidência** nos documentos 00 a 15.
- A **Tabela 1** resume, por produto (P1 a P9), a média da nota da 1ª entrega (devolutiva oficial) e a média da autoavaliação da dupla.
- A **Tabela 2** traz, elemento a elemento, a crítica da devolutiva, a correção feita com a localização da evidência e a autoavaliação.
- A autoavaliação é da dupla e não substitui a nota oficial. Os dois elementos com nota 3 têm a lacuna declarada: a resposta do advogado não foi localizada (C-12) e o número de registro da CCT não foi encontrado no Mediador (C-40).

A seção 2 reúne as inconsistências do próprio caso que a dupla identificou e tratou (o Estudo de Caso avisa que "nem todas as informações serão entregues prontas").$t$,
   'usuario', 'homologado_contadora', 'Doc 16 criado em 27/11/2026 (decisão da usuária).'),
  ('docsec:d2:d2_16_rastreabilidade:2_inconsistencias', 1, 'D2', 'd2_16_rastreabilidade', 3, '2_inconsistencias', '2. Inconsistências do caso identificadas e tratamento',
   $t$| Nº | Inconsistência | Origem | Tratamento | Onde está |
|---|---|---|---|---|
| 1 | Jornada do E1: 08h às 18h com 1h48 de intervalo soma 41h semanais, mas o caso declara 44h | Estudo de Caso 02, p. 2 | Horário literal registrado, sem inventar intervalo ou sábados; definição das 3h com o cliente | Docs. 07 e 08; `PR-11`; `PEND-04`; `AUD-05` |
| 2 | Prazo da integralização: 31/07/2026 (Cl. 3ª, § 1º) × 31/07/2025 (Cl. 4ª da Consolidação), com R$ 500.000,00 não integralizados | Anexo I, pp. 8 e 9 | Errata reconhecida pelo cliente (Q5; resposta no grupo); sócios em mora (CC, arts. 1.004 e 1.058) | Doc. 01 §3.3; R-02 |
| 3 | CNAEs de motocicletas e automóveis sob "Importação e Exportação", vedados no Simples | Anexo I, pp. 7 a 9; LC 123/2006, art. 17, VIII | Exclusão dos CNAEs na 3ª Alteração; sensibilidade de encargos fora do Simples | Doc. 01 (R-01); `PR-02`; `AUD-06` |
| 4 | "Sala 223" × "223 A 32" e "Distribuidora" × "Distribuição" | Anexo I | Padronização na 3ª Alteração | Doc. 01; R-06 |
| 5 | Quórum 50/50 sem desempate, três critérios de apuração de haveres e AGO/tesouraria em sociedade limitada | Anexo I, Cl. 5ª, 12ª, 14ª e 18ª | Cláusula de desempate, critério único de haveres e regência adequada | Doc. 01 §3.4; R-03 a R-05 |
| 6 | Filial de Itajaí com objeto e CNAEs que não correspondem à finalidade real (só importação de pneus) | Anexo I; resposta do cliente no grupo | Depuração do objeto da filial; o Simples não proíbe filial | Doc. 01; `PR-02`; R-01 |
| 7 | ASO admissional não realizado antes do início | Resposta do cliente (Q7) | Pendência real, sem atestar exame inexistente; S-2220 pendente | Docs. 05 e 06; `PEND-01`; `AUD-01` |
| 8 | Documentos de admissão "a apurar" | Estudo de Caso 02, p. 3 | Coleta e conferência (DOC-09) | Docs. 05 e 06; `AUD-03` |
| 9 | Convenção coletiva, piso e sindicato não informados | Estudo de Caso 02, p. 3; resposta do cliente no grupo | CCT da aula como premissa didática; registro não localizado | Doc. 06 §3; `PR-03` |
| 10 | Base de vendas da comissão não informada | Estudo de Caso 02, p. 3; aula de DP, p. 25 | Premissa da aula (R$ 60.000,00); relatório comercial pendente | `PR-07`; `AUD-04` |
| 11 | Retirada dos sócios de "80% do lucro líquido do mês", verbal e sem pró-labore | Resposta do cliente no grupo | Formalizar pró-labore e distribuição com base em escrituração | `PR-15`; R-09; `AUD-07` |
| 12 | Obrigações de março a agosto/2026 não entregues pelo contador anterior | Resposta do cliente (Q8); resposta no grupo | Responsabilidade delimitada no termo de RT; regularização | Docs. 04 e 05; `PEND-03`; R-07 |
| 13 | Causa trabalhista de R$ 120.987,00 sem avaliação do advogado | Resposta do cliente no grupo | Carta de avaliação do advogado; provisão ou divulgação conforme a probabilidade | Doc. 13 (`AUD-08`) |
| 14 | Ponto anotado em papel ou celular e desconhecimento do DSR sobre comissões | Resposta do cliente (Q4) | Controle de ponto formal; DSR em rubrica destacada | Doc. 11; `AUD-07` |$t$,
   'usuario', 'homologado_contadora', 'Inconsistências conferidas (27/11/2026) com o Estudo de Caso 02, o Anexo I, a aula de DP e as respostas do cliente (carta de onboarding e grupo da disciplina).');
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'Seções do Doc 16: %', n; END IF;

  UPDATE erp.documento_secao SET conteudo_md = regexp_replace(conteudo_md,
      '(Finalidade, ferramentas, verificação em fonte oficial e correções humanas \| P9 \|)',
      E'\\1\n| 16 | Rastreabilidade das correções (`16_Rastreabilidade_Devolutiva_Correcoes.pdf`) | Devolutiva da 1ª entrega × correção × evidência, e inconsistências do caso identificadas | — |'),
    atualizado_em = now()
   WHERE empresa_id = 1 AND documento = 'd2_00_indice' AND codigo_secao = '1_inventario_de_documentos_da_en'
     AND strpos(conteudo_md, 'correções humanas | P9 |') > 0 AND strpos(conteudo_md, '16_Rastreabilidade') = 0;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'Doc 00 (inventário): %', n; END IF;
END
$a$;

SELECT documento, codigo_secao, status_validacao FROM erp.documento_secao WHERE documento = 'd2_16_rastreabilidade' ORDER BY ordem;
