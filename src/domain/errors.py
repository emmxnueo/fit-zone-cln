"""Errores de dominio. Cada uno lleva el código HTTP que la API debe devolver
(Anexo B del BRD): 409 conflicto de estado/cupo/membresía, 422 regla violada."""


class ErrorDeDominio(Exception):
    codigo_http = 400

    def __init__(self, mensaje: str, regla: str | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.regla = regla


class ReglaDeNegocioViolada(ErrorDeDominio):
    """Una regla RN-xx no se cumple (422)."""

    codigo_http = 422


class ConflictoDeEstado(ErrorDeDominio):
    """La operación choca con el estado actual del recurso (409)."""

    codigo_http = 409


class TransicionInvalida(ConflictoDeEstado):
    """La máquina de estados no permite la acción desde el estado actual (RN-41)."""


class CupoAgotado(ConflictoDeEstado):
    """El plan ya no tiene cupo de contratación (RN-39)."""


class MembresiaActivaExistente(ConflictoDeEstado):
    """El socio ya tiene una membresía activa (RN-03)."""
