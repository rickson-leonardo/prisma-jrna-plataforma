"""Importa em quarentena as secoes narrativas dos documentos do Dossie 1 (erp.documento_secao).

Somente leitura na origem (G:\\Meu Drive\\Nath\\Trabalho 01\\_entrega_limpa_Dossie1).
Tudo entra como origem 'importado_rascunho_v2' e status 'pendente_revisao': a contadora revisa,
edita via CRUD (/emissao) e homologa. Reimportar nunca sobrescreve edicoes (ON CONFLICT DO NOTHING).

O que NAO e importado (porque vem vivo do banco/motor):
- Secao 8 do Plano de Negocios (numeros financeiros -> motor_contabil.py);
- Clausulas do Contrato/MoU (erp.instrumento_societario_clausula);
- Etapas A-H do Fluxo (erp.processo_legalizacao_etapa), BPMN e cadeia de evidencias;
- Q1-Q10 e decisoes preliminares (erp.consulta_normativa / erp.empresa_decisao_preliminar).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sistema.pg.db import conectar_pg

DEFAULT_V2_DIR = Path(r"G:\Meu Drive\Nath\Trabalho 01\_entrega_limpa_Dossie1")
EMPRESA_CHAVE = "emp:prisma_jrna_g07"

APONT_PADRAO = (
    "Texto importado do rascunho v2 (_entrega_limpa_Dossie1). Conferir premissas, afirmacoes e fontes "
    "antes de homologar; este texto ainda nao foi validado pela contadora."
)
APONT_NUMEROS = (
    " Contem valores monetarios/percentuais digitados no rascunho: substitua por marcadores vivos "
    "(ex.: {{RECEITA_A1}}, {{VPL}}, {{TIR}}) para sincronizar com o motor contabil."
)


def _limpar(md: str) -> str:
    """Remove blocos mermaid (o BPMN e gerado do banco), links para .md/.xlsx e separadores soltos."""
    md = re.sub(r"```mermaid.*?```\s*", "", md, flags=re.S)
    md = re.sub(r"\[`?([^\]`]+?)`?\]\((?:\.\./)?[^)]+\.(?:md|xlsx|pdf)\)", r"\1", md)
    md = re.sub(r"\n-{3,}\s*$", "", md.strip())
    return md.strip()


def _secoes_h2(texto: str) -> list[tuple[str, str]]:
    """Divide um markdown em (titulo_h2, corpo) mantendo subsecoes ### no corpo."""
    partes = re.split(r"^## +(.+)$", texto, flags=re.M)
    return [(partes[i].strip(), partes[i + 1]) for i in range(1, len(partes), 2)]


def _ate(corpo: str, marcador: str) -> str:
    i = corpo.find(marcador)
    return corpo[:i] if i >= 0 else corpo


def parse_plano_negocios(texto: str) -> list[dict[str, Any]]:
    out = []
    for titulo, corpo in _secoes_h2(texto):
        m = re.match(r"(\d+)\.\s*(.+)", titulo)
        if not m:
            continue
        num = int(m.group(1))
        if num == 8:  # Plano financeiro: gerado ao vivo pelo motor contabil
            continue
        out.append({"ordem": num, "codigo_secao": f"S{num:02d}", "titulo": m.group(2).strip(), "conteudo_md": _limpar(corpo)})
    return out


def parse_contrato(texto: str) -> list[dict[str, Any]]:
    secs = dict(_secoes_h2(texto))
    out = []
    pre = next((c for t, c in secs.items() if t.upper().startswith("PREÂMBULO")), "")
    if pre:
        out.append({"ordem": 1, "codigo_secao": "preambulo", "titulo": "Preâmbulo e qualificação das sócias", "conteudo_md": _limpar(pre)})
    cap8 = next((c for t, c in secs.items() if "CAPÍTULO VIII" in t.upper()), "")
    m = re.search(r"(E, por estarem.*?)(?:\n\*\*_{5,})", cap8, flags=re.S)
    if m:
        out.append({"ordem": 2, "codigo_secao": "encerramento", "titulo": "Fecho, local e data", "conteudo_md": _limpar(m.group(1))})
    anexos = next((c for t, c in secs.items() if t.upper().startswith("ANEXOS")), "")
    if anexos:
        out.append({"ordem": 3, "codigo_secao": "anexos", "titulo": "Anexos integrantes do ato constitutivo (I a IV)", "conteudo_md": _limpar(anexos)})
    return out


def parse_memorando(texto: str) -> list[dict[str, Any]]:
    secs = dict(_secoes_h2(texto))
    out = []
    pre = next((c for t, c in secs.items() if t.upper().startswith("PREÂMBULO")), "")
    if pre:
        out.append({"ordem": 1, "codigo_secao": "preambulo", "titulo": "Preâmbulo e qualificação das partes", "conteudo_md": _limpar(pre)})
    cl10 = next((c for t, c in secs.items() if t.upper().startswith("CLÁUSULA 10")), "")
    m = re.search(r"(E, por estarem.*?)(?:\n\*\*_{5,})", cl10, flags=re.S)
    if m:
        out.append({"ordem": 2, "codigo_secao": "encerramento", "titulo": "Fecho, local e data", "conteudo_md": _limpar(m.group(1))})
    return out


def parse_fluxo(texto: str) -> list[dict[str, Any]]:
    out = []
    m = re.search(r"^> \*\*Escopo:\*\*.*$", texto, flags=re.M)
    if m:
        out.append({"ordem": 1, "codigo_secao": "apresentacao", "titulo": "Escopo do documento", "conteudo_md": m.group(0)[2:].strip()})
    secs = _secoes_h2(texto)
    bloco_f = next((c for t, c in secs if t.startswith("6.")), "")
    sub = re.split(r"^### +(.+)$", bloco_f, flags=re.M)
    for i in range(1, len(sub), 2):
        tit = sub[i].strip()
        if tit.startswith("6.1"):
            out.append({"ordem": 2, "codigo_secao": "F_orgaos", "titulo": "Os oito órgãos licenciadores integrados à RedeSim-DF", "conteudo_md": _limpar(sub[i + 1])})
        elif tit.startswith("6.2"):
            out.append({"ordem": 3, "codigo_secao": "F_risco", "titulo": "Classificação de risco e consequências procedimentais", "conteudo_md": _limpar(sub[i + 1])})
    refs = next((c for t, c in secs if t.startswith("9.")), "")
    if refs:
        out.append({"ordem": 9, "codigo_secao": "referencias", "titulo": "Referências oficiais e técnicas", "conteudo_md": _limpar(refs)})
    return out


def parse_pesquisa(texto: str) -> list[dict[str, Any]]:
    secs = _secoes_h2(texto)
    ia = next((c for t, c in secs if t.startswith("3.")), "")
    return [{"ordem": 1, "codigo_secao": "ia_pesquisa", "titulo": "Registro de uso de inteligência artificial (Pesquisa — Aula 02)", "conteudo_md": _limpar(ia)}] if ia else []


def parse_indice(texto: str) -> list[dict[str, Any]]:
    secs = _secoes_h2(texto)
    evo = next((c for t, c in secs if t.startswith("2.")), "")
    return [{"ordem": 1, "codigo_secao": "evolucao_v1", "titulo": "Evolução frente à devolutiva docente (v1)", "conteudo_md": _limpar(evo)}] if evo else []


ARQUIVOS = (
    ("indice", "00_Indice_Geral_Dossie1_PRISMA_JRNA.md", parse_indice),
    ("pesquisa", "01_Pesquisa_Registro_Profissional_e_Redesim_DF.md", parse_pesquisa),
    ("plano_negocios", "02_Plano_de_Negocios_PRISMA_JRNA.md", parse_plano_negocios),
    ("contrato_social", "03_Contrato_Social_PRISMA_JRNA.md", parse_contrato),
    ("memorando", "04_Memorando_de_Entendimentos_MOU_PRISMA_JRNA.md", parse_memorando),
    ("fluxo_abertura", "05_Fluxo_Abertura_Empresa_DF_Redesim_e_BPMN.md", parse_fluxo),
)


def importar_secoes_dossie1(v2_dir: Path = DEFAULT_V2_DIR) -> dict[str, int]:
    """Carrega as secoes narrativas em quarentena. Retorna quantidade lida por documento."""
    contagem: dict[str, int] = {}
    if not v2_dir.exists():
        return contagem
    with conectar_pg() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM erp.empresa WHERE chave = %s", (EMPRESA_CHAVE,))
            row = cur.fetchone()
            if not row:
                return contagem
            emp_id = int(row["id"])
            for documento, arquivo, parser in ARQUIVOS:
                p = v2_dir / arquivo
                if not p.exists():
                    continue
                secoes = parser(p.read_text(encoding="utf-8"))
                contagem[documento] = len(secoes)
                for s in secoes:
                    apont = APONT_PADRAO + (APONT_NUMEROS if re.search(r"R\$\s?\d|\d+,\d+\s?%", s["conteudo_md"]) else "")
                    cur.execute(
                        """
                        INSERT INTO erp.documento_secao
                            (chave, empresa_id, documento, ordem, codigo_secao, titulo, conteudo_md,
                             origem_registro, status_validacao, apontamento_auditoria)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'importado_rascunho_v2', 'pendente_revisao', %s)
                        ON CONFLICT (chave) DO NOTHING
                        """,
                        (
                            f"docsec:d1:{documento}:{s['codigo_secao']}", emp_id, documento, s["ordem"],
                            s["codigo_secao"], s["titulo"], s["conteudo_md"], apont,
                        ),
                    )
        conn.commit()
    return contagem


if __name__ == "__main__":
    print("Secoes narrativas importadas em quarentena:", importar_secoes_dossie1())
