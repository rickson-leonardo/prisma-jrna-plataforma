"""Rotulos legiveis em portugues contabil para codigos tecnicos do banco.

A UI mostra o rotulo; o codigo tecnico fica apenas em metadado (atributo title / data-codigo).
"""

from __future__ import annotations

ROTULOS: dict[str, dict[str, str]] = {
    "status": {
        "pendente_revisao": "Pendente de revisão",
        "alerta_inconsistencia": "Inconsistência apontada",
        "homologado_contadora": "Homologado pela contadora",
        "acervo_referencia": "Referência do acervo",
    },
    "origem": {
        "acervo_sigaa": "Acervo oficial da disciplina",
        "importado_v1": "Importado da 1ª entrega (v1)",
        "importado_rascunho_v2": "Importado do rascunho v2",
        "usuario": "Registrado pela contadora",
    },
    "regime": {
        "simples_segregado": "Simples — receitas segregadas por CNAE",
        "simples_fator_r_global": "Simples — Fator R sobre toda a receita",
        "simples_auto_prolabore_28": "Simples — pró-labore ajustado a 28%",
        "v1_fixo_6_erro": "Erro da v1 — alíquota fixa de 6%",
    },
    "regime_tributario": {
        "Simples_Anexo_III": "Simples Nacional — Anexo III",
        "Simples_Anexo_V": "Simples Nacional — Anexo V",
        "Simples_Misto": "Simples Nacional — Anexos III e V (misto)",
        "Lucro_Presumido": "Lucro Presumido",
        "Lucro_Real": "Lucro Real",
    },
    "anexo": {"Anexo_III": "Anexo III", "Anexo_V": "Anexo V"},
    "raia": {
        "socias": "Sócias / requerentes",
        "escritorio_contabil": "Escritório / contadora RT",
        "orgaos_publicos": "Órgãos públicos DF e RFB",
    },
    "risco": {
        "dispensa": "Dispensa de ato público",
        "baixo": "Baixo risco",
        "alto_na": "Alto risco — não aplicável",
        "alto": "Alto risco",
        "regulatorio": "Regulatório (conselho profissional)",
    },
    "execucao": {
        "pendente": "A iniciar",
        "em_andamento": "Em andamento",
        "concluida": "Concluída",
        "exigencia": "Em exigência",
    },
    "haveres": {
        "nao_aplicavel": "Não se aplica",
        "balanco_determinacao": "Balanço de determinação",
        "fcd": "Fluxo de caixa descontado (FCD)",
    },
    "quorum": {
        "nao_aplicavel": "Não se aplica",
        "unanimidade": "Unanimidade",
        "gestao_ordinaria": "Gestão ordinária (administradora)",
        "judicial": "Via judicial (art. 1.030 CC)",
        "maioria_simples": "Maioria simples",
    },
    "matriz": {
        "plano_negocios": "Plano de Negócios",
        "contrato_social": "Contrato Social",
        "memorando": "Memorando (MoU)",
        "fluxo_abertura": "Fluxo de Abertura DF",
    },
    "tipo_estab": {"matriz": "Matriz", "filial": "Filial", "unico": "Estabelecimento único"},
    "porte": {"ME": "Microempresa (ME)", "EPP": "Empresa de Pequeno Porte (EPP)", "Demais": "Demais portes"},
    "severidade": {"critico": "Crítico", "alerta": "Atenção", "info": "Nota"},
    "modulo": {
        "cadastro": "Cadastro e QSA",
        "instrumentos": "Contrato Social e MoU",
        "legalizacao": "Legalização DF",
        "planejamento": "Financeiro e tributário",
        "sustentacao": "Sustentação",
        "cadastro_empresa": "Empresa",
        "cadastro_estabelecimento": "Estabelecimentos",
        "cadastro_socios": "Quadro de sócias",
        "cadastro_pessoas": "Pessoas",
        "cadastro_identificadores": "Registros (CPF, CRC, CNPJ)",
        "cadastro_enquadramento": "Enquadramento e RT",
        "instrumentos_societarios": "Cláusulas societárias",
        "legalizacao_df": "Etapas de legalização",
        "orcamento_tributario": "Cenários orçamentários",
        "consultas_normativas": "Consultas normativas",
        "decisoes_preliminares": "Decisões preliminares",
        "conformidade_criterios": "Critérios das matrizes",
        "diario_ia": "Diário de IA",
        "documentos_dossie1": "Textos dos documentos",
    },
    "documento": {
        "indice": "00 · Índice Geral",
        "pesquisa": "01 · Pesquisa Normativa",
        "plano_negocios": "02 · Plano de Negócios",
        "contrato_social": "03 · Contrato Social",
        "memorando": "04 · Memorando (MoU)",
        "fluxo_abertura": "05 · Fluxo de Abertura DF",
    },
}

# Status -> classe visual DMA v3 (ok / at / cr / in)
CLASSE_STATUS = {
    "homologado_contadora": "ok",
    "pendente_revisao": "at",
    "alerta_inconsistencia": "cr",
    "acervo_referencia": "in",
    "critico": "cr",
    "alerta": "at",
    "info": "in",
}

# Modulos da view de quarentena -> estacao (rota) onde sao revisados
MODULO_ESTACAO = {
    "cadastro_empresa": "cadastro",
    "cadastro_estabelecimento": "cadastro",
    "cadastro_socios": "cadastro",
    "cadastro_pessoas": "cadastro",
    "cadastro_identificadores": "cadastro",
    "cadastro_enquadramento": "cadastro",
    "instrumentos_societarios": "instrumentos",
    "legalizacao_df": "legalizacao",
    "orcamento_tributario": "planejamento",
    "consultas_normativas": "sustentacao",
    "decisoes_preliminares": "sustentacao",
    "conformidade_criterios": "sustentacao",
    "diario_ia": "sustentacao",
    "documentos_dossie1": "emissao",
}


def rotulo(valor: object, grupo: str = "status") -> str:
    """Retorna o rotulo legivel; se nao houver traducao, devolve o proprio valor."""
    if valor is None:
        return "—"
    return ROTULOS.get(grupo, {}).get(str(valor), str(valor))


def opcoes(grupo: str) -> list[tuple[str, str]]:
    return list(ROTULOS.get(grupo, {}).items())
