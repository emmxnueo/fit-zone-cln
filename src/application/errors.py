from src.domain.errors import ErrorDeDominio


class NoEncontrado(ErrorDeDominio):
    """El recurso solicitado no existe (404)."""

    codigo_http = 404
