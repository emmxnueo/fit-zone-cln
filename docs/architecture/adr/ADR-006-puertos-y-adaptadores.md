# ADR-006: Puertos y adaptadores; repositorios en memoria y SQL

**Estado:** Aceptada, implementada

## Contexto
El PIA exige persistencia en PostgreSQL y pruebas unitarias rápidas. Los casos de uso no deben depender de la base de datos, y el despliegue debe poder arrancar aun sin base configurada.

## Alternativas
- **SQLAlchemy directo en los casos de uso:** menos código, pero la lógica queda atada a la base y las pruebas necesitan una base.
- **Un repositorio genérico para todo:** una sola interfaz, pero obliga a implementar métodos que cada consumidor no usa.
- **Un puerto por agregado o rol, con adaptadores intercambiables.**

## Decisión
`application/puertos.py` define `Protocol` pequeños: `RepositorioSocios`, `RepositorioPlanes`, `RepositorioSolicitudes`, `RepositorioClases`, `RepositorioIngresos`, `Reloj` y `PublicadorDeEventos`. `infrastructure/` los implementa con SQLAlchemy (`repositorios_sql.py`) y en memoria (`memoria.py`). `composicion.crear_servicios()` elige: con `DATABASE_URL` usa PostgreSQL; sin ella, memoria. Los repositorios SQL se prueban sobre SQLite en memoria, y el flujo de reservas también sobre PostgreSQL cuando hay uno disponible.

## Consecuencias
- Beneficio: el dominio y los casos de uso se prueban sin base; cambiar de motor no toca el negocio.
- Costo: dos implementaciones que deben comportarse igual; una prueba compara sus conteos de cupo.
- Limitación: el publicador de eventos es solo en memoria, así que los eventos no sobreviven a un reinicio.

## Trazabilidad
Principios D, L e I de [solid.md](../solid.md) · RN-03, RN-39 (consultas de vigencia y cupo) · `tests/unit/infrastructure/test_repositorios_sql.py`
