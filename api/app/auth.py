"""Auth stub de M4: tokens fijos por rol. En M5 se reemplaza por auth real sin tocar los routers."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.errores import NoAutenticado, PermisoDenegado
from app.models import Rol


@dataclass(frozen=True)
class Usuario:
    nombre: str
    rol: Rol


USUARIOS_STUB: dict[str, Usuario] = {
    "token-operario": Usuario("Operario Demo", Rol.OPERARIO),
    "token-mantenimiento": Usuario("Mantenimiento Demo", Rol.MANTENIMIENTO),
    "token-encargado": Usuario("Encargado Demo", Rol.ENCARGADO),
    "token-consulta": Usuario("Gerencia Demo", Rol.CONSULTA),
}

esquema_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
) -> Usuario:
    if credenciales is None or credenciales.credentials not in USUARIOS_STUB:
        raise NoAutenticado()
    return USUARIOS_STUB[credenciales.credentials]


def requiere_rol(*roles: Rol) -> Callable[[Usuario], Usuario]:
    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise PermisoDenegado()
        return usuario

    return dependencia
