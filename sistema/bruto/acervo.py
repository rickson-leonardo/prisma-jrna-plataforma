"""Camada 1 — Inventario, hashes, ZIPs, SIGAA e extracao bruta fiel (PDF/XLSX/DOCX/HTML/TXT)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sqlite3
import unicodedata
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import docx
import openpyxl
import pymupdf

from sistema.config import PASTAS_ACERVO

# Mapeamento deterministico dos rotulos amigaveis do SIGAA em _relatorio.txt para o caminho relativo no disco
SIGAA_ALIASES: dict[str, str] = {
    "CCA0174_Laboratório_Contábil_Plano_de_Ensino": "D1/2026_2_Plano_de_Ensino_CCA0174_Laboratrio_Contbil.pdf",
    "Aula 01": "D1/Aula_01_Laboratorio_Contabil_CCA_0174.pdf",
    "Aula 02": "D1/Aula_02_Laboratorio_Contabil_CCA_0174.pdf",
    "Pesquisa_Orientada_Aula_02_Dossie_1_CCA_0174 .docx": "D1/Pesquisa_Orientada_Aula_02_Dossie_1_CCA_0174_.docx",
    "Artigo Tributação sobre dividendos": "D1/TributaoSobreDividendos.pdf",
    "Estudo Guiado 19.08.2026.pdf": "D1/Estudo_Guiado_19.08.2026.pdf",
    "Aula 08": "D1/Aula_08_Laboratorio_Contabil_CCA_0174_.pdf",
    "Matriz Plano de Negócios": "D1/Matriz_de_Requisitos_-_Plano_de_Negocios_-_Laboratorio_Contabil_CCA_0174.docx",
    "Matriz Memorando Entendimento dos Sócios": "D1/Matriz_de_Requisitos_-_Memorando_de_Entendimento_dos_Socios_-_CCA_0174.docx",
    "Matriz Contrato Social": "D1/Matriz_de_Requisitos_-_Contrato_Social_-_CCA_0174.docx",
    "Matriz Fluxo de Abertura de Empresas": "D1/Matriz_de_Requisitos_-_Fluxo_de_Abertura_de_Empresas_no_DF_-_CCA_0174.docx",
    "Folha de Pagamento": "D2/Aulas_DP_Admissao_Folha_Fechamento_2026_Atualizado_IRRF_.pdf",
    "Escrita Fiscal": "D3/Aula_17_a_19_Setor_Fiscal.pdf",
    "Modelo_Mapeamento_Tributário": "D3/Anlise_Tributria_Modelo.xlsx",
    "Fechamento Fiscal": "D3/Aula_22_Fechamento_Fiscal.pdf",
    "Auditoria Fiscal -  NFSe": "D3/01_NFSe_Ficticia_Auditoria_Ente_Federal.pdf",
    "Individuais_parte3_2025-10_a_2026-01 (1).zip": "D4/Individuais_parte3_2025-10_a_2026-01_1.zip",
    "Individuais_parte5_2026-06_a_2026-08 (2).zip": "D4/Individuais_parte5_2026-06_a_2026-08_2.zip",
}


class _SigaaHtmlParser(HTMLParser):
    """Extrai o fieldset principal (#conteudo) e paineis de noticias/atividades do HTML do SIGAA."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_conteudo = False
        self._conteudo_depth = 0
        self._in_barra_dir = False
        self._barra_depth = 0
        self._in_script_or_style = False
        self._in_th = False
        self._in_td = False
        self._in_form_ava = False
        self._form_ava_depth = 0
        self._cur_label: str = ""
        self._cur_val_parts: list[str] = []
        self.form_ava_campos: list[tuple[str, str]] = []
        self.blocos_laterais: list[str] = []
        self._lateral_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        tag_l = tag.lower()
        if tag_l in ("script", "style"):
            self._in_script_or_style = True
            return

        if tag_l == "div" and attr_map.get("id") == "conteudo":
            self._in_conteudo = True
            self._conteudo_depth = 1
        elif self._in_conteudo and tag_l == "div":
            self._conteudo_depth += 1

        if tag_l == "div" and attr_map.get("id") == "barraDireita":
            self._in_barra_dir = True
            self._barra_depth = 1
        elif self._in_barra_dir and tag_l == "div":
            self._barra_depth += 1

        if self._in_conteudo and tag_l == "table" and "formAva" in (attr_map.get("class") or ""):
            self._in_form_ava = True
            self._form_ava_depth = 1
        elif self._in_form_ava and tag_l == "table":
            self._form_ava_depth += 1

        if self._in_form_ava:
            if tag_l == "th":
                self._in_th = True
                self._cur_label = ""
            elif tag_l == "td":
                self._in_td = True
                self._cur_val_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l in ("script", "style"):
            self._in_script_or_style = False
            return

        if self._in_form_ava:
            if tag_l == "th":
                self._in_th = False
            elif tag_l == "td":
                self._in_td = False
                valor = " ".join("".join(self._cur_val_parts).replace("\xa0", " ").split())
                rotulo = " ".join(self._cur_label.replace("\xa0", " ").split())
                self.form_ava_campos.append((rotulo, valor))
            elif tag_l == "table":
                self._form_ava_depth -= 1
                if self._form_ava_depth <= 0:
                    self._in_form_ava = False

        if self._in_conteudo and tag_l == "div":
            self._conteudo_depth -= 1
            if self._conteudo_depth <= 0:
                self._in_conteudo = False

        if self._in_barra_dir and tag_l == "div":
            self._barra_depth -= 1
            if self._barra_depth <= 0:
                self._in_barra_dir = False

    def handle_data(self, data: str) -> None:
        if self._in_script_or_style:
            return
        if self._in_th:
            self._cur_label += data
        elif self._in_td:
            self._cur_val_parts.append(data)
        elif self._in_barra_dir:
            txt = " ".join(data.replace("\xa0", " ").split())
            if txt and txt not in ("(Visualizar)", "Nenhuma enquete encontrada", "Nenhuma avaliação cadastrada", "Não há mensagens cadastradas"):
                self._lateral_parts.append(txt)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _inferir_dominio(rel_posix: str, dossie: str) -> str:
    if dossie == "D4":
        if rel_posix.endswith("Atividade_Dossie4_Doc1_SN_Reforma_Tributaria_ALUNOS.docx"):
            return "misto"
        return "empresa"
    if dossie == "D1":
        if rel_posix.endswith("Balancete_Abertura_31-12-2024.xlsx"):
            return "empresa"
        return "curso"
    if dossie in ("D2", "D3"):
        if rel_posix in (
            "D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf",
            "D3/01_NFSe_Ficticia_Auditoria_Ente_Federal.pdf",
            "D3/02_Enunciado_Auditoria_NFSe_Ente_Federal.pdf",
            "D3/Anlise_Tributria_Modelo.xlsx",
        ):
            return "misto"
        return "curso"
    if dossie == "_paginas":
        if "ROTA SUL" in rel_posix:
            return "misto"
        return "curso"
    return "curso"


def _eh_marca_dagua(texto: str, cor_hex: str | None = None, tam_fonte: float = 0.0) -> bool:
    s = texto.strip()
    if cor_hex in ("0xb41e1e", "0x8a1c1c"):
        return True
    if cor_hex == "0xffffff" and tam_fonte == 6.0 and "fictício" in s.lower():
        return True
    if s in ("DOCUMENTO DIDÁTICO", "SEM VALOR FISCAL"):
        return True
    if s.startswith("DOCUMENTO DIDÁTICO – SEM VALOR FISCAL"):
        return True
    if s.startswith("DOCUMENTO DIDÁTICO - SEM VALOR FISCAL"):
        return True
    return False


def _fmt_celula(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, dt.datetime):
        return val.date().isoformat()
    if isinstance(val, dt.date):
        return val.isoformat()
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    return str(val)


def _normalizar_nome(s: str) -> str:
    s_nfd = unicodedata.normalize("NFD", s)
    sem_acento = "".join(ch for ch in s_nfd if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", sem_acento.lower())


def _coletar_arquivos(acervo_dir: Path) -> list[tuple[str, Path, str]]:
    """Lista ordenada de (caminho_relativo_posix, Path, dossie) nas pastas do acervo."""
    itens: list[tuple[str, Path, str]] = []
    for pasta in PASTAS_ACERVO:
        raiz = acervo_dir / pasta
        if not raiz.exists():
            continue
        for p in raiz.rglob("*"):
            if p.is_file():
                rel = p.relative_to(acervo_dir).as_posix()
                itens.append((rel, p, pasta))
    itens.sort(key=lambda x: x[0])
    return itens


def _popular_bru_arquivo(
    conn: sqlite3.Connection, acervo_dir: Path
) -> dict[str, tuple[int, str, str, Path, str]]:
    """Preenche bru_arquivo, identifica duplicatas e retorna mapa rel -> (id, chave, sha256, path, papel)."""
    arquivos = _coletar_arquivos(acervo_dir)
    info_por_rel: dict[str, tuple[int, str, str, Path, str]] = {}
    d1_por_sha: dict[str, int] = {}

    # 1a passada: inserir todos sem duplicata_de_id (para resolver FK em seguida)
    for rel, path, dossie in arquivos:
        sha = _sha256_arquivo(path)
        ext = path.suffix.lower()
        tamanho = path.stat().st_size
        dominio = _inferir_dominio(rel, dossie)
        if ext == ".zip":
            papel = "container_zip"
        elif dossie == "D4" and path.name.endswith("_consolidado.pdf"):
            papel = "consolidado_espelho"
        elif rel == "D4/Balancetes_Verificacao_Mensais_2025-2026.pdf":
            papel = "formato_espelho"
        else:
            papel = "primario"

        chave = f"arq:{rel}"
        cur = conn.execute(
            """
            INSERT INTO bru_arquivo (
                chave, caminho_relativo, nome, extensao, sha256, tamanho_bytes,
                dossie, dominio, papel_acervo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chave, rel, path.name, ext, sha, tamanho, dossie, dominio, papel),
        )
        arq_id = int(cur.lastrowid)
        info_por_rel[rel] = (arq_id, chave, sha, path, papel)
        if dossie == "D1" and sha not in d1_por_sha:
            d1_por_sha[sha] = arq_id

    # 2a passada: marcar duplicatas de Resultado/ em relacao a D1/
    for rel, (arq_id, chave, sha, path, papel) in list(info_por_rel.items()):
        if rel.startswith("Resultado/") and sha in d1_por_sha:
            orig_id = d1_por_sha[sha]
            conn.execute(
                "UPDATE bru_arquivo SET papel_acervo = 'duplicata_sha256', duplicata_de_id = ? WHERE id = ?",
                (orig_id, arq_id),
            )
            info_por_rel[rel] = (arq_id, chave, sha, path, "duplicata_sha256")

    return info_por_rel


def _popular_zips(
    conn: sqlite3.Connection,
    info_por_rel: dict[str, tuple[int, str, str, Path, str]],
) -> int:
    """Inspeciona todos os ZIPs primarios (D1 e D4) e mapeia para os arquivos descompactados."""
    por_sha_e_dossie: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for rel, (arq_id, _, sha, _, papel) in info_por_rel.items():
        if papel != "container_zip":
            dossie = rel.split("/", 1)[0]
            por_sha_e_dossie.setdefault((dossie, sha), []).append((arq_id, rel))

    total_entradas = 0
    for rel, (zip_id, _, _, path, papel) in sorted(info_por_rel.items()):
        if papel != "container_zip":
            continue
        dossie = rel.split("/", 1)[0]
        with zipfile.ZipFile(path, "r") as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                if info.is_dir():
                    continue
                dados = zf.read(info.filename)
                sha_ent = _sha256_bytes(dados)
                candidatos = por_sha_e_dossie.get((dossie, sha_ent), [])
                arq_disco_id: int | None = None
                if len(candidatos) == 1:
                    arq_disco_id = candidatos[0][0]
                elif len(candidatos) > 1:
                    nome_ent = Path(info.filename).name
                    for cand_id, cand_rel in candidatos:
                        if Path(cand_rel).name == nome_ent:
                            arq_disco_id = cand_id
                            break
                    if arq_disco_id is None:
                        arq_disco_id = candidatos[0][0]

                chave_ent = f"zip:{rel}:{info.filename}"
                conn.execute(
                    """
                    INSERT INTO bru_zip_entrada (
                        chave, zip_arquivo_id, caminho_interno, tamanho_bytes,
                        crc32, sha256, arquivo_disco_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (chave_ent, zip_id, info.filename, info.file_size, info.CRC, sha_ent, arq_disco_id),
                )
                if arq_disco_id is not None:
                    conn.execute(
                        "UPDATE bru_arquivo SET zip_origem_id = ? WHERE id = ? AND zip_origem_id IS NULL",
                        (zip_id, arq_disco_id),
                    )
                total_entradas += 1
    return total_entradas


def _extrair_pdfs(
    conn: sqlite3.Connection,
    info_por_rel: dict[str, tuple[int, str, str, Path, str]],
) -> int:
    """Extrai todas as linhas de todos os PDFs via pymupdf com geometria e tipografia."""
    total_linhas = 0
    batch: list[tuple[Any, ...]] = []

    for rel, (arq_id, _, _, path, papel) in sorted(info_por_rel.items()):
        if path.suffix.lower() != ".pdf" or papel == "duplicata_sha256":
            continue
        with pymupdf.open(path) as doc:
            n_paginas = len(doc)
            conn.execute("UPDATE bru_arquivo SET paginas_total = ? WHERE id = ?", (n_paginas, arq_id))
            for pag_idx, page in enumerate(doc, start=1):
                n_linha = 0
                for block in page.get_text("dict")["blocks"]:
                    if block.get("type") != 0:
                        continue
                    for ln in block.get("lines", []):
                        spans = ln.get("spans", [])
                        texto = "".join(sp.get("text", "") for sp in spans)
                        n_linha += 1
                        bbox = ln.get("bbox", (0.0, 0.0, 0.0, 0.0))
                        x0 = round(float(bbox[0]), 1)
                        y0 = round(float(bbox[1]), 1)
                        if spans:
                            sp0 = spans[0]
                            tam_fonte = round(float(sp0.get("size", 0.0)), 1)
                            fonte = str(sp0.get("font", ""))
                            cor_hex = f"0x{int(sp0.get('color', 0)):06x}"
                        else:
                            tam_fonte = 0.0
                            fonte = ""
                            cor_hex = "0x000000"

                        eh_md = 1 if _eh_marca_dagua(texto, cor_hex, tam_fonte) else 0
                        destino = "marca_dagua" if eh_md else None
                        chave_lin = f"lin:{rel}:{pag_idx}:{n_linha}"
                        batch.append(
                            (chave_lin, arq_id, pag_idx, n_linha, texto, x0, y0, tam_fonte, fonte, cor_hex, eh_md, destino)
                        )
                        total_linhas += 1
                        if len(batch) >= 10000:
                            conn.executemany(
                                """
                                INSERT INTO bru_linha (
                                    chave, arquivo_id, pagina, n_linha, texto,
                                    x0, y0, tam_fonte, fonte, cor_hex, eh_marca_dagua, destino
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                batch,
                            )
                            batch.clear()

    if batch:
        conn.executemany(
            """
            INSERT INTO bru_linha (
                chave, arquivo_id, pagina, n_linha, texto,
                x0, y0, tam_fonte, fonte, cor_hex, eh_marca_dagua, destino
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
    return total_linhas


def _extrair_planilhas(
    conn: sqlite3.Connection,
    info_por_rel: dict[str, tuple[int, str, str, Path, str]],
) -> int:
    """Extrai todas as celulas nao vazias dos arquivos .xlsx preservando formula e valor cacheado."""
    total_celulas = 0
    batch: list[tuple[Any, ...]] = []

    for rel, (arq_id, _, _, path, papel) in sorted(info_por_rel.items()):
        if path.suffix.lower() != ".xlsx" or papel == "duplicata_sha256":
            continue
        wb_raw = openpyxl.load_workbook(path, data_only=False)
        wb_val = openpyxl.load_workbook(path, data_only=True)
        try:
            for ordem_aba, aba in enumerate(wb_raw.sheetnames, start=1):
                ws_raw = wb_raw[aba]
                ws_val = wb_val[aba]
                for r in range(1, ws_raw.max_row + 1):
                    for c in range(1, ws_raw.max_column + 1):
                        cel_raw = ws_raw.cell(r, c)
                        cel_val = ws_val.cell(r, c)
                        raw = cel_raw.value
                        cached = cel_val.value
                        if raw is None and cached is None:
                            continue

                        endereco = cel_raw.coordinate
                        fmt = cel_raw.number_format
                        if isinstance(raw, str) and raw.startswith("="):
                            tipo = "formula"
                            formula = raw
                            val_cache_str = _fmt_celula(cached)
                            val_texto = val_cache_str
                        elif isinstance(raw, (dt.datetime, dt.date)):
                            tipo = "data"
                            formula = None
                            val_texto = _fmt_celula(raw)
                            val_cache_str = val_texto
                        elif isinstance(raw, bool):
                            tipo = "booleano"
                            formula = None
                            val_texto = _fmt_celula(raw)
                            val_cache_str = val_texto
                        elif isinstance(raw, (int, float)):
                            tipo = "numero"
                            formula = None
                            val_texto = str(raw)
                            val_cache_str = val_texto
                        else:
                            tipo = "texto"
                            formula = None
                            val_texto = str(raw)
                            val_cache_str = val_texto

                        chave_cel = f"cel:{rel}:{aba}:{endereco}"
                        batch.append(
                            (
                                chave_cel,
                                arq_id,
                                aba,
                                ordem_aba,
                                r,
                                c,
                                endereco,
                                tipo,
                                val_texto,
                                val_cache_str,
                                formula,
                                fmt,
                                None,
                            )
                        )
                        total_celulas += 1
        finally:
            wb_raw.close()
            wb_val.close()

    if batch:
        conn.executemany(
            """
            INSERT INTO bru_celula (
                chave, arquivo_id, aba, ordem_aba, linha, coluna, endereco,
                tipo_dado, valor_texto, valor_cacheado, formula, formato_numero, destino
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
    return total_celulas


def _extrair_docx(
    conn: sqlite3.Connection,
    rel: str,
    arq_id: int,
    path: Path,
) -> int:
    """Extrai paragrafos e celulas de tabela de um .docx na ordem exata do documento."""
    doc = docx.Document(path)
    p_map = {p._element: p for p in doc.paragraphs}
    t_map = {t._element: t for t in doc.tables}
    ordem = 0
    tabela_idx = 0
    batch: list[tuple[Any, ...]] = []

    for child in doc.element.body:
        if child in p_map:
            p = p_map[child]
            texto = p.text.strip()
            if not texto:
                continue
            ordem += 1
            estilo = p.style.name if p.style else None
            batch.append(
                (f"par:{rel}:{ordem}", arq_id, ordem, "paragrafo", None, None, None, estilo, texto, None)
            )
        elif child in t_map:
            tabela_idx += 1
            tbl = t_map[child]
            for l_idx, row in enumerate(tbl.rows, start=1):
                seen_tc: set[int] = set()
                c_idx = 0
                for cell in row.cells:
                    if id(cell._tc) in seen_tc:
                        continue
                    seen_tc.add(id(cell._tc))
                    c_idx += 1
                    texto = "\n".join(ln.strip() for ln in cell.text.splitlines() if ln.strip())
                    if not texto:
                        continue
                    ordem += 1
                    batch.append(
                        (
                            f"par:{rel}:{ordem}",
                            arq_id,
                            ordem,
                            "tabela_celula",
                            tabela_idx,
                            l_idx,
                            c_idx,
                            None,
                            texto,
                            None,
                        )
                    )

    if batch:
        conn.executemany(
            """
            INSERT INTO bru_paragrafo (
                chave, arquivo_id, ordem, origem_bloco, tabela_idx, linha_idx, coluna_idx,
                estilo, texto, destino
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
    return ordem


def _extrair_paginas(
    conn: sqlite3.Connection,
    info_por_rel: dict[str, tuple[int, str, str, Path, str]],
) -> int:
    """Extrai blocos textuais dos arquivos .docx primarios e das paginas HTML/TXT em _paginas/."""
    total = 0
    for rel, (arq_id, chave_arq, _, path, papel) in sorted(info_por_rel.items()):
        ext = path.suffix.lower()
        if ext == ".docx" and papel == "primario":
            total += _extrair_docx(conn, rel, arq_id, path)
        elif rel == "_paginas/_relatorio.txt":
            linhas = path.read_text(encoding="utf-8").splitlines()
            ordem = 0
            for ln in linhas:
                s = ln.strip()
                if not s:
                    continue
                ordem += 1
                conn.execute(
                    """
                    INSERT INTO bru_paragrafo (
                        chave, arquivo_id, ordem, origem_bloco, estilo, texto, destino
                    ) VALUES (?, ?, ?, 'txt_linha', 'relatorio_sigaa', ?, NULL)
                    """,
                    (f"par:{rel}:{ordem}", arq_id, ordem, s),
                )
                total += 1
        elif rel.startswith("_paginas/") and ext in (".html", ".2026"):
            raw = path.read_bytes()
            texto_html = raw.decode("iso-8859-1", errors="replace")
            parser = _SigaaHtmlParser()
            parser.feed(texto_html)
            parser.close()

            ordem = 0
            conteudo_vazio = False
            for rotulo, valor in parser.form_ava_campos:
                ordem += 1
                conn.execute(
                    """
                    INSERT INTO bru_paragrafo (
                        chave, arquivo_id, ordem, origem_bloco, estilo, texto, destino
                    ) VALUES (?, ?, ?, 'html_bloco', 'formAva', ?, NULL)
                    """,
                    (f"par:{rel}:{ordem}", arq_id, ordem, f"{rotulo} {valor}".strip()),
                )
                total += 1
                if rotulo.lower().startswith("conte") and not valor:
                    conteudo_vazio = True

            if parser._lateral_parts:
                ordem += 1
                conn.execute(
                    """
                    INSERT INTO bru_paragrafo (
                        chave, arquivo_id, ordem, origem_bloco, estilo, texto, destino
                    ) VALUES (?, ?, ?, 'html_bloco', 'barraDireita', ?, NULL)
                    """,
                    (f"par:{rel}:{ordem}", arq_id, ordem, " | ".join(parser._lateral_parts)),
                )
                total += 1

            if conteudo_vazio:
                conn.execute(
                    """
                    INSERT INTO conferencia (
                        chave, regra, severidade, registros_json, valores_json, status, descricao
                    ) VALUES (?, 'sigaa_html_vazio', 'alerta', ?, ?, 'registrado', ?)
                    """,
                    (
                        f"conf:sigaa_html_vazio:{rel}",
                        json.dumps({"arquivo_chave": chave_arq, "caminho_relativo": rel}, ensure_ascii=False),
                        json.dumps({"campos": parser.form_ava_campos}, ensure_ascii=False),
                        f"Pagina HTML salva do SIGAA ({rel}) possui campo Conteudo vazio (&nbsp;).",
                    ),
                )
    return total


def _popular_sigaa(
    conn: sqlite3.Connection,
    acervo_dir: Path,
    info_por_rel: dict[str, tuple[int, str, str, Path, str]],
) -> int:
    """Mapeia os 135 itens de _paginas/_relatorio.txt para os arquivos locais em bru_arquivo."""
    rel_txt = acervo_dir / "_paginas" / "_relatorio.txt"
    if not rel_txt.exists():
        return 0

    por_nome_exato: dict[str, list[tuple[int, str]]] = {}
    por_norm: dict[str, list[tuple[int, str]]] = {}
    for rel, (arq_id, _, _, path, _) in sorted(info_por_rel.items()):
        por_nome_exato.setdefault(path.name, []).append((arq_id, rel))
        por_norm.setdefault(_normalizar_nome(path.name), []).append((arq_id, rel))

    linhas = [ln.strip() for ln in rel_txt.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rotulos_vistos: set[str] = set()

    for ordem, linha in enumerate(linhas, start=1):
        partes = [p.strip() for p in linha.split("|")]
        status = partes[0]
        content_type: str | None = None
        bytes_fetch: int | None = None
        link_texto: str | None = None
        rotulo: str
        obs: str | None = None

        if status == "200":
            content_type = partes[1]
            m_b = re.search(r"(\d+)", partes[2])
            bytes_fetch = int(m_b.group(1)) if m_b else None
            rotulo = partes[3]
            if len(partes) > 4 and partes[4].startswith("link:"):
                link_texto = partes[4].removeprefix("link:").strip()
        else:
            rotulo = partes[1]
            obs = partes[2] if len(partes) > 2 else None

        arq_id: int | None = None
        dossie_inf: str | None = None

        # 1. Caminho relativo direto (ex.: D1/Aula dia 18.08.2026)
        if f"_paginas/{rotulo}" in info_por_rel:
            arq_id = info_por_rel[f"_paginas/{rotulo}"][0]
            dossie_inf = "_paginas"
        elif rotulo in info_por_rel:
            arq_id = info_por_rel[rotulo][0]
            dossie_inf = rotulo.split("/", 1)[0]
        # 2. Alias explicito para titulos amigaveis do SIGAA
        elif rotulo in SIGAA_ALIASES and SIGAA_ALIASES[rotulo] in info_por_rel:
            rel_alvo = SIGAA_ALIASES[rotulo]
            arq_id = info_por_rel[rel_alvo][0]
            dossie_inf = rel_alvo.split("/", 1)[0]
        # 3. Nome exato de arquivo (se repetido no relatorio, prioriza Resultado/ na 2a ocorrencia)
        elif rotulo in por_nome_exato:
            cands = por_nome_exato[rotulo]
            if rotulo in rotulos_vistos and len(cands) > 1:
                escolhido = next((c for c in cands if c[1].startswith("Resultado/")), cands[-1])
                obs = "duplicata_no_relatorio"
            else:
                escolhido = next((c for c in cands if not c[1].startswith("Resultado/")), cands[0])
            arq_id = escolhido[0]
            dossie_inf = escolhido[1].split("/", 1)[0]
        # 4. Normalizado sem acentos/espacos
        else:
            norm = _normalizar_nome(rotulo)
            if norm in por_norm:
                escolhido = por_norm[norm][0]
                arq_id = escolhido[0]
                dossie_inf = escolhido[1].split("/", 1)[0]

        if rotulo in rotulos_vistos and obs is None:
            obs = "duplicata_no_relatorio"
        rotulos_vistos.add(rotulo)

        conn.execute(
            """
            INSERT INTO bru_sigaa_item (
                chave, ordem, status_fetch, content_type, bytes_fetch,
                rotulo_sigaa, link_texto, dossie_inferido, arquivo_id, observacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"sigaa:{ordem}",
                ordem,
                status,
                content_type,
                bytes_fetch,
                rotulo,
                link_texto,
                dossie_inf,
                arq_id,
                obs,
            ),
        )
    return len(linhas)


def executar_camada_bruta(conn: sqlite3.Connection, acervo_dir: Path) -> dict[str, int]:
    """Executa toda a Camada 1 sobre acervo_dir e retorna contagens consolidadas."""
    info_por_rel = _popular_bru_arquivo(conn, acervo_dir)
    n_zips = _popular_zips(conn, info_por_rel)
    n_linhas = _extrair_pdfs(conn, info_por_rel)
    n_celulas = _extrair_planilhas(conn, info_por_rel)
    n_paragrafos = _extrair_paginas(conn, info_por_rel)
    n_sigaa = _popular_sigaa(conn, acervo_dir, info_por_rel)

    return {
        "arquivos": len(info_por_rel),
        "zip_entradas": n_zips,
        "linhas_pdf": n_linhas,
        "celulas_xlsx": n_celulas,
        "paragrafos": n_paragrafos,
        "sigaa_itens": n_sigaa,
    }
