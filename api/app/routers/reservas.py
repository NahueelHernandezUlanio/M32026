from fastapi import APIRouter, Depends, status

from app.auth import Usuario, requiere_rol, usuario_actual
from app.dependencias import reserva_service
from app.models import Repuesto, Reserva, Rol
from app.schemas import ReservaCrear, ReservaOperacionRespuesta, ReservaRespuesta, StockRespuesta
from app.services import EstadoStock, ReservaService

router = APIRouter(tags=["reservas"])


def a_respuesta(reserva: Reserva, repuesto: Repuesto) -> ReservaRespuesta:
    return ReservaRespuesta(
        id=reserva.codigo,
        repuesto_codigo=repuesto.codigo,
        cantidad=reserva.cantidad,
        motivo=reserva.motivo,
        estado=reserva.estado,
    )


def a_operacion(reserva: Reserva, estado: EstadoStock) -> ReservaOperacionRespuesta:
    return ReservaOperacionRespuesta(
        reserva=a_respuesta(reserva, estado.repuesto),
        stock=StockRespuesta.desde(estado),
        alerta_umbral=estado.bajo_umbral,
    )


@router.get("/reservas", response_model=list[ReservaRespuesta])
def listar_reservas_activas(
    _usuario: Usuario = Depends(usuario_actual),
    servicio: ReservaService = Depends(reserva_service),
) -> list[ReservaRespuesta]:
    return [a_respuesta(reserva, repuesto) for reserva, repuesto in servicio.listar_activas()]


@router.post("/reservas", status_code=status.HTTP_201_CREATED, response_model=ReservaOperacionRespuesta)
def crear_reserva(
    datos: ReservaCrear,
    usuario: Usuario = Depends(requiere_rol(Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: ReservaService = Depends(reserva_service),
) -> ReservaOperacionRespuesta:
    return a_operacion(*servicio.reservar(datos.repuesto_codigo, datos.cantidad, datos.motivo, usuario))


@router.post("/reservas/{codigo}/liberacion", response_model=ReservaOperacionRespuesta)
def liberar_reserva(
    codigo: str,
    usuario: Usuario = Depends(usuario_actual),
    servicio: ReservaService = Depends(reserva_service),
) -> ReservaOperacionRespuesta:
    return a_operacion(*servicio.liberar(codigo, usuario))


@router.post("/reservas/{codigo}/ejecucion", response_model=ReservaOperacionRespuesta)
def ejecutar_reserva(
    codigo: str,
    usuario: Usuario = Depends(requiere_rol(Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: ReservaService = Depends(reserva_service),
) -> ReservaOperacionRespuesta:
    return a_operacion(*servicio.ejecutar(codigo, usuario))
