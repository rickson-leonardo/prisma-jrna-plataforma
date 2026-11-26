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
from sistema.web.emissor_dossie2 import _capital_doc01, _normalizar_docs_admissao, html_documento
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




