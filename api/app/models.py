from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Rol(StrEnum):
    OPERARIO = "OPERARIO"
    MANTENIMIENTO = "MANTENIMIENTO"
    ENCARGADO = "ENCARGADO"
    CONSULTA = "CONSULTA"


class Turno(StrEnum):
    MANANA = "manana"
    TARDE = "tarde"
    NOCHE = "noche"


class EstadoIncidencia(StrEnum):
    REPORTADA = "REPORTADA"
    EN_REPARACION = "EN_REPARACION"
    RESUELTA = "RESUELTA"


class EstadoReserva(StrEnum):
    ACTIVA = "ACTIVA"
    EJECUTADA = "EJECUTADA"
    LIBERADA = "LIBERADA"


class TipoMovimiento(StrEnum):
    ENTRADA = "entrada"
    SALIDA = "salida"
    RESERVA = "reserva"
    LIBERACION = "liberacion"
    CONSUMO = "consumo"


class Maquina(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre: str
    tipo: str


class Ubicacion(SQLModel, table=True):
    codigo: str = Field(primary_key=True)
    descripcion: str | None = None


class Repuesto(SQLModel, table=True):
    # La CHECK de stock es la última barrera de RN-01 ante concurrencia (ver docs/adr/0001).
    __table_args__ = (
        CheckConstraint("stock_fisico >= 0", name="ck_repuesto_stock_fisico_no_negativo"),
        CheckConstraint("umbral_minimo >= 0", name="ck_repuesto_umbral_no_negativo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre: str
    descripcion: str | None = None
    lote: str | None = None
    ubicacion_codigo: str | None = Field(default=None, foreign_key="ubicacion.codigo")
    stock_fisico: int = 0
    umbral_minimo: int = 0


class Incidencia(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    maquina_id: int = Field(foreign_key="maquina.id")
    descripcion: str
    turno: Turno
    estado: EstadoIncidencia = EstadoIncidencia.REPORTADA
    reportada_por: str
    creada_en: datetime = Field(default_factory=ahora)

    @property
    def codigo(self) -> str:
        return f"INC-{self.id:04d}"


class FotoIncidencia(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incidencia_id: int = Field(foreign_key="incidencia.id", index=True)
    ruta: str


class LineaUso(SQLModel, table=True):
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_linea_uso_cantidad_positiva"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    incidencia_id: int = Field(foreign_key="incidencia.id", index=True)
    cantidad: int
    usuario: str
    fecha: datetime = Field(default_factory=ahora)


class Reserva(SQLModel, table=True):
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_reserva_cantidad_positiva"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    motivo: str
    estado: EstadoReserva = EstadoReserva.ACTIVA
    creada_por: str
    creada_en: datetime = Field(default_factory=ahora)
    cerrada_por: str | None = None
    cerrada_en: datetime | None = None

    @property
    def codigo(self) -> str:
        return f"RES-{self.id:04d}"


class Recepcion(SQLModel, table=True):
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_recepcion_cantidad_positiva"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    lote: str
    cantidad: int
    ubicacion_codigo: str = Field(foreign_key="ubicacion.codigo")
    remito_ruta: str | None = None
    usuario: str
    fecha: datetime = Field(default_factory=ahora)


class MovimientoStock(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    tipo: TipoMovimiento
    cantidad: int
    referencia: str
    usuario: str
    fecha: datetime = Field(default_factory=ahora)
