"""Modelos da familia tributaria (guias de recolhimento e apuracao PGDAS-D)."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo

MODELOS: dict[str, SpecModelo] = {
    "DAS": SpecModelo(
        nome="DAS",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DO DOCUMENTO",),
        rotulos_data=("DATA DE VENCIMENTO",),
        rotulos_valor=("VALOR TOTAL DO DOCUMENTO",),
    ),
    "DARF-IPI": SpecModelo(
        nome="DARF-IPI",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DO DOCUMENTO",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("VALOR TOTAL",),
    ),
    "PGDAS-D": SpecModelo(
        nome="PGDAS-D",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("PERÍODO DE APURAÇÃO (PA)",),
        rotulos_data=(),
        rotulos_valor=("TOTAL DO DAS",),
    ),
    "GNRE-DF": SpecModelo(
        nome="GNRE-DF",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DA GUIA",),
        rotulos_data=("DATA DE VENCIMENTO",),
        rotulos_valor=("VALOR PRINCIPAL", "(=) TOTAL A RECOLHER"),
    ),
    "GNRE-ES": SpecModelo(
        nome="GNRE-ES",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DA GUIA",),
        rotulos_data=("DATA DE VENCIMENTO",),
        rotulos_valor=("VALOR PRINCIPAL", "(=) TOTAL A RECOLHER"),
    ),
    "GNRE-MG": SpecModelo(
        nome="GNRE-MG",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DA GUIA",),
        rotulos_data=("DATA DE VENCIMENTO",),
        rotulos_valor=("VALOR PRINCIPAL", "(=) TOTAL A RECOLHER"),
    ),
    "Guia-AFRMM": SpecModelo(
        nome="Guia-AFRMM",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("DI / CONHECIMENTO",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("VALOR DO AFRMM",),
    ),
    "Guia-DARE-GO-ICMS-importacao": SpecModelo(
        nome="Guia-DARE-GO-ICMS-importacao",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DA GUIA",),
        rotulos_data=("DATA DE VENCIMENTO",),
        rotulos_valor=("(=) TOTAL A RECOLHER",),
    ),
    "Guia-DARE-GO-ST": SpecModelo(
        nome="Guia-DARE-GO-ST",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("PERÍODO DE REFERÊNCIA",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("(=) TOTAL A RECOLHER",),
    ),
    "Guia-DARE-SC": SpecModelo(
        nome="Guia-DARE-SC",
        tipo="tributo_guia",
        familia="tributos",
        rotulos_numero=("Nº DA GUIA",),
        rotulos_data=("DATA DE VENCIMENTO",),
        rotulos_valor=("(=) TOTAL A RECOLHER",),
    ),
}
