"""Importador em quarentena do Dossie 2 (Rota Sul Importadora — Competencia 09/2026).

Regras de governanca:
- Nunca mistura emp:rota_sul_d4 (Joinville/D4) com emp:rota_sul_d2 (Goiania/Itajai, id=1).
- Re-execucoes sao idempotentes (ON CONFLICT DO NOTHING) e nunca sobrescrevem registros
  editados pela contadora (origem_registro = 'usuario' ou status_validacao = 'homologado_contadora').
- Importa secoes narrativas de G:\\Meu Drive\\Nath\\Trabalho 01\\_entrega_limpa\\editaveis\\
  quando acessivel localmente; em ambientes sem G:\\ (ex.: Vercel), opera normalmente com o banco.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from psycopg2.extras import execute_values

from sistema.pg.db import conectar_pg

EMPRESA_CHAVE_D2 = "emp:rota_sul_d2"
ESCRITORIO_CHAVE_D1 = "emp:prisma_jrna_g07"
RELACAO_CHAVE_D2 = "rel:g07:rota_sul_d2"
DEFAULT_D2_EDITAVEIS = Path(r"G:\Meu Drive\Nath\Trabalho 01\_entrega_limpa\editaveis")


def _slug(txt: str) -> str:
    s = txt.lower().strip()
    for k, v in {
        "á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e",
        "í": "i", "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "item"


def _limpar_md_d2(md: str) -> str:
    md = md.replace("\\$", "$")
    md = re.sub(r"```mermaid.*?```\s*", "", md, flags=re.S)
    md = re.sub(r"\[`?([^\]`]+?)`?\]\((?:\.\./)?[^)]+\.(?:md|xlsx|pdf)\)", r"\1", md)
    md = re.sub(r"\n-{3,}\s*$", "", md.strip())
    return md.strip()


def _dividir_secoes_md(texto: str) -> list[dict[str, Any]]:
    """Divide Markdown por H2 ('## '), ou devolve corpo integral se nao houver H2."""
    partes = re.split(r"^## +(.+)$", texto.strip(), flags=re.M)
    out: list[dict[str, Any]] = []
    if len(partes) <= 1:
        # Documento sem secoes H2 (ex.: fichas individuais podem usar '## I — ...', caso contrario inteiro)
        return [{"ordem": 1, "codigo_secao": "corpo", "titulo": "Conteudo integral", "conteudo_md": _limpar_md_d2(texto)}]
    cabecalho = partes[0].strip()
    ordem = 1
    if cabecalho:
        # Remove H1 repetido se for apenas titulo principal + metadados
        out.append({
            "ordem": ordem,
            "codigo_secao": "cabecalho",
            "titulo": "Identificacao e cabecalho do documento",
            "conteudo_md": _limpar_md_d2(cabecalho),
        })
        ordem += 1
    vistos: dict[str, int] = {}
    for i in range(1, len(partes), 2):
        tit = partes[i].strip()
        corpo = _limpar_md_d2(partes[i + 1])
        base_cod = _slug(tit)[:32]
        idx = vistos.get(base_cod, 0) + 1
        vistos[base_cod] = idx
        cod = base_cod if idx == 1 else f"{base_cod}_{idx}"
        out.append({"ordem": ordem, "codigo_secao": cod, "titulo": tit, "conteudo_md": corpo})
        ordem += 1
    return out


DOCUMENTOS_D2_ARQUIVOS: tuple[tuple[str, str], ...] = (
    ("d2_00_indice", "00_Indice_Geral_Dossie2_Rota_Sul.md"),
    ("d2_01_diagnostico", "01_Diagnostico_Societario_e_Analise_Contrato_Social_Rota_Sul.md"),
    ("d2_02_proposta", "02_Proposta_Honorarios_Contabeis_e_BPO.md"),
    ("d2_03_contrato", "03_Contrato_Prestacao_Servicos_Contabeis_e_Procuracao.md"),
    ("d2_04_termo_rt", "04_Termo_Responsabilidade_Tecnica_Contabil.md"),
    ("d2_05_onboarding", "05_Comunicacao_Onboarding_Checklist_e_Respostas_Cliente.md"),
    ("d2_06_prontuario", "06_Prontuario_Indice_Roteiro_eSocial_e_Termos_VT_VR.md"),
    ("d2_07_ficha_e1", "07_Ficha_Registro_Empregado_1_Auxiliar_Administrativo.md"),
    ("d2_08_exp_e1", "08_Contrato_Experiencia_Empregado_1_Auxiliar_Administrativo.md"),
    ("d2_09_ficha_e2", "09_Ficha_Registro_Empregado_2_Vendedor.md"),
    ("d2_10_exp_e2", "10_Contrato_Experiencia_Empregado_2_Vendedor.md"),
    ("d2_11_folha", "11_Folha_Pagamento_Set2026_Memoria_Calculo.md"),
    ("d2_12_resumo_contab", "12_Resumo_Folha_Provisoes_Contabilizacao_e_Recibos.md"),
    ("d2_13_auditoria", "13_Relatorio_Tecnico_Auditoria_Trabalhista.md"),
    ("d2_14_premissas", "14_Registro_Premissas_Adotadas_e_Fontes_Oficiais.md"),
    ("d2_15_ia", "15_Declaracao_Uso_Inteligencia_Artificial_e_LGPD.md"),
)

# 47 criterios oficiais da Devolutiva D2 (P1..P9) — REVISAO_ENTREGA_LIMPA_2026-11-24.md
CRITERIOS_D2: tuple[tuple[str, str, str, int, str, int, str, str], ...] = (
    # (matriz, bloco, codigo, nota_v1, critica_v1, bloco_peso, descricao, referencia_localizacao)
    ("d2_p1", "P1", "C-01", 2, "CNAEs genericos na v1 e divergencia Matriz x Filial SC nao apontada.", 100, "Objeto, CNAE, denominacao e filial (18x17 CNAEs, 4530-7/02 e 05, risco 4541-2/01, Distribuidora x Distribuicao, Sala 223 x 223 A 32).", "Doc. 01 §1, §3.1, §3.2"),
    ("d2_p1", "P1", "C-02", 1, "Nao identificou quorum 50/50 nem os 3 criterios conflitantes de haveres na v1.", 100, "Governanca, administracao, quorum 50/50, tres criterios conflitantes de haveres (Cl. 5a/12a/14a), AGO/tesouraria, JCP, Cl. 15a e 18a.", "Doc. 01 §3.4"),
    ("d2_p1", "P1", "C-03", 1, "Ausencia de classificacao Formal x Material e plano de saneamento na v1.", 100, "Matriz de riscos (Formal x Material) e plano de saneamento R-01 a R-09 para a 3a Alteracao Contratual com fundamento legal.", "Doc. 01 §4 e §5"),
    ("d2_p1", "P1", "C-04", 2, "NIREs, enderecos completos e historico da filial Itajai incompletos na v1.", 100, "Identificacao completa do cliente (Matriz Goiania-GO e Filial Itajai-SC, CNPJ, NIRE, enderecos, socios e capital).", "Doc. 01 §1"),
    ("d2_p1", "P1", "C-05", 2, "Analise critica do Anexo I dispersa e sem citacao exata de clausula na v1.", 100, "Clareza e organizacao do registro por clausula exata do Anexo I (Cl. 1a a 19a).", "Doc. 01 Sumario e §3"),
    ("d2_p1", "P1", "C-06", 1, "Nao apontou conflito 31/07/2026 x 31/07/2025 nem mora de R$ 500 mil (CC arts. 1.004/1.058).", 100, "Capital social (R$ 1.500.000,00), conflito de prazos (31/07/2026 x 31/07/2025) e mora na integralizacao de R$ 500.000,00.", "Doc. 01 §3.3"),

    ("d2_p2", "P2", "C-07", 2, "Campos [INSERIR ...] em aberto e citacao a revogada Res. CFC 1.555/2018.", 100, "Contrato de prestacao de servicos contabeis com partes qualificadas, objeto, prazo, rescisao, foro e assinatura conjunta > R$ 15 mil.", "Doc. 03"),
    ("d2_p2", "P2", "C-08", 2, "Proposta sem memoria de horas nem justificativa frente ao ticket medio do Dossie 1.", 100, "Proposta de honorarios com memoria de custo (R$ 125/h: 16h setup, 96h recuperacao, 20h Matriz, 12h Filial, 13o honorario).", "Doc. 02 §3"),
    ("d2_p2", "P2", "C-09", 2, "Faltavam Carta de Responsabilidade, delimitacao mar-ago/2026 e minuta de procuracao.", 100, "Responsabilidades, blindagem contabil (mar-ago/2026), LGPD e Anexo I (minuta de procuracao com poderes e vedacoes).", "Doc. 03 Cl. 4a, 5a, 7a e Anexo I"),
    ("d2_p2", "P2", "C-10", 2, "Termo RT sem rol de pendencias de onboarding nem numero CRC preenchido.", 100, "Termo de Responsabilidade Tecnica atualizado pela Res. CFC 1.708/2023 com rol de 7 pendencias e assinatura da RT.", "Doc. 04 §5"),
    ("d2_p2", "P2", "C-11", 2, "Divergencia de 13o honorario entre Proposta e Contrato na v1.", 100, "Coerencia integral entre Proposta, Contrato e Termo RT (valores, vigencia 01/09/2026, 13o honorario R$ 4.000 e dados D1).", "Docs. 02-04"),

    ("d2_p3", "P3", "C-12", 1, "Nao incorporava as 5 respostas literais da Solicitacao_JRNA.pdf na v1.", 100, "Respostas registradas com origem comprovada (5 respostas literais do cliente em Solicitacao_JRNA e lacunas verbais sem inventar evidencia).", "Doc. 05 §2.1 e §2.2"),
    ("d2_p3", "P3", "C-13", 1, "Faltava quadro estruturado de pendencias com risco, responsavel e prazo.", 100, "Quadro de tratamento das pendencias em aberto (PEND-01 a PEND-08 com risco, responsavel, prazo e providencia).", "Doc. 05 §3"),
    ("d2_p3", "P3", "C-14", 2, "Lista de documentos nao segregada por ator responsavel e status real.", 100, "Checklist de documentos DOC-01 a DOC-13 organizado por ator responsavel, tema, finalidade, prazo e status.", "Doc. 05 §1"),
    ("d2_p3", "P3", "C-15", 2, "Perguntas ao cliente sem cobrir ASO, SST, ponto, DSR e CCT de forma sistematica.", 100, "Perguntas formuladas ao cliente na carta de onboarding e desdobramento tecnico (Q1 a Q9 + OP-03).", "Doc. 05 §2"),

    ("d2_p4", "P4", "C-16", 2, "Prontuarios de E1 e E2 sem sub-indice consolidado nem controle de pecas faltantes.", 100, "Prontuario completo com sub-indices individuais para E1 e E2 e status real de cada peca.", "Doc. 06 §1"),
    ("d2_p4", "P4", "C-17", 1, "Relatorio v1 citava piso R$ 1.580 sem fonte e CNAE 4530-7/01 inexistente no Anexo I.", 100, "Confronto de CBO (4110-05 / 5211-10), pisos CCT (R$ 1.722,25 / R$ 1.863,00) e CNAEs do Anexo I com registro MTE.", "Docs. 06-10 §3"),
    ("d2_p4", "P4", "C-18", 2, "Faltavam termos formalizados de VT/VR e declaracao de dependentes (salario-familia).", 100, "Declaracoes de dependentes (IRRF/SF) e termos de opcao de Vale-Transporte e Vale-Refeicao (OP-01: sensibilidade 4x2).", "Doc. 06 §4 e §5"),
    ("d2_p4", "P4", "C-19", 2, "Roteiro do eSocial incompleto e sem diferenciar documento fisico de evento transmitido.", 100, "Roteiro completo eSocial (S-1000 a S-1299) e CTPS Digital sem inventar numeros de recibo ou protocolos.", "Doc. 06 §2"),
    ("d2_p4", "P4", "C-20", 3, "Fichas v1 com CNAE errado e salario-familia indevido para E1.", 100, "Fichas de registro de E1 (16/09/2026) e E2 (21/09/2026) fiéis ao caso, sem atestar eventos ou exames inexistentes.", "Docs. 07 e 09"),
    ("d2_p4", "P4", "C-21", 1, "v1 alterou intervalo para 1h12, inventou sabados e deixou 6 marcadores [cite: 19, 25].", 100, "Contratos de experiencia (45+45d e 30+60d), termos de prorrogacao, intervalo literal 1h48 (41h x 44h), zero residuos e estorno Lei 3.207/57.", "Docs. 08 e 10"),
    ("d2_p4", "P4", "C-22", 3, "Manter ASO e documentos civis ausentes como pendencia real sem inventar aprovacao.", 100, "ASO admissional (NR-7) e documentos pendentes classificados honestamente como PENDENTE CRITICO / PEND-01.", "Docs. 06, 07, 09"),

    ("d2_p5", "P5", "C-23", 1, "Folha v1 omitiu integralmente comissao (R$ 900) e DSR (R$ 100) do Empregado 2.", 100, "Comissao 1,5% (R$ 900,00) sobre R$ 60.000,00 e DSR destacado (R$ 100,00 = 900/9*1) para o Empregado 2.", "Doc. 11"),
    ("d2_p5", "P5", "C-24", 1, "Folha v1 entregue apenas em PDF estatico sem formulas abertas.", 100, "Memoria de calculo aberta em planilha (.xlsx com 4 abas e formulas dinamicas ligadas a Parametros).", "Planilha Doc. 11"),
    ("d2_p5", "P5", "C-25", 1, "Folha v1 concedeu salario-familia indevido de R$ 62,04 ao E1 (salario R$ 2.400 > teto R$ 1.980,38).", 100, "Salario-familia zerado por formula (Portaria MPS/MF 13/2026: teto R$ 1.980,38, cota R$ 67,54) e confronto com piso CCT.", "Doc. 11"),
    ("d2_p5", "P5", "C-26", 2, "Omissao de VR (R$ 330) e Contribuicao Negocial (R$ 94,35) na folha v1.", 100, "VT (6%: R$ 72 e R$ 38; 4/dia + sensibilidade 2/dia), VR (E1 R$ 330) e Contribuicao Negocial (3,33%: R$ 39,96 e R$ 54,39; Cenarios A e B).", "Doc. 11"),
    ("d2_p5", "P5", "C-27", 2, "INSS do E2 calculado sobre base sem comissao/DSR (R$ 47,50 vs R$ 122,68).", 100, "INSS progressivo 4 faixas (Portaria MPS/MF 13/2026): E1 = R$ 90,00; E2 = R$ 122,68 (Total R$ 212,68).", "Doc. 11"),
    ("d2_p5", "P5", "C-28", 3, "Demonstrar formula dinamica de IRRF 2026 e recolhimento FGTS 8% sobre base corrigida.", 100, "IRRF 2026 (Lei 15.270/2025 + simplificado R$ 607,20 = R$ 0,00) e FGTS 8% (R$ 96,00 e R$ 130,67 = R$ 226,67).", "Doc. 11"),

    ("d2_p6", "P6", "C-29", 0, "Ausencia total de provisoes de 13o, ferias, 1/3 e FGTS sobre provisoes na v1.", 100, "Provisoes trabalhistas (E1 15d -> 1/12 avo: 13o R$ 200, Ferias R$ 200, 1/3 R$ 66,67, FGTS R$ 37,33 = R$ 504,00; E2 10d = R$ 0,00).", "Doc. 12 §2"),
    ("d2_p6", "P6", "C-30", 1, "Faltava contabilizacao por partidas dobradas segregando Adm. x Comercial.", 100, "Lancamentos contabeis de integracao em partidas dobradas (L1-L4: D = C = R$ 4.238,00), segregando Adm. (4.1.1.*) e Comercial (4.2.1.*).", "Doc. 12 §3"),
    ("d2_p6", "P6", "C-31", 1, "Sem conciliacao numerica entre planilha, resumo e partidas dobradas.", 100, "Conciliacao fechada com diferenca zero (R$ 0,00) em todas as rubricas entre folha, resumo e contabilizacao.", "Doc. 12 §4"),
    ("d2_p6", "P6", "C-32", 2, "Explicitar reflexo do Simples Nacional (CPP no DAS) e sensibilidade de exclusao.", 100, "Tratamento de encargos no Simples Nacional (CPP no DAS) e analise de sensibilidade de exclusao (+R$ 917,40/mes).", "Doc. 12 §1 e §5"),
    ("d2_p6", "P6", "C-33", 2, "Recibos da v1 nao refletiam comissao, DSR, VR nem contribuicao negocial.", 100, "Resumo consolidado da folha e recibos de pagamento (E1 R$ 998,04 e E2 R$ 1.418,26; Total R$ 2.416,30; Cenario B R$ 2.510,65).", "Doc. 12 §1 e §6"),

    ("d2_p7", "P7", "C-34", 1, "Relatorio de auditoria v1 nao executava recalculo independente da folha.", 100, "Recalculo independente de 100% da folha em confronto triplo (v1 x Auditoria x Planilha Final, diferenca R$ 0,00).", "Doc. 13 PT-03"),
    ("d2_p7", "P7", "C-35", 1, "Faltavam planejamento formal sob NBC TA 315/330, materialidade e matriz de risco.", 100, "Planejamento de auditoria trabalhista (PT-01): objetivos, populacao 100%, materialidade R$ 0,01 e riscos inerente/controle.", "Doc. 13 PT-01"),
    ("d2_p7", "P7", "C-36", 1, "Sem cruzamento com guias DCTFWeb (R$ 212,68) e FGTS Digital (R$ 226,67).", 100, "Conferencia de encargos, DCTFWeb (R$ 212,68), FGTS Digital (R$ 226,67) e roteiro eSocial.", "Doc. 13 PT-04"),
    ("d2_p7", "P7", "C-37", 2, "Testes documentais v1 omitiam PGR/PCMSO/LTCAT e controle de ponto.", 100, "Auditoria cadastral e documental (PT-02): ASO, SST, ponto, VT/VR e termos sem atestar documento inexistente.", "Doc. 13 PT-02"),
    ("d2_p7", "P7", "C-38", 1, "Achados v1 sem codificacao, evidencia documental e impacto monetario.", 100, "Quadro consolidado de achados AUD-01 a AUD-10 com evidencia documental, risco e impacto financeiro.", "Doc. 13 PT-05"),
    ("d2_p7", "P7", "C-39", 1, "Sem plano de acao indicando correcao proposta, responsavel e prazo.", 100, "Correcoes propostas por achado com responsavel, prazo e status (saneado na revisao x aberto para cliente).", "Doc. 13 PT-05"),

    ("d2_p8", "P8", "C-40", 0, "Produto P8 (Registro de Premissas e Fontes) nao foi entregue na v1.", 100, "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Aditivo 2026/2027) e tabelas oficiais (Portaria 13/2026, Lei 15.270/2025).", "Doc. 14 PR-03 a PR-06"),
    ("d2_p8", "P8", "C-41", 0, "Sem quadro de governanca de decisoes pendentes nem impacto se alteradas.", 100, "Quadro de decisoes e pendencias sobre premissas (Quem Decide x Prazo Limite x Impacto se Alterada).", "Doc. 14 §3"),
    ("d2_p8", "P8", "C-42", 1, "Premissas soltas sem numeracao nem justificativa tecnica.", 100, "Registro numerado PR-01 a PR-18 com decisao adotada, motivo/justificativa e documentos impactados.", "Doc. 14 §2"),
    ("d2_p8", "P8", "C-43", 0, "Faltavam norma exata, link oficial e data de consulta em cada premissa.", 100, "Fonte oficial completa (norma, artigo/clausula, URL e data de consulta) para cada premissa.", "Doc. 14 §2"),

    ("d2_p9", "P9", "C-44", 0, "Produto P9 (Declaracao de Uso de IA) nao foi entregue no Dossie 2 v1.", 100, "Declaracao especifica do Dossie 2 detalhando finalidade do uso de IA por documento/etapa.", "Doc. 15 §1"),
    ("d2_p9", "P9", "C-45", 0, "Sem registro das ferramentas utilizadas nem resumo dos prompts.", 100, "Ferramentas utilizadas (Gemini v1, Antigravity v2, Claude revisao) e comandos resumidos sem dados pessoais reais.", "Doc. 15 §2"),
    ("d2_p9", "P9", "C-46", 0, "Faltava demonstracao de verificacao independente das respostas de IA em fontes oficiais.", 100, "Verificacao independente das respostas e calculos pela dupla frente a fontes oficiais.", "Doc. 15 §3"),
    ("d2_p9", "P9", "C-47", 0, "Ausencia de relato de correcoes humanas e declaracao de conformidade LGPD.", 100, "Correcoes humanas efetuadas (incluindo expurgo de arquivo de outra dupla) e conformidade com a LGPD (Lei 13.709/2018).", "Doc. 15 §4"),
)

PREMISSAS_D2: tuple[tuple[int, str, str, str, str, str, str, date], ...] = (
    # (num, enunciado, resposta_autoral, norma_citada, link_oficial, decisao_impactada, apontamento, data_acesso)
    (1, "PR-01 — Enquadramento Tributario (Simples Nacional)", "Tratar a Rota Sul como optante pelo Simples Nacional (Classificacao 01 no eSocial, Anexo I Comercio, CPP no DAS), conforme confirmacao dos socios em Solicitacao_JRNA.pdf p. 3.", "LC nº 123/2006, art. 13, VI e art. 18, § 4º, I", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm", "Docs. 01, 06-10, 11, 12, 13 (CPP = R$ 0,00 na folha)", "Validar certidao Simples e monitorar debito mar-ago/2026.", date(2026, 11, 23)),
    (2, "PR-02 — Vedacao do Simples na Importacao de Motocicletas", "Classificar como risco material critico o CNAE 4541-2/01 (atacado de motos) sob clausula de Importacao e Exportacao, exigindo exclusao de 4541-2/01, 4541-2/03 e 4511-1/02 na 3a Alteracao Contratual.", "LC nº 123/2006, art. 17, VIII e arts. 29-30", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm", "Doc. 01 (§3.2 e R-01) + Sensibilidade +22,22% na folha", "Conferir texto literal do art. 17, VIII e pautar 3a Alteracao.", date(2026, 11, 23)),
    (3, "PR-03 — Convencao Coletiva de Trabalho (CCT) de Referencia", "Adotar CCT SECEG x SINDILOJAS-GO 2025/2027 (Registro MTE SRT00189/2025) + Termo Aditivo 2026/2027 (Cl. 3a, 6a e 11a): Piso Geral R$ 1.722,25; Garantia Vendedor R$ 1.863,00; Teto VT misto R$ 2.257,50; Negocial 3,33% teto R$ 148,00.", "CCT SRT00189/2025 + Aditivo 2026/2027, Cl. 3ª, 6ª e 11ª", "https://www3.mte.gov.br/sistemas/mediador/", "Docs. 06-10, 11, 13, 14 (substitui R$ 1.580 sem fonte da v1)", "OP-02: confirmar registro direto no Mediador MTE.", date(2026, 11, 23)),
    (4, "PR-04 — Tabela Progressiva de INSS (4 Faixas — 2026)", "Aplicar tabela oficial 2026 (Portaria MPS/MF 13/2026): F1 ate R$ 1.621,00 (7,5%); F2 ate R$ 2.902,84 (9%); F3 ate R$ 4.354,27 (12%); F4 ate R$ 8.475,55 (14%).", "Portaria Interministerial MPS/MF nº 13/2026 (DOU 12/01/2026)", "https://www.gov.br/inss/pt-br/direitos-e-deveres/inscricao-e-contribuicao/tabela-de-contribuicao-mensal", "INSS retido: E1 = R$ 90,00; E2 = R$ 122,68 (DCTFWeb R$ 212,68)", "Conferir calculo progressivo por faixa no motor.", date(2026, 11, 23)),
    (5, "PR-05 — Tabela de IRRF 2026, Desconto Simplificado e Reducao Legal", "Aplicar tabela progressiva RFB (isento ate R$ 2.428,80; dependente R$ 189,59; simplificado R$ 607,20) com Reducao Lei 15.270/2025 (isencao efetiva ate R$ 5.000,00; transicao ate R$ 7.350,00).", "Lei nº 15.270/2025 e Lei nº 14.848/2024", "https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas", "Bases otima E1 (R$ 592,80) e E2 (R$ 1.026,13) -> IRRF = R$ 0,00", "Manter formula dinamica ativa para futuras faixas acima de R$ 5k.", date(2026, 11, 23)),
    (6, "PR-06 — Salario-Familia (Elegibilidade e Cota 2026)", "Nao conceder Salario-Familia ao Empregado 1 (R$ 0,00): salario contratual de R$ 2.400,00 supera o teto legal de R$ 1.980,38, mantendo parametrizada a cota de R$ 67,54.", "Decreto nº 3.048/1999, art. 82 e Portaria MPS/MF nº 13/2026", "https://www.gov.br/inss/pt-br/assuntos/salario-familia", "Corrige pagamento indevido de R$ 62,04 da v1 (AUD-03)", "Conferir dependencia E1 apenas para eventual deducao IRRF.", date(2026, 11, 23)),
    (7, "PR-07 — Base de Vendas Liquidas e DSR do Empregado 2", "Adotar premissa didatica de R$ 60.000,00 em vendas liquidas (21/09 a 30/09/2026), gerando comissao 1,5% = R$ 900,00 e DSR = R$ 100,00 (900 / 9 dias uteis x 1 domingo em 27/09).", "CLT arts. 457 e 466; Lei 3.207/1957 art. 7º; Lei 605/1949; Sum. 27 TST", "https://www.planalto.gov.br/ccivil_03/leis/l0605.htm", "Bruto E2 passa para R$ 1.633,33 (PEND-05 confirmar DOC-13)", "Aguardar relatorio comercial assinado de vendas e estornos.", date(2026, 11, 23)),
    (8, "PR-08 — Vale-Transporte (RMTC Goiania, 4/dia x Sensibilidade 2/dia)", "Tarifa R$ 4,30; adotado 4 passagens/dia (2 ida + 2 volta = R$ 17,20/dia) com subsidio de R$ 234,00 e desconto 6% sobre basico proporcional (E1 R$ 72,00; E2 R$ 38,00; teto CCT R$ 2.257,50). Sensibilidade 2/dia: subsidio R$ 62,00.", "Lei nº 7.418/1985, art. 4º e Aditivo CCT 2026/2027, Cl. 6ª", "https://www.planalto.gov.br/ccivil_03/leis/l7418.htm", "Subsidio VT R$ 234,00 ou R$ 62,00 (liquido empregados inalterado)", "OP-01: confirmar no Termo VT (DOC-12) se 2 ou 4 conducoes/dia.", date(2026, 11, 23)),
    (9, "PR-09 — Vale-Refeicao (Empregado 1 — PAT)", "Conceder R$ 30,00/dia util ao E1 (11 dias uteis = R$ 330,00) 100% custeado pela empresa sob natureza indenizatoria (PAT / CLT art. 457 § 2º). E2 sem VR na competencia 09/2026.", "CLT, art. 457, § 2º e Lei nº 6.321/1976 (PAT)", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm", "Inclui R$ 330,00 de beneficio no E1 e corrige base errada do acervo para E2", "Formalizar inscricao/instrumento PAT junto a diretoria.", date(2026, 11, 23)),
    (10, "PR-10 — Contribuicao Negocial (CCT SECEG — Cenarios A e B)", "Aplicar 3,33% com teto R$ 148,00 (Cenario A sem oposicao: E1 R$ 39,96; E2 R$ 54,39; Total R$ 94,35) e demonstrar Cenario B (R$ 0,00). VEDACAO: empresa nao deve induzir nem fornecer modelo de oposicao.", "CCT SECEG x SINDILOJAS-GO Cl. 11ª e STF Tema 935 (ARE 1.018.459)", "https://portal.stf.jus.br/", "Liquido A = R$ 2.416,30 vs Liquido B = R$ 2.510,65", "Aguardar eventual protocolo espontaneo de oposicao.", date(2026, 11, 23)),
    (11, "PR-11 — Jornada e Intervalo do Empregado 1 (1h48 — 41h x 44h)", "Adotar literalmente o texto do Caso (08h-18h com 1h48 de intervalo = 41h semanais), registrando a divergencia de 3h/sem frente as 44h como PEND-04 sem inventar 1h12 nem sabados.", "CLT, art. 59, § 6º e art. 71", "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm", "Corrige invencao da v1 nos docs. 07, 08 e 13", "Alinhar escala das 3h faltantes com a diretoria e E1.", date(2026, 11, 23)),
    (12, "PR-12 — Provisoes Trabalhistas (13o, Ferias, 1/3 e FGTS)", "Provisionar 1/12 avo somente para E1 (15 dias em 09/2026): 13o R$ 200,00 + Ferias R$ 200,00 + 1/3 R$ 66,67 + FGTS 8% R$ 37,33 = R$ 504,00. E2 (10 dias < 15d) = R$ 0,00.", "Lei 4.090/1962 art. 1º § 2º; CLT art. 146; NBC TG 33 (R2)", "https://cfc.org.br/", "Custo total da folha sobe para R$ 4.128,00 e partidas L4 somam R$ 504,00", "A partir de 10/2026 incluir media de comissoes+DSR para E2.", date(2026, 11, 23)),
    (13, "PR-13 — FGTS Digital, eSocial S-1.3 e SST (S-2220 / S-2240)", "FGTS 8% via PIX no FGTS Digital; roteiro completo S-1000 a S-1299 sem inventar recibos; exigir ASO (NR-7) e laudos SST (PGR/DIR, PCMSO, LTCAT) antes de transmitir S-2220/S-2240.", "MOS eSocial S-1.3; Lei 8.036/1990; NR-1, NR-4 e NR-7", "https://www.gov.br/esocial/pt-br/documentacao-tecnica", "Bloqueia S-2220 e S-2240 como pendentes reais (AUD-01/AUD-09)", "Nao transmitir ou atestar eventos sem ASO e e-CNPJ.", date(2026, 11, 23)),
    (14, "PR-14 — Res. CFC 1.708/2023 e Dados Ficticios Padronizados da PRISMA JRNA", "Fundamentar Contrato e Termo RT na Res. CFC 1.708/2023 (revogou 1.555/2018), com Carta de Responsabilidade ITG 1000, dados padronizados da PRISMA JRNA (CNPJ 48.123.456/0001-90, CRC-DF 004.821/O-2, Nathalia CRC-DF 025.431/O-7) e assinatura conjunta > R$ 15 mil.", "Resolução CFC nº 1.708/2023; ITG 1000; NBC PG 01", "https://www2.cfc.org.br/sisweb/sre/Default.aspx", "Docs. 02, 03 e 04 100% coerentes com o Dossie 1", "Confirmar dados didaticos da contratada na leitura final.", date(2026, 11, 23)),
    (15, "PR-15 — Pro-Labore dos Socios e Bloqueio de Distribuicao de Lucros", "Nao incluir pro-labore ficticio em 09/2026 (PEND-08); registrar vedacao expressa a distribuicao de lucros enquanto houver debitos fiscais em aberto de mar-ago/2026 (multa de 50%).", "Lei nº 4.357/1964, art. 32; Lei 8.212/1991; SC COSIT nº 120/2016", "https://www.planalto.gov.br/ccivil_03/leis/l4357.htm", "Blinda escritorio contra responsabilidade por omissao anterior", "Formalizar definicao de pro-labore para competencia 10/2026.", date(2026, 11, 23)),
    (16, "PR-16 — Segregacao Funcional de Despesas na DRE (Adm. x Comercial)", "Segregar despesas na DRE conforme NBC TG 26 item 99: E1 em Despesas Administrativas 4.1.1.* (R$ 2.247,20) e E2 em Despesas Comerciais 4.2.1.* (R$ 1.880,80).", "NBC TG 26 (R5), item 99", "https://cfc.org.br/", "Lotes contabeis L1-L4 segregados (Partidas dobradas R$ 4.238,00)", "Consolidar plano de contas reduzido definitivo no Dossie 4.", date(2026, 11, 23)),
    (17, "PR-17 — Sensibilidade de Exclusao do Simples Nacional (+27,8%)", "Modelar impacto trabalhista da eventual exclusao do Simples Nacional (CPP 20% + RAT 2% + Terceiros 5,8% = 27,8% sobre folha + provisoes): +R$ 917,40/mes (+22,22%, custo total R$ 5.045,40).", "Lei nº 8.212/1991, art. 22, I; Decreto 3.048/1999 Anexo V; IN RFB 2.110/2022", "https://www.planalto.gov.br/ccivil_03/leis/l8212cons.htm", "Quantifica urgencia de excluir CNAE 4541-2/01 na 3a Alteracao", "Apresentar comparativo aos socios na entrega.", date(2026, 11, 23)),
    (18, "PR-18 — Dados Pessoais Ficticios dos Empregados e Dependente (LGPD)", "Adotar nomes, RGs, enderecos e CPFs de teste para E1 (Mariana Alves Costa), dependente (Lucas Alves Costa) e E2 (Rafael Souza Lima), preservando 100% dos parametros trabalhistas do caso e sem inventar advogado, despachante ou clinica.", "LGPD — Lei nº 13.709/2018, art. 6º", "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm", "Docs. 05-13 com transparencia didatica total", "Manter nota explicativa de dados ficticios didaticos.", date(2026, 11, 24)),
)


def _obter_emp_id_d2(cur: Any) -> int:
    cur.execute("SELECT id FROM erp.empresa WHERE chave = %s", (EMPRESA_CHAVE_D2,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Empresa {EMPRESA_CHAVE_D2} nao encontrada no PostgreSQL.")
    return int(row["id"])


def semear_etapa0(conn: Any) -> dict[str, int]:
    """Semear ajustes de base D2, requisitos P1..P9, enquadramento, 2a alteracao, R-01..R-09, C-01..C-47, PR-01..PR-18 e diario IA."""
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        emp_id = _obter_emp_id_d2(cur)
        cur.execute("SELECT id FROM erp.pessoa WHERE chave = 'pes:pf:nathalia_peres_araujo'")
        rt_row = cur.fetchone()
        rt_id = int(rt_row["id"]) if rt_row else None

        # 1. Atualizar erp.dossie para D2
        cur.execute(
            """
            UPDATE erp.dossie
            SET empresa_id = %s,
                competencia = '2026-09',
                peso_micro = COALESCE(peso_micro, 250000),
                titulo = 'Dossiê 2 — Onboarding, Departamento Pessoal e Auditoria (Rota Sul Importadora)'
            WHERE codigo = 'D2'
            """,
            (emp_id,),
        )
        cur.execute("SELECT id FROM erp.dossie WHERE codigo = 'D2'")
        dossie_d2_id = int(cur.fetchone()["id"])

        # 2. Corrigir as 2 inconsistencias apontadas no acervo vigente da Rota Sul D2
        cur.execute(
            """
            UPDATE erp.evento
            SET data_evento = DATE '2025-07-22',
                descricao = '2ª Alteração Contratual e Consolidação (Anexo I): assinada em 22/07/2025, registrada na JUCEG em 24/07/2025 sob nº 20259999999 (capital R$ 1.000.000 -> R$ 1.500.000; filial Itajaí-SC).'
            WHERE chave = 'evt:d2:2a_alteracao_contratual' AND origem_registro <> 'usuario'
            """
        )
        cur.execute(
            """
            UPDATE erp.fato
            SET valor_texto = 'Empregado 2: salário R$ 1.900,00 mensais + comissão 1,5% + DSR; sem VR na competência 09/2026 (VR apenas E1 conforme PR-09)'
            WHERE chave = 'fato:d2:rs:emp2' AND origem_registro <> 'usuario'
            """
        )
        cur.execute(
            """
            UPDATE erp.estabelecimento
            SET endereco = 'Rua das Mangueiras, Quadra 40, Lote 11, nº 215, Setor Campinas, Goiânia-GO, CEP 74.515-000'
            WHERE chave = 'est:rota_sul_d2:matriz' AND origem_registro <> 'usuario' AND endereco = 'Sede conforme D2'
            """
        )
        cur.execute(
            """
            UPDATE erp.estabelecimento
            SET endereco = 'BR-101, nº 15.000, Sala 223 (Anexo I: Sala 223 A 32), Bairro Canhanduba, Itajaí-SC, CEP 88.313-000 (NIRE 42900000012)'
            WHERE chave = 'est:rota_sul_d2:filial_itajai' AND origem_registro <> 'usuario'
              AND endereco LIKE 'Filial Itajaí conforme D2%'
            """
        )

        # 3. Requisitos D2-P1..D2-P9
        reqs = [
            (1, "D2-P1", "Diagnóstico Societário, Cadastral e Análise Crítica da 2ª Alteração Contratual (Anexo I)", ["d2_00_indice", "d2_01_diagnostico"]),
            (2, "D2-P2", "Proposta de Honorários, Contrato de Prestação de Serviços, Procuração e Termo RT (Res. CFC 1.708/2023)", ["d2_02_proposta", "d2_03_contrato", "d2_04_termo_rt"]),
            (3, "D2-P3", "Comunicação de Onboarding, Checklist DOC-01..13, Respostas Literais Q1..Q9 e Pendências PEND-01..08", ["d2_05_onboarding"]),
            (4, "D2-P4", "Prontuários Completos E1 e E2, Roteiro eSocial/CTPS Digital, Termos VT/VR, Fichas e Contratos de Experiência", ["d2_06_prontuario", "d2_07_ficha_e1", "d2_08_exp_e1", "d2_09_ficha_e2", "d2_10_exp_e2"]),
            (5, "D2-P5", "Planilha Aberta e Memória de Cálculo da Folha de Pagamento (Competência 09/2026)", ["d2_11_folha"]),
            (6, "D2-P6", "Resumo Consolidado da Folha, Provisões Trabalhistas, Partidas Dobradas (Adm. x Comercial) e Recibos", ["d2_12_resumo_contab"]),
            (7, "D2-P7", "Relatório Técnico de Auditoria Trabalhista (Papéis de Trabalho PT-01..05 e Achados AUD-01..10)", ["d2_13_auditoria"]),
            (8, "D2-P8", "Registro Numerado de Premissas Adotadas e Fontes Oficiais (PR-01..PR-18)", ["d2_14_premissas"]),
            (9, "D2-P9", "Declaração de Uso de Inteligência Artificial, Verificação em Fontes Oficiais e LGPD", ["d2_15_ia"]),
        ]
        for ordem, cod, desc, docs in reqs:
            cur.execute(
                """
                INSERT INTO erp.requisito (chave, dossie_id, codigo, descricao, fonte_chave, ordem, documentos_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (chave) DO UPDATE
                SET ordem = EXCLUDED.ordem, documentos_json = EXCLUDED.documentos_json, descricao = EXCLUDED.descricao
                """,
                (f"req:{cod}", dossie_d2_id, cod, desc, "arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf", ordem, json.dumps(docs)),
            )
        counts["erp.requisito"] = len(reqs)

        # 4. Enquadramento historico da Rota Sul D2
        cur.execute(
            """
            INSERT INTO erp.enquadramento_historico (
                chave, empresa_id, porte, regime_tributario, cnae_principal, cnaes_secundarios,
                registro_crc, responsavel_tecnico_pessoa_id, vigente_de, fonte_chave,
                origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria
            ) VALUES (%s, %s, 'ME', 'Simples_Anexo_I', '4530-7/02', %s::jsonb, 'CRC-DF 004.821/O-2', %s,
                      DATE '2024-10-28', 'arq:D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf',
                      'importado_rascunho_v2', 'alerta_inconsistencia',
                      'Fichas e relatorio v1 citavam CNAE 4530-7/01 inexistente no Anexo I.',
                      'CRITICO Simples Nacional (LC 123 art. 17 VIII): Matriz tem 18 CNAEs e Filial 17 (omite 8211-3/00), mantendo 4541-2/01 (motos) sob clausula de Importacao.')
            ON CONFLICT (chave) DO NOTHING
            """,
            (
                "enq:rota_sul_d2:2026", emp_id,
                json.dumps(["4530-7/05", "4541-2/02", "4541-2/06", "4541-2/01", "4541-2/03", "4511-1/02", "8211-3/00"]),
                rt_id,
            ),
        )
        counts["erp.enquadramento_historico"] = 1

        # 5. Clausulas da 2a Alteracao Contratual (Anexo I — Estacao 2 em contexto D2)
        clausulas_2a = [
            (1, "D2-ANEXO1", "C-01", "Preâmbulo / Título Consolidação", "Divergência na denominação social: DISTRIBUIÇÃO x DISTRIBUIDORA",
             "O preâmbulo e a Cl. 1ª grafam 'DISTRIBUIDORA LTDA.', mas o título da Consolidação (Cl. 4ª, pág. 8) grafa 'DISTRIBUIÇÃO LTDA.' (risco formal — CC art. 1.158).",
             "alerta_inconsistencia", "Anexo I pág. 1 vs. pág. 8", "Uniformizar como 'DISTRIBUIDORA LTDA.' na 3ª Alteração Contratual."),
            (2, "D2-ANEXO1", "C-01", "Cl. 1ª e Par. Único Consolidação", "Endereço da Filial de Itajaí-SC (Sala 223 × Sala 223 A 32)",
             "Matriz transferida para Rua das Mangueiras nº 215, Goiânia-GO. Filial Itajaí-SC consta como 'Sala 223' na ficha do caso e 'Sala 223 A 32' no Anexo I (IN RFB 2.119/2022).",
             "alerta_inconsistencia", "Ficha do Caso vs. Anexo I pág. 8", "Confirmar matrícula/IPTU em SC e retificar complemento na 3ª Alteração."),
            (3, "D2-ANEXO1", "C-01", "Cl. 2ª Alteração e Cl. 3ª Consolidação", "Objeto social heterogêneo: 18 CNAEs Matriz × 17 Filial e risco 4541-2/01 no Simples",
             "Matriz lista 18 CNAEs e Filial omite 8211-3/00; inclui título 'IMPORTAÇÃO E EXPORTAÇÃO' cumulado com 4541-2/01 (motos), 4541-2/03 e 4511-1/02, expondo à vedação do art. 17, VIII da LC 123/2006 (+R$ 917,40/mês na folha se excluída).",
             "alerta_inconsistencia", "v1 usava CNAE 4530-7/01 inexistente no contrato", "CRÍTICO: excluir CNAEs de motos/automóveis e depurar CNAEs estranhos aos pneumáticos."),
            (4, "D2-ANEXO1", "C-06", "Cl. 3ª § 1º × Cl. 4ª Consolidação", "Capital Social R$ 1.500.000,00: conflito 31/07/2026 × 31/07/2025 e mora de R$ 500 mil",
             "Capital aumentado de R$ 1.000.000 para R$ 1.500.000 (50% Helena / 50% Bruno). Cl. 3ª § 1º fixa integralização até 31/07/2026 e Cl. 4ª fixa 31/07/2025. Sócios confirmaram que nada foi integralizado — mora solidária (CC arts. 1.004, 1.052 e 1.058).",
             "alerta_inconsistencia", "v1 não detectou conflito de datas nem mora", "Notificar sócios (30 dias) e optar por aporte efetivo ou redução do capital."),
            (5, "D2-ANEXO1", "C-02", "Cl. 5ª, Cl. 12ª e Cl. 14ª", "TRÊS critérios conflitantes de apuração de haveres + AGO/Tesouraria",
             "Cl. 5ª I prevê IGPM+3% em 24x; Cl. 12ª §§ 1º/4º prevê Balanço Especial em 10x; Cl. 14ª I-IV prevê Valor de Mercado por avaliadores. Além disso, Cl. 5ª IV menciona 'AGO' e 'tesouraria' (institutos de S.A.).",
             "alerta_inconsistencia", "v1 não analisou haveres nem AGO", "Unificar haveres pelo Balanço de Determinação (CC art. 1.031 / CPC art. 606) e trocar AGO por Reunião/Assembleia."),
            (6, "D2-ANEXO1", "C-02", "Cl. 7ª–11ª Consolidação", "Quórum 50/50 sem desempate (Deadlock) e conflito de mandato de 3 anos",
             "Capital dividido exatamente em 50%/50%, porém cláusulas exigem maioria (>50%). Cl. 11ª remete sócios administradores às regras de não-sócios (mandato de 3 anos da Cl. 10ª § 2º).",
             "alerta_inconsistencia", "Sem mecanismo de resolução de impasse na v1", "Inserir mediação/desempate societário e explicitar mandato por prazo indeterminado dos sócios administradores."),
            (7, "D2-ANEXO1", "C-02", "Cl. 13ª § 1º e Cl. 16ª Consolidação", "JCP oneroso no Simples, pró-labore facultativo e bloqueio de lucros (Lei 4.357/64)",
             "JCP (Cl. 13ª § 1º) sofre 15% IRRF sem dedutibilidade no Simples; pró-labore facultativo (Cl. 16ª) gera risco INSS 11% (SC COSIT 120/2016); débitos mar-ago/2026 bloqueiam lucros (Lei 4.357/64 art. 32 — multa 50%).",
             "alerta_inconsistencia", "Risco previdenciário e multa de 50% não mapeados na v1", "Definir pró-labore formal dos administradores e suspender lucros até regularização fiscal."),
            (8, "D2-ANEXO1", "C-02", "Cl. 15ª Consolidação", "Quórum legal desatualizado (3/4 vs. maioria absoluta da Lei 14.451/2022)",
             "Exige 3/4 do capital para modificação contratual, fusão, incorporação e dissolução, desconsiderando a redução legal para mais da metade do capital promovida pela Lei 14.451/2022 no art. 1.076 do CC.",
             "pendente_revisao", "Redação desatualizada no Anexo I", "Ajustar quórum contratual alinhado ao art. 1.076 CC (Lei 14.451/2022) conforme deliberação dos sócios."),
            (9, "D2-ANEXO1", "C-02", "Cl. 18ª Consolidação", "Regência supletiva contraditória (Sociedade Simples + S.A. simultaneamente)",
             "Prevê aplicar conjuntamente normas de Sociedade Simples e de Sociedade Anônima (CC art. 1.053 permite optar supletivamente pela Lei 6.404/76 ou aplicar Sociedade Simples como regra geral, não cumular ambas sem ordem).",
             "pendente_revisao", "Cláusula ambígua no Anexo I", "Definir regência supletiva única e clara na 3ª Alteração Contratual."),
        ]
        cl_rows = [
            (
                f"inst:d2:{ordem:02d}", emp_id, ordem, bloco, cod, num_cl, tit, txt,
                False, True, None, txt, "balanco_determinacao" if ordem == 5 else "nao_aplicavel",
                "unanimidade" if ordem in (6, 8) else "nao_aplicavel", None, 2,
                "importado_rascunho_v2", st, ref_v1, apont, None, "2a_alteracao",
            )
            for ordem, bloco, cod, num_cl, tit, txt, st, ref_v1, apont in clausulas_2a
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.instrumento_societario_clausula
                (chave, empresa_id, ordem, bloco, codigo_criterio, numero_clausula, titulo, regra_texto,
                 aplica_mou, aplica_contrato, redacao_mou, redacao_contrato, metodo_haveres, quorum_tipo,
                 alcada_centavos, versao, origem_registro, status_validacao, referencia_v1_original,
                 apontamento_auditoria, justificativa_contadora, tipo_instrumento)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            cl_rows,
        )
        counts["erp.instrumento_societario_clausula"] = len(cl_rows)

        # 6. Plano de Saneamento (Estacao 3 -> R-01..R-09 da 3a Alteracao Contratual)
        etapas_d2 = [
            (1, "SAN", "R-01", "Depuração do objeto social e exclusão dos CNAEs de motos/autos (4541-2/01, 4541-2/03, 4511-1/02)", "socias", "JUCEG / RFB (LC 123/2006 art. 17, VIII)", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm", "Anexo I + Relatório de operações reais Itajaí-SC", "Minuta objeto social focado em pneumáticos e câmaras de ar", "10 dias (urgente)", "Se mantiver importação de motos, formalizar exclusão prévia do Simples Nacional.", "alto", "pendente", "SANE-D2-01"),
            (2, "SAN", "R-02", "Saneamento da mora de integralização do capital (R$ 500.000,00) e conflito 2025 × 2026", "socias", "JUCEG / Advogado Societário (CC arts. 1.004 e 1.058)", "https://www.gov.br/empresas-e-negocios/pt-br/drei", "Solicitação_JRNA.pdf (Resp. 1 e 5) + extratos bancários", "Integralização em conta corrente OU redução do capital para R$ 1.000.000,00", "20/10/2026", "Notificar formalmente ambos os sócios em 30 dias antes da deliberação.", "alto", "pendente", "SANE-D2-02"),
            (3, "SAN", "R-03", "Unificação do critério de apuração de haveres (fim do triplo conflito Cl. 5ª × 12ª × 14ª)", "escritorio_contabil", "Advogado Societário / PRISMA JRNA (CC art. 1.031 / CPC art. 606)", "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm", "Diagnóstico Doc. 01 §3.4", "Cláusula única de Balanço de Determinação com prazo e parcelas definidos", "20/10/2026", "Incluir vedação expressa a métodos divergentes em outras cláusulas.", "alto", "pendente", "SANE-D2-03"),
            (4, "SAN", "R-04", "Cláusula de desempate societário (quórum 50/50) e quórum da Lei 14.451/2022", "socias", "Advogado Societário (CC arts. 1.010 e 1.076)", "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm", "Anexo I Cl. 7ª–15ª", "Mediação em 15 dias + cláusula de resolução de impasse e quórum atualizado", "20/10/2026", "Definir mandato por prazo indeterminado para sócios administradores.", "regulatorio", "pendente", "SANE-D2-04"),
            (5, "SAN", "R-05", "Substituição de AGO/Tesouraria (S.A.) e definição da regência supletiva (Cl. 18ª)", "escritorio_contabil", "JUCEG (IN DREI nº 81/2020; CC art. 1.053)", "https://www.gov.br/empresas-e-negocios/pt-br/drei", "Cl. 5ª IV e Cl. 18ª do Anexo I", "Redação ajustada para Reunião de Sócios e regência única", "20/10/2026", "Adequar ao padrão registral DREI para evitar exigência na Junta.", "baixo", "pendente", "SANE-D2-05"),
            (6, "SAN", "R-06", "Padronização da denominação (DISTRIBUIDORA), endereço SC (Sala 223) e erro gramatical Cl. 4ª", "escritorio_contabil", "JUCEG / JUCESC / RFB (DBE Redesim)", "https://www.gov.br/empresas-e-negocios/pt-br/redesim", "Certidão JUCEG + IPTU/Contrato Locação Filial Itajaí-SC", "DBE sincronizado entre Matriz GO e Filial SC", "20/10/2026", "Confrontar alvará e inscrição estadual de SC antes de protocolar DBE.", "baixo", "pendente", "SANE-D2-06"),
            (7, "SAN", "R-07", "Regularização da omissão fiscal/contábil mar–ago/2026 e notificação à Sócontas / Dr. Osvaldo", "escritorio_contabil", "RFB (PGDAS-D) + CRC (Res. CFC nº 1.708/2023)", "https://www2.cfc.org.br/sisweb/sre/Default.aspx", "Extratos OFX (DOC-08) + Termo de Transferência (DOC-07)", "Escrituração retroativa, transmissão PGDAS-D mar–ago/2026 e bloqueio de lucros (Lei 4.357/64)", "30/10/2026", "Manter suspensão expressa de lucros até quitação/parcelamento integral.", "alto", "em_andamento", "SANE-D2-07"),
            (8, "SAN", "R-08", "Protocolo da 3ª Alteração Contratual Consolidada e sincronização na JUCESC (Filial Itajaí)", "orgaos_publicos", "JUCEG (Goiânia-GO) e JUCESC (Itajaí-SC)", "https://www.portaldoempreendedorgoiano.go.gov.br/", "Minuta aprovada + DBE + taxas pagas", "3ª Alteração registrada com sincronização de CNAEs Matriz (GO) e Filial (SC)", "25/10/2026", "Atender eventual exigência da JUCEG/JUCESC em até 30 dias (Lei 8.934/94).", "regulatorio", "pendente", "SANE-D2-08"),
            (9, "SAN", "R-09", "Definição formal de pró-labore dos sócios e exclusão de previsão de JCP no Simples", "socias", "PRISMA JRNA / Sócios (Lei 8.212/91; SC COSIT 120/2016)", "https://www.gov.br/esocial/pt-br/documentacao-tecnica", "PEND-08 + Cl. 13ª § 1º e Cl. 16ª", "Ata/definição de pró-labore e transmissão S-2300/S-1200 se houver retirada", "05/10/2026", "Se não houver retirada, documentar declaração negativa mensal sem distribuição disfarçada.", "alto", "pendente", "SANE-D2-09"),
        ]
        et_rows = [
            (
                f"leg:d2:{cod}", emp_id, ordem, bloco, cod, nome, raia, orgao, url,
                date(2026, 11, 23), entrada, saida, prazo, reg_exig, risco, st, prot,
                "importado_rascunho_v2", "pendente_revisao",
                "Saneamento ausente na 1ª entrega (v1 nao detalhou plano da 3a Alteracao).",
                f"Diretriz {cod} extraida do Doc. 01 §4-§5 para saneamento societario da Rota Sul.",
            )
            for ordem, bloco, cod, nome, raia, orgao, url, entrada, saida, prazo, reg_exig, risco, st, prot in etapas_d2
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.processo_legalizacao_etapa
                (chave, empresa_id, ordem, bloco, codigo, nome_etapa, raia_responsavel, orgao, portal_url,
                 data_consulta, entrada_docs, saida_doc, prazo_legal, regra_retorno_exigencia,
                 classificacao_risco, status, protocolo_simulado, origem_registro, status_validacao,
                 referencia_v1_original, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            et_rows,
        )
        counts["erp.processo_legalizacao_etapa"] = len(et_rows)

        # 7. Criterios D2 (47) e Avaliacoes (em quarentena — nota NULL ate contadora homologar)
        crit_rows = [
            (f"crit:d2:{cod}", mat, blk, f"Produto {blk} — Dossiê 2", peso, cod, desc, ref_loc, "D2")
            for mat, blk, cod, _nv1, _cv1, peso, desc, ref_loc in CRITERIOS_D2
        ]
        execute_values(
            cur,
            """
            INSERT INTO auditoria.criterio_conformidade
                (chave, matriz, bloco, bloco_titulo, bloco_peso, codigo, descricao, referencia_fonte, dossie)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            crit_rows,
        )
        cur.execute("SELECT id, matriz, codigo FROM auditoria.criterio_conformidade WHERE dossie = 'D2'")
        crit_id_map = {(r["matriz"], r["codigo"]): int(r["id"]) for r in cur.fetchall()}
        av_rows = [
            (
                f"av:d2:{cod}", emp_id, crit_id_map[(mat, cod)], nv1, None, False, ref_loc, cv1, None,
                "importado_v1", "pendente_revisao", "Devolutiva D2 G07 / Quarentena", "D2",
            )
            for mat, _blk, cod, nv1, cv1, _peso, _desc, ref_loc in CRITERIOS_D2
            if (mat, cod) in crit_id_map
        ]
        execute_values(
            cur,
            """
            INSERT INTO auditoria.avaliacao_conformidade
                (chave, empresa_id, criterio_id, nota_v1, nota, nao_aplicavel, referencia_localizacao,
                 critica_v1, justificativa_sustentacao, origem_registro, status_validacao, autor, dossie)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            av_rows,
        )
        counts["auditoria.criterio_conformidade:D2"] = len(crit_rows)
        counts["auditoria.avaliacao_conformidade:D2"] = len(av_rows)

        # 8. Consultas normativas / Premissas PR-01..PR-18 (dossie = 'D2')
        pr_rows = [
            (
                f"cn:d2:PR-{num:02d}", emp_id, num, enunciado, resp, norma, url, dt, dec,
                "importado_rascunho_v2", "pendente_revisao",
                "Produto P8 (Registro de Premissas) ausente na entrega v1." if num <= 17 else "Empregados ficticios criados para transparência LGPD.",
                apont, "D2",
            )
            for num, enunciado, resp, norma, url, dec, apont, dt in PREMISSAS_D2
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.consulta_normativa
                (chave, empresa_id, numero_questao, enunciado, resposta_autoral, norma_citada, link_oficial,
                 data_acesso, decisao_impactada, origem_registro, status_validacao, referencia_v1_original,
                 apontamento_auditoria, dossie)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            pr_rows,
        )
        counts["erp.consulta_normativa:D2"] = len(pr_rows)

        # 9. Diario IA (D2 — Doc 15)
        diario_d2 = [
            ("ia:d2:01", "Mapeamento, Analise GAP e Questionario", "Decomposicao dos 47 itens da Devolutiva em plano por ondas e questionario objetivo para decisao humana.", "REF_Devolutiva_Dossie2_G07.pdf + Estudo de Caso 02", "Expurgado parecer de outra dupla anexado por engano e validadas as respostas pela dupla.", "Jeovanna / Nathalia", "Diagnostico e Planejamento", "Antigravity (Gemini 4)"),
            ("ia:d2:02", "Analise critica do Anexo I (Cl. 1a-19a)", "Tabulacao dispositivo a dispositivo do Anexo I, confronto 18x17 CNAEs, riscos LC 123 art. 17 VIII e plano da 3a Alteracao.", "Anexo I + Planalto (LC 123/2006 conferida diretamente)", "Corrigida citacao literal do art. 17, VIII (importacao ou fabricacao de autos e motos) e classificados riscos.", "Jeovanna / Nathalia", "Doc. 01", "Antigravity (Gemini 4) / Claude"),
            ("ia:d2:03", "Proposta, Contrato (+ Procuracao) e Termo RT", "Alinhamento contratual com Dossie 1 (Asa Sul, RT Nathalia, assinatura conjunta > R$ 15 mil), R$ 125/h e Res. CFC 1.708/2023.", "Res. CFC 1.708/2023 + ITG 1000 + Contrato Social D1", "Eliminados todos os [INSERIR] e atualizada a resolucao revogada 1.555/2018.", "Nathalia / Jeovanna", "Docs. 02-04", "Google Gemini (v1) + Antigravity"),
            ("ia:d2:04", "Onboarding, Checklist DOC-01..13 e Pendencias", "Organizacao das 5 respostas literais do cliente e registro honesto de lacunas sem resposta formal arquivada.", "Solicitacao_JRNA.pdf p. 3 + relato de onboarding", "Garantida ausencia de inventar prints de ASO, parecer de advogado ou distrato do contador anterior.", "Jeovanna / Nathalia", "Doc. 05", "Antigravity (Gemini 4)"),
            ("ia:d2:05", "Prontuarios, Fichas, Contratos e eSocial", "Remocao de 6 residuos [cite], roteiro eSocial S-1.3 sem recibos ficticios, termos VT/VR e dados ficticios didaticos (PR-18).", "CLT + Lei 3.207/57 art. 7o + MOS eSocial S-1.3 + LGPD", "Restaurado intervalo literal de 1h48 (41h x 44h como PEND-04) sem inventar sabados.", "Nathalia / Jeovanna", "Docs. 06-10", "Google Gemini (v1) + Antigravity"),
            ("ia:d2:06", "Planilha aberta, Folha 09/2026, Provisoes e Partidas Dobradas", "Construcao de memoria com formulas dinamicas, INSS 2026 (Port. 13/2026), IRRF 2026 (Lei 15.270/2025), provisoes e L1-L4.", "Portaria MPS/MF 13/2026; Lei 15.270/2025; CCT SRT00189/2025; NBC TG 33", "Recalculo independente manual em Python/Excel bateu 11/11 rubricas com diferenca R$ 0,00.", "Jeovanna / Nathalia", "Docs. 11 e 12", "Antigravity (Gemini 4)"),
            ("ia:d2:07", "Auditoria Trabalhista (PT-01..05) e Premissas (PR-01..18)", "Estruturacao NBC TA 315/330, confronto triplo v1 x Auditoria x Planilha e catalogo de 10 achados + 18 premissas oficiais.", "NBC TA 315/330 + Mediador MTE + Portal Planalto", "Revisao cruzada entre documentos eliminou codigos antigos e caminhos internos de arquivo.", "Jeovanna / Nathalia", "Docs. 13 e 14", "Antigravity / Claude Code"),
        ]
        execute_values(
            cur,
            """
            INSERT INTO auditoria.diario_ia
                (chave, dossie, empresa_id, finalidade, prompt_resumo, fonte_oficial, revisao_humana,
                 autor, entregavel, ferramenta, origem_registro, status_validacao)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            [
                (ch, "D2", emp_id, fin, pr, fnt, rev, aut, ent, fer, "importado_rascunho_v2", "pendente_revisao")
                for ch, fin, pr, fnt, rev, aut, ent, fer in diario_d2
            ],
        )
        counts["auditoria.diario_ia:D2"] = len(diario_d2)

    conn.commit()
    return counts


def importar_secoes_dossie2(conn: Any, editaveis_dir: Path = DEFAULT_D2_EDITAVEIS) -> dict[str, int]:
    """Importa secoes dos 16 arquivos .md do Dossie 2 para erp.documento_secao (dossie='D2')."""
    contagem: dict[str, int] = {}
    if not editaveis_dir.exists():
        return contagem
    with conn.cursor() as cur:
        emp_id = _obter_emp_id_d2(cur)
        for doc_cod, fname in DOCUMENTOS_D2_ARQUIVOS:
            fpath = editaveis_dir / fname
            if not fpath.exists():
                continue
            secoes = _dividir_secoes_md(fpath.read_text(encoding="utf-8"))
            contagem[doc_cod] = len(secoes)
            for s in secoes:
                apont = "Texto importado dos editaveis D2 (_entrega_limpa). Conferir numeros e status de pendencias antes de homologar."
                cur.execute(
                    """
                    INSERT INTO erp.documento_secao
                        (chave, empresa_id, documento, ordem, codigo_secao, titulo, conteudo_md,
                         origem_registro, status_validacao, apontamento_auditoria, dossie)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'importado_rascunho_v2', 'pendente_revisao', %s, 'D2')
                    ON CONFLICT (chave) DO NOTHING
                    """,
                    (
                        f"docsec:d2:{doc_cod}:{s['codigo_secao']}", emp_id, doc_cod,
                        s["ordem"], s["codigo_secao"], s["titulo"], s["conteudo_md"], apont,
                    ),
                )
    conn.commit()
    return contagem


def semear_onboarding(conn: Any) -> dict[str, int]:
    """Semear Estacao 7 (P2 Contratos de Servico + P3 Diligencia Q1..Q9, DOC-01..13, PEND-01..08)."""
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        emp_id = _obter_emp_id_d2(cur)
        cur.execute("SELECT id FROM erp.relacao_escritorio_cliente WHERE chave = %s", (RELACAO_CHAVE_D2,))
        rel = cur.fetchone()
        rel_id = int(rel["id"]) if rel else None

        # 4 documentos de P2 (erp.contrato_servico)
        mem_horas = json.dumps([
            {"frente": "Setup Fee (Implantação)", "horas": 16, "valor_hora": 125, "total": 2000},
            {"frente": "Recuperação Passivo Mar–Ago/2026 (6 × 16h)", "horas": 96, "valor_hora": 125, "total": 12000},
            {"frente": "Mensal Matriz (GO) + DP", "horas": 20, "valor_hora": 125, "total": 2500},
            {"frente": "Mensal Filial (Itajaí-SC)", "horas": 12, "valor_hora": 125, "total": 1500},
            {"frente": "13º Honorário Anual (Dezembro)", "horas": 32, "valor_hora": 125, "total": 4000},
        ], ensure_ascii=False)

        contratos = [
            ("cs:d2:proposta", "proposta", 1, "Proposta Técnica e Comercial de Honorários Contábeis e BPO",
             400000, True, 12500, 32, mem_horas, date(2026, 9, 14), "Goiânia-GO",
             "Setup R$ 2.000 + Recuperação mar-ago/2026 R$ 12.000 + Recorrente R$ 4.000/mês (2.500 Matriz GO + 1.500 Filial SC) + 13º Honorário R$ 4.000 (32h x R$ 125/h).",
             "Proposta alinhada ao Dossiê 1 (Asa Sul, sala 901) cobrindo os 2 estabelecimentos em GO e SC e operação de importação."),
            ("cs:d2:contrato", "contrato", 2, "Contrato de Prestação de Serviços Contábeis e BPO",
             400000, True, 12500, 32, mem_horas, date(2026, 9, 1), "Goiânia-GO",
             "Vigência 12 meses a partir de 01/09/2026, reajuste IPCA, aviso prévio 30d, assinatura conjunta > R$ 15.000 (Nathalia + Jeovanna), blindagem mar-ago/2026 e Res. CFC nº 1.708/2023.",
             "Inclui Carta de Responsabilidade anual (ITG 1000 / NBC TA 580), sigilo NBC PG 01 e cláusula LGPD (Lei 13.709/2018)."),
            ("cs:d2:termo_rt", "termo_rt", 3, "Termo de Responsabilidade Técnica Contábil (Res. CFC nº 1.708/2023)",
             400000, True, 12500, 32, "[]", date(2026, 9, 1), "Goiânia-GO",
             "Assunção RT exclusiva por Nathalia Peres Araujo (CRC-DF 025.431/O-7) a partir de 01/09/2026 com delimitação mar-ago/2026 (Sócontas / Dr. Osvaldo) e rol de 7 pendências.",
             "Substituiu a revogada Res. CFC 1.555/2018 pela Res. CFC nº 1.708/2023."),
            ("cs:d2:procuracao", "procuracao", 4, "Anexo I — Minuta de Procuração Eletrônica e Administrativa",
             0, True, 0, 0, "[]", date(2026, 9, 14), "Goiânia-GO",
             "Poderes estritamente técnicos no e-CAC, eSocial, DCTFWeb, FGTS Digital, SEFAZ-GO/SC e Juntas Comerciais; vedado confessar dívida, parcelar ou movimentar conta bancária.",
             "Vigência vinculada de 12 meses a partir de 14/09/2026."),
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.contrato_servico
                (chave, empresa_id, relacao_id, codigo_documento, ordem, titulo, honorario_mensal_centavos,
                 tem_decimo_terceiro, valor_hora_centavos, horas_mes_estimadas, memoria_horas_json,
                 vigencia_inicio, foro, escopo_resumo, conteudo_md, origem_registro, status_validacao,
                 referencia_v1_original, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            [
                (ch, emp_id, rel_id, cod, ord_, tit, hon, dec13, vh, hm, mh, vig, foro, esc, txt,
                 "importado_rascunho_v2", "pendente_revisao",
                 "v1 possuía campos [INSERIR] e 13º divergente entre Proposta e Contrato.",
                 f"Conferir coerência cruzada com Doc. 02/03/04 e Dossiê 1 antes de homologar ({cod}).")
                for ch, cod, ord_, tit, hon, dec13, vh, hm, mh, vig, foro, esc, txt in contratos
            ],
        )
        counts["erp.contrato_servico"] = len(contratos)

        # Diligencia P3: DOC-01..DOC-13, Q1..Q9, PEND-01..PEND-08
        dilig_rows: list[tuple[Any, ...]] = []
        docs_p3 = [
            ("DOC-01", 1, "advogado", "Societário", "Contrato Social Original (28/10/2024) e 1ª Alteração Contratual", "Reconstruir histórico e integralização inicial de R$ 1.000.000,00.", "25/09/2026", "baixo", "pendente_critico"),
            ("DOC-02", 2, "advogado", "Societário", "2ª Alteração e Consolidação Contratual (22/07/2025 — Anexo I)", "Diagnóstico cadastral, 18/17 CNAEs, governança e capital.", "14/09/2026", "critico", "em_saneamento"),
            ("DOC-03", 3, "cliente", "Societário / DP", "RG, CPF, comprovante de residência dos sócios e definição de pró-labore", "Conferência cadastral, procuração e eventual S-2300.", "25/09/2026", "alto", "pendente_critico"),
            ("DOC-04", 4, "cliente", "Fiscal / Aduaneiro", "Certificados Digitais (e-CNPJ A1) da Matriz (GO) e Filial (SC) + senhas", "Transmissão PGDAS-D, eSocial, DCTFWeb, FGTS Digital e SEFAZ.", "18/09/2026", "critico", "pendente_critico"),
            ("DOC-05", 5, "cliente", "Fiscal / Aduaneiro", "Alvarás de Funcionamento e Inscrições Estaduais (GO e SC)", "Validar endereço filial SC (Sala 223 x 223 A 32) e CNAEs ativos.", "25/09/2026", "medio", "pendente_critico"),
            ("DOC-06", 6, "cliente", "Fiscal / Aduaneiro", "Comprovantes de habilitação ativa RADAR/Siscomex (Matriz e Filial)", "Cliente confirmou ativo em Q3 — comprovantes estão com despachante em Itajaí.", "30/09/2026", "alto", "em_saneamento"),
            ("DOC-07", 7, "contador_anterior", "Contábil / Transição", "Termo de Transferência de Responsabilidade Técnica (Res. CFC 1.708/2023) e distrato", "Formalizar sucessão técnica até 31/08/2026 (Sócontas / Dr. Osvaldo).", "25/09/2026", "critico", "sem_resposta"),
            ("DOC-08", 8, "contador_anterior", "Contábil / Financeiro", "Balanço, DRE, Balancete (fev e ago/2026) + Extratos OFX (mar–set/2026)", "Saldos de abertura e recuperação da omissão de mar–ago/2026.", "30/09/2026", "critico", "pendente_critico"),
            ("DOC-09", 9, "cliente", "Departamento Pessoal", "Documentos civis admissionais E1 e E2 (RG, CPF, título, certidão filho E1)", "Completar prontuários docs. 06–10 (dados fictícios didáticos PR-18).", "25/09/2026", "baixo", "concluido"),
            ("DOC-10", 10, "cliente", "DP / SST (NR-7)", "Exame Médico Admissional (ASO) de E1 e E2", "Cumprimento pré-admissional e transmissão do S-2220.", "Imediato (02/10/2026)", "critico", "pendente_critico"),
            ("DOC-11", 11, "cliente", "DP / SST (NR-1/NR-4)", "Grau de Risco NR-4, PGR (ou DIR), PCMSO e LTCAT", "Lastro técnico obrigatório para envio do S-2240 no eSocial.", "15/10/2026", "alto", "pendente_critico"),
            ("DOC-12", 12, "cliente", "Departamento Pessoal", "Termos assinados de VT e VR + controle de ponto implantado", "Lastrear descontos VT (6%, 4x2 passagens), VR/PAT e jornada.", "05/10/2026", "alto", "pendente_critico"),
            ("DOC-13", 13, "cliente", "Departamento Pessoal", "Relatório comercial validado de vendas líquidas e estornos do E2 (set/2026)", "Validar premissa de R$ 60.000,00 (comissão R$ 900 + DSR R$ 100).", "05/10/2026", "medio", "em_saneamento"),
        ]
        for cod, ord_, ator, tema, enun, resp, prazo, risco, st in docs_p3:
            dilig_rows.append((
                f"dil:d2:{cod}", emp_id, "documento", cod, ord_, ator, tema, enun, resp,
                "Doc. 05 §1 (Checklist de Onboarding)", date(2026, 9, 14), "Diretoria / DP PRISMA", prazo, risco, st,
                "importado_rascunho_v2", "pendente_revisao" if st != "concluido" else "pendente_revisao",
                "Checklist v1 não segregava ator responsável nem status real.", None,
            ))

        perguntas_p3 = [
            ("Q1", 1, "cliente", "Capital Social (R$ 500.000)", "O aporte pendente de R$ 500.000,00 foi integralizado na conta corporativa?", "\"Não, senhores, ainda não colocamos os R$ 500 mil. O prazo que assumimos é 31/07/2026 — o que está escrito 2025 naquele outro trecho é erro mesmo. Como não pagamos nada, não tem lançamento nenhum na conta da empresa, pode conferir.\"", "Solicitação_JRNA.pdf, pág. 3 (resposta escrita)", "concluido"),
            ("Q2", 2, "cliente", "Regime Tributário", "Qual o enquadramento tributário atual da Rota Sul perante a RFB?", "\"A gente está no Simples Nacional desde que abriu a empresa, lá em outubro de 2024. Nunca mudamos de regime.\"", "Solicitação_JRNA.pdf, pág. 3 (resposta escrita)", "concluido"),
            ("Q3", 3, "cliente", "RADAR / Siscomex", "Matriz e Filial possuem habilitação ativa no RADAR/Siscomex?", "\"A habilitação está ativa, sim, tanto da matriz quanto da filial de Itajaí. Os comprovantes estão com o despachante lá em Itajaí; se precisarem, a gente pede para ele mandar.\"", "Solicitação_JRNA.pdf, pág. 3 (resposta escrita)", "concluido"),
            ("Q4", 4, "cliente", "Ponto e DSR s/ Comissões", "Adotarão ponto? A comissão de 1,5% de E2 já inclui o DSR?", "\"Ponto? A gente não tem sistema nenhum comprado para isso. O pessoal ia marcar no papel, num caderno mesmo, ou anotar no celular — o que vocês recomendarem está bom. Sobre a comissão, combinamos com o vendedor 1,5% em cima das vendas líquidas do mês, e ponto. Não sei nada desse DSR, achava que o valor combinado já era tudo. Isso é coisa para vocês resolverem.\"", "Solicitação_JRNA.pdf, pág. 3 (resposta escrita)", "concluido"),
            ("Q5", 5, "cliente", "Conflito de Datas (Anexo I)", "Houve retificação corrigindo 31/07/2026 (Cl. 3ª) vs. 31/07/2025 (Cl. 4ª)?", "\"Nenhuma retificação, não. A gente nem tinha percebido que o documento mostra duas datas diferentes. O prazo real que a gente se comprometeu é 31/07/2026; não fizemos alteração posterior nenhuma corrigindo isso.\"", "Solicitação_JRNA.pdf, pág. 3 (resposta escrita)", "concluido"),
            ("Q6", 6, "cliente", "Parâmetros dos Empregados", "Informação verbal sobre cargos, salários, jornadas (1h48 E1), VT 2 conduções/dia e dependente.", "Dados do Estudo de Caso 02 + docs civis fictícios (PR-18); intervalo 1h48 mantido com registro da incoerência 41h x 44h.", "Relato verbal (Caso 02, págs. 2-3)", "em_saneamento"),
            ("Q7", 7, "cliente", "ASO Admissional (NR-7)", "Realização de exame médico admissional prévio para E1 e E2.", "Informado verbalmente que não foram feitos; mantido como PEND-01 crítico sem print arquivado.", "Relato de onboarding (sem registro escrito)", "pendente_critico"),
            ("Q8", 8, "contador_anterior", "Omissão Mar–Ago/2026", "Transmissão PGDAS-D e escrituração mar–ago/2026 e distrato (Sócontas / Dr. Osvaldo).", "Relato verbal dos sócios sobre paralisação; sem resposta formal escrita do contador anterior.", "Relato de onboarding (sem resposta formal)", "sem_resposta"),
            ("Q9", 9, "advogado", "Parecer Jurídico 3ª Alteração", "Manifestação do advogado societário/trabalhista da Rota Sul.", "Sem parecer escrito ou resposta formal recebida até o encerramento do dossiê.", "Sem manifestação formal recebida", "sem_resposta"),
        ]
        for cod, ord_, ator, tema, enun, resp, fonte, st in perguntas_p3:
            dilig_rows.append((
                f"dil:d2:{cod}", emp_id, "pergunta", cod, 100 + ord_, ator, tema, enun, resp,
                fonte, date(2026, 9, 14), "PRISMA JRNA", "23/11/2026", "alto" if st != "concluido" else "baixo", st,
                "importado_rascunho_v2", "pendente_revisao",
                "v1 omitia as 5 respostas literais da Solicitação_JRNA.", None,
            ))

        pendencias_p3 = [
            ("PEND-01", 1, "cliente", "SST / NR-7", "ASO admissional de E1 e E2 não realizado", "Realizar exames clínicos imediatos, transmitir S-2220 e arquivar em docs. 06–10.", "02/10/2026", "critico", "pendente_critico"),
            ("PEND-02", 2, "advogado", "Societário", "3ª Alteração Contratual (CNAE 4541-2/01, R$ 500 mil, datas, 3 haveres, 50/50, AGO, Sala 223)", "Submeter diretrizes do Doc. 01 ao advogado e registrar na JUCEG/JUCESC.", "20/10/2026", "critico", "pendente_critico"),
            ("PEND-03", 3, "contador_anterior", "Fiscal / Contábil", "Omissão mar–ago/2026, notificação a Sócontas / Dr. Osvaldo e bloqueio de lucros", "Notificar contador anterior (Res. CFC 1.708/2023), coletar OFX, transmitir PGDAS-D e manter bloqueio Lei 4.357/64.", "30/10/2026", "critico", "pendente_critico"),
            ("PEND-04", 4, "escritorio", "DP / Jornada", "Termos VT/VR (DOC-12), implantação de ponto formal e ajuste das 3h da jornada E1 (41h vs 44h)", "Colher assinaturas VT/VR, implantar ponto idôneo e formalizar escala das 3h.", "05/10/2026", "alto", "pendente_critico"),
            ("PEND-05", 5, "cliente", "Comercial", "Validação do faturamento de vendas líquidas do E2 (premissa didática R$ 60.000,00)", "Enviar relatório validado de NF-e/estornos (DOC-13).", "05/10/2026", "medio", "em_saneamento"),
            ("PEND-06", 6, "cliente", "Procuração / Aduaneiro", "Procurações eletrônicas assinadas, e-CNPJs e comprovantes RADAR/Siscomex (Itajaí)", "Outorgar procurações (Anexo I Doc. 03), enviar e-CNPJs e coletar RADAR com despachante.", "05/10/2026", "alto", "pendente_critico"),
            ("PEND-07", 7, "cliente", "SST (S-2240)", "Laudos SST além do ASO (Grau Risco NR-4, PGR/DIR, PCMSO e LTCAT)", "Contratar clínica SST para lastrear envio do S-2240.", "15/10/2026", "alto", "pendente_critico"),
            ("PEND-08", 8, "cliente", "Pró-Labore", "Definição formal de pró-labore dos sócios Helena e Bruno (S-2300/S-1200)", "Definir valor mensal de pró-labore ou formalizar ausência de retirada na competência.", "05/10/2026", "medio", "pendente_critico"),
        ]
        for cod, ord_, ator, tema, enun, resp, prazo, risco, st in pendencias_p3:
            dilig_rows.append((
                f"dil:d2:{cod}", emp_id, "pendencia", cod, 200 + ord_, ator, tema, enun, resp,
                "Doc. 05 §3 (Quadro de Pendências)", date(2026, 9, 14), ator, prazo, risco, st,
                "importado_rascunho_v2", "pendente_revisao",
                "v1 não possuía quadro estruturado de pendências.", None,
            ))

        execute_values(
            cur,
            """
            INSERT INTO erp.diligencia_item
                (chave, empresa_id, tipo, codigo, ordem, ator, tema, enunciado, resposta_literal,
                 fonte_evidencia, data_interacao, responsavel, prazo_texto, risco, status_item,
                 origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            dilig_rows,
        )
        counts["erp.diligencia_item"] = len(dilig_rows)
    conn.commit()
    return counts


def semear_dp(conn: Any) -> dict[str, int]:
    """Semear Estacao 8 (P4: Parametros Legais 2026 + CCT, Contratos E1/E2 e Roteiro eSocial)."""
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        emp_id = _obter_emp_id_d2(cur)
        cur.execute("SELECT id FROM erp.estabelecimento WHERE chave = 'est:rota_sul_d2:matriz'")
        est_row = cur.fetchone()
        est_matriz_id = int(est_row["id"]) if est_row else None

        # 1. Parametros legais 2026 + CCT SRT00189/2025 + Aditivo 2026/2027
        params = [
            ("inss", 1, "INSS-F1", "INSS 2026 Faixa 1 (até R$ 1.621,00 — 7,5%)", 162100, 75000, 0, None, "Portaria MPS/MF nº 13/2026", "https://www.gov.br/inss/", "Alíquota 7,5% até R$ 1.621,00."),
            ("inss", 2, "INSS-F2", "INSS 2026 Faixa 2 (R$ 1.621,01 a R$ 2.902,84 — 9%)", 290284, 90000, 2431, None, "Portaria MPS/MF nº 13/2026", "https://www.gov.br/inss/", "Alíquota 9% com parcela a deduzir R$ 24,315 (truncada 24,31 na faixa progressiva)."),
            ("inss", 3, "INSS-F3", "INSS 2026 Faixa 3 (R$ 2.902,85 a R$ 4.354,27 — 12%)", 435427, 120000, 11140, None, "Portaria MPS/MF nº 13/2026", "https://www.gov.br/inss/", "Alíquota 12% sobre a parcela entre R$ 2.902,85 e R$ 4.354,27."),
            ("inss", 4, "INSS-F4", "INSS 2026 Faixa 4 (R$ 4.354,28 a R$ 8.475,55 — 14%)", 847555, 140000, 19849, None, "Portaria MPS/MF nº 13/2026", "https://www.gov.br/inss/", "Teto previdenciário R$ 8.475,55 (alíquota 14%)."),
            ("irrf", 1, "IRRF-F1", "IRRF Clássico Faixa Isenta (até R$ 2.428,80)", 242880, 0, 0, None, "Lei nº 14.848/2024 / RFB 2026", "https://www.gov.br/receitafederal/", "Isento até R$ 2.428,80."),
            ("irrf", 2, "IRRF-F2", "IRRF Faixa 2 (R$ 2.428,81 a R$ 2.826,65 — 7,5%)", 282665, 75000, 18216, None, "Lei nº 14.848/2024 / RFB 2026", "https://www.gov.br/receitafederal/", "7,5% - dedução R$ 182,16."),
            ("irrf", 3, "IRRF-F3", "IRRF Faixa 3 (R$ 2.826,66 a R$ 3.751,05 — 15%)", 375105, 150000, 39416, None, "Lei nº 14.848/2024 / RFB 2026", "https://www.gov.br/receitafederal/", "15% - dedução R$ 394,16."),
            ("irrf", 4, "IRRF-F4", "IRRF Faixa 4 (R$ 3.751,06 a R$ 4.664,68 — 22,5%)", 466468, 225000, 67549, None, "Lei nº 14.848/2024 / RFB 2026", "https://www.gov.br/receitafederal/", "22,5% - dedução R$ 675,49."),
            ("irrf", 5, "IRRF-F5", "IRRF Faixa 5 (acima de R$ 4.664,68 — 27,5%)", None, 275000, 90873, None, "Lei nº 14.848/2024 / RFB 2026", "https://www.gov.br/receitafederal/", "27,5% - dedução R$ 908,73."),
            ("irrf", 6, "IRRF-SIMPLIF", "Desconto Simplificado Mensal IRRF (R$ 607,20)", 60720, None, None, 60720, "Lei nº 14.848/2024 / RFB 2026", "https://www.gov.br/receitafederal/", "Comparado com (INSS + dependentes) escolhendo o maior desconto."),
            ("irrf", 7, "IRRF-DEP", "Dedução por Dependente IRRF (R$ 189,59)", None, None, None, 18959, "RFB 2026", "https://www.gov.br/receitafederal/", "R$ 189,59 por dependente legal quando usa deduções legais."),
            ("reducao_irrf_2026", 1, "RED-ISENTO", "Redução IRRF 2026 — Isenção até R$ 5.000,00 (Redutor máx. R$ 312,89)", 500000, None, None, 31289, "Lei nº 15.270/2025", "https://www.gov.br/receitafederal/", "Rendimentos tributáveis <= R$ 5.000,00 têm redução que zera o IRRF."),
            ("reducao_irrf_2026", 2, "RED-TRANS", "Redução IRRF 2026 — Transição R$ 5.000,01 a R$ 7.350,00", 735000, 133145, 97862, None, "Lei nº 15.270/2025", "https://www.gov.br/receitafederal/", "Redutor linear = max(0, 978,62 - 0,133145 * rendimentos)."),
            ("salario_familia", 1, "SF-2026", "Salário-Família 2026 — Teto R$ 1.980,38 / Cota R$ 67,54", 198038, None, None, 6754, "Portaria MPS/MF nº 13/2026 + Dec. 3.048/99 art. 82", "https://www.gov.br/inss/", "E1 tem salário contratual R$ 2.400,00 > R$ 1.980,38 -> inelegível."),
            ("fgts", 1, "FGTS-8", "FGTS Mensal (8% s/ Remuneração e s/ Provisões)", None, 80000, None, None, "Lei nº 8.036/1990 (FGTS Digital PIX)", "https://www.gov.br/trabalho-e-emprego/", "Alíquota padrão 8% via FGTS Digital."),
            ("cct_clausula", 1, "CCT-PISO-GERAL", "CCT Cl. 3ª — Piso Geral Goiania (R$ 1.722,25)", None, None, None, 172225, "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Adit. 2026/2027 Cl. 3ª)", "https://www3.mte.gov.br/sistemas/mediador/", "Vigência 01/04/2026; E1 recebe R$ 2.400,00 (> piso)."),
            ("cct_clausula", 2, "CCT-PISO-VEND", "CCT Cl. 3ª — Garantia Mínima Vendedor (R$ 1.863,00)", None, None, None, 186300, "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Aditivo Cl. 3ª)", "https://www3.mte.gov.br/sistemas/mediador/", "E2 possui fixo R$ 1.900,00 (> garantia mínima)."),
            ("cct_clausula", 3, "CCT-VT-MISTO", "CCT Cl. 6ª — Teto Base VT Salário Misto (R$ 2.257,50) / RMTC R$ 4,30", 225750, 60000, None, 430, "CCT Cl. 6ª + Lei 7.418/1985 art. 4º + RMTC Goiânia", "https://www.rmtcgoiania.com.br/", "Desconto máximo 6% do salário básico proporcional (tarifa R$ 4,30)."),
            ("cct_clausula", 4, "CCT-NEGOCIAL", "CCT Cl. 11ª — Contribuição Negocial (3,33%, Teto R$ 148,00)", 14800, 33300, None, 14800, "CCT Aditivo 2026/2027 Cl. 11ª + STF Tema 935", "https://portal.stf.jus.br/", "3,33% sobre proventos brutos limitado a R$ 148,00; proibido fornecer modelo de oposição."),
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.parametro_legal
                (chave, empresa_id, vigencia, categoria, ordem, codigo, descricao, limite_centavos,
                 aliquota_micro, deducao_centavos, valor_centavos, norma_citada, link_oficial,
                 data_consulta, regra_texto, origem_registro, status_validacao, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            [
                (f"par:d2:{cod}", emp_id, "2026", cat, ord_, cod, desc, lim, aliq, ded, val, norm, url,
                 date(2026, 11, 23), txt, "importado_rascunho_v2", "pendente_revisao",
                 "Conferir tabela oficial 2026 e registro MTE SRT00189/2025 antes de homologar.")
                for cat, ord_, cod, desc, lim, aliq, ded, val, norm, url, txt in params
            ],
        )
        counts["erp.parametro_legal"] = len(params)

        # 2. Contratos de trabalho E1 e E2 (dados ficticios PR-18 + parametros exatos do caso)
        deps_e1 = json.dumps([{
            "nome": "Lucas Alves Costa", "parentesco": "Filho", "nascimento": "2020-03-12",
            "cpf": "456.789.123-64", "elegivel_irrf": True, "elegivel_sf": False,
        }], ensure_ascii=False)
        docs_e1 = json.dumps(["RG/CPF (ficticio)", "Titulo/Residencia", "Certidao/CPF/Vacina/Escola filho"], ensure_ascii=False)
        docs_e2 = json.dumps(["RG/CPF (ficticio)", "Titulo/Residencia"], ensure_ascii=False)

        cts = [
            ("ct:d2:E1", emp_id, est_matriz_id, "E1", "Mariana Alves Costa", "123.456.789-09",
             "Auxiliar Administrativo", "administrativo", "4110-05", date(2026, 9, 16), 45, 45,
             240000, 172225, 0, 44, "Segunda a sexta, 08h00 às 18h00 com intervalo de 1h48 (41h reais vs 44h contratuais — PEND-04)",
             108, "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Adit. 2026/2027)",
             True, 4, 430, True, 3000, "pendente_critico",
             "ASO Admissional (NR-7) NÃO realizado antes da admissão (PEND-01 / AUD-01).",
             1, 1, deps_e1, docs_e1, "importado_rascunho_v2", "alerta_inconsistencia",
             "v1 alterava intervalo para 1h12, inventava sábados, citava CNAE 4530-7/01 e concedia Salário-Família.",
             "Jornada literal 1h48 mantida (41h x 44h como PEND-04); ASO pendente real; CPF fictício didático (PR-18)."),
            ("ct:d2:E2", emp_id, est_matriz_id, "E2", "Rafael Souza Lima", "987.654.321-00",
             "Vendedor de Comércio Varejista", "comercial", "5211-10", date(2026, 9, 21), 30, 60,
             190000, 186300, 15000, 44, "Segunda a sexta 09h00–18h00 (1h int.) e sábados 09h00–13h00 (44h/sem)",
             60, "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Adit. 2026/2027)",
             True, 4, 430, False, 0, "pendente_critico",
             "ASO Admissional (NR-7) NÃO realizado antes da admissão (PEND-01 / AUD-01).",
             0, 0, "[]", docs_e2, "importado_rascunho_v2", "alerta_inconsistencia",
             "v1 deixava 6 marcações [cite: 19, 25], CNAE 4530-7/01 e omitia comissão/DSR na folha.",
             "Comissão 1,5% + DSR destacado; estorno restrito a insolvência (Lei 3.207/57 art. 7º); sem VR em 09/2026."),
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.contrato_trabalho
                (chave, empresa_id, estabelecimento_id, codigo_empregado, nome_empregado, cpf_ficticio,
                 cargo, departamento, cbo, data_admissao, experiencia_dias_1, experiencia_dias_2,
                 salario_base_centavos, piso_cct_centavos, comissao_pct_micro, jornada_semanal_horas,
                 jornada_descricao, intervalo_minutos, cct_referencia, vt_optante, vt_passagens_dia,
                 vt_tarifa_centavos, vr_elegivel, vr_valor_dia_centavos, aso_status, aso_observacao,
                 qtd_dependentes_ir, qtd_dependentes_sf, dependentes_json, docs_admissionais_json,
                 origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            cts,
        )
        counts["erp.contrato_trabalho"] = len(cts)

        cur.execute("SELECT id, codigo_empregado FROM erp.contrato_trabalho WHERE empresa_id = %s", (emp_id,))
        ct_map = {r["codigo_empregado"]: int(r["id"]) for r in cur.fetchall()}

        # 3. Roteiro eSocial (sem inventar nenhum numero de recibo)
        eventos_esocial = [
            ("esoc:d2:S-1000", emp_id, None, 1, "S-1000", "Informações do Empregador (Classif. Trib. 01 — Simples Nacional)", "2026-09", "Antes dos demais eventos", "aguardando_insumo", "Depende de procuração / e-CNPJ A1 (DOC-04)."),
            ("esoc:d2:S-1005", emp_id, None, 2, "S-1005", "Tabela de Estabelecimentos (Matriz GO + Filial SC)", "2026-09", "Antes dos eventos periódicos", "aguardando_insumo", "Conferir CNAEs ativos e endereço Filial Itajaí-SC (Sala 223)."),
            ("esoc:d2:S-2200:E1", emp_id, ct_map.get("E1"), 3, "S-2200", "Cadastramento Inicial / Admissão E1 (Mariana — 16/09/2026)", "2026-09", "Até 15/09/2026 (anterior ao início)", "aguardando_insumo", "Sem recibo arquivado no onboarding; validar protocolo no portal (AUD-08)."),
            ("esoc:d2:S-2200:E2", emp_id, ct_map.get("E2"), 4, "S-2200", "Cadastramento Inicial / Admissão E2 (Rafael — 21/09/2026)", "2026-09", "Até 20/09/2026 (anterior ao início)", "aguardando_insumo", "Sem recibo arquivado no onboarding; validar protocolo no portal (AUD-08)."),
            ("esoc:d2:S-2220:E1", emp_id, ct_map.get("E1"), 5, "S-2220", "Monitoramento da Saúde do Trabalhador (ASO E1)", "2026-09", "Até 15/10/2026", "pendente", "BLOQUEADO: ASO admissional não realizado (PEND-01 / NR-7)."),
            ("esoc:d2:S-2220:E2", emp_id, ct_map.get("E2"), 6, "S-2220", "Monitoramento da Saúde do Trabalhador (ASO E2)", "2026-09", "Até 15/10/2026", "pendente", "BLOQUEADO: ASO admissional não realizado (PEND-01 / NR-7)."),
            ("esoc:d2:S-2240", emp_id, None, 7, "S-2240", "Condições Ambientais de Trabalho (Agentes Nocivos — SST)", "2026-09", "Até 15/10/2026", "pendente", "BLOQUEADO: requer PGR/DIR, PCMSO e LTCAT (PEND-07 / NR-1 / NR-4)."),
            ("esoc:d2:S-2300", emp_id, None, 8, "S-2300", "TSVE Início — Pró-Labore Sócios (Condicional)", "2026-09", "Até dia 15 do mês seguinte", "aguardando_insumo", "Condicional à definição de retirada de pró-labore (PEND-08)."),
            ("esoc:d2:S-1200", emp_id, None, 9, "S-1200", "Remuneração RGPS (Folha 09/2026 — Bruto R$ 2.833,33 / INSS R$ 212,68)", "2026-09", "Até 15/10/2026", "pronto_envio", "Rubricas conciliadas no motor; transmissão depende do e-CNPJ."),
            ("esoc:d2:S-1299", emp_id, None, 10, "S-1299", "Fechamento dos Eventos Periódicos -> DCTFWeb e FGTS Digital", "2026-09", "Até 15/10/2026 (Guias: 20/10)", "pronto_envio", "Gera DARF DCTFWeb R$ 212,68 e guia PIX FGTS Digital R$ 226,67."),
        ]
        execute_values(
            cur,
            """
            INSERT INTO erp.esocial_evento
                (chave, empresa_id, contrato_trabalho_id, ordem, codigo_evento, nome_evento,
                 competencia, prazo_legal, status_envio, numero_recibo, observacao,
                 origem_registro, status_validacao, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            [
                (ch, eid, ctid, ord_, cod, nom, comp, prz, st, None, obs,
                 "importado_rascunho_v2", "alerta_inconsistencia" if st == "pendente" else "pendente_revisao",
                 "Documento fisico != evento transmitido: nunca inventar numero de recibo sem protocolo real.")
                for ch, eid, ctid, ord_, cod, nom, comp, prz, st, obs in eventos_esocial
            ],
        )
        counts["erp.esocial_evento"] = len(eventos_esocial)
    conn.commit()
    return counts


def semear_auditoria_folha(conn: Any) -> dict[str, int]:
    """Semear Estacao 9 (Competencia 2026-09, Papeis de Trabalho PT-01..05 e Achados AUD-01..10)."""
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        emp_id = _obter_emp_id_d2(cur)
        cur.execute(
            """
            INSERT INTO erp.folha_competencia
                (chave, empresa_id, competencia, status_folha, vendas_liquidas_e2_centavos,
                 dias_mes_padrao, dias_trabalhados_e1, dias_trabalhados_e2, dias_uteis_comissao_e2,
                 domingos_feriados_e2, dias_uteis_vt_e1, dias_uteis_vt_e2, dias_uteis_vr_e1,
                 cenario_negocial, data_pagamento, origem_registro, status_validacao,
                 referencia_v1_original, apontamento_auditoria)
            VALUES ('folha:d2:2026-09', %s, '2026-09', 'aberta', 6000000,
                    30, 15, 10, 9, 1, 11, 9, 11, 'A_desconta', DATE '2026-10-07',
                    'importado_rascunho_v2', 'pendente_revisao',
                    'v1 somava apenas R$ 1.833,33 (sem comissão/DSR, com SF indevido e sem VR/Negocial/Provisões).',
                    'Executar recálculo no Motor da Folha para gerar rubricas, provisões (R$ 504) e lotes L1–L4 (R$ 4.238).')
            ON CONFLICT (chave) DO NOTHING
            """,
            (emp_id,),
        )
        counts["erp.folha_competencia"] = 1

        pts = [
            ("papel_trabalho", "PT-01", 1, "Planejamento, Avaliação de Risco e Materialidade (NBC TA 315/330)", "NBC TA 315 / NBC TA 330",
             "Asseguração razoável sobre 100% dos empregados (E1 e E2). Riscos Inerente e de Controle: ALTOS.", "Tolerância zero (R$ 0,01) aritmética + inspeção integral das fontes 2026.", None, None,
             "Planejamento executado com testes substantivos integrais em 100% da população.", "Auditoria PRISMA JRNA", "23/11/2026", "conforme", "pendente_revisao"),
            ("papel_trabalho", "PT-02", 2, "Auditoria Cadastral, Contratual e Documental (SST, Ponto, CNAE, VT/VR)", "CLT, CCT SRT00189/2025, NR-1/4/7",
             "Exame das fichas, contratos, Anexo I e Solicitação_JRNA.pdf p. 3.", "Verificação de CNAEs, jornada 1h48, ASO, PGR/PCMSO/LTCAT, ponto e termos VT/VR.", None, None,
             "Saneado nos textos (v2); permanecem abertos ASO (AUD-01), ponto/SST/pró-labore (AUD-09) e termos/recibos (AUD-08).", "Diretoria + DP", "02/10 a 15/10/2026", "aberto_cliente", "alerta_inconsistencia"),
            ("papel_trabalho", "PT-03", 3, "Recálculo Independente da Folha (Confronto Triplo: v1 × Auditoria × Motor)", "Port. MPS/MF 13/2026; Lei 15.270/2025; CCT",
             "Folha v1 totalizava R$ 1.833,33 brutos contra R$ 2.833,33 recalculados (+R$ 1.000,00 E2; -R$ 62,04 SF).", "Recálculo de 100% das rubricas, líquido Cenários A/B, FGTS e provisões.", 183333, 283333,
             "Recálculo auditado bate 100% com planilha (dif. R$ 0,00) — requer validação comercial de vendas (DOC-13).", "DP PRISMA JRNA", "05/10/2026", "saneado_v2", "pendente_revisao"),
            ("papel_trabalho", "PT-04", 4, "Conferência de Encargos, eSocial, DCTFWeb e FGTS Digital", "LC 123/2006; Lei 8.036/1990; MOS eSocial S-1.3",
             "DCTFWeb = R$ 212,68 (INSS retido); FGTS Digital = R$ 226,67; CPP 20% = R$ 0,00 no DAS.", "Cruzamento integral S-1200/S-1299 x guias x partidas dobradas.", 14667, 22667,
             "Valores das guias conciliados (dif. R$ 0,00); eventos S-2220 e S-2240 seguem bloqueados por falta de ASO/SST.", "DP PRISMA + Clínica SST", "15/10/2026", "aberto_cliente", "pendente_revisao"),
            ("papel_trabalho", "PT-05", 5, "Quadro Consolidado de Achados, Evidências e Plano de Saneamento (AUD-01..10)", "NBC TA 330 / ITG 1000",
             "Consolidação dos 10 achados materiais e formais entre a entrega v1 e a competência 09/2026.", "Classificação de risco, impacto financeiro, responsável e prazo de saneamento.", None, None,
             "6 achados saneados na revisão técnica e 4 dependentes de ação documental/clínica da administração.", "PRISMA JRNA + Diretoria", "02/10 a 20/10/2026", "aberto_cliente", "pendente_revisao"),
        ]
        achados = [
            ("achado", "AUD-01", 101, "Ausência de ASO Admissional (NR-7) para E1 e E2", "CLT art. 168 / art. 201; NR-7",
             "Doc. 05 PEND-01 e relatos de onboarding (exames não realizados pré-admissão).", "Risco Crítico: multa administrativa e bloqueio do eSocial S-2220.", None, None,
             "Realizar exames clínicos imediatos e transmitir S-2220.", "Diretoria Rota Sul + Clínica SST", "02/10/2026", "aberto_cliente", "alerta_inconsistencia"),
            ("achado", "AUD-02", 102, "Omissão de Comissão (R$ 900,00) e DSR (R$ 100,00) do E2 na v1", "CLT art. 457; Lei 3.207/57; Súmula 27 TST",
             "Folha v1 ignorava R$ 60.000 de vendas líquidas e DSR (Solicitação_JRNA Resp. 4).", "Risco Crítico: omissão de R$ 1.000,00 brutos (+R$ 75,18 INSS e +R$ 80,00 FGTS).", 0, 100000,
             "Recalculado na folha e memória aberta; validar relatório comercial assinado (DOC-13).", "DP PRISMA + Comercial", "05/10/2026", "saneado_v2", "pendente_revisao"),
            ("achado", "AUD-03", 103, "Concessão indevida de Salário-Família ao E1 (R$ 62,04) na v1", "Dec. 3.048/99 art. 82; Port. MPS/MF 13/2026",
             "Folha v1 pagou R$ 62,04 apesar do salário contratual de R$ 2.400,00 (> teto R$ 1.980,38).", "Risco Alto: glosa na DCTFWeb / compensação indevida de INSS.", 6204, 0,
             "Cota zerada por fórmula dinâmica com tabela 2026 (cota R$ 67,54 / teto R$ 1.980,38).", "DP PRISMA JRNA", "Concluído", "saneado_v2", "pendente_revisao"),
            ("achado", "AUD-04", 104, "Omissão de VR (R$ 330), Negocial (R$ 94,35), Provisões (R$ 504) e Contabilização na v1", "PAT; CCT Cl. 11ª; Lei 4.090/62; NBC TG 33",
             "Folha e recibos v1 omitiam benefícios, contribuição sindical e partidas dobradas.", "Risco Alto: distorção de R$ 928,35 no passivo e resultado de setembro/2026.", 0, 92835,
             "Incluídos no motor e partidas dobradas (L1–L4 = R$ 4.238,00; conciliação = R$ 0,00).", "Contábil / DP PRISMA", "Concluído", "saneado_v2", "pendente_revisao"),
            ("achado", "AUD-05", 105, "Piso salarial sem fonte (R$ 1.580,00) citado no relatório técnico v1", "CCT SRT00189/2025 + Aditivo 2026/2027 Cl. 3ª",
             "Relatório v1 citava R$ 1.580,00 sem norma sindical oficial.", "Risco Médio: erro técnico de fundamentação normativa (salários reais são maiores).", 158000, 172225,
             "Substituído por pisos oficiais Goiânia 2026: R$ 1.722,25 (Adm.) e R$ 1.863,00 (Vendedor).", "Auditoria PRISMA", "Concluído", "saneado_v2", "pendente_revisao"),
            ("achado", "AUD-06", 106, "Divergência de CNAE (4530-7/01) + risco de exclusão do Simples (4541-2/01)", "Anexo I Cl. 2ª/3ª; LC 123/2006 art. 17, VIII",
             "Fichas v1 traziam 4530-7/01 inexistente no Anexo I; objeto mantém 4541-2/01 (motos) com importação.", "Risco Crítico Tributário: exclusão do Simples eleva custo mensal da folha em +R$ 917,40 (+22,22%).", 412800, 504540,
             "CNAEs DP corrigidos para 4530-7/02 e 05; pautada exclusão de 4541-2/01 na 3ª Alteração.", "Fiscal PRISMA + Sócios", "10/10/2026", "saneado_v2", "alerta_inconsistencia"),
            ("achado", "AUD-07", 107, "Intervalo E1 adulterado (1h12 + sábados), 6 [cite] e estorno ilegal no E2", "CLT art. 71; Lei 3.207/1957 art. 7º",
             "Contratos de experiência v1 corrigidos frente ao texto literal do Caso 02 (1h48).", "Risco Médio: 3h semanais descobertas (41h reais x 44h contratuais) e cláusula nula de estorno.", None, None,
             "Removidos [cite], saneado estorno (só insolvência), mantido 1h48 e aberta PEND-04.", "DP PRISMA + Diretoria", "05/10/2026", "saneado_v2", "alerta_inconsistencia"),
            ("achado", "AUD-08", 108, "Ausência de recibos do eSocial (S-2200) e de termos VT/VR assinados", "MOS eSocial S-1.3; Lei 7.418/1985",
             "Doc. 05 DOC-12 e Doc. 06: sem protocolos eSocial arquivados nem termos assinados.", "Risco Alto: fragilidade probatória (sem inventar números de recibo).", None, None,
             "Coletar termos VT/VR assinados (sem fornecer modelo de oposição) e arquivar recibos eSocial.", "Diretoria + DP PRISMA", "05/10/2026", "aberto_cliente", "alerta_inconsistencia"),
            ("achado", "AUD-09", 109, "Ausência de PGR/PCMSO/LTCAT (S-2240), ponto formal e definição de pró-labore", "NR-1, NR-4, CLT art. 74; Lei 4.357/64 art. 32",
             "Solicitação_JRNA Resp. 4 (papel/celular) e ausência de SST/pró-labore (PEND-07/08).", "Risco Alto: multa SST, Súmula 338 TST (horas extras) e reclassificação INSS sócios.", None, None,
             "Contratar clínica SST, implantar ponto idôneo e formalizar pró-labore (mantendo bloqueio lucros).", "Diretoria Rota Sul", "15/10/2026", "aberto_cliente", "alerta_inconsistencia"),
            ("achado", "AUD-10", 110, "Critério de quantidade de Vale-Transporte (4 vs. 2 passagens/dia — Sensibilidade)", "Lei 7.418/1985; Caso 02 pág. 3",
             "Premissa formal 4/dia (subsídio R$ 234,00) vs leitura literal 2/dia (subsídio R$ 62,00).", "Risco Baixo: diferença de R$ 172,00 no subsídio empresa; R$ 0,00 no desconto 6% dos empregados.", 6200, 23400,
             "Sensibilidade explícita documentada em docs. 11/12/14; confirmar trajeto no Termo VT (DOC-12).", "DP PRISMA + E1/E2", "05/10/2026", "conforme", "pendente_revisao"),
        ]
        all_aud = pts + achados
        execute_values(
            cur,
            """
            INSERT INTO erp.auditoria_folha
                (chave, empresa_id, tipo_registro, codigo, ordem, titulo, norma_referencia,
                 objetivo_ou_evidencia, procedimento_ou_risco, valor_v1_centavos, valor_recalculado_centavos,
                 conclusao_ou_correcao, responsavel, prazo_texto, situacao_achado,
                 origem_registro, status_validacao, apontamento_auditoria)
            VALUES %s ON CONFLICT (chave) DO NOTHING
            """,
            [
                (f"aud:d2:{cod}", emp_id, tipo, cod, ord_, tit, norm, obj, proc, v1, vrec, concl, resp, prz, sit,
                 "importado_rascunho_v2", st,
                 "Achado ou papel de trabalho importado para revisão da contadora.")
                for tipo, cod, ord_, tit, norm, obj, proc, v1, vrec, concl, resp, prz, sit, st in all_aud
            ],
        )
        counts["erp.auditoria_folha"] = len(all_aud)
    conn.commit()
    return counts


def importar_dossie2_completo(editaveis_dir: Path = DEFAULT_D2_EDITAVEIS) -> dict[str, Any]:
    """Executa toda a carga inicial idempotente do Dossie 2 em PostgreSQL."""
    out: dict[str, Any] = {}
    with conectar_pg() as conn:
        out["etapa0"] = semear_etapa0(conn)
        out["secoes"] = importar_secoes_dossie2(conn, editaveis_dir)
        out["onboarding"] = semear_onboarding(conn)
        out["dp"] = semear_dp(conn)
        out["auditoria_folha"] = semear_auditoria_folha(conn)
    return out


if __name__ == "__main__":
    print("Importacao Dossie 2:", json.dumps(importar_dossie2_completo(), ensure_ascii=False, indent=2))
