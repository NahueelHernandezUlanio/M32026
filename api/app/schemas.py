from pydantic import BaseModel, Field

from app.models import EstadoIncidencia, EstadoReserva, Rol
from app.services import EstadoStock


class ErrorRespuesta(BaseModel):
    codigo: str
    mensaje: str


class HealthRespuesta(BaseModel):
    status: str


class UsuarioRespuesta(BaseModel):
    nombre: str
    rol: Rol


class IncidenciaRespuesta(BaseModel):
    id: str
    estado: EstadoIncidencia


class DestinoUso(BaseModel):
    id: str
    maquina: str


class StockRespuesta(BaseModel):
    stock_fisico: int
    stock_reservado: int
    stock_disponible: int

    @classmethod
    def desde(cls, estado: EstadoStock) -> "StockRespuesta":
        return cls(
            stock_fisico=estado.repuesto.stock_fisico,
            stock_reservado=estado.stock_reservado,
            stock_disponible=estado.stock_disponible,
        )


class RepuestoRespuesta(StockRespuesta):
    codigo: str
    nombre: str
    lote: str | None
    ubicacion: str | None
    umbral_minimo: int

    @classmethod
    def desde(cls, estado: EstadoStock) -> "RepuestoRespuesta":
        repuesto = estado.repuesto
        return cls(
            codigo=repuesto.codigo,
            nombre=repuesto.nombre,
            lote=repuesto.lote,
            ubicacion=repuesto.ubicacion_codigo,
            umbral_minimo=repuesto.umbral_minimo,
            **StockRespuesta.desde(estado).model_dump(),
        )


class UsoCrear(BaseModel):
    destino_id: str
    cantidad: int = Field(default=1, ge=1)


class UsoRespuesta(StockRespuesta):
    alerta_umbral: bool

    @classmethod
    def desde(cls, estado: EstadoStock) -> "UsoRespuesta":
        return cls(alerta_umbral=estado.bajo_umbral, **StockRespuesta.desde(estado).model_dump())


class ReservaCrear(BaseModel):
    repuesto_codigo: str
    cantidad: int = Field(ge=1)
    motivo: str = Field(min_length=1)


class ReservaRespuesta(BaseModel):
    id: str
    repuesto_codigo: str
    cantidad: int
    motivo: str
    estado: EstadoReserva


class ReservaOperacionRespuesta(BaseModel):
    reserva: ReservaRespuesta
    stock: StockRespuesta
    alerta_umbral: bool
