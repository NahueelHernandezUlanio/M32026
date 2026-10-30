from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.almacenamiento import guardar_archivo
from app.auth import Usuario, requiere_rol
from app.dependencias import incidencia_service
from app.models import Rol, Turno
from app.schemas import DestinoUso, IncidenciaRespuesta
from app.services import IncidenciaService

router = APIRouter(tags=["incidencias"])


@router.post("/incidencias", status_code=status.HTTP_201_CREATED, response_model=IncidenciaRespuesta)
def crear_incidencia(
    codigo_maquina: str = Form(),
    descripcion: str = Form(min_length=1),
    turno: Turno | None = Form(default=None),
    fotos: list[UploadFile] = File(default=[]),
    usuario: Usuario = Depends(requiere_rol(Rol.OPERARIO, Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: IncidenciaService = Depends(incidencia_service),
) -> IncidenciaRespuesta:
    rutas = [guardar_archivo(foto, "incidencias") for foto in fotos if foto.filename]
    incidencia = servicio.reportar(codigo_maquina, descripcion, turno, rutas, usuario)
    return IncidenciaRespuesta(id=incidencia.codigo, estado=incidencia.estado)


@router.post("/incidencias/{codigo}/reparacion", response_model=IncidenciaRespuesta)
def iniciar_reparacion(
    codigo: str,
    _usuario: Usuario = Depends(requiere_rol(Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: IncidenciaService = Depends(incidencia_service),
) -> IncidenciaRespuesta:
    incidencia = servicio.iniciar_reparacion(codigo)
    return IncidenciaRespuesta(id=incidencia.codigo, estado=incidencia.estado)


@router.get("/destinos-uso", response_model=list[DestinoUso])
def listar_destinos_uso(
    _usuario: Usuario = Depends(requiere_rol(Rol.MANTENIMIENTO, Rol.ENCARGADO)),
    servicio: IncidenciaService = Depends(incidencia_service),
) -> list[DestinoUso]:
    return [DestinoUso(id=codigo, maquina=maquina) for codigo, maquina in servicio.destinos_de_uso()]
