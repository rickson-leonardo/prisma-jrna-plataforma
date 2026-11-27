"""Testes puros (sem banco) das correções da revisão das fases 1–5 do D2."""
from __future__ import annotations

from pathlib import Path

from sistema.erp.motor_folha import (
    ALIQ_EXCLUSAO_SIMPLES_MICRO_PADRAO,
    _historico_lote_l3,
    detectar_residuos_texto_d2,
    recalcular_folha_independente_dados,
)
from sistema.testes.test_web_dossie2 import _fixture_dados_d2
from sistema.web.app import create_app
from sistema.web.emissor_dossie2 import _capital_doc01, _marcadores_honorarios, _normalizar_docs_admissao, html_documento
from sistema.web.planilha_dossie2 import _montar_workbook_d2

TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"


def _secao(texto: str) -> dict[str, str]:
    return {"documento": "d2_teste", "codigo_secao": "s", "conteudo_md": texto}


def test_residuo_1555_aceita_qualquer_forma_de_revogacao() -> None:
    # Frases reais de produção (26/11/2026) que geravam alerta crítico falso
    termo_rt = ("*(Contrato de prestação de serviços contábeis, a transferência de responsabilidade técnica "
                "e o distrato, revogando a Resolução CFC nº 1.555/2018)*")
    diario_ia = ("| **Responsabilidade Técnica Contábil e Ética** | Revogação da Resolução CFC nº 1.555/2018 e "
                 "exigências vigentes de contrato escrito, distrato, Carta de Responsabilidade e sigilo profissional. |")
    assert detectar_residuos_texto_d2([_secao(termo_rt), _secao(diario_ia)], []) == []
    # A norma revogada citada como vigente continua gerando alerta
    achados = detectar_residuos_texto_d2([_secao("Emitido nos termos da Resolução CFC nº 1.555/2018.")], [])
    assert [a["padrao"] for a in achados] == ["1.555/2018"]


def _macros():
    app = create_app()
    with app.test_request_context():
        return app.jinja_env.get_template("_macros.html").make_module({})


def test_select_rotulos_com_opcao_vazia_nao_inventa_classificacao() -> None:
    m = _macros()
    sem_valor = str(m.select_rotulos("risco_tipo", "risco_tipo", None, "— não classificado —"))
    assert '<option value="" selected' in sem_valor
    assert 'value="formal" selected' not in sem_valor
    com_valor = str(m.select_rotulos("risco_tipo", "risco_tipo", "material", "— não classificado —"))
    assert 'value="material" selected' in com_valor
    assert '<option value="" selected' not in com_valor
    # Sem o parâmetro `vazio` o select fica como antes (D1 inalterado)
    assert 'value=""' not in str(m.select_rotulos("risco_tipo", "risco_tipo", "formal"))


def test_instrumentos_d2_sem_risco_pre_selecionado() -> None:
    html = (TEMPLATES / "instrumentos.html").read_text(encoding="utf-8")
    assert "or 'formal'" not in html and "or 'medio'" not in html
    assert "'risco_tipo', 'formal')" not in html and "'risco_nivel', 'medio')" not in html
    assert html.count("'— não classificado —'") == 4


def test_pdf_sem_fallback_providencia_e_impacto() -> None:
    dados = _fixture_dados_d2()
    dados["clausulas_d2"][0]["providencia"] = None
    dados["clausulas_d2"][0]["apontamento_auditoria"] = "NOTA-X"
    html_doc01 = html_documento("d2_01_diagnostico", para_web=True, dados=dados)
    assert "NOTA-X" not in html_doc01

    dados["consultas"][0]["impacto_se_alterada"] = None
    dados["consultas"][0]["decisao_impactada"] = "DEC-Y"
    html_doc14 = html_documento("d2_14_premissas", para_web=True, dados=dados)
    ini_t2 = html_doc14.index("Tabela 2 — Quadro de decisões")
    fim_t2 = html_doc14.index("Tabela 3 — Tabelas oficiais")
    tabela2 = html_doc14[ini_t2:fim_t2]
    assert "DEC-Y" in html_doc14[:ini_t2]
    assert "DEC-Y" not in tabela2


def test_prontuario_nao_afirma_entrega_sem_status() -> None:
    pecas_str = _normalizar_docs_admissao({"docs_admissionais_json": ["RG/CPF"], "aso_status": "pendente_critico"})
    assert pecas_str[0] == {"peca": "RG/CPF", "status": "Não informado", "observacao": "Status não registrado no banco"}
    assert "ASO Admissional" in pecas_str[-1]["peca"]

    pecas_sem_st = _normalizar_docs_admissao({"docs_admissionais_json": [{"documento": "CTPS"}], "aso_status": "apto"})
    assert pecas_sem_st[0] == {"peca": "CTPS", "status": "Não informado", "observacao": "Status não registrado no banco"}

    pecas_com_st = _normalizar_docs_admissao({"docs_admissionais_json": [{"documento": "CTPS", "status": "entregue"}]})
    assert pecas_com_st[0]["status"] == "entregue"
    assert "ASO Admissional" in pecas_com_st[-1]["peca"]


def test_capital_integralizado_exige_fato_explicito() -> None:
    dados = _fixture_dados_d2()
    cap_com = _capital_doc01(dados)
    assert cap_com == {"subscrito": 150_000_000, "integralizado": 100_000_000, "a_integralizar": 50_000_000}

    dados["fatos_capital"] = [
        {"atributo": "capital_social", "valor_centavos": 100_000_000, "vigente_ate": "2026-09-13"},
        {"atributo": "capital_social", "valor_centavos": 150_000_000, "vigente_ate": None},
    ]
    cap_sem = _capital_doc01(dados)
    assert cap_sem == {"subscrito": 150_000_000, "integralizado": None, "a_integralizar": None}

    html = html_documento("d2_01_diagnostico", para_web=True, dados=dados)
    assert "Integralizado: <span class=\"mono\">— (não registrado)</span>" in html
    assert "A integralizar: <span class=\"mono\">— (não registrado)</span>" in html
    assert "R$\xa0500.000,00" not in html


def test_emissor_sem_fallback_rt_e_sede() -> None:
    emissor_src = (Path(__file__).resolve().parents[1] / "web" / "emissor_dossie2.py").read_text(encoding="utf-8")
    for proibido in ("Nathalia Peres Araujo", "CRC-DF 025.431/O-7", "'Goiânia'", "'GO'"):
        assert proibido not in emissor_src

    dados = _fixture_dados_d2()
    dados["estabelecimentos"] = [{"id": 1, "tipo": "matriz", "cnpj": "11.222.333/0001-81", "uf": None, "municipio": None, "endereco": None, "status_validacao": "pendente_revisao"}]
    dados["escritorio"] = {}
    dados["rt"] = {"nome": "—", "crc": "—"}
    html = html_documento("d2_01_diagnostico", para_web=True, dados=dados)
    assert "— — —/—" in html
    assert "PRISMA JRNA (RT —, —)" in html
    assert "Goiânia" not in html
    assert "Nathalia Peres Araujo" not in html


def test_planilha_sem_valores_reserva_e_excl_simples() -> None:
    plan_src = (Path(__file__).resolve().parents[1] / "web" / "planilha_dossie2.py").read_text(encoding="utf-8")
    for literal in ("6000000", "15000", "172225", "186300", "0.278"):
        assert literal not in plan_src

    dados = _fixture_dados_d2()
    dados["comp"].pop("vendas_liquidas_e2_centavos", None)
    dados["contratos"][0].pop("piso_cct_centavos", None)
    dados["contratos"][1].pop("piso_cct_centavos", None)
    dados["contratos"][1].pop("comissao_pct_micro", None)
    wb = _montar_workbook_d2(dados)
    ws_par = wb["Parametros"]
    assert ws_par["C11"].value is None
    assert ws_par["D11"].value is None
    assert ws_par["C28"].value is None
    assert ws_par["D28"].value is None
    assert ws_par["D29"].value == ALIQ_EXCLUSAO_SIMPLES_MICRO_PADRAO / 1_000_000.0

    # Com parâmetro EXCL-SIMPLES explícito no banco, a planilha usa o parâmetro
    dados["parametros"].append({"codigo": "EXCL-SIMPLES", "categoria": "encargos", "ordem": 1, "aliquota_micro": 295_000})
    wb2 = _montar_workbook_d2(dados)
    assert wb2["Parametros"]["D29"].value == 0.295


def test_recalculo_sem_fgts_registra_ausente_e_nao_inventa() -> None:
    dados = _fixture_dados_d2()
    dados["parametros"] = [p for p in dados["parametros"] if p.get("codigo") != "FGTS-8"]
    ausentes: list[str] = []
    comp = recalcular_folha_independente_dados(
        dados["comp"], dados["contratos"], dados["parametros"], dados["itens"], parametros_ausentes=ausentes
    )
    assert "FGTS-8" in ausentes
    assert not any(r["codigo_rubrica"] in ("FGTS-8", "PROV-FGTS") for r in comp)

    motor_src = (Path(__file__).resolve().parents[1] / "erp" / "motor_folha.py").read_text(encoding="utf-8")
    assert "D2_PARAMETRO_AUSENTE" in motor_src


def test_recalculo_com_parametros_producao_preserva_gabarito() -> None:
    dados = _fixture_dados_d2()
    # Completa demais faixas de produção do IRRF e RED-TRANS
    dados["parametros"].extend([
        {"codigo": "IRRF-F2", "categoria": "irrf", "ordem": 4, "limite_centavos": 282_665, "aliquota_micro": 75_000, "deducao_centavos": 18_216},
        {"codigo": "IRRF-F3", "categoria": "irrf", "ordem": 5, "limite_centavos": 375_105, "aliquota_micro": 150_000, "deducao_centavos": 39_416},
        {"codigo": "IRRF-F4", "categoria": "irrf", "ordem": 6, "limite_centavos": 466_468, "aliquota_micro": 225_000, "deducao_centavos": 67_549},
        {"codigo": "IRRF-F5", "categoria": "irrf", "ordem": 7, "limite_centavos": None, "aliquota_micro": 275_000, "deducao_centavos": 90_873},
        {"codigo": "RED-TRANS", "categoria": "reducao_irrf_2026", "ordem": 2, "limite_centavos": 735_000, "aliquota_micro": 133_145, "deducao_centavos": 97_862},
    ])
    ausentes: list[str] = []
    comp = recalcular_folha_independente_dados(
        dados["comp"], dados["contratos"], dados["parametros"], dados["itens"], parametros_ausentes=ausentes
    )
    assert ausentes == []
    mapa = {(r["codigo_empregado"], r["codigo_rubrica"]): r["valor_recalculado_centavos"] for r in comp}
    assert mapa[("E1", "INSS-RET")] == 9_000
    assert mapa[("E2", "INSS-RET")] == 12_268
    assert mapa[("E1", "NEGOCIAL")] == 3_996
    assert mapa[("E2", "NEGOCIAL")] == 5_439
    assert mapa[("E1", "VT-DESC")] == 7_200
    assert mapa[("E2", "VT-DESC")] == 3_800
    assert mapa[("E1", "PROV-13")] == 20_000
    assert mapa[("E1", "PROV-FER")] == 20_000
    assert mapa[("E1", "PROV-1/3")] == 6_667
    assert mapa[("E1", "PROV-FGTS")] == 3_733

    # Verifica correção de precedência com dias_trabalhados_e1=None e dias_uteis_vt_e1=None
    comp_none = dict(dados["comp"], dias_trabalhados_e1=None, dias_uteis_vt_e1=None)
    rec_none = recalcular_folha_independente_dados(comp_none, dados["contratos"], dados["parametros"], [])
    mapa_none = {(r["codigo_empregado"], r["codigo_rubrica"]): r["valor_recalculado_centavos"] for r in rec_none}
    assert mapa_none[("E1", "SAL-PROP")] == 0
    assert mapa_none[("E1", "VT-DESC")] == 0


def test_historico_lote_l3_dinamico() -> None:
    cts_2 = [
        {"codigo_empregado": "E1", "vt_optante": True, "vt_passagens_dia": 2},
        {"codigo_empregado": "E2", "vt_optante": True, "vt_passagens_dia": 2},
    ]
    assert _historico_lote_l3(cts_2, "2026-09") == "L3 — Apropriação de Benefícios VT (2/dia) e VR PAT 09/2026"

    cts_misto = [
        {"codigo_empregado": "E1", "vt_optante": True, "vt_passagens_dia": 4},
        {"codigo_empregado": "E2", "vt_optante": True, "vt_passagens_dia": 2},
    ]
    assert _historico_lote_l3(cts_misto, "2026-09") == "L3 — Apropriação de Benefícios VT (E1 4/dia, E2 2/dia) e VR PAT 09/2026"


def test_regua_d2_sem_47_fixo() -> None:
    sust_html = (TEMPLATES / "sustentacao.html").read_text(encoding="utf-8")
    base_html = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "47" not in sust_html
    assert "47" not in base_html

    imp_src = (Path(__file__).resolve().parents[1] / "erp" / "importar_dossie2.py").read_text(encoding="utf-8")
    assert "REVISAO_ENTREGA_LIMPA_2026-11-24.md" not in imp_src
    assert "Critérios D2 alinhados à devolutiva oficial no banco (48, incl. C-48); não reimportar." in imp_src

    app = create_app()
    app.jinja_env.globals["progresso_estacoes"] = lambda: {}
    app.jinja_env.globals["dossie_ativo"] = lambda: "D2"
    with app.test_request_context("/sustentacao"):
        rendered = app.jinja_env.get_template("sustentacao.html").render(
            empresa={"dossie": "D2"},
            placar=[],
            total_criterios=48,
            criterios=[],
            matriz_ativa="d2_p1",
            apenas_pendentes=False,
            matrizes_disponiveis=("d2_p1",),
            consultas=[],
            decisoes=[],
            diario_ia=[],
        )
    assert "48 critérios" in rendered


def test_cadastro_d2_progresso_rotulos_vigencia_nire_e_select_ident() -> None:
    app = create_app()
    app.jinja_env.globals["progresso_estacoes"] = lambda: {}
    app.jinja_env.globals["dossie_ativo"] = lambda: "D2"
    ctx_d2 = {
        "empresa": {"id": 1, "dossie": "D2", "nome_curto": "Rota Sul Importadora", "razao_social_pessoa": "Rota Sul Ltda.", "origem_registro": "acervo_sigaa", "status_validacao": "acervo_referencia"},
        "estabelecimentos": [
            {"id": 1, "tipo": "matriz", "cnpj": "11.222.333/0001-81", "nire": "52900000015", "uf": "GO", "municipio": "Goiânia", "endereco": "Rua das Mangueiras", "status_validacao": "acervo_referencia", "origem_registro": "acervo_sigaa"},
            {"id": 2, "tipo": "filial", "cnpj": "11.222.333/0002-62", "nire": "42900000012", "uf": "SC", "municipio": "Itajaí", "endereco": "BR-101, Sala 223", "status_validacao": "acervo_referencia", "origem_registro": "acervo_sigaa"},
        ],
        "socios": [
            {"id": 1, "nome_canonico": "Helena Aparecida Mendes Duarte", "papel": "Sócia administradora (assina individualmente)", "quotas": 750_000, "valor_centavos": 75_000_000, "percentual_micro": 500_000, "status_validacao": "acervo_referencia", "origem_registro": "acervo_sigaa"},
            {"id": 2, "nome_canonico": "Bruno Mendes Duarte", "papel": "Sócio administrador (assina individualmente)", "quotas": 750_000, "valor_centavos": 75_000_000, "percentual_micro": 500_000, "status_validacao": "acervo_referencia", "origem_registro": "acervo_sigaa"},
        ],
        "identificadores": [
            {"id": i, "tipo_id": "CPF", "valor": f"000-{i}", "nome_canonico": "Helena", "eh_ficticio": True, "status_validacao": "acervo_referencia", "origem_registro": "acervo_sigaa"}
            for i in range(1, 7)
        ],
        "pessoas": [
            {"id": 1, "tipo_pessoa": "PJ", "nome_canonico": "Rota Sul Ltda."},
            {"id": 7, "tipo_pessoa": "PF", "nome_canonico": "Helena Aparecida Mendes Duarte"},
            {"id": 463, "tipo_pessoa": "PF", "nome_canonico": "Nathalia Peres Araujo"},
        ],
        "pessoas_ident": [
            {"id": 1, "tipo_pessoa": "PJ", "nome_canonico": "Rota Sul Ltda."},
            {"id": 7, "tipo_pessoa": "PF", "nome_canonico": "Helena Aparecida Mendes Duarte"},
        ],
        "enquadramentos": [
            {"id": 86, "porte": "ME", "regime_tributario": "Simples_Anexo_I", "cnae_principal": "4530-7/02", "cnaes_secundarios": ["4530-7/05"], "registro_crc": "CRC-DF 004.821/O-2", "responsavel_tecnico_pessoa_id": 463, "vigente_de": "2026-09-01", "vigente_ate": None, "status_validacao": "homologado_contadora", "origem_registro": "usuario"},
            {"id": 85, "porte": "ME", "regime_tributario": "Simples_Anexo_I", "cnae_principal": "4530-7/02", "cnaes_secundarios": ["4530-7/05"], "registro_crc": None, "responsavel_tecnico_pessoa_id": None, "vigente_de": "2024-10-28", "vigente_ate": "2026-08-31", "status_validacao": "homologado_contadora", "origem_registro": "importado_rascunho_v2"},
        ],
        "soma_quotas_pct": 100.0,
        "soma_capital_centavos": 150_000_000,
    }
    with app.test_request_context("/cadastro"):
        html_d2 = app.jinja_env.get_template("cadastro.html").render(**ctx_d2)
    assert '<span class="mono">2/2</span> registros cadastrais homologados · 11 referências do acervo' in html_d2
    assert "Estabelecimentos (Matriz e Filial)" in html_d2
    assert "Quadro Societário e participação societária" in html_d2
    assert "NIRE 42900000012" in html_d2
    assert "Vigente de <span class=\"mono\">28/10/2024</span> a <span class=\"mono\">31/08/2026</span>" in html_d2
    assert "Vigente desde <span class=\"mono\">01/09/2026</span>" in html_d2
    # RT aparece no select de Enquadramento (1.5), mas nao no + Novo de Registros (1.4)
    sec_reg = html_d2[html_d2.index('id="registros"'):html_d2.index('id="enquadramento"')]
    sec_enq = html_d2[html_d2.index('id="enquadramento"'):]
    assert "Nathalia Peres Araujo" not in sec_reg
    assert "Nathalia Peres Araujo" in sec_enq

    # D1 preservado
    ctx_d1 = dict(ctx_d2, empresa={"id": 11, "dossie": "D1", "nome_curto": "Prisma", "razao_social_pessoa": "Prisma Ltda.", "origem_registro": "usuario", "status_validacao": "homologado_contadora"})
    with app.test_request_context("/cadastro"):
        html_d1 = app.jinja_env.get_template("cadastro.html").render(**ctx_d1)
    assert "Estabelecimentos e sede no Distrito Federal" in html_d1
    assert "Quadro de Sócias e participação societária" in html_d1


def test_doc01_exibe_nire_filial_e_matriz() -> None:
    dados = _fixture_dados_d2()
    dados["estabelecimentos"][0]["nire"] = "52900000015"
    dados["estabelecimentos"][1]["nire"] = "42900000012"
    html = html_documento("d2_01_diagnostico", para_web=True, dados=dados)
    assert "52900000015" in html
    assert "42900000012" in html


def test_alerta_cnae_simples_sem_numero_hardcoded() -> None:
    motor_src = (Path(__file__).resolve().parents[1] / "erp" / "motor_folha.py").read_text(encoding="utf-8")
    bloco = motor_src[motor_src.index("D2_CNAE_VEDACAO_SIMPLES"):motor_src.index("D2_ASO_ADMISSIONAL_PENDENTE")]
    assert "917,40" not in bloco and "22,22%" not in bloco








def test_marcadores_honorarios_vem_de_horas_vezes_valor_hora() -> None:
    cs = [
        {"codigo_documento": "proposta", "valor_hora_centavos": 12_500, "honorario_mensal_centavos": 400_000,
         "tem_decimo_terceiro": True, "horas_mes_estimadas": 32,
         "memoria_horas_json": [{"codigo": "SETUP", "frente": "Implantação", "horas": 16},
                                {"codigo": "RECUPERACAO", "frente": "Passivo", "horas": 96},
                                {"codigo": "MENSAL_MATRIZ", "frente": "Matriz", "horas": 20}]},
        {"codigo_documento": "contrato", "valor_hora_centavos": 12_500, "honorario_mensal_centavos": 400_000,
         "tem_decimo_terceiro": False, "horas_mes_estimadas": 32, "memoria_horas_json": []},
    ]
    mk = {k: v.replace(" ", " ") for k, v in _marcadores_honorarios(cs).items()}
    assert mk["VALOR_SETUP"] == "R$ 2.000,00" and mk["HORAS_RECUPERACAO"] == "96"
    assert mk["VALOR_RECUPERACAO"] == "R$ 12.000,00" and mk["VALOR_MENSAL_MATRIZ"] == "R$ 2.500,00"
    assert mk["HONORARIO_MENSAL"] == "R$ 4.000,00" and mk["VALOR_HORA"] == "R$ 125,00"
    assert mk["DECIMO_TERCEIRO"] == "—"  # o contrato (fonte dos campos escalares) diz que não há 13º
    # dado muda -> texto muda
    cs[0]["valor_hora_centavos"] = 15_000
    assert _marcadores_honorarios(cs)["VALOR_SETUP"].replace(" ", " ") == "R$ 2.400,00"


def test_pdf_contrato_resolve_marcadores_de_honorarios() -> None:
    dados = _fixture_dados_d2()
    dados["contratos_servico"][0]["memoria_horas_json"] = [{"codigo": "SETUP", "frente": "Implantação", "horas": 16}]
    dados["secoes"]["d2_03_contrato"] = [{"codigo_secao": "c2", "titulo": "Honorários", "ordem": 1,
                                          "conteudo_md": "Setup de {{VALOR_SETUP}} e mensal de {{HONORARIO_MENSAL}}.",
                                          "status_validacao": "pendente_revisao"}]
    html = html_documento("d2_03_contrato", para_web=True, dados=dados).replace(" ", " ").replace("&nbsp;", " ")
    assert "Setup de R$ 2.000,00 e mensal de R$ 4.000,00." in html
    assert "{{" not in html
