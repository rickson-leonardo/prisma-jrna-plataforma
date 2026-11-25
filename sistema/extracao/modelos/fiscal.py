"""Modelos da familia fiscal (NF-e, NFS-e, CT-e, Faturas de utilidades)."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo

MODELOS: dict[str, SpecModelo] = {
    "NFe": SpecModelo(
        nome="NFe",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("Nº / SÉRIE",),
        rotulos_data=("DATA DE EMISSÃO",),
        rotulos_valor=("TOTAL DA NOTA",),
    ),
    "NFSe": SpecModelo(
        nome="NFSe",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("NÚMERO",),
        rotulos_data=("DATA DE EMISSÃO",),
        rotulos_valor=("VALOR TOTAL DOS SERVIÇOS",),
    ),
    "CTe": SpecModelo(
        nome="CTe",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("Nº / SÉRIE",),
        rotulos_data=("EMISSÃO",),
        rotulos_valor=("VALOR TOTAL DA PRESTAÇÃO",),
    ),
    "NFe-compra": SpecModelo(
        nome="NFe-compra",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("Nº / SÉRIE",),
        rotulos_data=("EMISSÃO",),
        rotulos_valor=("TOTAL DA NOTA",),
    ),
    "NFe-entrada-importacao": SpecModelo(
        nome="NFe-entrada-importacao",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("DI Nº",),
        rotulos_data=("EMISSÃO",),
        rotulos_valor=("TOTAL DA NOTA",),
    ),
    "Fatura-energia": SpecModelo(
        nome="Fatura-energia",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("UNIDADE CONSUMIDORA",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("TOTAL A PAGAR", "TOTAL DA FATURA"),
    ),
    "Fatura-telecom": SpecModelo(
        nome="Fatura-telecom",
        tipo="fiscal",
        familia="fiscal",
        rotulos_numero=("PLANO",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("TOTAL",),
    ),
}
