-- Dossiê 2: registra no acervo a carta de onboarding da PRISMA (14/09/2026) com, na p. 3, as respostas do cliente
-- dadas pelo professor no grupo da disciplina e transcritas pela dupla (material original registrado por legado).
-- Arquivo: Solicitação_JRNA.pdf | sha256 ec866df087c281521b07f79cbd5b007a3ece1f8161fd02b74131bdda32e967ff | 168176 bytes | 3 páginas | 74 linhas. Tudo ou nada.
DO $blk$
DECLARE v_arq bigint; n int;
BEGIN
  IF EXISTS (SELECT 1 FROM acervo.bru_arquivo WHERE sha256 = 'ec866df087c281521b07f79cbd5b007a3ece1f8161fd02b74131bdda32e967ff') THEN RAISE EXCEPTION 'Arquivo já está no acervo'; END IF;
  INSERT INTO acervo.bru_arquivo (chave, caminho_relativo, nome, extensao, sha256, tamanho_bytes, dossie, dominio, papel_acervo, paginas_total)
  VALUES ($t$arq:D2/Solicitacao_JRNA.pdf$t$, $t$D2/Solicitacao_JRNA.pdf$t$, $t$Solicitação_JRNA.pdf$t$, '.pdf', 'ec866df087c281521b07f79cbd5b007a3ece1f8161fd02b74131bdda32e967ff', 168176, 'D2', 'misto', 'primario', 3) RETURNING id INTO v_arq;
  INSERT INTO acervo.bru_linha (chave, arquivo_id, pagina, n_linha, texto, x0, y0, tam_fonte, fonte, cor_hex) VALUES
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:1$t$, v_arq, 1, 1, $t$Local e Data: Brasília, 14 de setembro de 2026.   $t$, 72.0, 191.9, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:2$t$, v_arq, 1, 2, $t$À Diretoria da Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda. $t$, 72.0, 215.9, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:3$t$, v_arq, 1, 3, $t$A/C: Helena Aparecida Mendes Duarte e Bruno Mendes Duarte $t$, 72.0, 239.9, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:4$t$, v_arq, 1, 4, $t$Assunto: Comunicação de Onboarding - Solicitação de informações e documentações $t$, 72.0, 264.0, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:5$t$, v_arq, 1, 5, $t$preliminares $t$, 72.0, 280.2, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:6$t$, v_arq, 1, 6, $t$Prezados Srs. Sócios, é com grande satisfação que o escritório PRISMA JRNA Auditoria e $t$, 72.0, 304.3, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:7$t$, v_arq, 1, 7, $t$Contabilidade atendem à demanda para assumir a gestão contábil, fiscal e do departamento $t$, 72.0, 320.3, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:8$t$, v_arq, 1, 8, $t$pessoal da Rota Sul Importadora (Matriz-GO e Filial-SC). Nosso objetivo é garantir total $t$, 72.0, 336.4, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:9$t$, v_arq, 1, 9, $t$segurança jurídica e conformidade tributária para a operação de vocês.  Durante a análise $t$, 72.0, 352.4, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:10$t$, v_arq, 1, 10, $t$preliminar da 2ª Alteração Contratual fornecida (registrada em 24/07/2025), nossa equipe $t$, 72.0, 368.4, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:11$t$, v_arq, 1, 11, $t$técnica identificou a necessidade de alinhamento imediato sobre o regime atual da empresa, $t$, 72.0, 384.5, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:12$t$, v_arq, 1, 12, $t$visando dimensionar os honorários, estruturar as admissões urgentes solicitadas para esta $t$, 72.0, 400.6, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:13$t$, v_arq, 1, 13, $t$semana e evitar a geração de passivos fiscais e trabalhistas.  Para prosseguirmos com a $t$, 72.0, 416.5, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:14$t$, v_arq, 1, 14, $t$elaboração da Proposta de Honorários e do Contrato de Prestação de Serviços, solicitamos a $t$, 72.0, 432.6, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:15$t$, v_arq, 1, 15, $t$gentileza de responderem aos questionamentos abaixo e disponibilizarem a documentação $t$, 72.0, 448.7, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:16$t$, v_arq, 1, 16, $t$exigida. $t$, 72.0, 464.6, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:17$t$, v_arq, 1, 17, $t$Questionário Técnico Preliminar $t$, 72.0, 488.6, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:18$t$, v_arq, 1, 18, $t$1. Sobre o Capital Social: O aporte pendente de R$ 500.000,00 foi efetivamente $t$, 90.0, 512.6, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:19$t$, v_arq, 1, 19, $t$integralizado pelos senhores em moeda corrente, conforme a previsão legal? Em caso $t$, 108.0, 528.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:20$t$, v_arq, 1, 20, $t$positivo, o valor transitou integralmente pela conta bancária corporativa da matriz? $t$, 108.0, 544.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:21$t$, v_arq, 1, 21, $t$2. Sobre o Regime Tributário Atual: Qual é o atual enquadramento tributário da Rota $t$, 90.0, 576.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:22$t$, v_arq, 1, 22, $t$Sul perante a Receita Federal (Simples Nacional, Lucro Presumido ou Lucro Real), $t$, 108.0, 592.9, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:23$t$, v_arq, 1, 23, $t$fundamental para calcularmos a tributação das importações?   $t$, 108.0, 609.0, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:24$t$, v_arq, 1, 24, $t$3. Sobre a Operação Aduaneira: A matriz (GO) e a filial (SC) já possuem habilitação $t$, 90.0, 640.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:25$t$, v_arq, 1, 25, $t$ativa no RADAR/Siscomex para operar como importadores diretos de pneumáticos no $t$, 108.0, 657.1, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:26$t$, v_arq, 1, 26, $t$desembaraço aduaneiro em Itajaí?   $t$, 108.0, 673.2, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:27$t$, v_arq, 1, 27, $t$4. Sobre as Admissões: A empresa adotará sistema de controle de ponto (eletrônico ou $t$, 90.0, 705.0, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:28$t$, v_arq, 1, 28, $t$manual) para os dois novos funcionários (Auxiliar e Vendedor)? Para o Empregado 2, $t$, 108.0, 721.3, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:29$t$, v_arq, 1, 29, $t$a comissão de 1,5% sobre vendas líquidas já considera o reflexo obrigatório no $t$, 108.0, 737.3, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:1:30$t$, v_arq, 1, 30, $t$Descanso Semanal Remunerado (DSR)?   $t$, 108.0, 753.4, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:1$t$, v_arq, 2, 1, $t$5. Sobre a Inconsistência Contratual no Anexo I: Notamos um erro material na 2ª $t$, 90.0, 86.6, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:2$t$, v_arq, 2, 2, $t$Alteração Contratual fornecida. A Cláusula Terceira, Parágrafo Primeiro, cita o prazo $t$, 108.0, 102.7, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:3$t$, v_arq, 2, 3, $t$de integralização do aumento de capital para 31/07/2026. No entanto, a Cláusula $t$, 108.0, 118.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:4$t$, v_arq, 2, 4, $t$Quarta (texto consolidado) indica a data de 31/07/2025. Houve alguma retificação ou $t$, 108.0, 134.9, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:5$t$, v_arq, 2, 5, $t$alteração contratual posterior corrigindo esta divergência formal? $t$, 108.0, 150.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:6$t$, v_arq, 2, 6, $t$Checklist de Documentos Iniciais $t$, 72.0, 174.8, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:7$t$, v_arq, 2, 7, $t$Para iniciarmos os trabalhos e a implantação do setor de departamento pessoal, solicitamos a $t$, 72.0, 199.0, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:8$t$, v_arq, 2, 8, $t$disponibilização dos seguintes arquivos: $t$, 72.0, 215.0, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:9$t$, v_arq, 2, 9, $t$1. Ato Constitutivo: Contrato Social Original e a 1ª Alteração Contratual (possuímos $t$, 90.0, 238.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:10$t$, v_arq, 2, 10, $t$apenas a 2ª).  Certificações: Certificados Digitais (e-CNPJ) válidos da Matriz (GO) e $t$, 108.0, 255.1, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:11$t$, v_arq, 2, 11, $t$da Filial (SC) com as respectivas senhas. $t$, 108.0, 271.1, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:12$t$, v_arq, 2, 12, $t$2. Licenciamento: Alvarás de Funcionamento e Inscrições Estaduais atualizadas de $t$, 90.0, 303.0, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:13$t$, v_arq, 2, 13, $t$Goiás e Santa Catarina. $t$, 108.0, 319.2, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:14$t$, v_arq, 2, 14, $t$3. Fechamento Anterior: Balanço Patrimonial, DRE e Balancete de Verificação $t$, 90.0, 351.2, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:15$t$, v_arq, 2, 15, $t$encerrados no mês anterior (Agosto/2026). $t$, 108.0, 367.4, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:16$t$, v_arq, 2, 16, $t$4. Transição Contábil: Termo de Transferência de Responsabilidade Técnica assinado $t$, 90.0, 399.3, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:17$t$, v_arq, 2, 17, $t$pelo contador anterior e cópia do distrato. $t$, 108.0, 415.6, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:18$t$, v_arq, 2, 18, $t$5. Bancário: Extratos bancários (arquivos no formato OFX) de todas as contas $t$, 90.0, 447.4, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:19$t$, v_arq, 2, 19, $t$corporativas ativas. $t$, 108.0, 463.7, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:20$t$, v_arq, 2, 20, $t$6. Societário: Cópia atualizada de documento de identidade com CPF e comprovante de $t$, 90.0, 495.5, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:21$t$, v_arq, 2, 21, $t$residência de ambos os sócios. $t$, 108.0, 511.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:22$t$, v_arq, 2, 22, $t$Ficamos no aguardo do retorno para o envio formal da Proposta Comercial e do Acordo de $t$, 72.0, 535.8, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:23$t$, v_arq, 2, 23, $t$Sigilo para proteção de dados (LGPD). $t$, 72.0, 551.9, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:24$t$, v_arq, 2, 24, $t$ Atenciosamente, $t$, 72.0, 575.9, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:25$t$, v_arq, 2, 25, $t$Nathalia Peres Araujo e Jeovanna Ripardo Lustosa $t$, 72.0, 599.9, 12.0, $t$TimesNewRomanPSMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:2:26$t$, v_arq, 2, 26, $t$Sócias Diretoras | PRISMA JRNA Auditoria e Contabilidade $t$, 72.0, 623.8, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:1$t$, v_arq, 3, 1, $t$RESPOSTAS OFERECIDAS $t$, 72.0, 70.5, 12.0, $t$TimesNewRomanPS-BoldMT$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:2$t$, v_arq, 3, 2, $t$1. Capital Social — "Não, senhores, ainda não colocamos os R$ 500 mil. O prazo que $t$, 72.0, 95.2, 12.0, $t$Aptos-Bold$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:3$t$, v_arq, 3, 3, $t$assumimos é 31/07/2026 — o que está escrito 2025 naquele outro trecho é erro mesmo. $t$, 72.0, 112.2, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:4$t$, v_arq, 3, 4, $t$Como não pagamos nada, não tem lançamento nenhum na conta da empresa, pode $t$, 72.0, 129.2, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:5$t$, v_arq, 3, 5, $t$conferir." $t$, 72.0, 146.3, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:6$t$, v_arq, 3, 6, $t$2. Regime tributário — "A gente está no Simples Nacional desde que abriu a empresa, $t$, 72.0, 171.4, 12.0, $t$Aptos-Bold$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:7$t$, v_arq, 3, 7, $t$lá em outubro de 2024. Nunca mudamos de regime." $t$, 72.0, 188.4, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:8$t$, v_arq, 3, 8, $t$3. RADAR/Siscomex — "A habilitação está ativa, sim, tanto da matriz quanto da filial de $t$, 72.0, 213.4, 12.0, $t$Aptos-Bold$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:9$t$, v_arq, 3, 9, $t$Itajaí. Os comprovantes estão com o despachante lá em Itajaí; se precisarem, a gente $t$, 72.0, 230.4, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:10$t$, v_arq, 3, 10, $t$pede para ele mandar." $t$, 72.0, 247.4, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:11$t$, v_arq, 3, 11, $t$4. Admissões — "Ponto? A gente não tem sistema nenhum comprado para isso. O $t$, 72.0, 272.5, 12.0, $t$Aptos-Bold$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:12$t$, v_arq, 3, 12, $t$pessoal ia marcar no papel, num caderno mesmo, ou anotar no celular — o que vocês $t$, 72.0, 289.4, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:13$t$, v_arq, 3, 13, $t$recomendarem está bom. Sobre a comissão, combinamos com o vendedor 1,5% em $t$, 72.0, 306.5, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:14$t$, v_arq, 3, 14, $t$cima das vendas líquidas do mês, e ponto. Não sei nada desse DSR, achava que o valor $t$, 72.0, 323.5, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:15$t$, v_arq, 3, 15, $t$combinado já era tudo. Isso é coisa para vocês resolverem." $t$, 72.0, 340.6, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:16$t$, v_arq, 3, 16, $t$5. Divergência da Cláusula Terceira — "Nenhuma retificação, não. A gente nem tinha $t$, 72.0, 365.6, 12.0, $t$Aptos-Bold$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:17$t$, v_arq, 3, 17, $t$percebido que o documento mostra duas datas diferentes. O prazo real que a gente se $t$, 72.0, 382.7, 12.0, $t$Aptos$t$, '0x000000'),
    ($t$lin:D2/Solicitacao_JRNA.pdf:3:18$t$, v_arq, 3, 18, $t$comprometeu é 31/07/2026; não fizemos alteração posterior nenhuma corrigindo isso." $t$, 72.0, 399.7, 12.0, $t$Aptos$t$, '0x000000');
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 74 THEN RAISE EXCEPTION 'linhas: %', n; END IF;
  -- As 5 respostas literais do diligência (Q1 a Q5) precisam estar na p. 3 do arquivo
  SELECT count(*) INTO n FROM erp.diligencia_item d WHERE d.empresa_id = 1 AND d.codigo IN ('Q1','Q2','Q3','Q4','Q5')
     AND strpos(regexp_replace((SELECT string_agg(texto, ' ' ORDER BY n_linha) FROM acervo.bru_linha WHERE arquivo_id = v_arq AND pagina = 3), '\s+', ' ', 'g'),
                regexp_replace(trim(both '"' from left(d.resposta_literal, 60)), '\s+', ' ', 'g')) > 0;
  IF n <> 5 THEN RAISE EXCEPTION 'Respostas Q1–Q5 do banco não conferem com a p. 3 (% de 5)', n; END IF;
END
$blk$;
