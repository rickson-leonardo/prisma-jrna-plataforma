"""Modelos da familia de comprovantes bancarios e avisos de tarifa."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo

_NOMES_COMPROVANTES: tuple[str, ...] = (
    "Comprovante-BOL-recebido",
    "Comprovante-PIX-enviado",
    "Comprovante-PIX-recebido",
    "Comprovante-PIX-recebido-PF",
    "Comprovante-TED-enviada",
    "Comprovante-TED-recebida",
    "Comprovante-TED-recebido",
    "Comprovante-cheque-pago",
    "Comprovante-credito-cartao",
    "Comprovante-debito",
    "Comprovante-debito-automatico",
    "Comprovante-debito-frete",
    "Comprovante-deposito-especie",
    "Comprovante-liberacao-credito",
    "Comprovante-pagto-boleto",
    "Comprovante-pagto-tributo",
)

MODELOS: dict[str, SpecModelo] = {
    nome: SpecModelo(
        nome=nome,
        tipo="comprovante",
        familia="comprovantes",
        rotulos_numero=(
            "IDENTIFICADOR (E2E)",
            "IDENTIFICADOR",
            "NOSSO NÚMERO (FICTÍCIO)",
            "NOSSO NÚMERO",
            "CHEQUE Nº",
            "CONTRATO",
        ),
        rotulos_data=(
            "DATA / HORA DO CRÉDITO",
            "DATA / HORA",
            "DATA DO DÉBITO NA CONTA",
            "DATA",
        ),
        rotulos_valor=("VALOR", "TOTAL DEPOSITADO"),
    )
    for nome in _NOMES_COMPROVANTES
}

MODELOS["Aviso-debito-tarifas"] = SpecModelo(
    nome="Aviso-debito-tarifas",
    tipo="comprovante",
    familia="comprovantes",
    rotulos_numero=("REFERÊNCIA NO EXTRATO",),
    rotulos_data=(),
    rotulos_valor=("TOTAL DEBITADO",),
)
