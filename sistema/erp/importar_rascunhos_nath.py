"""Importador em quarentena anti-enviesamento dos insumos do Dossie 1 (v1 + rascunho v2).

Regras de governanca:
- Le apenas dados reais existentes em D1/ (via lab_contabil) e G:\\Meu Drive\\Nath\\Trabalho 01.
- Nenhuma suposicao ou dado ficticio de rascunho_v2 entra como "homologado".
- Registros criados pela contadora (origem_registro = 'usuario') ou homologados
  (status_validacao = 'homologado_contadora') nunca sao sobrescritos por re-execucoes.
  A tela preserva origem_registro ao editar; a protecao vem de INSERT ... ON CONFLICT DO NOTHING.
  # ponytail: os 2 UPDATEs de complemento (empresa/enquadramento) nao protegem registro editado e
  # ainda pendente (so preenchem COALESCE/placeholder); se surgir sobrescrita real, criar coluna editado_em.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from psycopg2.extras import execute_values

from sistema.pg.db import conectar_pg

DEFAULT_NATH_DIR = Path(r"G:\Meu Drive\Nath\Trabalho 01")


def _slug(txt: str) -> str:
    s = txt.lower().strip()
    trocas = {
        "á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e",
        "í": "i", "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    for k, v in trocas.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "item"


def _limpar_md(txt: str) -> str:
    t = txt.replace("\\$", "$").replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", t).strip()


def parse_clausulas_originais_contrato(texto: str) -> dict[int, str]:
    """Extrai o texto literal das clausulas (1..23) de orig_Contrato_Social_Atualizado.md."""
    limpo = re.sub(r"\n---\n+## Página \d+\s*\n", "\n", texto)
    matches = list(re.finditer(r"CLÁUSULA\s+(\d+)[ªa]?\s*-\s*([^\n:]+):", limpo))
    res: dict[int, str] = {}
    for idx, m in enumerate(matches):
        num = int(m.group(1))
        ini = m.start()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(limpo)
        bloco = re.sub(r"\s+", " ", limpo[ini:fim]).strip()
        res[num] = bloco
    return res


def parse_clausulas_v2_contrato(texto: str) -> list[dict[str, Any]]:
    """Extrai as clausulas do rascunho v2 de 03_Contrato_Social_PRISMA_JRNA.md."""
    matches = list(re.finditer(r"^###\s+CLÁUSULA\s+(\d+)[ªa]?\s*[—–-]\s*(.+)$", texto, re.M))
    clausulas: list[dict[str, Any]] = []
    for idx, m in enumerate(matches):
        num = int(m.group(1))
        titulo = m.group(2).strip()
        ini = m.end()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else texto.find("## ANEXOS INTEGRANTES")
        if fim == -1 or fim < ini:
            fim = len(texto)
        corpo = texto[ini:fim].strip()
        corpo = re.sub(r"\n---\n.*", "", corpo, flags=re.S).strip()
        clausulas.append({"numero": num, "titulo": titulo, "texto": corpo})
    return clausulas


def parse_clausulas_originais_mou(texto: str) -> dict[str, str]:
    """Extrai o texto literal das clausulas de orig_Memorando_Entendimentos_Atualizado.md."""
    limpo = re.sub(r"\n---\n+## Página \d+\s*\n", "\n", texto)
    matches = list(re.finditer(r"CLÁUSULA\s+([A-ZÁÉÍÓÚÇ]+)\s*-\s*([^\n]+)", limpo))
    res: dict[str, str] = {}
    for idx, m in enumerate(matches):
        ord_txt = m.group(1).strip().upper()
        ini = m.start()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(limpo)
        res[ord_txt] = re.sub(r"\s+", " ", limpo[ini:fim]).strip()
    return res


def parse_clausulas_v2_mou(texto: str) -> list[dict[str, Any]]:
    """Extrai as 10 clausulas por bloco (A..J) de 04_Memorando_de_Entendimentos_MOU_PRISMA_JRNA.md."""
    matches = list(
        re.finditer(r"^##\s+CLÁUSULA\s+(\d+)[ªa]?\s*[—–-]\s*(.+?)\s*\(BLOCO\s+([A-Z])\)", texto, re.M)
    )
    res: list[dict[str, Any]] = []
    for idx, m in enumerate(matches):
        num = int(m.group(1))
        titulo = m.group(2).strip()
        bloco = m.group(3).strip().upper()
        ini = m.end()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else texto.find("E, por estarem justas")
        if fim == -1 or fim < ini:
            fim = len(texto)
        corpo = re.sub(r"\n---\s*$", "", texto[ini:fim].strip()).strip()
        res.append({"numero": num, "bloco": bloco, "titulo": titulo, "texto": corpo})
    return res


def parse_pesquisa_v2(texto: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extrai Q1..Q10 e Tabela 2 de Decisoes Preliminares de 01_Pesquisa_Registro_Profissional_e_Redesim_DF.md."""
    q_matches = list(re.finditer(r"^###\s+Q(\d+)\s*[—–-]\s*(.+)$", texto, re.M))
    questoes: list[dict[str, Any]] = []
    # Mapeamento da Tabela 1 (Q9)
    impactos_q9 = {}
    t1_m = re.search(r"### Q9.*?\n(\|[^\n]+\|(?:\n\|[^\n]+\|)+)", texto, re.S)
    if t1_m:
        impactos_q9_txt = []
        for row in t1_m.group(1).splitlines()[2:]:
            cols = [c.strip() for c in row.strip("|").split("|")]
            if len(cols) >= 3:
                impactos_q9_txt.append(f"{_limpar_md(cols[0])} -> {_limpar_md(cols[2])}")
        impactos_q9["9"] = " | ".join(impactos_q9_txt)

    for idx, m in enumerate(q_matches):
        num = int(m.group(1))
        enunc = m.group(2).strip()
        ini = m.end()
        fim = q_matches[idx + 1].start() if idx + 1 < len(q_matches) else texto.find("## 2. Quadro Consolidado")
        bloco = texto[ini:fim].strip()

        fonte_m = re.search(r"\*\*Fonte oficial[^:]*:\*\*\s*(.+)", bloco)
        link_m = re.search(r"\*\*Link oficial[^:]*:\*\*\s*(.+)", bloco)
        data_m = (
            re.search(r"\*\*Data de acesso:\*\*\s*(\d{2})/(\d{2})/(\d{4})", bloco)
            or re.search(r"\((\d{2})/(\d{2})/(\d{4})\)", bloco)
        )

        norma = _limpar_md(fonte_m.group(1)) if fonte_m else ("Consolidacao normativa Tabela 1 (Q9)" if num == 9 else "NORMA NAO INFORMADA NA ORIGEM")
        link = link_m.group(1).strip() if link_m else ("cfc.org.br / crcdf.org.br / redesim.df.gov.br (Tabela 1)" if num == 9 else "LINK NAO INFORMADO NA ORIGEM")
        if data_m is None:
            raise ValueError(f"Data de acesso ausente na questao Q{num} da Pesquisa.")
        data_iso = f"{data_m.group(3)}-{data_m.group(2)}-{data_m.group(1)}"

        linhas_resp = []
        for ln in bloco.splitlines():
            if ln.startswith("- **Fonte oficial") or ln.startswith("- **Link oficial") or ln.startswith("- **Data de acesso") or ln.strip() == "---":
                continue
            linhas_resp.append(ln)
        resp = "\n".join(linhas_resp).strip()

        questoes.append({
            "numero_questao": num,
            "enunciado": enunc,
            "resposta_autoral": resp,
            "norma_citada": norma,
            "link_oficial": link,
            "data_acesso": data_iso,
            "decisao_impactada": impactos_q9.get(str(num)),
        })

    # Tabela 2 (Decisoes Preliminares)
    decisoes: list[dict[str, Any]] = []
    sec2_m = re.search(r"## 2\. Quadro Consolidado de Decisões Preliminares.*?\n(\|[^\n]+\|(?:\n\|[^\n]+\|)+)", texto, re.S)
    if sec2_m:
        for i, row in enumerate(sec2_m.group(1).splitlines()[2:], start=1):
            cols = [c.strip() for c in row.strip("|").split("|")]
            if len(cols) >= 4:
                decisoes.append({
                    "ordem": i,
                    "elemento": _limpar_md(cols[0]),
                    "opcao_adotada": _limpar_md(cols[1]),
                    "alternativas_consideradas": _limpar_md(cols[2]),
                    "justificativa_documental": _limpar_md(cols[3]),
                })
    return questoes, decisoes


def parse_criticas_devolutiva(texto: str) -> tuple[dict[tuple[str, str], tuple[int, str]], dict[str, list[str]]]:
    """Extrai notas (< 3) por criterio e criticas textuais literais de orig_Devolutiva_Dossie1_G07.md."""
    criterios_v1: dict[tuple[str, str], tuple[int, str]] = {}
    secoes = {
        "plano_negocios": re.search(r"Plano de Negócios — nota.*?(?=Contrato Social — nota)", texto, re.S),
        "contrato_social": re.search(r"Contrato Social — nota.*?(?=Memorando de Entendimento — nota)", texto, re.S),
        "memorando": re.search(r"Memorando de Entendimento — nota.*?(?=Fluxo de Abertura — nota)", texto, re.S),
        "fluxo_abertura": re.search(r"Fluxo de Abertura — nota.*", texto, re.S),
    }
    criticas_texto: dict[str, list[str]] = {}
    for mat, m_sec in secoes.items():
        if not m_sec:
            continue
        bloco = m_sec.group(0)
        linhas = [ln.strip() for ln in bloco.splitlines() if ln.strip() and not ln.strip().startswith("|")]
        criticas_texto[mat] = linhas[:12]
        for row in re.findall(r"^\|\s*([A-Z]\d+)\s*\|\s*([^|]+)\|\s*(\d)/4\s*\|", bloco, re.M):
            cod, desc_esp, nota_s = row[0].strip(), row[1].strip(), int(row[2])
            criterios_v1[(mat, cod)] = (nota_s, f"Devolutiva v1 ({nota_s}/4): {desc_esp}")
    return criterios_v1, criticas_texto


def parse_diario_ia(texto: str) -> list[dict[str, str]]:
    """Extrai a matriz de uso de IA de 06_Declaracao_Uso_Inteligencia_Artificial_Dossie1.md."""
    m = re.search(r"## 1\. Matriz de Uso de Inteligência Artificial.*?\n(\|[^\n]+\|(?:\n\|[^\n]+\|)+)", texto, re.S)
    if not m:
        return []
    itens: list[dict[str, str]] = []
    for row in m.group(1).splitlines()[2:]:
        cols = [c.strip() for c in row.strip("|").split("|")]
        if len(cols) >= 5:
            itens.append({
                "entregavel": _limpar_md(cols[0]),
                "houve_uso": _limpar_md(cols[1]),
                "finalidade": _limpar_md(cols[2]),
                "fonte_oficial": _limpar_md(cols[3]),
                "revisao_humana": _limpar_md(cols[4]),
            })
    return itens


def _build_etapas_legalizacao_df() -> list[dict[str, Any]]:
    """Etapas do fluxo paralegal de abertura no Distrito Federal baseadas em 05_Fluxo_Abertura_Empresa_DF_Redesim_e_BPMN.md."""
    ref_v1 = "Fluxo de Abertura nao entregue na v1 (Nota 0,0); havia apenas rascunho parcial Bizagi sem RA-I/LUOS, SEEC-DF ou RLE."
    return [
        {
            "ordem": 1, "bloco": "A", "codigo": "A1-A2",
            "nome_etapa": "Definicao Societaria, Tipo Ltda., Capital R$ 40k e CNAEs 6920-6/01 e 6920-6/02",
            "raia_responsavel": "socias",
            "orgao": "Planejamento Interno Societario (Codigo Civil arts. 1.052 a 1.087; DREI IN 81/2020)",
            "portal_url": "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Definicao de objeto social (Contabilidade + Auditoria/Consultoria Tributaria), divisao 50/50 de quotas e aporte em moeda corrente.",
            "saida_doc": "Termo de Planejamento Societario, Enquadramento ME (LC 123/2006) e Checklist ausencia vedacoes art. 17.",
            "prazo_legal": "Previo a qualquer protocolo",
            "regra_retorno_exigencia": "Se incluir atividade vedada ou objeto de Auditoria sem CNAE 6920-6/02, revisar objeto antes da viabilidade.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "PLAN-G07-2026-01",
            "apontamento_auditoria": "Confirmar na interface se o escopo incluira Auditoria (CNAE 6920-6/02) e validar impacto tributario do Fator R.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 2, "bloco": "A", "codigo": "A5",
            "nome_etapa": "Consulta Urbanistica Previa (LUOS / Geoportal SEDUH-DF) antes da Locacao",
            "raia_responsavel": "socias",
            "orgao": "SEDUH-DF / Geoportal DF (LC Distrital 948/2019 — LUOS)",
            "portal_url": "https://www.geoportal.seduh.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Inscricao imobiliaria (IPTU) da unidade pretendida no Setor Comercial Sul (SCS Q. 06) e lista de CNAEs.",
            "saida_doc": "Confirmacao urbanistica de uso comercial/servicos compativel antes da assinatura do contrato de locacao/coworking.",
            "prazo_legal": "Anterior ao contrato de locacao",
            "regra_retorno_exigencia": "Caso o lote nao admita o CNAE pretendido na LUOS, suspender locacao e selecionar endereco comercial compativel.",
            "classificacao_risco": "baixo",
            "protocolo_simulado": "LUOS-SCS-2026",
            "apontamento_auditoria": "VALIDAR ENDERECO REAL/DIDATICO: SCS Q. 06 Bl. A Lote 157 Sala 901 foi preenchido no rascunho v2 para eliminar CEP XX.XXX.XXX.",
            "referencia_v1_original": "v1 citava apenas 'Asa Sul, 6º andar, sala 901, CEP XX.XXX.XXX' sem verificar LUOS.",
        },
        {
            "ordem": 3, "bloco": "A", "codigo": "A3",
            "nome_etapa": "Consulta ao Simulador de Risco (RedeSim-DF / RLE)",
            "raia_responsavel": "escritorio_contabil",
            "orgao": "JUCIS-DF / RedeSim-DF (Lei 13.874/2019 e Res. CGSIM 57/2020)",
            "portal_url": "https://redesim.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "CNAEs 6920-6/01 e 6920-6/02, metragem estimada da sala comercial e questionario preliminar de risco.",
            "saida_doc": "Enquadramento preliminar de Baixo Risco (Risco I/II) dispensando vistoria previa.",
            "prazo_legal": "Previo a viabilidade",
            "regra_retorno_exigencia": "Para clientes futuros classificados como Risco III (Alto Risco — ex.: clinicas), acionar fluxo especifico de projeto/vistoria antes da operacao.",
            "classificacao_risco": "baixo",
            "protocolo_simulado": "SIM-RISCO-6920",
            "apontamento_auditoria": "Verificar classificacao de baixo risco com metragem real/simulada do coworking.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 4, "bloco": "B", "codigo": "B1-B5",
            "nome_etapa": "Consulta Previa de Viabilidade (Localizacao na Adm. Regional RA-I + Nome na JUCIS-DF)",
            "raia_responsavel": "orgaos_publicos",
            "orgao": "Administracao Regional do Plano Piloto (RA-I) + JUCIS-DF via RedeSim-DF (Decreto DF 40.178/2019)",
            "portal_url": "https://www.jucis.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Endereco completo com IPTU, CNAEs e denominacao social principal + nomes alternativos de contingencia.",
            "saida_doc": "Protocolo DFP aprovado (localizacao LUOS sem prefeitura no DF + pesquisa de colidencia de nome + mapa preliminar de licenciadores).",
            "prazo_legal": "Validade operacional de 90 dias (controle B3)",
            "regra_retorno_exigencia": "Em caso de exigencia de IPTU ou colidencia de nome, registrar motivo, anexar certidao de onus/IPTU ou acionar nome alternativo #2 ('Lustosa & Peres') antes do prazo.",
            "classificacao_risco": "baixo",
            "protocolo_simulado": "DFP-2026-004198-DF",
            "apontamento_auditoria": "DF nao possui municipios nem prefeituras (art. 32 CF); conferencia critica para a defesa oral.",
            "referencia_v1_original": "Relatorio Bizagi v1 citava apenas 'Analisar Viabilidade (JUCIS-DF)' omitindo competencia da Administracao Regional.",
        },
        {
            "ordem": 5, "bloco": "C", "codigo": "C1-C4",
            "nome_etapa": "Preenchimento do DBE no Coletor Nacional e Conferencia Tripla no Integrador RLE-DF",
            "raia_responsavel": "escritorio_contabil",
            "orgao": "Receita Federal (Coletor Nacional Redesim) + Integrador RedeSim-DF",
            "portal_url": "https://www.gov.br/empresas-e-negocios/pt-br/redesim",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Protocolo DFP aprovado, dados cadastrais, QSA 50/50, capital R$ 40k, RT CRC-DF e minuta do Contrato Social.",
            "saida_doc": "Recibo DBE transmitido, FCN (Ficha de Cadastro Nacional) e checklist pre-protocolo conferido.",
            "prazo_legal": "Dentro dos 90 dias de validade do DFP",
            "regra_retorno_exigencia": "Corrigir eventual divergencia de CEP, CNAE ou quotas entre DFP, DBE e Contrato Social antes da assinatura.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "DBE-DF2600194827",
            "apontamento_auditoria": "Conferir consistencia tripla com Estacao 1 (Cadastro) e Estacao 2 (Contrato Social).",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 6, "bloco": "D", "codigo": "D1",
            "nome_etapa": "Validacao de Assinatura Eletronica (Gov.br Prata/Ouro ou e-CPF ICP-Brasil) e Firma Digital",
            "raia_responsavel": "socias",
            "orgao": "Portal Gov.br / ICP-Brasil (Lei 14.063/2020; MP 2.200-2/2001)",
            "portal_url": "https://www.gov.br/governodigital/pt-br/assinatura-eletronica",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Contas Gov.br Prata/Ouro ou certificados e-CPF A1/A3 validos das duas socias (> 30 dias da expiracao).",
            "saida_doc": "Contrato Social definitivo + Declaracao de Desimpedimento (arts. 972 e 1.011 § 1º CC) assinados em via unica digital.",
            "prazo_legal": "Previo ao protocolo na JUCIS-DF",
            "regra_retorno_exigencia": "Se assinatura falhar por nivel Bronze no Gov.br ou certificado expirado, atualizar validacao biometrica/certificado antes do reenvio.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "GOVBR-ASSIN-2026",
            "apontamento_auditoria": "Confirmar alinhamento com Clausula 23 e fecho do Contrato Social.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 7, "bloco": "D", "codigo": "D2-D5",
            "nome_etapa": "Protocolo em Via Unica Digital, Deferimento e Emissao do NIRE + Contrato Chancelado",
            "raia_responsavel": "orgaos_publicos",
            "orgao": "JUCIS-DF — Junta Comercial, Industrial e Servicos do DF (Lei 8.934/1994; CC arts. 1.151 e 1.154)",
            "portal_url": "https://www.jucis.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "DARE paga, Contrato Social assinado, DBE, DFP e anexos integrantes (Desimpedimento e documentos civis).",
            "saida_doc": "Contrato Social registrado com chancela digital (hash) + numero do NIRE.",
            "prazo_legal": "Protocolo em ate 30 dias da assinatura p/ retroagir efeitos (CC art. 1.151); 30 dias para cumprir eventual exigencia (Lei 8.934 art. 40 § 2º).",
            "regra_retorno_exigencia": "Havendo exigencia do vogal/analista, sanear minuta/anexos em ate 30 dias mantendo a taxa recolhida e reenviar protocolo.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "JUCIS-DF-NIRE-2026",
            "apontamento_auditoria": "Garantir que Cl. 3ª do Contrato fixe inicio das atividades no registro (NAO na assinatura).",
            "referencia_v1_original": "Contrato v1 dizia inicio 'na data de assinatura deste instrumento'.",
        },
        {
            "ordem": 8, "bloco": "E", "codigo": "E1-E3",
            "nome_etapa": "Emissao Simultanea do CNPJ (RFB) e do Cadastro Fiscal do DF — CF/DF (SEEC-DF)",
            "raia_responsavel": "orgaos_publicos",
            "orgao": "Receita Federal do Brasil + Secretaria de Estado de Economia do DF — SEEC-DF (CF art. 147)",
            "portal_url": "https://www.economia.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Transmissao automatica do deferimento JUCIS-DF via Integrador Nacional Redesim.",
            "saida_doc": "Comprovante CNPJ (Nat. Jur. 206-2, QSA, CNAEs) e Ficha CF/DF (unificada ISS/ICMS; SEEC-DF atua apenas na esfera tributaria, nao licenciadora).",
            "prazo_legal": "Integracao simultanea ao arquivamento",
            "regra_retorno_exigencia": "Conferir divergencias de QSA/CNAEs imediatamente via evento de alteracao cadastral se houver inconsistencia no cartao CNPJ ou CF/DF.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "CNPJ-48123456000190",
            "apontamento_auditoria": "ATENCAO: CNPJ 48.123.456/0001-90 e didatico padronizado com D2. Ressaltar expressamente que SEEC-DF NAO e orgao licenciador.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 9, "bloco": "E", "codigo": "E4-E5",
            "nome_etapa": "Credenciamento NFS-e DF (e-CNPJ A1 / Agenci@Net) e Opcao pelo Simples Nacional",
            "raia_responsavel": "escritorio_contabil",
            "orgao": "SEEC-DF (Agenci@Net) + Portal do Simples Nacional / RFB (LC 123/2006; Res. CGSN 140/2018 art. 6º § 5º)",
            "portal_url": "https://www8.receita.fazenda.gov.br/SimplesNacional/",
            "data_consulta": "2026-08-14",
            "entrada_docs": "Cartao CNPJ, Ficha CF/DF, certificado digital e-CNPJ A1 da sociedade e conferencia de ausencia de impedimentos.",
            "saida_doc": "Autorizacao de emissao NFS-e DF + Termo de Deferimento da Opcao pelo Simples Nacional (ano-calendario inicial).",
            "prazo_legal": "Opcao Simples: ate 30 dias do ultimo deferimento (CF/DF), limitado a 60 dias da data de abertura do CNPJ.",
            "regra_retorno_exigencia": "Se houver pendencia cadastral impeditiva na SEEC-DF ou RFB dentro da janela de 30 dias, regularizar antes do decurso para nao perder o Simples no exercicio.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "SN-2026-DEFERIDO",
            "apontamento_auditoria": "Validar no simulador tributario (Estacao 4) como a segregacao NFS-e (6920-6/01 vs 6920-6/02) sera emitida na pratica.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 10, "bloco": "F", "codigo": "F1-F3,F5-F7",
            "nome_etapa": "Licenciamento Integrado no RLE-DF (8 Orgaos Integrados, Baixo Risco e Autodeclaracao)",
            "raia_responsavel": "orgaos_publicos",
            "orgao": "RLE / RedeSim-DF (Adm. Regional, CBMDF, DF Legal + triagem negativa DIVISA, IBRAM, SEAGRI, PCDF, DER/SEMOB)",
            "portal_url": "https://redesim.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Questionario de risco (<= 200 m2, escritorio paperless), Habite-se predial / CBMDF condominio e autodeclaracao assinada digitalmente.",
            "saida_doc": "Certificado de Licenciamento / Alvara Eletronico automatico sem vistoria previa + Termo de Ciencia e Responsabilidade arquivado.",
            "prazo_legal": "Imediato apos autodeclaracao; exige atualizacao previa em mudanca de endereco/CNAE/metragem.",
            "regra_retorno_exigencia": "Se fiscalizacao posterior (DF Legal / CBMDF) detectar divergencia nas condicoes autodeclaradas, sanear no prazo da notificacao sob pena de cassacao.",
            "classificacao_risco": "baixo",
            "protocolo_simulado": "RLE-LIC-2026-DF",
            "apontamento_auditoria": "Listar explicitamente os 8 orgaos do DF e seus respectivos papeis para cumprir o Bloco F da Matriz.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 11, "bloco": "F", "codigo": "F4",
            "nome_etapa": "Desvio Condicional — Atividades de Alto Risco (NA para Prisma JRNA / Aplicavel a Clientes Risco III)",
            "raia_responsavel": "orgaos_publicos",
            "orgao": "CBMDF / DIVISA / IBRAM-DF (Res. CGSIM 57/2020 — Risco III)",
            "portal_url": "https://redesim.df.gov.br",
            "data_consulta": "2026-08-13",
            "entrada_docs": "Projeto tecnico contra incendio/sanitario/ambiental e laudos exigidos quando o CNAE/porte enquadrar-se em Alto Risco.",
            "saida_doc": "Justificativa formal de Nao Aplicavel (F4 = NA) no dossie da Prisma JRNA; vistoria previa antes da operacao para clientes Risco III.",
            "prazo_legal": "Previo ao funcionamento (quando aplicavel a Risco III)",
            "regra_retorno_exigencia": "Em caso de inclusao futura de CNAE de alto risco, bloquear operacao ate conclusao de vistoria presencial e emissao de licença definitiva.",
            "classificacao_risco": "alto_na",
            "protocolo_simulado": "F4-NA-BAIXO-RISCO",
            "apontamento_auditoria": "Confirmar classificacao F4 = NA na avaliacao da Matriz de Fluxo de Abertura.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 12, "bloco": "G", "codigo": "G1",
            "nome_etapa": "Registro Cadastral da Organizacao Contabil e Vinculo de RT no CRC-DF",
            "raia_responsavel": "escritorio_contabil",
            "orgao": "Conselho Regional de Contabilidade do Distrito Federal — CRC-DF (DL 9.295/46; Res. CFC 1.708/2023)",
            "portal_url": "https://www.crcdf.org.br/registro/registro-de-organizacoes-contabeis/",
            "data_consulta": "2026-08-12",
            "entrada_docs": "Requerimento digital, Contrato Social chancelado + NIRE, CNPJ/QSA, RG/CPF/comprovante das socias, Certidao CRP da RT e Termo de Responsabilidade Tecnica.",
            "saida_doc": "Certidao de Registro Cadastral da PJ (CRC-DF 004.821/O-2) vinculando Nathalia Peres Araujo como RT.",
            "prazo_legal": "Obrigatorio antes do anuncio e execucao de servicos contabeis privativos.",
            "regra_retorno_exigencia": "Havendo exigencia cadastral sobre composicao societaria ou regularidade de RT, regularizar antes de emitir balancos/declaracoes.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "CRC-DF-004821-O2",
            "apontamento_auditoria": "Validar se numero simulado CRC-DF 004.821/O-2 e CRC-DF 025.431/O-7 estao consistentes com Cadastro e Contrato.",
            "referencia_v1_original": "Q4 original dizia erroneamente que o registro cadastral era concedido 'no CFC'.",
        },
        {
            "ordem": 13, "bloco": "G", "codigo": "G2-G4",
            "nome_etapa": "Obrigacoes Iniciais (eSocial S-1000/S-1005, FGTS Digital, Abertura Contabil e Calendario Fiscal)",
            "raia_responsavel": "escritorio_contabil",
            "orgao": "eSocial / FGTS Digital / PGDAS-D / DCTFWeb / Sistema ERP Contabil (ITG 2000; CC art. 1.179)",
            "portal_url": "https://www.gov.br/esocial/pt-br",
            "data_consulta": "2026-08-14",
            "entrada_docs": "e-CNPJ A1, Tabela de Rubricas (S-1010 p/ pro-labore M4+), Plano de Contas, Balanco de Abertura M0 (R$ 40k) e procuracoes eletronicas.",
            "saida_doc": "Eventos S-1000 (Classif. Trib. 01), DCTFWeb Sem Movimento (M1-M3), Livro Diario/Razao abertos e calendario de PGDAS-D/DEFIS/anuidades.",
            "prazo_legal": "eSocial/DCTFWeb ate dia 15; PGDAS-D/DAS/GFD ate dia 20 do mes seguinte; DEFIS ate 31/03.",
            "regra_retorno_exigencia": "Divergencia entre trava de pro-labore e eSocial/DCTFWeb exige retificacao imediata de eventos S-1200/DCTFWeb.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "ESOCIAL-S1000-2026",
            "apontamento_auditoria": "Verificar consistencia do Balanco de Abertura M0 (Caixa 30k + Imobilizado 10k = Capital 40k) com Estacao 4.",
            "referencia_v1_original": ref_v1,
        },
        {
            "ordem": 14, "bloco": "G,H", "codigo": "G5,H1-H7",
            "nome_etapa": "Governanca LGPD/NBC PG 01, Cadeia de Evidencias e Arquivamento Digital Paperless",
            "raia_responsavel": "socias",
            "orgao": "Controle Interno Prisma JRNA / ANPD (Lei 13.709/2018) / NBC PG 01",
            "portal_url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
            "data_consulta": "2026-08-14",
            "entrada_docs": "Todas as evidencias das etapas 1 a 13 (DFP, DBE, Contrato JUCIS-DF, CNPJ, CF/DF, Simples, RLE, CRC-DF, eSocial).",
            "saida_doc": "Prontuario digital criptografado com 2FA, cadeia completa de rastreabilidade e diagrama BPMN padronizado (Figura unica).",
            "prazo_legal": "Continuo a partir do Go-Live",
            "regra_retorno_exigencia": "Auditoria interna bloqueia inicio do atendimento ao primeiro cliente caso falte qualquer evidencia da cadeia.",
            "classificacao_risco": "regulatorio",
            "protocolo_simulado": "PRONTUARIO-D1-OK",
            "apontamento_auditoria": "Assegurar na exportacao que o diagrama BPMN caiba em uma pagina (Matriz Fluxo H7).",
            "referencia_v1_original": ref_v1,
        },
    ]


def importar_dossie1_quarentena(nath_dir: Path = DEFAULT_NATH_DIR) -> dict[str, Any]:
    """Importa insumos de G:\\Meu Drive\\Nath\\Trabalho 01 em quarentena no lab_contabil."""
    plan_base = nath_dir / "_planejamento" / "dossie1_base"
    v2_dir = nath_dir / "_entrega_limpa_Dossie1"
    for p in (plan_base, v2_dir):
        if not p.exists():
            raise FileNotFoundError(f"Diretorio de origem D1 nao encontrado: {p}")

    txt_dev = (plan_base / "orig_Devolutiva_Dossie1_G07.md").read_text(encoding="utf-8")
    txt_cs_v1 = (plan_base / "orig_Contrato_Social_Atualizado.md").read_text(encoding="utf-8")
    txt_mou_v1 = (plan_base / "orig_Memorando_Entendimentos_Atualizado.md").read_text(encoding="utf-8")
    txt_cs_v2 = (v2_dir / "03_Contrato_Social_PRISMA_JRNA.md").read_text(encoding="utf-8")
    txt_mou_v2 = (v2_dir / "04_Memorando_de_Entendimentos_MOU_PRISMA_JRNA.md").read_text(encoding="utf-8")
    txt_pesq_v2 = (v2_dir / "01_Pesquisa_Registro_Profissional_e_Redesim_DF.md").read_text(encoding="utf-8")
    txt_ia_v2 = (v2_dir / "06_Declaracao_Uso_Inteligencia_Artificial_Dossie1.md").read_text(encoding="utf-8")

    cs_orig_map = parse_clausulas_originais_contrato(txt_cs_v1)
    cs_v2_list = parse_clausulas_v2_contrato(txt_cs_v2)
    mou_orig_map = parse_clausulas_originais_mou(txt_mou_v1)
    mou_v2_list = parse_clausulas_v2_mou(txt_mou_v2)
    questoes_v2, decisoes_v2 = parse_pesquisa_v2(txt_pesq_v2)
    crit_v1_map, criticas_secao = parse_criticas_devolutiva(txt_dev)
    ia_rows = parse_diario_ia(txt_ia_v2)

    counts: dict[str, int] = {}
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.empresa WHERE chave = 'emp:prisma_jrna_g07'")
            row_emp = cur.fetchone()
            if not row_emp:
                raise RuntimeError("Empresa 'emp:prisma_jrna_g07' nao encontrada em erp.empresa. Execute migrar_para_pg antes.")
            emp_id = int(row_emp["id"])

            # 1. Governanca da empresa + Cadastro de Socias, Identificadores, Sede e Enquadramento
            cur.execute(
                """
                UPDATE erp.empresa
                SET status_validacao = CASE
                        WHEN status_validacao IN ('homologado_contadora', 'alerta_inconsistencia') THEN status_validacao
                        ELSE 'pendente_revisao'
                    END,
                    referencia_v1_original = COALESCE(referencia_v1_original, 'PRISMA JRNA AUDITORIA E CONTABILIDADE LTDA. (Contrato Atualizado 15/09/2026 sem CNPJ/endereco completo)'),
                    apontamento_auditoria = COALESCE(apontamento_auditoria, 'Validar dados cadastrais didaticos herdados do rascunho v2 e confirmar objeto social (Contabilidade + Auditoria).')
                WHERE id = %s AND origem_registro <> 'usuario' AND status_validacao <> 'homologado_contadora'
                """,
                (emp_id,),
            )

            # Pessoas PF (Nathalia e Jeovanna)
            pessoas_pf = [
                ("pes:pf:nathalia_peres_araujo", "PF", "Nathalia Peres Araujo", "importado_rascunho_v2", "pendente_revisao",
                 "Qualificacao v1: [INSERIR RG], [INSERIR CPF], [INSERIR ENDERECO COMPLETO], CRC-DF [INSERIR NUMERO].",
                 "RG 3.451.892 SSP/DF, CPF 041.825.911-04 e CRC-DF 025.431/O-7 sao dados didaticos do rascunho v2; confirmar se mantem como simulacao ou altera."),
                ("pes:pf:jeovanna_ripardo_lustosa", "PF", "Jeovanna Ripardo Lustosa", "importado_rascunho_v2", "pendente_revisao",
                 "Qualificacao v1: [INSERIR RG], [INSERIR CPF], [INSERIR ENDERECO COMPLETO].",
                 "RG 3.672.410 SSP/DF, CPF 052.734.621-18 e SQN 210 sao dados didaticos do rascunho v2; confirmar antes da entrega."),
            ]
            execute_values(
                cur,
                """
                INSERT INTO erp.pessoa (chave, tipo_pessoa, nome_canonico, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                pessoas_pf,
            )
            cur.execute("SELECT chave, id FROM erp.pessoa WHERE chave IN ('pes:pj:prisma_jrna_g07', 'pes:pf:nathalia_peres_araujo', 'pes:pf:jeovanna_ripardo_lustosa')")
            pid_by_chave = {str(r["chave"]): int(r["id"]) for r in cur.fetchall()}

            idents = [
                ("pid:g07:pj:cnpj", pid_by_chave["pes:pj:prisma_jrna_g07"], "CNPJ", "48.123.456/0001-90", True, "nath:03_Contrato_Social", "importado_rascunho_v2", "pendente_revisao", "v1 sem CNPJ preenchido.", "CNPJ ficticio padronizado com D2 (Rota Sul); confirmar se aceita na defesa."),
                ("pid:g07:pj:crc", pid_by_chave["pes:pj:prisma_jrna_g07"], "CRC", "CRC-DF 004.821/O-2", True, "nath:01_Pesquisa", "importado_rascunho_v2", "pendente_revisao", "v1 nao citava numero de registro cadastral PJ.", "Numero didatico padronizado no rascunho v2."),
                ("pid:g07:nath:crc", pid_by_chave["pes:pf:nathalia_peres_araujo"], "CRC", "CRC-DF 025.431/O-7", True, "nath:03_Contrato_Social", "importado_rascunho_v2", "pendente_revisao", "v1 constava 'CRC-DF [INSERIR NUMERO]'.", "CRC-DF herdado de D2/rascunho v2; confirmar responsabilidade tecnica exclusiva."),
                ("pid:g07:nath:cpf", pid_by_chave["pes:pf:nathalia_peres_araujo"], "CPF", "041.825.911-04", True, "nath:03_Contrato_Social", "importado_rascunho_v2", "pendente_revisao", "v1 constava '[INSERIR CPF]'.", "CPF ficticio didatico (validar politica da disciplina sobre dados simulados)."),
                ("pid:g07:nath:rg", pid_by_chave["pes:pf:nathalia_peres_araujo"], "OUTRO", "RG 3.451.892 SSP/DF | SQS 308 Bl. C Apto 402", True, "nath:03_Contrato_Social", "importado_rascunho_v2", "pendente_revisao", "v1 constava '[INSERIR RG]' e '[INSERIR ENDERECO COMPLETO]'.", "Dado civil ficticio didatico."),
                ("pid:g07:jeo:cpf", pid_by_chave["pes:pf:jeovanna_ripardo_lustosa"], "CPF", "052.734.621-18", True, "nath:03_Contrato_Social", "importado_rascunho_v2", "pendente_revisao", "v1 constava '[INSERIR CPF]'.", "CPF ficticio didatico."),
                ("pid:g07:jeo:rg", pid_by_chave["pes:pf:jeovanna_ripardo_lustosa"], "OUTRO", "RG 3.672.410 SSP/DF | SQN 210 Bl. F Apto 204", True, "nath:03_Contrato_Social", "importado_rascunho_v2", "pendente_revisao", "v1 constava '[INSERIR RG]' e '[INSERIR ENDERECO COMPLETO]'.", "Dado civil ficticio didatico."),
            ]
            execute_values(
                cur,
                """
                INSERT INTO erp.pessoa_identificador
                    (chave, pessoa_id, tipo_id, valor, eh_ficticio, fonte_chave, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                idents,
            )
            counts["erp.pessoa_identificador"] = len(idents)

            estab = (
                "est:prisma_jrna:matriz",
                emp_id,
                "matriz",
                "48.123.456/0001-90",
                "DF",
                "Brasilia",
                "Setor Comercial Sul (SCS), Quadra 06, Bloco A, Lote 157, 6º andar, sala 901, Asa Sul, CEP 70.390-000",
                "importado_rascunho_v2",
                "pendente_revisao",
                "v1: 'Asa Sul, 6º andar, sala 901, CEP XX.XXX.XXX'.",
                "Logradouro completo no SCS e CEP 70.390-000 foram padronizados para fins didaticos (RA-I Plano Piloto / LUOS). Validar se deseja manter ou alterar.",
            )
            cur.execute(
                """
                INSERT INTO erp.estabelecimento
                    (chave, empresa_id, tipo, cnpj, uf, municipio, endereco, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chave) DO NOTHING
                """,
                estab,
            )

            parts = [
                ("part:g07:nathalia", emp_id, pid_by_chave["pes:pf:nathalia_peres_araujo"], 20000, 2000000, 500000,
                 "Socia Administradora / RT", "2026-09-15", None, "nath:03_Contrato_Social", "importado_v1", "pendente_revisao",
                 "v1 Cl. 4ª e 9ª: 20.000 quotas (50%), administracao isolada (alcada R$ 15k) e RT CRC-DF.",
                 "Paridade 50/50 exige mecanismo expresso de desempate (deadlock) e coerencia entre Contrato e MoU."),
                ("part:g07:jeovanna", emp_id, pid_by_chave["pes:pf:jeovanna_ripardo_lustosa"], 20000, 2000000, 500000,
                 "Socia Quotista / Diretora de Operacoes", "2026-09-15", None, "nath:03_Contrato_Social", "importado_v1", "pendente_revisao",
                 "v1 Cl. 4ª: 20.000 quotas (50%), funcao operacional no Plano de Negocios.",
                 "Confirmar se assinara exclusivamente junto acima de R$ 15.000 e regras de vesting 24 meses."),
            ]
            execute_values(
                cur,
                """
                INSERT INTO erp.participacao_societaria
                    (chave, empresa_id, socio_pessoa_id, quotas, valor_centavos, percentual_micro, papel, vigente_de, vigente_ate, fonte_chave, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                parts,
            )
            counts["erp.participacao_societaria"] = len(parts)

            # Atualiza enq:g07:2026 sem sobrescrever edicoes do usuario
            cur.execute(
                """
                UPDATE erp.enquadramento_historico
                SET responsavel_tecnico_pessoa_id = COALESCE(responsavel_tecnico_pessoa_id, %s),
                    registro_crc = CASE WHEN registro_crc = 'DF-SIMULADO-G07' THEN 'CRC-DF 004.821/O-2' ELSE registro_crc END,
                    regime_tributario = CASE WHEN origem_registro = 'acervo_sigaa' THEN 'Simples_Misto' ELSE regime_tributario END,
                    status_validacao = CASE
                        WHEN status_validacao IN ('homologado_contadora', 'alerta_inconsistencia') THEN status_validacao
                        ELSE 'pendente_revisao'
                    END,
                    referencia_v1_original = COALESCE(referencia_v1_original, %s),
                    apontamento_auditoria = COALESCE(apontamento_auditoria, %s)
                WHERE chave = 'enq:g07:2026' AND origem_registro <> 'usuario' AND status_validacao <> 'homologado_contadora'
                """,
                (
                    pid_by_chave["pes:pf:nathalia_peres_araujo"],
                    "Contrato v1 citava apenas CNAE 6920-6/01 omitindo 6920-6/02 (Auditoria); Plano v1 falava em Anexo III/IV a 6% fixo e ME constante.",
                    "Validar CNAEs (6920-6/01 + 6920-6/02), Fator R nos Anexos III/V e transicao legal ME -> EPP no Ano 2 (> R$ 360k).",
                ),
            )

            # 2. Instrumentos Societarios (Contrato Social + MoU em visao integrada + conflitos v1 destacados)
            clausulas_rows: list[tuple[Any, ...]] = []
            ordem_cs = 1
            for cl in cs_v2_list:
                num = cl["numero"]
                orig_txt = cs_orig_map.get(num, "Clausula ausente ou resumida na versao v1.")
                # Mapeia metadados estruturados por clausula para o validador de coerencia
                metodo_haveres = "balanco_determinacao" if num == 18 else "nao_aplicavel"
                quorum_tipo = "unanimidade" if num == 12 else ("judicial" if num == 16 else ("gestao_ordinaria" if num == 9 else "nao_aplicavel"))
                alcada = 1500000 if num == 9 else None

                apont = "Revisar redacao frente a Matriz de Contrato Social e homologar."
                if num == 1:
                    apont = "Endereco SCS Q. 06 e CEP 70.390-000 inseridos em rascunho_v2 (v1 usava CEP XX.XXX.XXX)."
                elif num == 2:
                    apont = "CORRECAO v2: incluiu CNAE secundario 6920-6/02 (Auditoria/Consultoria) ausente na v1."
                elif num == 3:
                    apont = "CORRECAO v2: alterou inicio de atividades da 'data de assinatura' para 'data de registro na JUCIS-DF' + citou transicao ME->EPP."
                elif num == 9:
                    apont = "Conferir alcada de R$ 15.000,00 com MoU Cl. 5ª."
                elif num == 11:
                    apont = "Trava de pro-labore 90 dias impacta diretamente o Fator R (< 28% no Ano 1). Confirmar com Planejamento Financeiro!"
                elif num == 12:
                    apont = "CORRECAO v2: incluiu regra de impasse 50/50 (mediacao 15d -> Acordo/Shotgun -> art. 1.030 CC). Na v1 o quorum de >50% era matematicamente impossivel."
                elif num == 16:
                    apont = "CORRECAO v2: exclusao em 50/50 remetida a via judicial (art. 1.030 CC) e prazo de defesa 5 dias uteis quando houver maioria (art. 1.085 CC)."
                elif num == 18:
                    apont = "PONTO CRITICO v1: Contrato v1 usava Balanco de Determinacao enquanto MoU v1 e V3 usavam FCD! Confirmar escolha unica pelo Balanco de Determinacao (36x + IPCA + carencia 180d)."
                elif num == 22:
                    apont = "CORRECAO v2: substituiu dissolucao em 180d pela continuidade em Sociedade Limitada Unipessoal (SLU — Lei 13.874/2019)."

                clausulas_rows.append((
                    f"inst:cs:{num:02d}", emp_id, ordem_cs, f"CS-CAP-{num:02d}", f"CS-CL-{num:02d}",
                    f"Contrato Cl. {num}ª", cl["titulo"], cl["texto"],
                    False, True, None, cl["texto"],
                    metodo_haveres, quorum_tipo, alcada, 2,
                    "importado_rascunho_v2", "pendente_revisao", orig_txt, apont, None,
                ))
                ordem_cs += 1

            mou_v1_lookup = {
                1: mou_orig_map.get("PRIMEIRA", "Ausente na v1."),
                2: "Bloco B ausente na v1.",
                3: mou_orig_map.get("SEGUNDA", "Na v1 nao havia vesting nem mora/aportes futuros."),
                4: mou_orig_map.get("TERCEIRA", "") + " " + mou_orig_map.get("SEXTA", ""),
                5: "Na v1 havia apenas administracao exclusiva sem alcada R$ 15k nem matriz de unanimidade.",
                6: "Bloco F (reservas/lucros/despesas/entidade) ausente na v1.",
                7: mou_orig_map.get("SETIMA", "Confidencialidade sem prazo e non-compete amplo demais na v1."),
                8: mou_orig_map.get("QUARTA", "") + " " + mou_orig_map.get("QUINTA", ""),
                9: "Bloco I (etica, CRC-DF, conflito de interesses, DL 9.295) ausente na v1 (nota 0,0/4).",
                10: "Na v1 faltava matriz de coerencia MoU x Contrato x Plano.",
            }
            for cl in mou_v2_list:
                num = cl["numero"]
                apont_m = f"Reconstrucao do MoU (v1 teve nota 2,8). Verificar aderencia integral ao Contrato Social e ao Bloco {cl['bloco']}."
                metodo_haveres = "balanco_determinacao" if num == 8 else "nao_aplicavel"
                quorum_tipo = "unanimidade" if num == 5 else "nao_aplicavel"
                alcada = 1500000 if num == 5 else None
                if num == 3:
                    apont_m = "Incluiu reverse vesting 24m (cliff 6m), aportes futuros e regra para terceiros/familiares (ausentes na v1)."
                elif num == 4:
                    apont_m = "Explicitou trava 90d, pro-labore M4-M12 (R$ 4.500/mes) e distincao entre pro-labore e lucros."
                elif num == 8:
                    apont_m = "CRITICO: Substituiu FCD 5 anos (MoU v1 Cl. 5ª) por Balanco de Determinacao para zerar conflito com Contrato Social Cl. 18ª!"
                clausulas_rows.append((
                    f"inst:mou:{num:02d}", emp_id, 100 + num, f"MOU-{cl['bloco']}", f"MOU-{cl['bloco']}1",
                    f"MoU Cl. {num}ª", cl["titulo"], cl["texto"],
                    True, False, cl["texto"], None,
                    metodo_haveres, quorum_tipo, alcada, 2,
                    "importado_rascunho_v2", "pendente_revisao", mou_v1_lookup.get(num, "").strip(), apont_m, None,
                ))

            execute_values(
                cur,
                """
                INSERT INTO erp.instrumento_societario_clausula
                    (chave, empresa_id, ordem, bloco, codigo_criterio, numero_clausula, titulo, regra_texto,
                     aplica_mou, aplica_contrato, redacao_mou, redacao_contrato, metodo_haveres, quorum_tipo,
                     alcada_centavos, versao, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria, justificativa_contadora)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                clausulas_rows,
            )
            counts["erp.instrumento_societario_clausula"] = len(clausulas_rows)

            # 3. Processo Paralegal DF (14 etapas Redesim / JUCIS-DF / SEEC-DF / RLE / CRC-DF)
            etapas = _build_etapas_legalizacao_df()
            execute_values(
                cur,
                """
                INSERT INTO erp.processo_legalizacao_etapa
                    (chave, empresa_id, ordem, bloco, codigo, nome_etapa, raia_responsavel, orgao, portal_url,
                     data_consulta, entrada_docs, saida_doc, prazo_legal, regra_retorno_exigencia, classificacao_risco,
                     status, protocolo_simulado, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                [
                    (
                        f"leg:df:{e['ordem']:02d}", emp_id, e["ordem"], e["bloco"], e["codigo"],
                        e["nome_etapa"], e["raia_responsavel"], e["orgao"], e["portal_url"], e["data_consulta"],
                        e["entrada_docs"], e["saida_doc"], e["prazo_legal"], e["regra_retorno_exigencia"],
                        e["classificacao_risco"], "pendente", e["protocolo_simulado"],
                        "importado_rascunho_v2", "pendente_revisao", e["referencia_v1_original"], e["apontamento_auditoria"],
                    )
                    for e in etapas
                ],
            )
            counts["erp.processo_legalizacao_etapa"] = len(etapas)

            # 4. Consultas Normativas (Q1..Q10) + Decisoes Preliminares
            criticas_q = {
                1: "v1 listava apenas tipos de registro sem requisitos (bacharelado, Exame de Suficiencia, documentos).",
                4: "v1 afirmava incorretamente que o registro cadastral e concedido 'no CFC' (e no CRC-DF).",
                5: "v1 nao explicava a funcao pratica e legal da Responsabilidade Tecnica.",
                6: "v1 copiou a lista do site do CRC-DF letra por letra (proibido).",
                7: "DF nao tem prefeitura: validar papel da Adm. Regional (LUOS) vs JUCIS-DF.",
                9: "ATENCAO ANTI-ENVIESAMENTO: resposta v2 vincula o split 85%/15% de CNAEs criado no rascunho; contadora deve confirmar ou alterar.",
                10: "ATENCAO ANTI-ENVIESAMENTO: duvida tecnica depende da premissa de segregacao de NFS-e nos 90 dias sem pro-labore.",
            }
            execute_values(
                cur,
                """
                INSERT INTO erp.consulta_normativa
                    (chave, empresa_id, numero_questao, enunciado, resposta_autoral, norma_citada, link_oficial,
                     data_acesso, decisao_impactada, origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                [
                    (
                        f"cons:q{q['numero_questao']:02d}", emp_id, q["numero_questao"], q["enunciado"],
                        q["resposta_autoral"], q["norma_citada"], q["link_oficial"], q["data_acesso"],
                        q["decisao_impactada"], "importado_rascunho_v2", "pendente_revisao",
                        "Arquivo original .docx ausente em _referencia/Dossie_1; Devolutiva atribuiu nota 5,0 na v1.",
                        criticas_q.get(q["numero_questao"], "Validar redacao autoral com palavras proprias, link oficial vigente e data de acesso."),
                    )
                    for q in questoes_v2
                ],
            )
            counts["erp.consulta_normativa"] = len(questoes_v2)

            execute_values(
                cur,
                """
                INSERT INTO erp.empresa_decisao_preliminar
                    (chave, empresa_id, ordem, elemento, opcao_adotada, alternativas_consideradas, justificativa_documental,
                     origem_registro, status_validacao, referencia_v1_original, apontamento_auditoria)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                [
                    (
                        f"decpre:{d['ordem']:02d}", emp_id, d["ordem"], d["elemento"], d["opcao_adotada"],
                        d["alternativas_consideradas"], d["justificativa_documental"],
                        "importado_rascunho_v2", "pendente_revisao",
                        "Na v1 faltava definicao final do publico-alvo e pendencia de viabilidade estava aberta.",
                        "Confirmar coerencia com Cadastro Societario e Plano de Negocios.",
                    )
                    for d in decisoes_v2
                ],
            )
            counts["erp.empresa_decisao_preliminar"] = len(decisoes_v2)

            # 5. Cenarios Financeiros e Tributarios em Quarentena (4 teses comparaveis)
            cur.execute("SELECT 1 FROM erp.orcamento_cenario WHERE empresa_id = %s AND eh_oficial = true LIMIT 1", (emp_id,))
            ja_tem_oficial = cur.fetchone() is not None
            cenarios = [
                (
                    "orc:v2_segregacao", emp_id, "v2_segregacao",
                    "Simulacao rascunho_v2 (Segregacao 85% 6920-6/01 III + 15% 6920-6/02 Fator R)",
                    "simples_segregado", not ja_tem_oficial, 36, 4000000, 1000000, 1200000, 1500000, 200000,
                    150000, 2, 50000, 30000, 50000, 24, 150000, 200000, 850000,
                    300000, 650000, 950000, 0, 450000, 700000, 1000000,
                    1000000, 2520000, 296400,
                    json.dumps({"fonte": "02_Plano_Financeiro_PRISMA_JRNA.xlsx", "premissa_d2_amostra_n": None}, ensure_ascii=False),
                    "importado_rascunho_v2", "pendente_revisao",
                    "Plano v1 usava DAS 6% fixo, sem 5% inadimplencia, sem CLT discriminado em Y2-Y3 e sem Balanco Patrimonial.",
                    "ATENCAO ANTI-ENVIESAMENTO: divisao 85%/15% foi inserida por IA no rascunho v2 para acomodar pro-labore R$ 0 em M1-M3. Nota na aba 2 (linha 31) cita ~6,08 clientes quando o calculo E30 resulta em 5,92. Homologar apenas apos comparar com Fator R Global!",
                ),
                (
                    "orc:stress_fator_r_global", emp_id, "stress_fator_r_global",
                    "Stress Test (Sem Segregacao CNAE: 100% sujeito ao Fator R — Anexo V se < 28%)",
                    "simples_fator_r_global", False, 36, 4000000, 1000000, 1200000, 1500000, 200000,
                    150000, 2, 50000, 30000, 50000, 24, 150000, 200000, 0,
                    300000, 650000, 950000, 0, 450000, 700000, 1000000,
                    1000000, 2520000, 296400,
                    json.dumps({"finalidade": "Comparativo caso o fisco/banca rejeite segregacao 85/15"}, ensure_ascii=False),
                    "importado_rascunho_v2", "alerta_inconsistencia",
                    "Devolutiva v1 alertou que pro-labore 0 (M1-M3) e R$ 4.500 (M4-M12) mantem Fator R < 28% no Ano 1.",
                    "Cenario de estresse: demonstra quanto custa de DAS (15,5%+) caso nao seja feita segregacao em NFS-e para o CNAE 6920-6/01.",
                ),
                (
                    "orc:planejamento_prolabore_28", emp_id, "planejamento_prolabore_28",
                    "Planejamento Tributario (Ajuste de Pro-Labore >= 28% desde o M1 p/ garantir Anexo III)",
                    "simples_auto_prolabore_28", False, 36, 4000000, 1000000, 1200000, 1500000, 200000,
                    150000, 2, 50000, 30000, 50000, 24, 150000, 200000, 0,
                    300000, 650000, 950000, 0, 450000, 700000, 1000000,
                    1000000, 2520000, 296400,
                    json.dumps({"finalidade": "Alternativa sem trava de 90d caso prefiram Fator R >= 28% desde M1"}, ensure_ascii=False),
                    "importado_rascunho_v2", "pendente_revisao",
                    "Alternativa tecnica a trava de 90 dias prevista na Cl. 10/11 do Contrato.",
                    "Simula pro-labore minimo mensal = 28% da receita para enquadramento integral no Anexo III sem depender de segregacao.",
                ),
                (
                    "orc:v1_historico_6pct", emp_id, "v1_historico_6pct",
                    "Linha Base Historica v1 (Erro Original: DAS 6% fixo + 10% Var., sem PDD 5%)",
                    "v1_fixo_6_erro", False, 36, 4000000, 1000000, 0, 0, 200000,
                    150000, 2, 0, 100000, 0, 24, 150000, 200000, 1000000,
                    300000, 1250000, 1833333, 0, 450000, 0, 0,
                    0, 0, 296400,
                    json.dumps({"fonte": "orig_Extracao_Financeira_v1.xlsx (apenas historico de auditoria)"}, ensure_ascii=False),
                    "importado_v1", "alerta_inconsistencia",
                    "Entrega v1 (Plano Atualizado + Consolidado): DAS fixo 6%, custos variaveis 10%, Ano 2 OPEX 150k e Ano 3 OPEX 220k.",
                    "NAO USAR COMO OFICIAL: mantido apenas como referencia historica para a contadora visualizar os erros tributarios e aritmeticos da v1.",
                ),
            ]
            execute_values(
                cur,
                """
                INSERT INTO erp.orcamento_cenario (
                    chave, empresa_id, codigo_cenario, nome, regime_simulacao, eh_oficial, horizonte_meses,
                    capital_social_centavos, capex_m0_centavos, capex_ano2_centavos, capex_ano3_centavos,
                    taxa_depreciacao_anual_micro, ticket_medio_centavos, novos_clientes_mes, inadimplencia_micro,
                    custo_variavel_micro, cac_centavos, retencao_meses, tma_anual_micro, taxa_reserva_lucros_micro,
                    pct_cnae_principal_micro, opex_fixo_ano1_mensal_centavos, opex_fixo_ano2_mensal_centavos,
                    opex_fixo_ano3_mensal_centavos, prolabore_m1_3_mensal_centavos, prolabore_m4_12_mensal_centavos,
                    prolabore_ano2_mensal_centavos, prolabore_ano3_mensal_centavos, folha_clt_ano2_mensal_centavos,
                    folha_clt_ano3_mensal_centavos, encargos_clt_micro, premissas_json, origem_registro,
                    status_validacao, referencia_v1_original, apontamento_auditoria
                ) VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                cenarios,
            )
            counts["erp.orcamento_cenario"] = len(cenarios)

            # 6. Avaliacao de Conformidade (200 criterios em quarentena — nota atual NULL ate contadora avaliar!)
            cur.execute("SELECT id, matriz, codigo FROM auditoria.criterio_conformidade ORDER BY matriz, id")
            criterios = cur.fetchall()
            av_rows = []
            for cr in criterios:
                mat = str(cr["matriz"])
                cod = str(cr["codigo"])
                nota_v1, crit_v1 = crit_v1_map.get((mat, cod), (None, None))
                if mat == "fluxo_abertura" and crit_v1 is None:
                    nota_v1 = 0
                    crit_v1 = "Fluxo de Abertura nao entregue na v1 (Nota 0,0/10 — perda de 2,0 pts na Entrega)."
                av_rows.append((
                    f"av:g07:{mat}:{cod}", emp_id, int(cr["id"]), nota_v1, None, False, None,
                    crit_v1, None, "importado_v1", "pendente_revisao", "Devolutiva G07 / Quarentena",
                ))
            execute_values(
                cur,
                """
                INSERT INTO auditoria.avaliacao_conformidade
                    (chave, empresa_id, criterio_id, nota_v1, nota, nao_aplicavel, referencia_localizacao,
                     critica_v1, justificativa_sustentacao, origem_registro, status_validacao, autor)
                VALUES %s ON CONFLICT (chave) DO NOTHING
                """,
                av_rows,
            )
            counts["auditoria.avaliacao_conformidade"] = len(av_rows)

            # 7. Diario de IA (D1) em quarentena
            diario_rows = [
                (
                    f"ia:d1:{i:02d}", "D1", emp_id, row["finalidade"],
                    f"Revisao D1 — {row['entregavel']} ({row['houve_uso']})",
                    row["fonte_oficial"], row["revisao_humana"], "Grupo G07 (Quarentena)",
                    row["entregavel"], "Assistente IA", "importado_rascunho_v2", "pendente_revisao",
                )
                for i, row in enumerate(ia_rows, start=1)
            ]
            if diario_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO auditoria.diario_ia
                        (chave, dossie, empresa_id, finalidade, prompt_resumo, fonte_oficial, revisao_humana, autor,
                         entregavel, ferramenta, origem_registro, status_validacao)
                    VALUES %s ON CONFLICT (chave) DO NOTHING
                    """,
                    diario_rows,
                )
            counts["auditoria.diario_ia"] = len(diario_rows)

        conn.commit()

    # Secoes narrativas dos documentos (Plano, preambulos, anexos) — tambem em quarentena
    from sistema.erp.importar_secoes_dossie1 import importar_secoes_dossie1

    for doc, qtd in importar_secoes_dossie1(v2_dir).items():
        counts[f"erp.documento_secao:{doc}"] = qtd
    return counts


if __name__ == "__main__":
    res = importar_dossie1_quarentena()
    print("Importacao em quarentena Dossie 1 concluida:", res)
