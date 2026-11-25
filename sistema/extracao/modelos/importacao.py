"""Modelos da familia de cambio e importacao."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo

MODELOS: dict[str, SpecModelo] = {
    "Contrato-cambio": SpecModelo(
        nome="Contrato-cambio",
        tipo="cambio_importacao",
        familia="importacao",
        rotulos_numero=("REF. EXTRATO",),
        rotulos_data=("DATA DA CONTRATAÇÃO",),
        rotulos_valor=("TOTAL DEBITADO NA CONTA (Doc/Ref CAMB",),
    ),
    "Commercial-Invoice": SpecModelo(
        nome="Commercial-Invoice",
        tipo="cambio_importacao",
        familia="importacao",
        moeda_padrao="USD",
        rotulos_numero=("BANK REFERENCE",),
        rotulos_data=("INVOICE DATE",),
        rotulos_valor=("TOTAL INVOICE VALUE CIF", "TOTAL INVOICE VALUE FOB", "TOTAL INVOICE VALUE"),
    ),
    "Extrato-DI": SpecModelo(
        nome="Extrato-DI",
        tipo="cambio_importacao",
        familia="importacao",
        rotulos_numero=("Nº DA DI (FICTÍCIA)",),
        rotulos_data=("DATA DE REGISTRO",),
        rotulos_valor=("VALOR ADUANEIRO (R$)",),
    ),
}
