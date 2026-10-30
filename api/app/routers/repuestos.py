from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlmodel import Session

from app.almacenamiento import guardar_archivo
from app.auth import Usuario, requiere_rol, usuario_actual
from app.db import get_session
from app.dependencias import stock_service
from app.models import Rol
from app.repositories import UbicacionRepository
from app.schemas import RepuestoRespuesta, StockRespuesta, UsoCrear, UsoRespuesta
from app.services import StockService

router = APIRouter(tags=["stock"])


@router.get("/repuestos/{codigo}", response_model=RepuestoRespuesta)
def obtener_repuesto(
    codigo: str,
    _usuario: Usuario = Depends(usuario_actual),
    servicio: StockService = Depends(stock_service),
) -> RepuestoRespuesta:
    return RepuestoRespuesta.desde(servicio.consultar(codigo))


@router.post("/repuestos/{codigo}/usos", status_code=status.HTTP_201_CREATED, response_model=UsoRespuesta)
def registrar_uso(
    codigo: str,
    uso: UsoCrear,
    usuario: Usuario = Depends(requiere_rol(Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: StockService = Depends(stock_service),
) -> UsoRespuesta:
    return UsoRespuesta.desde(servicio.registrar_uso(codigo, uso.destino_id, uso.cantidad, usuario))


@router.post(
    "/repuestos/{codigo}/recepciones",
    status_code=status.HTTP_201_CREATED,
    response_model=StockRespuesta,
)
def registrar_recepcion(
    codigo: str,
    lote: str = Form(min_length=1),
    cantidad: int = Form(ge=1),
    ubicacion: str = Form(),
    remito: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(requiere_rol(Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: StockService = Depends(stock_service),
) -> StockRespuesta:
    ruta = guardar_archivo(remito, "remitos") if remito and remito.filename else None
    return StockRespuesta.desde(servicio.registrar_recepcion(codigo, lote, cantidad, ubicacion, ruta, usuario))


@router.get("/ubicaciones", response_model=list[str])
def listar_ubicaciones(
    _usuario: Usuario = Depends(usuario_actual),
    session: Session = Depends(get_session),
) -> list[str]:
    return [ubicacion.codigo for ubicacion in UbicacionRepository(session).listar()]
