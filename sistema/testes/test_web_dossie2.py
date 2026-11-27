"""Testes automatizados end-to-end e testes puros (sem banco) do Dossie 2 (Rota Sul Importadora — Set/2026)."""

from __future__ import annotations

from datetime import datetime
import io
from pathlib import Path
import re
from typing import Any

import openpyxl
import pytest

from sistema.erp.motor_folha import (
    detectar_divergencia_contratos_d2,
    detectar_recalculo_divergente_d2,
    detectar_residuos_texto_d2,
    detectar_salario_abaixo_piso_d2,
    impacto_exclusao_simples,
    recalcular_folha_d2,
    recalcular_folha_independente_dados,
)
from sistema.pg.db import ENV_PATH, conectar_pg, obter_database_url
from sistema.web import ajuda as ajuda_mod
from sistema.web import texto
from sistema.web.app import create_app
from sistema.web.emissor_dossie2 import DOCUMENTOS, _marcadores_d2, html_documento
from sistema.web.planilha_dossie2 import _montar_workbook_d2


def _pg_disponivel() -> bool:
    try:
        obter_database_url()
        conectar_pg().close()
        return True
    except Exception:
        return False


def _fixture_dados_d2() -> dict[str, Any]:
    """Fixture pura no formato de carregar_dados_dossie2() com os valores do gabarito (09/2026)."""
    return {
        "emitido_em": datetime(2026, 11, 26, 16, 0, 0),
        "empresa": {
            "id": 1,
            "chave": "emp:rota_sul_d2",
            "pessoa_id": 1,
            "nome_curto": "Rota Sul (Caso D2)",
            "razao_social": "Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda.",
            "status_validacao": "pendente_revisao",
        },
        "estabelecimentos": [
            {
                "id": 1,
                "tipo": "matriz",
                "cnpj": "11.222.333/0001-81",
                "uf": "GO",
                "municipio": "Goiânia",
                "endereco": "Rua das Mangueiras, Quadra 40, Lote 11, nº 215, Setor Campinas, Goiânia-GO, CEP 74.515-000",
                "status_validacao": "pendente_revisao",
            },
            {
                "id": 2,
                "tipo": "filial",
                "cnpj": "11.222.333/0002-62",
                "uf": "SC",
                "municipio": "Itajaí",
                "endereco": "BR-101, nº 15.000, Sala 223 (Anexo I: Sala 223 A 32), Bairro Canhanduba, Itajaí-SC, CEP 88.313-000 (NIRE 42900000012)",
                "status_validacao": "pendente_revisao",
            },
        ],
        "contratos": [
            {
                "id": 1,
                "codigo_empregado": "E1",
                "nome_empregado": "Mariana Alves Costa",
                "cpf_ficticio": "123.456.789-10",
                "cargo": "Auxiliar Administrativo",
                "departamento": "administrativo",
                "cbo": "4110-05",
                "data_admissao": "2026-09-16",
                "experiencia_dias_1": 45,
                "experiencia_dias_2": 45,
                "salario_base_centavos": 240_000,
                "piso_cct_centavos": 172_225,
                "comissao_pct_micro": 0,
                "jornada_semanal_horas": 44,
                "jornada_descricao": "Segunda a sexta, 08h às 18h (1h48 de intervalo)",
                "intervalo_minutos": 108,
                "cct_referencia": "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Adit. 2026/2027)",
                "vt_optante": True,
                "vt_passagens_dia": 4,
                "vt_tarifa_centavos": 430,
                "vr_elegivel": True,
                "vr_valor_dia_centavos": 3_000,
                "aso_status": "pendente_critico",
                "aso_observacao": "ASO admissional pendente de coleta física (bloqueia S-2220)",
                "qtd_dependentes_ir": 1,
                "qtd_dependentes_sf": 1,
                "dependentes_json": [{"nome": "Lucas Alves Costa", "parentesco": "Filho", "cpf": "456.789.123-64"}],
                "docs_admissionais_json": ["RG/CPF (fictício)", "Título/Residência", "Certidão/CPF/Vacina/Escola filho"],
                "status_validacao": "pendente_revisao",
            },
            {
                "id": 2,
                "codigo_empregado": "E2",
                "nome_empregado": "Rafael Souza Lima",
                "cpf_ficticio": "987.654.321-99",
                "cargo": "Vendedor",
                "departamento": "comercial",
                "cbo": "5211-10",
                "data_admissao": "2026-09-21",
                "experiencia_dias_1": 30,
                "experiencia_dias_2": 60,
                "salario_base_centavos": 190_000,
                "piso_cct_centavos": 186_300,
                "comissao_pct_micro": 15_000,
                "jornada_semanal_horas": 44,
                "jornada_descricao": "Segunda a sexta 08h–18h (2h intervalo) e sábado 08h–12h",
                "intervalo_minutos": 120,
                "cct_referencia": "CCT SECEG x SINDILOJAS-GO (SRT00189/2025 + Adit. 2026/2027)",
                "vt_optante": True,
                "vt_passagens_dia": 4,
                "vt_tarifa_centavos": 430,
                "vr_elegivel": False,
                "vr_valor_dia_centavos": 0,
                "aso_status": "pendente_critico",
                "aso_observacao": "ASO admissional pendente de coleta física (bloqueia S-2220)",
                "qtd_dependentes_ir": 0,
                "qtd_dependentes_sf": 0,
                "dependentes_json": [],
                "docs_admissionais_json": ["RG/CPF (fictício)", "Título/Residência"],
                "status_validacao": "pendente_revisao",
            },
        ],
        "parametros": [
            {"codigo": "INSS-F1", "categoria": "inss", "ordem": 1, "descricao": "Faixa 1 INSS", "limite_centavos": 162_100, "aliquota_micro": 75_000, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "Portaria MPS/MF nº 13/2026", "link_oficial": "https://www.gov.br/previdencia", "data_consulta": "2026-09-20", "status_validacao": "pendente_revisao"},
            {"codigo": "INSS-F2", "categoria": "inss", "ordem": 2, "descricao": "Faixa 2 INSS", "limite_centavos": 290_284, "aliquota_micro": 90_000, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "Portaria MPS/MF nº 13/2026", "link_oficial": "https://www.gov.br/previdencia", "data_consulta": "2026-09-20", "status_validacao": "pendente_revisao"},
            {"codigo": "INSS-F3", "categoria": "inss", "ordem": 3, "descricao": "Faixa 3 INSS", "limite_centavos": 435_427, "aliquota_micro": 120_000, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "Portaria MPS/MF nº 13/2026", "link_oficial": "https://www.gov.br/previdencia", "data_consulta": "2026-09-20", "status_validacao": "pendente_revisao"},
            {"codigo": "INSS-F4", "categoria": "inss", "ordem": 4, "descricao": "Faixa 4 INSS", "limite_centavos": 847_555, "aliquota_micro": 140_000, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "Portaria MPS/MF nº 13/2026", "link_oficial": "https://www.gov.br/previdencia", "data_consulta": "2026-09-20", "status_validacao": "pendente_revisao"},
            {"codigo": "IRRF-SIMPLIF", "categoria": "irrf", "ordem": 1, "descricao": "Desconto simplificado mensal", "limite_centavos": None, "aliquota_micro": None, "deducao_centavos": None, "valor_centavos": 60_720, "norma_citada": "Lei nº 14.848/2024", "link_oficial": "https://www.planalto.gov.br", "data_consulta": "2026-09-21", "status_validacao": "pendente_revisao"},
            {"codigo": "IRRF-DEP", "categoria": "irrf", "ordem": 2, "descricao": "Dedução por dependente", "limite_centavos": None, "aliquota_micro": None, "deducao_centavos": None, "valor_centavos": 18_959, "norma_citada": "RFB 2026", "link_oficial": "https://www.gov.br/receitafederal", "data_consulta": "2026-09-21", "status_validacao": "pendente_revisao"},
            {"codigo": "IRRF-F1", "categoria": "irrf", "ordem": 3, "descricao": "Faixa isenta IRRF", "limite_centavos": 242_880, "aliquota_micro": 0, "deducao_centavos": 0, "valor_centavos": None, "norma_citada": "RFB 2026", "link_oficial": "https://www.gov.br/receitafederal", "data_consulta": "2026-09-21", "status_validacao": "pendente_revisao"},
            {"codigo": "RED-ISENTO", "categoria": "reducao_irrf_2026", "ordem": 1, "descricao": "Redução total até R$ 5.000,00", "limite_centavos": 500_000, "aliquota_micro": None, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "Lei nº 15.270/2025", "link_oficial": "https://www.planalto.gov.br", "data_consulta": "2026-09-22", "status_validacao": "pendente_revisao"},
            {"codigo": "SF-2026", "categoria": "salario_familia", "ordem": 1, "descricao": "Cota Salário-Família 2026", "limite_centavos": 198_038, "aliquota_micro": None, "deducao_centavos": None, "valor_centavos": 6_754, "norma_citada": "Portaria MPS/MF nº 13/2026", "link_oficial": "https://www.gov.br/previdencia", "data_consulta": "2026-09-20", "status_validacao": "pendente_revisao"},
            {"codigo": "FGTS-8", "categoria": "fgts", "ordem": 1, "descricao": "Alíquota mensal FGTS", "limite_centavos": None, "aliquota_micro": 80_000, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "Lei nº 8.036/1990", "link_oficial": "https://www.planalto.gov.br", "data_consulta": "2026-09-20", "status_validacao": "pendente_revisao"},
            {"codigo": "CCT-VT-MISTO", "categoria": "cct_clausula", "ordem": 1, "descricao": "Teto base salário misto VT", "limite_centavos": 225_750, "aliquota_micro": None, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "CCT SRT00189/2025 Cl. 6ª", "link_oficial": None, "data_consulta": "2026-09-23", "status_validacao": "pendente_revisao"},
            {"codigo": "CCT-NEGOCIAL", "categoria": "cct_clausula", "ordem": 2, "descricao": "Contribuição Negocial CCT", "limite_centavos": 14_800, "aliquota_micro": 33_300, "deducao_centavos": None, "valor_centavos": None, "norma_citada": "CCT Adit. 2026/2027 Cl. 11ª", "link_oficial": None, "data_consulta": "2026-09-23", "status_validacao": "pendente_revisao"},
        ],
        "requisitos": [
            {"codigo": "D2-P1", "ordem": 1, "descricao": "Diagnóstico Societário e Análise da 2ª Alteração", "documentos_json": ["d2_00_indice", "d2_01_diagnostico"]},
            {"codigo": "D2-P3", "ordem": 3, "descricao": "Comunicação de Onboarding, Checklist DOC-01..13, Q1..Q9 e PEND-01..08", "documentos_json": ["d2_05_onboarding"]},
            {"codigo": "D2-P4", "ordem": 4, "descricao": "Prontuários E1 e E2, eSocial e Fichas", "documentos_json": ["d2_06_prontuario", "d2_07_ficha_e1", "d2_09_ficha_e2"]},
            {"codigo": "D2-P8", "ordem": 8, "descricao": "Premissas Adotadas PR-01..18", "documentos_json": ["d2_14_premissas"]},
            {"codigo": "D2-P9", "ordem": 9, "descricao": "Declaração de Uso de IA e LGPD", "documentos_json": ["d2_15_ia"]},
        ],
        "diligencias": [
            {"id": 1, "tipo": "documento", "codigo": "DOC-01", "ator": "cliente", "tema": "Societário", "enunciado": "2ª Alteração Contratual consolidada", "resposta_literal": None, "fonte_evidencia": "Anexo I", "data_interacao": "2026-09-14", "responsavel": "Sócios Rota Sul", "prazo_texto": "Imediato", "risco": "alto", "status_item": "concluido", "status_validacao": "homologado_contadora"},
            {"id": 2, "tipo": "pergunta", "codigo": "Q1", "ator": "cliente", "tema": "Capital", "enunciado": "Houve integralização dos R$ 500 mil?", "resposta_literal": "Não houve integralização até o momento.", "fonte_evidencia": "Solicitação_JRNA.pdf", "data_interacao": "2026-09-18", "responsavel": "Helena Duarte", "prazo_texto": "Respondido", "risco": "critico", "status_item": "concluido", "status_validacao": "pendente_revisao"},
            {"id": 3, "tipo": "pendencia", "codigo": "PEND-01", "ator": "cliente", "tema": "SST / eSocial", "enunciado": "Coleta dos ASOs admissionais E1 e E2", "resposta_literal": "Agendar exame clínico NR-7", "fonte_evidencia": "Onboarding", "data_interacao": None, "responsavel": "Diretoria Rota Sul", "prazo_texto": "05/10/2026", "risco": "critico", "status_item": "pendente_critico", "status_validacao": "alerta_inconsistencia"},
        ],
        "esocial": [
            {"id": 1, "codigo_evento": "S-2200", "codigo_empregado": "E1", "nome_evento": "Admissão E1 (Mariana)", "competencia": "2026-09", "prazo_legal": "Até 15/09/2026", "status_envio": "aguardando_insumo", "numero_recibo": None, "status_validacao": "pendente_revisao"},
            {"id": 2, "codigo_evento": "S-2220", "codigo_empregado": "E1", "nome_evento": "ASO Admissional E1", "competencia": "2026-09", "prazo_legal": "Até 15/10/2026", "status_envio": "pendente", "numero_recibo": None, "status_validacao": "alerta_inconsistencia"},
        ],
        "consultas": [
            {"id": 1, "numero_questao": 1, "enunciado": "PR-01 — Enquadramento Simples Nacional", "resposta_autoral": "Anexo I sem CPP em folha.", "decisao_impactada": "Docs. 11, 12, 13", "norma_citada": "LC 123/2006", "link_oficial": "https://www.planalto.gov.br", "data_acesso": "2026-09-20", "responsavel_decisao": "RT PRISMA", "prazo_decisao": "30/09/2026", "impacto_se_alterada": "Altera encargos da folha", "status_validacao": "pendente_revisao"},
        ],
        "diario_ia": [
            {"id": 1, "entregavel": "Doc. 05", "ferramenta": "Antigravity (Gemini 4)", "finalidade": "Organização de checklist e respostas literais", "prompt_resumo": "Tabular DOC-01..13 e Q1..Q9 sem inventar evidência.", "fonte_oficial": "Estudo de Caso 02 e respostas da diretoria", "revisao_humana": "Conferido item a item pela contadora.", "status_validacao": "pendente_revisao"},
        ],
        "escritorio": {
            "nome_curto": "PRISMA JRNA",
            "nome_canonico": "Prisma JRNA Auditoria e Contabilidade Ltda.",
            "cnpj": "48.123.456/0001-90",
            "registro_crc": "CRC-DF 004.821/O-2",
            "rt_nome": "Nathalia Peres Araujo",
            "rt_crc": "CRC-DF 025.431/O-7",
            "sede": "Asa Sul, Brasília-DF",
        },
        "socios": [
            {"pessoa_id": 7, "nome_canonico": "Helena Aparecida Mendes Duarte", "papel": "socio_administrador", "quotas": 750_000, "valor_centavos": 75_000_000, "percentual_micro": 50_000_000, "status_validacao": "acervo_referencia"},
            {"pessoa_id": 8, "nome_canonico": "Bruno Mendes Duarte", "papel": "socio_administrador", "quotas": 750_000, "valor_centavos": 75_000_000, "percentual_micro": 50_000_000, "status_validacao": "acervo_referencia"},
        ],
        "identificadores": [
            {"pessoa_id": 1, "tipo_id": "CNPJ", "valor": "11.222.333/0001-81"},
            {"pessoa_id": 1, "tipo_id": "NIRE", "valor": "52900000015"},
        ],
        "enquadramento": {"porte": "EPP", "regime_tributario": "Simples_Anexo_I"},
        "fatos_capital": [
            {"atributo": "capital_social", "valor_centavos": 100_000_000, "vigente_ate": "2026-09-13"},
            {"atributo": "capital_social", "valor_centavos": 150_000_000, "vigente_ate": None},
            {"atributo": "capital_integralizado", "valor_centavos": 100_000_000, "vigente_ate": None},
        ],
        "clausulas_d2": [
            {
                "id": 1, "numero_clausula": "Cl. 2ª Alteração / Cl. 3ª", "titulo": "CNAE 4541-2/01 no Simples",
                "regra_texto": "Importação de motocicletas veda Simples Nacional.",
                "risco_tipo": "material", "risco_nivel": "critico",
                "fundamento_legal": "LC 123/2006, art. 17, VIII",
                "providencia": "Excluir 4541-2/01 na 3ª Alteração Contratual.",
                "responsavel": "Sócios + Advogado", "prazo_texto": "10/10/2026",
                "apontamento_auditoria": "Excluir CNAE impeditivo.", "status_validacao": "alerta_inconsistencia",
            },
        ],
        "contratos_servico": [
            {
                "id": 1, "codigo_documento": "proposta", "titulo": "Proposta de Honorários e BPO",
                "honorario_mensal_centavos": 400_000, "tem_decimo_terceiro": True,
                "valor_hora_centavos": 12_500, "horas_mes_estimadas": 32,
                "vigencia_inicio": "2026-09-14", "foro": "Goiânia-GO",
                "escopo_resumo": "BPO Contábil, Fiscal e DP (Matriz GO + Filial SC).",
                "memoria_horas_json": [{"frente": "Setup Fee (Implantação)", "horas": 16, "valor_hora": 999}, {"frente": "Mensal Matriz + Filial", "horas": 32, "valor_hora": 125}],
                "conteudo_md": "Proposta válida por 15 dias.", "status_validacao": "pendente_revisao",
            },
            {
                "id": 2, "codigo_documento": "contrato", "titulo": "Contrato de Prestação de Serviços Contábeis",
                "honorario_mensal_centavos": 400_000, "tem_decimo_terceiro": True,
                "valor_hora_centavos": 12_500, "horas_mes_estimadas": 32,
                "vigencia_inicio": "2026-09-01", "foro": "Goiânia-GO",
                "escopo_resumo": "Prestação contínua a partir de 09/2026.",
                "memoria_horas_json": [], "conteudo_md": "Contrato completo.", "status_validacao": "pendente_revisao",
            },
            {
                "id": 3, "codigo_documento": "termo_rt", "titulo": "Termo de Responsabilidade Técnica",
                "honorario_mensal_centavos": 400_000, "tem_decimo_terceiro": True,
                "valor_hora_centavos": 12_500, "horas_mes_estimadas": 32,
                "vigencia_inicio": "2026-09-01", "foro": "Goiânia-GO",
                "escopo_resumo": "Res. CFC nº 1.708/2023.",
                "memoria_horas_json": [], "conteudo_md": "Termo RT.", "status_validacao": "pendente_revisao",
            },
        ],
        "auditoria": [
            {
                "id": 1, "tipo_registro": "papel_trabalho", "codigo": "PT-01",
                "titulo": "Planejamento de Auditoria Trabalhista", "norma_referencia": "NBC TA 300 / 315",
                "objetivo_ou_evidencia": "100% da folha 09/2026 (E1 e E2)", "procedimento_ou_risco": "Recálculo integral e conferência documental",
                "conclusao_ou_correcao": "Materialidade total aplicada.", "responsavel": "Auditoria PRISMA", "prazo_texto": "30/09/2026",
                "situacao_achado": "conforme", "status_validacao": "pendente_revisao",
            },
            {
                "id": 2, "tipo_registro": "achado", "codigo": "AUD-03",
                "titulo": "Salário-Família pago indevidamente na V1", "norma_referencia": "Portaria MPS/MF nº 13/2026",
                "objetivo_ou_evidencia": "Salário contratual E1 = R$ 2.400,00 > teto R$ 1.980,38",
                "procedimento_ou_risco": "Alto risco trabalhista/previdenciário",
                "valor_v1_centavos": 6_204, "valor_recalculado_centavos": 0,
                "conclusao_ou_correcao": "Estornar pagamento indevido na folha recalculada.",
                "responsavel": "DP PRISMA", "prazo_texto": "Concluído",
                "situacao_achado": "saneado_v2", "status_validacao": "homologado_contadora",
            },
        ],
        "comp": {
            "id": 1,
            "competencia": "2026-09",
            "dias_mes_padrao": 30,
            "vendas_liquidas_e2_centavos": 6_000_000,
            "dias_trabalhados_e1": 15,
            "dias_trabalhados_e2": 10,
            "dias_uteis_comissao_e2": 9,
            "domingos_feriados_e2": 1,
            "dias_uteis_vt_e1": 11,
            "dias_uteis_vt_e2": 9,
            "dias_uteis_vr_e1": 11,
            "cenario_negocial": "A_desconta",
            "bruto_total_centavos": 283_333,
            "inss_total_centavos": 21_268,
            "fgts_total_centavos": 22_667,
            "liquido_total_centavos": 241_630,
            "provisoes_total_centavos": 50_400,
            "custo_total_centavos": 412_800,
            "status_validacao": "pendente_revisao",
        },
        "itens": [
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "SAL-PROP", "nome_rubrica": "Salário Proporcional (15/30)", "tipo_rubrica": "provento", "referencia_texto": "15 dias", "base_centavos": 240_000, "valor_centavos": 120_000},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "SAL-FAMILIA", "nome_rubrica": "Salário-Família", "tipo_rubrica": "informativo", "referencia_texto": "Inelegível", "base_centavos": 240_000, "valor_centavos": 0},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "INSS-RET", "nome_rubrica": "INSS Retido", "tipo_rubrica": "desconto", "referencia_texto": "Progressivo", "base_centavos": 120_000, "valor_centavos": 9_000},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "IRRF", "nome_rubrica": "IRRF 2026", "tipo_rubrica": "desconto", "referencia_texto": "Isento", "base_centavos": 59_280, "valor_centavos": 0},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "VT-DESC", "nome_rubrica": "Desconto VT (6%)", "tipo_rubrica": "desconto", "referencia_texto": "6%", "base_centavos": 120_000, "valor_centavos": 7_200},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "VT-SUBS", "nome_rubrica": "Subsídio VT Empresa", "tipo_rubrica": "informativo", "referencia_texto": "11d x 4/d", "base_centavos": 18_920, "valor_centavos": 11_720},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "VR-PAT", "nome_rubrica": "Vale-Refeição (PAT)", "tipo_rubrica": "informativo", "referencia_texto": "11d x R$ 30,00", "base_centavos": 33_000, "valor_centavos": 33_000},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "NEGOCIAL", "nome_rubrica": "Contribuição Negocial CCT", "tipo_rubrica": "desconto", "referencia_texto": "3,33%", "base_centavos": 120_000, "valor_centavos": 3_996},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "FGTS-8", "nome_rubrica": "FGTS 8%", "tipo_rubrica": "encargo", "referencia_texto": "8,00%", "base_centavos": 120_000, "valor_centavos": 9_600},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "PROV-13", "nome_rubrica": "Provisão 13º Salário", "tipo_rubrica": "provisao", "referencia_texto": "1/12 avo", "base_centavos": 240_000, "valor_centavos": 20_000},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "PROV-FER", "nome_rubrica": "Provisão Férias (1/12 avo)", "tipo_rubrica": "provisao", "referencia_texto": "1/12 avo", "base_centavos": 240_000, "valor_centavos": 20_000},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "PROV-1/3", "nome_rubrica": "Provisão 1/3 Constitucional de Férias", "tipo_rubrica": "provisao", "referencia_texto": "1/12 avo", "base_centavos": 20_000, "valor_centavos": 6_667},
            {"codigo_empregado": "E1", "nome_empregado": "Mariana Alves Costa", "codigo_rubrica": "PROV-FGTS", "nome_rubrica": "FGTS s/ Provisões", "tipo_rubrica": "provisao", "referencia_texto": "8%", "base_centavos": 46_667, "valor_centavos": 3_733},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "SAL-PROP", "nome_rubrica": "Salário Fixo Proporcional (10/30)", "tipo_rubrica": "provento", "referencia_texto": "10 dias", "base_centavos": 190_000, "valor_centavos": 63_333},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "COMISSAO", "nome_rubrica": "Comissão sobre Vendas (1,5%)", "tipo_rubrica": "provento", "referencia_texto": "1,50%", "base_centavos": 6_000_000, "valor_centavos": 90_000},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "DSR-COM", "nome_rubrica": "DSR sobre Comissões", "tipo_rubrica": "provento", "referencia_texto": "1/9", "base_centavos": 90_000, "valor_centavos": 10_000},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "SAL-FAMILIA", "nome_rubrica": "Salário-Família", "tipo_rubrica": "informativo", "referencia_texto": "0 dep.", "base_centavos": 190_000, "valor_centavos": 0},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "INSS-RET", "nome_rubrica": "INSS Retido", "tipo_rubrica": "desconto", "referencia_texto": "Progressivo", "base_centavos": 163_333, "valor_centavos": 12_268},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "IRRF", "nome_rubrica": "IRRF 2026", "tipo_rubrica": "desconto", "referencia_texto": "Isento", "base_centavos": 102_613, "valor_centavos": 0},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "VT-DESC", "nome_rubrica": "Desconto VT (6%)", "tipo_rubrica": "desconto", "referencia_texto": "6%", "base_centavos": 63_333, "valor_centavos": 3_800},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "VT-SUBS", "nome_rubrica": "Subsídio VT Empresa", "tipo_rubrica": "informativo", "referencia_texto": "9d x 4/d", "base_centavos": 15_480, "valor_centavos": 11_680},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "NEGOCIAL", "nome_rubrica": "Contribuição Negocial CCT", "tipo_rubrica": "desconto", "referencia_texto": "3,33%", "base_centavos": 163_333, "valor_centavos": 5_439},
            {"codigo_empregado": "E2", "nome_empregado": "Rafael Souza Lima", "codigo_rubrica": "FGTS-8", "nome_rubrica": "FGTS 8%", "tipo_rubrica": "encargo", "referencia_texto": "8,00%", "base_centavos": 163_333, "valor_centavos": 13_067},
        ],
        "partidas": [
            {"numero_lancamento": 901, "historico": "L1 — Folha", "tag_ref": "folha_l1", "dc": "D", "conta_codigo": "4.1.1.01", "conta_nome": "Salários E1", "valor_centavos": 120_000},
            {"numero_lancamento": 901, "historico": "L1 — Folha", "tag_ref": "folha_l1", "dc": "D", "conta_codigo": "4.2.1.01", "conta_nome": "Salários E2", "valor_centavos": 163_333},
            {"numero_lancamento": 901, "historico": "L1 — Folha", "tag_ref": "folha_l1", "dc": "C", "conta_codigo": "2.1.2.01", "conta_nome": "Salários a Pagar", "valor_centavos": 241_630},
            {"numero_lancamento": 901, "historico": "L1 — Folha", "tag_ref": "folha_l1", "dc": "C", "conta_codigo": "2.1.2.02", "conta_nome": "INSS a Recolher", "valor_centavos": 21_268},
            {"numero_lancamento": 901, "historico": "L1 — Folha", "tag_ref": "folha_l1", "dc": "C", "conta_codigo": "2.1.2.05", "conta_nome": "Negocial a Recolher", "valor_centavos": 9_435},
            {"numero_lancamento": 901, "historico": "L1 — Folha", "tag_ref": "folha_l1", "dc": "C", "conta_codigo": "4.1.1.05", "conta_nome": "Recup. VT", "valor_centavos": 11_000},
            {"numero_lancamento": 902, "historico": "L2 — FGTS", "tag_ref": "folha_l2", "dc": "D", "conta_codigo": "4.1.1.03", "conta_nome": "FGTS", "valor_centavos": 22_667},
            {"numero_lancamento": 902, "historico": "L2 — FGTS", "tag_ref": "folha_l2", "dc": "C", "conta_codigo": "2.1.2.03", "conta_nome": "FGTS a Recolher", "valor_centavos": 22_667},
            {"numero_lancamento": 903, "historico": "L3 — Benefícios", "tag_ref": "folha_l3", "dc": "D", "conta_codigo": "4.1.1.05", "conta_nome": "VT e VR", "valor_centavos": 67_400},
            {"numero_lancamento": 903, "historico": "L3 — Benefícios", "tag_ref": "folha_l3", "dc": "C", "conta_codigo": "1.1.4.01", "conta_nome": "Adiant. VT/VR", "valor_centavos": 67_400},
            {"numero_lancamento": 904, "historico": "L4 — Provisões", "tag_ref": "folha_l4", "dc": "D", "conta_codigo": "4.1.1.07", "conta_nome": "Provisões E1", "valor_centavos": 50_400},
            {"numero_lancamento": 904, "historico": "L4 — Provisões", "tag_ref": "folha_l4", "dc": "C", "conta_codigo": "2.1.2.10", "conta_nome": "Provisões a Pagar", "valor_centavos": 50_400},
        ],
        "quarentena": [
            {"modulo": "folha_pagamento", "total": 1, "homologados": 0, "inconsistencias": 0, "pendentes": 1},
        ],
        "pendencias_total": 1,
        "secoes": {
            "d2_11_folha": [
                {
                    "id": 1,
                    "documento": "d2_11_folha",
                    "ordem": 1,
                    "codigo_secao": "resumo",
                    "titulo": "1. Resumo da Folha",
                    "conteudo_md": "Bruto: {{BRUTO_TOTAL}} | Líquido A: {{LIQUIDO_A}} | Líquido B: {{LIQUIDO_B}} | VT: {{SUBSIDIO_VT}} | VR: {{VR_TOTAL}} | Exclusão: {{IMPACTO_EXCLUSAO_SIMPLES}}",
                    "status_validacao": "pendente_revisao",
                }
            ]
        },
        "rt": {"nome": "Nathalia Peres Araujo", "crc": "CRC-DF 025.431/O-7"},
    }


def test_d2_documentos_sem_constantes() -> None:
    arq = Path(__file__).resolve().parents[1] / "web" / "emissor_dossie2.py"
    codigo = arq.read_text(encoding="utf-8")
    constantes_proibidas = (
        "283333", "283_333",
        "21268", "21_268",
        "22667", "22_667",
        "241630", "241_630",
        "251065", "251_065",
        "50400", "50_400",
        "412800", "412_800",
        "23400", "23_400",
        "33000", "33_000",
        "91740", "91_740",
        "423800", "423_800",
        "0.278", "278000", "278_000",
    )
    for c in constantes_proibidas:
        assert not re.search(rf"\b{re.escape(c)}\b", codigo), f"Constante proibida {c} encontrada em emissor_dossie2.py"

    # Quando faltam dados no dicionário, o resumo e os marcadores devolvem "—" (nunca valor reserva)
    dados_vazios = _fixture_dados_d2()
    dados_vazios["comp"] = {}
    dados_vazios["itens"] = []
    dados_vazios["partidas"] = []
    dados_vazios["contratos_servico"] = []
    mk_vazio = _marcadores_d2(dados_vazios)
    for chave, valor in mk_vazio.items():
        assert valor == "—", f"Marcador {chave} deveria ser '—' sem dados, mas retornou {valor!r}"

    html_vazio = html_documento("d2_11_folha", para_web=True, dados=dados_vazios)
    assert "2.833,33" not in html_vazio
    assert "2.510,65" not in html_vazio
    assert "Bruto: — | Líquido A: — | Líquido B: —" in html_vazio


def test_d2_cenario_b() -> None:
    dados = _fixture_dados_d2()
    mk = _marcadores_d2(dados)
    assert mk["LIQUIDO_A"] == texto.brl(241_630)
    assert mk["LIQUIDO_B"] == texto.brl(251_065)
    assert mk["SUBSIDIO_VT"] == texto.brl(23_400)
    assert mk["VR_TOTAL"] == texto.brl(33_000)
    assert mk["IMPACTO_EXCLUSAO_SIMPLES"] == texto.brl(91_740)
    assert mk["PARTIDAS_DOBRADAS"] == texto.brl(423_800)

    html = html_documento("d2_11_folha", para_web=True, dados=dados)
    assert "2.510,65" in html
    assert "917,40" in html

    # Alterando a rubrica NEGOCIAL de E1 (+R$ 10,00), o Líquido B sobe dinamicamente em +R$ 10,00
    for it in dados["itens"]:
        if it["codigo_empregado"] == "E1" and it["codigo_rubrica"] == "NEGOCIAL":
            it["valor_centavos"] += 1_000
    mk2 = _marcadores_d2(dados)
    assert mk2["LIQUIDO_B"] == texto.brl(252_065)


def test_d2_regra_texto_residuo_pura() -> None:
    # 1. Falsos positivos reais da V2 (citações entre crases, "todos os documentos", revogação explícita da 1.555/2018)
    secoes_limpas = [
        {"documento": "d2_00_indice", "codigo_secao": "s1", "conteudo_md": "Eliminados campos `[INSERIR]`, removidos 6 resíduos `[cite: 19, 25]` em todos os documentos."},
        {"documento": "d2_04_termo_rt", "codigo_secao": "s2", "conteudo_md": "Termo atualizado para a Res. CFC nº 1.708/2023 (revogando a Resolução CFC nº 1.555/2018)."},
        {"documento": "d2_03_contrato", "codigo_secao": "s3", "conteudo_md": "Vencimento todo dia 10 do mês subsequente em todo o contrato."},
    ]
    cs_limpos = [
        {"codigo_documento": "termo_rt", "conteudo_md": "Substituiu a revogada Res. CFC 1.555/2018 pela Res. CFC nº 1.708/2023."},
    ]
    assert detectar_residuos_texto_d2(secoes_limpas, cs_limpos) == []

    # 2. Resíduos reais fora de crases ou 1.555/2018 invocada como norma vigente
    secoes_sujas = [
        {"documento": "d2_02_proposta", "codigo_secao": "condicoes", "conteudo_md": "Contratante inscrita no CNPJ [INSERIR CNPJ] e [cite: 19]."},
        {"documento": "d2_04_termo_rt", "codigo_secao": "base", "conteudo_md": "Emitido nos termos da Resolução CFC nº 1.555/2018 vigente."},
        {"documento": "d2_05_onboarding", "codigo_secao": "pend", "conteudo_md": "TODO: revisar CEP XX.XXX-000 e ??? antes de enviar."},
    ]
    achados = detectar_residuos_texto_d2(secoes_sujas, [])
    padroes = {a["padrao"] for a in achados}
    assert {"[INSERIR", "[cite", "1.555/2018", "TODO", "XX.XXX", "???"} <= padroes


def test_d2_quadros_fase2() -> None:
    dados = _fixture_dados_d2()
    esperados = {
        "d2_00_indice": ("Tabela 1 — Produtos do Estudo de Caso", "D2-P1", "Tabela 2 — Quarentena"),
        "d2_05_onboarding": ("Tabela 1 — Checklist de documentos", "DOC-01", "Não houve integralização", "PEND-01"),
        "d2_06_prontuario": ("Tabela 1 — Índice do prontuário", "S-2200", "Não transmitido", "Pendente crítico (sem ASO)"),
        "d2_07_ficha_e1": ("Tabela 1 — Dados de registro do empregado E1", "4110-05", "1h48", "1.722,25"),
        "d2_09_ficha_e2": ("Tabela 1 — Dados de registro do empregado E2", "5211-10", "2h00", "1.863,00"),
        "d2_14_premissas": ("Tabela 1 — Premissas adotadas", "PR-01", "Tabela 2 — Quadro de decisões", "Tabela 3 — Tabelas oficiais"),
        "d2_15_ia": ("Tabela 1 — Diário transparente de uso de IA", "Tabular DOC-01..13", "Conferido item a item pela contadora."),
    }
    for doc, trechos in esperados.items():
        html = html_documento(doc, para_web=True, dados=dados)
        assert "Dossiê 2" in html, doc
        assert "(Dossiê 1)" not in html and "do Dossiê 1" not in html, doc
        for tr in trechos:
            assert tr in html, f"{doc}: trecho esperado ausente: {tr!r}"


def test_d2_quadros_fase3_e_dado_muda_pdf_muda() -> None:
    dados = _fixture_dados_d2()
    esperados = {
        "d2_01_diagnostico": ("Tabela 1 — Identificação do cliente", "52900000015", "Helena Aparecida Mendes Duarte", "50,00%", "1.000.000,00", "500.000,00", "Tabela 3 — Quadro de achados", "LC 123/2006, art. 17, VIII", "Tabela 4 — Plano de saneamento"),
        "d2_02_proposta": ("Tabela 1 — Qualificação das partes", "48.123.456/0001-90", "CRC-DF 025.431/O-7", "Tabela 2 — Condições comerciais", "Tabela 3 — Memória de custo", "2.000,00", "6.000,00"),
        "d2_03_contrato": ("Tabela 1 — Qualificação das partes", "Tabela 2 — Condições comerciais", "4.000,00"),
        "d2_04_termo_rt": ("Tabela 1 — Qualificação das partes", "Tabela 3 — Rol de pendências abertas", "PEND-01"),
        "d2_08_exp_e1": ("Tabela 1 — Parâmetros contratuais de E1", "45 + 45 dias", "1h48"),
        "d2_10_exp_e2": ("Tabela 1 — Parâmetros contratuais de E2", "30 + 60 dias", "1,50%", "2h00"),
        "d2_12_resumo_contab": ("Tabela 2 — Conciliação integral", "Conciliado", "2.833,33"),
    }
    for doc, trechos in esperados.items():
        html = html_documento(doc, para_web=True, dados=dados)
        assert "[INSERIR" not in html, doc
        for tr in trechos:
            assert tr in html, f"{doc}: trecho esperado ausente: {tr!r}"

    # test_d2_dado_muda_pdf_muda: alterar intervalo do E1 e honorario da proposta reflete no HTML
    dados["contratos"][0]["intervalo_minutos"] = 90
    html_e1 = html_documento("d2_07_ficha_e1", para_web=True, dados=dados)
    assert "1h30" in html_e1
    dados["contratos_servico"][0]["honorario_mensal_centavos"] = 450_000
    html_prop = html_documento("d2_02_proposta", para_web=True, dados=dados)
    assert "4.500,00" in html_prop


def test_d2_regras_contrato_e_piso_puras() -> None:
    dados = _fixture_dados_d2()
    # Estado base: proposta 14/09 != contrato 01/09 nao deve gerar alerta; contrato == termo_rt (01/09) -> 0 divergencias
    assert detectar_divergencia_contratos_d2(dados["contratos_servico"]) == []

    # Contrato != termo_rt na vigencia ou proposta != contrato no honorario -> alerta
    cs_div = [dict(x) for x in dados["contratos_servico"]]
    cs_div[0]["honorario_mensal_centavos"] = 350_000
    cs_div[2]["vigencia_inicio"] = "2026-09-15"
    divs = detectar_divergencia_contratos_d2(cs_div)
    assert {d["campo"] for d in divs} == {"honorario_mensal_centavos", "vigencia_inicio"}

    # Salario >= piso e referencia preenchida -> 0 alertas
    assert detectar_salario_abaixo_piso_d2(dados["contratos"]) == []
    cts_err = [dict(x) for x in dados["contratos"]]
    cts_err[0]["salario_base_centavos"] = 150_000
    cts_err[1]["cct_referencia"] = ""
    errs = detectar_salario_abaixo_piso_d2(cts_err)
    assert any(e["tipo"] == "abaixo_piso" and e["severidade"] == "critico" for e in errs)
    assert any(e["tipo"] == "piso_ausente" and e["severidade"] == "alerta" for e in errs)

    # Todas as chaves de ajuda novas estao registradas
    for chave in (
        "aud.valor_v1", "aud.valor_rec", "cl.risco_tipo", "cl.risco_nivel", "cl.fundamento",
        "cl.providencia", "cl.responsavel", "cl.prazo", "q.resp_decisao", "q.prazo_decisao",
        "q.impacto_alt", "dil.data", "ct.jornada_horas", "ct.cct_ref", "par.data_consulta",
    ):
        assert ajuda_mod.ajuda(chave), f"Chave de ajuda ausente: {chave}"


def test_d2_quadros_por_documento() -> None:
    dados = _fixture_dados_d2()
    verificacoes = {
        "d2_00_indice": ("Tabela 1 — Produtos", "D2-P1"),
        "d2_01_diagnostico": ("Tabela 3 — Quadro de achados", "52900000015"),
        "d2_02_proposta": ("Tabela 3 — Memória de custo", "48.123.456/0001-90"),
        "d2_03_contrato": ("Tabela 2 — Condições comerciais", "4.000,00"),
        "d2_04_termo_rt": ("Tabela 3 — Rol de pendências", "PEND-01"),
        "d2_05_onboarding": ("Tabela 1 — Checklist", "DOC-01"),
        "d2_06_prontuario": ("Tabela 2 — Roteiro de eventos eSocial", "S-2200"),
        "d2_07_ficha_e1": ("Tabela 1 — Dados de registro do empregado E1", "4110-05"),
        "d2_08_exp_e1": ("Tabela 1 — Parâmetros contratuais de E1", "45 + 45 dias"),
        "d2_09_ficha_e2": ("Tabela 1 — Dados de registro do empregado E2", "5211-10"),
        "d2_10_exp_e2": ("Tabela 1 — Parâmetros contratuais de E2", "30 + 60 dias"),
        "d2_11_folha": ("Espelho dinâmico do Motor Contábil", "PROV-1/3"),
        "d2_12_resumo_contab": ("Tabela 2 — Conciliação integral", "Conciliado"),
        "d2_13_auditoria": ("Tabela 1 — Planejamento e Papéis de Trabalho", "PT-01", "Tabela 2 — Recálculo Independente", "AUD-03"),
        "d2_14_premissas": ("Tabela 1 — Premissas adotadas", "PR-01"),
        "d2_15_ia": ("Tabela 1 — Diário transparente de uso de IA", "Tabular DOC-01..13"),
    }
    assert set(verificacoes) == set(DOCUMENTOS)
    for doc, trechos in verificacoes.items():
        html = html_documento(doc, para_web=True, dados=dados)
        for tr in trechos:
            assert tr in html, f"{doc}: trecho esperado ausente: {tr!r}"


def test_d2_recalculo_independente_bate_com_gabarito() -> None:
    dados = _fixture_dados_d2()
    comp = recalcular_folha_independente_dados(dados["comp"], dados["contratos"], dados["parametros"], dados["itens"])
    mapa = {(r["codigo_empregado"], r["codigo_rubrica"]): r for r in comp}

    # Gabarito E1
    assert mapa[("E1", "INSS-RET")]["valor_recalculado_centavos"] == 9_000
    assert mapa[("E1", "FGTS-8")]["valor_recalculado_centavos"] == 9_600
    assert mapa[("E1", "VR-PAT")]["valor_recalculado_centavos"] == 33_000
    assert mapa[("E1", "NEGOCIAL")]["valor_recalculado_centavos"] == 3_996
    assert mapa[("E1", "PROV-FER")]["valor_recalculado_centavos"] == 20_000
    assert mapa[("E1", "PROV-1/3")]["valor_recalculado_centavos"] == 6_667
    assert mapa[("E1", "PROV-FGTS")]["valor_recalculado_centavos"] == 3_733

    # Gabarito E2
    assert mapa[("E2", "COMISSAO")]["valor_recalculado_centavos"] == 90_000
    assert mapa[("E2", "DSR-COM")]["valor_recalculado_centavos"] == 10_000
    assert mapa[("E2", "INSS-RET")]["valor_recalculado_centavos"] == 12_268
    assert mapa[("E2", "FGTS-8")]["valor_recalculado_centavos"] == 13_067
    assert mapa[("E2", "NEGOCIAL")]["valor_recalculado_centavos"] == 5_439

    # Diferenca zero em 100% das rubricas contra o motor
    assert len(comp) == len(dados["itens"])
    assert detectar_recalculo_divergente_d2(comp) == []


def test_d2_regras_novas() -> None:
    dados = _fixture_dados_d2()
    # 1. D2_TEXTO_RESIDUO (sujo -> alerta; falso positivo -> 0)
    assert detectar_residuos_texto_d2([{"documento": "d2_01", "codigo_secao": "s1", "conteudo_md": "Campo [INSERIR CNPJ]"}], [])
    assert detectar_residuos_texto_d2([{"documento": "d2_01", "codigo_secao": "s1", "conteudo_md": "Eliminados `[INSERIR]` em todos os docs."}], []) == []
    # 2. D2_PROPOSTA_CONTRATO_DIVERGENTE
    cs_div = [dict(x) for x in dados["contratos_servico"]]
    cs_div[0]["valor_hora_centavos"] = 15_000
    assert detectar_divergencia_contratos_d2(cs_div)
    # 3. D2_SALARIO_ABAIXO_PISO
    cts_div = [dict(x) for x in dados["contratos"]]
    cts_div[1]["salario_base_centavos"] = 100_000
    assert any(a["severidade"] == "critico" for a in detectar_salario_abaixo_piso_d2(cts_div))
    # 4. D2_RECALCULO_DIVERGENTE (forcar divergencia no motor)
    itens_div = [dict(x) for x in dados["itens"]]
    itens_div[0]["valor_centavos"] += 100
    comp_div = recalcular_folha_independente_dados(dados["comp"], dados["contratos"], dados["parametros"], itens_div)
    divs = detectar_recalculo_divergente_d2(comp_div)
    assert len(divs) == 1 and divs[0]["codigo_rubrica"] == "SAL-PROP" and divs[0]["diferenca_centavos"] == 100


def test_d2_planilha_provisoes_separadas() -> None:
    dados = _fixture_dados_d2()
    wb = _montar_workbook_d2(dados)
    ws_prov = wb["Provisoes_e_Integracao"]
    ws_mem = wb["Memoria_Calculo"]

    assert ws_prov["A7"].value == "Férias (1/12)"
    assert ws_prov["A8"].value == "1/3 Constitucional s/ Férias"
    assert ws_prov["C9"].value == "=SUM(C6:C8)"
    assert ws_prov["E29"].value == "=E7+E8"
    assert ws_prov["E34"].value == "=SUM(E13:E33)"
    assert "Provisoes_e_Integracao!E10" in str(ws_mem["C11"].value)
    assert "Provisoes_e_Integracao!E9" in str(ws_mem["C12"].value)

    formulas = [
        v for s in wb.worksheets for row in s.iter_rows(values_only=True) for v in row
        if isinstance(v, str) and v.startswith("=")
    ]
    assert len(formulas) >= 100


@pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")
def test_motor_folha_d2_reconciliacao_e_partidas_dobradas():
    with conectar_pg() as conn:
        res = recalcular_folha_d2(conn)
        conn.commit()
    tot = res["totais"]
    assert tot["bruto"] == 283_333
    assert tot["inss"] == 21_268
    assert tot["irrf"] == 0
    assert tot["fgts"] == 22_667
    assert tot["vt_desc"] == 11_000
    assert tot["vt_subs"] == 23_400
    assert tot["vt_subs_2d"] == 6_200
    assert tot["vr"] == 33_000
    assert tot["neg_a"] == 9_435
    assert tot["liq_a"] == 241_630
    assert tot["liq_b"] == 251_065
    assert tot["prov_total"] == 50_400
    assert res["custo_total_centavos"] == 412_800
    assert tot["custo_adm"] == 224_720
    assert tot["custo_com"] == 188_080
    assert res["exclusao_simples_extra_centavos"] == 91_740
    assert res["partidas_debito_centavos"] == 423_800
    assert res["partidas_credito_centavos"] == 423_800
    assert res["diferenca_partidas"] == 0


@pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")
def test_seletor_contexto_d1_d2_e_isolamento_d4():
    app = create_app()
    c = app.test_client()

    # Padrao inicia em D1 (PRISMA JRNA)
    r1 = c.get("/")
    assert r1.status_code == 200
    assert "PRISMA JRNA" in r1.get_data(as_text=True)

    # Alterna para D2 via query ou POST
    r2 = c.get("/?dossie=D2")
    assert r2.status_code == 200
    html_d2 = r2.get_data(as_text=True)
    assert "Rota Sul" in html_d2
    assert "2.833,33" in html_d2
    assert "Joinville" not in html_d2

    # Todas as rotas em D2 abrem sem erros e sem chaves de ajuda faltantes
    for url in ("/cadastro", "/instrumentos", "/legalizacao", "/onboarding", "/dp", "/folha", "/sustentacao", "/emissao"):
        resp = c.get(url)
        html = resp.get_data(as_text=True)
        assert resp.status_code == 200, url
        assert "data-help-missing" not in html, url
        assert 'data-modo="consulta"' in html, url

    # Alterna de volta para D1 via POST
    r_back = c.post("/contexto/selecionar", data={"dossie": "D1", "next": "/"}, follow_redirects=True)
    assert r_back.status_code == 200
    assert "PRISMA JRNA" in r_back.get_data(as_text=True)


@pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")
def test_esocial_recusa_transmitido_sem_recibo_e_homologar_exige_justificativa():
    app = create_app()
    c = app.test_client()
    c.get("/dp")
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM erp.esocial_evento WHERE codigo_evento = 'S-2220' LIMIT 1")
        ev_id = int(cur.fetchone()["id"])

    r1 = c.post(
        f"/dp/esocial/{ev_id}/salvar",
        data={
            "prazo_legal": "Até 15/10/2026",
            "status_envio": "transmitido",
            "numero_recibo": "",
            "observacao": "teste",
            "status_validacao": "pendente_revisao",
            "acao": "rascunho",
        },
        follow_redirects=True,
    )
    assert "recibo" in r1.get_data(as_text=True).lower()

    r2 = c.post(
        f"/dp/esocial/{ev_id}/salvar",
        data={
            "prazo_legal": "Até 15/10/2026",
            "status_envio": "pendente",
            "numero_recibo": "",
            "observacao": "bloqueado ASO",
            "status_validacao": "pendente_revisao",
            "justificativa_contadora": "",
            "acao": "homologar",
        },
        follow_redirects=True,
    )
    assert "justificativa" in r2.get_data(as_text=True).lower()


@pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")
def test_planilha_aberta_d2_formulas_e_16_previas():
    app = create_app()
    c = app.test_client()
    c.get("/?dossie=D2")

    rx = c.get("/emissao/planilha.xlsx")
    assert rx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(rx.data), data_only=False)
    assert set(wb.sheetnames) == {"Leia-me", "Parametros", "Folha_Set2026", "Memoria_Calculo", "Provisoes_e_Integracao"}
    formulas = [
        v for s in wb.worksheets for row in s.iter_rows(values_only=True) for v in row
        if isinstance(v, str) and v.startswith("=")
    ]
    assert len(formulas) >= 100

    for doc in DOCUMENTOS:
        rp = c.get(f"/emissao/previa/{doc}")
        assert rp.status_code == 200, doc
        assert "Rota Sul" in rp.get_data(as_text=True) or "PRISMA JRNA" in rp.get_data(as_text=True)
