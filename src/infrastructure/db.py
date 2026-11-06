"""Conexión y modelos de persistencia (SQLAlchemy 2.0).

Estas clases son filas de tablas, NO entidades del dominio: el dominio no las
conoce. Los repositorios de `repositorios_sql.py` traducen entre ambos mundos.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class SocioRow(Base):
    __tablename__ = "socios"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    es_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ciudad: Mapped[str] = mapped_column(String(80), default="")


class PlanRow(Base):
    __tablename__ = "planes"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(120))
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cupo: Mapped[int] = mapped_column(Integer)
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)
    duracion_meses: Mapped[int] = mapped_column(Integer, default=1)


class SolicitudRow(Base):
    __tablename__ = "solicitudes"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    socio_id: Mapped[str] = mapped_column(ForeignKey("socios.id"), index=True)
    fecha_solicitud: Mapped[date] = mapped_column(Date)
    validada: Mapped[bool] = mapped_column(Boolean, default=False)
    cortesia_activa: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia: Mapped[str] = mapped_column(String(120), default="")
    estado: Mapped[str] = mapped_column(String(20), index=True)
    lineas: Mapped[list["LineaRow"]] = relationship(
        back_populates="solicitud",
        cascade="all, delete-orphan",
        order_by="LineaRow.id",
    )


class LineaRow(Base):
    __tablename__ = "lineas_solicitud"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[str] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("planes.id"))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cantidad: Mapped[int] = mapped_column(Integer)
    solicitud: Mapped[SolicitudRow] = relationship(back_populates="lineas")


def normalizar_url(url: str) -> str:
    """Railway/Render/Heroku entregan `postgres://` o `postgresql://`; SQLAlchemy
    con psycopg 3 necesita `postgresql+psycopg://`."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def crear_motor(url: str) -> Engine:
    url = normalizar_url(url)
    if url.startswith("sqlite"):
        # SQLite en memoria (pruebas): una sola conexión compartida.
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    return create_engine(url, pool_pre_ping=True)


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker:
    Base.metadata.create_all(engine)  # crea las tablas si no existen
    return sessionmaker(engine, expire_on_commit=False)
