"""Camada 2 (Fase 4) — Extracao integral dos materiais do curso (D1-D4 e _paginas)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

_MAX_BLOCOS_POR_SECAO_SEM_HEADING = 40


@dataclass
class _LinhaCurso:
    id: int
    pagina: int
    n_linha: int
    texto: str
    eh_marca_dagua: int


@dataclass
class _ParagrafoCurso:
    id: int
    ordem: int
    origem_bloco: str
    estilo: str | None
    texto: str


def _classificar_categoria_pdf(nome: str) -> str:
    if "Plano_de_Ensino" in nome:
        return "plano_ensino"
    if "Estudo_de_Caso" in nome or nome.startswith(("01_NFSe", "02_Enunciado")):
        return "estudo_caso"
    return "aula"


def _classificar_categoria_texto(caminho_rel: str, nome: str, dossie: str) -> str:
    if "Devolutiva_Dossie" in caminho_rel:
        return "devolutiva"
    if "Matriz_de_Requisitos" in nome:
        return "matriz_requisitos"
    if dossie == "_paginas":
        return "pagina_sigaa"
    if "Pesquisa_Orientada" in nome or "Atividade_Dossie4" in nome:
        return "orientacao"
    return "orientacao"


def _titulo_limpo(nome: str, primeiro_texto: str | None) -> str:
    if primeiro_texto:
        limpo = " ".join(primeiro_texto.split()).strip()
        if 3 <= len(limpo) <= 140:
            return limpo
    return nome.rsplit(".", 1)[0].replace("_", " ").strip()


def extrair_curso(conn: sqlite3.Connection) -> dict[str, int]:
    """Extrai 100% dos PDFs nao-D4 (bru_linha) e arquivos de texto/DOCX/HTML (bru_paragrafo)."""
    n_materiais = 0
    n_secoes = 0
    n_linhas_marcadas = 0
    n_paragrafos_marcados = 0

    linhas_updates: list[tuple[str, int]] = []
    par_updates: list[tuple[str, int]] = []

    # 1. PDFs fora do D4 (13 arquivos em D1, D2, D3 com linhas ainda sem destino)
    pdfs_curso = conn.execute(
        """
        SELECT DISTINCT a.id, a.caminho_relativo, a.nome, a.dossie
        FROM bru_arquivo a
        JOIN bru_linha l ON l.arquivo_id = a.id
        WHERE a.dossie IN ('D1', 'D2', 'D3')
          AND a.extensao = '.pdf'
          AND a.papel_acervo = 'primario'
        ORDER BY a.caminho_relativo
        """
    ).fetchall()

    for arq_id, rel, nome, dossie in pdfs_curso:
        rows = conn.execute(
            """
            SELECT id, pagina, n_linha, texto, eh_marca_dagua
            FROM bru_linha
            WHERE arquivo_id = ?
            ORDER BY pagina, n_linha
            """,
            (arq_id,),
        ).fetchall()
        linhas = [
            _LinhaCurso(id=int(r[0]), pagina=int(r[1]), n_linha=int(r[2]), texto=str(r[3]), eh_marca_dagua=int(r[4]))
            for r in rows
        ]
        por_pag: dict[int, list[_LinhaCurso]] = {}
        first_txt: str | None = None
        for ln in linhas:
            if ln.eh_marca_dagua:
                linhas_updates.append(("marca_dagua", ln.id))
                n_linhas_marcadas += 1
                continue
            if first_txt is None and ln.texto.strip():
                first_txt = ln.texto.strip()
            por_pag.setdefault(ln.pagina, []).append(ln)

        cat = _classificar_categoria_pdf(str(nome))
        chave_mat = f"extmat:{rel}"
        cur = conn.execute(
            """
            INSERT INTO ext_material (chave, arquivo_id, dossie, categoria, titulo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chave_mat, arq_id, dossie, cat, _titulo_limpo(str(nome), first_txt)),
        )
        mat_id = int(cur.lastrowid)
        n_materiais += 1

        for ordem_idx, pag in enumerate(sorted(por_pag), start=1):
            grupo = por_pag[pag]
            textos = [g.texto.strip() for g in grupo if g.texto.strip()]
            titulo_sec = textos[0][:140] if textos else f"Página {pag}"
            conteudo_sec = "\n".join(textos) if textos else f"[Página {pag}]"
            chave_sec = f"extsec:{rel}:P{pag:03d}"
            conn.execute(
                """
                INSERT INTO ext_secao (chave, material_id, ordem, titulo, conteudo, linha_bruto_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chave_sec, mat_id, ordem_idx, titulo_sec, conteudo_sec, grupo[0].id),
            )
            dest = f"ext_secao:{chave_sec}"
            for g in grupo:
                linhas_updates.append((dest, g.id))
                n_linhas_marcadas += 1
            n_secoes += 1

    # 2. Arquivos DOCX, HTML, TXT e .2026 em bru_paragrafo (62 arquivos, 15.090 paragrafos)
    docs_texto = conn.execute(
        """
        SELECT DISTINCT a.id, a.caminho_relativo, a.nome, a.dossie
        FROM bru_arquivo a
        JOIN bru_paragrafo p ON p.arquivo_id = a.id
        WHERE a.papel_acervo = 'primario'
        ORDER BY a.caminho_relativo
        """
    ).fetchall()

    for arq_id, rel, nome, dossie in docs_texto:
        rows = conn.execute(
            """
            SELECT id, ordem, origem_bloco, estilo, texto
            FROM bru_paragrafo
            WHERE arquivo_id = ?
            ORDER BY ordem
            """,
            (arq_id,),
        ).fetchall()
        blocos = [
            _ParagrafoCurso(
                id=int(r[0]),
                ordem=int(r[1]),
                origem_bloco=str(r[2]),
                estilo=str(r[3]) if r[3] is not None else None,
                texto=str(r[4]),
            )
            for r in rows
        ]
        first_txt = next((b.texto.strip() for b in blocos if b.texto.strip()), None)
        cat = _classificar_categoria_texto(str(rel), str(nome), str(dossie))
        chave_mat = f"extmat:{rel}"
        cur = conn.execute(
            """
            INSERT INTO ext_material (chave, arquivo_id, dossie, categoria, titulo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chave_mat, arq_id, dossie, cat, _titulo_limpo(str(nome), first_txt)),
        )
        mat_id = int(cur.lastrowid)
        n_materiais += 1

        # Segmenta em secoes por Heading/Title ou janela de blocos
        grupos: list[list[_ParagrafoCurso]] = []
        atual: list[_ParagrafoCurso] = []
        for b in blocos:
            est = (b.estilo or "").strip()
            eh_titulo = est.startswith(("Heading", "Title")) or est in ("h1", "h2", "h3")
            if atual and (eh_titulo or len(atual) >= _MAX_BLOCOS_POR_SECAO_SEM_HEADING):
                grupos.append(atual)
                atual = [b]
            else:
                atual.append(b)
        if atual:
            grupos.append(atual)

        for ordem_idx, grupo in enumerate(grupos, start=1):
            textos = [g.texto.strip() for g in grupo if g.texto.strip()]
            titulo_sec = textos[0][:140] if textos else f"Seção {ordem_idx}"
            conteudo_sec = "\n".join(textos) if textos else ""
            chave_sec = f"extsec:{rel}:S{ordem_idx:03d}"
            conn.execute(
                """
                INSERT INTO ext_secao (chave, material_id, ordem, titulo, conteudo, paragrafo_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chave_sec, mat_id, ordem_idx, titulo_sec, conteudo_sec, grupo[0].id),
            )
            dest = f"ext_secao:{chave_sec}"
            for g in grupo:
                par_updates.append((dest, g.id))
                n_paragrafos_marcados += 1
            n_secoes += 1

    if linhas_updates:
        conn.executemany("UPDATE bru_linha SET destino = ? WHERE id = ?", linhas_updates)
    if par_updates:
        conn.executemany("UPDATE bru_paragrafo SET destino = ? WHERE id = ?", par_updates)

    return {
        "materiais": n_materiais,
        "secoes": n_secoes,
        "linhas_curso_marcadas": n_linhas_marcadas,
        "paragrafos_marcados": n_paragrafos_marcados,
    }
