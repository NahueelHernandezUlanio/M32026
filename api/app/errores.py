class ErrorDeDominio(Exception):
    status_code = 400

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class NoEncontrado(ErrorDeDominio):
    status_code = 404

    def __init__(self, mensaje: str) -> None:
        super().__init__("NO_ENCONTRADO", mensaje)


class ReglaDeNegocio(ErrorDeDominio):
    status_code = 409


class NoAutenticado(ErrorDeDominio):
    status_code = 401

    def __init__(self) -> None:
        super().__init__("NO_AUTENTICADO", "Falta un token válido en el header Authorization.")


class PermisoDenegado(ErrorDeDominio):
    status_code = 403

    def __init__(self, mensaje: str = "Tu rol no tiene permiso para esta operación.") -> None:
        super().__init__("PERMISO_DENEGADO", mensaje)
