import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import Usuario, usuario_actual
from app.errores import ErrorDeDominio
from app.routers import incidencias, repuestos, reservas
from app.schemas import HealthRespuesta, UsuarioRespuesta

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="API de Stock y Mantenimiento de Planta",
    version="0.2.0",
    description="Grupo 3 - S32",
)


@app.exception_handler(ErrorDeDominio)
def manejar_error_de_dominio(_request: Request, error: ErrorDeDominio) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"codigo": error.codigo, "mensaje": error.mensaje})


@app.exception_handler(RequestValidationError)
def manejar_error_de_validacion(_request: Request, error: RequestValidationError) -> JSONResponse:
    campos = ", ".join(".".join(str(parte) for parte in detalle["loc"][1:]) for detalle in error.errors())
    return JSONResponse(
        status_code=422,
        content={"codigo": "DATOS_INVALIDOS", "mensaje": f"Datos inválidos en: {campos}."},
    )


@app.get("/health", response_model=HealthRespuesta, tags=["sistema"])
def health() -> HealthRespuesta:
    return HealthRespuesta(status="ok")


@app.get("/auth/me", response_model=UsuarioRespuesta, tags=["auth"])
def usuario_logueado(usuario: Usuario = Depends(usuario_actual)) -> UsuarioRespuesta:
    return UsuarioRespuesta(nombre=usuario.nombre, rol=usuario.rol)


app.include_router(incidencias.router)
app.include_router(repuestos.router)
app.include_router(reservas.router)
