"""Value Objects del módulo de contratación de membresías (RN-38)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .errors import ReglaDeNegocioViolada

_CENTAVOS = Decimal("0.01")


@dataclass(frozen=True, order=True)
class Dinero:
    """Importe en MXN. Siempre Decimal con 2 decimales, nunca float."""

    monto: Decimal

    def __post_init__(self) -> None:
        if isinstance(self.monto, float):
            raise TypeError("Dinero no acepta float; usa Decimal o str")
        valor = Decimal(str(self.monto)).quantize(_CENTAVOS, ROUND_HALF_UP)
        if valor < 0:
            raise ReglaDeNegocioViolada("El importe no puede ser negativo", "RN-38")
        object.__setattr__(self, "monto", valor)

    @classmethod
    def de(cls, valor: str | int | Decimal) -> "Dinero":
        return cls(Decimal(str(valor)))

    def __add__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.monto + otro.monto)

    def por(self, factor: int) -> "Dinero":
        return Dinero(self.monto * factor)

    def __str__(self) -> str:
        return f"{self.monto} MXN"


CERO = Dinero(Decimal("0"))


@dataclass(frozen=True)
class Cantidad:
    """Periodos contratados: entero de 1 o más (RN-38)."""

    valor: int

    def __post_init__(self) -> None:
        if isinstance(self.valor, bool) or not isinstance(self.valor, int):
            raise ReglaDeNegocioViolada("La cantidad debe ser un entero", "RN-38")
        if self.valor < 1:
            raise ReglaDeNegocioViolada("La cantidad debe ser 1 o más", "RN-38")


@dataclass(frozen=True)
class LineaSolicitud:
    """Plan × periodos contratados. Guarda el precio vigente al solicitar."""

    plan_id: str
    precio_unitario: Dinero
    cantidad: Cantidad

    @property
    def subtotal(self) -> Dinero:
        return self.precio_unitario.por(self.cantidad.valor)
