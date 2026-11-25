"""Camada 3 (Fase 6) — Resolucao de pessoas, empresas, estabelecimentos e historia temporal."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from sistema.qualidade.gates import _upsert_conferencia

_RE_DOC = re.compile(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})")
_CPF_CONFLITANTE = "77788899942"  # Compartilhado entre Helena Duarte Lima (CCB) e Tereza Cristina (pro-labore)


def _limpar_digits(val: str | None) -> str:
    if not val:
        return ""
    return re.sub(r"\D", "", val)


def _slug(txt: str) -> str:
    s = txt.lower().strip()
    rep = {
        "á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c", "–": "_", "-": "_",
    }
    for k, v in rep.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:48] or "sem_nome"


def _limpar_nome_impresso(s: str) -> str:
    txt = re.sub(r"\s*\(fictíci[ao]s?(?:\s+[^)]*)?\)", "", s, flags=re.I)
    txt = re.sub(r"\s*–\s*fictíci[ao]", "", txt, flags=re.I)
    return " ".join(txt.split()).strip(" |·-")


@dataclass
class ContextoEntidades:
    arq_chave_por_id: dict[int, str]
    lin_chave_por_id: dict[int, str]
    cel_chave_por_id: dict[int, str]
    par_chave_por_id: dict[int, str]
    pessoas_por_chave: dict[str, int] = field(default_factory=dict)
    empresas_por_chave: dict[str, int] = field(default_factory=dict)
    estabelecimentos_por_chave: dict[str, int] = field(default_factory=dict)
    estab_por_prefixo: dict[str, int] = field(default_factory=dict)
    contas_por_chave: dict[str, int] = field(default_factory=dict)
    pessoas_por_doc: dict[str, int] = field(default_factory=dict)
    pessoas_por_nome: dict[str, int] = field(default_factory=dict)
    _ident_chaves: set[str] = field(default_factory=set)
    _ocorr_chaves: set[str] = field(default_factory=set)
    _ev_seen: set[str] = field(default_factory=set)
    _ev_rows: list[tuple[str, str, str, str, str]] = field(default_factory=list)
    n_eventos: int = 0
    n_fatos: int = 0

    def add_ev(self, tabela_destino: str, registro_chave: str, bru_tabela: str, bru_chave: str) -> None:
        chave = f"ev:{tabela_destino}:{registro_chave}:{bru_chave}"
        if chave in self._ev_seen:
            return
        self._ev_seen.add(chave)
        self._ev_rows.append((chave, tabela_destino, registro_chave, bru_tabela, bru_chave))

    def flush_evidencias(self, conn: sqlite3.Connection) -> int:
        if self._ev_rows:
            conn.executemany(
                """
                INSERT OR IGNORE INTO evidencia (chave, tabela_destino, registro_chave, bru_tabela, bru_chave)
                VALUES (?, ?, ?, ?, ?)
                """,
                self._ev_rows,
            )
        n = len(self._ev_rows)
        self._ev_rows.clear()
        return n

    def garantir_pessoa(
        self,
        conn: sqlite3.Connection,
        chave: str,
        tipo_pessoa: str,
        nome_canonico: str,
        bru_tabela: str,
        bru_chave: str,
        ident_valor: str | None = None,
        tipo_id: str | None = None,
        papel: str | None = None,
        fonte_chave: str | None = None,
    ) -> int:
        if chave in self.pessoas_por_chave:
            pid = self.pessoas_por_chave[chave]
        else:
            cur = conn.execute(
                "INSERT INTO nrm_pessoa (chave, tipo_pessoa, nome_canonico) VALUES (?, ?, ?)",
                (chave, tipo_pessoa, nome_canonico),
            )
            pid = int(cur.lastrowid)
            self.pessoas_por_chave[chave] = pid
            self.pessoas_por_nome[_slug(nome_canonico)] = pid
            self.add_ev("nrm_pessoa", chave, bru_tabela, bru_chave)

        if ident_valor and tipo_id:
            dig = _limpar_digits(ident_valor)
            c_id = f"pid:{chave}:{tipo_id}:{dig or _slug(ident_valor)}"
            if c_id not in self._ident_chaves:
                self._ident_chaves.add(c_id)
                conn.execute(
                    """
                    INSERT INTO nrm_pessoa_identificador (chave, pessoa_id, tipo_id, valor, eh_ficticio, fonte_chave)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (c_id, pid, tipo_id, ident_valor.strip(), fonte_chave or bru_chave),
                )
                self.add_ev("nrm_pessoa_identificador", c_id, bru_tabela, bru_chave)
            if dig and dig != _CPF_CONFLITANTE:
                self.pessoas_por_doc.setdefault(dig, pid)

        if papel:
            c_oc = f"poc:{chave}:{papel}:{_slug(fonte_chave or bru_chave)[:24]}"
            if c_oc not in self._ocorr_chaves:
                self._ocorr_chaves.add(c_oc)
                conn.execute(
                    """
                    INSERT INTO nrm_pessoa_ocorrencia (chave, pessoa_id, nome_impresso, identificador_impresso, papel, fonte_chave)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (c_oc, pid, nome_canonico, ident_valor, papel, fonte_chave or bru_chave),
                )
                self.add_ev("nrm_pessoa_ocorrencia", c_oc, bru_tabela, bru_chave)
        return pid

    def resolver_ou_criar_contraparte(
        self,
        conn: sqlite3.Connection,
        nome_raw: str,
        doc_raw: str | None,
        papel: str,
        fonte_chave: str,
        bru_tabela: str,
        bru_chave: str,
        estrangeira: bool = False,
    ) -> int | None:
        nome = _limpar_nome_impresso(nome_raw)
        if not nome or len(nome) < 2:
            return None
        doc_str = None
        tipo_id = None
        if doc_raw:
            m_doc = _RE_DOC.search(doc_raw)
            if m_doc:
                doc_str = m_doc.group(1)
                tipo_id = "CNPJ" if "/" in doc_str else "CPF"
        if doc_str is None:
            m_doc2 = _RE_DOC.search(nome_raw)
            if m_doc2:
                doc_str = m_doc2.group(1)
                tipo_id = "CNPJ" if "/" in doc_str else "CPF"

        dig = _limpar_digits(doc_str)
        # Regras anti-fusao silenciosa para o CPF conflitante
        if dig == _CPF_CONFLITANTE:
            if "tereza" in nome.lower():
                chave = "pes:pf:tereza_cristina_alves_brandao"
            else:
                chave = "pes:pf:helena_duarte_lima"
            return self.garantir_pessoa(
                conn, chave, "PF", nome, bru_tabela, bru_chave,
                ident_valor=doc_str, tipo_id="CPF", papel=papel, fonte_chave=fonte_chave,
            )

        if dig and dig in self.pessoas_por_doc:
            pid = self.pessoas_por_doc[dig]
            chave = next(k for k, v in self.pessoas_por_chave.items() if v == pid)
            return self.garantir_pessoa(
                conn, chave, "PJ" if tipo_id == "CNPJ" else "PF", nome, bru_tabela, bru_chave,
                ident_valor=doc_str, tipo_id=tipo_id, papel=papel, fonte_chave=fonte_chave,
            )

        slug_n = _slug(nome)
        if slug_n in self.pessoas_por_nome:
            pid = self.pessoas_por_nome[slug_n]
            chave = next(k for k, v in self.pessoas_por_chave.items() if v == pid)
            return self.garantir_pessoa(
                conn, chave, "estrangeira" if estrangeira else ("PJ" if tipo_id == "CNPJ" else "PF"),
                nome, bru_tabela, bru_chave,
                ident_valor=doc_str, tipo_id=tipo_id, papel=papel, fonte_chave=fonte_chave,
            )

        if estrangeira:
            tp = "estrangeira"
            chave = f"pes:ext:{slug_n}"
        elif tipo_id == "CNPJ":
            tp = "PJ"
            chave = f"pes:pj:{dig}"
        elif tipo_id == "CPF":
            tp = "PF"
            chave = f"pes:pf:{dig}"
        else:
            tp = "PJ" if any(w in nome.lower() for w in ("ltda", "s.a", "s/a", "eireli", "me", "banco", "cia", "conselho", "prefeitura")) else "PF"
            chave = f"pes:{tp.lower()}:{slug_n}"

        return self.garantir_pessoa(
            conn, chave, tp, nome, bru_tabela, bru_chave,
            ident_valor=doc_str, tipo_id=tipo_id, papel=papel, fonte_chave=fonte_chave,
        )


def _carregar_mapas_bruto(conn: sqlite3.Connection) -> ContextoEntidades:
    arq_m = {int(r[0]): str(r[1]) for r in conn.execute("SELECT id, chave FROM bru_arquivo").fetchall()}
    lin_m = {int(r[0]): str(r[1]) for r in conn.execute("SELECT id, chave FROM bru_linha").fetchall()}
    cel_m = {int(r[0]): str(r[1]) for r in conn.execute("SELECT id, chave FROM bru_celula").fetchall()}
    par_m = {int(r[0]): str(r[1]) for r in conn.execute("SELECT id, chave FROM bru_paragrafo").fetchall()}
    return ContextoEntidades(
        arq_chave_por_id=arq_m,
        lin_chave_por_id=lin_m,
        cel_chave_por_id=cel_m,
        par_chave_por_id=par_m,
    )


def normalizar_cadastro_e_historia(conn: sqlite3.Connection) -> ContextoEntidades:
    """Popula nrm_pessoa, nrm_empresa, nrm_estabelecimento, contas, eventos, fatos e participacoes."""
    ctx = _carregar_mapas_bruto(conn)

    def _arq_chave(rel: str) -> str:
        return f"arq:{rel}"

    # Fontes chave das empresas e casos
    arq_d2_caso = _arq_chave("D2/Estudo_de_Caso_02_Laboratorio_Contabil.pdf")
    arq_d3_nfse = _arq_chave("D3/01_NFSe_Ficticia_Auditoria_Ente_Federal.pdf")
    arq_carta_g = _arq_chave("D4/Carta_dos_socios_ao_contador_Goiania.pdf")
    arq_ativ_d4 = _arq_chave("D4/Atividade_Dossie4_Doc1_SN_Reforma_Tributaria_ALUNOS.docx")
    arq_g07 = _arq_chave("D1/Devolutivas_Individuais_Dossie1/Devolutiva_Dossie1_G07.docx")
    arq_extr_d4 = _arq_chave("D4/ExtratosBancariosRotaSul.xlsx")
    arq_extr_g = _arq_chave("D4/ExtratoBancario_MeiaPonte_Goiania_jan-ago2026.xlsx")

    # Pessoas juridicas centrais e de estudo
    p_rs_d2 = ctx.garantir_pessoa(
        conn, "pes:pj:11222333000181", "PJ",
        "Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda.",
        "bru_arquivo", arq_d2_caso, ident_valor="11.222.333/0001-81", tipo_id="CNPJ",
        papel="empresa_cliente_d2", fonte_chave=arq_d2_caso,
    )
    ctx.garantir_pessoa(
        conn, "pes:pj:11222333000181", "PJ",
        "Rota Sul Importadora, Exportadora, Comércio e Distribuidora Ltda.",
        "bru_arquivo", arq_d2_caso, ident_valor="52900000015", tipo_id="NIRE", fonte_chave=arq_d2_caso,
    )

    p_rs_d4 = ctx.garantir_pessoa(
        conn, "pes:pj:12345678000190", "PJ",
        "Rota Sul Importadora Ltda",
        "bru_arquivo", arq_carta_g, ident_valor="12.345.678/0001-90", tipo_id="CNPJ",
        papel="empresa_cliente_d4", fonte_chave=arq_carta_g,
    )
    p_mp = ctx.garantir_pessoa(
        conn, "pes:pj:41234567000101", "PJ",
        "Meia Ponte Pneus e Acessórios Ltda – ME",
        "bru_arquivo", arq_carta_g, ident_valor="41.234.567/0001-01", tipo_id="CNPJ",
        papel="empresa_relacionada_d4", fonte_chave=arq_carta_g,
    )
    p_hz = ctx.garantir_pessoa(
        conn, "pes:pj:48321765000120", "PJ",
        "Horizonte Projetos e Consultoria Ltda.",
        "bru_arquivo", arq_d3_nfse, ident_valor="48.321.765/0001-20", tipo_id="CNPJ",
        papel="prestador_auditoria_d3", fonte_chave=arq_d3_nfse,
    )
    p_cf = ctx.garantir_pessoa(
        conn, "pes:pj:00123456000100", "PJ",
        "Conselho Federal de Desenvolvimento Técnico",
        "bru_arquivo", arq_d3_nfse, ident_valor="00.123.456/0001-00", tipo_id="CNPJ",
        papel="tomador_auditoria_d3", fonte_chave=arq_d3_nfse,
    )
    p_g07 = ctx.garantir_pessoa(
        conn, "pes:pj:prisma_jrna_g07", "PJ",
        "Prisma JRNA Auditoria e Contabilidade Ltda.",
        "bru_arquivo", arq_g07, papel="escritorio_g07", fonte_chave=arq_g07,
    )

    # Pessoas fisicas do caso (socios D2 e D4 + titular formal)
    p_helena_d2 = ctx.garantir_pessoa(
        conn, "pes:pf:helena_aparecida_mendes_duarte", "PF",
        "Helena Aparecida Mendes Duarte",
        "bru_arquivo", arq_d2_caso, papel="socio_d2", fonte_chave=arq_d2_caso,
    )
    p_bruno_d2 = ctx.garantir_pessoa(
        conn, "pes:pf:bruno_mendes_duarte", "PF",
        "Bruno Mendes Duarte",
        "bru_arquivo", arq_d2_caso, ident_valor="529.982.247-25", tipo_id="CPF",
        papel="socio_d2", fonte_chave=arq_d2_caso,
    )
    p_ronaldo = ctx.garantir_pessoa(
        conn, "pes:pf:ronaldo_teixeira_brandao", "PF",
        "Ronaldo Teixeira Brandão",
        "bru_arquivo", arq_carta_g, ident_valor="111.222.333-97", tipo_id="CPF",
        papel="socio_administrador", fonte_chave=arq_carta_g,
    )
    p_marina = ctx.garantir_pessoa(
        conn, "pes:pf:marina_costa_brandao", "PF",
        "Marina Costa Brandão",
        "bru_arquivo", arq_carta_g, ident_valor="444.555.666-10", tipo_id="CPF",
        papel="socio", fonte_chave=arq_carta_g,
    )
    p_helena_d4 = ctx.garantir_pessoa(
        conn, "pes:pf:helena_duarte_lima", "PF",
        "Helena Duarte Lima",
        "bru_arquivo", arq_carta_g, ident_valor="888.777.666-04", tipo_id="CPF",
        papel="socio", fonte_chave=arq_carta_g,
    )
    p_tereza = ctx.garantir_pessoa(
        conn, "pes:pf:tereza_cristina_alves_brandao", "PF",
        "Tereza Cristina Alves Brandão",
        "bru_arquivo", arq_carta_g, ident_valor="777.888.999-42", tipo_id="CPF",
        papel="titular_formal", fonte_chave=arq_carta_g,
    )

    # Inserir empresas
    empresas_def = [
        ("emp:rota_sul_d2", p_rs_d2, "Rota Sul (Caso D2)", "cliente_d2", arq_d2_caso),
        ("emp:rota_sul_d4", p_rs_d4, "Rota Sul Importadora Ltda", "cliente_d4", arq_carta_g),
        ("emp:meia_ponte", p_mp, "Meia Ponte Pneus e Acessórios Ltda – ME", "empresa_relacionada_d4", arq_carta_g),
        ("emp:horizonte", p_hz, "Horizonte Projetos e Consultoria Ltda.", "caso_auditoria_d3", arq_d3_nfse),
        ("emp:conselho_federal_d3", p_cf, "Conselho Federal de Desenvolvimento Técnico", "contraparte", arq_d3_nfse),
        ("emp:prisma_jrna_g07", p_g07, "Prisma JRNA Auditoria e Contabilidade Ltda.", "contraparte", arq_g07),
    ]
    for ch, pid, nome_c, papel_c, src in empresas_def:
        cur = conn.execute(
            "INSERT INTO nrm_empresa (chave, pessoa_id, nome_curto, papel_no_caso) VALUES (?, ?, ?, ?)",
            (ch, pid, nome_c, papel_c),
        )
        ctx.empresas_por_chave[ch] = int(cur.lastrowid)
        ctx.add_ev("nrm_empresa", ch, "bru_arquivo", src)

    # Estabelecimentos
    est_def = [
        ("est:rota_sul_d2:matriz", "emp:rota_sul_d2", "matriz", "11.222.333/0001-81", "GO", "Goiânia", "Sede conforme D2", None, arq_d2_caso),
        ("est:rota_sul_d2:filial_itajai", "emp:rota_sul_d2", "filial", "11.222.333/0002-62", "SC", "Itajaí", "Filial Itajaí conforme D2 (NIRE 42900000012)", None, arq_d2_caso),
        ("est:rota_sul_d4:matriz", "emp:rota_sul_d4", "matriz", "12.345.678/0001-90", "SC", "Joinville", "Rua das Hortênsias, 1.250 – Distrito Industrial", "M", arq_carta_g),
        ("est:rota_sul_d4:filial_itajai", "emp:rota_sul_d4", "filial", "12.345.678/0002-71", "SC", "Itajaí", "Filial Portuária Itajaí/SC", "F", arq_carta_g),
        ("est:meia_ponte:matriz", "emp:meia_ponte", "unico", "41.234.567/0001-01", "GO", "Goiânia", "Av. Independência, 3.420 – Setor Leste Universitário", "G", arq_carta_g),
        ("est:horizonte:matriz", "emp:horizonte", "unico", "48.321.765/0001-20", "GO", "Goiânia", "Goiânia/GO", None, arq_d3_nfse),
    ]
    for ch, emp_ch, tp, cnpj, uf, mun, end, pfx, src in est_def:
        cur = conn.execute(
            """
            INSERT INTO nrm_estabelecimento (chave, empresa_id, tipo, cnpj, uf, municipio, endereco)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ch, ctx.empresas_por_chave[emp_ch], tp, cnpj, uf, mun, end),
        )
        eid = int(cur.lastrowid)
        ctx.estabelecimentos_por_chave[ch] = eid
        if pfx:
            ctx.estab_por_prefixo[pfx] = eid
        ctx.add_ev("nrm_estabelecimento", ch, "bru_arquivo", src)
    ctx.estab_por_prefixo["NF"] = ctx.estabelecimentos_por_chave["est:rota_sul_d4:matriz"]

    # Contas bancarias
    ctas_def = [
        ("cta:meridional:matriz", "emp:rota_sul_d4", "est:rota_sul_d4:matriz", "Banco Meridional S.A.", "0001", "10001-1", "Conta Matriz Joinville (2025-2026)", arq_extr_d4, ("matriz_2025", "matriz_2026")),
        ("cta:meridional:filial", "emp:rota_sul_d4", "est:rota_sul_d4:filial_itajai", "Banco Meridional S.A.", "0002", "20002-2", "Conta Filial Itajaí (2025-2026)", arq_extr_d4, ("filial",)),
        ("cta:goiania:meia_ponte", "emp:meia_ponte", "est:meia_ponte:matriz", "Banco Comercial Goiânia S.A.", "0003", "30003-3", "Conta Goiânia Meia Ponte (jan-ago 2026)", arq_extr_g, ("goiania",)),
    ]
    for ch, emp_ch, est_ch, bco, ag, cta_n, desc, src, cods in ctas_def:
        cur = conn.execute(
            """
            INSERT INTO nrm_conta_bancaria (chave, empresa_id, estabelecimento_id, banco_nome, agencia, conta_numero, descricao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ch, ctx.empresas_por_chave[emp_ch], ctx.estabelecimentos_por_chave[est_ch], bco, ag, cta_n, desc),
        )
        cid = int(cur.lastrowid)
        for cod in cods:
            ctx.contas_por_chave[cod] = cid
        ctx.contas_por_chave[ch] = cid
        ctx.add_ev("nrm_conta_bancaria", ch, "bru_arquivo", src)

    # Eventos e Fatos temporais + Participacoes Societarias
    eventos_def = [
        ("evt:d2:2a_alteracao_contratual", "emp:rota_sul_d2", "alteracao_contratual", "2026-09-14",
         "2ª Alteração Contratual e Consolidação (D2): capital R$ 1.000.000,00 -> R$ 1.500.000,00 e filial Itajaí.", arq_d2_caso),
        ("evt:d2:admissao_empregados", "emp:rota_sul_d2", "admissao_prevista", "2026-09-21",
         "Parâmetros de admissão dos dois empregados no Estudo de Caso 02 (D2).", arq_d2_caso),
        ("evt:d4:rota_sul_sede_joinville", "emp:rota_sul_d4", "constituicao", "2025-01-01",
         "Operação da Rota Sul Importadora Ltda (D4) com matriz em Joinville/SC e filial em Itajaí/SC no Simples Nacional.", arq_carta_g),
        ("evt:d4:meia_ponte_constituicao", "emp:meia_ponte", "constituicao", "2021-01-01",
         "Constituição da Meia Ponte Pneus e Acessórios Ltda – ME (Goiânia/GO) em nome de Tereza Cristina Alves Brandão.", arq_carta_g),
        ("evt:d4:meia_ponte_importacao_2026", "emp:meia_ponte", "abertura_filial", "2026-01-01",
         "Início das importações diretas pelo CNPJ de Goiânia operadas de fato por Ronaldo (procuração) e Marina.", arq_carta_g),
        ("evt:d4:carta_socios_2026", "emp:meia_ponte", "carta_socios", "2026-09-14",
         "Carta dos sócios da Rota Sul e Meia Ponte ao contador relatando divisão de CNPJ para teto do Simples.", arq_carta_g),
        ("evt:d3:auditoria_nfse", "emp:horizonte", "mudanca_regime", "2026-10-20",
         "Emissão da DANFSe didática 2026/000184 (Horizonte Projetos - Lucro Presumido) com retenções federais e ISSQN.", arq_d3_nfse),
    ]
    evt_ids: dict[str, int] = {}
    for ch, emp_ch, tp, dt, desc, src in eventos_def:
        cur = conn.execute(
            """
            INSERT INTO nrm_evento (chave, empresa_id, tipo_evento, data_evento, descricao, fonte_chave)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ch, ctx.empresas_por_chave[emp_ch], tp, dt, desc, src),
        )
        evt_ids[ch] = int(cur.lastrowid)
        ctx.n_eventos += 1
        ctx.add_ev("nrm_evento", ch, "bru_arquivo", src)

    fatos_def = [
        ("fato:d2:rs:sede", "emp:rota_sul_d2", "evt:d2:2a_alteracao_contratual", "sede", "Goiânia/GO (Matriz) e Itajaí/SC (Filial)", None, "2026-09-14", None, arq_d2_caso),
        ("fato:d2:rs:capital_antes", "emp:rota_sul_d2", "evt:d2:2a_alteracao_contratual", "capital_social", "R$ 1.000.000,00 totalmente integralizados", 100000000, "2024-01-01", "2026-09-13", arq_d2_caso),
        ("fato:d2:rs:capital_depois", "emp:rota_sul_d2", "evt:d2:2a_alteracao_contratual", "capital_social", "R$ 1.500.000,00 (R$ 1.000.000,00 integralizados + R$ 500.000,00 a integralizar)", 150000000, "2026-09-14", None, arq_d2_caso),
        ("fato:d2:rs:emp1", "emp:rota_sul_d2", "evt:d2:admissao_empregados", "empregado_parametro", "Empregado 1: salário R$ 2.400,00 mensais + refeição R$ 30,00/dia", 240000, "2026-09-21", None, arq_d2_caso),
        ("fato:d2:rs:emp2", "emp:rota_sul_d2", "evt:d2:admissao_empregados", "empregado_parametro", "Empregado 2: salário R$ 1.900,00 mensais + comissão 1,5% + refeição R$ 30,00/dia", 190000, "2026-09-21", None, arq_d2_caso),
        ("fato:d4:rs:sede", "emp:rota_sul_d4", "evt:d4:rota_sul_sede_joinville", "sede", "Joinville/SC (Matriz) e Itajaí/SC (Filial)", None, "2025-01-01", None, arq_carta_g),
        ("fato:d4:rs:regime", "emp:rota_sul_d4", "evt:d4:rota_sul_sede_joinville", "regime", "Simples Nacional (CRT 1)", None, "2025-01-01", None, arq_ativ_d4),
        ("fato:d4:mp:regime", "emp:meia_ponte", "evt:d4:meia_ponte_constituicao", "regime", "Simples Nacional (loja pequena ~R$ 50 mil/mês em 2021-2025; importações diretas R$ 250-330 mil/mês em 2026)", None, "2021-01-01", None, arq_carta_g),
        ("fato:d4:mp:gestao", "emp:meia_ponte", "evt:d4:meia_ponte_importacao_2026", "razao_social", "Titular formal Tereza Cristina Alves Brandão; operada de fato por Ronaldo (procuração) e Marina", None, "2026-01-01", None, arq_carta_g),
        ("fato:d3:hz:regime", "emp:horizonte", "evt:d3:auditoria_nfse", "regime", "Lucro Presumido (Não optante pelo Simples)", None, "2026-10-20", None, arq_d3_nfse),
    ]
    for ch, suj, evt_ch, atr, vtxt, vc, de, ate, src in fatos_def:
        conn.execute(
            """
            INSERT INTO nrm_fato (chave, sujeito_chave, evento_id, atributo, valor_texto, valor_centavos, vigente_de, vigente_ate, fonte_chave)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ch, suj, evt_ids[evt_ch], atr, vtxt, vc, de, ate, src),
        )
        ctx.n_fatos += 1
        ctx.add_ev("nrm_fato", ch, "bru_arquivo", src)

    parts_def = [
        ("part:d2:helena", "emp:rota_sul_d2", p_helena_d2, 750000, 75000000, 50000000, "socio_administrador", "2026-09-14", None, arq_d2_caso),
        ("part:d2:bruno", "emp:rota_sul_d2", p_bruno_d2, 750000, 75000000, 50000000, "socio_administrador", "2026-09-14", None, arq_d2_caso),
        ("part:d4:ronaldo", "emp:rota_sul_d4", p_ronaldo, None, None, None, "socio_administrador", "2025-01-01", None, arq_carta_g),
        ("part:d4:marina", "emp:rota_sul_d4", p_marina, None, None, None, "socio", "2025-01-01", None, arq_carta_g),
        ("part:d4:helena", "emp:rota_sul_d4", p_helena_d4, None, None, None, "socio", "2025-01-01", None, arq_carta_g),
        ("part:d4:mp:tereza", "emp:meia_ponte", p_tereza, None, None, 100000000, "titular_formal", "2021-01-01", None, arq_carta_g),
        ("part:d4:mp:ronaldo", "emp:meia_ponte", p_ronaldo, None, None, None, "procurador", "2026-01-01", None, arq_carta_g),
        ("part:d4:mp:marina", "emp:meia_ponte", p_marina, None, None, None, "socio_de_fato", "2026-01-01", None, arq_carta_g),
    ]
    for ch, emp_ch, spid, qts, vc, pct, ppl, de, ate, src in parts_def:
        conn.execute(
            """
            INSERT INTO nrm_participacao_societaria (
                chave, empresa_id, socio_pessoa_id, quotas, valor_centavos, percentual_micro, papel, vigente_de, vigente_ate, fonte_chave
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ch, ctx.empresas_por_chave[emp_ch], spid, qts, vc, pct, ppl, de, ate, src),
        )
        ctx.add_ev("nrm_participacao_societaria", ch, "bru_arquivo", src)

    # Catalogar contrapartes dos documentos D4 via ext_campo
    rotulos_nome = (
        "NOME / RAZÃO SOCIAL", "RAZÃO SOCIAL", "EXPORTER / SELLER", "EXPORTADOR",
        "NOME", "BENEFICIÁRIO", "PAGADOR", "LOCADOR", "TOMADOR", "CLIENT",
    )
    docs_info = conn.execute(
        """
        SELECT d.id, d.chave, d.modelo, a.chave
        FROM ext_documento d
        JOIN bru_arquivo a ON a.id = d.arquivo_id
        ORDER BY d.id
        """
    ).fetchall()
    for did, dchave, modelo, achave in docs_info:
        campos = conn.execute(
            "SELECT rotulo, valor_texto, linha_bruto_id FROM ext_campo WHERE documento_id = ?",
            (did,),
        ).fetchall()
        mapa = {r: (v, lid) for r, v, lid in campos}
        cnpj_val = None
        for rk in ("CNPJ", "CNPJ / CPF", "CNPJ EMITENTE", "CPF"):
            if rk in mapa and _RE_DOC.search(mapa[rk][0]):
                cnpj_val = mapa[rk][0]
                break
        for r, v, lid in campos:
            if r in rotulos_nome or r.startswith(("EMITENTE", "DESTINATÁRIO", "BENEFICIÁRIO", "PAGADOR")):
                eh_est = modelo == "Commercial-Invoice" or r in ("EXPORTER / SELLER", "EXPORTADOR")
                b_tab = "bru_linha" if lid and lid in ctx.lin_chave_por_id else "bru_arquivo"
                b_key = ctx.lin_chave_por_id[lid] if b_tab == "bru_linha" else achave
                ctx.resolver_ou_criar_contraparte(
                    conn, v, cnpj_val, _slug(r), dchave, b_tab, b_key, estrangeira=eh_est
                )

    # Registrar conflitos deliberados do caso em conferencia (sem resolver em silencio)
    _upsert_conferencia(
        conn,
        "conf:cpf_compartilhado_helena_tereza",
        "cpf_compartilhado_pessoas_distintas",
        "divergencia",
        ["pes:pf:helena_duarte_lima", "pes:pf:tereza_cristina_alves_brandao"],
        {
            "cpf_conflitante": "777.888.999-42",
            "helena_carta_socios": "888.777.666-04",
            "helena_ccb_2025": "777.888.999-42",
            "tereza_prolabore_2026": "777.888.999-42",
        },
        "aberto",
        "CPF 777.888.999-42 aparece associado a Helena Duarte Lima na CCB e a Tereza Cristina Alves Brandao nos recibos de pro-labore; mantidas como pessoas distintas.",
    )
    _upsert_conferencia(
        conn,
        "conf:versoes_rota_sul_d2_vs_d4",
        "versoes_empresa_d2_vs_d4",
        "info",
        ["emp:rota_sul_d2", "emp:rota_sul_d4"],
        {
            "d2": {"cnpj": "11.222.333/0001-81", "sede": "Goiânia/GO", "socios": ["Helena A. M. Duarte", "Bruno M. Duarte"]},
            "d4": {"cnpj": "12.345.678/0001-90", "sede": "Joinville/SC", "socios": ["Ronaldo T. Brandão", "Marina C. Brandão", "Helena D. Lima"]},
        },
        "registrado",
        "Versoes distintas da empresa ficticia Rota Sul no Estudo de Caso 02 (D2) e no acervo documental do D4 preservadas separadamente.",
    )
    _upsert_conferencia(
        conn,
        "conf:prazo_dossie4_divergente",
        "prazo_dossie4_divergente",
        "alerta",
        ["dos:D4", arq_d2_caso, _arq_chave("_paginas/D4/Orientações 18.11.22026 Dossiê 4.html")],
        {"prazo_plano_e_d2": "2026-12-14", "prazo_orientacoes_sigaa": "2026-12-07"},
        "aberto",
        "Divergencia de prazo de entrega do Dossie 4 entre o Estudo de Caso/Plano de Ensino (14/12/2026) e a pagina de Orientacoes do SIGAA (07/12/2026).",
    )

    return ctx
