"""Definicao declarativa de modelos de PDFs da Camada 2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecModelo:
    """Especificacao declarativa de um modelo de documento PDF."""

    nome: str
    tipo: str  # fiscal, comprovante, tributo_guia, cambio_importacao, credito_cartao, titulo, controle_interno
    familia: str  # fiscal, comprovantes, tributos, importacao, credito_cartao, controle_interno
    moeda_padrao: str = "BRL"
    rotulos_numero: tuple[str, ...] = ()
    rotulos_data: tuple[str, ...] = ()
    rotulos_valor: tuple[str, ...] = ()
    eh_prosa: bool = False
